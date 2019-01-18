
Rsfile 2.2
============

* Python 3.6 and Python 3.7 compatibility


Rsfile 2.1
============

* Add some tweaks to mimick the more tolerant behaviour of python2.7 open(), 
  regarding the mixing of str and unicode
* Add script for aggregate coverage reporting
* Strengthen tests of rsopen() usage errors


Rsfile 2.0
=============

* Switch from Mercurial to Git
* Remove python2.6 support and its polyfills
* Move backends and test suites inside rsfile package
* Conform rsfile to the behaviour of latest "io" module and "open" builtin
* Make rsfile work against py33, py34 and py35, by leveraging their stdlib test suites
* Rename "win32" to "windows" everywhere (even pywin32 extensions actually handle x64 system)
* Improve the I/O benchmark runner
* Cache decorated methods to boost performances
* Add support for the new "x" mode flag in rsopen()
* Fix the corner case of uninitialized streams
* Tweak the excessive verbosity of locking tests
* Handle exceptions when closing raw streams (stream is marked as closed anyway)
* Normalize the naming of backend modules
* Fix bugs with __getattr__() lookup forwarding
* Use C/N flags for file existence on opening (-/+ supported but deprecated)
* Automatically compare the behaviour of all possible open modes, between stdlib/io and rsfile
* Autogenerate equivalence matrix for file opening modes, using python-tabulate.
* Switch from distutils to setuptools for setup.py
* Add support for the new "opener" parameter of open() builtin
* Strengthen tests around fileno/handle reuse and duplication
* Fix bug regarding improper value of file "modification_time" on windows
* Add implicit flush() before every sync()
* Remove heavy star imports from pywin32 backend
* Roughly test sync() parameters, via performance measurements
* Rename file "uid()" to "unique_id()", to prevent confusion with "user id" (but an alias remains)
* Fix nasty bug where file unique_id could be None in internal registries
* Add lots of defensive assertions
* Make FileTimes repr() more friendly
* Add support for the wrapping of [non-blocking] pipes/fifos
* Reject the opening of directories properly
* Reorganize and cleanup sphinx docs
* Improve docstrings of added/updated methods/attributes
* Explain the file locking semantic better
* Update and correct typos in the "I/O Overview" article
* Document lots of corner cases: thread safety, reentrancy, sync parameters, file-share-delete semantic...
* Remove the now obsolete "multi_syscall_lock" (thread-safe interface does better)
* Integrate tests and doc building with Tox
* Fix bug with windows/ctypes backend on python3.5 (OVERLAPPED structure was broken)
* Add tests for the behaviour of streams after a fork()
* Add optmizations for systems without fork (no need for multiprocessing locks then)
* Normalize "__future__" imports and code formatting
* Review and document the exception types used
* Cleanup/DRY tons of obsolete TODOs and comments
* Better document the CAVEATS of rsfile, regarding fcntl and interoperability with other I/O libs
* Add standard files to the repository (readme, contributing, changelog etc.)
* Integrate with Travis CI


Rsfile 1.1
=============

* Workaround for old python2.6 bug, rejecting unicode strings in **kwargs
* Fixed indentation problem in exception handlers


Rsfile 1.0
=============

Initial release, supporting py26, py27, and py31
