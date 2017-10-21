#!/usr/bin/env python
#
# widgets_number.py - Create widgets for modifying Number properties.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module provides the :func:`_Number` function, which is imported into
the :mod:`widgets` module namespace. It is separated purely to keep the
``widgets`` module file size down.
"""

import logging
import sys

import wx


from . import properties_types     as ptypes
from . import                         widgets
import fsleyes_widgets.floatslider as floatslider
import fsleyes_widgets.floatspin   as floatspin


log = logging.getLogger(__name__)


def _Number(
        parent,
        hasProps,
        propObj,
        propVal,
        slider=True,
        spin=True,
        showLimits=True,
        editLimits=True,
        mousewheel=False,
        increment=None,
        spinWidth=None,
        **kwargs):
    """Creates and returns a widget allowing the user to edit the given
    :class:`.Number` property value.

    If both the ``slider`` and ``spin`` arguments are ``True``, a
    :class:`.SliderSpinPanel` widget is returned; otherwise a
    :class:`.FloatSpinCtrl`, or :class:`.FloatSliders` widget is returned.


    If both ``slider`` and ``spin`` are ``False``, a :exc:`ValueError` is
    raised.


    :arg slider:     Display slider widgets allowing the user to control the
                     bound values.

    :arg spin:       Display spin control widgets allowing the user to control
                     the bound values.

    :arg showLimits: Show labels displaying the min/max values, if thye are
                     set on the ``Number`` property.

    :arg editLimits: Allow the user to edit the min/max values.

    :arg mousewheel: If ``True``, mouse wheel events on the spin/slider
                     control(s) will change the value.

    :arg increment:  If ``spin=True``, the increment/step size to be used when
                     increasing/decreasing the value. If not provided, a
                     suitable increment is calculated.

    :arg spinWidth:  Desired spin control width in characters. See the
                     :class:`.FloatSpinCtrl` class.

    See the :func:`.widgets._String` documentation for details on the
    parameters.
    """

    if not (slider or spin):
        raise ValueError('One of slider or spin must be True')

    minval  = propVal.getAttribute('minval')
    maxval  = propVal.getAttribute('maxval')
    isRange = (minval is not None) and (maxval is not None)

    if (not isRange) or (not slider):
        return _makeSpinBox(parent,
                            hasProps,
                            propObj,
                            propVal,
                            mousewheel,
                            increment,
                            spinWidth)

    else:
        return _makeSlider(parent,
                           hasProps,
                           propObj,
                           propVal,
                           spin,
                           showLimits,
                           editLimits,
                           mousewheel,
                           spinWidth)


def _makeSpinBox(parent,
                 hasProps,
                 propObj,
                 propVal,
                 mousewheel,
                 increment,
                 spinWidth):
    """Used by the :func:`_Number` function.

    Creates a :class:`.FloatSpinCtrl` and binds it to the given
    :class:`.PropertyValue` instance.

    See :func:`_Number` for details on the parameters.
    """

    if not isinstance(propObj, (ptypes.Int, ptypes.Real)):
        raise TypeError('Unrecognised property type: {}'.format(
            propObj.__class__.__name__))

    def getMinVal(val):
        if val is not None: return val
        if   isinstance(propObj, ptypes.Int):  return -2 ** 31 + 1
        elif isinstance(propObj, ptypes.Real): return -sys.float_info.max

    def getMaxVal(val):
        if val is not None: return val
        if   isinstance(propObj, ptypes.Int):  return 2 ** 31 - 1
        elif isinstance(propObj, ptypes.Real): return sys.float_info.max

    value   = propVal.get()
    minval  = propVal.getAttribute('minval')
    maxval  = propVal.getAttribute('maxval')
    limited = propVal.getAttribute('clamped')
    isRange = (minval is not None) and (maxval is not None)
    minval  = getMinVal(minval)
    maxval  = getMaxVal(maxval)

    if mousewheel: style = floatspin.FSC_MOUSEWHEEL
    else:          style = 0

    if isinstance(propObj, ptypes.Int):
        style     |= floatspin.FSC_INTEGER

    if not limited:
        style |= floatspin.FSC_NO_LIMIT

    if increment is None:
        if isinstance(propObj, ptypes.Int):
            increment = 1

        elif isinstance(propObj, ptypes.Real):
            if isRange: increment = (maxval - minval) / 100.0
            else:       increment = 0.5

    spin = floatspin.FloatSpinCtrl(
        parent,
        value=value,
        minValue=minval,
        maxValue=maxval,
        increment=increment,
        style=style,
        width=spinWidth)

    widgets._propBind(
        hasProps, propObj, propVal, spin, floatspin.EVT_FLOATSPIN)

    def updateRange(*a):
        minval = getMinVal(propVal.getAttribute('minval'))
        maxval = getMaxVal(propVal.getAttribute('maxval'))

        log.debug('Updating {} range from {}.{}: {} - {}'.format(
            type(spin).__name__,
            type(hasProps).__name__,
            propVal._name,
            minval,
            maxval))

        spin.SetRange(minval, maxval)

    listenerName = 'widgets_number_py_updateRange_{}'.format(id(spin))
    propVal.addAttributeListener(listenerName, updateRange, weak=False)

    def onDestroy(ev):
        propVal.removeAttributeListener(listenerName)
        ev.Skip()

    spin.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)

    return spin


def _makeSlider(parent,
                hasProps,
                propObj,
                propVal,
                showSpin,
                showLimits,
                editLimits,
                mousewheel,
                spinWidth):
    """Used by the :func:`_Number` function.

    Creates and returns a :class:`.FloatSlider` or :class:`.SliderSpinPanel`,
    and binds it to the given :class:`.PropertyValue` instance.

    See :func:`_Number` for details on the parameters.
    """

    value   = propVal.get()
    minval  = propVal.getAttribute('minval')
    maxval  = propVal.getAttribute('maxval')
    limited = propVal.getAttribute('clamped')

    if   isinstance(propObj, ptypes.Int):  real = False
    elif isinstance(propObj, ptypes.Real): real = True

    if not showSpin:

        if mousewheel: style = floatslider.FS_MOUSEWHEEL
        else:          style = 0

        if not real:
            style |= floatslider.FS_INTEGER

        evt    = wx.EVT_SLIDER
        slider = floatslider.FloatSlider(
            parent,
            value=value,
            minValue=minval,
            maxValue=maxval,
            style=style)

    else:
        evt    = floatslider.EVT_SSP_VALUE
        style  = 0

        if not real:    style |= floatslider.SSP_INTEGER
        if not limited: style |= floatslider.SSP_NO_LIMITS
        if showLimits:  style |= floatslider.SSP_SHOW_LIMITS
        if editLimits:  style |= floatslider.SSP_EDIT_LIMITS
        if mousewheel:  style |= floatslider.SSP_MOUSEWHEEL

        slider = floatslider.SliderSpinPanel(
            parent,
            value=value,
            minValue=minval,
            maxValue=maxval,
            style=style,
            spinWidth=spinWidth)

    # bind the slider value to the property value
    widgets._propBind(hasProps, propObj, propVal, slider, evt)

    # Update slider min/max bounds and labels
    # whenever the property attributes change.
    def updateSliderRange(*a):
        minval = propVal.getAttribute('minval')
        maxval = propVal.getAttribute('maxval')

        log.debug('Updating {} range from {}.{}: {} - {}'.format(
            type(slider).__name__,
            type(hasProps).__name__,
            propVal._name,
            minval,
            maxval))

        slider.SetRange(minval, maxval)
        # TODO check that value has changed due to the range change?

    listenerName = 'widgets_number_py_updateRange_{}'.format(id(slider))
    propVal.addAttributeListener(listenerName, updateSliderRange, weak=False)

    # remove the listener when the slider is destroyed
    def onDestroy(ev):
        propVal.removeAttributeListener(listenerName)
        ev.Skip()

    slider.Bind(wx.EVT_WINDOW_DESTROY, onDestroy)

    if editLimits:

        # When the user edits the slider bounds,
        # update the property attributes
        def updatePropRange(ev):
            propVal.setAttribute('minval', ev.min)
            propVal.setAttribute('maxval', ev.max)

        slider.Bind(floatslider.EVT_SSP_LIMIT, updatePropRange)

    return slider
