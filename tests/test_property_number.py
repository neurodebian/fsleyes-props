#!/usr/bin/env python
#
# test_property_number.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#


import pytest

import fsleyes_props as props


def test_Int():

    class MyObj(props.HasProperties):
        unbounded           = props.Int()
        unbounded_default   = props.Int(default=10)
        bounded             = props.Int(minval=0, maxval=10)
        bounded_min         = props.Int(minval=0)
        bounded_max         = props.Int(maxval=10)
        bounded_clamped     = props.Int(clamped=True, minval=0, maxval=10)
        bounded_min_clamped = props.Int(clamped=True, minval=0)
        bounded_max_clamped = props.Int(clamped=True, maxval=10)


    obj = MyObj()

    # property, value, expected

    assert obj.unbounded_default == 10

    with pytest.raises(ValueError): obj.unbounded = ''
    with pytest.raises(ValueError): obj.unbounded = 'abcde'
    with pytest.raises(TypeError):  obj.unbounded = None

    testcases = [
        ('unbounded',         '-999', -999),
        ('unbounded',            '0',    0),
        ('unbounded',          '999',  999),
        ('unbounded',           -999, -999),
        ('unbounded',              0,    0),
        ('unbounded',            999,  999),
        ('unbounded',           -1.7,   -1),
        ('unbounded',           -1.2,   -1),
        ('unbounded',           -0.7,    0),
        ('unbounded',           -0.3,    0),
        ('unbounded',            0.3,    0),
        ('unbounded',            0.7,    0),
        ('unbounded',            1.2,    1),
        ('unbounded',            1.7,    1),
        ('bounded',             -999, -999),
        ('bounded',                0,    0),
        ('bounded',              999,  999),
        ('bounded_min',         -999, -999),
        ('bounded_min',            0,    0),
        ('bounded_min',          999,  999),
        ('bounded_max',         -999, -999),
        ('bounded_max',            0,    0),
        ('bounded_max',          999,  999),
        ('bounded_clamped',     -999,    0),
        ('bounded_clamped',       -1,    0),
        ('bounded_clamped',        0,    0),
        ('bounded_clamped',        5,    5),
        ('bounded_clamped',       10,   10),
        ('bounded_clamped',       11,   10),
        ('bounded_clamped',      999,   10),
        ('bounded_min_clamped', -999,    0),
        ('bounded_min_clamped',   -1,    0),
        ('bounded_min_clamped',    0,    0),
        ('bounded_min_clamped',    5,    5),
        ('bounded_min_clamped',   10,   10),
        ('bounded_min_clamped',  999,  999),
        ('bounded_max_clamped', -999, -999),
        ('bounded_max_clamped',   -1,   -1),
        ('bounded_max_clamped',    0,    0),
        ('bounded_max_clamped',    5,    5),
        ('bounded_max_clamped',   10,   10),
        ('bounded_max_clamped',   11,   10),
        ('bounded_max_clamped',  999,   10),
    ]


    for prop, val, exp in testcases:

        setattr(obj, prop, val)
        assert getattr(obj, prop) == exp

def test_Real():

    class MyObj(props.HasProperties):
        unbounded           = props.Real()
        unbounded_default   = props.Real(default=10)
        bounded             = props.Real(minval=0, maxval=10)
        bounded_min         = props.Real(minval=0)
        bounded_max         = props.Real(maxval=10)
        bounded_clamped     = props.Real(clamped=True, minval=0, maxval=10)
        bounded_min_clamped = props.Real(clamped=True, minval=0)
        bounded_max_clamped = props.Real(clamped=True, maxval=10)


    obj = MyObj()

    assert obj.unbounded_default == 10
    assert obj.bounded_min       == 0
    assert obj.bounded_max       == 10
    assert obj.bounded           == 5

    # property, value, expected
    testcases = [
        ('unbounded',         '-0.5', -0.5),
        ('unbounded',          '0.0',  0.0),
        ('unbounded',          '0.5',  0.5),
        ('unbounded',         '-999', -999),
        ('unbounded',            '0',    0),
        ('unbounded',          '999',  999),
        ('unbounded',           -999, -999),
        ('unbounded',              0,    0),
        ('unbounded',            999,  999),
        ('bounded',             -999, -999),
        ('bounded',                0,    0),
        ('bounded',              999,  999),
        ('bounded_min',         -999, -999),
        ('bounded_min',            0,    0),
        ('bounded_min',          999,  999),
        ('bounded_max',         -999, -999),
        ('bounded_max',            0,    0),
        ('bounded_max',          999,  999),
        ('bounded_clamped',     -999,    0),
        ('bounded_clamped',       -1,    0),
        ('bounded_clamped',        0,    0),
        ('bounded_clamped',        5,    5),
        ('bounded_clamped',       10,   10),
        ('bounded_clamped',       11,   10),
        ('bounded_clamped',      999,   10),
        ('bounded_min_clamped', -999,    0),
        ('bounded_min_clamped',   -1,    0),
        ('bounded_min_clamped',    0,    0),
        ('bounded_min_clamped',    5,    5),
        ('bounded_min_clamped',   10,   10),
        ('bounded_min_clamped',  999,  999),
        ('bounded_max_clamped', -999, -999),
        ('bounded_max_clamped',   -1,   -1),
        ('bounded_max_clamped',    0,    0),
        ('bounded_max_clamped',    5,    5),
        ('bounded_max_clamped',   10,   10),
        ('bounded_max_clamped',   11,   10),
        ('bounded_max_clamped',  999,   10),
    ]


    for prop, val, exp in testcases:

        setattr(obj, prop, val)
        assert getattr(obj, prop) == exp


def test_Percentage():

    class MyObj(props.HasProperties):
        default                 = props.Percentage()
        default_clamped         = props.Percentage(clamped=True)
        default_bounded_clamped = props.Percentage(clamped=True,
                                                   minval=100,
                                                   maxval=1000)

    obj = MyObj()

    testcases = [
        ('default',                  -500,   -500),
        ('default',                  -100,   -100),
        ('default',                     0,      0),
        ('default',                   100,    100),
        ('default',                   500,    500),
        ('default_clamped',          -500,      0),
        ('default_clamped',          -100,      0),
        ('default_clamped',             0,      0),
        ('default_clamped',           100,    100),
        ('default_clamped',           500,    100),

        ('default_bounded_clamped',  -500,    100),
        ('default_bounded_clamped',  -100,    100),
        ('default_bounded_clamped',     0,    100),
        ('default_bounded_clamped',   100,    100),
        ('default_bounded_clamped',   500,    500),
        ('default_bounded_clamped',  1000,   1000),
        ('default_bounded_clamped',  1001,   1000),
    ]

    for prop, val, exp in testcases:

        setattr(obj, prop, val)
        assert getattr(obj, prop) == exp
