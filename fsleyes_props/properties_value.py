#!/usr/bin/env python
#
# properties_value.py - Definitions of the PropertyValue and
#                       PropertyValueList classes.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Definitions of the :class:`PropertyValue` and :class:`PropertyValueList`
classes.

 .. autosummary::
    :nosignatures:

    PropertyValue
    PropertyValueList


``PropertyValue`` and ``PropertyValueList`` instances are intended to be
created and managed by :class:`.PropertyBase` and :class:`.ListPropertyBase`
instances respectively, and are used to encapsulate attribute values of
:class:`.HasProperties` instances.


These class definitions are really a part of the :mod:`.properties` module -
they are separated to keep file sizes down.  However, the
:class:`.PropertyValue` class definitions have no dependence upon the
:class:`.PropertyBase` or :class:`.HasProperties` definitions.
"""


import uuid
import logging
import weakref

from collections import OrderedDict

from . import callqueue
from . import bindable

import fsl.utils.weakfuncref as weakfuncref


log = logging.getLogger(__name__)


class Listener(object):
    """The ``Listener`` class is used by :class:`PropertyValue` instances to
    manage their listeners - see :meth:`PropertyValue.addListener`.
    """
    def __init__(self, propVal, name, function, enabled, immediate):
        """Create a ``Listener``.

        :arg propVal:   The ``PropertyValue`` that owns this ``Listener``.
        :arg name:      The listener name.
        :arg function:  The callback function.
        :arg enabled:   Whether the listener is enabled/disabled.
        :arg immediate: Whether the listener is to be called immediately, or
                        via the :attr:`PropertyValue.queue`.
        """

        self.propVal   = weakref.ref(propVal)
        self.name      = name
        self.function  = function
        self.enabled   = enabled
        self.immediate = immediate


    def makeQueueName(self):
        """Returns a more descriptive name for this ``Listener``, which
        is used as its name when passed to the :class:`.CallQueue`.
        """

        ctxName = self.propVal()._context().__class__.__name__
        pvName  = self.propVal()._name

        return '{} ({}.{})'.format(self.name, ctxName, pvName)


class PropertyValue(object):
    """An object which encapsulates a value of some sort.

    The value may be subjected to casting and validation rules, and listeners
    may be registered for notification of value and validity changes.

    Notification of value and attribute listeners is performed by the
    :mod:`.bindable` module - see the :func:`.bindable.syncAndNotify` and
    :func:`.bindable.syncAndNotifyAtts` functions.
    """


    queue = callqueue.CallQueue(skipDuplicates=True)
    """A :class:`.CallQueue` instance which is shared by all
    :class:`PropertyValue` instances, and used for notifying listeners
    of value and attribute changes.

    A queue is used for notification so that listeners are notified in
    the order that values were changed.
    """


    def __init__(self,
                 context,
                 name=None,
                 value=None,
                 castFunc=None,
                 validateFunc=None,
                 equalityFunc=None,
                 preNotifyFunc=None,
                 postNotifyFunc=None,
                 allowInvalid=True,
                 parent=None,
                 **attributes):
        """Create a ``PropertyValue`` object.

        :param context:        An object which is passed as the first argument
                               to the ``validateFunc``, ``preNotifyFunc``,
                               ``postNotifyFunc``, and any registered
                               listeners. Can technically be anything, but will
                               nearly always be a :class:`.HasProperties`
                               instance.

        :param name:           Value name - if not provided, a default, unique
                               name is created.

        :param value:          Initial value.

        :param castFunc:       Function which performs type casting or data
                               conversion. Must accept three parameters - the
                               context, a dictionary containing the attributes
                               of this object, and the value to cast. Must
                               return that value, cast/converted appropriately.

        :param validateFunc:   Function which accepts three parameters - the
                               context, a dictionary containing the attributes
                               of this object, and a value. This function
                               should test the provided value, and raise a
                               :exc:`ValueError` if it is invalid.

        :param equalityFunc:   Function which accepts two values, and should
                               return ``True`` if they are equal, ``False``
                               otherwise. If not provided, the python equailty
                               operator (i.e. ``==``) is used.

        :param preNotifyFunc:  Function to be called whenever the property
                               value changes, but before any registered
                               listeners are called. See the
                               :meth:`addListener` method for details of the
                               parameters this function must accept.

        :param postNotifyFunc: Function to be called whenever the property
                               value changes, but after any registered
                               listeners are called. Must accept the same
                               parameters as the ``preNotifyFunc``.

        :param allowInvalid:   If ``False``, any attempt to set the value to
                               something invalid will result in a
                               :exc:`ValueError`. Note that this does not
                               guarantee that the property will never have an
                               invalid value, as the definition of 'valid'
                               depends on external factors (i.e. the
                               ``validateFunc``).  Therefore, the validity of
                               a value may change, even if the value itself
                               has not changed.

        :param parent:         If this PV instance is a member of a
                               :class:`PropertyValueList` instance, the latter
                               sets itself as the parent of this PV. Whenever
                               the value of this PV changes, the
                               :meth:`PropertyValueList._listPVChanged` method
                               is called.

        :param attributes:     Any key-value pairs which are to be associated
                               with this :class:`PropertyValue` object, and
                               passed to the ``castFunc`` and ``validateFunc``
                               functions. Attributes are not used by the
                               ``PropertyValue`` or ``PropertyValueList``
                               classes, however they are used by the
                               :class:`.PropertyBase` and
                               :class:`.ListPropertyBase` classes to store
                               per-instance property attributes. Listeners
                               may register to be notified when attribute
                               values change.
        """

        if name     is     None: name  = 'PropertyValue_{}'.format(id(self))
        if castFunc is not None: value = castFunc(context, attributes, value)
        if equalityFunc is None: equalityFunc = lambda a, b: a == b

        self._context                 = weakref.ref(context)
        self._validate                = validateFunc
        self._name                    = name
        self._equalityFunc            = equalityFunc
        self._castFunc                = castFunc
        self._allowInvalid            = allowInvalid
        self._attributes              = attributes.copy()
        self._changeListeners         = OrderedDict()
        self._attributeListeners      = OrderedDict()

        self.__value                  = value
        self.__valid                  = False
        self.__lastValue              = None
        self.__lastValid              = False
        self.__notification           = True

        self._preNotifyListener  = Listener(self,
                                            'prenotify',
                                            preNotifyFunc,
                                            True,
                                            True)
        self._postNotifyListener = Listener(self,
                                            'postnotify',
                                            postNotifyFunc,
                                            True,
                                            False)

        if parent is not None: self.__parent = weakref.ref(parent)
        else:                  self.__parent = None

        if not allowInvalid and validateFunc is not None:
            validateFunc(context, self._attributes, value)


    def __repr__(self):
        """Returns a string representation of this PropertyValue object."""
        return 'PV({})'.format(self.__value)


    def __str__(self):
        """Returns a string representation of this PropertyValue object."""
        return self.__repr__()


    def __hash__(self):
        return id(self)


    def __eq__(self, other):
        """Returns ``True`` if the given object has the same value as this
        instance. Returns ``False`` otherwise.
        """
        if isinstance(other, PropertyValue):
            other = other.get()
        return self._equalityFunc(self.get(), other)


    def __ne__(self, other):
        """Returns ``True`` if the given object has a different value to
        this instance, ``False`` otherwise.
        """
        return not self.__eq__(other)


    def __saltListenerName(self, name):
        """Adds a constant string to the given listener name.

        This is done for debug output, so we can better differentiate between
        listeners with the same name registered on different PV objects.
        """
        return 'PropertyValue_{}_{}'.format(self._name, name)


    def __unsaltListenerName(self, name):
        """Removes a constant string from the given listener name,
        which is assumed to have been generated by the
        :meth:`__saltListenerName` method.
        """

        salt = 'PropertyValue_{}_'.format(self._name)

        return name[len(salt):]


    def getParent(self):
        """If this ``PropertyValue`` is an item in a :class:`PropertyValueList`,
        this method returns a reference to the owning ``PropertyValueList``.
        Otherwise, this method returns ``None``.
        """
        if self.__parent is not None: return self.__parent()
        else:                         return None


    def allowInvalid(self, allow=None):
        """Query/set the allow invalid state of this value.

        If no arguments are passed, returns the current allow invalid state.
        Otherwise, sets the current allow invalid state. to the given argument.
        """
        if allow is None:
            return self._allowInvalid

        self._allowInvalid = bool(allow)


    def enableNotification(self, bound=False, att=False):
        """Enables notification of property value and attribute listeners for
        this ``PropertyValue`` object.

        :arg bound: If ``True``, notification is enabled on all other
                    ``PropertyValue`` instances that are bound to this one
                    (see the :mod:`.bindable` module). If ``False`` (the
                    default), notification is only enabled on this
                    ``PropertyValue``.

        :arg att:   If ``True``, notification is enabled on all attribute
                    listeners as well as property value listeners.
        """
        self.__notification = True

        if not bound:
            return

        bpvs = list(bindable.buildBPVList(self, 'boundPropVals')[0])

        if att:
            bpvs += list(bindable.buildBPVList(self, 'boundAttPropVals')[0])

        for bpv in bpvs:
            bpv.enableNotification()


    def disableNotification(self, bound=False, att=False):
        """Disables notification of property value and attribute listeners for
        this ``PropertyValue`` object. Notification can be re-enabled via
        the :meth:`enableNotification` or :meth:`setNotificationState` methods.


        :arg bound: If ``True``, notification is disabled on all other
                    ``PropertyValue`` instances that are bound to this one
                    (see the :mod:`.bindable` module). If ``False`` (the
                    default), notification is only disabled on this
                    ``PropertyValue``.

        :arg att:   If ``True``, notification is disabled on all attribute
                    listeners as well as property value listeners.
        """
        self.__notification = False

        if not bound:
            return

        bpvs = list(bindable.buildBPVList(self, 'boundPropVals')[0])

        if att:
            bpvs += list(bindable.buildBPVList(self, 'boundAttPropVals')[0])

        for bpv in bpvs:
            bpv.disableNotification()


    def getNotificationState(self):
        """Returns ``True`` if notification is currently enabled, ``False``
        otherwise.
        """
        return self.__notification


    def setNotificationState(self, value):
        """Sets the current notification state."""
        if value: self.enableNotification()
        else:     self.disableNotification()


    def addAttributeListener(self, name, listener, weak=True, immediate=False):
        """Adds an attribute listener for this ``PropertyValue``. The
        listener callback function must accept the following arguments:

          - ``context``:   The context associated with this ``PropertyValue``.

          - ``attribute``: The name of the attribute that changed.

          - ``value``:     The new attribute value.

          - ``name``:      The name of this ``PropertyValue`` instance.

        :param name:      A unique name for the listener. If a listener with
                          the specified name already exists, it will be
                          overwritten.

        :param listener:  The callback function.

        :param weak:      If ``True`` (the default), a weak reference to the
                          callback function is used.

        :param immediate: If ``False`` (the default), the listener is called
                          immediately; otherwise, it is called via the
                          :attr:`queue`.
        """
        log.debug('Adding attribute listener on {}.{} ({}): {}'.format(
            self._context().__class__.__name__, self._name, id(self), name))

        if weak:
            listener = weakfuncref.WeakFunctionRef(listener)

        name = self.__saltListenerName(name)
        self._attributeListeners[name] = Listener(self,
                                                  name,
                                                  listener,
                                                  True,
                                                  immediate)


    def disableAttributeListener(self, name):
        """Disables the attribute listener with the specified ``name``. """
        name = self.__saltListenerName(name)
        log.debug('Disabling attribute listener on {}: {}'.format(self._name,
                                                                  name))
        self._attributeListeners[name].enabled = False


    def enableAttributeListener(self, name):
        """Enables the attribute listener with the specified ``name``. """
        name = self.__saltListenerName(name)
        log.debug('Enabling attribute listener on {}: {}'.format(self._name,
                                                                 name))
        self._attributeListeners[name].enabled = True


    def removeAttributeListener(self, name):
        """Removes the attribute listener of the given name."""
        log.debug('Removing attribute listener on {}.{}: {}'.format(
            self._context().__class__.__name__, self._name, name))

        name     = self.__saltListenerName(name)
        listener = self._attributeListeners.pop(name, None)

        if listener is not None:

            cb = listener.function

            if isinstance(cb, weakfuncref.WeakFunctionRef):
                cb = cb.function()

            if cb is not None:
                PropertyValue.queue.dequeue(listener.makeQueueName())


    def getAttributes(self):
        """Returns a dictionary containing all the attributes of this
        ``PropertyValue`` object.
        """
        return self._attributes.copy()


    def setAttributes(self, atts):
        """Sets all the attributes of this ``PropertyValue`` object.
        from the given dictionary.
        """

        for name, value in atts.items():
            self.setAttribute(name, value)


    def getAttribute(self, name, *arg):
        """Returns the value of the named attribute.

        :arg default: If provided, the default value to use if ``name`` is not
                      an attribute. If not provided, and ``name`` is not an
                      attribute, a ``KeyError`` is raised.
        """

        nodefault = len(arg) == 0

        if nodefault: return self._attributes[name]
        else:         return self._attributes.get(name, arg[0])


    def setAttribute(self, name, value):
        """Sets the named attribute to the given value, and notifies any
        registered attribute listeners of the change.
        """
        oldVal = self._attributes.get(name, None)

        self._attributes[name] = value

        if oldVal == value: return

        log.debug('Attribute on {}.{} ({}) changed: {} = {}'.format(
            self._context().__class__.__name__,
            self._name,
            id(self),
            name,
            value))

        self.notifyAttributeListeners(name, value)

        self.revalidate()


    def prepareListeners(self, att, name=None, value=None):
        """Prepares a list of :class:`Listener` instances ready to be called,
        and a list of arguments to pass to them.

        :arg att:   If ``True``, attribute listeners are returned, otherwise
                    value listeners are returned.
        :arg name:  If ``att == True``, the attribute name.
        :arg value: If ``att == True``, the attribute value.
        """

        if not self.__notification:
            return [], []

        if att: lDict = self._attributeListeners
        else:   lDict = self._changeListeners

        allListeners = []

        for lName, listener in list(lDict.items()):

            if not listener.enabled:
                continue

            cb = listener.function

            if isinstance(cb, weakfuncref.WeakFunctionRef):
                cb = cb.function()

            # The owner of the referred function/method
            # has been GC'd - remove it
            if cb is None:

                log.debug('Removing dead listener {}'.format(lName))
                if att:
                    self.removeAttributeListener(
                        self.__unsaltListenerName(lName))
                else:
                    self.removeListener(
                        self.__unsaltListenerName(lName))
                continue

            allListeners.append(listener)

        # if we're preparing value listenres, add
        # the pre-notify and post-notify functions
        if not att:

            if self._preNotifyListener.function is not None and \
               self._preNotifyListener.enabled:
                allListeners = [self._preNotifyListener] + allListeners

            if self._postNotifyListener.function is not None and \
               self._postNotifyListener.enabled:
                allListeners = allListeners + [self._postNotifyListener]

        if att: args = self._context(), name, value, self._name
        else:   args = (self.get(), self.__valid, self._context(), self._name)

        return allListeners, args


    def notifyAttributeListeners(self, name, value):
        """Notifies all registered attribute listeners of an attribute
        changed - see the :func:`.bindable.syncAndNotifyAtts` function.
        """

        bindable.syncAndNotifyAtts(self, name, value)


    def addListener(self,
                    name,
                    callback,
                    overwrite=False,
                    weak=True,
                    immediate=False):
        """Adds a listener for this value.

        When the value changes, the listener callback function is called. The
        callback function must accept the following arguments:

          - ``value``:   The property value
          - ``valid``:   Whether the value is valid or invalid
          - ``context``: The context object passed to :meth:`__init__`.
          - ``name``:    The name of this ``PropertyValue`` instance.

        Listener names ``prenotify`` and ``postnotify`` are reserved - if
        either of these are passed in for the listener name, a :exc`ValueError`
        is raised.

        :param str name:  A unique name for this listener. If a listener with
                          the name already exists, a :exc`RuntimeError` will be
                          raised, or it will be overwritten, depending upon
                          the value of the ``overwrite`` argument.

        :param callback:  The callback function.

        :param overwrite: If ``True`` any previous listener with the same name
                          will be overwritten.

        :param weak:      If ``True`` (the default), a weak reference to the
                          callback function is retained, meaning that it
                          can be garbage-collected. If passing in a lambda or
                          inner function, you will probably want to set
                          ``weak`` to ``False``, in which case a strong
                          reference will be used.

        :param immediate: If ``False`` (the default), this listener will be
                          notified through the :class:`.CallQueue` - listeners
                          for all ``PropertyValue`` instances are queued, and
                          notified in turn. If ``True``, If ``True``, the
                          ``CallQueue`` will not be used, and this listener
                          will be notified as soon as this ``PropertyValue``
                          changes.
        """

        if name in ('prenotify', 'postnotify'):
            raise ValueError('Reserved listener name used: {}. '
                             'Use a different name.'.format(name))

        log.debug('Adding listener on {}.{}: {}'.format(
            self._context().__class__.__name__,
            self._name,
            name))

        fullName = self.__saltListenerName(name)
        prior    = self._changeListeners.get(fullName, None)

        if weak:
            callback = weakfuncref.WeakFunctionRef(callback)

        if (prior is not None) and (not overwrite):
            raise RuntimeError('Listener {} already exists'.format(name))

        elif prior is not None:
            prior.function  = callback
            prior.immediate = immediate

        else:
            self._changeListeners[fullName] = Listener(self,
                                                       fullName,
                                                       callback,
                                                       True,
                                                       immediate)


    def removeListener(self, name):
        """Removes the listener with the given name from this
        ``PropertyValue``.
        """

        # The typical stack trace of a call to this method is:
        #    someHasPropertiesObject.removeListener(...) (the original call)
        #      HasProperties.removeListener(...)
        #        PropertyBase.removeListener(...)
        #          this method
        # So to be a bit more informative, we'll examine the stack
        # and extract the (assumed) location of the original call
        if log.getEffectiveLevel() == logging.DEBUG:
            import inspect
            stack = inspect.stack()

            if len(stack) >= 4: frame = stack[ 3]
            else:               frame = stack[-1]

            srcMod  = '...{}'.format(frame[1][-20:])
            srcLine = frame[2]

            log.debug('Removing listener on {}.{}: {} ({}:{})'.format(
                self._context().__class__.__name__,
                self._name,
                name,
                srcMod,
                srcLine))

        name     = self.__saltListenerName(name)
        listener = self._changeListeners.pop(name, None)

        if listener is not None:

            # The bindable._allAllListeners does
            # funky things to the call queue,
            # so we mark this listener as disabled
            # just in case bindable tries to call
            # a removed listener.
            listener.enabled = False

            cb = listener.function

            if isinstance(cb, weakfuncref.WeakFunctionRef):
                cb = cb.function()

            if cb is not None:
                PropertyValue.queue.dequeue(listener.makeQueueName())


    def enableListener(self, name):
        """(Re-)Enables the listener with the specified ``name``."""
        name = self.__saltListenerName(name)
        log.debug('Enabling listener on {}: {}'.format(self._name, name))
        self._changeListeners[name].enabled = True


    def disableListener(self, name):
        """Disables the listener with the specified ``name``, but does not
        remove it from the list of listeners.
        """
        name = self.__saltListenerName(name)
        log.debug('Disabling listener on {}: {}'.format(self._name, name))
        self._changeListeners[name].enabled = False


    def getListenerState(self, name):
        """Returns ``True`` if the specified listener is currently enabled,
        ``False`` otherwise.

        An :exc:`AttributeError` is raised if a listener with the specified
        ``name`` does not exist.
        """

        fullName = self.__saltListenerName(name)
        listener = self._changeListeners.get(fullName, None)

        return listener.enabled


    def setListenerState(self, name, state):
        """Enables/disables the specified listener. """

        if state: self.enableListener(name)
        else:     self.disableListener(name)


    def hasListener(self, name):
        """Returns ``True`` if a listener with the given name is registered,
        ``False`` otherwise.
        """

        name = self.__saltListenerName(name)
        return name in self._changeListeners.keys()


    def setPreNotifyFunction(self, preNotifyFunc):
        """Sets the function to be called on value changes, before any
        registered listeners.
        """
        self._preNotifyListener.function = preNotifyFunc


    def setPostNotifyFunction(self, postNotifyFunc):
        """Sets the function to be called on value changes, after any
        registered listeners.
        """
        self._postNotifyListener.function = postNotifyFunc


    def getLast(self):
        """Returns the most recent property value before the current one."""
        return self.__lastValue


    def get(self):
        """Returns the current property value."""
        return self.__value


    def set(self, newValue):
        """Sets the property value.

        The property is validated and, if the property value or its validity
        has changed, any registered listeners are called through the
        :meth:`propNotify` method.  If ``allowInvalid`` was set to
        ``False``, and the new value is not valid, a :exc:`ValueError` is
        raised, and listeners are not notified.
        """

        # cast the value if necessary.
        # Allow any errors to be thrown
        if self._castFunc is not None:
            newValue = self._castFunc(self._context(),
                                      self._attributes,
                                      newValue)

        # Check to see if the new value is valid
        valid    = False
        validStr = None
        try:
            if self._validate is not None:
                self._validate(self._context(), self._attributes, newValue)
            valid = True

        except ValueError as e:

            # Oops, we don't allow invalid values.
            validStr = str(e)
            if not self._allowInvalid:
                import traceback
                log.debug('Attempt to set {}.{} to an invalid value ({}), '
                          'but allowInvalid is False ({})'.format(
                              self._context().__class__.__name__,
                              self._name,
                              newValue,
                              e), exc_info=True)
                traceback.print_stack()
                raise e

        self.__lastValue = self.__value
        self.__lastValid = self.__valid
        self.__value     = newValue
        self.__valid     = valid

        # If the value or its validity has not
        # changed, listeners are not notified
        changed = (self.__valid != self.__lastValid) or \
                  not self._equalityFunc(self.__value, self.__lastValue)

        if not changed: return

        log.debug('Value {}.{} changed: {} -> {} ({})'.format(
            self._context().__class__.__name__,
            self._name,
            self.__lastValue,
            self.__value,
            'valid' if valid else 'invalid - {}'.format(validStr)))

        # Notify any registered listeners.
        self.propNotify()


    def propNotify(self):
        """Notifies registered listeners - see the
        :func:`.bindable.syncAndNotify` function.
        """

        bindable.syncAndNotify(self)

        # If this PV is a member of a PV list,
        # tell the list that this PV has
        # changed, so that it can notify its own
        # list-level listeners of the change
        if self.__parent is not None and self.__parent() is not None:
            self.__parent()._listPVChanged(self)


    def revalidate(self):
        """Revalidates the current property value, and re-notifies any
        registered listeners if the value validity has changed.
        """
        self.set(self.get())


    def isValid(self):
        """Returns ``True`` if the current property value is valid, ``False``
        otherwise.
        """
        try: self._validate(self._context(), self._attributes, self.get())
        except: return False
        return True


class PropertyValueList(PropertyValue):
    """A ``PropertyValueList`` is a :class:`PropertyValue` instance which
    stores other :class:`PropertyValue` instance in a list. Instances of
    this class are generally managed by a :class:`.ListPropertyBase` instance.

    When created, separate validation functions may be passed in for
    individual items, and for the list as a whole. Listeners may be registered
    on individual ``PropertyValue`` instances (accessible via the
    :meth:`getPropertyValueList` method), or on the entire list.

    The values contained in this ``PropertyValueList`` may be accessed
    through standard Python list operations, including slice-based access and
    assignment, :meth:`append`, :meth:`insert`, :meth:`extend`, :meth:`pop`,
    :meth:`index`, :meth:`count`, :meth:`move`, :meth:`insertAll`,
    :meth:`removeAll`, and :meth:`reorder` (these last few are non-standard).

    Because the values contained in this list are ``PropertyValue``
    instances themselves, some limitations are present on list modifying
    operations::

      class MyObj(props.HasProperties):
        mylist = props.List(default[1, 2, 3])

      myobj = MyObj()

    Simple list-slicing modifications work as expected::

      # the value after this will be [5, 2, 3]
      myobj.mylist[0]  = 5

      # the value after this will be [5, 6, 7]
      myobj.mylist[1:] = [6, 7]

    However, modifications which would change the length of the list are not
    supported::

      # This will result in an IndexError
      myobj.mylist[0:2] = [6, 7, 8]

    The exception to this rule concerns modifications which would replace
    every value in the list::

      # These assignments are equivalent
      myobj.mylist[:] = [1, 2, 3, 4, 5]
      myobj.mylist    = [1, 2, 3, 4, 5]

    While the simple list modifications described above will change the
    value(s) of the existing ``PropertyValue`` instances in the list,
    modifications which replace the entire list contents will result in
    existing ``PropertyValue`` instances being destroyed, and new ones
    being created. This is a very important point to remember if you have
    registered listeners on individual ``PropertyValue`` items.

    A listener registered on a ``PropertyValueList`` will be notified
    whenever the list is modified (e.g. additions, removals, reorderings), and
    whenever any individual value in the list changes. Alternately, listeners
    may be registered on the individual ``PropertyValue`` instances (which
    are accessible through the :meth:`getPropertyValueList` method) to be
    nofitied of changes to those values only.

    There are some interesting type-specific subclasses of the
    ``PropertyValueList``, which provide additional functionality:

      - The :class:`.PointValueList`, for :class:`.Point` properties.

      - The :class:`.BoundsValueList`, for :class:`.Bounds` properties.
    """

    def __init__(self,
                 context,
                 name=None,
                 values=None,
                 itemCastFunc=None,
                 itemEqualityFunc=None,
                 itemValidateFunc=None,
                 listValidateFunc=None,
                 itemAllowInvalid=True,
                 preNotifyFunc=None,
                 postNotifyFunc=None,
                 listAttributes=None,
                 itemAttributes=None):
        """Create a ``PropertyValueList``.

        :param context:          See :meth:`PropertyValue.__init__`.

        :param name:             See :meth:`PropertyValue.__init__`.

        :param values:           Initial list values.

        :param itemCastFunc:     Function which casts a single list item.

        :param itemEqualityFunc: Function which tests equality of two values.

        :param itemValidateFunc: Function which validates a single list item.

        :param listValidateFunc: Function which validates the list as a whole.

        :param itemAllowInvalid: Whether items are allowed to containg
                                 invalid values.

        :param preNotifyFunc:    See :meth:`PropertyValue.__init__`.

        :param postNotifyFunc:   See :meth:`PropertyValue.__init__`.

        :param listAttributes:   Attributes to be associated with this
                                 ``PropertyValueList``.

        :param itemAttributes:   Attributes to be associated with new
                                 ``PropertyValue`` items added to
                                 the list.
        """
        if name is None: name = 'PropertyValueList_{}'.format(id(self))

        if listAttributes is None: listAttributes = {}

        def itemEquals(a, b):
            if isinstance(a, PropertyValue): a = a.get()
            if isinstance(b, PropertyValue): b = b.get()

            if itemEqualityFunc is not None: return itemEqualityFunc(a, b)
            else:                            return a == b

        listValid = None
        if listValidateFunc is not None:
            def listValid(ctx, atts, value):
                value = list(value)
                for i, v in enumerate(value):
                    if isinstance(v, PropertyValue):
                        value[i] = v.get()
                return listValidateFunc(ctx, atts, value)

        # The list as a whole must be allowed to contain
        # invalid values because, if an individual
        # PropertyValue item value changes, there is no
        # nice way to propagate those changes on to other
        # (dependent) items without the list as a whole
        # being validated first, and errors being raised.
        PropertyValue.__init__(
            self,
            context,
            name=name,
            allowInvalid=True,
            validateFunc=listValid,
            preNotifyFunc=preNotifyFunc,
            postNotifyFunc=postNotifyFunc,
            **listAttributes)

        # These attributes are passed to the PropertyValue
        # constructor whenever a new item is added to the list
        self._itemCastFunc     = itemCastFunc
        self._itemValidateFunc = itemValidateFunc
        self._itemEqualityFunc = itemEquals
        self._itemAllowInvalid = itemAllowInvalid
        self._itemAttributes   = itemAttributes

        # Internal flag used in the __setitem__
        # and _listPVChanged methods indicating
        # that notifications from list items
        # should be temporarily ignored. This
        # is intended for internal use only, and
        # may change in the future.
        self._ignoreListItems  = False

        # The list of PropertyValue objects.
        if values is not None: values = [self.__newItem(v) for v in values]
        else:                  values = []

        PropertyValue.set(self, values)


    def __eq__(self, other):
        """Retuns ``True`` if the given object contains the same values as
        this instance, ``False`` otherwise.
        """

        if other is None:
            return False

        if len(self) != len(other):
            return False

        return all([self._itemEqualityFunc(ai, bi)
                    for ai, bi
                    in zip(self[:], other[:])])


    def getPropertyValueList(self):
        """Return (a copy of) the underlying property value list, allowing
        access to the ``PropertyValue`` instances which manage each list
        item.
        """
        return list(PropertyValue.get(self))


    def get(self):
        """Overrides :meth:`PropertyValue.get`. Returns this
        ``PropertyValueList`` object.
        """
        return self


    def set(self, newValues):
        """Overrides :meth:`PropertyValue.set`.

        Sets the values stored in this ``PropertyValueList``. If the
        length of the ``newValues`` argument does not match the current list
        length,  an :exc:`IndexError` is raised.
        """

        if self._itemCastFunc is not None:
            newValues = [self._itemCastFunc(
                self._context(),
                self._itemAttributes,
                v) for v in newValues]

        self[:] = newValues


    def __newItem(self, item):
        """Called whenever a new item is added to the list.  Encapsulate the
        given item in a ``PropertyValue`` instance.
        """

        if self._itemAttributes is None: itemAtts = {}
        else:                            itemAtts = self._itemAttributes

        propVal = PropertyValue(
            self._context(),
            name='{}_Item'.format(self._name),
            value=item,
            castFunc=self._itemCastFunc,
            allowInvalid=self._itemAllowInvalid,
            equalityFunc=self._itemEqualityFunc,
            validateFunc=self._itemValidateFunc,
            parent=self,
            **itemAtts)

        return propVal


    def getLast(self):
        """Overrides :meth:`PropertyValue.getLast`. Returns the most
        recent list values.
        """
        lastVal = PropertyValue.getLast(self)

        if lastVal is None: return None
        else:               return [pv.get() for pv in lastVal]


    def _listPVChanged(self, pv):
        """This function is called by list items when their value changes.
        List-level listeners are notified of the change. See the
        :meth:`PropertyValue.propNotify` method.
        """

        if self._ignoreListItems:
            return

        log.debug('List item {}.{} changed ({}) - notifying '
                  'list-level listeners ({})'.format(
                      self._context().__class__.__name__,
                      self._name,
                      id(self._context()),
                      pv,
                      self[:]))
        self.propNotify()


    def __getitem__(self, key):
        vals = [pv.get() for pv in PropertyValue.get(self)]
        return vals.__getitem__(key)

    def __len__(     self):
        return self[:].__len__()
    def __repr__(    self):
        return self[:].__repr__()
    def __str__(     self):
        return self[:].__str__()
    def __iter__(    self):
        return self[:].__iter__()
    def __contains__(self, item):
        return self[:].__contains__(item)
    def index(       self, item):
        return self[:].index(item)
    def count(       self, item):
        return self[:].count(item)


    def insert(self, index, item):
        """Inserts the given item before the given index. """

        propVals = self.getPropertyValueList()
        propVals.insert(index, self.__newItem(item))
        PropertyValue.set(self, propVals)


    def insertAll(self, index, items):
        """Inserts all of the given items before the given index."""

        propVals = self.getPropertyValueList()
        propVals[index:index] = [self.__newItem(i) for i in items]
        PropertyValue.set(self, propVals)


    def append(self, item):
        """Appends the given item to the end of the list."""

        propVals = self.getPropertyValueList()
        propVals.append(self.__newItem(item))
        PropertyValue.set(self, propVals)


    def extend(self, iterable):
        """Appends all items in the given iterable to the end of the list."""

        propVals = self.getPropertyValueList()
        propVals.extend([self.__newItem(i) for i in iterable])
        PropertyValue.set(self, propVals)


    def pop(self, index=-1):
        """Remove and return the specified value in the list (default:
        last).
        """

        propVals      = self.getPropertyValueList()
        poppedPropVal = propVals.pop(index)
        PropertyValue.set(self, propVals)
        return poppedPropVal.get()


    def move(self, from_, to):
        """Move the item from 'from\_' to 'to'."""

        propVals = self.getPropertyValueList()
        propVals.insert(to, propVals.pop(from_))
        PropertyValue.set(self, propVals)


    def remove(self, value):
        """Remove the first item in the list with the specified value. """

        # delegates to __delitem__, defined below
        del self[self.index(value)]


    def removeAll(self, values):
        """Removes the first occurrence in the list of all of the specified
        values.
        """

        propVals = self.getPropertyValueList()
        listVals = [pv.get() for pv in propVals]

        for v in values:
            propVals.pop(listVals.index(v))

        PropertyValue.set(self, propVals)


    def reorder(self, idxs):
        """Reorders the list according to the given sequence of indices."""

        idxs = list(idxs)

        if list(sorted(idxs)) != list(range(len(self))):
            raise ValueError('Indices ({}) must '
                             'cover the list range '
                             '([0..{}])'.format(idxs, len(self) - 1))

        if idxs == list(range(len(self))):
            return

        propVals = self.getPropertyValueList()
        propVals = [propVals[i] for i in idxs]

        PropertyValue.set(self, propVals)


    def __setitem__(self, key, values):
        """Sets the value(s) of the list at the specified index/slice."""

        if isinstance(key, slice):
            indices = list(range(*key.indices(len(self))))
            if len(indices) != len(self) and \
               len(indices) != len(values):
                raise IndexError(
                    'PropertyValueList does not support complex slices')

        elif isinstance(key, int):
            indices = [key]
            values  = [values]
        else:
            raise IndexError('Invalid key type')

        # Replacement of all items in list
        if len(indices) == len(self) and \
           len(indices) != len(values):

            notifState = self.getNotificationState()
            self.disableNotification()
            del self[:]
            self.setNotificationState(notifState)
            self.extend(values)
            return

        # prepare the new values
        propVals    = self.getPropertyValueList()
        oldVals     = [pv.get() for pv in propVals]
        changedVals = [False] * len(self)

        # Update the PV instances that
        # correspond to the new values,
        # but suppress notification on them
        self._ignoreListItems = True

        try:
            for idx, val in zip(indices, values):

                propVal    = propVals[idx]
                notifState = propVal.getNotificationState()

                propVal.disableNotification()
                propVal.set(val)
                propVal.setNotificationState(notifState)

                changedVals[idx] = not self._itemEqualityFunc(
                    propVal.get(), oldVals[idx])

            # Notify list-level and item-level listeners
            # if any values in the list were changed
            if any(changedVals):

                log.debug('Notifying list-level listeners ({}.{} {})'.format(
                    self._context().__class__.__name__,
                    self._name,
                    id(self._context())))

                self.propNotify()

                log.debug('Notifying item-level listeners ({}.{} {})'.format(
                    self._context().__class__.__name__,
                    self._name,
                    id(self._context())))

                for idx in indices:
                    if changedVals[idx]:
                        propVals[idx].propNotify()

        finally:
            self._ignoreListItems = False


    def __delitem__(self, key):
        """Remove items at the specified index/slice from the list."""

        propVals = self.getPropertyValueList()
        propVals.__delitem__(key)
        PropertyValue.set(self, propVals)


def safeCall(func, *args, **kwargs):
    """This function is may be used to "safely" run a function which may
    trigger ``PropertyValue`` notifications. Any notifications are queued
    and executed in the correct order.
    """
    name = uuid.uuid4()
    PropertyValue.queue.call(func, name, *args, **kwargs)
