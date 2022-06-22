# -*- coding: utf-8 -*-


## THIS CLASS IS CURRENTLY ONLY USED FOR DOCUMENTATION PURPOSE ##


import sys, os


class RSIOBase(object):
    """
    This abstract base class is only used to document the **additional/modified** features of rsfile streams,
    compared to those of the stdlib `io.IOBase` subclasses. Unless stated otherwise, all methods and attributes
    documented for the `io` module also exist on rsfile sreams, with a compatible behaviour.

    Advanced streams can be found in the *rsfile* package, as classes named *RSFileIO*, *RSBufferedReader*,
    *RSBufferedWriter*, *RSBufferedRandom*, *RSTextIOWrapper* and *RSThreadSafeWrapper*.
    However, you shouldn't have to deal with them directly, since RSOpen() takes care of instantiating them properly.
    Also note that the signature of *RSFileIO* differs quite much from its stdlib counterpart, because of its enhanced
    capabilities.

    """

    def _unsupported(selfself, name):
        raise NotImplementedError(name)

    ### IMPROVED METHODS ###

    def truncate(self, size=None, zero_fill=True):
        """Truncates regular file to ``size`` bytes.

        ``size`` defaults to the current IO position as reported by tell().

        Contrary to what the name may suggest, this 'truncation' can as well
        reduce the file as extend it.

        - In case of reduction, bytes located
          after the new end of file are discarded.
        - In case of extension, the content
          of the byte range added depends on ``zero_fill``. If it is True, new bytes
          will always appear as zeros (but file truncation can then be quite slow on
          filesystems which don't support sparse files, such as FAT). If it is False,
          the content of the added bytes is undefined, as the quickest extension method
          is used.

        Returns the new file size.
        """
        self._unsupported("truncate")

    def flush(self):
        """
        Flushes read and/or write buffers, if applicable.

        These operations ensure that all bytes written get pushed
        at least from the application to the kernel I/O cache, and
        that the file pointer of the underlying low level stream becomes
        the same as the 'virtual' file position returned by tell().

        Returns None.
        """
        self._unsupported("flush")

    def close(self):
        """
        Flushes and closes the IO object. This method has no effect if the file is already closed.

        Potential exceptions are NOT swallowed. Yet the underlying raw streams are closed even if the flush() failed,
        as is done in the stdlib io module. So if your data is very important, issue a separate flush() and handle
        potential errors (no more disk space, blocking operation error on a non-blocking stream...) before close().

        When closing, all the locks still held by the stream's file descriptor are released.

        However, note that the native file descriptor wrapped by this stream might be kept alive for a while,
        to prevent unexpected losses of locks elsewhere in the process (see :ref:`rsfile_locking_caveats` for details).
        """
        self._unsupported("close")

    ### NEW METHODS ###

    def size(self):  # non standard method
        """Returns the size, in bytes, of the opened file.

        Intermediate buffers are flushed before the size is actually computed.
        """
        self._unsupported("size")

    def sync(self, metadata=True, full_flush=True):
        """Pushes file (meta)data from application to physical device, through
        kernel cache and other layers of caching.

        An implicit flush() always happens first, to empty python-level buffers.

        If ``full_flush`` is True (only works on OSX for now), RSFileIO will
        try to ensure that data is really written to permanent storage, since
        disk devices might else keep data in their cache for out-of-order writing.
        If full flush is successful, metadata gets written as well.

        If no full flush took place, if ``metadata`` is False,
        and if the platform supports it (win32 and OSX don't),
        this sync is a "datasync", i.e only data and file sizes are written to disk, not
        file times and other metadata (this can improve performance, at the cost of some
        incoherence in filesystem state).

        If None of the above works, a standard sync() is attempted, i.e pushing both data and 
        metadata up to the disk device.

        Note that the file's parent directory is not necessarily updated synchronously, so
        some risks of data loss may remain.

        For a constant synchronization between the kernel cache and the disk oxide,
        see the "synchronized" argument at stream opening.

        Raises IOError if no sync operation is possible on the stream (eg. for pipes).

        No return value is expected.
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

    def unique_id(self):
        """Returns a tuple of (device, inode) integers, identifying unambiguously the stream.

        Different file objects refer to the same disk file if
        and only if they have the same unique_id.

        Raises OSError if it is impossible to retrieve this information (on some network
        or virtual filesystems, for unnamed streams...).

        Nota : a file path can't be used as an unique identifier,
        since it is often possible to delete/recreate
        a file, while other streams born from that same path are still in use.
        """
        self._unsupported("unique_id")

    def fileno(self):
        """Returns the C-style file descriptor (an integer).

        Rsfile streams always expose a file descriptor. However, on Windows, this file descriptor is just a wrapper
        around the native Handle, and it shouldn't be relied upon too much.
        """
        self._unsupported("fileno")

    def handle(self):
        """Returns the native file handle associated with the stream.

        On most (\*nix-like) systems, it's the same as fileno (an integer).

        On windows, it's a specific Handle value, which is also an integer.
        """
        self._unsupported("handle")

    def lock_file(self, timeout=None, length=None, offset=None, whence=os.SEEK_SET, shared=None):
        """
        Locks the whole regular file or a portion of it, depending on the arguments provided.

        See the :ref:`rsfile_locking_semantic` doc to understand what type of locking, exactly,
        you can achieve with that method.

        .. warning::

           Be sure, in particular, to read the :ref:`rsfile_locking_caveats`,
           to be aware of some limitations and dangers of these file locks.


        .. rubric::
            Parameters
        
        - *timeout* (None or positive integer):
          If timeout is None, the process will block on this operation
          until it manages to get the lock;
          else, it must be a number indicating how many seconds
          the operation will wait before raising a timeout IOError
          (thus, timeout=0 means a non-blocking locking attempt).
          Low level APIs do not support lock timeout, so it's currently emulated via repeated
          non-blocking calls (spin-lock).
          See :ref:`rsfile-options` for customization.
    
        - *length* (None or positive integer): Specifies how many bytes must be locked.
          If length is None or 0, it means *infinity*, i.e all the bytes after the 
          locking offset will be locked. It is not an error to lock bytes farther 
          than the current end of file.
          
        - *offset* (None or positive integer):
          Relative offset, starting at which bytes should be locked. 
          This position can be beyond the end of file.
        
        - *whence* (SEEK_SET, SEEK_CUR or SEEK_END):
          Whence is the same as in :meth:`io.IOBase.seek`, and specifies what the offset is
          referring to (beginning, current position, or end of file).
                
        - *shared* (None or boolean): 
          If ``shared`` is True, the lock is a "reader", non-exclusive lock, which can be
          shared by several "reader" streams, but prevents "writer" locks from being taken
          on the locked portion.
          The owner of the lock shall himself not attempt to write to the locked area if it's *shared*,
          even if file open mode allows it: it'll fail if locking is mandatory, eg. on windows.
          
          If ``shared`` is False, the lock is a "writer", exclusive lock, preventing both writer 
          and reader locks from being taken by other processes on the locked portion.
          
          By default, ``shared`` is set to False for writable streams, and to True for others.
          Note that this sharing mode can be compatible with the stream permission, i.e shared locks can only
          by taken by stream having read access, and exclusive locks are reserved to writable streams.
          Thus, this parameter is only useful for read/write streams, which can alternate between
          shared and exclusive locks depending on their needs.

        This method raises `RuntimeError` if an abnormal workflow is detected (eg. attempting the lock overlapping
        areas of the files several times through the *same* file handle, whatever the "shared" mode provided).

        On success, ``lock_file`` returns a context manager for use inside a *with* statement,
        to automatically release the lock. However, it is advised that you don't release locks 
        if you close the stream just after that: letting the close() operation release the locks
        is as efficient, and prevents some corner-case problems as described in :ref:`rsfile_locking_caveats`.

        """
        self._unsupported("lock_file")

    def unlock_file(self, length=None, offset=0, whence=os.SEEK_SET):
        """
        Unlocks a portion of regular file previously locked through the same native handle.
        
        The specifications of the locked area (absolute offset and length) must 
        be the same as those used when calling lock_file(),
        else errors will occur; its is thus not possible to release only 
        a part of a locked area, or to unlock with only one call
        two consecutive ranges.
        
        This function will usually be implicitly called thanks to a context manager
        returned by :meth:`lock_file`. But as stated above, don't use it if you plan 
        to close the file immediately - the closing system will handle the unlocking
        in a safer manner.
        """
        self._unsupported("unlock_file")

    @property
    def mode(self):
        """
        At the moment, this property behaves like its sibling from the stdlib io module, and returns a string of
        *standard* (lowercase) mode flags.

        On a binary stream, it recomputes the mode from the raw stream attributes,
        except that it does't distinguish "rb+" from "wb+" ("rb+" is always returned).

        If the file is opened in text mode however, its "mode" attribute is exactly that which was passed open().
        """
        self._unsupported("mode")

    @property
    def origin(self):
        """
        Returns a string indicating the origin of the stream,
        as well as the meaning of its :attr:`name`.
        Possible values are 'path', 'fileno' and 'handle'.
        """
        self._unsupported("origin")

    @property
    def name(self):
        """
        Contains the path, fileno, or handle of the stream,
        depending on the way the stream was created.
        To interpret this attribute safely, refer to the :attr:`origin` property.
        """
        self._unsupported("name")
