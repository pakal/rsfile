
.. _rsfile_locking_semantic:

Semantic of RSFile Locking
==============================

Cross-platform Behaviour
+++++++++++++++++++++++++


RSFile relies on `windows LockFile()` and `unix fcntl()` locks, as well as miscellaneous intraprocess
threading locks and registries, to achieve *shared/exclusive bytes range locking*, *locking
on remote filesystems* (CIFS from Windows client, NFS from Unixclient ), and to *prevent
the sharing of the same lock objects by several processes* (even related to each other).

The strength of the locking depends on the underlying platform.

- on windows, all file locks (using LockFile()) are **mandatory**, i.e
  even programs which are not using file locks won't be able to access
  locked parts of files for reading or writing (depending on the type of
  lock used).
- in unix-like platforms, most of the time, locking is only
  **advisory**: unless they use the same type of lock as rsFile (fcntl),
  programs will freely access your files if they have proper filesystem
  permissions. It is possible to enforce mandatory locking, thanks
  to some mount options and file flags, but this practice is advised against.

Native locks have very different semantics depending on the platform, but
RSFile enforces a single semantic : **per handle, bytes level, non-reentrant locks**.

**per handle**: once a lock has been acquired via a native handle,
this handle is the owner of the lock. No other handle, even in the current
process, even if they have been duplicated or inherited from the owner handle,
can lock/unlock bytes that are protected by the original lock.

**bytes level**: the lock can concern the whole file, or only a range of bytes.
It's not a problem to have locks beyond the current end of file, locking the "virtual
bytes" that may be written in the future.

**non-reentrant**: no merging/splitting of byte ranges can be performed with
this method : the ranges targeted by unlock_file() calls must be exactly the same
as those previously locked.
Also, trying to lock the same bytes several times will raise an exception, even if the sharing mode is not the same (no **atomic** lock
upgrade/downgrade is available in kernels anyway, it seems).

.. note::
    Being carried by file handles, rsfile locks can be used both as inter-process and intra-process locks.
    However this semantic doesn't say anything about thread-safety, which is
    ensured through other means (like the :class:`RSThreadSafeWrapper` class
    added by default in front of stream chains).


.. _rsfile_locking_caveats:

Caveats and Limitations
+++++++++++++++++++++++


Unwanted Blocking
------------------

The first danger of file locking, is the **Denial Of Service**. Files can often be accessed by multiple
users and processes on a machine, if any of these uses the same kind of file locking than your own program,
conflicts may happen. A malevolent program might block yours forever. And like in any concurrent system
(multiprocessing, multithreading...), deadlocks may happen between different entities, if they try to lock
several files (or portions of files) at the same time. To mitigate these risks, and help detecting programming
errors, you can use timeouts on lock_file() calls, or globally enforce a timeout for all RSFile locks (see :ref:`rsfile-options`).

Note that since locks are per-handle, a **single thread can easily block itself**, if it creates several streams targeting the same disk file. This may occur when manually issuing lock_file() calls, or when opening implicitly fully-locked files (which is the default for :func:`rsfile.rsopen`). Indeed, Rsfile prevents the taking of conflicting locks on a same handle, but can't guess by which thread(s) the different handles that it creates are supposed to be handled in the end.



Shortage of Open Files (unix)
------------------------------

Another caveat comes from the strange semantic of fcntl() calls, on unix-like systems: native file descriptors can't
be released as long as locks still exist on the same target file, somewhere else in the process ; else all these locks run the risk of being silently released.

So in RSFile on unx, file closing operations have been modified to work around that flaw: when
a stream is closed, RSFile may actually **keep the native file descriptor alive**, in an internal registry.
As long as the process has some locks taken on the same disk file (identified by its device+inode),
this file descriptor won't be released.

The danger with this workaround, is that your process or system could run out of available file descriptors, if it continuously
opens and locks the same file without ever letting the possibility to release these handle (i.e by constantly keeping at
least some bytes locked on this file).

In practice, if you really need to constantly lock parts of the file (eg. for a shared database file), then you should:

- keep using the same file descriptors whenever possible
- plan "zero locks" moments, to allow the purging of "zombie" file descriptors
- let the closing operation of a file descriptor atomically release the locks still kept,
  instead of manually unlocking them just before closing the file. This helps the purge of previous file descriptors,
  by preventing new locks from being taken in the short time between the unlocking and the closing of the stream.

Anyway, if your application behaves that way, it also creates some kind of denial-of-service against any other process
which would want to lock the whole file, so it could be the sign that other means of protection (file permissions,
immediate deletion of the filesystem entry...) would be more appropriate for your needs.


Interferences with Third-Party Libs (unix)
-------------------------------------------


The workaround explained above, to preserve fcntl() locks on stream closing, will of course only work as long as accesses to disk file are done through the **RSFile API**. Code using other python modules ("io", "_pyio"...),  or low level routines (eg. in C extensions), may still silently break your locks, by opening+closing the same disk files.

If wanted, some of these dangers can be prevented by enforcing the use of RSFile for all python-side stream operations (CF :ref:`rsfile-patching`). But overriding the lowest level I/O routines, like libc's open(), would require tremendous skills and work.




.. OLDIES


        Still because of fcntl() behaviour on unix-like systems,

        Note that rsfile protections can't do anything if a third-party functions or C extensions
        used by the process open the same file without using rsfile's interface  - in this case,
        file locks might be silently lost...


        tries to acquire several simultaneously

        Due to the per-handle semantic of RSFile locking, if a single thread opens a file with locking, and then tries to open

        To avoid this, simply plan lock-less moments for this flushing of pending handles,
        or reuse the same file objects as much as possible.

        Another danger

                but on unix systems the file descriptor itself is only closed when no more locks
                are held by the process on the target disk file. This is a workaround to prevent fctnl
                locks on that file from all becoming stale in the process, due to the fctnl semantic.

         that your own process needs to lock, this may

        in exclusive locking mode,
        and then attempts to open it in shared


        So if your process constantly opens and closes the same files while keeping locks on them, you might eventually
        run out of process resources.




        An internal registry is then used to normalize the behaviour of file locks across platforms:
        - locks are attached to a specific "file descriptor", not to an "open file object" or to the whole process.
        - the merging/splitting of bytes range locks, and the use of lock reentrancy, are prevented


               on unix it might
                prevents other threads from taking locks in the short time
                between unlocking and stream closing (which could).


        So how does RSFile do, to get a decent cross-platform API from all this ?






