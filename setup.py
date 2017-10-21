#!/usr/bin/env python
#
# setup.py - setuptools configuration for installing the fsleyes-props
# package.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#


from __future__ import print_function

import os.path as op
import            shutil

from setuptools import setup
from setuptools import find_packages
from setuptools import Command


basedir = op.dirname(__file__)

# Dependencies are listed in requirements.txt
install_requires = open(op.join(basedir, 'requirements.txt'), 'rt').readlines()

packages = find_packages(
    exclude=('doc', 'tests', 'dist', 'build', 'fsleyes_props.egg-info'))

# Extract the vesrion number from fsleyes_props/__init__.py
version = {}
with open(op.join(basedir, "fsleyes_props", "__init__.py"), 'rt') as f:
    for line in f:
        if line.startswith('__version__'):
            exec(line, version)
            break
version = version.get('__version__')

with open(op.join(basedir, 'README.rst'), 'rt') as f:
    readme = f.read()


class doc(Command):
    """Build the API documentation. """

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):

        docdir  = op.join(basedir, 'doc')
        destdir = op.join(docdir, 'html')

        if op.exists(destdir):
            shutil.rmtree(destdir)

        print('Building documentation [{}]'.format(destdir))

        import sphinx

        try:
            import unittest.mock as mock
        except:
            import mock

        mockedModules = [
            'fsl',
            'fsl.utils',
            'fsl.utils.async',
            'fsl.utils.weakfuncref',
            'fsleyes_widgets',
            'fsleyes_widgets.bitmapradio',
            'fsleyes_widgets.bitmaptoggle',
            'fsleyes_widgets.colourbutton',
            'fsleyes_widgets.elistbox',
            'fsleyes_widgets.floatslider',
            'fsleyes_widgets.floatspin',
            'fsleyes_widgets.notebook',
            'fsleyes_widgets.rangeslider',
            'numpy',
            'numpy.linalg',
            'wx',
            'wx.adv',
        ]

        mockobj       = mock.MagicMock()
        mockedModules = { m : mockobj for m in mockedModules}

        with mock.patch.dict('sys.modules', **mockedModules):
            sphinx.main(['sphinx-build', docdir, destdir])


setup(

    name='fsleyes-props',
    version=version,
    description='[wx]Python event programming framework',
    long_description=readme,
    url='https://git.fmrib.ox.ac.uk/fsl/fsleyes/props',
    author='Paul McCarthy',
    author_email='pauldmccarthy@gmail.com',
    license='Apache License Version 2.0',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules'],

    packages=packages,
    install_requires=install_requires,
    setup_requires=['pytest-runner', 'sphinx', 'sphinx-rtd-theme', 'mock'],
    tests_require=['pytest',
                   'mock',
                   'coverage',
                   'pytest-cov',
                   'pytest-html',
                   'pytest-runner'],
    test_suite='tests',

    cmdclass={
        'doc' : doc
    }
)
