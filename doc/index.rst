
RSFile package |version|
========================


RSFile provides drop-in replacements for the classes of the :mod:`io` module, and for the :py:func:`open` builtin.

Its goal is to provide a cross-platform, reliable, and comprehensive file I/O API, with advanced features like fine-grained opening modes, shared/exclusive file record locking, thread-safety, cache synchronization, file descriptor inheritability, and handy stat getters (size, inode, times...).

Locking is performed using actual file locking capabilities of the OS, not by using separate files/directories as locking markers, or other fragile gimmicks. Unix users might particularly be interested by the workaround that this library provides, concerning the weird semantic of fcntl() locks (when any descriptor to a disk file is closed, the process loses ALL locks acquired on this file through any descriptor).

Note that RSFile only concerns I/O stream manipulation, not filesystem operations like pathutil or shutil do. And that it has no specific support for async I/O (although you may use non-blocking streams with it).

RSFile uses utilities scattered over the python stdlib (os, stat, fnctl, _pyio...), and accesses native APIs (like "Handles" on Windows) when it's necessary to achieve robust cross-platform interoperability. In particular, on Windows, it'll make use of `pywin32 <https://sourceforge.net/projects/pywin32/>`_ extensions if they are available, instead of relying on `ctypes`. And on Unix-like systems, it provides specific systems to make up for the flaws of `fcntl` locks.

Because RSFile adds multiple layers of securities to I/O streams, and is a pure python package, it is currently 3x to 10x slower than the C-backed :mod:`io` module from the stdlib. Speeding up RSFile would be possible (with cython, or cffi, or ctypes optimizations...), but not necessarily useful, since it can be used in parallel with :mod:`io` (one for security-critical file accesses, the other for high throughput). Be aware of some :ref:`rsfile_locking_caveats` though.

Compatibility-wise, RSFile is compliant with the stdlib test suite (except some testcases which check C-extension behaviours or "ResourceWarning" emitting). It may be used on regular files as well as on other stream types (anonymous pipes, named fifos, devices...), although its advanced features only work on "normal", seekable and lockable, files.

Beware, Windows users: `os.pipe()` returns anonymous pipes which appear seekable for stdlib io module ; `rsfile` corrects this and shows them as non-seekable.

.. note::
    Regarding exceptions encountered in RSFile:

    - wrong arguments raise ValueError or TypeError
    - some improper workflows, especially when locking, lead to RuntimeError
    - for the rest of file I/O troubles, the library will raise subclasses of **EnvironmentError**, which may depend on the backend used, and on whether or not you are under `the new OSError hierarchy <https://docs.python.org/3/library/exceptions.html#OSError>`_ ; so better catch them "defensively".

.. warning::
    The stdlib io module appeared with python2.6, and was still young on python2.7,
    so consider upgrading to the latest python2.7.X version to avoid corner-case buglets.

.. toctree::
	:maxdepth: 4

	rsopen.rst
	streams.rst
	locking_semantic.rst
	utilities_options.rst
	native_io_concepts.rst
