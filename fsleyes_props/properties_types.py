#!/usr/bin/env python
#
# properties_types.py - Definitions for different property types.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""Definitions for different property types.

This module provides a number of :class:`.PropertyBase` subclasses which
define properties of different types. These classes are intended to be
added as attributes of a :class:`.HasProperties` class definition.

 .. autosummary::
    :nosignatures:

    Object
    Boolean
    Number
    Int
    Real
    Percentage
    String
    Choice
    FilePath
    List
    Colour
    ColourMap
    Bounds
    Point
    Array
"""


import os.path as op

import collections

import six

import numpy as np

from . import properties        as props
from . import properties_value  as propvals


class Object(props.PropertyBase):
    """A property which encapsulates any value. """

    def __init__(self, **kwargs):
        """Create a ``Object`` property. If an ``equalityFunc`` is not
        provided, any writes to this property will be treated as if the value
        has changed (and any listeners will be notified).
        """

        def defaultEquals(this, other):
            return False

        kwargs['equalityFunc'] = kwargs.get('equalityFunc', defaultEquals)
        props.PropertyBase.__init__(self, **kwargs)


class Boolean(props.PropertyBase):
    """A property which encapsulates a ``bool`` value."""

    def __init__(self, **kwargs):
        """Create a ``Boolean`` property.

        If the ``default`` ``kwarg`` is not provided, a default value of
        ``False`` is used.
        """

        kwargs['default'] = kwargs.get('default', False)
        props.PropertyBase.__init__(self, **kwargs)


    def cast(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.cast`. Casts the given value to a
        ``bool``.
        """
        return bool(value)


class Number(props.PropertyBase):
    """Base class for the :class:`Int` and :class:`Real` classes.

    A property which represents a number.  Don't use/subclass this,
    use/subclass one of ``Int`` or ``Real``.
    """

    def __init__(self,
                 minval=None,
                 maxval=None,
                 clamped=False,
                 **kwargs):
        """Define a :class:`Number` property.

        :param minval:  Minimum valid value

        :param maxval:  Maximum valid value

        :param clamped: If ``True``, the value will be clamped to its
                        min/max bounds.

        :param kwargs:  Passed through to :meth:`.PropertyBase.__init__`.
                        If a ``default`` value is not provided, it is set
                        to something sensible.
        """

        default = kwargs.get('default', None)

        if default is None:
            if minval is not None and maxval is not None:
                default = (minval + maxval) / 2
            elif minval is not None:
                default = minval
            elif maxval is not None:
                default = maxval
            else:
                default = 0

        kwargs['default']    = default
        kwargs['minval']     = minval
        kwargs['maxval']     = maxval
        kwargs['clamped']    = clamped
        props.PropertyBase.__init__(self, **kwargs)


    def validate(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.validate`. Validates the given
        number.

        Calls the :meth:`.PropertyBase.validate` method.
        Then, if the ``minval`` and/or ``maxval`` attributes have been set,
        and the given value is not within those values, a :exc:`ValueError` is
        raised.

        :param instance:   The owning :class:`.HasProperties` instance (or
                           ``None`` for unbound property values).

        :param attributes: Dictionary containing property attributes.

        :param value:      The value to validate.
        """

        props.PropertyBase.validate(self, instance, attributes, value)

        minval = attributes['minval']
        maxval = attributes['maxval']

        if minval is not None and value < minval:
            raise ValueError('Must be at least {}'.format(minval))

        if maxval is not None and value > maxval:
            raise ValueError('Must be at most {}'.format(maxval))


    def cast(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.cast`.

        If the ``clamped`` attribute is ``True`` and the ``minval`` and/or
        ``maxval`` have been set, this function ensures that the given value
        lies within the ``minval`` and ``maxval`` limits. Otherwise the value
        is returned unchanged.
        """

        clamped = attributes['clamped']

        if not clamped: return value

        minval = attributes['minval']
        maxval = attributes['maxval']

        if minval is not None and value < minval: return minval
        if maxval is not None and value > maxval: return maxval

        return value


class Int(Number):
    """A :class:`Number` which encapsulates an integer."""

    def __init__(self, **kwargs):
        """Create an ``Int`` property. """
        Number.__init__(self, **kwargs)


    def cast(self, instance, attributes, value):
        """Overrides :meth:`Number.cast`. Casts the given value to an ``int``,
        and then passes the value to :meth:`Number.cast`.
        """
        return Number.cast(self, instance, attributes, int(value))


class Real(Number):
    """A :class:`.Number` which encapsulates a floating point number."""


    def __equals(self, a, b):
        """Custom equality function passed to :class`.PropertyBase.__init__`.

        Tests for equality according to the ``precision`` passed to
        :meth:`__init__`.
        """

        if any((a is None, b is None, self.__precision is None)):
            return a == b

        return abs(a - b) < self.__precision


    def __init__(self, precision=0.000000001, **kwargs):
        """Define a ``Real`` property.

        :param precision: Tolerance for equality testing. Set to ``None`` to
                          use exact equality.
        """
        self.__precision = precision

        Number.__init__(self, equalityFunc=self.__equals, **kwargs)


    def cast(self, instance, attributes, value):
        """Overrides :meth:`Number.cast`. Casts the given value to a ``float``,
        and then passes the value to :meth:`Number.cast`.
        """
        return Number.cast(self, instance, attributes, float(value))


class Percentage(Real):
    """A :class:`Real` property which represents a percentage.

    A ``Percentage`` property is just a ``Real`` property with
    a default minimum value of ``0`` and default maximum value of ``100``.
    """

    def __init__(self, **kwargs):
        """Create a ``Percentage`` property."""
        kwargs['minval']  = kwargs.get('minval',    0.0)
        kwargs['maxval']  = kwargs.get('maxval',  100.0)
        kwargs['default'] = kwargs.get('default',  50.0)
        Real.__init__(self, **kwargs)


class String(props.PropertyBase):
    """A property which encapsulates a string."""

    def __init__(self, minlen=None, maxlen=None, **kwargs):
        """Cteate a ``String`` property.

        :param int minlen: Minimum valid string length.
        :param int maxlen: Maximum valid string length.
        """

        kwargs['default'] = kwargs.get('default', None)
        kwargs['minlen']  = minlen
        kwargs['maxlen']  = maxlen
        props.PropertyBase.__init__(self, **kwargs)


    def cast(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.cast`.

        Casts the given value to a string. If the given value is the empty
        string, it is replaced with ``None``.
        """

        if value == '': return None
        else:           return value


    def validate(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.validate`.

        Passes the given value to
        :meth:`.PropertyBase.validate`. Then, if either the
        ``minlen`` or ``maxlen`` attributes have been set, and the given
        value has length less than ``minlen`` or greater than ``maxlen``,
        raises a :exc:`ValueError`.
        """

        if value == '': value = None

        props.PropertyBase.validate(self, instance, attributes, value)

        if value is None: return

        if not isinstance(value, six.string_types):
            raise ValueError('Must be a string')

        minlen = attributes['minlen']
        maxlen = attributes['maxlen']

        if minlen is not None and len(value) < minlen:
            raise ValueError('Must have length at least {}'.format(minlen))

        if maxlen is not None and len(value) > maxlen:
            raise ValueError('Must have length at most {}'.format(maxlen))


class Choice(props.PropertyBase):
    """A property which may only be set to one of a set of predefined values.

    Choices can be added/removed via the :meth:`addChoice`,
    :meth:`removeChoice` method, and :meth:`setChoices` methods. Existing
    choices can be modified with the :meth:`updateChoice` method.

    Individual choices can be enabled/disabled via the :meth:`enableChoice`
    and :meth:`disableChoice` methods. The ``choiceEnabled`` attribute
    contains a dictionary of ``{choice : boolean}`` mappings
    representing the enabled/disabled state of each choice.

    A set of alternate values can be provided for each choice - these
    alternates will be accepted when assigning to a ``Choice`` property.

    .. note:: If you create a ``Choice`` property with non-string choice and
              alternate values, you may run into problems when using
              :mod:`.serialise` and/or :mod:`.cli` functionality, unless you
              set ``allowStr`` to ``True``.
    """

    def __init__(self,
                 choices=None,
                 alternates=None,
                 allowStr=False,
                 **kwargs):
        """Create a ``Choice`` property.

        :arg choices:    List of values, the possible values that this property
                         can take. Can alternately be a ``dict`` - see the note
                         above.

        :arg alternates: A list of lists, specificying alternate acceptable
                         values for each choice. Can also be a dict of
                         ``{choice : [alternates]}`` mappings. All alternate
                         values must be unique - different choices cannot have
                         equivalent alternate values.

        :arg allowStr:   If ``True``, string versions of any non-string choice
                         values will be accepted - ``str`` versions of each
                         choice are added as alternate values for that choice.
                         Defaults to ``False``.
        """

        if choices is None:
            choices    = []
            alternates = {}

        # Alternates are stored twice:
        #
        #   - As a dict of { choice    : [alternate] } mappings
        #   - As a dict of { alternate : choice      } mappings
        #
        # We generate the first dict here
        if alternates is None:
            alternates = {c : [] for c in choices}

        elif isinstance(alternates, dict):
            alternates = dict(alternates)

        elif isinstance(alternates, (list, tuple)):
            alternates = {c : list(a) for (c, a) in zip(choices, alternates)}

        # Add stringified versions of all
        # choices if allowStr is True
        if allowStr:
            for c in choices:
                strc = str(c)
                alts = alternates[c]
                if strc not in alts:
                    alts.append(strc)

        # Generate the second alternates dict
        altLists   = alternates
        alternates = self.__generateAlternatesDict(altLists)

        # Enabled flags are stored as a dict
        # of {choice : bool} mappings
        enabled = {choice: True for choice in choices}

        if len(choices) > 0: default = choices[0]
        else:                default = None

        if len(choices) != len(altLists):
            raise ValueError('Alternates are required for every choice')

        kwargs['choices']       = list(choices)
        kwargs['alternates']    = dict(alternates)
        kwargs['altLists']      = dict(altLists)
        kwargs['choiceEnabled'] = enabled
        kwargs['allowStr']      = allowStr
        kwargs['default']       = kwargs.get('default',      default)
        kwargs['allowInvalid']  = kwargs.get('allowInvalid', False)

        props.PropertyBase.__init__(self, **kwargs)


    def setDefault(self, default, instance=None):
        """Sets the default choice value. """
        if default not in self.getChoices(instance):
            raise ValueError('{} is not a choice'.format(default))

        self.setAttribute(instance, 'default', default)


    def enableChoice(self, choice, instance=None):
        """Enables the given choice. """
        choiceEnabled = dict(self.getAttribute(instance, 'choiceEnabled'))
        choiceEnabled[choice] = True
        self.setAttribute(instance, 'choiceEnabled', choiceEnabled)


    def disableChoice(self, choice, instance=None):
        """Disables the given choice. An attempt to set the property to
        a disabled value will result in a :exc:`ValueError`.
        """
        choiceEnabled = dict(self.getAttribute(instance, 'choiceEnabled'))
        choiceEnabled[choice] = False
        self.setAttribute(instance, 'choiceEnabled', choiceEnabled)


    def choiceEnabled(self, choice, instance=None):
        """Returns ``True`` if the given choice is enabled, ``False``
        otherwise.
        """
        return self.getAttribute(instance, 'choiceEnabled')[choice]


    def getChoices(self, instance=None):
        """Returns a list of the current choices. """
        return list(self.getAttribute(instance, 'choices'))


    def getAlternates(self, instance=None):
        """Returns a list of the current acceptable alternate values for each
        choice.
        """
        choices  = self.getAttribute(instance, 'choices')
        altLists = self.getAttribute(instance, 'altLists')

        return [altLists[c] for c in choices]


    def updateChoice(self,
                     choice,
                     newChoice=None,
                     newAlt=None,
                     instance=None):
        """Updates the choice value and/or alternates for the specified choice.
        """

        choices    = list(self.getAttribute(instance, 'choices'))
        altLists   = dict(self.getAttribute(instance, 'altLists'))
        idx        = choices.index(choice)

        if newChoice is not None:
            choices[ idx]       = newChoice
            altLists[newChoice] = altLists[choice]

            altLists.pop(choice)
        else:
            newChoice = choice

        if newAlt is not None: altLists[newChoice] = list(newAlt)

        self.__updateChoices(choices, altLists, instance)


    def setChoices(self, choices, alternates=None, instance=None):
        """Sets the list of possible choices (and their alternate values, if
        not None).
        """

        if alternates is None:
            alternates = {c : [] for c in choices}
        elif isinstance(alternates, (list, tuple)):
            alternates = {c : a for (c, a) in zip(choices, alternates)}
        elif isinstance(alternates, dict):
            alternates = dict(alternates)

        # Add stringified versions of all
        # choices if allowStr is True
        if self.getAttribute(instance, 'allowStr'):
            for c in choices:
                strc = str(c)
                alts = alternates[c]
                if strc not in alts:
                    alts.append(strc)

        if len(choices) != len(alternates):
            raise ValueError('Alternates are required for every choice')

        self.__updateChoices(choices, alternates, instance)


    def addChoice(self, choice, alternate=None, instance=None):
        """Adds a new choice to the list of possible choices."""

        if alternate is None: alternate = []
        else:                 alternate = list(alternate)

        choices  = list(self.getAttribute(instance, 'choices'))
        altLists = dict(self.getAttribute(instance, 'altLists'))

        if self.getAttribute(instance, 'allowStr'):
            strc = str(choice)
            if strc not in alternate:
                alternate.append(strc)

        choices.append(choice)
        altLists[choice] = list(alternate)

        self.__updateChoices(choices, altLists, instance)


    def removeChoice(self, choice, instance=None):
        """Removes the specified choice from the list of possible choices. """

        choices   = list(self.getAttribute(instance, 'choices'))
        altLists  = dict(self.getAttribute(instance, 'altLists'))

        choices .remove(choice)
        altLists.pop(   choice)

        self.__updateChoices(choices, altLists, instance)


    def __generateAlternatesDict(self, altLists):
        """Given a dictionary containing ``{choice : [alternates]}``
        mappings, creates and returns a dictionary containing
        ``{alternate : choice}`` mappings.

        Raises a ``ValueError`` if there are any duplicate alternate values.
        """

        alternates = {}

        for choice, altList in altLists.items():
            for alt in altList:
                if alt in alternates:
                    raise ValueError('Duplicate alternate value '
                                     '(choice: {}): {}'.format(choice, alt))
                alternates[alt] = choice

        return alternates


    def __updateChoices(self, choices, alternates, instance=None):
        """Used by all of the public choice modifying methods. Updates
        all choices, labels, and altenrates.

        :param choices:    A list of choice values

        :param alternates: A dict of ``{choice :  [alternates]}`` mappings.
        """

        propVal    = self.getPropVal(  instance)
        default    = self.getAttribute(instance, 'default')
        oldEnabled = self.getAttribute(instance, 'choiceEnabled')
        newEnabled = {}

        # Prevent notification while
        # we're updating constraints
        if propVal is not None:
            oldChoice  = propVal.get()
            notifState = propVal.getNotificationState()
            validState = propVal.allowInvalid()
            propVal.disableNotification()
            propVal.allowInvalid(True)

        for choice in choices:
            if choice in oldEnabled: newEnabled[choice] = oldEnabled[choice]
            else:                    newEnabled[choice] = True

        if default not in choices:
            default = choices[0]

        altLists   = alternates
        alternates = self.__generateAlternatesDict(altLists)

        self.setAttribute(instance, 'choiceEnabled', newEnabled)
        self.setAttribute(instance, 'altLists',      altLists)
        self.setAttribute(instance, 'alternates',    alternates)
        self.setAttribute(instance, 'choices',       choices)
        self.setAttribute(instance, 'default',       default)

        if propVal is not None:

            if oldChoice not in choices:
                if   default in choices: propVal.set(default)
                elif len(choices) > 0:   propVal.set(choices[0])
                else:                    propVal.set(None)

            propVal.setNotificationState(notifState)
            propVal.allowInvalid(        validState)

            if notifState:
                propVal.notifyAttributeListeners('choices', choices)

            if propVal.get() != oldChoice:
                propVal.propNotify()


    def validate(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.validate`.

        Raises a :exc:`ValueError` if the given value is not one of the
        possible values for this :class:`Choice` property.
        """
        props.PropertyBase.validate(self, instance, attributes, value)

        choices    = self.getAttribute(instance, 'choices')
        enabled    = self.getAttribute(instance, 'choiceEnabled')
        alternates = self.getAttribute(instance, 'alternates')

        if len(choices) == 0: return

        # Check to see if this is an
        # acceptable alternate value
        altValue = alternates.get(value, None)

        if value not in choices and altValue not in choices:
            raise ValueError('Invalid choice ({})'    .format(value))

        if not enabled.get(value, False):
            raise ValueError('Choice is disabled ({})'.format(value))


    def cast(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.cast`.

        Checks to see if the given value is a valid alternate value for a
        choice. If so, the alternate value is replaced with the choice value.
        """
        alternates = self.getAttribute(instance, 'alternates')
        return alternates.get(value, value)



class FilePath(String):
    """A property which represents a file or directory path.

    There is currently no support for validating a path which may be either a
    file or a directory - only one or the other.
    """

    def __init__(self, exists=False, isFile=True, suffixes=[], **kwargs):
        """Create a ``FilePath`` property.

        :param bool exists:   If ``True``, the path must exist.

        :param bool isFile:   If ``True``, the path must be a file. If
                              ``False``, the path must be a directory. This
                              check is only performed if ``exists`` is
                              ``True``.

        :param list suffixes: List of acceptable file suffixes (only relevant
                              if ``isFile`` is ``True``).
        """

        kwargs['exists']   = exists
        kwargs['isFile']   = isFile
        kwargs['suffixes'] = suffixes

        String.__init__(self, **kwargs)


    def validate(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.validate`.

        If the ``exists`` attribute is not ``True``, does nothing. Otherwise,
        if ``isFile`` is ``False`` and the given value is not a path to an
        existing directory, a :exc:`ValueError` is raised.

        If ``isFile`` is ``True``, and the given value is not a path to an
        existing file (which, if ``suffixes`` is not None, must end in one of
        the specified suffixes), a :exc:`ValueError` is raised.
        """

        String.validate(self, instance, attributes, value)

        exists   = attributes['exists']
        isFile   = attributes['isFile']
        suffixes = attributes['suffixes']

        if value is None: return
        if value == '':   return
        if not exists:    return

        if isFile:

            matchesSuffix = any([value.endswith(s) for s in suffixes])

            # If the file doesn't exist, it's bad
            if not op.isfile(value):
                raise ValueError('Must be a file ({})'.format(value))

            # if the file exists, and matches one of
            # the specified suffixes, then it's good
            if len(suffixes) == 0 or matchesSuffix: return

            # Otherwise it's bad
            else:
                raise ValueError(
                    'Must be a file ending in [{}] ({})'.format(
                        ','.join(suffixes), value))

        elif not op.isdir(value):
            raise ValueError('Must be a directory ({})'.format(value))


class List(props.ListPropertyBase):
    """A property which represents a list of items, of another property type.

    If you use ``List`` properties, you really should read the documentation
    for the :class:`.PropertyValueList`, as it contains important usage
    information.
    """

    def __init__(self, listType=None, minlen=None, maxlen=None, **kwargs):
        """Create a ``List`` property.

        :param listType:   A :class:`.PropertyBase` type, specifying the
                           values allowed in the list. If ``None``, anything
                           can be stored in the list, but no casting or
                           validation will occur.

        :param int minlen: Minimum list length.

        :param int maxlen: Maximum list length.
        """

        if (listType is not None) and \
           (not isinstance(listType, props.PropertyBase)):
            raise ValueError(
                'A list type (a PropertyBase instance) must be specified')

        kwargs['default'] = kwargs.get('default', [])
        kwargs['minlen']  = minlen
        kwargs['maxlen']  = maxlen

        # This needs to be removed when you update widgets_list.py
        self.embed = False

        props.ListPropertyBase.__init__(self, listType,  **kwargs)


    def validate(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.validate`.

        Checks that the given value (which should be a list) meets the
        ``minlen``/``maxlen`` attribute. Raises a :exc:`ValueError` if it
        does not.
        """

        props.ListPropertyBase.validate(self, instance, attributes, value)

        minlen = attributes['minlen']
        maxlen = attributes['maxlen']

        if minlen is not None and len(value) < minlen:
            raise ValueError('Must have length at least {}'.format(minlen))
        if maxlen is not None and len(value) > maxlen:
            raise ValueError('Must have length at most {}'.format(maxlen))


class Colour(props.PropertyBase):
    """A property which represents a RGBA colour, stored as four floating
    point values in the range ``0.0 - 1.0``.

    RGB colours are also accepted - if an RGB colour is provided, the
    alpha channel is set to 1.0.
    """


    def __init__(self, **kwargs):
        """Create a ``Colour`` property.

        If the ``default`` ``kwarg`` is not provided, the default is set
        to white.
        """

        default = kwargs.get('default', (1.0, 1.0, 1.0, 1.0))

        if len(default) == 3:
            default = list(default) + [1.0]

        kwargs['default'] = default

        props.PropertyBase.__init__(self, **kwargs)


    def validate(self, instance, attributes, value):
        """Checks the given ``value``, and raises a :exc:`ValueError` if
        it does not consist of three or four floating point numbers in the
        range ``(0.0 - 1.0)``.
        """
        props.PropertyBase.validate(self, instance, attributes, value)

        if (not isinstance(value, collections.Sequence)) or \
           (len(value) not in (3, 4)):
            raise ValueError('Colour must be a sequence of three/four values')

        for v in value:
            if (v < 0.0) or (v > 1.0):
                raise ValueError('Colour values must be between 0.0 and 1.0')


    def cast(self, instance, attributes, value):
        """Ensures that the given ``value`` contains three or four floating
        point numbers, in the range ``(0.0 - 1.0)``.

        If the alpha channel is not provided, it is set to the current alpha
        value (which defaults to ``1.0``).
        """

        pv = self.getPropVal(instance)

        if pv is not None: currentVal = pv.get()
        else:              currentVal = self.getAttribute(None, 'default')

        value = [float(v) for v in value]

        if len(value) == 3:
            value = value + [currentVal[3]]

        value = value[:4]

        for i, v in enumerate(value):
            if v < 0.0: value[i] = 0.0
            if v > 1.0: value[i] = 1.0

        return value


class ColourMap(props.PropertyBase):
    """A property which encapsulates a :class:`matplotlib.colors.Colormap`.

    A ``ColourMap`` property can take any ``Colormap`` instance as its
    value. ColourMap values may be specified either as a
    ``Colormap`` instance, or as a string containing
    the name of a registered colour map instance.

    ``ColourMap`` properties also maintain an internal list of colour
    map names; while these names do not restrict the value that a ``ColourMap``
    property can take, they are used for display purposes - a widget which is
    created for a ``ColourMap`` instance will only display the options returned
    by the :meth:`getColourMaps` method. See the :func:`widgets._ColourMap`
    function.
    """

    def __init__(self, cmaps=None, **kwargs):
        """Define a ``ColourMap`` property. """

        default = kwargs.get('default', None)

        if cmaps is None:
            cmaps = []

        if default is None and len(cmaps) > 0:
            default = cmaps[0]

        kwargs['default'] = default
        kwargs['cmaps']   = list(cmaps)

        props.PropertyBase.__init__(self, **kwargs)


    def setColourMaps(self, cmaps, instance=None):
        """Set the colour maps for this property.

        :arg cmaps: a list of registered colour map names.
        """

        default = self.getAttribute(instance, 'default')

        if default not in cmaps:
            default = cmaps[0]

        self.setAttribute(instance, 'cmaps'  , cmaps)
        self.setAttribute(instance, 'default', default)


    def addColourMap(self, cmap, instance=None):
        """Add a colour map to the list.

        :arg cmap: The name of a registered colour map.
        """

        cmaps = self.getColourMaps(instance)

        if cmap not in cmaps:
            cmaps.append(cmap)
            self.setColourMaps(cmaps, instance)


    def getColourMaps(self, instance=None):
        """Returns a list containing the names of registered colour maps
        available for this property.
        """
        return list(self.getAttribute(instance, 'cmaps'))


    def validate(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.validate`.

        Raises a :exc:`ValueError` if the given ``value`` is not a
        matplotlib :class:`.Colormap` instance.
        """

        import matplotlib.colors as mplcolors
        if not isinstance(value, mplcolors.Colormap):
            raise ValueError('Colour map value is not a '
                             'matplotlib.colors.Colormap instance')


    def cast(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.cast`.

        If the provided value is a string, an attempt is made to convert it to
        a colour map, via the :func:`matplotlib.cm.get_cmap` function. The
        value may either be the registered colour map name, or its
        ``Colormap.name`` attribute. The match is case-insensitive.
        """

        if isinstance(value, six.string_types):

            import matplotlib.cm as mplcm

            # Case insensitive match
            cmapKeys   = list(mplcm.cmap_d.keys())
            cmapNames  = [cm.name for cm in mplcm.cmap_d.values()]

            lCmapNames = [s.lower() for s in cmapNames]
            lCmapKeys  = [s.lower() for s in cmapKeys]

            value = value.lower()

            try:    idx = lCmapKeys .index(value)
            except: idx = lCmapNames.index(value)

            value = cmapKeys[idx]
            value = mplcm.get_cmap(value)

        return value


class BoundsValueList(propvals.PropertyValueList):
    """A :class:`.PropertyValueList` with values which represent bounds along
    a number of dimensions (up to 4).

    This class is used by the :class:`Bounds` property to encapsulate bounding
    values for an arbitrary number of dimensions. For ``N+1`` dimensions, the
    bounding values are stored as a list::

      [lo0, hi0, lo1, hi1, ..., loN, hiN]

    This class just adds some convenience methods and attributes to the
    ``PropertyValueList`` base class.  For a single dimension, a bound
    object has a ``lo`` value and a ``hi`` value, specifying the bounds along
    that dimension. To make things confusing, each dimension also has ``min``
    and ``max`` attributes, which define the minimum/maximum values that the
    ``lo`` and ``high`` values may take for that dimension.

    Some dynamic attributes are available on ``BoundsValueList`` objects,
    allowing access to and assignment of bound values and
    attributes. Dimensions ``0, 1, 2, 3`` respectively map to identifiers
    ``x, y, z, t``. If an attempt is made to access/assign an attribute
    corresponding to a dimension which does not exist on a particular
    ``BoundsValueList`` instance (e.g. attribute ``t`` on a 3-dimensional
    list), an :exc:`IndexError` will be raised. Here is an example of dynamic
    bound attribute access::

        class MyObj(props.HasProperties):
            myBounds = Bounds(ndims=4)

        obj = MyObj()

        # set/access lo/hi values together
        xlo, xhi = obj.mybounds.x
        obj.mybounds.z = (25, 30)

        # set/access lo/hi values separately
        obj.mybounds.xlo = 2
        obj.mybounds.zhi = 50

        # get the length of the bounds for a dimension
        ylen = obj.mybounds.ylen

        # set/access the minimum/maximum
        # constraints for a dimension
        obj.mybounds.xmin = 0
        tmax = obj.mybounds.tmax
    """


    def __init__(self, *args, **kwargs):
        """Create a ``BoundsValueList`` instance - see
        :meth:`.PropertyValueList.__init__`.
        """
        propvals.PropertyValueList.__init__(self, *args, **kwargs)


    def getLo(self, axis=None):
        """Return the low value for the given (0-indexed) axis. If ``axis`` is
        not specified, the low bounds for all axes are returned.
        """
        if axis is not None: return self[axis * 2]
        else:                return self[::2]


    def getHi(self, axis=None):
        """Return the high value for the given (0-indexed) axis. If ``axis``
        is not specified, the high bounds for all axes are returned.
        """
        if axis is not None: return self[axis * 2 + 1]
        else:                return self[1::2]


    def getRange(self, axis):
        """Return the (low, high) values for the given (0-indexed) axis."""
        return (self.getLo(axis), self.getHi(axis))


    def getLen(self, axis):
        """Return the distance between the low and high values for the
        specified axis.
        """
        return abs(self.getHi(axis) - self.getLo(axis))


    def setLimit(self, axis, limit, value):
        """Sets the value for the specified axis and limit
        (0 == low, 1 == high).
        """
        self[axis * 2 + limit] = value


    def getLimit(self, axis, limit):
        """Returns the value for the specified axis and limit
        (0 == low, 1 == high).
        """
        return self[axis * 2 + limit]


    def setLo(self, axis, value):
        """Set the low value for the specified axis."""
        self[axis * 2] = value


    def setHi(self, axis, value):
        """Set the high value for the specified axis."""
        self[axis * 2 + 1] = value


    def setRange(self, axis, loval, hival):
        """Set the low and high values for the specified axis."""
        self[axis * 2:axis * 2 + 2] = [loval, hival]


    def getMin(self, axis):
        """Return the minimum value (the low limit) for the specified axis."""
        return self.getPropertyValueList()[axis * 2].getAttribute('minval')


    def getMax(self, axis):
        """Return the maximum value (the high limit) for the specified axis."""
        return self.getPropertyValueList()[axis * 2 + 1].getAttribute('maxval')


    def setMin(self, axis, value):
        """Set the minimum value for the specified axis."""
        self.getPropertyValueList()[axis * 2]    .setAttribute('minval', value)
        self.getPropertyValueList()[axis * 2 + 1].setAttribute('minval', value)


    def setMax(self, axis, value):
        """Set the maximum value for the specified axis."""
        self.getPropertyValueList()[axis * 2]    .setAttribute('maxval', value)
        self.getPropertyValueList()[axis * 2 + 1].setAttribute('maxval', value)


    def getLimits(self, axis):
        """Return (minimum, maximum) limit values for the specified axis."""
        return (self.getMin(axis), self.getMax(axis))


    def setLimits(self, axis, minval, maxval):
        """Set the minimum and maximum limit values for the specified axis."""
        self.setMin(axis, minval)
        self.setMax(axis, maxval)


    def inBounds(self, point):
        """Returns ``True`` if the given point (a sequence of numbers) lies
        within the bounds represented by this ``BoundsValueList``, ``False``
        otherwise.
        """
        if 2 * len(point) != len(self):
            raise ValueError('Invalid number of dimensions: {}'.format(point))

        for ax, coord in enumerate(point):
            if coord < self.getLo(ax) or coord > self.getHi(ax):
                return False

        return True


    def __getattr__(self, name):
        """Return the specified value. Raises an :exc:`AttributeError` for
        unrecognised attributes, or an :exc:`IndexError` if an attempt is made
        to access bound values values of a higher dimension than this list
        contains.
        """

        lname = name.lower()

        # TODO this is easy to read, but
        # could be made much more efficient
        if   lname == 'x':    return self.getRange( 0)
        elif lname == 'y':    return self.getRange( 1)
        elif lname == 'z':    return self.getRange( 2)
        elif lname == 't':    return self.getRange( 3)
        elif lname == 'lo':   return self.getLo()
        elif lname == 'hi':   return self.getHi()
        elif lname == 'xlo':  return self.getLo(    0)
        elif lname == 'xhi':  return self.getHi(    0)
        elif lname == 'ylo':  return self.getLo(    1)
        elif lname == 'yhi':  return self.getHi(    1)
        elif lname == 'zlo':  return self.getLo(    2)
        elif lname == 'zhi':  return self.getHi(    2)
        elif lname == 'tlo':  return self.getLo(    3)
        elif lname == 'thi':  return self.getHi(    3)
        elif lname == 'xlen': return self.getLen(   0)
        elif lname == 'ylen': return self.getLen(   1)
        elif lname == 'zlen': return self.getLen(   2)
        elif lname == 'tlen': return self.getLen(   3)
        elif lname == 'xmin': return self.getMin(   0)
        elif lname == 'ymin': return self.getMin(   1)
        elif lname == 'zmin': return self.getMin(   2)
        elif lname == 'tmin': return self.getMin(   3)
        elif lname == 'xmax': return self.getMax(   0)
        elif lname == 'ymax': return self.getMax(   1)
        elif lname == 'zmax': return self.getMax(   2)
        elif lname == 'tmax': return self.getMax(   3)
        elif lname == 'xlim': return self.getLimits(0)
        elif lname == 'ylim': return self.getLimits(1)
        elif lname == 'zlim': return self.getLimits(2)
        elif lname == 'tlim': return self.getLimits(3)

        raise AttributeError('{} has no attribute called {}'.format(
            self.__class__.__name__, name))


    def __setattr__(self, name, value):
        """Set the specified value. Raises an :exc:`IndexError` if an attempt
        is made to assign bound values values of a higher dimension than this
        list contains.
        """

        lname = name.lower()

        if   lname == 'x':    self.setRange( 0, *value)
        elif lname == 'y':    self.setRange( 1, *value)
        elif lname == 'z':    self.setRange( 2, *value)
        elif lname == 't':    self.setRange( 3, *value)
        elif lname == 'xlo':  self.setLo(    0, value)
        elif lname == 'xhi':  self.setHi(    0, value)
        elif lname == 'ylo':  self.setLo(    1, value)
        elif lname == 'yhi':  self.setHi(    1, value)
        elif lname == 'zlo':  self.setLo(    2, value)
        elif lname == 'zhi':  self.setHi(    2, value)
        elif lname == 'tlo':  self.setLo(    3, value)
        elif lname == 'thi':  self.setHi(    3, value)
        elif lname == 'xmin': self.setMin(   0, value)
        elif lname == 'ymin': self.setMin(   1, value)
        elif lname == 'zmin': self.setMin(   2, value)
        elif lname == 'tmin': self.setMin(   3, value)
        elif lname == 'xmax': self.setMax(   0, value)
        elif lname == 'ymax': self.setMax(   1, value)
        elif lname == 'zmax': self.setMax(   2, value)
        elif lname == 'tmax': self.setMax(   3, value)
        elif lname == 'xlim': self.setLimits(0, *value)
        elif lname == 'ylim': self.setLimits(1, *value)
        elif lname == 'zlim': self.setLimits(2, *value)
        elif lname == 'tlim': self.setLimits(3, *value)
        else:                 self.__dict__[name] = value


class Bounds(List):
    """A property which represents numeric bounds in any number of dimensions,
    as long as that number is no more than 4.

    ``Bounds`` values are stored in a :class:`BoundsValueList`, a list of
    integer or floating point values, with two values (lo, hi) for each
    dimension.

    ``Bounds`` values may also have bounds of their own, i.e. minimium/maximum
    values that the bound values can take. These bound-limits are referred to
    as 'min' and 'max', and can be set via the :meth:`BoundsValueList.setMin`
    and :meth:`BoundsValueList.setMax` methods. The advantage to using these
    methods, instead of using, for example,
    :meth:`.PropertyValue.setAttribute`, is that if you use the latter you will
    have to set the attributes on both the low and the high values.
    """

    def __init__(self,
                 ndims=1,
                 real=True,
                 minDistance=None,
                 clamped=True,
                 **kwargs):
        """Create a ``Bounds`` property.

        :arg ndims:        Number of dimensions. This is (currently)
                           not a property attribute, hence it cannot
                           be changed.

        :arg real:         If ``True`` (the default), the bound values are
                           stored as :class:`Real` values; otherwise, they
                           are stored as :class:`Int` values.

        :arg minDistance:  Minimum distance to be maintained between the
                           low/high values for each dimension.

        :arg clamped:      If ``True`` (the default), the bound values are
                           clamped to their limits. See the :class:`Number`
                           class.
        """

        default = kwargs.get('default', None)

        if minDistance is None:
            minDistance = 0.0

        if default is None:
            default = [0.0, minDistance] * ndims

        if ndims < 1 or ndims > 4:
            raise ValueError('Only bounds of one to four '
                             'dimensions are supported')

        elif len(default) != 2 * ndims:
            raise ValueError('{} bound values are required'.format(2 * ndims))

        kwargs['default']     = default
        kwargs['minDistance'] = minDistance

        self._real   = real
        self._ndims  = ndims

        if real: listType = Real(clamped=clamped)
        else:    listType = Int( clamped=clamped)

        List.__init__(self,
                      listType=listType,
                      minlen=ndims * 2,
                      maxlen=ndims * 2,
                      **kwargs)


    def _makePropVal(self, instance):
        """Overrides :meth:`.ListPropertyBase._makePropVal`.

        Creates and returns a ``BoundsValueList`` instead of a
        ``PropertyValueList``, so callers get to use the convenience
        methods/attributes defined in the BVL class.
        """

        default = self.getAttribute(None, 'default', None)

        bvl = BoundsValueList(
            instance,
            name=self.getLabel(instance),
            values=default,
            itemCastFunc=self._listType.cast,
            itemEqualityFunc=self._listType._equalityFunc,
            itemValidateFunc=self._listType.validate,
            listValidateFunc=self.validate,
            listAttributes=self._defaultAttributes,
            itemAttributes=self._listType._defaultAttributes)

        return bvl


    def validate(self, instance, attributes, value):
        """Overrides :meth:`.PropertyBase.validate`.

        Raises a :exc:`ValueError` if the given value (a list of min/max
        values) is of the wrong length or data type, or if any of the min
        values are greater than the corresponding max value.
        """

        minDistance = attributes['minDistance']

        # the List.validate method will check
        # the value length and type for us
        List.validate(self, instance, attributes, value)

        for i in range(self._ndims):

            imin = value[i * 2]
            imax = value[i * 2 + 1]

            if imin > imax:
                raise ValueError('Minimum bound must be smaller '
                                 'than maximum bound (dimension {}, '
                                 '{} - {}'.format(i, imin, imax))

            if imax - imin < minDistance:
                raise ValueError('Minimum and maximum bounds must be at '
                                 'least {} apart'.format(minDistance))


class PointValueList(propvals.PropertyValueList):
    """A list of values which represent a point in some n-dimensional (up to 4)
    space.

    This class is used by the :class:`Point` property to encapsulate point
    values for between 1 and 4 dimensions.

    This class just adds some convenience methods and attributes to the
    :class:`.PropertyValueList` base class, in a similar manner to the
    :class:`BoundsValueList` class.

    The point values for each dimension may be queried/assigned via the
    dynamic attributes ``x, y, z, t``, which respectively map to dimensions
    ``0, 1, 2, 3``. When querying/assigning point values, you may use
    `GLSL-like swizzling
    <http://www.opengl.org/wiki/Data_Type_(GLSL)#Swizzling>`_. For example::

        class MyObj(props.HasProperties):
            mypoint = props.Point(ndims=3)

        obj = MyObj()

        y,z = obj.mypoint.yz

        obj.mypoint.zxy = (3,6,1)
    """


    def __init__(self, *args, **kwargs):
        """Create a ``PointValueList`` - see
        :meth:`.PropertyValueList.__init__`.
        """
        propvals.PropertyValueList.__init__(self, *args, **kwargs)


    def getPos(self, axis):
        """Return the point value for the specified (0-indexed) axis."""
        return self[axis]


    def setPos(self, axis, value):
        """Set the point value for the specified axis."""
        self[axis] = value


    def getMin(self, axis):
        """Get the minimum limit for the specified axis."""
        return self.getPropertyValueList()[axis].getAttribute('minval')


    def getMax(self, axis):
        """Get the maximum limit for the specified axis."""
        return self.getPropertyValueList()[axis].getAttribute('maxval')


    def getLimits(self, axis):
        """Get the (minimum, maximum) limits for the specified axis."""
        return (self.getMin(axis), self.getMax(axis))


    def setMin(self, axis, value):
        """Set the minimum limit for the specified axis."""
        self.getPropertyValueList()[axis].setAttribute('minval', value)


    def setMax(self, axis, value):
        """Set the maximum limit for the specified axis."""
        self.getPropertyValueList()[axis].setAttribute('maxval', value)


    def setLimits(self, axis, minval, maxval):
        """Set the minimum and maximum limits for the specified axis."""
        self.setMin(axis, minval)
        self.setMax(axis, maxval)


    def __getattr__(self, name):
        """Return the specified point value. Raises an :exc:`AttributeError`
        for unrecognised attributes, or an :exc:`IndexError` if a dimension
        which does not exist for this ``PointValueList`` is specified.
        """

        lname = name.lower()

        if any([dim not in 'xyzt' for dim in lname]):
            raise AttributeError('{} has no attribute called {}'.format(
                self.__class__.__name__, name))

        res = []
        for dim in lname:
            if   dim == 'x': res.append(self[0])
            elif dim == 'y': res.append(self[1])
            elif dim == 'z': res.append(self[2])
            elif dim == 't': res.append(self[3])

        if len(res) == 1: return res[0]
        return res


    def __setattr__(self, name, value):
        """Set the specified point value. Raises an :exc:`IndexError` if a
        dimension which does not exist for this ``PointValueList`` is
        specified.
        """

        lname = name.lower()

        if any([dim not in 'xyzt' for dim in lname]):
            self.__dict__[name] = value
            return

        if len(lname) == 1:
            value = [value]

        if len(lname) != len(value):
            raise AttributeError('Improper number of values '
                                 '({}) for attribute {}'.format(
                                     len(value), lname))

        newvals = self[:]

        for dim, val in zip(lname, value):
            if   dim == 'x': newvals[0] = val
            elif dim == 'y': newvals[1] = val
            elif dim == 'z': newvals[2] = val
            elif dim == 't': newvals[3] = val

        self[:] = newvals


class Point(List):
    """A property which represents a point in some n-dimensional (up to 4)
    space.

    ``Point`` property values are stored in a :class:`PointValueList`, a
    list of integer or floating point values, one for each dimension.
    """

    def __init__(self,
                 ndims=2,
                 real=True,
                 **kwargs):
        """Create a ``Point`` property.

        :param int ndims: Number of dimensions.

        :param bool real: If ``True`` the point values are stored as
                          :class:`Real` values, otherwise they are
                          stored as :class:`Int` values.
        """

        default = kwargs.get('default', None)

        if default is None: default = [0] * ndims

        if real:
            default = [float(v) for v in default]

        if ndims < 1 or ndims > 4:
            raise ValueError('Only points of one to four '
                             'dimensions are supported')

        elif len(default) != ndims:
            raise ValueError('{} point values are required'.format(ndims))

        kwargs['default']    = default

        self._ndims   = ndims
        self._real    = real

        if real: listType = Real(clamped=True)
        else:    listType = Int( clamped=True)

        List.__init__(self,
                      listType=listType,
                      minlen=ndims,
                      maxlen=ndims,
                      **kwargs)


    def _makePropVal(self, instance):
        """Overrides :meth:`.ListPropertyBase._makePropVal`.

        Creates and returns a ``PointValueList`` instead of a
        ``PropertyValueList``, so callers get to use the convenience
        methods/attributes defined in the PVL class.
        """

        default = self.getAttribute(None, 'default', None)

        pvl = PointValueList(
            instance,
            name=self.getLabel(instance),
            values=default,
            itemCastFunc=self._listType.cast,
            itemEqualityFunc=self._listType._equalityFunc,
            itemValidateFunc=self._listType.validate,
            listValidateFunc=self.validate,
            listAttributes=self._defaultAttributes,
            itemAttributes=self._listType._defaultAttributes)

        return pvl


class ArrayProxy(propvals.PropertyValue):
    """A proxy class indended to encapsulate a ``numpy`` array.  ``ArrayProxy``
    instances are used by the :class:`Array` property type.


    An ``ArrayProxy`` is a :class:`.PropertyValue` which contains, and tries
    to act like, a ``numpy`` array.  Element access andassignment, and
    attribute access can be performed through the ``ArrayProxy``.


    All element assignments which occur via an ``ArrayProxy`` instance will
    result in notification of all registered listeners (see the
    :meth:`.PropertyValue.addListener` method). A limitation of this
    implementation is that notification will occur even if the assignment
    does not change the array values.


    The underlying ``numpy`` array is accessible via the :meth:`getArray`
    method. However, changes made directly to the numpy array will
    bypass the :class:`.PropertyValue` notification procedure.
    """


    def __init__(self, *args, **kwargs):
        """Create an ``ArrayProxy``. All arguments are passed through to the
        :meth:`.PropertyValue.__init__` method.
        """

        def defaultEquals(this, other):
            if isinstance(this,  ArrayProxy): this  = this .getArray()
            if isinstance(other, ArrayProxy): other = other.getArray()

            return np.all(this == other)

        kwargs['equalityFunc'] = kwargs.get('equalityFunc', defaultEquals)
        propvals.PropertyValue.__init__(self, *args, **kwargs)


    def get(self):
        """Overrides :meth:`.PropertyValue.get`. Returns this ``ArrayProxy``.
        """
        return self


    def getArray(self):
        """Returns a reference to the ``numpy`` array encapsulated by this
        ``ArrayProxy``.
        """
        return propvals.PropertyValue.get(self)


    def __getattr__(self, name):
        """Returns the attribute of the ``numpy`` array with the given name.
        """
        return getattr(self.getArray(), name)


    def __getitem__(self, *args, **kwargs):
        """Calls the ``__getitem``__ method of the ``numpy`` array. """
        return self.getArray().__getitem__(*args, **kwargs)


    def __setitem__(self, *args, **kwargs):
        """Calls the ``__setitem__`` method of the ``numpy`` array, and triggers
        notification of all registered listeners.
        """

        array = self.getArray()

        array.__setitem__(*args, **kwargs)

        notifState = self.getNotificationState()
        self.disableNotification()

        self.set(array)

        self.setNotificationState(notifState)
        self.propNotify()


class Array(props.PropertyBase):
    """A property which represents a ``numpy`` array. Each array is
    encapsulated within an :class:`ArrayProxy` instance.
    """

    def __init__(self, dtype=None, shape=None, resizable=True, **kwargs):
        """Create an ``Array`` property.

        .. warning:: If you set a ``default`` value here (see
                     :meth:`.PropertyBase.__init__`), *do not* use a ``numpy``
                     array - use a regular python list. It will be converted
                     in a ``numpy`` array internally. An equality test is made
                     on the ``default`` attribute, so if you use a ``numpy``
                     array, a :exc:`ValueError` will be raised, as ``numpy``
                     performs equality tests on an element-wise basis.

        :arg dtype:     ``numpy`` data type.

        :arg shape:     Initial shape of the array.

        :arg resizable: Defaults to ``True``. If ``False``, the array size
                        will be fixed to the ``shape`` specified
                        here. Different sized arrays will still be allowed, if
                        the ``allowInvalid`` parameter to
                        :meth:`.PropertyBase.__init__` is set to ``True``.
        """

        if dtype is None: dtype = np.float64
        if shape is None: shape = (4, 4)

        kwargs['dtype']     = dtype
        kwargs['shape']     = shape
        kwargs['resizable'] = resizable
        kwargs['default']   = kwargs.get('default', np.zeros(shape, dtype))

        props.PropertyBase.__init__(self, **kwargs)


    def _makePropVal(self, instance):
        """Overrides :meth`.PropertyBase._makePropVal`. Creates and returns
        an :class:`.ArrayProxy` for the given ``instance``.
        """

        default = self.getAttribute(None, 'default', None)
        ap      = ArrayProxy(
            instance,
            name=self.getLabel(instance),
            value=default,
            castFunc=self.cast,
            validateFunc=self.validate,
            allowInvalid=self._allowInvalid,
            **self._defaultAttributes)

        return ap


    def cast(self, instance, attributes, value):
        """Overrides :meth`.PropertyBase.cast`. Casts the given value to a
        ``numpy`` array (with the data type that was specified in
        :meth:`__init__`).
        """
        dtype = attributes['dtype']
        return np.array(value, dtype=dtype)


    def validate(self, instance, attributes, value):
        """Overrides :meth`.PropertyBase.validate`. If the given ``value`` has
        the wrong data type, or this ``Array`` is not resizable and the
        ``value`` has the wrong shape, a :exc:`ValueError` is raised.
        """
        props.PropertyBase.validate(self, instance, attributes, value)

        dtype     = attributes['dtype']
        shape     = attributes['shape']
        resizable = attributes['resizable']

        if value.dtype != dtype:
            raise ValueError('Invalid data type: {} (should be {})'.format(
                value.dtype, dtype))

        if (not resizable) and (value.shape != shape):
            raise ValueError('Invalid shape: {} (should be {})'.format(
                value.shape, shape))
