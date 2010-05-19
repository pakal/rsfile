
RSFile package v1.0 
======================


RSFile aims at providing python with a cross-platform, reliable, and comprehensive file 
I/O API (that is, file stream manipulation, not filesystem operations like shutil does).
Features include shared/exclusive file record locking, cache synchronization, advanced opening flags, 
and handy stat getters (size, inode...). 

Stdlib file stream APIs suffer indeed from their history and C/unix origins : 
they are scattered all over lots of modules (os, stat, fnctl, tempfile...), 
poorly object-oriented, full of platform-specific behaviours, and worst of all 
they sometimes rely on castrated implementations, like windows' libc compatibility layer.

That's why RSFile offers more than a simple interfacing/adaptation layer : it 
also wraps native file objects (like win32 "Handles"), to ensure a maximal flexibility 
of the API.

The main idea behind the design of the API, is that "cross-platform" doesn't mean 
"lowest denominator", and that "high level" doesn't mean "poor". That's why, even though 
RSFile can transparently replace python's built-in file object, it also provides 
lots of additional methods and parameters to finely tweak the streams you need : file chunk 
locking, timeout handling, disk synchronization, atomic file creation, handle inheritance, 
thread safety...

This modules currently provides pure-python reimplementations of parts of the stdlib **io** modules,
and is compliant with stdlib test suites.
It mainly relies on stdlib modules and ctypes extensions (on windows, if pywin32 is available, it is used instead).

The 1.x series will remain in pure python, but future versions might run under cython, for performance considerations.

.. warning::
    The stdlib io module is still slightly suffering from it youth, so if you encounter problems with 
    RSFile (or, more likely, with running its test suite), consider upgrading to the latest stable version 
    (or to the development one) of python. 
    
    Furthermore, early python 2.6 versions a problems with "from __future__ import unicode_literals", preventing
    the use of the "\*\*kwargs" construct (and of rsfile) in some cases, with a weird error "*<funcname>() keyword 
    arguments must be strings*". Just update your python distribution if this problem occurs.

.. toctree::
	:maxdepth: 3
   
	rsopen.rst
	rsfile_streams.rst
	utilities_options.rst	
	native_io_concepts.rst