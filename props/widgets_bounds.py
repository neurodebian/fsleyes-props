#!/usr/bin/env python
#
# widgets_bounds.py - Create widgets for modifying Bounds properties.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

"""Create widgets for modifying :class:`~props.properties_types.Bounds`
properties.

This module is not intended to be used directly - it is imported into the
:mod:`props.widgets` namespace.
"""

import wx

import pwidgets.rangeslider as rangeslider

def _boundBind(hasProps, propObj, sliderPanel, propVal, axis, editLimits):
    """Binds the given :class:`~pwidgets.rangeslider.RangeSliderSpinPanel` to
    one axis of the given :class:`~props.properties_types.BoundsValueList` so
    that changes in one are propagated to the other.

    :param hasProps:    The owning :class:`~props.properties.HasProperties`
                        instance.
    
    :param propObj:     The :class:`~props.properties_types.Bounds` instance.
    
    :param sliderPanel: The :class:`~pwidgets.rangeslider.RangeSliderSpinPanel`
                        instance.
    
    :param propVal:     The :class:`~props.properties_types.BoundsValueList`
                        instance.
    
    :param axis:        The 0-indexed axis of the
                        :class:`~props.properties_types.Bounds` value.

    :param editLimits:  If ``True`` the ``sliderPanel`` has been configure to
                        allow the user to edit the bound limits.
    """

    
    lowProp    = propVal.getPropertyValueList()[axis * 2]
    highProp   = propVal.getPropertyValueList()[axis * 2 + 1]

    lowName    = 'BoundBind_{}_{}'.format(id(sliderPanel), id(lowProp))
    highName   = 'BoundBind_{}_{}'.format(id(sliderPanel), id(highProp))

    def lowGuiUpdate(value, *a):
        if sliderPanel.GetLow() == value: return
        sliderPanel.SetLow(value)
        
    def highGuiUpdate(value, *a):
        if sliderPanel.GetHigh() == value: return
        sliderPanel.SetHigh(value)

    def propUpdate(ev):
        lowProp .set(ev.low)
        highProp.set(ev.high)
        ev.Skip()

    def updateSliderRange(ctx, att, *a):

        if att not in ('minval', 'maxval'):
            return
        
        minval = propVal.getMin(axis)
        maxval = propVal.getMax(axis)

        if minval is not None: sliderPanel.SetMin(minval)
        if maxval is not None: sliderPanel.SetMax(maxval) 

    def updatePropRange(ev):
        propVal.setMin(axis, ev.min)
        propVal.setMax(axis, ev.max)
        ev.Skip()

    sliderPanel.Bind(rangeslider.EVT_RANGE, propUpdate)

    lowProp .addListener(lowName,  lowGuiUpdate,  weak=False)
    highProp.addListener(highName, highGuiUpdate, weak=False)

    lowProp .addAttributeListener(lowName,  updateSliderRange, weak=False)
    highProp.addAttributeListener(highName, updateSliderRange, weak=False)

    if editLimits:
        sliderPanel.Bind(rangeslider.EVT_RANGE_LIMIT, updatePropRange)

    def onDestroy(ev):
        lowProp .removeListener(         lowName)
        highProp.removeListener(         highName)
        lowProp .removeAttributeListener(lowName)
        highProp.removeAttributeListener(highName)
        ev.Skip()
        
    sliderPanel.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)


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
            **kwargs):
    """Creates and returns a panel containing sliders/spinboxes which
    allow the user to edit the low/high values along each dimension of the
    given :class:`~props.properties_types.Bounds` value.
    """

    ndims    = propObj._ndims
    panel    = wx.Panel(parent)
    sizer    = wx.BoxSizer(wx.VERTICAL)

    if labels is None:
        labels = propObj._labels
        if labels is None:
            labels = [None] * 2 * ndims
    
    panel.SetSizer(sizer)

    for i in range(ndims):
        minDistance = propObj.getConstraint(hasProps, 'minDistance')
        minval      = propVal.getMin(i)
        maxval      = propVal.getMax(i)
        loval       = propVal.getLo(i)
        hival       = propVal.getHi(i)

        if minDistance is None: minDistance = 0

        if slider and spin:

            if minval is None: minval = loval
            if maxval is None: maxval = hival
        
            slider = rangeslider.RangeSliderSpinPanel(
                panel,
                minValue=minval,
                maxValue=maxval,
                lowValue=loval,
                highValue=hival,
                lowLabel=labels[i * 2],
                highLabel=labels[i * 2 + 1],
                minDistance=minDistance, 
                showLimits=showLimits,
                editLimits=editLimits,
                mousewheel=mousewheel)
        else:
            if slider:
                widgetType = 'slider'
                if minval is None: minval = loval
                if maxval is None: maxval = hival                
            elif spin:
                widgetType = 'spin'
            else: raise ValueError('One of slider or spin must be True')
            
            slider = rangeslider.RangePanel(
                panel,
                widgetType,
                minValue=minval,
                maxValue=maxval,
                lowValue=loval,
                highValue=hival,
                lowLabel=labels[i * 2],
                highLabel=labels[i * 2 + 1],
                minDistance=minDistance,
                mousewheel=mousewheel) 

        sizer.Add(slider, flag=wx.EXPAND)

        _boundBind(hasProps, propObj, slider, propVal, i, editLimits)

    panel.Layout()
    return panel
