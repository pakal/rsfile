#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function


## THIS CLASS IS CURRENTLY ONLY USED FOR DOCUMENTATION PURPOSE ##

### Based on trunk _pyio from python3.4 ! ###


import os
import abc

from .rsfile_definitions import io_module



class RSIOBase(object):
    __metaclass__ = abc.ABCMeta

    """
    This abstract base class is used to document the additional features of rsfile streams,
    compared to that of the stdlib `io.IOBase` subclasses.

    Unless stated otherwise, all
    methods and attributes specified in the docs of the `io` module also exist in rsfile sreams,
    with a compatible behaviour.
    """


    ### IMPROVED METHODS ###

    def truncate(self, size=None, zero_fill=True):
        """Truncates file to ``size`` bytes.

        ``size`` defaults to the current IO position as reported by tell().

        Contrary to what the name may suggest, this 'truncation' can as well
        reduce the file as extend it. In case of reduction, bytes located
        after the new end of file are discarded. In case of extension, the content
        of the byte range added depends on ``zero_fill``. If it is True, new bytes
        will always appear as zeros (but files can then be quite slow on
        filesystems which don't support sparse files, such as FAT). If it is False,
        the content of the added bytes is undefined, as the quickest extension method
        is used.

        Returns the new file size.
        """
        self._unsupported("truncate")

    def close(self):
        """
        Flushes and closes the IO object. This method has no effect if the file is already closed.

        Potential exceptions are NOT swallowed. Yet the underlying IO streams are closed even if the flush() failed, as is done in the stdlib io module. So if your data is very important, issue a separate flush() and handle potential errors (no more disk space, blocking operation error on a non-blocking stream...) before close().

        All the locks still held by the stream's file descriptor are released,
        but on unix systems the file descriptor itself is only closed when no more locks
        are held by the process on the target disk file. This is a workaround to prevent fctnl
        locks on that file from all becoming stale in the process, due to the fctnl semantic.
        """



    ### NEW METHODS ###

    def size(self): # non standard method    
        """Returns the size, in bytes, of the opened file.

        Intermediate buffers are flushed before the size is actually computed.
        """
        self._unsupported("size")


    def sync(self, metadata=True, full_flush=True):
        """Synchronizes file data between kernel cache and physical device.

        If ``metadata`` is False, and if the platform supports it (win32 and Mac OS X don't),
        this sync is a "datasync", i.e only data and file sizes are written to disk, not
        file times and other metadata (this can improve performance, at the cost of some
        incoherency in filesystem state).

        If ``full_flush`` is True, RSFileIO will whenever possible force the flushing of device
        caches too.

        For a constant synchronization between the kernel cache and the disk oxyde,
        CF the "synchronized" argument at stream opening.

        Raises an IOError if no sync operation is available for the stream.
        """
        self._unsupported("sync")


    def times(self):
        """Returns a :class:`FileTimes` instance with portable file time attributes.

        These attributes are integers or floats.
        Their precision may vary depending on the platform, but they're always expressed in seconds.
        Currently supported attributes, for disk files: ``access_time`` and ``modification_time``.

        .. note:: more specific times are supported by different platforms, they might be included
                  in next releases through OS-specific FileTimes attributes.

        Raises IOError if the stream has no times available.
        """
        self._unsupported("times")


    def uid(self):
        """Returns a tuple of (device, inode) integers, identifying unambiguously the stream.

        Different file objects refer to the same disk file if
        and only if they have the same uid.

        Raises OSError if it is impossible to retrieve this information (on some network
        or virtual filesystems, or for unnamed streams...).

        Nota : a file path can't be used as an unique identifier,
        since it is often possible to delete/recreate
        a file, while other streams born from that same path are still in use.
        """
        self._unsupported("uid")


    def fileno(self):
        """Returns the C-style file descriptor (an integer).

        Rsfile streams always expose a file descriptor. However, on Windows, this file descriptor is just a wrapper around the native Handle, and it shouldn't be relied upon too much.
        """
        self._unsupported("fileno")


    def handle(self):
        """Returns the native file handle associated with the stream.

        On most (*nix-like) systems, it's the same as fileno (an integer).

        On windows, it's a specific Handle value, which is also an integer.
        """


    def lock_file(self, timeout=None, length=None, offset=None, whence=os.SEEK_SET, shared=None):
        
        """
        Locks the whole file or a portion of it, depending on the arguments provided.

        The strength of the locking depends on the underlying platform. 
        On windows, all file locks (using LockFile()) are mandatory, i.e even programs 
        which are not using file locks won't be able to access locked 
        parts of files for reading or writing (depending on the type 
        of lock used).
        On posix platforms, most of the time locking is only advisory:
        unless they use the same type of lock as rsFile
        (currently, fcntl calls), programs will freely access your files if they have 
        proper permissions. Note that it is possible to enforce mandatory 
        locking thanks to some mount options and file flags, 
        but this practice is highly advised against by unix gurus.
        
        Native locks have very different semantics depending on the platform, but 
        rsfile enforces a single semantic : *per-handle, non-reentrant locks*.
        
        *per handle*: once a lock has been acquired via a native handle, 
        this handle is the owner of the lock. No other handle, even in the current
        process, even if they have been duplicated or inherited from the owner handle, 
        can lock/unlock bytes that are protected by the original lock.
        
        *non-reentrant*: no merging/splitting of byte ranges can be performed with
        this method : the ranges targetted by unlock() calls must be exactly the same
        as those previously locked.
        Also, trying to lock the same bytes several times will raise a 
        RuntimeError, even if the sharing mode is not the same (no **atomic** lock 
        upgrade/downgrade is available in kernels, anyway).
        
        This way, rsfile locks act both as inter-process and intra-process locks. 

        .. note: this semantic doesn't tell anything about thread-safety, which must 
                 be ensured through other means, like a :class:`RSThreadSafeWrapper`. 
                 Also, nothing is done to detect inter-process or intra-process
                 deadlocks - that's the responsibility of the programmer.
        
        .. warning::
            
            Due to the amazing semantic of fcntl() calls, native handles can't be released
            as long as locks exist on the target file. So if your process constantly opens 
            and closes the same files while keeping locks on them, you might eventually 
            run out of process resources.
            To avoid this, simply plan lock-less moments for this flushing of pending handles, 
            or reuse the same file objects as much as possible.
            
            Note that rsfile protections can't do anything if a third-party functions or C extensions
            used by the process open the same file without using rsfile's interface  - in this case, 
            file locks might be silently lost...
            
        .. rubric::
            Parameters
        
        - *timeout* (None or positive integer):  
          If timeout is None, the process will block on this operation until it manages to get the lock; 
          else, it must be a number indicating how many seconds
          the operation will wait before raising a timeout IOError
          (thus, timeout=0 means a non-blocking locking attempt).
    
    
        - *length* (None or positive integer): Specifies how many bytes must be locked.
          If length is None or 0, it means *infinity*, i.e all the bytes after the 
          locking offset will be locked. It is not an error to lock bytes farther 
          than the current end of file.
          
        - *offset* (None or positive integer):
          Relative offset, starting at which bytes should be locked. 
          This position can be beyond the end of file.
        
        - *whence* (SEEK_SET, SEEK_CUR or SEEK_END):
          Whence is the same as in seek(), and specifies what the offset is 
          referring to(beginning, current position, or end of file).
                
        - *shared* (None or boolean): 
          If ``shared`` is True, the lock is a "reader", non-exclusive lock, which can be shared by several 
          processes, but prevents "writer" locks from being taken on the locked portion. 
          The owner of the lock shall himself not attempt to write to the locked area.
          
          If ``shared`` is False, the lock is a "writer", exclusive lock, preventing both writer 
          and reader locks from being taken by other processes on the locked portion.
          
          By default, ``shared`` is set to False for writable streams, and to True for others.
          Note that this sharing mode can be compatible with the stream permission, i.e shared locks can only
          by taken by stream having read access, and exclusive locks are reserve to writable streams. 
          Thus, this parameter is only useful for read/write streams, which can alternate 
          shared and exclusive locks depening on their needs.
        
        On success, ``lock_file`` returns a context manager for use inside a with statement, 
        to automatically release the lock. However, it is advised that you don't release locks 
        if you close the stream just after that; letting the close() operation release the locks
        is as efficient, and on unix it prevents other threads from taking locks in the short time
        between unlocking and stream closing (thus allowing the system to safely free handle resources
        in spite of the unsafe fcntl() semantic).
        
        """
        self._unsupported("lock_file")


    def unlock_file(self, length=None, offset=0, whence=os.SEEK_SET):
        """
        Unlocks a file portion previously locked through the same native handle. 
        
        The specifications of the locked area (absolute offset and length) must 
        be the same as those used when calling locking methods,
        else errors will occur; its is thus not possible to release only 
        a part of a locked area, or to unlock with only one call
        two consecutive ranges.
        
        This function will usually be implicitly called thanks to a context manager
        returned by :meth:`lock_file`. But as stated above, don't use it if you plan 
        to close the file immediately - the closing system will handle the unlocking
        in a more efficient and safer manner. 
        """
        self._unsupported("unlock_file")
        

io_module.IOBase.register(RSIOBase)






