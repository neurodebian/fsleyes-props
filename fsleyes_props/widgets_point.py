#!/usr/bin/env python
#
# widgets_point.py - Create widgets for modifying Point properties.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides the :func:`_Point` function, which is imported into
the :mod:`widgets` module namespace. It is separated purely to keep the
``widgets`` module file size down.
"""


import wx

import fsleyes_widgets.floatslider as floatslider
from . import                         widgets


def _Point(parent,
           hasProps,
           propObj,
           propVal,
           labels=None,
           showLimits=True,
           editLimits=False,
           mousewheel=False):
    """Creates and returns a :class:`.SliderSpinPanel` allowing the user to
    edit the low/high values along each dimension of the given
    :class:`.Point` property value.

    :arg labels:     One label for each dimension, to be shown alongside the
                     corresponding controls.

    :arg showLimits: Show labels displaying the point limits.

    :arg editLimits: Show buttons allowing the user to edit the point limits.

    :arg mousewheel: The user can use the mouse wheel to change the point
                     value.

    See the :func:`.widgets._String` documentation for details on the other
    parameters.
    """
    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    panel.SetSizer(sizer)

    ndims  = propObj._ndims
    real   = propObj._real

    if labels is None:
        labels = [None] * ndims

    for dim in range(len(propVal)):

        style = 0
        if not real:   style |= floatslider.SSP_INTEGER
        if showLimits: style |= floatslider.SSP_SHOW_LIMITS
        if editLimits: style |= floatslider.SSP_EDIT_LIMITS
        if mousewheel: style |= floatslider.SSP_MOUSEWHEEL

        slider = floatslider.SliderSpinPanel(
            panel,
            value=propVal[dim],
            minValue=propVal.getMin(dim),
            maxValue=propVal.getMax(dim),
            label=labels[dim],
            style=style)

        sizer.Add(slider, flag=wx.EXPAND)

        _pointBind(hasProps, propObj, propVal, slider, dim)

    panel.Layout()

    return panel


def _pointBind(hasProps, propObj, propVal, slider, dim, editLimits):
    """Called by the :func:`_Point` function.

    Binds the given :class:`.SliderSpinPanel` to one dimension of the given
    :class:`.PointValueList` so that changes in one are propagated to the
    other.

    :arg slider: The :class:`.SliderSpinPanel` instance.

    :arg dim:    The 0-indexed dimension of the :class:`.Point` value.

    See :func:`_Point` for details on the other arguments.
    """

    dimPropVal = propVal.getPropertyValueList()[dim]

    widgets._propBind(hasProps,
                      propObj._listType,
                      dimPropVal,
                      slider,
                      floatslider.EVT_SSP_VALUE)

    def propLimitsChanged(*a):
        minval = propVal.getMin(dim)
        maxval = propVal.getMax(dim)

        if minval is not None: slider.SetMin(minval)
        if maxval is not None: slider.SetMax(maxval)

    def sliderLimitsChanged(ev):
        propVal.setMin(dim, ev.min)
        propVal.setMax(dim, ev.max)
        ev.Skip()

    if editLimits:
        slider.Bind(floatslider.EVT_SSP_LIMIT, sliderLimitsChanged)

    lName = 'PointLimits_{}_{}'.format(id(slider), dim)

    dimPropVal.addAttributeListener(lName, propLimitsChanged, weak=False)

    def onDestroy(ev):
        dimPropVal.removeAttributeListener(lName)
        ev.Skip()

    slider.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)
