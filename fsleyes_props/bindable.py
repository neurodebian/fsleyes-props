#!/usr/bin/env python
#
# bindable.py - This module adds functionality to the HasProperties class
# to allow properties from different instances to be bound to each other.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""This module adds functionality to the :class:`.HasProperties` class to
allow properties from different instances to be bound to each other.  The
logic defined in this module is separated purely to keep the
:mod:`.properties` and :mod:`.properties_value` module file sizes down.


The following functions are defined in this module and are used by the
the :class:`.HasProperties` class.


 .. autosummary::
    :nosignatures:

    bindProps
    unbindProps
    isBound


These functions use the following functions, which work directly with
:class:`.PropertyValue` instances, and are available for advanced usage:


 .. autosummary::
    :nosignatures:

    bindPropVals
    propValsAreBound


:class:`.PropertyValue` instances use the following methods for
synchronisation of attribute and values, notification of their listeners, and
access to other ``PropertyValue`` instances to which they are bound:

 .. autosummary::
    :nosignatures:

    syncAndNotify
    syncAndNotifyAtts
    buildBPVList


-------------
Example usage
-------------

::

    >>> import fsleyes_props as props

    >>> class MyObj(props.HasProperties):
            myint  = props.Int()
            myreal = props.Real()

    >>> myobj1 = MyObj()
    >>> myobj2 = MyObj()

    # Set some initial values
    >>> myobj1.myint  = 1
    >>> myobj1.myreal = 0.1
    >>> myobj2.myint  = 2
    >>> myobj2.myreal = 0.12

    # Bind myobj1.myint and myobj2.myint.
    # The instance on which bindProps is
    # called will inherit the value of the
    # other instance
    >>> myobj2.bindProps('myint', myobj1)

    >>> print myobj2
    MyObj
       myint = 1
      myreal = 0.2

    # Changing a bound property value on either
    # instance will result in the value being
    # propagated to the other instance.
    >>> myobj2.myint = 8
    >>> print myobj1
    MyObj
       myint = 8
      myreal = 0.1


-------
Details
-------


When a ``HasProperties`` property value is changed, the associated
``PropertyValue`` instance does two things:

  1. Casts and validates the new value and updates its stored value.
  2. Calls the :func:`syncAndNotify` function.

The ``syncAndNotify`` function then does the following:

  3. Updates the value on all bound ``PropertyValue`` instances.
  4. Notifies all listeners, registered on the source ``PV`` instance, of the
     value change.
  5. Notifies all listeners, registered on the bound ``PV`` instances, of the
     value change.

An important point to note regarding step 2 above is that *all* PV instances
which are bound, either directly or indirectly, to the source PV instance,
will be updated. In other words, there are no restrictions on the ways in
which ``PropertyValue`` instances may be bound.  A tree, chain, or even a
network of ``PV`` instances can be bound together - the above process will
still work.
"""


import logging
import weakref

import fsl.utils.weakfuncref as weakfuncref


log = logging.getLogger(__name__)


class Bidict(object):
    """A bare-bones bi-directional dictionary, used for binding
    :class:`.PropertyValueList` instances - see the :func:`_bindListProps` and
    :func:`_syncPropValLists` functions.
    """

    def __init__(self):
        self._thedict = {}

    def __setitem__(self, key, value):
        self._thedict[key]   = value
        self._thedict[value] = key

    def __delitem__(self, key):
        val = self._thedict.pop(key)
        self      ._thedict.pop(val)

    def get(self, key, default=None):
        return self._thedict.get(key, default)

    def __getitem__(self, key):
        return self._thedict.__getitem__(key)
    def __repr__(   self):
        return self._thedict.__repr__()
    def __str__(    self):
        return self._thedict.__str__()


def bindProps(self,
              propName,
              other,
              otherPropName=None,
              bindval=True,
              bindatt=True,
              unbind=False):
    """Binds the properties specified by ``propName`` and ``otherPropName``
    such that changes to one are applied to the other.

    If the properties are :class:`.List` properties, the :func:`_bindListProps`
    function is called. Otherwise the :func:`_bindProps` function is called.

    :arg str propName:  The name of a property on this ``HasProperties``
                        instance.

    :arg other:         Another ``HasProperties`` instance.

    :arg otherPropName: The name of a property on ``other`` to
                        bind to. If ``None`` it is assumed that
                        there is a property on ``other`` called
                        ``propName``.

    :arg bindval:       If ``True`` (the default), property values
                        are bound. This parameter is ignored for
                        list properties.

    :arg bindatt:       If ``True`` (the default), property attributes
                        are bound.  For :class:`.List` properties, this
                        parameter applies to the list values, not to the
                        list itself.

    :arg unbind:        If ``True``, the properties are unbound.
                        See the :meth:`unbindProps` method.
    """

    from . import properties

    if otherPropName is None: otherPropName = propName

    myProp    = self .getProp(propName)
    otherProp = other.getProp(otherPropName)

    if type(myProp) != type(otherProp):
        raise ValueError('Properties must be of the '
                         'same type to be bound')

    if isinstance(myProp, properties.ListPropertyBase):
        _bindListProps(self,
                       myProp,
                       other,
                       otherProp,
                       bindatt=bindatt,
                       unbind=unbind)
    else:
        _bindProps(self,
                   myProp,
                   other,
                   otherProp,
                   bindval=bindval,
                   bindatt=bindatt,
                   unbind=unbind)


def unbindProps(self,
                propName,
                other,
                otherPropName=None,
                bindval=True,
                bindatt=True):
    """Unbinds two properties previously bound via a call to :func:`bindProps`.
    """
    self.bindProps(propName,
                   other,
                   otherPropName,
                   bindval=bindval,
                   bindatt=bindatt,
                   unbind=True)


def isBound(self, propName, other, otherPropName=None):
    """Returns ``True`` if the specified property is bound to the
    other ``HasProperties`` instance, ``False`` otherwise.
    """

    if otherPropName is None: otherPropName = propName

    myProp       = self     .getProp(   propName)
    otherProp    = other    .getProp(   otherPropName)
    myPropVal    = myProp   .getPropVal(self)
    otherPropVal = otherProp.getPropVal(other)

    return propValsAreBound(myPropVal, otherPropVal)


def syncAndNotifyAtts(self, name, value):
    """This method is called by the
    :meth:`.PropertyValue.notifyAttributeListeners` method.

    It ensures that the attributes of any bound :class:`.PropertyValue`
    instances are synchronised, and then notifies all attribute listeners.
    """

    boundPropVals = _sync(self, True, name, value)
    boundPropVals = [self] + [bpv[0] for bpv in boundPropVals]

    _callAllListeners(boundPropVals, True, name, value)


def syncAndNotify(self):
    """Synchronises the value contained in all bound :class:`.PropertyValue`
    instances with the value contained in this instance, and notifies all
    registered listeners of the value change. This method is called by the
    :meth:`.PropertyValue.propNotify` method.
    """

    from . import properties_value

    bpvs    = _sync(self)
    allBpvs = []

    for bpv, listItems in bpvs:
        if isinstance(bpv, properties_value.PropertyValueList):
            allBpvs.extend(listItems)
        allBpvs.append(bpv)

    _callAllListeners([self] + allBpvs, False)


def _bindProps(self,
               myProp,
               other,
               otherProp,
               bindval=True,
               bindatt=True,
               unbind=False):
    """Binds the :class:`.PropertyValue` instances of two
    :class:`.PropertyBase` instances together. See the :func:`bindProps`
    function for details on the parameters.
    """

    myPropVal    = myProp   .getPropVal(self)
    otherPropVal = otherProp.getPropVal(other)

    if not unbind:
        allow = myPropVal.allowInvalid()
        myPropVal.allowInvalid(True)

        if bindatt: myPropVal.setAttributes(otherPropVal.getAttributes())
        if bindval: myPropVal.set(          otherPropVal.get())

        myPropVal.allowInvalid(allow)

    bindPropVals(myPropVal,
                 otherPropVal,
                 bindval=bindval,
                 bindatt=bindatt,
                 unbind=unbind)


def _bindListProps(self,
                   myProp,
                   other,
                   otherProp,
                   bindatt=True,
                   unbind=False):
    """Binds the :class:`.PropertyValueList` instances of two
    :class:`.ListPropertyBase` instances together. See the :func:`bindProps`
    function for details on the parameters.
    """

    myPropVal    = myProp   .getPropVal(self)
    otherPropVal = otherProp.getPropVal(other)

    # The unbinding case is easy
    if unbind:
        myPropValList    = myPropVal   .getPropertyValueList()
        otherPropValList = otherPropVal.getPropertyValueList()

        myPropVal   ._listPropValMaps.pop(id(otherPropVal))
        otherPropVal._listPropValMaps.pop(id(myPropVal))

        for myItem, otherItem in zip(myPropValList, otherPropValList):
            bindPropVals(myItem,
                         otherItem,
                         bindval=False,
                         bindatt=bindatt,
                         unbind=True)

        bindPropVals(myPropVal, otherPropVal, unbind=True)
        return

    # Binding two lists is a
    # bit more complicated ...

    # Inhibit list-level notification due to item
    # changes during the initial sync - we'll
    # manually do a list-level notification after
    # all the list values have been synced
    notifState = myPropVal.getNotificationState()
    myPropVal.disableNotification()

    # Force the two lists to have
    # the same number of elements
    if len(myPropVal) > len(otherPropVal):
        del myPropVal[len(otherPropVal):]

    elif len(myPropVal) < len(otherPropVal):
        myPropVal.extend(otherPropVal[len(myPropVal):])

    # Create a mapping between the
    # PropertyValue pairs across
    # the two lists
    myPropValList    = myPropVal   .getPropertyValueList()
    otherPropValList = otherPropVal.getPropertyValueList()
    propValMap       = Bidict()

    # Copy item values from the master list
    # to the slave list, and save the mapping
    for myItem, otherItem in zip(myPropValList, otherPropValList):

        log.debug('Binding list item {}.{} ({}) <- {}.{} ({})'.format(
            self.__class__.__name__,
            myProp.getLabel(self),
            myItem.get(),
            other.__class__.__name__,
            otherProp.getLabel(other),
            otherItem.get()))

        # Disable item notification - we'll
        # manually force a notify after the
        # sync
        itemNotifState = myItem.getNotificationState()
        myItem.disableNotification()

        # Bind attributes between PV item pairs,
        # but not value - value change of items
        # in a list is handled at the list level
        bindPropVals(myItem, otherItem, bindval=False, bindatt=bindatt)
        propValMap[myItem] = otherItem

        atts = otherItem.getAttributes()

        # Set attributes first, because the attribute
        # values may influence/modify the property value
        if bindatt: myItem.setAttributes(atts)
        myItem.set(otherItem.get())

        # Notify item level listeners of the value
        # change (if notification was enabled).
        #
        # TODO This notification occurs even
        # if the two PV objects had the same
        # value before the sync - you should
        # notify only if the myItem PV value
        # has changed.
        myItem.setNotificationState(itemNotifState)
        if itemNotifState:
            # notify attribute listeners first
            if bindatt:
                for name, val in atts.items():
                    syncAndNotifyAtts(myItem, name, val)

            syncAndNotify(myItem)

    # This mapping is stored on the PVL objects,
    # and used by the _syncListPropVals function
    myPropValMaps    = getattr(myPropVal,    '_listPropValMaps', {})
    otherPropValMaps = getattr(otherPropVal, '_listPropValMaps', {})

    # We can't use the PropValList objects as
    # keys, because they are not hashable.
    myPropValMaps[   id(otherPropVal)] = propValMap
    otherPropValMaps[id(myPropVal)]    = propValMap

    myPropVal   ._listPropValMaps = myPropValMaps
    otherPropVal._listPropValMaps = otherPropValMaps

    # Bind list-level value/attributes
    # between the PropertyValueList objects
    atts = otherPropVal.getAttributes()
    myPropVal.setAttributes(atts)

    bindPropVals(myPropVal, otherPropVal)

    # Manually notify list-level listeners
    #
    # TODO This notification will occur
    # even if the two lists had the same
    # value before being bound. It might
    # be worth only performing the
    # notification if the list has changed
    # value
    myPropVal.setNotificationState(notifState)

    # Sync the PVS, ensure that the sync
    # is propagated to other bound PVs,
    # and notify all listeners.
    for name, val in atts.items():
        syncAndNotifyAtts(myPropVal, name, val)

    syncAndNotify(myPropVal)


def propValsAreBound(pv1, pv2):
    """Returns ``True`` if the given :class:`.PropertyValue` instances are
    bound to each other, ``False`` otherwise.
    """

    pv1BoundPropVals = pv1.__dict__.get('boundPropVals', {})
    pv2BoundPropVals = pv2.__dict__.get('boundPropVals', {})

    return (id(pv2) in pv1BoundPropVals and
            id(pv1) in pv2BoundPropVals)


def bindPropVals(myPropVal,
                 otherPropVal,
                 bindval=True,
                 bindatt=True,
                 unbind=False):
    """Binds two :class:`.PropertyValue` instances together such that when the
    value of one changes, the other is changed. Note that the values are not
    immediately synchronised - they will become synchronised on the next change
    to either ``PropertyValue``.

    See :func:`bindProps` for details on the parameters.
    """

    mine  = myPropVal
    other = otherPropVal

    # A dict containing { id(PV) : PV } mappings is stored
    # on each PV, and used to maintain references to bound
    # PVs. We use a WeakValueDictionary (instead of just a
    # set) so that these references do not prevent PVs
    # which are no longer in use from being GC'd.
    wvd = weakref.WeakValueDictionary

    myBoundPropVals       = mine .__dict__.get('boundPropVals',    wvd())
    myBoundAttPropVals    = mine .__dict__.get('boundAttPropVals', wvd())
    otherBoundPropVals    = other.__dict__.get('boundPropVals',    wvd())
    otherBoundAttPropVals = other.__dict__.get('boundAttPropVals', wvd())

    if unbind: action = 'Unbinding'
    else:      action = 'Binding'

    log.debug('{} property values '
              '(val={}, att={}) {}.{} ({}) <-> {}.{} ({})'.format(
                  action,
                  bindval,
                  bindatt,
                  myPropVal._context.__class__.__name__,
                  myPropVal._name,
                  id(myPropVal),
                  otherPropVal._context.__class__.__name__,
                  otherPropVal._name,
                  id(otherPropVal)))

    if bindval:
        if unbind:
            myBoundPropVals   .pop(id(other))
            otherBoundPropVals.pop(id(mine))
        else:
            myBoundPropVals[   id(other)] = other
            otherBoundPropVals[id(mine)]  = mine

    if bindatt:
        if unbind:
            myBoundAttPropVals   .pop(id(other))
            otherBoundAttPropVals.pop(id(mine))
        else:
            myBoundAttPropVals[   id(other)] = other
            otherBoundAttPropVals[id(mine)]  = mine

    mine .boundPropVals    = myBoundPropVals
    mine .boundAttPropVals = myBoundAttPropVals
    other.boundPropVals    = otherBoundPropVals
    other.boundAttPropVals = otherBoundAttPropVals

    # When a master PV is synchronised to a slave PV,
    # it stores a flag on the slave PV which is checked
    # before starting a sync. If the flag is True,
    # the sync is inhibited. See the _sync function below.
    mine ._syncing = getattr(mine,  '_syncing', False)
    other._syncing = getattr(other, '_syncing', False)


def _syncPropValLists(masterList, slaveList):
    """Called by the :func:`_sync` function when one of a pair of bound
    :class:`.PropertyValueList` instances changes.

    Propagates the change on the ``masterList`` (either an addition, a
    removal, or a re-ordering) to the ``slaveList``.
    """

    propValMap = masterList._listPropValMaps[id(slaveList)]

    # If the change was due to the values of one or more PV
    # items changing (as opposed to a list modification -
    # addition/removal/reorder), the PV objects which
    # changed are stored in this list and returned
    changed = []

    # one or more items have been
    # added to the master list
    if len(masterList) > len(slaveList):

        # Loop through the PV objects in the master
        # list, and search for any which do not have
        # a paired PV object in the slave list
        for i, mpv in enumerate(masterList.getPropertyValueList()):

            spv = propValMap.get(mpv, None)

            # we've found a value in the master
            # list which is not in the slave list
            if spv is None:

                # add a new value to the slave list
                slaveList.insert(i, mpv.get())

                # retrieve the corresponding PV
                # object that was created by
                # the slave list
                spvs = slaveList.getPropertyValueList()
                spv  = spvs[i]

                # register a mapping between the
                # new master and slave PV objects
                propValMap[mpv] = spv

                # Bind the attributes of
                # the two new PV objects
                bindPropVals(mpv, spv, bindval=False)

    # one or more items have been
    # removed from the master list
    elif len(masterList) < len(slaveList):

        mpvs = masterList.getPropertyValueList()

        # Loop through the PV objects in the slave
        # list, and check to see if their mapped
        # master PV object has been removed from
        # the master list. Loop backwards so we can
        # delete items from the slave list as we go,
        # without having to offset the list index.
        for i, spv in reversed(
                list(enumerate(slaveList.getPropertyValueList()))):

            # If this raises an error, there's a bug
            # in somebody's code ... probably mine.
            mpv = propValMap[spv]

            # we've found a value in the slave list
            # which is no longer in the master list
            if mpv not in mpvs:

                # Delete the item from the slave
                # list, and delete the PV mapping
                del slaveList[ i]
                del propValMap[mpv]

    # list re-order, or individual
    # value change
    else:

        mpvs     = masterList.getPropertyValueList()
        mpvids   = [id(m) for m in mpvs]
        newOrder = []

        # loop through the PV objects in the slave list,
        # and build a list of indices of the corresponding
        # PV objects in the master list
        for i, spv in enumerate(slaveList.getPropertyValueList()):

            mpv = propValMap[spv]
            newOrder.append(mpvids.index(id(mpv)))

        # If the master list order has been
        # changed, re-order the slave list
        if newOrder != list(range(len(slaveList))):
            slaveList.reorder(newOrder)

        # The list order hasn't changed, so
        # this call must have been triggered
        # by a value change. Find the items
        # which have changed, and copy the
        # new value across to the slave list
        else:

            for i, (masterVal, slaveVal) in \
                enumerate(
                    zip(masterList.getPropertyValueList(),
                        slaveList .getPropertyValueList())):

                if masterVal == slaveVal: continue

                notifState = slaveVal.getNotificationState()
                validState = slaveVal.allowInvalid()
                slaveVal.disableNotification()
                slaveVal.allowInvalid(True)

                log.debug('Syncing bound PV list item '
                          '[{}] {}.{}[{}]({}) -> {}.{}[{}]({})'.format(
                              i,
                              masterList._context().__class__.__name__,
                              masterList._name,
                              id(masterList._context()),
                              masterVal.get(),
                              slaveList._context().__class__.__name__,
                              slaveList._name,
                              id(slaveList._context()),
                              slaveList.get()))

                slaveList._ignoreListItems = True

                try:
                    slaveVal.set(masterVal.get())
                    changed.append(slaveVal)
                finally:
                    slaveList._ignoreListItems = False

                slaveVal.allowInvalid(validState)
                slaveVal.setNotificationState(notifState)

    return changed


def buildBPVList(self, key, node=None, bpvSet=None):
    """Recursively builds a list of all PVs that are bound to this one, either
    directly or indirectly.

    For each PV, we also store a reference to the 'parent' PV, i.e. the PV to
    which it is directly bound, as the direct bindings are needed to
    synchronise list PVs.

    Returns two lists - the first containing bound PVs, and the second
    containing the parent for each bound PV.

    :arg self:   The root PV.

    :arg key:    A string, either ``boundPropVals`` or ``boundAttPropVals``.

    :arg node:   The current PV to begin this step of the recursive search
                 from (do not pass in on the non-recursive call).

    :arg bpvSet: A set used to prevent cycles in the depth-first search (do
                 not pass in on the non-recursive call).
    """

    boundPropVals = []
    bpvParents    = []

    if node is None:
        node = self

    # A recursive depth-first search from this
    # PV through the network of all directly
    # or indirectly bound PVs.
    #
    # We use a set of PV ids to make sure
    # that we don't add duplicates to the
    # list of PVs that need to be synced
    if bpvSet is None:
        bpvSet = set()

    bpvs = node.__dict__.get(key, {}).values()
    bpvs = [b for b in bpvs if b is not self and id(b) not in bpvSet]

    for b in bpvs:
        bpvSet.add(id(b))

    boundPropVals.extend(bpvs)
    bpvParents   .extend([node] * len(bpvs))

    for bpv in bpvs:
        childBpvs, childBpvps = buildBPVList(self, key, bpv, bpvSet)

        boundPropVals.extend(childBpvs)
        bpvParents   .extend(childBpvps)

    return boundPropVals, bpvParents


def _sync(self, atts=False, attName=None, attValue=None):
    """Called by :func:`_notify`.

    Synchronises the value or attributes of all bound ``PropertyValue``
    instances to the the value or attributes of this one.

    :arg atts:     If ``True``, the attribute with ``attName`` and ``attValue``
                   is synchronised. Otherwise, the property values are
                   synchronised.

    :arg attName:  If ``att=True``, the name of the attribute to synchronise.

    :arg attValue: If ``att=True``, the value of the attribute to synchronise.
    """

    from . import properties_value

    # This PV is already being synced
    # to some other PV - don't sync back
    if getattr(self, '_syncing', False):
        return []

    if atts: key = 'boundAttPropVals'
    else:    key = 'boundPropVals'

    boundPropVals, bpvParents = buildBPVList(self, key)

    # Sync all the values that need syncing. Store
    # a ref to each PV which was synced, but not
    # to PVs which already had the same value.
    changedPropVals = []

    # Set the syncing flag on all
    # slave PVs to prevent recursive
    # syncs back to this PV
    for bpv in boundPropVals:
        bpv._syncing = True

    try:
        for i, bpv in enumerate(boundPropVals):

            # Don't bother if the values are already equal
            if atts:
                try:
                    if bpv.getAttribute(attName) == attValue: continue
                except KeyError:
                    pass
            elif self == bpv:
                continue

            # Disable notification on the PV, as we
            # manually trigger notifications in the
            # _notify function below.
            notifState = bpv.getNotificationState()
            bpv.disableNotification()

            log.debug('Syncing bound property values ({}) '
                      '{}.{} ({}) - {}.{} ({})'.format(
                          'attributes: {} = {}'.format(attName, attValue)
                          if atts else 'values',
                          self._context.__class__.__name__,
                          self._name,
                          id(self._context()),
                          bpv._context.__class__.__name__,
                          bpv._name,
                          id(bpv._context())))

            # Normal PropertyValue object (i.e. not a PropertyValueList)
            if atts or \
               not isinstance(self, properties_value.PropertyValueList):

                # Store a reference to this PV
                changedPropVals.append((bpv, None))

                # Allow invalid values, as otherwise
                # an error may be raised.
                validState = bpv.allowInvalid()
                bpv.allowInvalid(True)

                # Sync the attribute value
                if atts: bpv.setAttribute(attName, attValue)

                # Or sync the property value
                else:    bpv.set(self.get())

                bpv.allowInvalid(validState)

            # PropertyValueList instances -
            # store a reference ot the PV list,
            # and to all list items that changed
            else:
                listItems = _syncPropValLists(bpvParents[i], bpv)
                changedPropVals.append((bpv, listItems))

            # Restore the notification state
            bpv.setNotificationState(notifState)

    finally:
        # Clear the syncing flag
        # on all slave PVs
        for bpv in boundPropVals:
            bpv._syncing = False

    # Return a list of all changed PVs back
    # to the _notify function, so it can
    # trigger notification on all of them.
    return changedPropVals


def _callAllListeners(propVals, att, name=None, value=None):
    """Calls all listeners of the given list of :class:`.PropertyValue`
    instances.

    :arg att:   If ``True``, attribute listeners are notified, otherwise
                value listeners are notified.
    :arg name:  If ``att == True``, the attribute name.
    :arg value: If ``att == True``, the attribute value.
    """

    from . import properties_value

    queued = []
    q      = properties_value.PropertyValue.queue

    # Hold the queue to inhibit any callbacks which
    # are triggered by immediate listener calls
    q.hold()

    # Get the function from a
    # properties_value.Listener
    # instance.
    def getFunc(listener):
        func = listener.function

        if isinstance(func, weakfuncref.WeakFunctionRef):
            func = func.function()

        return func

    try:
        for i, pv in enumerate(propVals):

            cListeners, cArgs = pv.prepareListeners(att, name, value)

            # If a bound PV is an item in a PV list,
            # then the listeners on the owning PV list
            # need to be called as well. We skip
            # the first PV in the propVals list, as it
            # is the source of the change.
            if (i > 0) and (not att) and (pv.getParent() is not None):
                pListeners, pArgs = pv.getParent().prepareListeners(False)
            else:
                pListeners = []
                pArgs      = None

            for listeners, args in [(cListeners, cArgs), (pListeners, pArgs)]:

                for l in listeners:

                    # The listener may have been removed/disabled
                    # due to another immediate listener
                    if not l.enabled:
                        continue

                    # Call the listener function directly
                    if l.immediate:

                        log.debug('Calling immediate mode '
                                  'listener {}'.format(l.name))
                        getFunc(l)(*args)

                    # Or add it to the queue
                    else:
                        queued.append((l, args))

    # Make sure the queue is freed
    finally:
        q.release()

    # Some listeners may have been disabled/removed
    # as the result of the execution of another
    # listener, so we only want to re-queue the ones
    # that are still active.
    queued = [(getFunc(l), l.makeQueueName(), a, {})
              for l, a in queued
              if l.enabled]

    # Some listeners referred to by weakrefs
    # may have been GC-d, in which case the
    # function reference will be None
    queued = [(f, n, a, kw) for f, n, a, kw in queued if f is not None]

    # Append any held functions on to the
    # end of the call list, so they are
    # executed after all of the listeners
    # for the original property value change
    held = q.clearHeld()
    q.callAll(queued + held)
