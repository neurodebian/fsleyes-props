#!/usr/bin/env python
#
# widgets_bounds.py - Create widgets for modifying Bounds properties.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

"""This module provides the :func:`_Bounds` function, which is imported into
the :mod:`widgets` module namespace. It is separated purely to keep the
``widgets`` module file size down.
"""


import wx

import numpy as np

import fsleyes_widgets.rangeslider as rangeslider


def _Bounds(parent,
            hasProps,
            propObj,
            propVal,
            slider=True,
            spin=True,
            showLimits=True,
            editLimits=True,
            mousewheel=False,
            labels=None,
            spinWidth=None,
            **kwargs):
    """Creates and returns a panel containing sliders/spinboxes which
    allow the user to edit the low/high values along each dimension of the
    given :class:`.Bounds` property value.


    If both the ``slider`` and ``spin`` arguments are ``True``, a
    :class:`.RangeSliderSpinPanel` widget is returned; otherwise
    a :class:`.RangePanel` is returned.


    If both ``slider`` and ``spin`` are ``False``, a :exc:`ValueError` is
    raised.


    :arg slider:     Display slider widgets allowing the user to control the
                     bound values.

    :arg spin:       Display spin control widgets allowing the user to control
                     the bound values.

    :arg showLimits: Show the bound limits.

    :arg editLimits: Add buttons allowing the user to edit the bound limits.

    :arg mousewheel: If ``True``, mouse wheel events over the slider/spin
                     controls will change the bounds values.

    :arg labels:     A list of strings of length ``2 * ndims``, where ``ndims``
                     is the number of dimensions on the ``Bounds`` property;
                     the strings are used as labels on the widget.

    :arg spinWidth:  Desired spin control width. See the
                     :class:`.FloatSpinCtrl` class.

    See the :func:`.widgets._String` documentation for details on the other
    parameters.
    """

    ndims   = propObj._ndims
    real    = propObj._real
    clamped = propObj.getListType().getAttribute(None, 'clamped')

    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    panel.SetSizer(sizer)

    if labels is None:
        labels = [None] * 2 * ndims

    for i in range(ndims):
        minDistance = propObj.getAttribute(hasProps, 'minDistance')
        minval      = propVal.getMin(i)
        maxval      = propVal.getMax(i)
        loval       = propVal.getLo(i)
        hival       = propVal.getHi(i)

        if minDistance is None: minDistance = 0
        if minval      is None: minval      = loval
        if maxval      is None: maxval      = hival

        if slider and spin:

            style = 0

            if mousewheel:  style |= rangeslider.RSSP_MOUSEWHEEL
            if not real:    style |= rangeslider.RSSP_INTEGER
            if showLimits:  style |= rangeslider.RSSP_SHOW_LIMITS
            if editLimits:  style |= rangeslider.RSSP_EDIT_LIMITS
            if not clamped: style |= rangeslider.RSSP_NO_LIMIT

            slider = rangeslider.RangeSliderSpinPanel(
                panel,
                minValue=minval,
                maxValue=maxval,
                lowValue=loval,
                highValue=hival,
                lowLabel=labels[i * 2],
                highLabel=labels[i * 2 + 1],
                minDistance=minDistance,
                spinWidth=spinWidth,
                style=style)

        elif slider or spin:

            style = 0

            if mousewheel:  style |= rangeslider.RP_MOUSEWHEEL
            if slider:      style |= rangeslider.RP_SLIDER
            if not real:    style |= rangeslider.RP_INTEGER
            if not clamped: style |= rangeslider.RP_NO_LIMIT

            slider = rangeslider.RangePanel(
                panel,
                minValue=minval,
                maxValue=maxval,
                lowValue=loval,
                highValue=hival,
                lowLabel=labels[i * 2],
                highLabel=labels[i * 2 + 1],
                minDistance=minDistance,
                spinWidth=spinWidth,
                style=style)

        else:
            raise ValueError('One of slider or spin must be True')

        _boundBind(hasProps, propObj, slider, propVal, i, editLimits)

        sizer.Add(slider, flag=wx.EXPAND)

    return panel


def _boundBind(hasProps, propObj, sliderPanel, propVal, axis, editLimits):
    """Called by the :func:`_Bounds` function.

    Binds the given :class:`.RangeSliderSpinPanel` or :class:`.RangePanel` to
    one axis of the given :class:`.BoundsValueList` so that changes in one are
    propagated to the other.

    :arg sliderPanel: The :class:`.RangeSliderSpinPanel`/:class:`.RangePanel`
                      instance.

    :arg axis:        The 0-indexed axis of the :class:`.Bounds` value.

    See :func:`_Bounds` for details on the other arguments.
    """


    lowProp    = propVal.getPropertyValueList()[axis * 2]
    highProp   = propVal.getPropertyValueList()[axis * 2 + 1]

    lowName     = 'BoundBind_{}_{}'.format(id(sliderPanel), id(lowProp))
    highName    = 'BoundBind_{}_{}'.format(id(sliderPanel), id(highProp))
    lowAttName  = 'BoundBindAtt_{}_{}'.format(id(sliderPanel), id(lowProp))
    highAttName = 'BoundBindAtt_{}_{}'.format(id(sliderPanel), id(highProp))

    # Called when the low or high PV changes
    def guiUpdate(*a):
        lowVal  = lowProp.get()
        highVal = highProp.get()

        if np.all(np.isclose(sliderPanel.GetRange(), (lowVal, highVal))):
            return

        sliderPanel.SetRange(lowVal, highVal)

    # Called on a rangeslider.EVT_LOW_RANGE event
    def lowPropUpdate(ev):
        lowProp.disableListener(lowName)
        lowProp.set(ev.low)
        lowProp.enableListener(lowName)
        ev.Skip()

    # Called on a rangeslider.EVT_HIGH_RANGE event
    def highPropUpdate(ev):
        highProp.disableListener(highName)
        highProp.set(ev.high)
        highProp.enableListener(highName)
        ev.Skip()

    # Called on a rangeslider.EVT_RANGE event
    def propUpdate(ev):
        lowProp .disableListener(lowName)
        highProp.disableListener(highName)
        propVal.setRange(axis, ev.low, ev.high)
        lowProp .enableListener(lowName)
        highProp.enableListener(highName)

    # Called when any attributes of the
    # individual bounds property values change
    def updateSliderRange(ctx, att, *a):

        if att not in ('minval', 'maxval'):
            return

        minval = propVal.getMin(axis)
        maxval = propVal.getMax(axis)

        sliderPanel.SetLimits(minval, maxval)

    # Called on rangeslider.EVT_RANGE_LIMIT events
    def updatePropRange(ev):
        lowProp .disableAttributeListener(lowName)
        highProp.disableAttributeListener(highName)
        propVal.setLimits(axis, ev.min, ev.max)
        lowProp .enableAttributeListener(lowName)
        highProp.enableAttributeListener(highName)
        ev.Skip()

    sliderPanel.Bind(rangeslider.EVT_RANGE,      propUpdate)
    sliderPanel.Bind(rangeslider.EVT_LOW_RANGE,  lowPropUpdate)
    sliderPanel.Bind(rangeslider.EVT_HIGH_RANGE, highPropUpdate)

    lowProp .addListener(lowName,  guiUpdate, weak=False)
    highProp.addListener(highName, guiUpdate, weak=False)

    lowProp .addAttributeListener(lowAttName,  updateSliderRange, weak=False)
    highProp.addAttributeListener(highAttName, updateSliderRange, weak=False)

    if editLimits:
        sliderPanel.Bind(rangeslider.EVT_RANGE_LIMIT, updatePropRange)

    def onDestroy(ev):
        ev.Skip()
        if ev.GetEventObject() is not sliderPanel:
            return

        lowProp .removeListener(         lowName)
        highProp.removeListener(         highName)
        lowProp .removeAttributeListener(lowAttName)
        highProp.removeAttributeListener(highAttName)

    sliderPanel.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)
