#!/usr/bin/env python
#
# build_parts.py - Parts used by the build module to build a GUI from a
# HasProperties object.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Parts for building a GUI.

This module provides definitiions of the parts used by the :mod:`.build`
module to build a GUI for a :class:`.HasProperties` instance. See the
:mod:`.build` module documentation for some examples.


----------------------------
Conditional visibility/state
----------------------------


The value of the ``ViewItem.dependencies`` parameter determines the required
format of the ``enabledWhen`` and ``visibleWhen`` parameters, and the
behaviour which controls the visible/enabled state of the displayed item.


If ``dependencies`` is ``None``, the visible/enabled state of the item will be
evaluated whenever any property on the target ``HasProperties`` instance
change. The ``enabledWhen`` and ``visibleWhen`` functions will be passed this
instance.


If ``dependencies`` is not ``None``, it must be a list containing the names of
properties on the ``HasProperties`` instance. The visible/enabled state of the
item will then be evaluated whenever the value of these specific properties
change, rather than whenever the value of any property changes. In this case,
the ``enabledWhen`` and ``visibleWhen`` functions will be passed the instance,
and the values of the specified properties as positional arguments.


If the enabled/visible state of the item is dependent on the value of a
property of a different ``HasProperties`` instance, the ``dependencies`` list
can contain a tuple which specifies the dependency as an ``(instance,
propName)`` pair. The ``instance`` may alternately be a function which accepts
the primary ``HasProperties`` instance as a single argument, and returns the
secondary instance (this is useful if you are defining ``ViewItems`` before
any of the ``HasProperties`` instances exist).


This all sounds a bit convoluted, but in practice is pretty simple.  Example::


    import wx
    import fsleyes_props as props

    class MyObj1(props.HasProperties):
        myPropA = props.Boolean()

    class MyObj2(props.HasProperties):
        myProp1 = props.Int()
        myProp2 = props.Real()
        myProp3 = props.Boolean()

        def __init__(self, mo1):
            self.mo1 = mo1

    mo2View = props.VGroup((

        # myProp1 is only visible
        # when MyObj1.myPropA is True
        props.Widget(
            'myProp1',

            # MyObj2 stores a reference to the
            # MyObj1 instance which controls
            # the state of the myProp1 widget.
            dependencies=[(lambda i: i.mo1, 'myPropA')],

            # The visibleWhen callback gets
            # passed the MyObj1 instance,
            # and the value of MyObj2.mo1.myPropA
            visibleWhen=lambda i, mo1val: mo1val),

        # myProp2 is only enabled
        # when MyObj2.myProp3 is True
        props.Widget(
            'myProp2',
            enabledWhen=lambda i: i.myProp3),

        # myProp3 is alway visible/enabled
        'myProp3'))

    mo1 = MyObj1()
    mo2 = MyObj2(mo1)

    app      = wx.App()
    mo1Frame = props.buildGUI(None, mo1)
    mo2Frame = props.buildGUI(None, mo2, view=mo2View)

    mo1Frame.Fit()
    mo2Frame.Fit()
    mo1Frame.Show()
    mo2Frame.Show()
    app.MainLoop()
"""


import copy

import logging


log = logging.getLogger(__name__)


class ViewItem(object):
    """Superclass for :class:`Widget`, :class:`Button`, :class:`Label` and
    :class:`Group`. Represents an item to be displayed.
    """

    def __init__(self,
                 key=None,
                 label=None,
                 tooltip=None,
                 visibleWhen=None,
                 enabledWhen=None,
                 dependencies=None,
                 setup=None,
                 **kwargs):
        """Define a ``ViewItem``.

        :param str key:      An identifier for this item. If this item is a
                             :class:`Widget`, this should be the property
                             name that the widget edits. This key is used to
                             look up labels and tooltips, if they are passed
                             in as dicts (see :func:`.buildGUI`).

        :param str label:    A label for this item, which may be used in the
                             GUI.

        :param str tooltip:  A tooltip, which may be displayed when the user
                             hovers the mouse over the widget for this
                             :class:`ViewItem`.

        :param visibleWhen:  A function which takes at least one argument (see
                             note about the ``dependencies`` parameter above),
                             the ``HasProperties`` instance, and returns a
                             ``bool``. When any property values change, the
                             function is called. The return value is used to
                             determine whether this item should be made
                             visible or invisible.

        :param enabledWhen:  Same as the ``visibleWhen`` parameter, except the
                             state of the item (and its children) is changed
                             between enabled and disabled.

        :param dependencies: List of dependencies which determine when the
                             visible/enabled state of the item are evaluated,
                             and the arguments that are passed to the
                             ``visibleWhen``/``enabledWhen`` functions.

        :param setup:        Optional function which is called when te GUI
                             object represented by this ViewItem is first
                             created. The function is passed the
                             ``HasProperties`` instance, the :mod:`wx` GUI
                             parent object, and the :mod:`wx` object.

        :param kwargs:       Any type-specific options which are to be passed
                             through to the creation function, defined in
                             the :mod:`.widgets` module.
        """

        self.key          = key
        self.label        = label
        self.tooltip      = tooltip
        self.visibleWhen  = visibleWhen
        self.enabledWhen  = enabledWhen
        self.dependencies = dependencies
        self.setup        = setup
        self.kwargs       = kwargs


    def __str__(self):
        return '{}({})'.format(self.__class__.__name__, self.key)


    def __repr__(self):
        return self.__str__()


    def __deepcopy__(self, memo):
        """Creates a deep copy of this ``ViewItem``. Deep copies are made
        of all attributes, except for the ``dependencies`` list, which may
        contain references to objects that cannot be deep-copied.
        """

        new = self.__class__.__new__(self.__class__)

        memo[id(self)] = new

        for k, v in self.__dict__.items():
            if k == 'dependencies': setattr(new, k, copy.copy(    v))
            else:                   setattr(new, k, copy.deepcopy(v, memo))

        return new


class Button(ViewItem):
    """Represents a button which, when clicked, will call a specified callback
    function.

    When the button is clicked, the callback function is passed two arguemnts
    - the :class:`.HasProperties` instance, and the :class:`wx.Button`
    instance.
    """

    def __init__(self,
                 key=None,
                 text=None,
                 callback=None,
                 icon=None,
                 **kwargs):
        """
        If the ``icon`` argument is provided, it is used instead of any
        specified ``text``. The ``icon`` should be a string containing the
        name of the image file.

        :arg key:      Passed to :meth:`ViewItem.__init__`.
        :arg text:     Text to show on the button (if ``icons`` are not used).
        :arg callback: Function to call when the button is clicked.
        :arg icon:     The name of an icon image to show on the button.

        All other arguments are passed through to :meth:`ViewItem.__init__`.
        """
        self.callback = callback
        self.icon     = icon
        self.text     = text
        ViewItem.__init__(self, key, **kwargs)

    def __str__( self):
        return '{}({})'.format(self.__class__.__name__, self.text)
    def __repr__(self):
        return self.__str__()


class Toggle(ViewItem):
    """Represents a *toggle* widget of some sort (e.g. a check box, or a
    toggle button) which, when clicked, calls a specified callback function.
    """
    def __init__(self,
                 key=None,
                 callback=None,
                 icon=None,
                 **kwargs):
        """Create a ``Toggle``.

        :arg key:      Passed to :meth:`ViewItem.__init__`.
        :arg callback: Function to call when the toggle widget is clicked.
                       Must accept two arguments - the :class:`.HasProperties`
                       instance, and the toggle widget.
        :arg icon:     The name of an image file, or a list of two image
                       file names.

        All other arguments are passed through to :meth:`ViewItem.__init__`.
        """

        self.callback = callback
        self.icon     = icon
        ViewItem.__init__(self, key, **kwargs)


    def __str__( self):
        return '{}()'.format(self.__class__.__name__)
    def __repr__(self):
        return self.__str__()


class Label(ViewItem):
    """Represents a static text label."""


    def __init__(self, viewItem=None, **kwargs):
        """Define a label.

        :class:`Label` objects are automatically created for other
        :class:`ViewItem` objects, which are to be labelled.
        """

        if viewItem is not None:
            kwargs['key']          = '{}_label'.format(viewItem.key)
            kwargs['label']        = viewItem.label
            kwargs['tooltip']      = viewItem.tooltip
            kwargs['visibleWhen']  = viewItem.visibleWhen
            kwargs['enabledWhen']  = viewItem.enabledWhen
            kwargs['dependencies'] = viewItem.dependencies

        ViewItem.__init__(self, **kwargs)

    def __str__( self):
        return '{}({})'.format(self.__class__.__name__, self.label)
    def __repr__(self):
        return self.__str__()


class LinkBox(ViewItem):
    """Represents a checkbox which allows the user to control whether a
    property is linked (a.k.a. bound) to the parent of the
    :class:`HasProperties` object.
    """

    def __init__(self, viewItem=None, **kwargs):

        if viewItem is not None:
            self.propKey          = viewItem.key
            kwargs['key']         = '{}_linkBox'.format(viewItem.key)
            kwargs['label']       = viewItem.label
            kwargs['tooltip']     = viewItem.tooltip
            kwargs['visibleWhen'] = viewItem.visibleWhen
            kwargs['enabledWhen'] = viewItem.enabledWhen

        ViewItem.__init__(self, **kwargs)


class Widget(ViewItem):
    """Represents a widget which is used to modify a property value. """


    def __init__(self, propName, index=None, **kwargs):
        """Define a :class:`Widget`.

        :param str propName: The name of the property which this widget can
                             modify.

        :param int index:    If provided, it is assumed that the property
                             is a :class:`.List`, and the index specifies
                             the list item that this widget will be bound
                             to.

        :param kwargs:       Passed to the :class:`ViewItem` constructor.
        """

        kwargs['key'] = propName
        self.index    = index
        ViewItem.__init__(self, **kwargs)


class Group(ViewItem):
    """Represents a collection of other :class:`ViewItem` objects.

    This class is not to be used directly - use one of the subclasses:
      - :class:`VGroup`
      - :class:`HGroup`
      - :class:`NotebookGroup`
    """


    def __init__(self, children, showLabels=True, border=False, **kwargs):
        """Define a :class:`Group`.

        Parameters:

        :param children:        List of :class:`ViewItem` objects, the
                                children of this :class:`Group`.

        :param bool showLabels: Whether labels should be displayed for each of
                                the children. If this is ``True``, an attribute
                                will be added to this :class:`Group` object in
                                the :func:`_prepareView` function, called
                                ``childLabels``, which contains a
                                :class:`Label` object for each child.

        :param bool border:     If ``True``, this group will be drawn with a
                                border around it. If this group is a child of
                                another :class:`VGroup`, it will be laid out
                                a bit differently, too.

        :param kwargs:          Passed to the :class:`ViewItem` constructor.
        """
        ViewItem.__init__(self, **kwargs)
        self.children   = children
        self.border     = border
        self.showLabels = showLabels

    def __str__(self):

        def doStr(viewItem, depth):

            if isinstance(viewItem, Group):

                s = '{}{}\n'.format(' ' * depth, ViewItem.__str__(viewItem))
                for child in viewItem.children:
                    s = s + doStr(child, depth + 1)
            else:
                s = '{}{}\n'.format(' ' * depth, str(viewItem))
            return s

        return doStr(self, 0)


class NotebookGroup(Group):
    """A :class:`Group` representing a GUI Notebook. Children are added as
    notebook pages.
    """
    def __init__(self, children, **kwargs):
        """Define a :class:`NotebookGroup`.

        :param children: List of :class:`ViewItem` objects - a tab in the
                         notebook is added for each child.
        """
        Group.__init__(self, children, **kwargs)


class HGroup(Group):
    """A group representing a GUI panel, whose children are laid out
    horizontally.
    """

    def __init__(self, children, wrap=False, vertLabels=False, **kwargs):
        """Create a :class:`HGroup`.

        :arg wrap:       If ``True`` the children are wrapped, via a
                         :class:`wx.WrapSizer`; if there is not enough
                         horizontal space to display all children in a
                         single row, the remaining children are
                         displayed on a new row.

        :arg vertLabels: If ``True`` child labels are displayed above
                         the child.
        """
        self.wrap       = wrap
        self.vertLabels = vertLabels
        Group.__init__(self, children, **kwargs)


class VGroup(Group):
    """A group representing a GUI panel, whose children are laid out
    vertically.
    """
    def __init__(self, children, **kwargs):
        kwargs['border'] = kwargs.get('border', True)
        Group.__init__(self, children, **kwargs)
