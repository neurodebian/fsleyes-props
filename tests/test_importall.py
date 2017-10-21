#!/usr/bin/env python
#
# test_importall.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#


import pkgutil


def test_importall():
    import fsleyes_props as props

    for _, module, _ in pkgutil.iter_modules(props.__path__, 'fsleyes_props.'):
        __import__(module)
