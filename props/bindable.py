#!/usr/bin/env python
#
# bindable.py - This module adds functionality to the HasProperties class
# to allow properties from different instances to be bound to each other.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""The :mod:`bindable` module adds functionality to the
:class:`~props.properties.HasProperties` class to allow properties from
different instances to be bound to each other.

The logic defined in this module is separated purely to keep the
:mod:`props.properties` and :mod:`props.properties_value` module file sizes
down.

The :func:`bindProps`, :func:`unbindProps`, and :func:`isBound` functions
defined in this module are added (monkey-patched) as methods of the
:class:`~props.properties.HasProperties` class.

The :func:`notify` and :func:`notifyAttributeListeners` functions replace
the :class:`~props.properties_value.PropertyValue` methods of the same
names.
"""

import logging
import weakref

import properties
import properties_value


log = logging.getLogger(__name__)


class Bidict(object):
    """A bare-bones bi-directional dictionary, used for binding
    :class:`~props.properties_value.PropertyValueList` instances -
    see the :func:`_bindListProps` and :func:`_boundsListChanged`
    functions.
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
    
    def __getitem__(self, key): return self._thedict.__getitem__(key)
    def __repr__(   self):      return self._thedict.__repr__()
    def __str__(    self):      return self._thedict.__str__() 

    
def bindProps(self,
              propName,
              other,
              otherPropName=None,
              bindval=True,
              bindatt=True,
              unbind=False):
    """Binds the properties specified by ``propName``  and
    ``otherPropName`` such that changes to one are applied
    to the other.

    :arg str propName:        The name of a property on this
                              :class:`HasProperties` instance.
    
    :arg HasProperties other: Another :class:`HasProperties` instance.
    
    :arg str otherPropName:   The name of a property on ``other`` to
                              bind to. If ``None`` it is assumed that
                              there is a property on ``other`` called
                              ``propName``.

    :arg bindval:             If ``True`` (the default), property values
                              are bound. This parameter is ignored for
                              list properties.

    :arg bindatt:             If ``True`` (the default), property attributes
                              are bound.  For list properties, this parameter
                              applies to the list values, not to the list
                              itself.

    :arg unbind:              If ``True``, the properties are unbound.
                              See the :meth:`unbindProps` method.
    """

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
    """Unbinds two properties previously bound via a call to
    :meth:`bindProps`. 
    """
    self.bindProps(propName,
                   other,
                   otherPropName,
                   bindval=bindval,
                   bindatt=bindatt,
                   unbind=True)


def isBound(self, propName, other, otherPropName=None):
    """Returns ``True`` if the specified property is bound to the
    other :class:`HasProperties` object, ``False`` otherwise.
    """
    
    if otherPropName is None: otherPropName = propName

    myProp       = self     .getProp(   propName)
    otherProp    = other    .getProp(   otherPropName)
    myPropVal    = myProp   .getPropVal(self)
    otherPropVal = otherProp.getPropVal(other)

    myBoundPropVals    = myPropVal   .__dict__.get('boundPropVals', {})
    otherBoundPropVals = otherPropVal.__dict__.get('boundPropVals', {})

    return (otherPropVal in myBoundPropVals and
            myPropVal    in otherBoundPropVals)
    

def _bindProps(self,
               myProp,
               other,
               otherProp,
               bindval=True,
               bindatt=True,
               unbind=False):
    """Binds two :class:`~props.properties_value.PropertyValue` instances
    together. See the :func:`bindProps` function for
    details on the parametes.

    The :meth:`_bindListProps` method is used to bind two
    :class:`~props.properties_value.PropertyValueList` instances.
    """

    myPropVal    = myProp   .getPropVal(self)
    otherPropVal = otherProp.getPropVal(other)

    if not unbind:
        allow = myPropVal.allowInvalid()
        myPropVal.allowInvalid(True)

        if bindatt: myPropVal.setAttributes(otherPropVal.getAttributes())
        if bindval: myPropVal.set(          otherPropVal.get())
        
        myPropVal.allowInvalid(allow)
        
    _bindPropVals(myPropVal,
                  otherPropVal,
                  val=bindval,
                  att=bindatt,
                  unbind=unbind)


def _bindListProps(self,
                   myProp,
                   other,
                   otherProp,
                   bindatt=True,
                   unbind=False):
    """Binds two :class:`~props.properties_value.PropertyValueList`
    instances together. See the :func:`bindProps` function for
    details on the parametes.
    """

    myPropVal    = myProp   .getPropVal(self)
    otherPropVal = otherProp.getPropVal(other)

    # TODO You're almost certainly not handling
    # unbind=True properly in this code

    # Inhibit list-level notification due to item
    # changes during the initial sync - we'll
    # manually do a list-level notification after
    # all the list values have been synced
    notifState = myPropVal.getNotificationState()
    myPropVal.disableNotification()
    
    # Force the two lists to have
    # the same number of elements
    if not unbind:
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
        _bindPropVals(myItem,
                      otherItem,
                      val=False,
                      att=bindatt,
                      unbind=unbind)
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
                    _notifyAttributeListeners(myItem, name, val) 
            
            _notify(myItem)

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
    
    _bindPropVals(myPropVal, otherPropVal, unbind=unbind)

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
        _notifyAttributeListeners(myPropVal, name, val)
        
    _notify(myPropVal)


def _bindPropVals(myPropVal,
                  otherPropVal,
                  val=True,
                  att=True,
                  unbind=False):
    """Binds two :class:`~props.properties_value.PropertyValue`
    instances together such that when the value of one changes,
    the other is changed. Attributes are also bound between the
    two instances.
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
                  val,
                  att,
                  myPropVal._context.__class__.__name__,
                  myPropVal._name,
                  id(myPropVal),
                  otherPropVal._context.__class__.__name__,
                  otherPropVal._name,
                  id(otherPropVal)))

    if val:
        if unbind:
            myBoundPropVals   .pop(id(other))
            otherBoundPropVals.pop(id(mine))
        else:
            myBoundPropVals[   id(other)] = other
            otherBoundPropVals[id(mine)]  = mine
        
    if att:
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
    """Called when one of a pair of bound
    :class:`~props.properties_value.PropertyValueList` instances changes.
    
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
                _bindPropVals(mpv, spv, val=False)

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
        mpvids   = map(id, mpvs)
        newOrder = []

        # loop through the PV objects in the slave list,
        # and build a list of indices of the corresponding
        # PV objects in the master list
        for i, spv in enumerate(slaveList.getPropertyValueList()):

            mpv = propValMap[spv]
            newOrder.append(mpvids.index(id(mpv)))

        # If the master list order has been
        # changed, re-order the slave list
        if newOrder != range(len(slaveList)):
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
                          '[{}] {}.{}({}) -> {}.{}({})'.format(
                              i,
                              masterList._context.__class__.__name__,
                              masterList._name,
                              masterVal.get(),
                              slaveList._context.__class__.__name__,
                              slaveList._name,
                              slaveList.get())) 
 
                slaveVal.set(masterVal.get())
                changed.append(slaveVal)

                slaveVal.allowInvalid(validState)
                slaveVal.setNotificationState(notifState)

    return changed


def _buildBPVList(self, key, node=None, bpvSet=None):
    """Used by the :func:`_sync` method.

    Recursively builds a list of all PVs that are bound to this one, either
    directly or indirectly.  For each PV, we also store a reference to the
    'parent' PV, i.e. the PV to which it is directly bound, as the direct
    bindings are needed to synchronise list PVs.

    Returns two lists - the first containing bound PVs, and the second
    containing the parent for each bound PV.
    
    :arg self:   The root PV

    :arg key:    Either ``boundPropVals`` or ``boundAttPropVals``

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
    bpvs = filter(lambda b: b is not self and id(b) not in bpvSet, bpvs)
        
    for b in bpvs:
        bpvSet.add(id(b))
            
    boundPropVals.extend(bpvs)
    bpvParents   .extend([node] * len(bpvs))

    for bpv in bpvs:
        childBpvs, childBpvps = _buildBPVList(self, key, bpv, bpvSet)

        boundPropVals.extend(childBpvs)
        bpvParents   .extend(childBpvps)

    return boundPropVals, bpvParents
    

def _sync(self, atts=False, attName=None, attValue=None):
    """
    """

    # This PV is already being synced 
    # to some other PV - don't sync back
    if getattr(self, '_syncing', False):
        return []


    if atts: key = 'boundAttPropVals'
    else:    key = 'boundPropVals'

    boundPropVals, bpvParents = _buildBPVList(self, key)

    # Sync all the values that need syncing. Store
    # a ref to each PV which was synced, but not
    # to PVs which already had the same value.
    changedPropVals = []
    for i, bpv in enumerate(boundPropVals):

        # Don't bother if the values are already equal
        if atts:
            try:
                if bpv.getAttribute(attName) == attValue: continue
            except KeyError:
                pass 
        elif self == bpv:
            continue

        # Set the syncing flag to prevent
        # recursive syncs back to this PV
        bpv._syncing = True

        # Disable notification on the PV, as we
        # manually trigger notifications in the
        # _notify function below. 
        notifState = bpv.getNotificationState() 
        bpv.disableNotification()

        log.debug('Syncing bound property values ({}) '
                  '{}.{} ({}) - {}.{} ({})'.format(
                      'attributes' if atts else 'values',
                      self._context.__class__.__name__,
                      self._name,
                      id(self._context),
                      bpv._context.__class__.__name__,
                      bpv._name,
                      id(bpv._context)))        

        # Normal PropertyValue object (i.e. not a PropertyValueList)
        if atts or not isinstance(self, properties_value.PropertyValueList):

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

        # Restore the notification state,
        # and remove the syncing flag
        bpv.setNotificationState(notifState)
        bpv._syncing = False

    # Return a list of all changed PVs back
    # to the _notify function, so it can
    # trigger notification on all of them.
    return changedPropVals


def _notify(self):
    """This method replaces :meth:`.PropertyValue.notify`. It ensures that
    bound :class:`.ProperyValue` objects are synchronised to have the same
    value, before any registered listeners are notified.
    """

    boundPropVals = _sync(self)

    # Now that the master-slave values are synced,
    # call the real PropertyValue.notify method
    self._orig_notify()

    # Call the registered property listeners 
    # of any slave PVs which changed value
    for i, (bpv, listItems) in enumerate(boundPropVals):

        # Normal PropertyValue objects
        if not isinstance(bpv, properties_value.PropertyValueList):
            bpv._orig_notify()

        # PropertyValueList objects -
        # notify for each list item,
        # and then notify at the list
        # level
        else:
            listNotifState = bpv.getNotificationState()
            bpv.disableNotification()

            # Call the notify method on any individual
            # list items which changed value
            for li in listItems:
                li._orig_notify()

            # Notify any list-level
            # listeners on the slave list
            bpv.setNotificationState(listNotifState)
            bpv._orig_notify()


def _notifyAttributeListeners(self, name, value):
    """This method replaces the
    :meth:`~props.properties_value.PropertyValue.notifyAttributeListeners`
    method. It ensures that the attributes of any bound
    :class:`~props.properties_value.PropertyValue` instances are synchronised
    before any attribute listeners are notified.
    """
    
    boundPropVals = _sync(self, True, name, value)

    # Notify the attribute listeners of the master
    # PV, and then of any slave PVs for which the
    # attribute changed value
    self._orig_notifyAttributeListeners(name, value)
    
    #
    # TODO what if the attribute change caused
    # a change to the property value?
    # 
    for bpv, _ in boundPropVals:
        bpv._orig_notifyAttributeListeners(name, value)

                         
# Patch the HasPropertyies and PropertyValue
properties.HasProperties.bindProps   = bindProps
properties.HasProperties.unbindProps = unbindProps
properties.HasProperties.isBound     = isBound

properties_value.PropertyValue._orig_notify = \
    properties_value.PropertyValue.notify
properties_value.PropertyValue._orig_notifyAttributeListeners = \
    properties_value.PropertyValue.notifyAttributeListeners

properties_value.PropertyValue.notify                   = _notify
properties_value.PropertyValue.notifyAttributeListeners = \
    _notifyAttributeListeners
