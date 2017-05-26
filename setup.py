#!/usr/bin/env python
#
# setup.py - setuptools configuration for installing the fsleyes-props
# package.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#


from __future__ import print_function

import               os
import os.path    as op
import subprocess as sp
import               shutil
import               pkgutil

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

with open(op.join(basedir, 'README.md'), 'rt') as f:
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

        env     = dict(os.environ)
        ppath   = list(env.get('PYTHONPATH', '').split(':'))
        dirname = pkgutil.get_loader('fsl').get_filename()
        dirname = op.dirname(dirname)
        dirname = op.abspath(op.join(dirname, '..'))
        ppath.append(dirname)

        env['PYTHONPATH'] = op.pathsep.join(ppath)

        print('Building documentation [{}]'.format(destdir))

        sp.call(['sphinx-build', docdir, destdir], env=env)


setup(

    name='fsleyes-props',

    version=version,

    description='Python event programming framework, using wxPython',
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
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules'],

    packages=packages,

    cmdclass={
        'doc' : doc
    },

    install_requires=install_requires,
    setup_requires=['pytest-runner'],
    tests_require=['pytest',
                   'mock',
                   'coverage',
                   'pytest-cov',
                   'pytest-html',
                   'pytest-runner'],
    test_suite='tests',
)
