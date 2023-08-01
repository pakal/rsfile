#!/usr/bin/env python

import sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # security

from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: Information Technology",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Topic :: System :: Filesystems",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: Unix",
    "Operating System :: MacOS :: MacOS X",
]
assert all(classifiers), classifiers


setup(
    name='RSFile',
    version=read("VERSION"),
    author='Pascal Chambon',
    author_email='pythoniks@gmail.com',
    url='https://github.com/pakal/rsfile',
    license="http://www.opensource.org/licenses/mit-license.php",
    platforms=["any"],
    description="Advanced I/O file streams with fine-grained locking and creation options",
    classifiers=classifiers,
    long_description=read("README.rst"),

    packages=("rsfile", "rsfile.rsbackend", "rsfile.rstest", "rsfile.rstest.stdlib"),
)

