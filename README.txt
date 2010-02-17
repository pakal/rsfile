
Release 1.0alpha1
17 feb 2010
By Pascal Chambon


Hello everyone,

I'm presently pleased to announce the first release 
of the "rsfile" package, in its alpha1 stage.

Whatszepoint ? will you ask. Libraries to access files, 
we already have quite a bunch of them, without counting 
the new io module of the stdlib!

And that's precisely where rsfile fits: it's a partial 
reimplementation of the io module, as backward compatible 
as possible, and which offers a set of new - and possibly 
very useful - features.

Ever dreamed of cross-platform, reliable and easy file 
locking, disk synchronization, stream inheritance management,
size() and uid() getters, O_SYNC or (O_CREAT|O_EXCL) semantics ?

Thanks to thin wrappers to native APIs, rsfile might spare you a
ton of headaches, as it offers such things in an object-oriented
and portable fashion, with the backup of a rather comprehensive
test suite (which currently passes on win32/linux/freebsd - I'm
currently building more virtual machines to track platform-specific
gotchas).

Power users might be afraid by the fact that rsfile is currently 
a pure-python package, far slower than the latest C implementation 
of the io module. But patience, focus is currently set on semantic 
and robustness, cython extensions and other optimizations will come 
later on. B-)

Since the primary goal is to stabilize the API, you're highly invited 
to browse the doc below, and to send feedback on method names, advanced
mode flags, wished functionalities etc.
http://bytebucket.org/pchambon/python-rock-solid-tools/wiki/index.html

For those eager to play with new streams (and why not, run the test 
suite on their exotic OS and send me potential error outputs), 
here is the repository:
http://bitbucket.org/pchambon/python-rock-solid-tools/downloads/

Enjoy, 
regards, 
Pascal (aka pythoniks)

PS : for those who have already encountered the ugly flaws of fcntl()
locks, I must precise that rsfile solves most of them, at least if you
make it your default file access gateway.

=====

To install RockSolidTools packages, simply copy them into a folder of your python path (eg. site-packages).
Note that to successfully run the test suite, you'll need the latest svn checkout of python 2.6 or 2.7, since some behaviour
bugs have only been fixed quite recently.
