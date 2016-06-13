
RSFile package |version|
========================


RSFile provides drop-in replacements for the classes of the ``io`` module, and for the ``open()`` builtin.

These new streams aim at providing a cross-platform, reliable, and comprehensive file I/O API, with advanced features like fine-grained opening modes, shared/exclusive file record locking, thread-safety, cache synchronization, file descriptor inheritability, and handy stat getters (size, inode...). Note that it only concerns I/O stream manipulation, not filesystem operations like pathutil or shutil do.

RSFile uses utilities scattered over the python stdlib (os, stat, fnctl, _pyio...), and accesses native APIs (like "Handles" on Windows) when it's necessary to achieve robust cross-platform interoperability. In particular, on Windows, it'll make use of ``pywin32`` if available, instead of just relying on stdlib and ``ctypes``.

Because RSFile adds multiple layers of securities to I/O streams, and is a pure python package, it is currently 3x to 10x slower than the C-backed ``io`` module from the stdlib. Using both together (one for security-critical file accesses, the other for high throughputs) is possible but with some caveats XXXXXXXXXX.

Compatibility-wise, RSFile is compliant with the stdlib test suite, except some testcases which check C-extension behaviours or "ResourceWarning" emitting. It may be used on regular files as well as on other stream types (anonymous pipes, named fifos, devices...), although its advanced features only work on "normal", seekable and lockable, files.

.. note::
    The stdlib io module appeared with python2.6 and was still young on python2.7,
    so consider upgrading to the latest python2.7.X version to avoid corner-case buglets.

.. toctree::
	:maxdepth: 3
   
	rsopen.rst
	rsfile_streams.rst
	utilities_options.rst	
	native_io_concepts.rst
