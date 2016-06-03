#!/usr/bin/env python

"""RockSolidTools' file I/O implementation

RSFile aims at providing python with a cross-platform, reliable, and
comprehensive file I/O API (that is, file stream manipulation, not
filesystem operations like shutil does).

Features include shared/exclusive file record locking, cache synchronization,
advanced opening flags, and handy stat getters (size, inode...).

Tested on py2.7, py3k, on windows and unix-like systems. Should work with IronPython/Jython/PyPy too.
"""

classifiers = """\
Development Status :: 5 - Production/Stable
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Programming Language :: Python
Topic :: System :: Filesystems
Topic :: Software Development :: Libraries :: Python Modules
Operating System :: Microsoft :: Windows
Operating System :: Unix
Operating System :: MacOS :: MacOS X
"""

doclines = [line.strip() for line in __doc__.split("\n")]


import sys
from distutils.core import setup

try:
    from distutils.command.build_py import build_py_2to3 as build_py
    print("Compiling via Py2to3")
except ImportError:
    from distutils.command.build_py import build_py
    print("Normal python build")


setup(name='RSFile',
      version='1.2',
      author='Pascal Chambon',
      author_email='pythoniks@gmail.com',
      url='http://bitbucket.org/pchambon/python-rock-solid-tools/',
      license="http://www.opensource.org/licenses/mit-license.php",
      platforms=["any"],
      description=doclines[0],
      classifiers=filter(None, classifiers.split("\n")),
      long_description=" ".join(doclines[2:]),
      # "rstest", "rstest.stdlib" TODO - can't be included atm because they use __file__, incompatible with EGGS
      packages=("rsfile", "rsfile.rsbackend", "rsfile.rstest", "rsfile.rstest.stdlib"),
      cmdclass={'build_py': build_py},
      zip_safe=False,  # tests refer to __file__...
     )

