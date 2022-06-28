RSFILE
================

.. image:: https://ci.appveyor.com/api/projects/status/x002hlal3qwiavsa/branch/master
    :target: https://ci.appveyor.com/project/pakal/rsfile

RSFile provides pure-python drop-in replacements for the classes of the **io** module, and for the **open()** builtin.

Its goal is to provide a cross-platform, reliable, and comprehensive synchronous file I/O API, with advanced features like fine-grained opening modes, shared/exclusive file record locking, thread-safety, disk cache synchronization, file descriptor inheritability, and handy *stat* getters (size, inode, times...).

Locking is performed using actual file record locking capabilities of the OS, not by using separate files/directories as locking markers, or other fragile gimmicks.

.. END OF PART KINDA SHARED WITH SPHINX DOC INDEX ..

Possible use cases for this library: concurrently writing to logs without ending up with garbled data, manipulating sensitive data like disk-based databases, synchronizing heterogeneous producer/consumer processes when multiprocessing semaphores aren't an option, etc.

Tested on Python 3.6+, on windows and unix-like systems. *Should* work with IronPython/Jython/PyPy too, since it uses stdlib utilities and ctypes bridges.

**Read the documentation here: http://rsfile.readthedocs.io/**


INSTALL
------------

::

    $ pip install rsfile


QUICKSTART
------------

.. code-block:: python

    from rsfile import rsopen

    with rsopen("myfile.txt", "w") as f:
        f.write("This string will be veeeeeryyyyy safely written to file.")

    with rsopen("myfile.txt", "WANISB", locking=False, thread_safe=False) as f:
        f.write(b"See the docs for info on these cool new modes and parameters.")


See CONTRIBUTING.rst for development advice (testing, benchmarking...)
