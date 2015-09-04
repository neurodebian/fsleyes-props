#!/usr/bin/env python
#
# properties.py - Python descriptor framework.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Python descriptor framework.

This module defines the :class:`PropertyBase`, :class:`ListPropertyBase`,
which form the basis for defining class properties; and the
:class:`HasProperties` class, which is intended to be sub-classed by
application code.

 .. autosummary::
    :nosignatures:

    HasProperties
    PropertyBase
    ListPropertyBase
"""

import weakref
import logging


log = logging.getLogger(__name__)


class _InstanceData(object):
    """An ``_InstanceData`` object is created for every ``PropertyBase``
    object of a ``HasProperties`` instance. It stores references to the 
    instance and the associated :class:`.PropertyValue` instance.
    """
    
    def __init__(self, instance, propVal):
        self.instance = weakref.ref(instance)
        self.propVal  = propVal


class DisabledError(Exception):
    """A ``DisabledError`` is raised when an attempt is made to assign
    a value to a disabled property. See the :meth:`PropertyBase.enable`
    and :meth:`PropertyBase.disable` methods.
    """
    pass

        
class PropertyBase(object):
    """The base class for properties.

    For every ``HasProperties`` instance which has this ``PropertyBase``
    object as a property, one ``_InstanceData`` object is created and attached
    as an attribute of the ``HasProperties`` object.
    
    One important point to note is that a ``PropertyBase`` object may exist
    without being bound to a ``HasProperties`` instance (in which case it will
    not create or manage any ``PropertyValue`` instances). This is useful
    if you just want validation functionality via the :meth:`validate`,
    :meth:`getConstraint` and :meth:`setConstraint` methods, passing in
    ``None`` for the instance parameter. Nothing else will work properly
    though.

    Several subclasses are defined in the :mod:`.properties_types` module.
    All subclasses should:

      - Ensure that the superclass :meth:`__init__` is called.

      - Override the :meth:`validate` method to implement any built in
        validation rules, ensuring that the the superclass implementation
        is called first (see the :class:`.Number` property for an example).

      - Override the :meth:`cast` method for implicit casting/conversion logic
        (see the :class:`.Boolean` property for an example).
    """

    def __init__(self,
                 default=None,
                 validateFunc=None,
                 equalityFunc=None,
                 required=False,
                 allowInvalid=True,
                 **constraints):
        """Define a ``PropertyBase`` property.
        
        :param default:       Default/initial value.
        
        :param bool required: Boolean determining whether or not this
                              property must have a value. May alternately
                              be a function which accepts one parameter,
                              the owning ``HasProperties`` instance,
                              and returns ``True`` or ``False``.
        
        :param validateFunc:  Custom validation function. Must accept three
                              parameters: a reference to the ``HasProperties``
                              instance, the owner of this property; a
                              dictionary containing the constraints for this
                              property; and the new property value. Should
                              return ``True`` if the property value is valid,
                              ``False`` otherwise.

        :param equalityFunc:  Function for testing equality of two values. 
        
        :param allowInvalid:  If ``False``, a :exc:`ValueError` will be
                              raised on all attempts to set this property
                              to an invalid value. This does not guarantee
                              that the property value will never be
                              invalid - see caveats in the
                              :class:`~props.properties_value.PropertyValue`
                              documentation.
        
        :param constraints:   Type specific constraints used to test
                              validity - passed to the
                              :meth:`.PropertyValue.__init__` method as
                              its ``attributes``.
        """

        constraints['default'] = default
        constraints['enabled'] = constraints.get('enabled', True)

        # A _label is added to this dict by the
        # PropertyOwner metaclass for each new
        # HasProperties class that is defined
        self._label              = {}
        
        self._required           = required
        self._validateFunc       = validateFunc
        self._equalityFunc       = equalityFunc
        self._allowInvalid       = allowInvalid
        self._defaultConstraints = constraints


    def __copy__(self):
        """Returns a copy of this :class:`PropertyBase` instance.
        
        NOTE: This has not been rigorously tested.
        """
        newProp = type(self)()
        newProp.__dict__.update(self.__dict__)

        # This is the critical step - make sure
        # that the class labels from this instance
        # are not copied across to the new instance
        newProp._label = {}

        # Give the new object an independent
        # defaultConstraint dictionary
        newProp._defaultConstraints = dict(newProp._defaultConstraints)
        
        return newProp

        
    def _setLabel(self, cls, label):
        """Sets the property label for the given class. A :exc:`RuntimeError`
        is raised if a label already exists for the given class.
        """
        
        if cls in self._label:
            raise RuntimeError('The {} instance assigned to {}.{} is '
                               'already present as {}.{}. A PropertyBase '
                               'instance may only be present on a class '
                               'once. Declare a new instance.'.format(
                                   self.__class__.__name__,
                                   cls.__name__,
                                   label,
                                   cls.__name__,
                                   self._label[cls]))
        
        self._label[cls] = label


    def getLabel(self, instance):
        """Returns the property label for the given instance (more
        specifically, for the class of the given instance), or ``None``
        if no such label has been defined.
        """
        if instance is None: return None
        return self._label.get(type(instance), None)

    
    def enable(self, instance):
        """Enables this property for the given :class:`HasProperties`
        instance.

        See the :meth:`disable` method for more details.
        """
        propVal = self.getPropVal(instance)
        propVal.setAttribute('enabled', True)

        
    def disable(self, instance):
        """Disables this property for the given :class:`HasProperties`
        instance.

        An attempt to set the value of a disabled property will result in a
        :class:`DisabledError`. This behaviour can be circumvented by dealing
        directly with the underlying :class:`.PropertyValue` object.

        Changes to the enabled state of a property may be detected by
        registering an attribute listener (see
        :meth:`.PropertyValue.addAttributeListener`) and listening for changes
        to the ``enabled`` attribute.
        """
        propVal = self.getPropVal(instance)
        propVal.setAttribute('enabled', False) 


    def isEnabled(self, instance):
        """Returns ``True``if this property is enabled for the given
        :class:`HasProperties` instance, ``False`` otherwise.

        See the :meth:`disable` method for more details.
        """
        propVal = self.getPropVal(instance)
        return propVal.getAttribute('enabled')

    
    def addListener(self,
                    instance,
                    name,
                    callback,
                    overwrite=False,
                    weak=True):
        """Register a listener with the ``PropertyValue`` object managed
        by this property. See :meth:`.PropertyValue.addListener`.
        
        :param instance:  The ``HasProperties`` instance on which the
                          listener is to be registered.
        """
        self._getInstanceData(instance).propVal.addListener(
            name, callback, overwrite=overwrite, weak=weak)
        
        
    def removeListener(self, instance, name):
        """De-register the named listener from the ``PropertyValue`` object
        managed by this property.
        """
        instData = self._getInstanceData(instance)
        
        if instData is None: return
        else:                instData.propVal.removeListener(name)

        
    def getConstraint(self, instance, constraint):
        """Returns the value of the named constraint for the specified
        ``HasProperties`` instance, or the default constraint value if
        instance is ``None``.
        """
        instData = self._getInstanceData(instance)
        
        if instData is None: return self._defaultConstraints[constraint]
        else:                return instData.propVal.getAttribute(constraint)


    def setConstraint(self, instance, constraint, value):
        """Sets the value of the named constraint for the specified
        ``HasProperties`` instance, or the default value if instance
        is ``None``.
        """

        instData = self._getInstanceData(instance)

        if instData is None: oldVal = self._defaultConstraints[constraint]
        else:                oldVal = instData.propVal.getAttribute(constraint)

        if value == oldVal: return

        log.debug('Changing {} constraint on {}: {} = {}'.format(
            self.getLabel(instance),
            'default' if instance is None else 'instance',
            constraint,
            value))

        if instData is None: self._defaultConstraints[constraint] = value
        else:                instData.propVal.setAttribute(constraint, value)


    def getPropVal(self, instance):
        """Return the :class:`.PropertyValue` instance(s) for this property,
        associated with the given ``HasProperties`` instance, or ``None``
        if there is no value for the given instance.
        """
        instData = self._getInstanceData(instance)
        if instData is None: return None
        return instData.propVal


    def _getInstanceData(self, instance):
        """Returns the :class:`_InstanceData` object for the given
        ``HasProperties`` instance, or ``None`` if there is no
        ``_InstanceData`` for the given instance. An ``_InstanceData``
        object, which provides a binding between a ``PropertyBase``
        object and a ``HasProperties`` instance, is created by that
        ``HasProperties`` instance when it is created (see
        :meth:`HasProperties.__new__`).
        """
        if instance is None: return None
        return instance.__dict__.get(self.getLabel(instance), None)

        
    def _makePropVal(self, instance):
        """Creates and returns a ``PropertyValue`` object for the given
        ``HasProperties`` instance.  
        """
        default = self._defaultConstraints.get('default', None)
        return PropertyValue(instance,
                             name=self.getLabel(instance),
                             value=default,
                             castFunc=self.cast,
                             validateFunc=self.validate,
                             equalityFunc=self._equalityFunc,
                             allowInvalid=self._allowInvalid,
                             **self._defaultConstraints)

    
    def validate(self, instance, attributes, value):
        """Called when an attempt is made to set the property value on the
        given instance.

        Called by ``PropertyValue`` objects when their value changes. The sole
        purpose of this method is to determine whether a given value is valid
        or invalid; it should not do anything else. In particular, it should
        not modify any other property values on the instance, as bad things
        will probably happen.
        
        If the given value is invalid, subclass implementations should raise a
        :exc:`ValueError` containing a useful message as to why the value is
        invalid. Otherwise, they should not return any value.  The default
        implementation does nothing, unless a custom validate function, and/or
        ``required=True``, was passed to the constructor. If ``required`` is
        ``True``, and the value is ``None``, a :exc:`ValueError` is raised. If
        a custom validate function was set, it is called and, if it returns
        ``False``, a :exc:`ValueError` is raised. It may also raise a
        :exc:`ValueError` of its own for invalid values.

        Subclasses which override this method should therefore call this
        superclass implementation in addition to performing their own
        validation.

        :param instance:        The ``HasProperties`` instance which
                                owns this ``PropertyBase`` instance,
                                or ``None`` for an unbound property value.
        
        :param dict attributes: Attributes of the ``PropertyValue`` object,
                                which are used to store type-specific
                                constraints for ``PropertyBase``
                                subclasses.
        
        :param value:           The value to be validated.
        """

        # a value is required
        if (self._required is not None) and (value is None):

            # required may either be a boolean value
            if isinstance(self._required, bool):
                if self._required:
                    raise ValueError('A value is required')

            # or a function
            elif self._required(instance):
                raise ValueError('A value is required')

        # a custom validation function has been provided
        if self._validateFunc is not None:
            if not self._validateFunc(instance, attributes, value):
                raise ValueError('Value does not meet custom validation rules')

        
    def cast(self, instance, attributes, value):
        """This method is called when a value is assigned to this
        ``PropertyBase`` instance through a ``HasProperties`` attribute
        access. The default implementaton just returns the given value.
        Subclasses may override this method to perform any required implicit
        casting or conversion rules.
        """
        return value
 
        
    def revalidate(self, instance):
        """Forces validation of this property value, for the current instance.
        This will result in any registered listeners being notified, but only
        if the validity of the value has changed.
        """

        propVal = self.getPropVal(instance)
        propVal.revalidate()

            
    def __get__(self, instance, owner):
        """If called on the ``HasProperties`` class, and not on an instance,
        returns this ``PropertyBase`` object. Otherwise, returns the value
        contained in the ``PropertyValue`` object which is attached to the
        instance.
        """

        if instance is None:
            return self
            
        instData = self._getInstanceData(instance)
        return instData.propVal.get()

        
    def __set__(self, instance, value):
        """Set the value of this property, as attached to the given instance,
        to the given value.
        """
        
        propVal = self.getPropVal(instance)

        if not propVal.getAttribute('enabled'):
            raise DisabledError('Property {}.{} is disabled'.format(
                instance.__class__.__name__,
                self.getLabel(instance)))
        
        propVal.set(value)


class ListPropertyBase(PropertyBase):
    """A :class:`PropertyBase` for properties which encapsulate more than
    one value.
    """
    
    def __init__(self, listType, **kwargs):
        """Define a ``ListPropertyBase`` property.

        :param listType: An unbound ``PropertyBase`` instance, defining
                         the type of value allowed in the list. This is
                         optional; if not provided, values of any type will be
                         allowed in the list, but no validation or casting
                         will be performed.
        """
        PropertyBase.__init__(self, **kwargs)
        self._listType = listType

        
    def _makePropVal(self, instance):
        """Creates and returns a :class:`.PropertyValueList` object to be
        associated with the given ``HasProperties`` instance.
        """

        if self._listType is not None:
            itemCastFunc     = self._listType.cast
            itemValidateFunc = self._listType.validate
            itemEqualityFunc = self._listType._equalityFunc
            itemAllowInvalid = self._listType._allowInvalid
            itemAttributes   = self._listType._defaultConstraints
        else:
            itemCastFunc     = None
            itemValidateFunc = None
            itemEqualityFunc = None
            itemAllowInvalid = True
            itemAttributes   = None

        default = self._defaultConstraints.get('default', None)
        
        return PropertyValueList(
            instance,
            name=self.getLabel(instance), 
            values=default,
            itemCastFunc=itemCastFunc,
            itemValidateFunc=itemValidateFunc,
            itemEqualityFunc=itemEqualityFunc,
            listValidateFunc=self.validate,
            itemAllowInvalid=itemAllowInvalid,
            listAttributes=self._defaultConstraints,
            itemAttributes=itemAttributes)

        
    def getPropValList(self, instance):
        """Returns the list of ``PropertyValue`` objects which represent the
        items stored in this list.

        Note that this is a list of ``PropertyValue`` instances; it is not the
        ``PropertyValueList`` instance. The latter can be accessed through
        the owning ``HasProperties`` instance with a simple attribute access.
        """
        propVal = self.getPropVal(instance)
        if propVal is not None: return propVal.getPropertyValueList()
        else:                   return None

        
class PropertyOwner(type):
    """Metaclass for the ``HasProperties`` class. Sets ``PropertyBase``
    labels from the corresponding class attribute names.
    """
    def __new__(cls, name, bases, attrs):

        newCls = super(PropertyOwner, cls).__new__(cls, name, bases, attrs)

        # Return *all* attributes of the new class,
        # including those of its super classes
        def allAttrs(cls):
            atts = cls.__dict__.items()
            if hasattr(cls, '__bases__'):
                for base in cls.__bases__:
                    atts += allAttrs(base)
            return atts
        
        for n, v in allAttrs(newCls):
            if isinstance(v, PropertyBase):
                v._setLabel(newCls, n)

        return newCls


class HasProperties(object):
    """Base class for classes which contain ``PropertyBase`` instances.  All
    classes which contain ``PropertyBase`` objects must subclass this
    class.
    """
    __metaclass__ = PropertyOwner

    
    def __new__(cls, *args, **kwargs):
        """Here we create a new ``HasProperties`` instance, and loop
        through all of its ``PropertyBase`` properties to ensure that
        they are initialised.
        """
        
        instance  = super(HasProperties, cls).__new__(cls, *args, **kwargs)
        propNames = dir(instance.__class__)

        # By default, when a property changes,
        # all other properties are not validated.
        # This behaviour can be changed by passing
        # validateOnChange=True to __init__.
        instance.__validateOnChange = False
        
        for propName in propNames:
            
            prop = getattr(instance.__class__, propName)
            if not isinstance(prop, PropertyBase): continue

            # Add each class level PropertyBase
            # object as a property of the new
            # HasProperties instance
            instance.addProperty(propName, prop)

        return instance


    def __init__(self, validateOnChange=False):
        """Create a ``HasProperties`` instance.

        ``HasProperties.__init__`` does not need to be called if
        ``validateOnChange=False``.

        .. note:: The ``validateOnChange`` argument warrants some explanation.
        
           The point of validating all other properties when one property
           changes is to handle the scenario where the validity of one
           property is dependent upon the values of other properties.
           
           Currently, the only option is to enable this globally;
           i.e. whenever the value of any property changes, all other
           properties are validated.
           
           At some stage, I may allow more fine grained control;
           e.g. validation could only occur when specific properties change,
           and/or only specific properties are validated. This should be
           fairly straightforward - we could just maintain a dict of
           ``{propName : [propNames ..]}`` mappings, where the key is the name
           of a property that should trigger validation, and the value is a
           list of properties that need to be validated when that property
           changes.

        :arg validateOnChange: Defaults to ``False``. If set to ``True``,
                               whenever any property value is changed,
                               the value of *every* property is re-validated.
                               This functionality is accomplished by using
                               the *preNotify* listener on all
                               ``PropertyValue`` instances - see the
                               :meth:`.PropertyValue.setPreNotifyFunction`
                               method.
        """

        self.__validateOnChange = validateOnChange

        # The prenotify function is added to new properties
        # in the addProperty method, but not for properties
        # defined at the class level (because the
        # __validateOnChange attribute is initially set to
        # false in __new__). So here we make sure that the
        # prenotify is set if needed.
        
        if validateOnChange:
            propNames, props = self.getAllProperties()

            for prop, propName in zip(propNames, props):
                propVal = prop.getPropVal(self)
                propVal.setPreNotifyFunction(self.__valueChanged)


    def __copy__(self):
        """Default copy operator.

        Creates a new instance of this type, and copies all property values
        across.

        If a no-arguments constructor is not available, an error will
        be raised.

        Subclasses which require arguments on initialisation, or which have
        more complex copy semantics, will need to implement their own
        ``__copy__`` operator if this one does not suffice.
        """

        copy = type(self)()

        # TODO Is this going to crash for List properties?
        #      If it does, make it not crash.
        for propName in self.getAllProperties()[0]:
            setattr(copy, propName, getattr(self, propName))
            
        return copy

                
    def addProperty(self, propName, propObj):
        """Add the given `PropertyBase`` instance as an attribute of this
        ``HasProperties`` instance. """
        if not isinstance(propObj, PropertyBase):
            raise ValueError('propObj must be a PropertyBase instance')

        if propName in self.__dict__:
            raise RuntimeError('This {} instance already has '
                               'an attribute ''called {}'.format(
                                   self.__class__.__name__, propName))

        # If this property does not exist on the class,
        # add it. This is a bit hacky, as the labels
        # for all the properties that exist in the class
        # definition are handled by the metaclass. What's
        # stopping me from throwing out the metaclass,
        # and doing everything in HasProps.__new__, and
        # this method? Related - is there a reason why
        # PropertyBase labels are tied to the HasProps
        # class, rather than to the instance?
        if not hasattr(self.__class__, propName):
            setattr(          self.__class__, propName, propObj)
            propObj._setLabel(self.__class__, propName)

        # Create a PropertyValue and an _InstanceData
        # object, which bind the PropertyBase object
        # to this HasProperties instance. 
        propVal = propObj._makePropVal(self)
        instData = _InstanceData(self, propVal)

        log.debug('Adding property to {}.{} [{}] ({})'.format(
            self.__class__.__name__,
            propName,
            id(self),
            propObj.__class__.__name__))

        # Store the _InstanceData object
        # on this instance itself
        self.__dict__[propName] = instData

        # validate other properties when
        # this property changes - does
        # nothing if validation is enabled
        if self.__validateOnChange:
            propVal.setPreNotifyFunction(self.__valueChanged)

        
    def __valueChanged(self, ctx, value, valid, name):
        """This method is only called if ``validateOnChange`` was set
        to true in :meth:`__init__`. It is registered as the ``preNotify``
        listener on all ``PropertyValue`` instances. See the note in
        :meth:`__init__`.
        """

        if not self.__validateOnChange:
            return
        
        # Force validation for all other properties of the instance, and
        # notification of their registered listeners, This is done because the
        # validity of some properties may be dependent upon the values of this
        # one. So when the value of this property changes, it may have changed
        # the validity of another property, meaning that the listeners of the
        # latter property need to be notified of this change in validity.

        log.debug('Revalidating all instance properties '
                  '(due to {} change)'.format(self.getLabel(instance)))
        
        propNames, props = self.getAllProperties()
        for propName, prop in zip(propNames, props):
            if propName is not name:
                prop.revalidate(instance)

        
    @classmethod
    def getAllProperties(cls):
        """Returns two lists, the first containing the names of all properties
        of this object, and the second containing the corresponding
        ``PropertyBase`` objects.

        Properties which have a name beginning with an underscore are not
        returned by this method
        """

        propNames = []
        props     = []

        for attName in dir(cls):
            
            att = getattr(cls, attName)

            if isinstance(att, PropertyBase) and (not attName.startswith('_')):
                propNames.append(attName)
                props    .append(att)

        return propNames, props


    @classmethod
    def getProp(cls, propName):
        """Return the ``PropertyBase`` object for the given property."""
        return getattr(cls, propName)

    
    def getPropVal(self, propName):
        """Return the ``PropertyValue`` object(s) for the given property.
        """
        return self.getProp(propName).getPropVal(self)


    def getLastValue(self, propName):
        """Returns the most recent value of the specified property before its
        current one.

        See the :meth:`.PropertyValue.getLast` method.
        """
        return self.getPropVal(propName).getLast()


    def enableNotification(self, propName):
        """Enables notification of listeners on the given property.

        See the :meth:`.PropertyValue.enableNotification` method.
        """
        self.getPropVal(propName).enableNotification()

    
    def disableNotification(self, propName):
        """Disables notification of listeners on the given property.

        See the :meth:`.PropertyValue.disableNotification` method.
        """
        self.getPropVal(propName).disableNotification()

        
    def enableAllNotification(self):
        """Enables notification of listeners on all properties."""
        propNames, props = self.getAllProperties()
        for propName in propNames:
            self.enableNotification(propName) 

    
    def disableAllNotification(self):
        """Disables notification of listeners on all properties."""
        propNames, props = self.getAllProperties()
        for propName in propNames:
            self.disableNotification(propName) 


    def enableProperty(self, propName):
        """Enables the given property - see :meth:`PropertyBase.enable`."""
        self.getProp(propName).enable(self)

        
    def disableProperty(self, propName):
        """Disables the given property - see :meth:`PropertyBase.disable`."""
        self.getProp(propName).disable(self)


    def propertyIsEnabled(self, propName):
        """Returns the enabled state of the given property - see
        :meth:`PropertyBase.isEnabled`.
        """
        return self.getProp(propName).isEnabled()


    def notify(self, propName):
        """Force notification of listeners on the given property. This will
        have no effect if notification for the property is disabled.

        See the :meth:`.PropertyValue.notify` method.
        """
        self.getPropVal(propName).notify()


    def getConstraint(self, propName, constraint):
        """Convenience method, returns the value of the named constraint for
        the named property. See :meth:`PropertyBase.getConstraint`.
        """
        return self.getProp(propName).getConstraint(self, constraint)

        
    def setConstraint(self, propName, constraint, value):
        """Convenience method, sets the value of the named constraint for
        the named property. See :meth:`PropertyBase.setConstraint`.
        """ 
        return self.getProp(propName).setConstraint(self, constraint, value)


    def addListener(self,
                    propName,
                    listenerName,
                    callback,
                    overwrite=False,
                    weak=True):
        """Convenience method, adds the specified listener to the specified
        property. See :meth:`PropertyValue.addListener`.
        """
        self.getPropVal(propName).addListener(
            listenerName,
            callback,
            overwrite=overwrite,
            weak=weak)

        
    def removeListener(self, propName, listenerName):
        """Convenience method, removes the specified listener from the
        specified property. See :meth:`PropertyValue.removeListener`.
        """
        self.getPropVal(propName).removeListener(listenerName)

        
    def enableListener(self, propName, name):
        """(Re-)Enables the listener on the specified property with the
        specified ``name``.
        """
        self.getPropVal(propName).enableListener(name)

    
    def disableListener(self, propName, name):
        """Disables the listener on the specified property with the specified
        ``name``, but does not remove it from the list of listeners.
        """
        self.getPropVal(propName).disableListener(name)


    def addGlobalListener(self,
                          listenerName,
                          callback,
                          overwrite=False,
                          weak=True):
        """Registers the given listener so that it will be notified of
        changes to any of the properties of this HasProperties instance.
        """
        propNames, props = self.getAllProperties()
        for propName in propNames:
            self.getPropVal(propName).addListener(
                listenerName, callback, overwrite=overwrite, weak=weak)
    
    
    def removeGlobalListener(self, listenerName):
        """De-registers the specified global listener (see
        :meth:`addGlobalListener`).
        """
        propNames, props = self.getAllProperties()
        for propName in propNames:
            self.getPropVal(propName).removeListener(listenerName) 


    def isValid(self, propName):
        """Returns ``True`` if the current value of the specified property is
        valid, ``False`` otherwise.
        """

        prop    = self.getProp(propName)
        propVal = prop.getPropVal(self)
        
        try: prop.validate(self, propVal.getAttributes(), propVal.get())
        except ValueError: return False

        return True

        
    def validateAll(self):
        """Validates all of the properties of this :class:`HasProperties`
        object.  A list of tuples is returned, with each tuple containing
        a property name, and an associated error string. The error string
        is a message about the property which failed validation. If all
        property values are valid, the returned list will be empty.
        """

        names, props = self.getAllProperties()

        errors = []

        for name, prop in zip(names, props):

            propVal = prop.getPropVal(self)
            
            try:
                prop.validate(self, propVal.getAttributes(), propVal.get())
                
            except ValueError as e:
                errors.append((name, e.message))

        return errors
    
        
    def __str__(self):
        """Returns a multi-line string containing the names and values of
        all the properties of this object.
        """
        
        clsname = self.__class__.__name__

        propNames, props = self.getAllProperties()

        if len(propNames) == 0:
            return clsname

        propVals = ['{}'.format(getattr(self, propName))
                    for propName in propNames]

        maxNameLength = max(map(len, propNames))

        lines = [clsname]

        for propName, propVal in zip(propNames, propVals):
            fmtStr = '  {:>' + str(maxNameLength) + '} = {}'
            lines.append(fmtStr.format(propName, propVal))
            
        return '\n'.join(lines)


from properties_value import *
from properties_types import *
