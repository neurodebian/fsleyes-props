#!/usr/bin/env python
#
# test_property_string.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#


import fsleyes_props as props


def test_assign():
    class MyObj(props.HasProperties):
        val = props.String()

    obj = MyObj()


    # TODO


def test_length():
    class MyObj(props.HasProperties):
        val = props.String()
