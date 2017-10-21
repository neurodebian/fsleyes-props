#!/usr/bin/env python
#
# widgets_boolean.py - Generate a widget to control a Boolean property.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides the :func:`_Boolean` function, which is imported into
the :mod:`widgets` module namespace. It is separated purely to keep the
``widgets`` module file size down.
"""


import wx

import six

from . import                          widgets
import fsleyes_widgets.bitmapradio  as bmpradio
import fsleyes_widgets.bitmaptoggle as bmptoggle


def _Boolean(parent,
             hasProps,
             propObj,
             propVal,
             icon=None,
             toggle=True,
             style=None,
             **kwargs):
    """Creates and returns a ``wx.CheckBox``, allowing the user to set the
    given :class:`.Boolean` property value.

    :arg icon:   If the ``icon`` argument is provided, it should be a string
                 containing the name of an image file, or a list of two image
                 file names.  In this case, case, a
                 `:class:`.BitmapToggleButton` is used instead of a
                 ``CheckBox``.

                 .. note:: If ``toggle`` is ``False``, ``icons`` may
                           alternately be a sequence of four icons, with the
                           order ``[selectedTrueIcon, unselectedTrueIcon,
                           selectedFalseIcon, unselectedFalseIcon]``.

    :arg toggle: If two icon images are provided, and the ``toggle`` argument
                 is ``True`` (the default), a :class:`.BitmapToggleButton` is
                 used. If ``toggle=False``, a :class:`.BitmapRadioBox` is used
                 instead.  In the latter case, the ``style`` argument is
                 passed through to the :meth:`.BitmapRadioBox.__init__`
                 method.

    :arg style:  If ``toggle`` is ``False``, this value is passed through to
                 the :meth:`BitmapRadioBox.__init__` method.

    See the :func:`.widgets._String` documentation for details on the other
    parameters.
    """

    if icon is None:
        widget, event, wget, wset = _booleanCheckBox(parent)

    else:

        if isinstance(icon, six.string_types):
            icon = [icon]

        for i in range(len(icon)):
            icon[i] = wx.Bitmap(icon[i], wx.BITMAP_TYPE_PNG)

        if toggle:
            widget, event, wget, wset = _booleanToggle(parent, icon)
        else:
            widget, event, wget, wset = _booleanRadio( parent, icon, style)

    widgets._propBind(hasProps,
                      propObj,
                      propVal,
                      widget,
                      event,
                      widgetGet=wget,
                      widgetSet=wset)
    return widget


def _booleanCheckBox(parent):
    """Create a ``wx.CheckBox`` to link to the :class:`.Boolean` property. """
    widget = wx.CheckBox(parent)
    event  = wx.EVT_CHECKBOX

    return widget, event, None, None


def _booleanToggle(parent, icons):
    """Create a :class:`.BitmapToggleButton` to link to the :class:`.Boolean`
    property.
    """
    if len(icons) == 1:
        icons = icons + [None]

    trueBmp  = icons[0]
    falseBmp = icons[1]

    style  = wx.BU_EXACTFIT | wx.ALIGN_CENTRE | wx.BU_NOTEXT
    widget = bmptoggle.BitmapToggleButton(
        parent,
        trueBmp=trueBmp,
        falseBmp=falseBmp,
        style=style)
    event  = bmptoggle.EVT_BITMAP_TOGGLE

    return widget, event, None, None


def _booleanRadio(parent, icons, style):
    """Create a :class:`.BitmapRadioBox` to link to the :class:`.Boolean`
    property.
    """

    widget = bmpradio.BitmapRadioBox(parent, style)
    event  = bmpradio.EVT_BITMAP_RADIO_EVENT

    if len(icons) == 2:
        icons = [icons[0], None, icons[1], None]

    widget.AddChoice(icons[0], unselectedBmp=icons[1])
    widget.AddChoice(icons[2], unselectedBmp=icons[3])

    def wget():
        return widget.GetSelection() == 0

    def wset(val):
        if val: widget.SetSelection(0)
        else:   widget.SetSelection(1)

    return widget, event, wget, wset
