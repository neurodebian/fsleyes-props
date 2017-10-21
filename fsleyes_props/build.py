#!/usr/bin/env python
#
# build.py - Automatically build a wx GUI for a HasProperties object.

# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

"""Automatically build a :mod:`wx` GUI for a :class:`.HasProperties` instance.

This module provides functionality to automatically build a :mod:`wx` GUI
containing widgets which allow the user to change the property values
(:class:`.PropertyBase` instances) of a specified :class:`.HasProperties`
instance.


This module has two main entry points:

 .. autosummary::
    :nosignatures:

    buildGUI
    buildDialog


A number of classes are defined in the separate :mod:`.build_parts` module.
The :class:`.ViewItem` class allows the layout of the generated interface to
be customised.  Property widgets may be grouped together by embedding them
within a :class:`.HGroup` or :class:`.VGroup` object; they will then
respectively be laid out horizontally or verticaly.  Groups may be embedded
within a :class:`.NotebookGroup` object, which will result in a notebook-like
interface containing a tab for each child :class:`.Group`.


The label for, and behaviour of, the widget for an individual property may be
customised with a :class:`.Widget` object. As an example::

    import wx
    import fsleyes_props as props

    class MyObj(props.HasProperties):
        myint  = props.Int()
        mybool = props.Boolean()

    # A reasonably complex view specification
    view = props.VGroup(
      label='MyObj properties',
      children=(
          props.Widget('mybool',
                       label='MyObj Boolean',
                       tooltip='If this is checked, you can '
                               'edit the MyObj Integer'),
          props.Widget('myint',
                       label='MyObj Integer',
                       enabledWhen=lambda mo: mo.mybool)))

    # A simpler view specification
    view = props.VGroup(('mybool', 'myint'))

    # The simplest view specification - a
    # default one will be generated
    view = None

    myobj = MyObj()

    app   = wx.App()
    frame = wx.Frame(None)

    myObjPanel = props.buildGUI(frame, myobj, view)


See the :mod:`.build_parts` module for details on the :class:`.Widget` (and
other :class:`.ViewItem`) definitions.


You may also pass in widget labels and tooltips to the :func:`buildGUI`
function::

    labels = {
        'myint':  'MyObj Integer value',
        'mybool': 'MyObj Boolean value'
    }

    tooltips = {
        'myint' : 'MyObj Integer tooltip'
    }

    props.buildGUI(frame, myobj, view=view, labels=labels, tooltips=tooltips)


As an alternative to passing in a view, labels, and tooltips to the
:func:`buildGUI` function, they may be specified as class attributes of the
``HasProperties`` instance or class, with respective names ``_view``,
``_labels``, and ``_tooltips``::

    class MyObj(props.HasProperties):
        myint  = props.Int()
        mybool = props.Boolean()

        _view = props.HGroup(('myint', 'mybool'))
        _labels = {
            'myint':  'MyObj integer',
            'mybool': 'MyObj boolean'
        }
        _tooltips = {
            'myint':  'MyObj integer tooltip',
            'mybool': 'MyObj boolean tooltip'
        }

    props.buildGUI(frame, myobj)

"""

import logging
import weakref
import copy
import sys

import six
import wx

from . import                          widgets
from . import                          syncable
from . import build_parts           as parts
import fsleyes_widgets.notebook     as nb
import fsleyes_widgets.bitmaptoggle as bmptoggle


log = logging.getLogger(__name__)


class PropGUI(object):
    """An internal container class used for convenience. Stores references to
    all :mod:`wx` objects that are created, and to all conditional callbacks
    (which control visibility/state).
    """

    def __init__(self):

        # onChangeCallbacks is a list of
        # tuples, each of which contains:
        #
        # ([weakref(HasProperties instances)],
        #  [propertyNames],
        #  listenerName,
        #  callback)
        #
        # If a property name is None, that
        # means that it is a global listener
        # on the HasProps instance
        self.onChangeCallbacks = []

        # A dictionary of {ViewItem.key : wx.Window} mappings
        self.guiObjects        = {}

        # The top level GUI container (typically a wx.Panel)
        self.topLevel          = None


def _configureEnabledWhen(viewItem, guiObj, hasProps, propGui):
    """Configures a callback function for this view item, if its ``enabledWhen``
    attribute was set.

    :param viewItem: The :class:`.ViewItem` object

    :param guiObj:   The GUI object created from the :class:`.ViewItem`

    :param hasProps: The :class:`.HasProperties` instance

    :param propGui:  The :class:`PropGui` instance, in which references to
                     all event callbacks are stored
    """

    if viewItem.enabledWhen is None: return None

    # Recursively toggle the enabled/disabled state
    # of the given object and all its children.
    def toggleAll(obj, state):

        obj.Enable(state)

        for child in obj.GetChildren():
            toggleAll(child, state)

    def _toggleEnabled(*args):
        """Calls the viewItem.enabledWhen function and
        enables/disables the GUI object, depending
        upon the result.
        """

        parent         = guiObj.GetParent()
        isNotebookPage = isinstance(parent, nb.Notebook)
        state          = viewItem.enabledWhen(*args)

        if isNotebookPage:
            if state: parent.EnablePage( parent.FindPage(guiObj))
            else:     parent.DisablePage(parent.FindPage(guiObj))

        elif guiObj.IsEnabled() != state:
            toggleAll(guiObj, state)
            guiObj.Refresh()
            guiObj.Update()

    _configureEventCallback(
        viewItem,
        _toggleEnabled,
        'enable',
        hasProps,
        guiObj,
        propGui)


def _configureVisibleWhen(viewItem, guiObj, hasProps, propGui):
    """Configures a callback function for this view item, if its visibleWhen
    attribute was set. See :func:`_configureEnabledWhen`.

    :param viewItem: The :class:`.ViewItem` object

    :param guiObj:   The GUI object created from the :class:`.ViewItem`

    :param hasProps: The :class:`.HasProperties` instance

    :param propGui:  The :class:`PropGui` instance, in which references to
                     all event callbacks are stored
    """

    if viewItem.visibleWhen is None: return None

    def _toggleVis(*args):

        parent         = guiObj.GetParent()
        isNotebookPage = isinstance(parent, nb.Notebook)
        visible        = viewItem.visibleWhen(*args)

        if isNotebookPage:
            if visible: parent.ShowPage(parent.FindPage(guiObj))
            else:       parent.HidePage(parent.FindPage(guiObj))

        elif visible != guiObj.IsShown():
            parent.GetSizer().Show(guiObj, visible)
            parent.GetSizer().Layout()

    _configureEventCallback(
        viewItem,
        _toggleVis,
        'visible',
        hasProps,
        guiObj,
        propGui)


def _configureEventCallback(
        viewItem,
        callback,
        evType,
        hasProps,
        guiObj,
        propGui):
    """Called by both the :func:`_configureVisibleWhen` and
    :func:`_configureEnabledWhen` functions.

    Wraps the given ``callback`` function (which is essentially a
    ``ViewItem.visibleWhen`` or ``ViewItem.enabledWhen`` function) inside
    another function, which handles the marshalling of arguments to be passed
    to the ``callback``.

    The arguments that are passed to the function depend on the value of the
    ``ViewItem.dependencies`` attribute - see the :mod:`build_parts` module
    for an explanation.

    The resulting callback function is added to the
    ``PropGui.onChangeCallbacks`` list.

    :arg viewItem: The :class:`.ViewItem` instance

    :arg callback: The callback function to be encapsulated.

    :arg evType:   Purely for logging. Either 'visible' or 'enable'.

    :arg hasProps: The :class:`.HasProperties` instance.

    :arg guiObj:   The :mod:`wx` GUI object which has been created from the
                   ``viewItem`` specification.

    :arg propGui:  The :class:`PropGui` instance which stores references to
                   all event callbacks.
    """

    lName = 'build_py_{}_{}_{}_{}_{}'.format(
        evType,
        type(hasProps).__name__,
        viewItem.key,
        id(guiObj),
        id(propGui.topLevel))

    log.debug('Configuring event callback for '
              '({}.{}) ({} dependencies)'.format(
                  type(hasProps).__name__,
                  viewItem.key,
                  len(viewItem.dependencies)
                  if viewItem.dependencies is not None
                  else '0'))

    # If this viewitem has no dependencies,
    # we just add a global listener to the
    # hasProps instance, and call the callback
    # whenever any properties change
    if viewItem.dependencies is None:

        def onEvent(*a):

            callback(hasProps)
            propGui.topLevel.Layout()
            propGui.topLevel.Refresh()
            propGui.topLevel.Update()

        hasProps.addGlobalListener(lName, onEvent, weak=False)

        propGui.onChangeCallbacks.append(
            ([weakref.ref(hasProps)], [None], lName, onEvent))
        return

    # Otherwise, we have a list
    # of dependencies to process
    targets   = []
    propNames = []

    def onEvent(*a):

        # targets are all weakrefs, hence the
        # 't()' - should I check for None here?
        args  = [hasProps]
        args += [getattr(t(), pn) for t, pn in zip(targets, propNames)]

        callback(*args)
        propGui.topLevel.Layout()
        propGui.topLevel.Refresh()
        propGui.topLevel.Update()

    for dep in viewItem.dependencies:

        target   = None
        propName = None

        # Each dependency is either the name of
        # a property on the hasProps instance..
        if isinstance(dep, six.string_types):
            target   = hasProps
            propName = dep

        # Or a tuple which specifies a different
        # instance, and the property name on that
        # instance
        else:
            instance, propName = dep

            # the first tuple element could
            # be an instance, or a function
            # which returns an instance
            if hasattr(instance, '__call__'):
                instance = instance(hasProps)

            target   = instance
            propName = propName

        targets  .append(weakref.ref(target))
        propNames.append(propName)

        target.addListener(propName, lName, onEvent, weak=False)

    propGui.onChangeCallbacks.append(
        (targets, propNames, lName, onEvent))


def _createLinkBox(parent, viewItem, hasProps, propGui):
    """Creates a checkbox which can be used to link/unlink a property
    from its parent property.
    """

    propName = viewItem.propKey
    linkBox = widgets.makeSyncWidget(parent, hasProps, propName)

    if (hasProps.getParent() is None)                   or \
       (not hasProps.canBeSyncedToParent(    propName)) or \
       (not hasProps.canBeUnsyncedFromParent(propName)):
        viewItem.enabledWhen = None

    return linkBox


def _createLabel(parent, viewItem, hasProps, propGui):
    """Creates a :class:`wx.StaticText` object containing a label for the
    given :class:`.ViewItem`.
    """
    label = wx.StaticText(parent, label=viewItem.label)
    return label


def _createButton(parent, viewItem, hasProps, propGui):
    """Creates a :class:`wx.Button` object for the given :class:`.Button`
    object.
    """

    btnText = None

    if   viewItem.text  is not None: btnText = viewItem.text
    elif viewItem.label is not None: btnText = viewItem.label
    elif viewItem.key   is not None: btnText = viewItem.key

    if viewItem.icon is not None:

        bmp    = wx.Bitmap(viewItem.icon, wx.BITMAP_TYPE_PNG)
        style  = wx.BU_EXACTFIT | wx.ALIGN_CENTRE | wx.BU_NOTEXT
        button = wx.Button(parent, style=style)

        button.SetBitmapLabel(bitmap=bmp)

    else:
        button = wx.Button(parent, label=btnText, style=wx.BU_EXACTFIT)

    button.Bind(wx.EVT_BUTTON, lambda e: viewItem.callback(hasProps, button))
    return button


def _createToggle(parent, viewItem, hasProps, propGui):
    """Creates a widget for the given :class:`.Toggle` object. If no icons
    have been set, a ``wx.CheckBox`` is used. Otherwise a
    :class:`.BitmapToggleButton` is used.
    """

    widget = None
    icon   = viewItem.icon

    # If no icons are set, use a CheckBox
    if icon is None:
        widget = wx.CheckBox(parent)
        event  = wx.EVT_CHECKBOX

    # Otherwise, use a BitmapToggleButton
    else:

        if isinstance(icon, six.string_types):
            icon = [icon]

        for i in range(len(icon)):

            icon[i] = wx.Bitmap(icon[i], wx.BITMAP_TYPE_PNG)

        if len(icon) == 1:
            icon = icon + [None]

        style = wx.BU_EXACTFIT | wx.ALIGN_CENTRE | wx.BU_NOTEXT
        widget = bmptoggle.BitmapToggleButton(parent,
                                              trueBmp=icon[0],
                                              falseBmp=icon[1],
                                              style=style)
        event  = bmptoggle.EVT_BITMAP_TOGGLE

    widget.Bind(event, lambda e: viewItem.callback(hasProps, widget))
    return widget


def _createWidget(parent, viewItem, hasProps, propGui):
    """Creates a widget for the given :class:`.Widget` object, using the
    :func:`.makeWidget` function (see the :mod:`props.widgets` module for more
    details).
    """

    if viewItem.index is not None:
        widget = widgets.makeListWidget(parent,
                                        hasProps,
                                        viewItem.key,
                                        viewItem.index,
                                        **viewItem.kwargs)
    else:
        widget = widgets.makeWidget(    parent,
                                        hasProps,
                                        viewItem.key,
                                        **viewItem.kwargs)

    return widget


def _makeGroupBorder(parent, group, ctr, *args, **kwargs):
    """Makes a border for a :class:`.Group`.

    If a the ``border`` attribute of a :class:`.Group` object has been set to
    ``True``, this function is called. It creates a parent :class:`wx.Panel`
    with a border and title, then creates and embeds the GUI object
    representing the group (via the `ctr` argument). Returns the parent border
    panel, and the group GUI object. Parameters:

    :param parent:   Parent GUI object

    :param group:    :class:`.VGroup`, :class:`.HGroup` or
                     :class:`.NotebookGroup`

    :param ctr:      Constructor for a :class:`wx.Window` object.

    :param args:     Passed to `ctr`. You don't need to pass in the parent.

    :param kwargs:   Passed to `ctr`.
    """

    borderPanel = wx.Panel(parent, style=wx.SUNKEN_BORDER)
    borderSizer = wx.BoxSizer(wx.VERTICAL)
    groupObject = ctr(borderPanel, *args, **kwargs)

    if group.label is not None:
        label = wx.StaticText(borderPanel, label=group.label)
        line  = wx.StaticLine(borderPanel, style=wx.LI_HORIZONTAL)

        font  = label.GetFont()
        font.SetPointSize(font.GetPointSize() - 2)
        font.SetWeight(wx.FONTWEIGHT_LIGHT)
        label.SetFont(font)

        borderSizer.Add(label, border=5, flag=wx.ALL)
        borderSizer.Add(line,  border=5, flag=wx.EXPAND | wx.ALL)

    borderSizer.Add(
        groupObject, border=5, flag=wx.EXPAND | wx.ALL, proportion=1)
    borderPanel.SetSizer(borderSizer)
    borderSizer.Layout()
    borderSizer.Fit(borderPanel)

    return borderPanel, groupObject


def _createNotebookGroup(parent, group, hasProps, propGui):
    """Creates a :class:`fsleyes_widgets.notebook.Notebook` object from the
    given :class:`.NotebookGroup` object.

    The children of the group object are also created via recursive calls to
    the :func:`_create` function.
    """

    if group.border:
        borderPanel, notebook = _makeGroupBorder(
            parent, group, nb.Notebook)
    else:
        notebook = nb.Notebook(parent)

    for i, child in enumerate(group.children):

        if child.label is None: pageLabel = '{}'.format(i)
        else:                   pageLabel = child.label

        if isinstance(child, parts.Group):
            child.border = False

        page = _create(notebook, child, hasProps, propGui)
        notebook.InsertPage(i, page, pageLabel)
        page._notebookIdx = i

    notebook.SetSelection(0)
    notebook.Layout()
    notebook.Fit()

    if group.border: return borderPanel
    else:            return notebook


def _layoutHGroup(group, parent, children, labels):
    """Lays out the children (and labels, if not ``None``) of the given
    :class:`.HGroup` object. Parameters:

    :param group:    :class:`.HGroup` object

    :param parent:   GUI object which represents the group

    :param children: List of GUI objects, the children of the group.

    :param labels:   ``None`` if no labels, otherwise a list of GUI Label
                     objects, one for each child.
    """

    if group.wrap: sizer = wx.WrapSizer(wx.HORIZONTAL)
    else:          sizer = wx.BoxSizer(wx.HORIZONTAL)

    for cidx in range(len(children)):

        vItem = group.children[cidx]

        if isinstance(vItem, parts.LinkBox):
            sizer.Add(children[cidx], flag=wx.ALIGN_CENTER_VERTICAL |
                                           wx.ALIGN_CENTER_HORIZONTAL)

        else:

            if labels is not None and labels[cidx] is not None:

                if group.vertLabels:
                    panel  = wx.Panel(parent, style=wx.SUNKEN_BORDER)
                    pSizer = wx.BoxSizer(wx.VERTICAL)
                    panel.SetSizer(pSizer)

                    labels[  cidx].Reparent(panel)
                    children[cidx].Reparent(panel)

                    pSizer.Add(labels[  cidx], flag=wx.EXPAND)
                    pSizer.Add(children[cidx], flag=wx.EXPAND)
                    sizer .Add(panel,          flag=wx.EXPAND)
                else:
                    sizer.Add(labels[  cidx], flag=wx.EXPAND)
                    sizer.Add(children[cidx], flag=wx.EXPAND, proportion=1)
            else:
                sizer.Add(children[cidx], flag=wx.EXPAND, proportion=1)

        # TODO I have not added support
        # for child groups with borders

    parent.SetSizer(sizer)


def _layoutVGroup(group, parent, children, labels):
    """Lays out the children (and labels, if not ``None``) of the
    given :class:`.VGroup` object. Parameters the same as
    :func:`_layoutHGroup`.
    """

    sizer = wx.GridBagSizer(1, 1)
    sizer.SetEmptyCellSize((0, 0))

    for cidx in range(len(children)):

        vItem       = group.children[cidx]
        child       = children[cidx]
        label       = labels[cidx]
        childParams = {}

        # Groups within VGroups, which don't have a border, are
        # laid out the same as any other widget, which probably
        # looks a bit ugly. If they do have a border, however,
        # they are laid out so as to span the entire width of
        # the parent VGroup. Instead of having a separate label
        # widget, the label is embedded in the border. The
        # _createGroup function takes care of creating the
        # border/label for the child GUI object.
        if (isinstance(vItem, parts.Group) and vItem.border):

            label = None
            childParams['pos']    = (cidx, 0)
            childParams['span']   = (1, 2)
            childParams['border'] = 20
            childParams['flag']   = wx.EXPAND | wx.ALL

        # No labels are being drawn for any child, so all
        # children should span both columns. In this case
        # we could just use a vertical BoxSizer instead of
        # a GridBagSizer,  but I'm going to leave that for
        # the time being.
        elif not group.showLabels:
            childParams['pos']    = (cidx, 0)
            childParams['span']   = (1, 2)
            childParams['border'] = 2
            childParams['flag']   = wx.EXPAND | wx.BOTTOM

        # Otherwise the child is drawn in the standard way -
        # label on the left column, child on the right.
        else:
            childParams['pos']    = (cidx, 1)
            childParams['border'] = 2
            childParams['flag']   = wx.EXPAND | wx.BOTTOM

        if label is not None:
            sizer.Add(labels[cidx],
                      pos=(cidx, 0),
                      flag=wx.ALIGN_CENTER_VERTICAL)

        sizer.Add(child, **childParams)

    sizer.AddGrowableCol(1)

    parent.SetSizer(sizer)


def _createGroup(parent, group, hasProps, propGui):
    """Creates a GUI panel object for the given :class:`.HGroup` or
    :class:`.VGroup`.

    Children of the group are recursively created via calls to
    :func:`_create`, and laid out via the :class:`_layoutHGroup` or
    :class:`_layoutVGroup` functions.
    """

    if group.border:
        borderPanel, panel = _makeGroupBorder(parent, group, wx.Panel)
    else:
        panel = wx.Panel(parent)

    childObjs = []
    labelObjs = []

    for i, child in enumerate(group.children):

        childObj = _create(panel, child, hasProps, propGui)

        # Create a label for the child if necessary
        if group.showLabels and group.childLabels[i] is not None:
            labelObj = _create(panel, group.childLabels[i], hasProps, propGui)
        else:
            labelObj = None

        labelObjs.append(labelObj)
        childObjs.append(childObj)

    if   isinstance(group, parts.HGroup):
        _layoutHGroup(group, panel, childObjs, labelObjs)
    elif isinstance(group, parts.VGroup):
        _layoutVGroup(group, panel, childObjs, labelObjs)

    panel.Layout()
    panel.Fit()

    if group.border:
        borderPanel.Layout()
        borderPanel.Fit()
        return borderPanel
    else:
        return panel


# These aliases are defined so we can introspectively look
# up the appropriate _create* function based upon the class
# name of the ViewItem being created, in the _create
# function below.

_createHGroup = _createGroup
"""Alias for the :func:`_createGroup` function."""


_createVGroup = _createGroup
"""Alias for the :func:`_createGroup` function."""


def _getCreateFunction(viewItemClass):
    """Searches within this module for a function which can parse instances of the
    specified :class:`.ViewItem` class.

    A match will be found if the given class is one of those defined in the
    :mod:`.build_parts` module, or has one of those classes in its base class
    hierarchy. In other words, application-defined subclasses of any of the
    :mod:`.build_parts` classes will still be built.
    """

    cls = viewItemClass

    createFunc = getattr(
        sys.modules[__name__], '_create{}'.format(cls.__name__), None)

    if createFunc is not None:
        return createFunc

    bases = cls .__bases__

    for baseCls in bases:
        createFunc = _getCreateFunction(baseCls)
        if createFunc is not None:
            return createFunc

    return None


def _create(parent, viewItem, hasProps, propGui):
    """Creates a GUI object for the given :class:`.ViewItem` object and, if it
    is a group, all of its children.
    """

    createFunc = _getCreateFunction(viewItem.__class__)

    if createFunc is None:
        raise ValueError('Unrecognised ViewItem: {}'.format(
            viewItem.__class__.__name__))

    guiObject = createFunc(parent, viewItem, hasProps, propGui)

    _configureVisibleWhen(viewItem, guiObject, hasProps, propGui)
    _configureEnabledWhen(viewItem, guiObject, hasProps, propGui)

    if viewItem.tooltip is not None:

        # Add the tooltip to the GUI object, and
        # also do so recursively to any children
        def setToolTip(obj):

            obj.SetToolTip(wx.ToolTip(viewItem.tooltip))

            children = obj.GetChildren()
            for c in children:
                setToolTip(c)

        setToolTip(guiObject)

    if viewItem.setup is not None:
        viewItem.setup(hasProps, parent, guiObject)

    propGui.guiObjects[viewItem.key] = guiObject

    return guiObject


def _defaultView(hasProps):
    """Creates a default view specification for the given :class:`.HasProperties`
    object, with all properties laid out vertically. This function is only
    called if a view specification was not provided in the call to the
    :func:`buildGUI` function
    """

    propNames, propObjs = hasProps.getAllProperties()

    widgets = [parts.Widget(name, label=name) for name in propNames]

    return parts.VGroup(label=hasProps.__class__.__name__, children=widgets)


def _prepareView(hasProps, viewItem, labels, tooltips, showUnlink):
    """Recursively steps through the given ``viewItem`` and its children (if
    any).

    If the ``viewItem`` is a string, it is assumed to be a property name, and
    it is turned into a :class:`.Widget` object. If the ``viewItem`` does not
    have a label/tooltip, and there is a label/tooltip for it in the given
    labels/tooltips dict, then its label/tooltip is set.  Returns a reference
    to the updated/newly created :class:`ViewItem`.
    """

    if isinstance(viewItem, str):
        viewItem = parts.Widget(viewItem)

    if not isinstance(viewItem, parts.ViewItem):
        raise ValueError('Not a ViewItem')

    if viewItem.label   is None:
        viewItem.label   = labels  .get(viewItem.key, viewItem.key)
    if viewItem.tooltip is None:
        viewItem.tooltip = tooltips.get(viewItem.key, None)

    if isinstance(viewItem, parts.Group):

        # children may have been specified as a tuple,
        # so we cast it to a list, making it mutable
        viewItem.children    = list(viewItem.children)
        viewItem.childLabels = []

        for i, child in enumerate(viewItem.children):
            viewItem.children[i] = _prepareView(hasProps,
                                                child,
                                                labels,
                                                tooltips,
                                                showUnlink)

        # Create a Label object for each
        # child of this group if necessary
        for child in viewItem.children:

            # unless no labels are to be shown
            # for the items in this group
            mkLabel = viewItem.showLabels

            # or there is no label specified for this child
            mkLabel = mkLabel and (child.label is not None)

            # or this child is a group with a border
            mkLabel = mkLabel and \
                      not (isinstance(child, parts.Group) and child.border)

            # unless there is no label specified
            if mkLabel: viewItem.childLabels.append(parts.Label(child))
            else:       viewItem.childLabels.append(None)

    # Add link/unlink checkboxes if necessary
    elif (showUnlink                                           and
          isinstance(viewItem, parts.Widget)                   and
          isinstance(hasProps, syncable.SyncableHasProperties) and
          hasProps.getParent() is not None):

        linkBox  = parts.LinkBox(viewItem)
        viewItem = parts.HGroup((linkBox, viewItem),
                                showLabels=False,
                                label=viewItem.label)

    return viewItem


def _finaliseCallbacks(hasProps, propGui):
    """Calls all defined :class:`.ViewItem` ``visibleWhen`` and ``enabledWhen``
    callback functions, in order to set the initial GUI state.

    Also registers a listener on the top level GUI panel to remove all property
    listeners from the ``hasProps`` instance when the panel is destroyed.
    """

    if len(propGui.onChangeCallbacks) == 0:
        return

    # A first call to all of the
    # visibleWhen/enabledWhen
    # functions, so the initial
    # GUI state is valid
    def onShow(ev=None):

        # We only want this function
        # to be called once, so on the
        # first call, deregister the
        # wx event listener
        if ev is not None:
            ev.Skip()
            propGui.topLevel.Unbind(wx.EVT_PAINT)

        for _, n, _, callback in propGui.onChangeCallbacks:
            callback()

    # De-register all property
    # listeners when the
    # top level panel/frame
    # is destroyed
    def onDestroy(ev):
        ev.Skip()

        for targets, propNames, lName, callback in propGui.onChangeCallbacks:
            for target, propName in zip(targets, propNames):

                # target is a weakref - it may
                # have been GC'd, in which case
                # we don't need to remove property
                # listeners from it
                target = target()
                if target is None:
                    continue

                log.debug('Removing listener from {}.{}'.format(
                    type(target).__name__,
                    propName))

                # If propName is none, it's a
                # global property listener
                if propName is None: target.removeGlobalListener(lName)
                else:                target.removeListener(propName, lName)

        propGui.onChangeCallbacks = None
        propGui.topLevel          = None
        propGui.guiObjects        = None

    propGui.topLevel.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)

    # If the top level GUI panel is already
    # visible (seems to happen on GTK), call
    # onShow directly. Otherwise, schedule it
    # to be called on the first paint.
    if propGui.topLevel.IsShownOnScreen():
        onShow()
    else:
        propGui.topLevel.Bind(wx.EVT_PAINT, onShow)


def buildGUI(parent,
             hasProps,
             view=None,
             labels=None,
             tooltips=None,
             showUnlink=False):
    """Builds a GUI interface which allows the properties of the given
    :class:`.HasProperties` object to be edited.

    Returns a reference to the top level GUI object (typically a
    :class:`wx.Frame`, :class:`wx.Panel` or
    :class:`~fsleyes_widgets.notebook.Notebook`).

    Parameters:

    :param parent:     The parent GUI object. If ``None``, the interface is
                       embedded within a :class:`wx.Frame`.

    :param hasProps:   The :class:`.HasProperties` instance.

    :param view:       A :class:`.ViewItem` object, specifying the interface
                       layout.

    :param labels:     A dictionary specifying labels.

    :param tooltips:   A dictionary specifying tooltips.

    :param showUnlink: If the given ``hasProps`` instance is a
                       :class:`.SyncableHasProperties` instance, and it has
                       a parent, a 'link/unlink' checkbox will be shown next
                       to any properties that can be bound/unbound from the
                       parent object.
    """

    if view is None:
        if hasattr(hasProps, '_view'):     view = hasProps._view
        else:                              view = _defaultView(hasProps)
    if labels is None:
        if hasattr(hasProps, '_labels'):   labels = hasProps._labels
        else:                              labels = {}
    if tooltips is None:
        if hasattr(hasProps, '_tooltips'): tooltips = hasProps._tooltips
        else:                              tooltips = {}

    if parent is None: parentObj = wx.Frame(None)
    else:              parentObj = parent

    view = copy.deepcopy(view)

    propGui   = PropGUI()
    view      = _prepareView(hasProps, view, labels, tooltips, showUnlink)

    log.debug('Creating GUI for {} from view: \n{}'.format(
        type(hasProps).__name__, view))

    mainPanel = _create(parentObj, view, hasProps, propGui)

    propGui.topLevel = mainPanel
    _finaliseCallbacks(hasProps, propGui)

    # TODO return the propGui object, so the caller
    # has access to all of the GUI objects that were
    # created, via the propGui.guiObjects dict. ??

    if parent is None:
        parentObj.Layout()
        parentObj.Fit()
        return parentObj
    else:
        return mainPanel


def buildDialog(parent,
                hasProps,
                view=None,
                labels=None,
                tooltips=None,
                showUnlink=False,
                dlgButtons=True):
    """Convenience method which embeds the result of a call to
    :func:`buildGUI` in a :class:`wx.Dialog`.

    See the :func:`buildGUI` documentation for details on the paramters.

    :arg dlgButtons: If ``True``, the dialog will have 'Ok' and 'Cancel'
                     buttons.
    """

    dialog = wx.Dialog(parent, style=wx.DEFAULT_DIALOG_STYLE |
                                     wx.RESIZE_BORDER)
    panel  = buildGUI(dialog, hasProps, view, labels, tooltips, showUnlink)

    sizer = wx.BoxSizer(wx.VERTICAL)
    dialog.SetSizer(sizer)

    sizer.Add(panel, flag=wx.EXPAND, proportion=1)

    if dlgButtons:
        ok     = wx.Button(dialog, wx.ID_OK,     label='Ok')
        cancel = wx.Button(dialog, wx.ID_CANCEL, label='Cancel')

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add((10, 1), flag=wx.EXPAND, proportion=1)
        btnSizer.Add(ok,      flag=wx.EXPAND)
        btnSizer.Add((10, 1), flag=wx.EXPAND)
        btnSizer.Add(cancel,  flag=wx.EXPAND)
        btnSizer.Add((10, 1), flag=wx.EXPAND, proportion=1)

        sizer.Add((1, 10),  flag=wx.EXPAND)
        sizer.Add(btnSizer, flag=wx.EXPAND)
        sizer.Add((1, 10),  flag=wx.EXPAND)

    dialog.Layout()
    dialog.Fit()

    return dialog
