#!/usr/bin/env python
#
# test_property_types.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import numpy as np

import fsleyes_props as props


def test_define_and_assign():
    class Thing(props.HasProperties):

        myobject     = props.Object()
        mybool       = props.Boolean()
        myint        = props.Int()
        myreal       = props.Real()
        mypercentage = props.Percentage()
        mystring     = props.String()
        mychoice     = props.Choice(('1', '2', '3', '4', '5'))
        myfilepath   = props.FilePath()
        mylist       = props.List()
        mycolour     = props.Colour()
        mycolourmap  = props.ColourMap()
        mybounds     = props.Bounds(ndims=2)
        mypoint      = props.Point(ndims=2)
        myarray      = props.Array()

    t = Thing()

    t.myobject     = '12345'
    t.mybool       = False
    t.myint        = 12345
    t.myreal       = 0.12345
    t.mypercentage = 12.345
    t.mystring     = '12345'
    t.mychoice     = '5'
    t.myfilepath   = '/path/to/nonexistent/file.txt'
    t.mylist       = [1, 2, 3, 4, 5]
    t.mycolour     = (0.2, 0.3, 0.5, 1.0)
    t.mycolourmap  = 'cool'
    t.mybounds     = [0, 1, 0, 1]
    t.mypoint      = [0, 1]
    t.myarray      = np.eye(4)
