#!/usr/bin/env python
#
# test_syncable.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import fsleyes_props as props

def test_syncabe_list_link1():  _test_syncabe_list_link(1)
def test_syncabe_list_link2():  _test_syncabe_list_link(2)
def test_syncabe_list_link3():  _test_syncabe_list_link(3)
def test_syncabe_list_link4():  _test_syncabe_list_link(4)
def test_syncabe_list_link5():  _test_syncabe_list_link(5)
def test_syncabe_list_link6():  _test_syncabe_list_link(6)
def test_syncabe_list_link7():  _test_syncabe_list_link(7)
def test_syncabe_list_link8():  _test_syncabe_list_link(8)
def test_syncabe_list_link9():  _test_syncabe_list_link(9)
def test_syncabe_list_link10(): _test_syncabe_list_link(10)

# List properties whcih are synced together, and also
# where, within each instance, individual list items
# are bound across properties
def _test_syncabe_list_link(nchildren):
    class Thing(props.SyncableHasProperties):
        crange = props.Bounds(ndims=1, clamped=False)
        drange = props.Bounds(ndims=1, clamped=False)
        linklo = props.Boolean(default=True)

        def __init__(self, *args, **kwargs):
            props.SyncableHasProperties.__init__(self, *args, **kwargs)
            parent = self.getParent()

            if parent is not None:
                self.addListener('linklo',
                                 str(id(self)),
                                 self.__linkloChanged)
                if self.linklo:  self.__linkloChanged()

        def __linkloChanged(self, *a):
            self.__updateLink(self.linklo, 0)

        def __updateLink(self, val, idx):

            drangePV = self.drange.getPropertyValueList()[idx]
            crangePV = self.crange.getPropertyValueList()[idx]

            if props.propValsAreBound(drangePV, crangePV) == val:
                return

            props.bindPropVals(drangePV,
                               crangePV,
                               bindval=True,
                               bindatt=False,
                               unbind=not val)

            if val:
                crangePV.set(drangePV.get())

    parent   = Thing()
    children = [Thing(parent=parent) for i in range(nchildren)]

    parent.crange = [10, 20]
    parent.drange = [5,  10]

    for i in [parent] + children:
        assert i.crange == [5, 20]
        assert i.drange == [5, 10]
