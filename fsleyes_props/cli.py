#!/usr/bin/env python
#
# cli.py - Generate command line arguments for a HasProperties object.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

"""Generate command line arguments for a :class:`.HasProperties` instance.

This module provides the following functions:

 .. autosummary::
    :nosignatures:

    addParserArguments
    applyArguments
    generateArguments

The ``addParserArguments`` function is used to add arguments to an
``ArgumentParser`` object for the properties of a ``HasProperties`` class. The
simplest way to do so is to allow the ``addParserArguments`` function to
automatically generate short and long arguments from the property names::

    >>> import argparse
    >>> import fsleyes_props as props

    >>> class MyObj(props.HasProperties):
            intProp  = props.Int()
            boolProp = props.Boolean()

    >>> parser = argparse.ArgumentParser('MyObj')
    >>> props.addParserArguments(MyObj, parser)

    >>> parser.print_help()
    usage: MyObj [-h] [-b] [-i INT]

    optional arguments:
        -h, --help            show this help message and exit
        -b, --boolProp
        -i INT, --intProp INT

Now, if we have a ``MyObj`` instance, and some arguments::

    >>> myobj = MyObj()

    >>> args = parser.parse_args(['-b', '--intProp', '52'])

    >>> print myobj
    MyObj
      boolProp = False
       intProp = 0

    >>> props.applyArguments(myobj, args)
    >>> print myobj
    MyObj
      boolProp = True
       intProp = 52

If you want to customise the short and long argument tags, and the help text,
for each property, you can pass them in to the ``addParserArguments``
function::

    >>> shortArgs = {'intProp' : 'r',              'boolProp' : 't'}
    >>> longArgs  = {'intProp' : 'TheInt',         'boolProp' : 'someBool'}
    >>> propHelp  = {'intProp' : 'Sets int value', 'boolProp' : 'Toggles bool'}

    >>> parser = argparse.ArgumentParser('MyObj')
    >>> props.addParserArguments(MyObj,
                                 parser,
                                 shortArgs=shortArgs,
                                 longArgs=longArgs,
                                 propHelp=propHelp)
    >>> parser.print_help()
    usage: MyObj [-h] [-t] [-r INT]

    optional arguments:
      -h, --help            show this help message and exit
      -t, --someBool        Toggles bool
      -r INT, --TheInt INT  Sets int value

Or, you can add the short and long arguments, and the help text, as specially
named class attributes of your ``HasProperties`` class or instance::

    >>> class MyObj(props.HasProperties):
            intProp  = props.Int()
            boolProp = props.Boolean()
            _shortArgs = {
                'intProp'  : 'r',
                'boolProp' : 't'
            }
            _longArgs = {
                'intProp'  : 'TheInt',
                'boolProp' : 'someBool'
            }
            _propHelp = {
                'intProp' : 'Sets int value',
                'boolProp' : 'Toggles bool'
            }

    >>> parser = argparse.ArgumentParser('MyObj')
    >>> props.addParserArguments(MyObj, parser)

    >>> parser.print_help()
    usage: MyObj [-h] [-t] [-r INT]

    optional arguments:
      -h, --help            show this help message and exit
      -t, --someBool        Toggles bool
      -r INT, --TheInt INT  Sets int value

    >>> args = parser.parse_args('--someBool -r 23413'.split())
    >>> myobj = MyObj()
    >>> props.applyArguments(myobj, args)
    >>> print myobj
    MyObj
      boolProp = True
       intProp = 23413

The ``generateArguments`` function, as the name suggests, generates command
line arguments from a ``HasProperties`` instance::

    >>> props.generateArguments(myobj)
    ['--someBool', '--TheInt', '23413']

The ``generateArguments`` and ``applyArguments`` functions optionally accept a
set of *transform* functions which, for ``generateArguments``, take the value
of a property, and return some transformation of that property, suitable to be
used as a command line argument value. The transform functions passed to the
``applyArguments`` function perform the reverse transformation.  Transforms
are useful for properties which cannot easily be converted to/from strings,
and also for properties where the value you wish users to pass in on the
command line does not correspond exactly to the value you wish the property to
be given.

For example::

    >>> class MyObject(props.HasProperties):
            showBlah = props.Boolean(default=True)

    >>> shortArgs = {'showBlah' : 'hb'}
    >>> longArgs  = {'showBlah' : 'hideBlah'}
    >>> xforms    = {'showBlah' : lambda b : not b }

    >>> parser = argparse.ArgumentParser('MyObject')
    >>> props.addParserArguments(MyObject,
                                 parser,
                                 shortArgs=shortArgs,
                                 longArgs=longArgs)

    >>> myobj = MyObject()
    >>> myobj.showBlah = False

    >>> props.generateArguments(myobj,
                                shortArgs=shortArgs,
                                longArgs=longArgs,
                                xformFuncs=xforms)
        ['--hideBlah']

In this example, we can use the same transform function for the reverse
operation::

    >>> myobj2 = MyObject()
    >>> args   = parser.parse_args(['--hideBlah'])
    >>> props.applyArguments(myobj2,
                             args,
                             xformFuncs=xforms,
                             longArgs=longArgs)
    >>> print myobj2
        MyObject
            showBlah = False

The ``cli`` module supports the following property types:

.. autosummary::
   :nosignatures:

   _String
   _Choice
   _Boolean
   _Int
   _Real
   _Percentage
   _Bounds
   _Point
   _Colour
   _ColourMap

"""


import logging

import sys
import argparse

from . import properties       as props
from . import properties_types as ptypes


log = logging.getLogger(__name__)


def _String(parser,
            propObj,
            propCls,
            propName,
            propHelp,
            shortArg,
            longArg,
            atype=str):
    """Adds an argument to the given parser for the given :class:`.String`
    property.

    :param parser:   An ``ArgumentParser`` instance.

    :param propCls:  A ``HasProperties`` class or instance.

    :param propObj:  The ``PropertyBase`` class.

    :param propName: Name of the property.

    :param propHelp: Custom help text for the property.

    :param shortArg: String to use as the short argument.

    :param longArg:  String to use as the long argument.

    :param atype:    Data type to expect (defaults to ``str``). This allows
                     the conversion type to be overridden for some, but not
                     all, property types.
    """
    parser.add_argument(shortArg, longArg, help=propHelp, type=atype)


def _Choice(parser,
            propObj,
            propCls,
            propName,
            propHelp,
            shortArg,
            longArg,
            **kwargs):
    """Adds an argument to the given parser for the given :class:`.Choice`
    property. See the :func:`_String` documentation for details on the
    parameters.

    Only works with ``Choice`` properties with string options (unless
    the ``choices`` argument is provided). See the ``allowStr`` parameter
    for :class:`.Choice` instances.

    All of the described arguments must be speified as keyword arguments.

    :arg choices: If not ``None``, assumed to be list of possible
                  choices for the property. If not provided, the possible
                  choices are taken from the :meth:`.Choice.getChoices`
                  method. If explicitly passed in as ``None``, the argument
                  will be configured to accept any value.

    :arg default: If not ``None``, gives the default value. Otherwise,
                  the ``default`` attribute of the :class:`.Choice`
                  object is used.

    :arg useAlts: If ``True`` (the default), alternate values for the
                  choices are added as options (see the :class:`.Choice`
                  class). n.b. This flag will have no effect if  ``choices``
                  is explicitly set to ``None``, as desrcibed above.

    :arg metavar: If ``None`` (the default), the available choices for
                  this property will be shown in the help text. Otherwise,
                  this string will be shown instead.
    """

    choices = kwargs.pop('choices', 'notspecified')
    default = kwargs.pop('default', None)
    useAlts = kwargs.pop('useAlts', True)
    metavar = kwargs.pop('metavar', None)

    if choices == 'notspecified':
        choices = propObj.getChoices()

    if useAlts and choices is not None:
        alternates = propObj.getAlternates()

        for altList in alternates:
            choices += [a for a in altList]

    if default is None:
        default = propObj.getAttribute(None, 'default')

    # Make sure that only unique
    # choices are set as options.
    if choices is not None:

        # We could just convert to a set, but
        # this would not preserve ordering, so
        # we'll uniquify the list the hard way.
        choices = [str(c) for c in choices]
        unique  = []

        for c in choices:
            if c not in unique:
                unique.append(c)

        choices = unique

    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        choices=choices,
                        metavar=metavar)


def _Boolean(parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.Boolean`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """
    # Using store_const instead of store_true,
    # because if the user doesn't set this
    # argument, we don't want to explicitly
    # set the property value to False (if it
    # has a default value of True, we don't
    # want that default value overridden).
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        action='store_const',
                        const=True)


def _Int(parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.Int`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        metavar='INT',
                        type=int)


def _Real(parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.Real`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        metavar='REAL',
                        type=float)


def _Percentage(
        parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.Percentage`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        metavar='PERC',
                        type=float)


def _Bounds(parser,
            propObj,
            propCls,
            propName,
            propHelp,
            shortArg,
            longArg,
            atype=None):
    """Adds an argument to the given parser for the given :class:`.Bounds`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """
    ndims = getattr(propCls, propName)._ndims
    real  = getattr(propCls, propName)._real

    metavar = tuple(['LO', 'HI'] * ndims)

    if atype is None:
        if real: atype = float
        else:    atype = int

    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        metavar=metavar,
                        type=atype,
                        nargs=2 * ndims)


def _Point(parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.Point`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """
    ndims = getattr(propCls, propName)._ndims
    real  = getattr(propCls, propName)._real
    if real: pType = float
    else:    pType = int
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        metavar='N',
                        type=pType,
                        nargs=ndims)


def _Colour(parser,
            propObj,
            propCls,
            propName,
            propHelp,
            shortArg,
            longArg,
            alpha=True):
    """Adds an argument to the given parser for the given :class:`.Colour`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """
    if alpha:
        metavar = ('R', 'G', 'B', 'A')
        nargs   = 4
    else:
        metavar = ('R', 'G', 'B')
        nargs   = 3
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        metavar=metavar,
                        type=float,
                        nargs=nargs)


def _ColourMap(parser,
               propObj,
               propCls,
               propName,
               propHelp,
               shortArg,
               longArg,
               parseStr=False,
               choices=None,
               metavar=None):
    """Adds an argument to the given parser for the given :class:`.ColourMap`
    property.

    :arg parseStr: If ``False`` (the default), the parser will be configured
                   to parse any registered ``matplotlib`` colour map name.
                   Otherwise, the parser will accept any string, and assume
                   that the ``ColourMap`` property is set up to accept it.

    :arg choices:  This parameter can be used to restrict the values that
                   will be accepted.

    :arg metavar:  If ``choices`` is not ``None``, they will be shown in the
                   help text, unless this string is provided.

    See the :func:`_String` documentation for details on the other parameters.
    """

    # Attempt to retrieve a matplotlib.cm.ColourMap
    # instance given its name
    def parse(cmapName):
        try:

            import matplotlib.cm as mplcm

            cmapKeys   = list(mplcm.cmap_d.keys())
            cmapNames  = [mplcm.cmap_d[k].name for k in cmapKeys]

            lCmapNames = [s.lower() for s in cmapNames]
            lCmapKeys  = [s.lower() for s in cmapKeys]

            cmapName = cmapName.lower()

            try:    idx = lCmapKeys .index(cmapName)
            except: idx = lCmapNames.index(cmapName)

            cmapName = cmapKeys[idx]

            return mplcm.get_cmap(cmapName)

        except:
            raise argparse.ArgumentTypeError(
                'Unknown colour map: {}'.format(cmapName))

    if choices is not None:
        choices = [c.lower() for c in choices]

    if parseStr: aType = str.lower
    else:        aType = parse

    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        type=aType,
                        choices=choices,
                        metavar=metavar)


def _getShortArgs(propCls, propNames, exclude=''):
    """Generates unique single-letter argument names for each of the names in
    the given list of property names. Any letters in the exclude string are
    not used as short arguments.

    :param propCls:   A ``HasProperties`` class.

    :param propNames: List of property names for which short arguments
                      are to be generated.

    :param exclude:   String containing letters which should not be used.
    """

    letters   = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    shortArgs = {}

    for propName in propNames:

        # if '_shortArgs' is present on the hasProps
        # object, and there is an entry for the
        # current property, use that entry.
        if hasattr(propCls, '_shortArgs'):
            if propName in propCls._shortArgs:

                # throw an error if that entry
                # has already been used, or
                # should be excluded
                if propCls._shortArgs[propName] in list(shortArgs.values()) or\
                   propCls._shortArgs[propName] in exclude:
                    raise RuntimeError(
                        'Duplicate or excluded short argument for property '
                        '{}.{}: {}'.format(
                            propCls.__name__,
                            propName,
                            propCls._shortArgs[propName]))

                shortArgs[propName] = propCls._shortArgs[propName]
                continue

        # use the first unique letter in the
        # property name or, if that doesn't
        # work, in the alphabet
        for c in propName + letters:

            if (c not in list(shortArgs.values())) and (c not in exclude):
                shortArgs[propName] = c
                break

    if any([name not in list(shortArgs) for name in propNames]):
        raise RuntimeError('Could not generate default short arguments '
                           'for HasProperties object {} - please provide '
                           'custom short arguments via a _shortArgs '
                           'attribute'.format(propCls.__name__))

    return shortArgs


def applyArguments(hasProps,
                   arguments,
                   propNames=None,
                   xformFuncs=None,
                   longArgs=None,
                   **kwargs):
    """Apply arguments to a ``HasProperties`` instance.

    Given a ``HasProperties`` instance and an ``argparse.Namespace`` instance,
    sets the property values of the ``HasProperties`` instance from the values
    stored in the ``Namespace`` object.

    :param hasProps:   The ``HasProperties`` instance.

    :param arguments:  The ``Namespace`` instance.

    :param propNames:  List of property names to apply. If ``None``, an attempt
                       is made to set all properties. If not ``None``, the
                       property values are set in the order specified by this
                       list.

    :param xformFuncs: A dictionary of ``{property name -> function}``
                       mappings, which can be used to transform the value given
                       on the command line before it is assigned to the
                       property.

    :param longArgs:   Dict containing ``{property name : longArg}`` mappings.

    All other keyword arguments are passed through to the ``xformFuncs``
    functions.
    """

    if propNames is None:
        propNames, propObjs = hasProps.getAllProperties()
    else:
        propObjs = [hasProps.getProp(name) for name in propNames]

    if longArgs is None:
        if hasattr(hasProps, '_longArgs'): longArgs = hasProps._longArgs
        else:                              longArgs = dict(zip(propNames,
                                                               propNames))

    if xformFuncs is None:
        xformFuncs = {}

    for propName, propObj in zip(propNames, propObjs):

        xform   = xformFuncs.get(propName, lambda v, **kwa : v)
        argName = longArgs.get(propName, propName)
        argVal  = getattr(arguments, argName, None)

        # An argVal of None means that no value
        # was passed in for this property
        if argVal is None:
            continue

        argVal = xform(argVal, **kwargs)

        log.debug('Setting {}.{} = {}'.format(
            type(hasProps).__name__,
            propName,
            argVal))

        setattr(hasProps, propName, argVal)


def addParserArguments(
        propCls,
        parser,
        cliProps=None,
        shortArgs=None,
        longArgs=None,
        propHelp=None,
        extra=None,
        exclude=''):
    """Adds arguments to the given ``argparse.ArgumentParser`` for the
    properties of the given ``HasProperties`` class or instance.

    :param propCls:        A ``HasProperties`` class. An instance may
                           alternately be passed in.

    :param parser:         An ``ArgumentParser`` to add arguments to.

    :param list cliProps:  List containing the names of properties to add
                           arguments for. If ``None``, and an attribute called
                           ``_cliProps``' is present on the ``propCls`` class,
                           the value of that attribute is used. Otherwise an
                           argument is added for all properties.

    :param dict shortArgs: Dict containing ``{propName: shortArg}`` mappings,
                           to be used as the short (typically single letter)
                           argument flag for each property. If ``None``, and
                           an attribute called ``_shortArgs`` is present on
                           the ``propCls`` class, the value of that attribute
                           is used. Otherwise, short arguments are
                           automatically generated for each property.

    :param dict longArgs:  Dict containing ``{propName: longArg}`` mappings,
                           to be used as the long argument flag for each
                           property. If ``None``, and an attribute called
                           ``_longArgs`` is present on the ``propCls`` class,
                           the value of that attribute is used. Otherwise, the
                           name of each property is used as its long argument.

    :param dict propHelp:  Dict containing ``{propName: helpString]``
                           mappings, to be used as the help text for each
                           property. If ``None``, and an attribute called
                           ``_propHelp`` is present on the ``propCls`` class,
                           the value of that attribute is used. Otherwise, no
                           help string is used.

    :param dict extra:     Any property-specific settings to be passed through
                           to the parser configuration function (see e.g. the
                           :func:`_Choice` function). If ``None``, and an
                           attribute called ``_propExtra`` is present on the
                           ``propCls`` class, the value of that attribute is
                           used instead.

    :param str exclude:    String containing letters which should not be used
                           as short arguments.
    """

    if isinstance(propCls, props.HasProperties):
        propCls = propCls.__class__

    if cliProps is None:
        if hasattr(propCls, '_cliProps'):
            cliProps = propCls._cliProps
        else:
            cliProps = propCls.getAllProperties()[0]

    if propHelp is None:
        if hasattr(propCls, '_propHelp'): propHelp = propCls._propHelp
        else:                             propHelp = {}

    if longArgs is None:
        if hasattr(propCls, '_longArgs'): longArgs = propCls._longArgs
        else:                             longArgs = dict(zip(cliProps,
                                                              cliProps))

    if shortArgs is None:
        if hasattr(propCls, '_shortArgs'):
            shortArgs = propCls._shortArgs
        else:
            shortArgs = _getShortArgs(propCls, cliProps, exclude)

    if extra is None:
        if hasattr(propCls, '_propExtra'):
            extra = propCls._propExtra
        else:
            extra = {prop : {} for prop in cliProps}

    for propName in cliProps:

        propObj    = propCls.getProp(propName)
        propType   = propObj.__class__.__name__
        parserFunc = getattr(
            sys.modules[__name__],
            '_{}'.format(propType), None)

        if parserFunc is None:
            log.warning('No CLI parser function for property {} '
                        '(type {})'.format(propName, propType))
            continue

        shortArg  =  '-{}'.format(shortArgs[propName])
        longArg   = '--{}'.format(longArgs[ propName])
        propExtra = extra.get(propName, {})

        parserFunc(parser,
                   propObj,
                   propCls,
                   propName,
                   propHelp.get(propName, None),
                   shortArg,
                   longArg,
                   **propExtra)


def generateArguments(hasProps,
                      useShortArgs=False,
                      xformFuncs=None,
                      cliProps=None,
                      shortArgs=None,
                      longArgs=None,
                      exclude='',
                      **kwargs):
    """Given a ``HasProperties`` instance, generates a list of arguments which
    could be used to configure another instance in the same way.

    :param hasProps:     The ``HasProperties`` instance.

    :param useShortArgs: If ``True`` the short argument version is used instead
                         of the long argument version.

    :param xformFuncs:   A dictionary of ``{property name -> function}``
                         mappings, which can be used to perform some arbitrary
                         transformation of property values.


    All other keyword arguments are passed through to the ``xformFuncs``
    functions.

    See the :func:`addParserArguments` function for descriptions of the other
    parameters.
    """
    args = []

    if cliProps is None:
        if hasattr(hasProps, '_cliProps'):
            cliProps = hasProps._cliProps
        else:
            cliProps = hasProps.getAllProperties()[0]

    if longArgs is None:
        if hasattr(hasProps, '_longArgs'): longArgs = hasProps._longArgs
        else:                              longArgs = dict(zip(cliProps,
                                                               cliProps))

    if shortArgs is None:
        if hasattr(hasProps, '_shortArgs'):
            shortArgs = hasProps._shortArgs
        else:
            shortArgs = _getShortArgs(hasProps, cliProps, exclude)

    if xformFuncs is None:
        xformFuncs = {}

    for propName in cliProps:
        propObj = hasProps.getProp(propName)
        xform   = xformFuncs.get(propName, lambda v, **kwa: v)
        propVal = xform(getattr(hasProps, propName), **kwargs)

        # TODO Should I skip a property
        #      if its value is None?
        if propVal is None:
            continue

        if useShortArgs: argKey =  '-{}'.format(shortArgs[propName])
        else:            argKey = '--{}'.format(longArgs[ propName])

        # TODO I should be using the (new)
        #      serialise module for this.
        #      This would incorporate the
        #      TODO below.

        # TODO This logic could somehow be stored
        #      as default transform functions for
        #      the respective types
        if isinstance(propObj, (ptypes.Bounds, ptypes.Point, ptypes.Colour)):
            values = ['{}'.format(v) for v in propVal]

        elif isinstance(propObj, ptypes.ColourMap):
            values = [propVal.name]

        elif isinstance(propObj, ptypes.String):
            values = ['"{}"'.format(propVal)]

        elif isinstance(propObj, ptypes.Boolean):
            values = None
            if not propVal: argKey = None
        else:
            if propVal is None: values = None
            else:               values = [propVal]

        if argKey is not None: args.append(argKey)
        if values is not None: args.extend(values)

    return [str(a) for a in args]
