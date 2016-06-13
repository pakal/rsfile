RSFILE
================

This lib (currently in version 1.1) is getting updated to support latest python2/3 versions.

Lots of stuffs have been moving in the last years regarding IO streams, exception hierarchies, file descriptor inheritance and all that stuff, so it's time to move towards a version 2.0

INSTALLING
------------
TODO


=======================================




Release V1.1
April 2011
By Pascal Chambon



I'm pleased to announce the first bugfix release of the "RSFile" package.

Issues addressed:
- rejection of unicode keys in kwargs arguments, in some versions of py2.6
- indentation bug swallowing some permission errors on file opening


RSFile aims at providing python with a cross-platform, reliable, and comprehensive file
I/O API. It's actually a partial reimplementation of the io module, as compatible possible 
(it passes latest stdlib io tests), which offers a set of new - and possibly very useful - features:
shared/exclusive file record locking, cache synchronization, advanced opening flags, handy stat 
getters (size, inode...), shortcut I/O functions etc. 

Unix users might particularly be interested by the workaround that this library provides, concerning 
the catastrophic fcntl() lock semantic (when any descriptor to a file is closed, your process loses ALL 
locks acquired on it through other streams).

RSFile has been tested with py2.6, py2.7, and py3.2, on win32, linux and freebsd systems, 
and should theoretically work with IronPython/Jython/PyPy (on Mac OS X too).

The technical documentation of RSFile includes a comprehensive description
of concepts and gotchas encountered while setting up this library, which could
prove useful to anyone interested in getting aware about gory file I/O details.

The implementation is currently pure-python, as integration with the C implementation of io module
raises lots of issues. So if you need heavy performances, standard python streams will
remain necessary. But for most programs and scripts, which just care about data integrity, RSFile 
should be a proper choice.

Downloads:
http://pypi.python.org/pypi/RSFile/1.1

Documentation:
http://bytebucket.org/pchambon/python-rock-solid-tools/wiki/index.html


PS : Due to miscellaneous bugs of python core and stdlib io modules which have been fixed relatively recently, 
it's advised to have an up-to-date minor version of python (be it 2.6, 2.7 or 3.2) to benefit from RSFile.
