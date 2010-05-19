#!/usr/bin/env python

import sys
from distutils.core import setup

try:
    from distutils.command.build_py import build_py_2to3 as build_py
    print("Compiling Py2to3")
except ImportError:
    from distutils.command.build_py import build_py
    print("Normal compilation")

sys.argv.append("install")

setup(name='RSFile',
      version='1.0',
      description='RockSolidTools File I/O Implementation',
      author='Pascal Chambon',
      author_email='pythoniks@gmail.com',
      url='http://bitbucket.org/pchambon/python-rock-solid-tools/',
      packages=("rsfile", "rsfile.stdlib", "rsbackends", "rstest", "rstest.stdlib"),
      cmdclass = {'build_py':build_py},
     )


