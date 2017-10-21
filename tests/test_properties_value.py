#!/usr/bin/env python
#
# test_propertyvalue.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import fsleyes_props.properties_value as properties_value

import logging

logging.basicConfig()
logging.getLogger('fsleyes_props').setLevel(logging.DEBUG)

class Context():
    pass


def test_listener():

    ctx    = Context()
    pv     = properties_value.PropertyValue(ctx)
    called = {}

    # TODO Test args passed to listener

    def l1(*a):
        called['l1'] = called.get('l1', 0) + 1

    def l2(*a):
        called['l2'] = called.get('l2', 0) + 1

    def al1(*a):
        called['al1'] = called.get('al1', 0) + 1

    def al2(*a):
        called['al2'] = called.get('al2', 0) + 1

    pv.addListener(         'l1',  l1)
    pv.addListener(         'l2',  l2)
    pv.addAttributeListener('al1', al1)
    pv.addAttributeListener('al2', al2)

    assert pv.hasListener('l1')
    assert pv.hasListener('l2')

    pv.set('New value')

    assert called['l1']  == 1
    assert called['l2']  == 1

    pv.set('New value')

    assert called['l1']  == 1
    assert called['l2']  == 1

    pv.set('New new value')

    assert called['l1']  == 2
    assert called['l2']  == 2

    assert called.get('al1') is None
    assert called.get('al2') is None

    pv.setAttribute('newAtt', 'value')

    assert called['al1'] == 1
    assert called['al2'] == 1

    pv.setAttribute('newAtt', 'value')

    assert called['al1'] == 1
    assert called['al2'] == 1

    pv.setAttribute('newAtt', 'new value')

    assert called['al1'] == 2
    assert called['al2'] == 2
