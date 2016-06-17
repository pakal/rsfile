RSFILE
================

RSFile provides drop-in replacements for the classes of the **io** module, and for the **open()** builtin.

These new streams aim at providing a cross-platform, reliable, and comprehensive synchronous file I/O API, with advanced features like fine-grained opening modes, shared/exclusive file record locking, thread-safety, cache synchronization, file descriptor inheritability, and handy stat getters (size, inode, times...). This comes at the cost of some performance though, since RSFile is currently pure-python.

This version 2.0 drops support for Python2.6, and puts RSFile in compliance with the numerous evolutions that happened to the I/O modules of the stdlib over the past years.

Tested on python2.7 and python3.3+, on windows and unix-like systems. *Should* work with IronPython/Jython/PyPy too, since it uses stdlib utilities and ctypes bridges.

**Learn more about RSFile : http://rsfile.readthedocs.io/**


INSTALLING
------------

Using pip is recommended, although installing from a checkout of the repository (via setup.py) also works:

$ pip install rsfile


QUICKSTART
------------

::

    from rsfile import rsopen

    with rsopen("myfile.txt", "w") as f:
        f.write(u"This string will be veeeeeryyyyy safely written to file.")

    with rsopen("myfile.txt", "WANISB", locking=False, thread_safe=False) as f:
        f.write(b"See the docs for info on these cool new modes and parameters.")
