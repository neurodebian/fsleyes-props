#!/usr/bin/env python
#
# widgets.py - Generate wx GUI widgets for PropertyBase objects.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides functions to generate Generate :mod:`wx` GUI widgets
which allow the user to edit the properties of a :class:`.HasProperties`
instance.

Most of the functions in this module are not intended to be called directly -
they are used by the :mod:`.build` module. However, a few functions defined
here are made available at the :mod:`fsleyes_props` namespace level, and are
intended to be called by application code:


 .. autosummary::
    :nosignatures:

    makeWidget
    makeListWidget
    makeListWidgets
    makeSyncWidget
    bindWidget
    unbindWidget


The other functions defined in this module are used by the :mod:`.build`
module, which generates a GUI from a view specification. The following
functions are available:


 .. autosummary::
    :nosignatures:

    _FilePath
    _String
    _Real
    _Int
    _Percentage
    _Colour
    _ColourMap
    _LinkBox


Widgets for some other property types are implemented in separate modules,
purely to keep module file sizes down:


 .. autosummary::
    :nosignatures:

    ~fsleyes_props.widgets_list._List
    ~fsleyes_props.widgets_bounds._Bounds
    ~fsleyes_props.widgets_point._Point
    ~fsleyes_props.widgets_choice._Choice
    ~fsleyes_props.widgets_boolean._Boolean
    ~fsleyes_props.widgets_number._Number


 .. warning:: The :mod:`.widgets_list` module has not been looked at
              in a while, and is probably broken.


While all of these functions have a standardised signature, some of them
(e.g. the ``_Colour`` function) accept extra arguments which provide some
level of customisation. You can provide these arguments indirectly in the
:class:`.ViewItem` specification for a specific property. For example::


    import fsleyes_props as props

    class MyObj(props.HasProperties):
        myColour     = props.Colour()
        myBoolean    = props.Boolean()

    view = props.VGroup((

        # Give the colour button a size of 32 * 32
        props.Widget('myColour',  size=(32, 32)),

        # Use a toggle button for the boolean property,
        # using 'boolean.png' as the button icon
        props.Widget('myBoolean', icon='boolean.png') ))

    myobj = MyObj()

    dlg = props.buildDialog(None, myobj, view=view)

    dlg.ShowModal()

"""

import logging

import sys

import os
import os.path as op

from collections import Iterable

import six

import wx

try:                from wx.combo import BitmapComboBox
except ImportError: from wx.adv   import BitmapComboBox

import fsleyes_widgets.colourbutton as colourbtn


log = logging.getLogger(__name__)


def _propBind(hasProps,
              propObj,
              propVal,
              guiObj,
              evType,
              widgetGet=None,
              widgetSet=None,
              widgetDestroy=None):
    """Binds a :class:`.PropertyValue` instance to a widget.

    Sets up event callback functions such that, on a change to the given
    property value, the value displayed by the given GUI widget will be
    updated. Similarly, whenever a GUI event of the specified type (or types -
    you may pass in a list of event types) occurs, the property value will be
    set to the value controlled by the GUI widget.

    :param hasProps:      The owning :class:`.HasProperties` instance.

    :param propObj:       The :class:`.PropertyBase` property type.

    :param propVal:       The :class:`.PropertyValue` to be bound.

    :param guiObj:        The :mod:`wx` GUI widget

    :param evType:        The event type (or list of event types) which should
                          be listened for on the ``guiObj``.

    :param widgetGet:     Function which returns the current widget value. If
                          ``None``, the ``guiObj.GetValue`` method is used.

    :param widgetSet:     Function which sets the current widget value. If
                          ``None``, the ``guiObj.SetValue`` method is used.

    :param widgetDestroy: Function which is called if/when the widget is
                          destroyed. Must accept one argument - the
                          :class:`wx.Event` object.
    """

    if not isinstance(evType, Iterable): evType = [evType]

    listenerName    = 'WidgetBind_{}'   .format(id(guiObj))
    listenerAttName = 'WidgetBindAtt_{}'.format(id(guiObj))

    if widgetGet is None:
        widgetGet = guiObj.GetValue
    if widgetSet is None:

        handleNone = True
        widgetSet  = guiObj.SetValue
    else:
        handleNone = False

    log.debug('Binding PropertyValue ({}.{} [{}]) to widget {} ({})'.format(
        hasProps.__class__.__name__,
        propVal._name,
        id(propVal),
        guiObj.__class__.__name__, id(guiObj)))

    def _guiUpdate(*a):
        """
        Called whenever the property value is changed.
        Sets the GUI widget value to that of the property.
        """
        value = propVal.get()

        if widgetGet() == value: return

        # most wx widgets complain if you try to set their value to None
        if handleNone and (value is None): value = ''

        log.debug('Updating Widget {} ({}) from {}.{} ({}): {}'.format(
            guiObj.__class__.__name__,
            id(guiObj),
            hasProps.__class__.__name__,
            propVal._name,
            id(hasProps),
            value))

        widgetSet(value)

    def _propUpdate(*a):
        """
        Called when the value controlled by the GUI widget
        is changed. Updates the property value.
        """

        value = widgetGet()

        if propVal.get() == value: return

        log.debug('Updating {}.{} ({}) from widget  {} ({}): {}'.format(
            hasProps.__class__.__name__,
            propVal._name,
            id(hasProps),
            guiObj.__class__.__name__,
            id(guiObj),
            value))

        propVal.disableListener(listenerName)
        propVal.set(value)

        # Re-enable the property listener
        # bound to this widget only if the
        # widget has not been destroyed.
        #
        # This is to prevent a (somewhat
        # harmless) scenario whereby setting
        # the property value results in the
        # deletion of the widget to which it
        # is bound.
        if guiObj:
            propVal.enableListener(listenerName)


    def _attUpdate(ctx, att, *a):
        val = propVal.getAttribute(att)
        if att == 'enabled':
            guiObj.Enable(val)

    _guiUpdate(propVal.get())
    _attUpdate(hasProps, 'enabled')

    # set up the callback functions
    for ev in evType: guiObj.Bind(ev, _propUpdate)
    propVal.addListener(         listenerName,    _guiUpdate, weak=False)
    propVal.addAttributeListener(listenerAttName, _attUpdate, weak=False)

    def onDestroy(ev):
        ev.Skip()

        if ev.GetEventObject() is not guiObj:
            return

        log.debug('Widget {} ({}) destroyed (removing '
                  'listener {} from {}.{})'.format(
                      guiObj.__class__.__name__,
                      id(guiObj),
                      listenerName,
                      hasProps.__class__.__name__,
                      propVal._name))
        propVal.removeListener(         listenerName)
        propVal.removeAttributeListener(listenerAttName)

        if widgetDestroy is not None:
            widgetDestroy(ev)

    guiObj.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)


def _propUnbind(hasProps, propObj, propVal, guiObj, evType):
    """Removes any event binding which has been previously configured via the
    :func:`_propBind` function, between the given :class:`.PropertyValue`
    instance, and the given :mod:`wx` widget.
    """
    if not isinstance(evType, Iterable): evType = [evType]

    listenerName    = 'WidgetBind_{}'   .format(id(guiObj))
    listenerAttName = 'WidgetBindAtt_{}'.format(id(guiObj))

    propVal.removeListener(         listenerName)
    propVal.removeAttributeListener(listenerAttName)

    for ev in evType: guiObj.Unbind(ev)


def _setupValidation(widget, hasProps, propObj, propVal):
    """Configures input validation for the given widget, which is assumed to be
    bound to the given ``propVal`` (a :class:`.PropertyValue` object).

    Any changes to the property value are validated and, if the new value is
    invalid, the widget background colour is changed to a light red, so that
    the user is aware of the invalid-ness.

    This function is only used for a few different property types, namely
      - :class:`.String`
      - :class:`.FilePath`
      - :class:`.Number`

    :param widget:   The :mod:`wx` GUI widget.

    :param hasProps: The owning :class:`.HasProperties` instance.

    :param propObj:  The :class:`.PropertyBase` property type.

    :param propVal:  The :class:`.PropertyValue` instance.
    """

    invalidBGColour = '#ff9999'
    validBGColour   = widget.GetBackgroundColour()

    def _changeBGOnValidate(value, valid, *a):
        """
        Called whenever the property value changes. Checks
        to see if the new value is valid and changes the
        widget background colour according to the validity
        of the new value.
        """

        if valid: newBGColour = validBGColour
        else:     newBGColour = invalidBGColour

        widget.SetBackgroundColour(newBGColour)
        widget.Refresh()

    # We add a callback listener to the PropertyValue object,
    # rather than to the PropertyBase, as one property may be
    # associated with multiple variables, and we don't want
    # the widgets associated with those other variables to
    # change background.
    lName = 'widgets_py_ChangeBG_{}'.format(id(widget))
    propVal.addListener(lName, _changeBGOnValidate, weak=False)

    # And ensure that the listener is
    # removed when the widget is destroyed
    def onDestroy(ev):
        propVal.removeListener(lName)
        ev.Skip()

    widget.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)

    # Validate the initial property value,
    # so the background is appropriately set
    _changeBGOnValidate(None, propVal.isValid(), None)


def _String(parent, hasProps, propObj, propVal, **kwargs):
    """Creates and returns a :class:`wx.TextCtrl` object, allowing the user to
    edit the given ``propVal`` (managed by a :class:`.String` instance).

    :param parent:   The :mod:`wx` parent object.

    :param hasProps: The owning :class:`.HasProperties` instance.

    :param propObj:  The :class:`.PropertyBase` instance (assumed to be a
                     :class:`.String`).

    :param propVal:  The :class:`.PropertyValue` instance.

    :param kwargs:   Type-specific options.
    """

    widget = wx.TextCtrl(parent)

    # Under linux/GTK, TextCtrl widgets
    # absorb mouse wheel events,  so I'm
    # adding a custom handler to prevent this.
    if wx.Platform == '__WXGTK__':
        def wheel(ev):
            widget.GetParent().GetEventHandler().ProcessEvent(ev)
        widget.Bind(wx.EVT_MOUSEWHEEL, wheel)

    # Use a DC object to calculate a decent
    # minimum size for the widget
    dc       = wx.ClientDC(widget)
    textSize = dc.GetTextExtent('w' * 17)
    widgSize = widget.GetBestSize().Get()

    widget.SetMinSize((max(textSize[0], widgSize[0]),
                       max(textSize[1], widgSize[1])))

    _propBind(hasProps, propObj, propVal, widget, wx.EVT_TEXT)
    _setupValidation(widget, hasProps, propObj, propVal)

    return widget


def _FilePath(parent, hasProps, propObj, propVal, **kwargs):
    """Creates and returns a panel containing a :class:`wx.TextCtrl` and a
    :class:`wx.Button`.

    The button, when clicked, opens a file dialog allowing the user to choose
    a file/directory to open, or a location to save (this depends upon how the
    ``propObj`` [a :class:`.FilePath` instance] object was configured).

    See the :func:`_String` documentation for details on the parameters.
    """

    # The _lastFilePathDir variable is used to
    # retain the most recently visited directory
    # in file dialogs. New file dialogs are
    # initialised to display this directory.

    # This is currently a global setting, but it
    # may be more appropriate to make it a per-widget
    # setting.  Easily done, just make this a dict,
    # with the widget (or property name) as the key.
    lastFilePathDir = getattr(_FilePath, 'lastFilePathDir', os.getcwd())

    value = propVal.get()
    if value is None: value = ''

    panel   = wx.Panel(parent)
    textbox = wx.TextCtrl(panel)
    button  = wx.Button(panel, label='Choose')

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    sizer.Add(textbox, flag=wx.EXPAND, proportion=1)
    sizer.Add(button,  flag=wx.EXPAND)

    panel.SetSizer(sizer)
    panel.SetAutoLayout(1)
    sizer.Fit(panel)

    exists = propObj.getAttribute(hasProps, 'exists')
    isFile = propObj.getAttribute(hasProps, 'isFile')

    def _choosePath(ev):
        global _lastFilePathDir

        if exists and isFile:
            dlg = wx.FileDialog(parent,
                                message='Choose file',
                                defaultDir=lastFilePathDir,
                                defaultFile=value,
                                style=wx.FD_OPEN)

        elif exists and (not isFile):
            dlg = wx.DirDialog(parent,
                               message='Choose directory',
                               defaultPath=lastFilePathDir)

        else:
            dlg = wx.FileDialog(parent,
                                message='Save file',
                                defaultDir=lastFilePathDir,
                                defaultFile=value,
                                style=wx.FD_SAVE)


        dlg.ShowModal()
        path = dlg.GetPath()

        if path != '' and path is not None:
            _FilePath.lastFilePathDir = op.dirname(path)
            propVal.set(path)

    _setupValidation(textbox, hasProps, propObj, propVal)
    _propBind(hasProps, propObj, propVal, textbox, wx.EVT_TEXT)

    button.Bind(wx.EVT_BUTTON, _choosePath)

    return panel


def _Real(parent, hasProps, propObj, propVal, **kwargs):
    """Creates and returns a widget allowing the user to edit the given
    :class:`.Real` property value. See the :func:`.widgets_number._Number`
    function for more details.

    See the :func:`_String` documentation for details on the parameters.
    """
    from fsleyes_props.widgets_number import _Number
    return _Number(parent, hasProps, propObj, propVal, **kwargs)


def _Int(parent, hasProps, propObj, propVal, **kwargs):
    """Creates and returns a widget allowing the user to edit the given
    :class:`.Int` property value. See the :func:`.widgets_number._Number`
    function for more details.

    See the :func:`_String` documentation for details on the parameters.
    """
    from fsleyes_props.widgets_number import _Number
    return _Number(parent, hasProps, propObj, propVal, **kwargs)


def _Percentage(parent, hasProps, propObj, propVal, **kwargs):
    """Creates and returns a widget allowing the user to edit the given
    :class:`.Percentage` property value. See the
    :func:`.widgets_number._Number` function for more details.

    See the :func:`_String` documentation for details on the parameters.
    """
    # TODO Add '%' signs to Scale labels.
    from fsleyes_props.widgets_number import _Number
    return _Number(parent, hasProps, propObj, propVal, **kwargs)


def _Colour(parent, hasProps, propObj, propVal, size=(16, 16), **kwargs):
    """Creates and returns a :class:`.ColourButton` widget, allowing
    the user to modify the given :class:`.Colour` property value.

    :arg size: Desired size, in pixels, of the ``ColourButton``.
    """

    colourButton = colourbtn.ColourButton(parent, size=size)

    def widgetGet():

        vals = colourButton.GetValue()
        return [v / 255.0 for v in vals]

    def widgetSet(vals):
        colour = [int(v * 255.0) for v in vals]
        colourButton.SetValue(colour)

    _propBind(hasProps,
              propObj,
              propVal,
              colourButton,
              colourbtn.EVT_COLOUR_BUTTON_EVENT,
              widgetGet,
              widgetSet)

    return colourButton


def _makeColourMapBitmap(cmap):
    """Used by the :func:`_ColourMap` function.

    Makes a little bitmap image from a :class:`~matplotlib.colors.Colormap`
    instance.
    """

    import numpy as np

    width, height = 75, 15

    # create a single colour  for each horizontal pixel
    colours = cmap(np.linspace(0.0, 1.0, width))

    # discard alpha values
    colours = colours[:, :3]

    # repeat each horizontal pixel (height) times
    colours = np.tile(colours, (height, 1, 1))

    # scale to [0,255] and cast to uint8
    colours = colours * 255
    colours = np.array(colours, dtype=np.uint8)

    # make a wx Bitmap from the colour data
    colours = colours.ravel(order='C')

    if six.PY2: bitmap = wx.BitmapFromBuffer( width, height, colours)
    else:       bitmap = wx.Bitmap.FromBuffer(width, height, colours)
    return bitmap


def _ColourMap(parent, hasProps, propObj, propVal, labels=None, **kwargs):
    """Creates and returns a combobox, allowing the user to change the value
    of the given :class:`.ColourMap` property value.

    :arg labels: A dictionary containing ``{name : label}`` mappings,
                 defining a display name/label for each colour map. If
                 not provided, the colour map ``name`` attribute is used
                 as the display name.

                 Can alternately be a function which accepts a colour map
                 identifier name, and returns its display name.

    See also the :func:`_makeColourMapBitmap` function.
    """

    import matplotlib.cm as mplcm

    # These are used by the inner-functions defined
    # below, and are dynamically updated when the
    # list of available colour maps change. I'm
    # storing each of them in a list, so the inner
    # functions will have access to updated versions.
    cmapKeys = [list(propObj.getColourMaps(hasProps))]
    cmapObjs = [list(map(mplcm.get_cmap, cmapKeys[0]))]

    # create the combobox
    cbox = BitmapComboBox(parent, style=wx.CB_READONLY | wx.CB_DROPDOWN)

    # OwnerDrawnComboBoxes seem to absorb mouse
    # events and, under OSX/cocoa at least, this
    # causes the currently selected item to
    # change. I don't want this.
    def wheel(ev):
        parent.GetEventHandler().ProcessEvent(ev)
    cbox.Bind(wx.EVT_MOUSEWHEEL, wheel)

    def widgetGet():
        sel = cbox.GetSelection()
        if sel == -1:
            sel = 0
        return cmapObjs[0][sel]

    def widgetSet(value):
        if value is not None:
            cbox.SetSelection(cmapObjs[0].index(value))
        else:
            cbox.SetSelection(0)

    # Called when the list of available
    # colour maps changes - updates the
    # options displayed in the combobox
    def cmapsChanged(*a):

        selected    = cbox.GetSelection()
        cmapKeys[0] = list(propObj.getColourMaps(hasProps))
        cmapObjs[0] = list(map(mplcm.get_cmap, cmapKeys[0]))

        cbox.Clear()

        # Store the width of the biggest bitmap,
        # and the width of the biggest label.
        # the BitmapComboBox doesn't size itself
        # properly on all platforms, so we'll
        # do it manually, dammit
        maxBmpWidth = 0
        maxLblWidth = 0
        dc          = wx.ClientDC(cbox)

        # Make a little bitmap for every colour
        # map, and add it to the combobox
        for cmap in cmapObjs[0]:

            # Labels can either be None
            if labels is None:
                name = cmap.name

            # Or a function
            elif hasattr(labels, '__call__'):
                name = labels(cmap.name)

            # Or a dictionary
            else:
                name = labels.get(cmap.name, cmap.name)

            bitmap = _makeColourMapBitmap(cmap)
            cbox.Append(name, bitmap)

            # use the DC to get the label size
            lblWidth = dc.GetTextExtent(name)[0]
            bmpWidth = bitmap.GetWidth()

            if bmpWidth > maxBmpWidth: maxBmpWidth = bmpWidth
            if lblWidth > maxLblWidth: maxLblWidth = lblWidth

        # Explicitly set the minimum size from
        # the maximum bitmap/label sizes, with
        # some extra to account for the drop
        # down button
        cbox.InvalidateBestSize()
        bestHeight = cbox.GetBestSize().GetHeight()
        cbox.SetMinSize((maxBmpWidth + maxLblWidth + 40, bestHeight))

        cbox.SetSelection(selected)
        cbox.Refresh()

    # Initialise the combobox options
    cmapsChanged()

    # Make sure the combobox options are updated
    # when the property options change
    lName = 'ColourMap_ComboBox_{}'.format(id(cbox))
    propVal.addAttributeListener(lName, cmapsChanged, weak=False)

    def onDestroy(ev):
        propVal.removeAttributeListener(lName)

    # Bind the combobox to the property
    _propBind(hasProps,
              propObj,
              propVal,
              cbox,
              evType=wx.EVT_COMBOBOX,
              widgetGet=widgetGet,
              widgetSet=widgetSet,
              widgetDestroy=onDestroy)

    # Set the initial combobox selection
    currentVal = propVal.get()
    if currentVal is None: currentVal = 0
    else:                  currentVal = cmapObjs[0].index(currentVal)

    cbox.SetSelection(currentVal)

    return cbox


def _LinkBox(parent, hasProps, propObj, propVal, **kwargs):
    """Creates a 'link' button which toggles synchronisation
    between the property on the given ``hasProps`` instance,
    and its parent.
    """
    propName = propObj.getLabel(hasProps)
    value    = hasProps.isSyncedToParent(propName)
    linkBox  = wx.ToggleButton(parent,
                               label=six.u('\u21cb'),
                               style=wx.BU_EXACTFIT)
    linkBox.SetValue(value)

    if (hasProps.getParent() is None)                   or \
       (not hasProps.canBeSyncedToParent(    propName)) or \
       (not hasProps.canBeUnsyncedFromParent(propName)):
        linkBox.Enable(False)

    else:

        # Update the binding state when the linkbox is modified
        def onLinkBox(ev):
            value = linkBox.GetValue()
            if value: hasProps.syncToParent(    propName)
            else:     hasProps.unsyncFromParent(propName)

        # And update the linkbox when the binding state is modified
        def onSyncProp(*a):
            linkBox.SetValue(hasProps.isSyncedToParent(propName))

        def onDestroy(ev):
            ev.Skip()
            hasProps.removeSyncChangeListener(propName, lName)

        lName = 'widget_LinkBox_{}_{}'.format(propName, linkBox)

        linkBox.Bind(wx.EVT_TOGGLEBUTTON,   onLinkBox)
        linkBox.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)
        hasProps.addSyncChangeListener(propName, lName, onSyncProp, weak=False)

    return linkBox


def makeSyncWidget(parent, hasProps, propName, **kwargs):
    """Creates a button which controls synchronisation of the specified
    property on the given ``hasProps`` instance, with the corresponding
    property on its parent.

    See the :func:`makeWidget` function for a description of the
    arguments.
    """
    propObj = hasProps.getProp(propName)
    propVal = propObj.getPropVal(hasProps)

    return _LinkBox(parent, hasProps, propObj, propVal, **kwargs)


def makeWidget(parent, hasProps, propName, **kwargs):
    """Given ``hasProps`` (a :class:`.HasProperties` instance), ``propName``
    (the name of a property of ``hasProps``), and ``parent``, a GUI object,
    creates and returns a widget, or a panel containing widgets, which may
    be used to edit the property value.

    :param parent:       A :mod:`wx` object to be used as the parent for the
                         generated widget(s).

    :param hasProps:     A :class:`.HasProperties` instance.

    :param str propName: Name of the :class:`.PropertyBase` property to
                         generate a widget for.

    :param kwargs:       Type specific arguments.
    """

    propObj = hasProps.getProp(propName)
    propVal = propObj.getPropVal(hasProps)

    if propObj is None:
        raise ValueError('Could not find property {}.{}'.format(
            hasProps.__class__.__name__, propName))

    makeFunc = getattr(
        sys.modules[__name__],
        '_{}'.format(propObj.__class__.__name__), None)

    if makeFunc is None:
        raise ValueError(
            'Unknown property type: {}'.format(propObj.__class__.__name__))

    return makeFunc(parent, hasProps, propObj, propVal, **kwargs)


def makeListWidget(parent, hasProps, propName, index, **kwargs):
    """Creeates a widget for a specific value in the specified list property.
    """
    propObj     = hasProps.getProp(propName)._listType
    propValList = getattr(hasProps, propName).getPropertyValueList()
    propVal     = propValList[index]

    makeFunc = getattr(
        sys.modules[__name__],
        '_{}'.format(propObj.__class__.__name__), None)

    if makeFunc is None:
        raise ValueError(
            'Unknown property type: {}'.format(propObj.__class__.__name__))

    return makeFunc(parent, hasProps, propObj, propVal, **kwargs)


def makeListWidgets(parent, hasProps, propName, **kwargs):
    """Creates a widget for every value in the given list property.
    """

    propObj     = hasProps.getProp(propName)._listType
    propValList = getattr(hasProps, propName).getPropertyValueList()

    makeFunc = getattr(
        sys.modules[__name__],
        '_{}'.format(propObj.__class__.__name__), None)

    if makeFunc is None:
        raise ValueError(
            'Unknown property type: {}'.format(propObj.__class__.__name__))

    widgets = []

    for propVal in propValList:
        widgets.append(makeFunc(parent, hasProps, propObj, propVal, **kwargs))

    return widgets


def bindWidget(widget,
               hasProps,
               propName,
               evTypes,
               widgetGet=None,
               widgetSet=None):
    """Binds the given widget to the specified property. See the
    :func:`_propBind` method for details of the arguments.
    """

    propObj = hasProps.getProp(   propName)
    propVal = hasProps.getPropVal(propName)

    _propBind(
        hasProps, propObj, propVal, widget, evTypes, widgetGet, widgetSet)


def bindListWidgets(widgets,
                    hasProps,
                    propName,
                    evTypes,
                    widgetSets=None,
                    widgetGets=None):
    """Binds the given sequence of widgets to each of the values in the
    specified list property.
    """

    if widgetSets is None: widgetSets = [None] * len(widgets)
    if widgetGets is None: widgetGets = [None] * len(widgets)

    propObj     = hasProps.getProp( propName)
    propValList = getattr(hasProps, propName).getPropertyValueList()

    for propVal, widget, wGet, wSet in zip(
            propValList, widgets, widgetGets, widgetSets):

        _propBind(hasProps,
                  propObj,
                  propVal,
                  widget,
                  evTypes,
                  wGet,
                  wSet)


def unbindWidget(widget, hasProps, propName, evTypes):
    """Unbinds the given widget from the specified property, assumed to have
    been previously bound via the :func:`bindWidget` function.
    """

    propObj = hasProps.getProp(   propName)
    propVal = hasProps.getPropVal(propName)

    _propUnbind(hasProps, propObj, propVal, widget, evTypes)
