#!/usr/bin/env python
#
# widgets_point.py - Create widgets for modifying Point properties.
#
# This module is not intended to be used directly - it is imported
# into the props.widgets namespace.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import wx

import pwidgets.floatslider as floatslider

import widgets

def _pointBind(hasProps, propObj, propVal, slider, dim):

    pvl        = propVal.getPropertyValueList()
    editLimits = propObj.getConstraint(hasProps, 'editLimits') 
    
    widgets._propBind(hasProps,
                      propObj._listType,
                      pvl[dim],
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

    propObj.addItemConstraintListener(
        hasProps, dim, lName, propLimitsChanged)

    def onDestroy(ev):
        propObj.removeItemConstraintListener(hasProps, dim, lName)
        ev.Skip()

    slider.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)


def _Point(parent, hasProps, propObj, propVal):
    """
    Creates and returns a widget allowing the user to edit the given Point
    property.
    """
    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    panel.SetSizer(sizer)

    ndims  = propObj._ndims
    real   = propObj._real
    labels = propObj._labels

    if labels is None: labels = [None] * ndims

    editLimits = propObj.getConstraint(hasProps, 'editLimits')

    for dim in range(len(propVal)):

        slider = floatslider.SliderSpinPanel(
            panel,
            real=real,
            value=propVal[dim],
            minValue=propVal.getMin(dim),
            maxValue=propVal.getMax(dim),
            label=labels[dim],
            showLimits=True,
            editLimits=editLimits)

        sizer.Add(slider, flag=wx.EXPAND)

        _pointBind(hasProps, propObj, propVal, slider, dim)

    panel.Layout()

    return panel
