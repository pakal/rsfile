#!/usr/bin/env python

from distutils.core import setup

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py



setup(name='RsFile',
      version='1.0',
      description='RockSolidTools File I/O Implementation',
      author='Pascal Chambon',
      author_email='pythoniks@gmail.com',
      url='http://bitbucket.org/pchambon/python-rock-solid-tools/',
      packages=['rsfile', 'rsbackends', "rstest"],
      cmdclass = {'build_py':build_py},
     )


