#!/usr/bin/env python

"""
FIXME

RockSolidTools' file I/O implementation

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

import sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from setuptools import setup


setup(
    name='RSFile',
    version='1.2',
    author='Pascal Chambon',
    author_email='pythoniks@gmail.com',
    url='http://bitbucket.org/pchambon/python-rock-solid-tools/',
    license="http://www.opensource.org/licenses/mit-license.php",
    platforms=["any"],
    description=doclines[0],
    classifiers=filter(None, classifiers.split("\n")),
    long_description=" ".join(doclines[2:]),

    #package_dir={'': 'src'},
    packages=("rsfile", "rsfile.rsbackend", "rsfile.rstest", "rsfile.rstest.stdlib"),

    # test_suite='your.module.tests',

    use_2to3=True,
    #convert_2to3_doctests=['src/your/module/README.txt'],
    #use_2to3_fixers=['your.fixers'],
    #use_2to3_exclude_fixers=['lib2to3.fixes.fix_import'],
)

