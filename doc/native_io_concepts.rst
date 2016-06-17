
Overview of File I/O Concepts and Gotchas
==========================================


RSfile is a relatively small library, but its birth was unexpectedly long and painful,
and one may wonder why such a basic subject as I/O streams require days and days spent
reading technical documentation.

So here is a summary of some (more or less happy) discoveries made during this journey
in what we may call "the I/O Hell", as well as some details on solutions which were chosen by RSFile.



Glossary
----------

  
File data
    The payload of the file, i.e the byte stream that you read/write/truncate in it 

File metadata
    Additional information like file sizes, times, permissions etc. 

Disk file
    This is the set of physical disk blocks on which your file (both metadata and data) 
    is eventually stored. This is also the only place where data can really be considered as persistent.
    One sometimes employs the expression "written to ferrous oxide" for disk files, although with SSDs it's not true anymore.
    The logical representation of a disk file, is its filesystem **inode**.

Open file object
    This kernel-level object represents an open stream to a file. As such, it 
    contains references to the target disk file, as well as transient state information relative 
    to the open stream (current file offset, miscellaneous caching and locking information...).
    In the case of stream inheritance, or other stream duplication mechanisms, a single file object
    can end up being shared by several processes. Creating too many of these objects is what leads to
    the sly 'too many open files' error.

File descriptor
    This type (C file descriptor on Posix systems, file Handle on windows platforms)
    mostly acts as a "pointer" to an open file object. It is typically an integer used as an index in
    a per-process "open file table". Several of these "open file references" can target the same open file objects,
    via inheritance (when forking) or dedicated duplication functions (dup() on posix, DuplicateHandle() on windows).
    Synchronization systems may then be required to avoid race conditions around the commonly shared file seek() offset.
    On some platforms, file descriptors have specific attributes (like permissions, locks, inheritability options...),
    and the rest of their "state" is that the open file object they represent.
    Note that compatibility aliases may exist, like the windows libc which exposes a "C file descriptor" actually
    wrapping a native windows Handle.

    .. note::
        Theoretically, "handles" should be used to designate pointers to "high level" stream objects, like C's FILE structures, or python's I/O stream instance. However, Windows uses the term as a synonym for "native file descriptor", so it is this semantic which is used by RSFile.

Buffering and caching
    They both consist in keeping data into an intermediate storage (most of the time, main memory), between a data
    source and its consumer. However, they can be distinguished by their intent. Buffers are used as intermediary
    storage for data which can't be directly accessed (eg. because data transfers are only possible in *block mode*),
    or to optimize transfers (reordering of I/O operations, reducing of disk seeks). Caching is rather meant to
    reduce latency, by providing fast access to frequently used data.
    In practice however, buffering and caching purposes are often combined, so the distinction is not that relevant,
    and these terms will be used quite interchangeably in the rest of this document.






Stream layers
------------------

In languages liek Python, file I/O streams are actually made of numerous layers, among which:

- high level objects (eg. the classes of the :mod:`io` module)
- file descriptors
- open file objects
- disk device

Depending on platforms and APIs used, native stream settings (access permissions, file locks...) are carried
by file descriptors or by open file objects. In such conditions, obtaining a safe and cross-platform behaviour 
requires some precautions :

- Considering, as much as possible *file descriptor -> open file object* couples as inseparable entities. 
  This implies avoiding descriptor duplications, and only sharing streams via their top-most level, i.e python I/O 
  stream objects.
- Carefully crafting the code, when sharing low level structures is unavoidable, for examples in stream inheritance 
  operations. Operating systems offer lots of functions and flags are available to customize the behaviour of each layer.

High level chains like that provided by RSFile (and which mimick the `io` module), offer abstractions which hide most of these implementation details, but not all.




Stream inheritance
---------------------------

Inheritance of file objects between parent and child processes isn't a simple subject,
especially if you want to play with different stream types (FILE*, ostream, filenos...), and different process
creation methods (spawn(), fork(), CreateProcess()), in several operating systems.

In the case of RSFile however, in which native file handles are used on each platform, 
a somehow unified behaviour can be obtained. By default, RSFile streams are NOT inheritable, 
but they can be made so at opening time.

Then, to achieve inheritance, three operations must be done.

- Creating stream(s) with an *inheritable* parameter set to True

- Spawning a new process thanks to a "RSFile compatible" call.

    - On windows, the standard call "CreateProcess()" is fine.
    - On unix-like systems, a fork+exec is necessary: fork() alone doesn't do the whole job, as all 
      file descriptors are ALWAYS duplicated to the child process ; only exec()
      can handle the closing of unwanted streams (see FD_CLOEXEC). Note that on these systems, spawn() is usually
      a wrapper around fork+exec, so it should work too.
      
- Providing the child process with integer file(s) descriptor(s) of stream(s) to be inherited. 
  Basic IPC mechanisms like command line arguments should suffice most of the time. Once retrieved, 
  just wrap this file descriptor with a python I/O stream, and all should go on well.

Note that if you use libraries like the stdlib's *multiprocessing* package, these two last 
tasks may be transparently performed for you, with python streams being pickled, transferred, 
and then restored in the new process, sometimes thanks to some low level routines taking
care of the transfer of handle access permissions between processes (eg. DuplicateHandle() on windows).


.. rubric::
    Nota: multiprocessing and multithreading

Some race conditions can appear on unix-like systems, if one of your threads forks while another one
is setting up a stream. Indeed, several stream settings can only be applied by subsequent fcntl() calls,
not opening-time flags. So a child process might abnormally inherit a newly created stream.

But issues between multiprocessing and multithreading far overwhelm this subject, anyway.
Let's recall, for example, a quite neglected fact: forking and multithreading HATE each other.
Basically, only the thread issuing the fork() will be duplicated to the new process, so many data 
structures, like threading locks, which were manipulated by other threads at that moment, 
might be left in a stale state in the child process. This may lead to deadlocks or crashes, if this
data is then used by the child process. And in the case of modules like "logging", which are commonly
used by secondary threads, troubles may come very soon.

So if you want to use both multithreading and multiprocessing, in any case you had better
either tame your threads before forking (CF atfork() specifications, or the python-atfork module), 
or issue an exec() immediately after forking to clean the process' data (that's visibly the way spawn() works). 

    
    
Stream locking
------------------------

Stream locking is a particularly acute issue in file I/O, since several threads
may often want to write to the same file streams (eg. standard output streams redirected to a file),
and several process may want to access the same disk files simultaneously (eg. shared logs).

Some file operations are specified as atomic (eg. atomic "appends" on unix), but they are heavily dependent on
the operating system, the fileystem used, the size of data written, the flags used at file opening etc. 
Since furthermore such specification details are easily overlooked by kernel programmers, relying on them may 
sound like a dangerous idea.

That's why RSFile uses several types of locks, to ensure your data won't get corrupted by simultaneous writes.
These locks are recursive, i.e as *threading.RLock*, they allow the same client to acquire them several
times, and need to be released the same number of time as they've been acquired.
Specific protections are setup to detect events like fork(), and reset data structures which make no sense anymore in the child process.


Inter-threads locking
^^^^^^^^^^^^^^^^^^^^^^^^^

Inside a process, the locking of file objects isn't much different from the locking of any
data structure, standard threading locks may thus be used. However, the *io* library of python,
and its set of modular streams, requires some care to achieve a proper thread synchronization system.

Indeed, if the principle of "composed streams" affords a great flexibility (a text streams wraps a bufferred stream, which wraps a raw stream..), it comes at the cost of losing the notion of "public method".

Depending on the chaining of different IOBase instances, these will be directly accessible, or instead wrapped in other objects. This is embarrassing concerning thread-safety : in contemplation of the moment where it might be used as
"top-level" object, each stream type would be tempted to implement its own mutex system, and this is both
error-prone and performance-hindering.

To solve the problem, RSFile uses some kind of "thread-safe interface" pattern : each class 
inheriting IOBase shall implement its logic in a thread-unsafe manner, and it's up to each factory
functions (like rsfile.rsopen()) to wrap the top-level object of the IO chain inside a thread-safe
adapter (a transparent wrapper which simply ensures that only one thread at a time may access the
methods and properties of the stream).

This system may prevent several micro-optimizations that the presence of the GIL and the semantic
of some methods would allow. However, the simplicity and maintainability of the RSFile API comes at this cost.
And when speed matters, it's still possible to create streams without any thread locking system, anyway.


Inter-related-processes locking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The inheritability of system semaphores allows an interesting optimization: when a python stream is created 
as *inheritable* and wrapped with a thread-safe interface, RSFile used an interprocess semaphore for the latter, 
instead of a standard threading lock.

Thus, if this instance gets inherited as a whole (eg. via multiprocessing module), parent and child processes will
share a handle to the same open file object **and** a handle to the same semaphore, allowing for a quite easy 
synchronisation between their respective access. 

This synchronization is particularly interesting in this case of parent-child stream sharing, since the file 
pointer (contained in the unique open file object) is common to all related processes. So without synchronization, not
only may related process corrupt each other's writes, but they also may read/write/truncate files at the wrong offset.


Inter-unrelated-processes locking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here begins the hard core part. In a dream world, a process having sufficient privileges would simply lock a file for reading
and writing, perform its I/O operations on it, and then release the locks. But it can't be so simple: a "file"
is actually made of lots of stream layers, each having different features depending on the platform, and lots of points have
to be decided, like the extent of the ownership of the lock (is it per-process, per-thread, per file descriptor, per open
file object ?), the level of enforcement of the locking, or its reentrancy.

The marvellous thing is, kernel programmers have managed to disagree on about any of these points.
So let's have a brief overview of lock families available to us.



Common features
#################
    
- All following locking systems allow both shared (for read-only operations) and exclusive (for writing operation) locks.

- They are never based on thread identity (only process and file data structures are taken into account).

- Except in emulation cases (eg. when flock() locks are simple wrappers around fcntl() ones, like on freebsd), 
  different types of locks are not supposed to be compatible. At best they'll ignore each other, at worst 
  (like when they're used together in the same process) they may interfere and cause some trouble.



Windows LockFile
#################


**Mandatory, per-handle, non reentrant lock, allowing bytes range locking.**

- Once a file area is locked through a handle, no other handle, in this process or another one, can access
  this area in a way incompatible with the lock type (shared or exclusive). This also means that a handle can't be used
  to write to an area that it has locked as "shared".
   
- Forbidden read/write operations will fail immediately, incompatible locking attempts through other handles/processes 
  will block (unless a "non-blocking" flag is set), and trying to lock several times the same bytes with the same handle
  will result in a deadlock.
  
- There is no merging/splitting of locked ranges: unlocking calls must provide as arguments a bytes range identical 
  to one previously locked.

- Remaining locks are removed automatically by the system (but possibly after some delay), when a handle is closed or the
  process is shut down.

- Remote windows shares (like CIFS/Samba) should behave the same way as local disks, regarding file locks.



Unix Flock
#################

**Advisory, per-open-file, reentrant lock, only dealing with the whole file (no bytes range locking).** 

- All handles pointing to the open file object on which the flock() call was issued, have ownership on the lock. 
  This means that different file descriptors duplicated in the same process, as well as different file
  descriptors inherited between processes, can have access to a locked file simultaneously.

- Locking a file several times simply updates the type of locking (exclusive or shared).
  However, this operation is not guaranteed to be atomic (other processes might take ownership of the bytes range 
  during upgrade/downgrade). Note that in any case, a single unlocking call will suffice to undo all previous locking calls.

- NFS shares have a complicated history with these locks, eg. see the flock() manual for details about support and emulation depending on linux kernel version..

.. warning::
  On several platforms, these locks are actually emulated via fcntl() locks, so they don't follow this semantic but
  the one described below.




Unix Fcntl
################

.. note::
    This lock is also known as Posix lock.
    
    On recent platforms, **SystemV lockf()** locks are actually just wrappers around fcntl() locks, so we won't study here their initial semantic.

**Advisory, per-process, rentrant lock, allowing bytes range locking.**

- Write or read operations which don't use fcntl locks will not be hindered by these locks, 
  unless mandatory locking has been activated on this particular filesystem and file node (but you had 
  better `avoid mandatory locking <http://www.mjmwired.net/kernel/Documentation/filesystems/mandatory-locking.txt>`_).
 
- Inside a process, it makes no difference whether a file/range has been locked via one file descriptor or another:
  fcntl locks concerns the disk file, and belong to the whole process.
    
- bytes range locking is very flexible:
    - Consecutive areas can be freed in a single unlock() call (bytes range merging)
    - It is possible to release only part of a bytes range (bytes range splitting)
    - Locking the same bytes several times simply updates their locking mode (exclusive or shared). Like for flock(),
      this operation is not guaranteed to be atomic, and locked bytes will only have to be released once.
  
- Such locks are **never** shared with child processes, even those born from a simple fork() without exec(). These locks are preserved through an exec() though.

- These locks are (theoretically) supported by recent enough NFS servers (> NFS v4).

All these features could make of fntcl() a very good backend to build a cross-platform API, but unfortunately they're 
a major gotcha we have to deal with, first... 



The curse of fcntl locks
############################


There is a disturbing flaw in Posix fcntl lock specifications: when any file descriptor to a disk file is closed,
all the locks owned by the process on that file are lost.

Beware: it is "any" file descriptor, not the file descriptor which was used to obtain locks, or one of the file
descriptors pointing to the same "open file table" entry. So if, while you're peacefully playing with your locks
around some important file (eg. /etc/passwd), one of the numerous libraries used in your project silently reads this file
with a temporary stream, you'll lose all your locks without even knowing it.

So we have to live with this fact : the only unix locks able to work over NFS and to lock bytes ranges, are also the only locks in the world able to discreetly run away as soon as they're disturbed by third-party libraries.

RSFile provides workarounds to prevent such unexpected lock losses, see the :ref:`rsfile_locking_semantic` section.



Cascading buffers and caches
------------------------------------

In a simple world, issuing a ``myfile.write("hello")`` would simply write the string "hello"
to the open file *myfile*. Programmers quickly learn that for performance reasons, it can't be so simple.
But they sometimes under-estimate *how much* more complicated it is. The data we read from or
write to files go through many levels of buffering/caching, so here is an overview of
the main steps involved.
    

Application-level buffering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is the buffering we find in C libraries (inside FILE* objects, cf setvbuf()), 
in python file objects (via the *buffering* parameter), and more generally any IO library 
written in any language.

This buffering usually consists of read-ahead buffering (to improve reading performance, allow character encoding
operations, and line ending detection) and write buffering (to decrease the number of write system calls - 
this buffer can be manually emptied with a flush()). A seek() on a stream typically resets these buffers.

Kernel-level caching
^^^^^^^^^^^^^^^^^^^^^^

Contrary to common beliefs, if you open a file, issue read/write operations on it, and close 
it (with an implicit flush), this doesn't imply that your modifications have been saved to disk.
Most likely, they have just been acknowledged by a cache located in the kernel, and will be "written
to oxyde" later, along with other changes, by a lazy writer (eg. *pdflush* on linux). On laptops in
particular, disks can be left asleep for dozens of minutes in order to preserve energy - your data will
then remain in memory for all that time.
    
Since this kernel caching is fully transparent to applications (no desynchronization should occur between
what different processes see of a file), it usually doesn't matter. But in case of crash, data which 
hasn't yet been written to oxyde will be lost - which can be quite embarrassing (goodbye to the 3 paragraphs
you've just written) or more than embarrassing (bank files management, database applications...).

That's why operating system offer ways of flushing this kernel cache, to ensure that data gets
properly written to the device before starting other operations. Such a flush can be manually triggered
(posix fsync() call, windows FlushFileBuffers()...) or enforced for each write on a given open file
(O_SYNC/FILE_WRITE_THROUGH opening flags). 

Note that several variants of kernel cache flushing exist (dsync, rsync, datasync semantics...),
eg. to also enforce flushing of read buffers, or to bypass the flushing of metadata, but the main
point of concern is, anyway, that the file data itself be properly pushed to oxyde when you command it.

A problem you might encounter at that level, is that on some platforms, sync-like calls actually do not wait
for the write operation to complete, they just plan write operations and immediately return (Posix1-2001 doesn't 
require more). Fortunately, most recent kernels seem to wait for the synchronization to be over, before returning
to the application. But this won't completely save you, because of the next caching level...


Internal disk cache
^^^^^^^^^^^^^^^^^^^^^^

For performance reasons, most hard disk have an internal "disk cache"
enabled by default, which doesn't necessarily get flushed by sync calls.
This allows optimizations like out-of-order writing.

Needless to say that your data is not much more likely to survive to a crash, if it's in the disk 
cache rather than in the kernel one (although sophisticated disks are sometimes backed by batteries 
to deal with this case, allowing the device to automatically flush its cache before falling out of energy).
So here is an overview of the "disk cache" affair.

Disks and operating system easily lie about their real synchronization state. That's why, if you have 
very important data to protect, your best chance is to disable all disk caching features,
through hardware configuration  utilities, (``hdparm -W 0``, windows hardware configuration panels
etc.). But such tweaks can heavily hinder performance, and they depend a lot on your 
hardware - IDE and SCSI disks, for example, can have very different options, and more or less 
deceiving behaviours. Luckily, your data won't always be sensitive enough to require such 
extreme measures.

If your data is stored on remote shares (samba, nfs...), then chances are big 
that your sync calls won't make it to the oxyde, and only a careful study of 
involved hardware/OS/applications may give you some certainties in this case 
(a good old "unplug the cable violently and check the result" might also help).

Windows
    The windows FlushFileBuffers call usually implies both kernel cache and disk
    cache flushing, as well on local storages as on remote filesystems. But this only works 
    if the disk hasn't been configured with option "Turn off Windows write-cache buffer flushing".

Unix-like systems:
    As well in Posix norms as in the Single Unix Specification, nothing requires that fsync() calls 
    care about disk cache. But in practice:
    
    - Mac OS X users : lucky you, Apple has introduced a new fcntl flag (F_FULLSYNC) to enforce 
      full synchronization on a file descriptor.
    - Linux users: it seems that for some kernel versions now (2.6.33 and above), full sync is in place.
    - Other unix-like platforms : Your mileage may vary... read the sweet manuals, as they say.


RSFile synchronization system
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

RSFile attempts to do its best with the constraints listed above: it offers a :meth:`rsfile.flush()` method 
(simple application-buffer flushing), as well as a :meth:`rsfile.sync()` method, which additionally handles the kernel-cache flushing. You can provide hints to the latter, to ignore metadata synchronization or enforce disk cache flushing, but RSFile won't do more than your OS can afford (and it won't tweak your hardware settings for you, either).

If you need constant synchronization data, see the "S" flag of advanced file open modes, which uses O_SYNC
on unix and FILE_FLAG_WRITE_THROUGH on windows, to enforce data+metadata synchronization on each flush().


Some links to go further
---------------------------

`On the Brokenness of File Locking <http://0pointer.de/blog/projects/locking.html>`_

`Everything You Always Wanted to Know About Fsync() <http://blog.httrack.com/blog/2013/11/15/everything-you-always-wanted-to-know-about-fsync/>`_

`A Tale of Two Standards - Samba <https://www.samba.org/samba/news/articles/low_point/tale_two_stds_os2.html>`_



