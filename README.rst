RSFILE
================

RSFile provides drop-in replacements for the classes of the `io` module, and for the `open` builtin.

These new streams aim at providing a cross-platform, reliable, and comprehensive synchronous file I/O API, with advanced features like fine-grained opening modes, shared/exclusive file record locking, thread-safety, cache synchronization, file descriptor inheritability, and handy stat getters (size, inode, times...). At the cost of some performance though.

This version 2.0 drops support for Python2.6, and puts RSFile in compliance with the numerous evolutions that happened to the "io" module and the "open" builtin over the past years.

Tested on py2.7 and py3.3+, on windows and unix-like systems. *Should* work with IronPython/Jython/PyPy too, since it uses stdlib utilities and ctypes bridges.

Documentation : http://rsfile.readthedocs.io/


INSTALLING
------------

Using pip is recommended, although installing from a checkout of the repository (via setup.py) also works:

$ pip install rsfile
