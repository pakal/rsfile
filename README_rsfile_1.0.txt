
Release V1.0
19 may 2010
By Pascal Chambon


Hello everyone,

I'm presently pleased to announce the first stable release of the "RSFile" package.

RSFile aims at providing python with a cross-platform, reliable, and comprehensive file
I/O API. It's actually a partial reimplementation of the io module, as compatible as possible 
(it passes latest stdlib io tests), and which offers a set of new - and possibly very useful - features:
shared/exclusive file record locking, cache synchronization, advanced opening flags, handy stat 
getters (size, inode...), shortcut I/O functions etc. 

Unix users might particularly be interested by the workaround that this library provides, concerning 
the catastrophic fcntl() lock semantic (when any descriptor to a file is closed, your process loses ALL 
locks acquired on it through other streams).

RSFile has been tested with py2.6, py2.7, and py3k, on win32 and unix-like systems, and should work 
with IronPython/Jython/PyPy.

The technical documentation of RSFile also includes a comprehensive description
of concepts and gotchas encountered while setting up this library, which could
prove useful to anyone interested in getting aware about gory file I/O details.

The implementation is currently pure-python, as integration with the C implementation of io module
raises lots of many issues. So if you need heavy performances, standard python streams will
remain necessary. But for many programs and scripts, which just care about data integrity, RSFile 
should be a good choice.

Downloads:
http://pypi.python.org/pypi/RSFile/1.0
http://bitbucket.org/pchambon/python-rock-solid-tools/downloads/

Documentation:
http://bytebucket.org/pchambon/python-rock-solid-tools/wiki/index.html

Enjoy, 
regards, 
Pascal

PS : due to miscellaneous bugs of python core and stdlib io modules which have been fixed quite recently, 
it's advised to have an up-to-date minor version of python (be it 2.6, 2.7 or 3k) to benefit from RSFile.