#!/usr/bin/env python
#
# cli.py - Generate command line arguments for a HasProperties object.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

"""Generate command line arguments for a :class:`.HasProperties` instance.

This module provides the following functions:

 .. autosummary::
    addParserArguments
    applyArguments
    generateArguments

The ``addParserArguments`` function is used to add arguments to an
``ArgumentParser`` object for the properties of a ``HasProperties`` class. The
simplest way to do so is to allow the ``addParserArguments`` function to
automatically generate short and long arguments from the property names::

    >>> import argparse
    >>> import props

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

import properties as props


log = logging.getLogger(__name__)


def _String(parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.String`
    property.
    
    :param parser:   An ``ArgumentParser`` instance.
    
    :param propCls:  A ``HasProperties`` class or instance.

    :param propObj:  The ``PropertyBase`` class.
    
    :param propName: Name of the property.
    
    :param propHelp: Custom help text for the property.
    
    :param shortArg: String to use as the short argument.
    
    :param longArg:  String to use as the long argument.

    """
    parser.add_argument(shortArg, longArg, help=propHelp) 


def _Choice(parser,
            propObj,
            propCls,
            propName,
            propHelp,
            shortArg,
            longArg,
            choices=None,
            default=None,
            useAlts=True):
    """Adds an argument to the given parser for the given :class:`.Choice`
    property. See the :func:`_String` documentation for details on the
    parameters.

    Only works with ``Choice`` properties with string options (unless
    the ``choices`` argument is provided).

    :arg choices:       If not ``None``, assumed to be list of possible
                        choices for the property. If ``None``, the possible
                        choices are taken from the :meth:`.Choice.getChoices`
                        method.

    :arg default:       If not ``None``, gives the default value. Otherwise,
                        the ``default`` constraint of the :class:`.Choice`
                        object is used.

    :arg useAlts:       If ``True`` (the default), alternate values for the 
                        choices are added as options (see the :class:`.Choice`
                        class).
    """

    if choices is None:
        choices = propObj.getChoices()

    if useAlts:
        alternates = propObj.getAlternates()

        for altList in alternates:
            choices += [a for a in altList]
        
    if default is None:
        default = propObj.getConstraint(None, 'default')

    # I'm assuming that all choices and
    # alternates have the same type
    cType   = type(choices[0])
    choices = set(choices)

    parser.add_argument(shortArg,
                        longArg,
                        type=cType,
                        help=propHelp,
                        choices=choices)
    
    
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


def _Bounds(parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.Bounds`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """ 
    ndims = getattr(propCls, propName)._ndims
    real  = getattr(propCls, propName)._real
    if real: bType = float
    else:    bType = int
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        metavar='N',
                        type=bType,
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


def _Colour(parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.Colour`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        metavar=('R', 'G', 'B', 'A'),
                        type=float,
                        nargs=4) 

    
def _ColourMap(
        parser, propObj, propCls, propName, propHelp, shortArg, longArg):
    """Adds an argument to the given parser for the given :class:`.ColourMap`
    property. See the :func:`_String` documentation for details on the
    parameters.
    """ 
    # Attempt to retrieve a matplotlib.cm.ColourMap
    # instance given its name
    def parse(cmapName):
        try:
            import matplotlib.cm as mplcm
            
            cmapKeys   = mplcm.cmap_d.keys()
            cmapNames  = [cm.name for cm in mplcm.cmap_d.values()]
            
            lCmapNames = map(lambda s: s.lower(), cmapNames)
            lCmapKeys  = map(lambda s: s.lower(), cmapKeys)

            cmapName = cmapName.lower()
            
            try:    idx = lCmapKeys .index(cmapName)
            except: idx = lCmapNames.index(cmapName)

            cmapName = cmapKeys[idx]
            
            return mplcm.get_cmap(cmapName)
        
        except:
            raise argparse.ArgumentTypeError(
                'Unknown colour map: {}'.format(cmapName))

    # TODO List all registered colour maps as choices.
    parser.add_argument(shortArg,
                        longArg,
                        help=propHelp,
                        type=parse,
                        metavar='CMAP',
                        action='store')

    
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
                if propCls._shortArgs[propName] in shortArgs.values() or \
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
            
            if (c not in shortArgs.values()) and (c not in exclude):
                shortArgs[propName] = c
                break

    if any([name not in shortArgs for name in propNames]):
        raise RuntimeError('Could not generate default short arguments '
                           'for HasProperties object {} - please provide '
                           'custom short arguments via a _shortArgs '
                           'attribute'.format(propCls.__name__))
        
    return shortArgs


def applyArguments(hasProps,
                   arguments,
                   propNames=None,
                   xformFuncs=None,
                   longArgs=None):
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

        xform   = xformFuncs.get(propName, lambda v : v)
        argName = longArgs.get(propName, propName)
        argVal  = getattr(arguments, argName, None)

        if argVal is None: continue

        argVal = xform(argVal)

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
            log.warn('No CLI parser function for property {} '
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
                      exclude=''):
    """Given a ``HasProperties`` instance, generates a list of arguments which
    could be used to configure another instance in the same way.
    
    :param hasProps:     The ``HasProperties`` instance.

    :param useShortArgs: If ``True`` the short argument version is used instead
                         of the long argument version.

    :param xformFuncs:   A dictionary of ``{property name -> function}``
                         mappings, which can be used to perform some arbitrary
                         transformation of property values.

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
        xform   = xformFuncs.get(propName, lambda v: v)
        propVal = xform(getattr(hasProps, propName))

        # TODO Should I skip a property 
        #      if its value is None?
        if propVal is None:
            continue

        if useShortArgs: argKey =  '-{}'.format(shortArgs[propName])
        else:            argKey = '--{}'.format(longArgs[ propName])

        # TODO This logic could somehow be stored
        #      as default transform functions for 
        #      the respective types
        if isinstance(propObj, (props.Bounds, props.Point, props.Colour)):
            values = ['{}'.format(v) for v in propVal]
            
        elif isinstance(propObj, props.ColourMap):
            values = [propVal.name]
            
        elif isinstance(propObj, props.Boolean):
            values = None
            if not propVal: argKey = None
        else:
            if propVal is None: values = None
            else:               values = [propVal]

        if argKey is not None: args.append(argKey)
        if values is not None: args.extend(values)

    return map(str, args)
