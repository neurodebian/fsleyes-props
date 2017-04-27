Props
=====

The `props` package is an event programming framework, which includes the
ability for automatic CLI generation and, optionally, automatic GUI generation
(if [wxPython](http://www.wxpython.org) is present).


Dependencies
------------


All of the dependencies of `props` are listed in the
[requirements.txt](requirements.txt) file. `props` can be used without
wxPython, but GUI functionality will not be available.


Documentation
-------------

`props` is documented using [sphinx](http://http://sphinx-doc.org/). You can
build the API documentation by installing `sphinx` and `sphinx-rtd-theme`, and
running:

    python setup.py doc

The HTML documentation will be generated and saved in the `doc/html/` directory.


Example usage
-------------


```python
>>> import props

>>> class PropObj(props.HasProperties):
>>>     myProperty = props.Boolean()

>>> myPropObj = PropObj()


# Access the property value as a normal attribute:
>>> myPropObj.myProperty = True
>>> myPropObj.myProperty
>>> True


# access the props.Boolean instance:
>>> myPropObj.getProp('myProperty')
>>> <props.prop.Boolean at 0x1045e2710>


# access the underlying props.PropertyValue object
# (there are caveats for List properties):
>>> myPropObj.getPropVal('myProperty')
>>> <props.prop.PropertyValue instance at 0x1047ef518>


# Receive notification of property value changes
>>> def myPropertyChanged(value, *args):
>>>     print('New property value: {}'.format(value))

>>> myPropObj.addListener(
>>>    'myProperty', 'myListener', myPropertyChanged)

>>> myPropObj.myProperty = False
>>> New property value: False


# Remove a previously added listener
>>> myPropObj.removeListener('myListener')
```
