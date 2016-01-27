#!/usr/bin/env python
#
# __init__.py - Sets up the props package namespace.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""``props`` is a framework for event-driven programming using python
descriptors, similar in functionality to, and influenced by
`Enthought Traits <http://code.enthought.com/projects/traits/>`_.
  
-------------
Example usage
-------------

::

    >>> import props

    >>> class PropObj(props.HasProperties):
            myProperty = props.Boolean()

    >>> myPropObj = PropObj()


    # Access the property value as a normal attribute:
    >>> myPropObj.myProperty = True
    >>> myPropObj.myProperty
    True


    # access the props.Boolean instance:
    >>> myPropObj.getProp('myProperty')
    <props.prop.Boolean at 0x1045e2710>


    # access the underlying props.PropertyValue object
    >>> myPropObj.getPropVal('myProperty')
    <props.prop.PropertyValue instance at 0x1047ef518>


    # Receive notification of property value changes
    >>> def myPropertyChanged(value, *args):
            print('New property value: {}'.format(value))

    >>> myPropObj.addListener(
           'myProperty', 'myListener', myPropertyChanged)

    >>> myPropObj.myProperty = False
    New property value: False


    # Remove a previously added listener
    >>> myPropObj.removeListener('myListener')


-----------------
Package structure
-----------------


To use ``props``, your first step will be to define a subclass of
:class:`.HasProperties`, which contains one or more :class:`.PropertyBase`
class attributes (see the :mod:`.properties_types` module for the available
types).


Once you have an instance of your ``HasProperties`` class, you can then create
a GUI for it using the functions defined in the :mod:`.build` and
:mod:`.widgets` modules, and the GUI specification building blocks defined in
the :mod:`build_parts` module. You can also generate a command-line interface
using the functions defined in the :mod:`.cli` module.


All of the classes and functions referred to above are available in the
``props`` namespace, so you only need to ``import props`` to access them. You
will however need to call the :func:`initGUI` function if you want to use any
of the GUI generation functionality, before they are made available at the
``props`` namespace level.


---------------
Boring overview
---------------


Lots of the code in this package is probably very confusing. First of all, you
will need to understand python descriptors.  Descriptors are a way of adding
properties to python objects, and allowing them to be accessed as if they were
just simple attributes of the object, but controlling the way that the
attributes are accessed and assigned.


The following link provides a good overview, and contains the ideas
which form the basis for the implementation in this package:


 -  http://nbviewer.ipython.org/urls/gist.github.com/\
ChrisBeaumont/5758381/raw/descriptor_writeup.ipynb


And if you've got 30 minutes, this video gives a very good
introduction to descriptors:


 - http://pyvideo.org/video/1760/encapsulation-with-descriptors


A :class:`.HasProperties` subclass contains a collection of
:class:`.PropertyBase` instances as class attributes. When an instance of the
``HasProperties`` class is created, a :class:`.PropertyValue` object is
created for each of the ``PropertyBase`` instances (or a
:class:`~.PropertyValueList` for :class:`.ListPropertyBase` instances).  Each
of these ``PropertyValue`` instances encapsulates a single value, of any type
(a ``PropertyValueList`` instance encapsulates multiple ``PropertyValue``
instances).  Whenever this value changes, the ``PropertyValue`` instance
notifies any registered listeners of the change.  


^^^^^^^^^^^^
Notification
^^^^^^^^^^^^


Application code may be notified of property changes by registering a callback
listener on a ``PropertyValue`` object, via the equivalent methods:

  - :meth:`.HasProperties.addListener`
  - :meth:`.PropertyBase.addListener`
  - :meth:`.PropertyValue.addListener`

Such a listener will be notified of changes to the ``PropertyValue`` object
managed by the ``PropertyBase`` object, and associated with the
``HasProperties`` instance. For ``ListPropertyBase`` properties, a listener
registered through one of the above methods will be notified of changes to the
entire list.  Alternately, a listener may be registered with individual items
contained in the list (see :meth:`.PropertyValueList.getPropertyValueList`).


^^^^^^^^^^
Validation
^^^^^^^^^^


When a ``PropertyValue`` accepts a new value, it passes the value to the
:meth:`.PropertyBase.validate` method of its parent ``PropertyBase`` instance
to determine whether the new value is valid.  The ``PropertyValue`` object
may allow its underlying value to be set to something invalid, but it will
tell registered listeners whether the new value is valid or
invalid. ``PropertyValue`` objects can alternately be configured to raise a
:exc:`ValueError` on an attempt to set them to an invalid value, but this has
some caveats - see the ``PropertyValue`` documentation. Finally, to make things
more confusing, some ``PropertyBase`` types will configure their
``PropertyValue`` objects to perform implicit casts when the property value is
set.


The default validation logic of most ``PropertyBase`` objects can be
configured via *constraints*. For example, the :class:`.Number` property
allows ``minval`` and ``maxval`` constraints to be set.  These may be set via
``PropertyBase`` constructors, (i.e. when it is defined as a class attribute
of a ``HasProperties`` definition), and may be queried and changed on
individual ``HasProperties`` instances via the
:meth:`.HasProperties.getConstraint`/:meth:`.HasProperties.setConstraint`
methods; similarly named methods are also available on ``PropertyBase``
instances. Some ``PropertyBase`` classes provide additional convenience
methods for accessing their constraints (e.g. :meth`.Choice.addChoice`).


^^^^^^^^^^^^^^^^^^^^^^^^^^^
Binding and Synchronisation
^^^^^^^^^^^^^^^^^^^^^^^^^^^


Properties from different ``HasProperties`` instances may be bound to each
other, so that changes in one are propagated to the other - see the
:mod:`.bindable` module.  Building on this is the :mod:`.syncable` module and
its :class:`.SyncableHasProperties` class, which allows a one-to-many (one
parent, multiple children) synchronisation hierarchy to be maintained, whereby
all the properties of a child instance are by default synchronised to those of
the parent, and this synchronisation can be independently enabled/disabled for
each property. To use this functionality, simply inherit from the
``SyncableHasProperties`` class instead of the ``HasProperties`` class.


------------
API overview
------------


The following classes are provided as building-blocks for your application
code:

.. autosummary::
   :nosignatures:

   ~props.properties.HasProperties
   ~props.syncable.SyncableHasProperties
   ~props.properties_types.Object
   ~props.properties_types.Boolean
   ~props.properties_types.Int
   ~props.properties_types.Real
   ~props.properties_types.Percentage
   ~props.properties_types.String
   ~props.properties_types.FilePath
   ~props.properties_types.Choice
   ~props.properties_types.List
   ~props.properties_types.Colour
   ~props.properties_types.ColourMap
   ~props.properties_types.Bounds
   ~props.properties_types.Point 


The following functions are provided to manage command-line argument
generation and parsing:

.. autosummary::
   :nosignatures:

   ~props.cli.applyArguments
   ~props.cli.addParserArguments
   ~props.cli.generateArguments


The following functions are provided for serialisation/deserialisation of
property values to/from strings (equivalent methods are also available on
:class:`.HasProperties` instances):

.. autosummary::
   :nosignatures:

   ~props.serialise.serialise
   ~props.serialise.deserialise


The following classes are provided for you to create GUI specifications:

.. autosummary::
   :nosignatures:

   ~props.build_parts.ViewItem
   ~props.build_parts.Button
   ~props.build_parts.Toggle
   ~props.build_parts.Label
   ~props.build_parts.Widget
   ~props.build_parts.Group
   ~props.build_parts.NotebookGroup
   ~props.build_parts.HGroup
   ~props.build_parts.VGroup 


If the :func:`initGUI` function is called, the following GUI-related functions
will be made available in the ``props`` package namespace:


.. autosummary::
   :nosignatures:

   ~props.widgets.makeWidget
   ~props.widgets.makeListWidgets
   ~props.widgets.makeSyncWidget
   ~props.widgets.bindWidget
   ~props.widgets.unbindWidget
   ~props.widgets.bindListWidgets
   ~props.build.buildGUI
   ~props.build.buildDialog
"""

import sys
import logging


log = logging.getLogger(__name__)


from properties import (
    HasProperties,
    DisabledError)

from properties_value import (
    WeakFunctionRef)

from bindable import (
    bindPropVals,
    propValsAreBound)

from properties_types import (
    Object,
    Boolean,
    Int,
    Real,
    Percentage,
    String,
    FilePath,
    Choice,
    List,
    Colour,
    ColourMap,
    Bounds,
    Point,
    Array)

from syncable import (
    SyncableHasProperties)

from cli import (
    applyArguments,
    addParserArguments,
    generateArguments)

from serialise import (
    serialise,
    deserialise)

from build_parts import (
    ViewItem, 
    Button,
    Toggle,
    Label,
    Widget, 
    Group, 
    NotebookGroup,
    HGroup, 
    VGroup)


def initGUI():
    """If you wish to use GUI generation functionality, calling this function
    will add the relevant functions to the ``props`` package namespace.
    """

    mod = sys.modules[__name__]

    from widgets import (
        makeWidget,
        makeListWidgets,
        makeSyncWidget,
        bindWidget,
        unbindWidget,
        bindListWidgets)

    from build import (
        buildGUI,
        buildDialog)

    mod.makeWidget      = makeWidget     
    mod.makeListWidgets = makeListWidgets
    mod.makeSyncWidget  = makeSyncWidget 
    mod.bindWidget      = bindWidget     
    mod.unbindWidget    = unbindWidget   
    mod.bindListWidgets = bindListWidgets
    mod.buildGUI        = buildGUI       
    mod.buildDialog     = buildDialog 
