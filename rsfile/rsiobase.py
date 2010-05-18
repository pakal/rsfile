#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals



## THIS CLASS IS CURRENTLY ONLY USED FOR DOCUMENTATION PURPOSE ##

### Based on trunk _pyio version 77890 ! ###



import os
import abc
import codecs
import warnings
# Import _thread instead of threading to reduce startup cost
try:
    from thread import allocate_lock as Lock
except ImportError:
    from dummy_thread import allocate_lock as Lock


from rsfile_definitions import SEEK_SET, SEEK_CUR, SEEK_END, io_module


__metaclass__ = type

# open() uses st_blksize whenever we can
DEFAULT_BUFFER_SIZE = 8 * 1024  # bytes


# NOTE: Base classes defined here are registered with the "official" ABCs
# defined in io.py. We don't use real inheritance though, because we don't
# want to inherit the C implementations.

from io import BlockingIOError, UnsupportedOperation   # useless ?

if hasattr(io_module.IOBase, "register"):
    USE_ABC = True # python >= 2.7 ?
    IO_BASE = object
    RAW_BASE = object
    BUFFER_BASE = object
else:
    IO_BASE = io_module.IOBase
    RAW_BASE = io_module.RawIOBase
    BUFFER_BASE = io_module.BufferedIOBase






class RSIOBase(IO_BASE):
    __metaclass__ = abc.ABCMeta

    """
    The abstract base class for all RockSolid I/O classes, acting on streams of
    bytes. There is no public constructor.

    This class provides dummy implementations for many methods that
    derived classes can override selectively; the default implementations
    represents a file that cannot be read, written or sought.

    Even though RSIOBase does not declare read, readinto, or write because
    their signatures will vary, implementations and clients should
    consider those methods part of the interface. Also, implementations
    may raise a IOError when operations they do not support are called.

    The basic type used for binary data read from or written to a file is
    bytes. bytearrays are accepted too, and in some cases (such as
    readinto) needed. Text I/O classes work with str data.

    Note that calling any method (even inquiries) on a closed stream
    will raise an IOError.

    RSIOBase (and its subclasses) support the iterator protocol, meaning
    that an RSIOBase object can be iterated over yielding the lines in a
    stream.

    RSIOBase also supports the :keyword:`with` statement. In this example,
    fp is closed after the suite of the with statement is complete:

    with open('spam.txt', 'r') as fp:
        fp.write('Spam and eggs!')
    """

    ### Internal ###

    def _unsupported(self, name):
        """Internal: raises an exception for unsupported operations."""
        raise UnsupportedOperation("%s.%s() not supported" %
                                   (self.__class__.__name__, name))



    ### Positioning ###

    def seek(self, pos, whence=0):
        """Changes stream position.

        Changes the stream position to byte offset ``pos`` . This offset is
        interpreted relative to the position indicated by whence.  Values
        for whence are:

        * SEEK_SET (0) -- start of stream (the default); offset should be zero or positive
        * SEEK_CUR (1) -- current stream position; offset may be negative
        * SEEK_END (2) -- end of stream; offset is usually negative

        Returns the new absolute position.
        """
        self._unsupported("seek")

    def tell(self):
        """Returns the current stream position, as an absolute byte offset."""
        return self.seek(0, 1)

    def size(self): # non standard method    
        """Returns the size, in bytes, of the opened file.
        Intermediary buffers are flushed before the size is actually computed.
        """
        self._unsupported("size")
        
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

    ### Flush and close ###

    def flush(self):
        """
        Flushes read and/or write buffers, if applicable.
        
        These operations ensure that all bytes written get pushed 
        at least from the application to the kernel I/O cache, and
        that the file pointer of underlying low level stream becomes 
        the same as the 'virtual' file position returned by tell().
        
        Returns None.
        """

    def sync(self, metadata=True, full_flush=True):
        """Synchronizes file data between kernel cache and physical device. 
        
        If ``metadata`` is False, and if the platform supports it (win32 and Mac OS X don't), 
        this sync is a "datasync", i.e only data and file sizes are written to disk, not 
        file times and other metadata (this can improve performance, but also i).
        
        If ``full_flush`` is True, RSFileIO will whenever possible force the flushing of device
        cache too.
        
        For a constant synchronization between the kernel cache and the disk oxyde, 
        CF the "synchronized" argument at stream opening.
        
        Raises an IOError if no sync operation is available for the stream.
        """
        self._unsupported("sync")
         
         
    __closed = False

    def close(self):
        """Flushes and closes the IO object. Potential exceptions are NOT swallowed, 
        and the streams is only marked as closed closed if the whole flush() was successful.
        
        This method has no effect if the file is already closed.
        
        All the locks still held by the stream's file descriptor are released,
        but on unix systems the descriptor itself is only closed when no more locks 
        are held by the process on the target disk file (this is a workaround for fctnl()'s
        amazing semantic). 
        """
        
        if not self.__closed:
            self.flush()
            self.__closed = True


    def __del__(self):
        """Destructor.  Calls close()."""
        # The try/except block is in case this is called at program
        # exit time, when it's possible that globals have already been
        # deleted, and then the close() call might fail.  Since
        # there's nothing we can do about such failures and they annoy
        # the end users, we suppress the traceback.
        try:
            self.close()
        except:
            pass

    ### Inquiries ###

    def seekable(self):
        """Returns whether object supports random access.

        If False, seek(), tell() and truncate() will raise IOError.
        This method may need to do a test seek().
        """
        return False

    def _checkSeekable(self, msg=None):
        """Internal: raises an IOError if file is not seekable.
        """
        if not self.seekable():
            raise IOError("File or stream is not seekable."
                          if msg is None else msg)


    def readable(self):
        """Returns whether object was opened for reading.

        If False, read() will raise IOError.
        """
        return False

    def _checkReadable(self, msg=None):
        """Internal: raises an IOError if file is not readable.
        """
        if not self.readable():
            raise IOError("File or stream is not readable."
                          if msg is None else msg)

    def writable(self):
        """Returns whether object was opened for writing.

        If False, write() and truncate() will raise IOError.
        """
        return False

    def _checkWritable(self, msg=None):
        """Internal: raises an IOError if file is not writable.
        """
        if not self.writable():
            raise IOError("File or stream is not writable."
                          if msg is None else msg)

    @property
    def closed(self):
        """True iff the file has been closed.

        For backwards compatibility, this is a property, not a predicate.
        """
        return self.__closed

    def _checkClosed(self, msg=None):
        """Internal: raises an ValueError if file is closed.
        """
        if self.closed:
            raise ValueError("I/O operation on closed file."
                             if msg is None else msg)

    ### Context manager ###

    def __enter__(self):
        """Context management protocol.  Returns self."""
        self._checkClosed()
        return self

    def __exit__(self, *args):
        """Context management protocol.  Calls close()"""
        self.close()


    ### Lower-level and Information APIs ###
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
        """Returns a (device, inode) tuple, identifying unambiguously the stream inode.
        
        Several file objects refer to the same disk file if 
        and only if they have the same uid.
    
        Raises IOError if it is impossible to retrieve this information (on some network or virtual filesystems,
        or for unnamed streams...).
        
        Nota : a file path can't be used as an unique identifier, since it is often possible to delete/recreate 
        a file, while streams born from that path are still in use.  
        """
        self._unsupported("uid")
        
    def fileno(self):
        """Returns the C file descriptor giving access to the file.
        
        Note that on win32, this file descriptor is just a (buggy) wrapper 
        around native Handle types, and it shouldn't be relied upon too much.

        An IOError is raised if the IO object does not use a file descriptor.
        """
        self._unsupported("fileno")

    def handle(self):
        """Returns the native file handle associated with the stream.
        
        On most systems, it's the same as fileno, but on win32 it's a specific Handle value.
        """
        
    def isatty(self):
        """Returns whether this is an 'interactive' stream.

        Returns False if it can't be determined.
        """
        self._checkClosed()
        return False


    ### Readline[s] and writelines ###

    def readline(self, limit=-1):
        r"""Reads and returns a line from the stream.

        If limit is specified, at most limit bytes will be read.

        The line terminator is always b'\n' for binary files; for text
        files, the newlines argument to open can be used to select the line
        terminator(s) recognized.
        """
        # For backwards compatibility, a (slowish) readline().
        if hasattr(self, "peek"):
            def nreadahead():
                readahead = self.peek(1)
                if not readahead:
                    return 1
                n = (readahead.find(b"\n") + 1) or len(readahead)
                if limit >= 0:
                    n = min(n, limit)
                return n
        else:
            def nreadahead():
                return 1
        if limit is None:
            limit = -1
        elif not isinstance(limit, (int, long)):
            raise TypeError("limit must be an integer")
        res = bytearray()
        while limit < 0 or len(res) < limit:
            b = self.read(nreadahead())
            if not b:
                break
            res += b
            if res.endswith(b"\n"):
                break
        return bytes(res)

    def __iter__(self):
        self._checkClosed()
        return self

    def next(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def readlines(self, hint=None):
        """Returns a list of lines from the stream.

        ``hint`` can be specified to control the number of lines read: no more
        lines will be read if the total size (in bytes/characters) of all
        lines so far exceeds hint.
        """
        if hint is not None and not isinstance(hint, (int, long)):
            raise TypeError("integer or None expected")
        if hint is None or hint <= 0:
            return list(self)
        n = 0
        lines = []
        for line in self:
            lines.append(line)
            n += len(line)
            if n >= hint:
                break
        return lines

    def writelines(self, lines):
        self._checkClosed()
        for line in lines:
            self.write(line)



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
        
        - *offset* (SEEK_SET, SEEK_CUR or SEEK_END):
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
        
        On success, ``lock_file`` returns a context manager inside a with statement, 
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
        
     
if USE_ABC:
    io_module.IOBase.register(RSIOBase)









'''

## REIMPLEMENTATIONS OF OTHER STANDARD STREAMS - UNUSED AT THE MOMENT ##



class _BufferedIOMixin(BufferedIOBase):

    """A mixin implementation of BufferedIOBase with an underlying raw stream.

    This passes most requests on to the underlying raw stream.  It
    does *not* provide implementations of read(), readinto() or
    write().
    """

    def __init__(self, raw):
        self.raw = raw

    ### Positioning ###

    def seek(self, pos, whence=0):
        new_position = self.raw.seek(pos, whence)
        if new_position < 0:
            raise IOError("seek() returned an invalid position")
        return new_position

    def tell(self):
        pos = self.raw.tell()
        if pos < 0:
            raise IOError("tell() returned an invalid position")
        return pos

    def truncate(self, pos=None):
        self.flush()
        if pos is None:
            pos = self.tell()
        return self.raw.truncate(pos)


    ### Flush and close ###

    def flush(self):
        self.raw.flush()

    def close(self):
        if not self.closed and self.raw is not None:
            self.flush()
            self.raw.close()

    def detach(self):
        if self.raw is None:
            raise ValueError("raw stream already detached")
        self.flush()
        raw = self.raw
        self.raw = None
        return raw


    ### Inquiries ###

    def seekable(self):
        return self.raw.seekable()

    def readable(self):
        return self.raw.readable()

    def writable(self):
        return self.raw.writable()

    @property
    def closed(self):
        return self.raw.closed

    @property
    def name(self):
        return self.raw.name

    @property
    def mode(self):
        return self.raw.mode

    def __repr__(self):
        clsname = self.__class__.__name__
        try:
            name = self.name
        except AttributeError:
            return "<_pyio.{0}>".format(clsname)
        else:
            return "<_pyio.{0} name={1!r}>".format(clsname, name)

    ### Lower-level APIs ###

    def fileno(self):
        return self.raw.fileno()

    def isatty(self):
        return self.raw.isatty()





class BufferedReader(_BufferedIOMixin):

    """BufferedReader(raw[, buffer_size])

    A buffer for a readable, sequential BaseRawIO object.

    The constructor creates a BufferedReader for the given readable raw
    stream and buffer_size. If buffer_size is omitted, DEFAULT_BUFFER_SIZE
    is used.
    """

    def __init__(self, raw, buffer_size=DEFAULT_BUFFER_SIZE):
        """Create a new buffered reader using the given readable raw IO object.
        """
        if not raw.readable():
            raise IOError('"raw" argument must be readable.')

        if buffer_size <= 0:
            raise ValueError("invalid buffer size")
        self.buffer_size = buffer_size
        
        # Reading
        self._read_buf = b""
        self._read_pos = 0
    
        
        self._reset_read_buf()






    def _reset_read_buf(self):
        self._read_buf = b""
        self._read_pos = 0

    def read(self, n=None):
        """Read n bytes.

        Returns exactly n bytes of data unless the underlying raw IO
        stream reaches EOF or if the call would block in non-blocking
        mode. If n is negative, read until EOF or until read() would
        block.
        """
        if n is not None and n < -1:
            raise ValueError("invalid number of bytes to read")
        with self._read_lock:
            return self._read_unlocked(n)

    def _read_unlocked(self, n=None):
     

    def peek(self, n=0):
        """Returns buffered bytes without advancing the position.

        The argument indicates a desired minimal number of bytes; we
        do at most one raw read to satisfy it.  We never return more
        than self.buffer_size.
        """
        with self._read_lock:
            return self._peek_unlocked(n)

    def _peek_unlocked(self, n=0):
        want = min(n, self.buffer_size)
        have = len(self._read_buf) - self._read_pos
        if have < want or have <= 0:
            to_read = self.buffer_size - have
            current = self.raw.read(to_read)
            if current:
                self._read_buf = self._read_buf[self._read_pos:] + current
                self._read_pos = 0
        return self._read_buf[self._read_pos:]

    def read1(self, n):
        """Reads up to n bytes, with at most one read() system call."""
        # Returns up to n bytes.  If at least one byte is buffered, we
        # only return buffered bytes.  Otherwise, we do one raw read.
        if n < 0:
            raise ValueError("number of bytes to read must be positive")
        if n == 0:
            return b""
        with self._read_lock:
            self._peek_unlocked(1)
            return self._read_unlocked(
                min(n, len(self._read_buf) - self._read_pos))

    def tell(self):
        return _BufferedIOMixin.tell(self) - len(self._read_buf) + self._read_pos

    def seek(self, pos, whence=0):
        if not (0 <= whence <= 2):
            raise ValueError("invalid whence value")
        with self._read_lock:
            if whence == 1:
                pos -= len(self._read_buf) - self._read_pos
            pos = _BufferedIOMixin.seek(self, pos, whence)
            self._reset_read_buf()
            return pos







class RSBufferedRandom(RSIOBase, BUFFER_BASE):

    """A mixin implementation of BufferedIOBase with an underlying raw stream.

    This passes most requests on to the underlying raw stream.  It
    does *not* provide implementations of read(), readinto() or
    write().
    """
    """BufferedReader(raw[, buffer_size])

    A buffer for a readable, sequential BaseRawIO object.

    The constructor creates a BufferedReader for the given readable raw
    stream and buffer_size. If buffer_size is omitted, DEFAULT_BUFFER_SIZE
    is used.
    """
    """Base class for buffered IO objects.

    The main difference with RSRawIOBase is that the read() method
    supports omitting the size argument, and does not have a default
    implementation that defers to readinto().

    In addition, read(), readinto() and write() may raise
    BlockingIOError if the underlying raw stream is in non-blocking
    mode and not ready; unlike their raw counterparts, they will never
    return None.

    A typical implementation should not inherit from a RawIOBase
    implementation, but wrap one.
    """

    """A buffer for a writeable sequential RawIO object.

    The constructor creates a BufferedWriter for the given writeable raw
    stream. If the buffer_size is not given, it defaults to
    DEFAULT_BUFFER_SIZE.
    """
    
    

    def __init__(self, raw, buffer_size=DEFAULT_BUFFER_SIZE, max_buffer_size=None):
        """Create a new buffered reader using the given readable raw IO object.
        """

        self.raw = raw

        # TOCHANGE
        if not raw.writable():
            raise IOError('"raw" argument must be writable.')       
        if not raw.readable():
            raise IOError('"raw" argument must be readable.')   
            
        if buffer_size <= 0:
            raise ValueError("invalid buffer size")

        if max_buffer_size is not None:
            warnings.warn("max_buffer_size is deprecated", DeprecationWarning, 2)
        
        self.buffer_size = buffer_size
        


        # Writing
        self._write_buf = bytearray()

        # RANDOM
        """
        raw._checkSeekable()
        BufferedReader.__init__(self, raw, buffer_size)
        BufferedWriter.__init__(self, raw, buffer_size, max_buffer_size)
        """
        
        

    ### Reading ###
    
    def _rewind_read_buf(self, rewind_raw_stream = True):
        
        if rewind_raw_stream and self._read_buf:
            self.raw.seek(-len(self._read_buf) + self._read_pos, 1)
        self._read_buf = b""
        self._read_pos = 0



    def _read_bytes(self, n):
    
        if n is not None and n < -1:
            raise ValueError("invalid number of bytes to read")
        nodata_val = b""
        empty_values = (b"", None)
        
        buf = self._read_buf
        pos = self._read_pos

        # Special case for when the number of bytes to read is unspecified.
        if n is None or n == -1:
            self._rewind_read_buf(rewind_raw_stream=False)
            chunks = [buf[pos:]]  # Strip the consumed bytes.
            current_size = 0
            while True:
                # Read until EOF or until read() would block.
                chunk = self.raw.read()
                if chunk in empty_values:
                    nodata_val = chunk
                    break
                current_size += len(chunk)
                chunks.append(chunk)
            return b"".join(chunks) or nodata_val

        # The number of bytes to read is specified, return at most n bytes.
        avail = len(buf) - pos  # Length of the available buffered data.
        if n <= avail:
            # Fast path: the data to read is fully buffered.
            self._read_pos += n
            return buf[pos:pos+n]
        # Slow path: read from the stream until enough bytes are read,
        # or until an EOF occurs or until read() would block.
        chunks = [buf[pos:]]
        wanted = max(self.buffer_size, n)
        while avail < n:
            chunk = self.raw.read(wanted)
            if chunk in empty_values:
                nodata_val = chunk
                break
            avail += len(chunk)
            chunks.append(chunk)
        # n is more then avail only when an EOF occurred or when
        # read() would have blocked.
        n = min(n, avail)
        out = b"".join(chunks)
        self._read_buf = out[n:]  # Save the extra data in the buffer.
        self._read_pos = 0
        return out[:n] if out else nodata_val
    
    
    def peek(self, n=0):
        """Returns buffered bytes without advancing the position.

        The argument indicates a desired minimal number of bytes; we
        do at most one raw read to satisfy it.  We never return more
        than self.buffer_size.
        """        
        self._flush_write_buffer()
        
        want = min(n, self.buffer_size)
        have = len(self._read_buf) - self._read_pos
        if have < want or have <= 0:
            to_read = self.buffer_size - have
            current = self.raw.read(to_read)
            if current:
                self._read_buf = self._read_buf[self._read_pos:] + current
                self._read_pos = 0
        return self._read_buf[self._read_pos:]
    
    
    def readinto(self, b):
        """Reads up to len(b) bytes into b.

        Like read(), this may issue multiple reads to the underlying raw
        stream, unless the latter is 'interactive'.

        Returns the number of bytes read (0 for EOF).

        Raises BlockingIOError if the underlying raw stream has no
        data at the moment.
        """
        self._flush_write_buffer()
        
        # XXX This ought to work with anything that supports the buffer API
        data = self._read_bytes(len(b))
        n = len(data)
        try:
            b[:n] = data
        except TypeError as err:
            import array
            if not isinstance(b, array.array):
                raise
            b[:n] = array.array(b'b', data)
        return n
    
            
    def read(self, n=None):
        """Read n bytes.

        Returns exactly n bytes of data unless the underlying raw IO
        stream reaches EOF or if the call would block in non-blocking
        mode. If n is negative, read until EOF or until read() would
        block.
        """
        """Reads and returns up to n bytes.

        If the argument is omitted, None, or negative, reads and
        returns all data until EOF.

        If the argument is positive, and the underlying raw stream is
        not 'interactive', multiple raw reads may be issued to satisfy
        the byte count (unless EOF is reached first).  But for
        interactive raw streams and pipes, at most one raw
        read will be issued, and a short result does not imply that
        EOF is imminent.

        Returns an empty bytes array on EOF, or if n == 0.

        Raises BlockingIOError if the underlying raw stream has no
        data at the moment.
        """
        """A buffered interface to random access streams.
    
        The constructor creates a reader and writer for a seekable stream,
        raw, given in the first argument. If the buffer_size is omitted it
        defaults to DEFAULT_BUFFER_SIZE.
        """        
        self._flush_write_buffer()
        self._read_bytes(n)
            
            
    def read1(self, n):
        """Reads up to n bytes, with at most one read() system call."""
        # Returns up to n bytes.  If at least one byte is buffered, we
        # only return buffered bytes.  Otherwise, we do one raw read.
        if n < 0:
            raise ValueError("number of bytes to read must be positive")
        if n == 0:
            return b""

        self.peek(1)
        return self._read_bytes(
            min(n, len(self._read_buf) - self._read_pos))



    ### Writing ###


    def _flush_write_buffer(self):
        written = 0
        try:
            while self._write_buf:
                n = self.raw.write(self._write_buf)
                if n > len(self._write_buf) or n < 0:
                    raise IOError("write() returned incorrect number of bytes")
                del self._write_buf[:n]
                written += n
            self.raw.flush()
        except BlockingIOError as e:
            n = e.characters_written
            del self._write_buf[:n]
            written += n
            raise BlockingIOError(e.errno, e.strerror, written)



    def write(self, b):  
        
        """Write the given buffer to the IO stream.

        Return the number of bytes written, which is never less than
        len(b).

        Raises BlockingIOError if the buffer is full and the
        underlying raw stream cannot accept more data at the moment.
        """
        self._rewind_read_buf(rewind_raw_stream=True)
         
        if self.closed:
            raise ValueError("write to closed file")
        if isinstance(b, unicode):
            raise TypeError("can't write unicode to binary stream")
        with self._write_lock:
            # XXX we can implement some more tricks to try and avoid
            # partial writes
            if len(self._write_buf) > self.buffer_size:
                # We're full, so let's pre-flush the buffer
                try:
                    self._flush_write_buffer()
                except BlockingIOError as e:
                    # We can't accept anything else.
                    # XXX Why not just let the exception pass through?
                    raise BlockingIOError(e.errno, e.strerror, 0)
            before = len(self._write_buf)
            self._write_buf.extend(b)
            written = len(self._write_buf) - before
            if len(self._write_buf) > self.buffer_size:
                try:
                    self._flush_write_buffer()
                except BlockingIOError as e:
                    if len(self._write_buf) > self.buffer_size:
                        # We've hit the buffer_size. We have to accept a partial
                        # write and cut back our buffer.
                        overage = len(self._write_buf) - self.buffer_size
                        written -= overage
                        self._write_buf = self._write_buf[:self.buffer_size]
                        raise BlockingIOError(e.errno, e.strerror, written)
            return written






    ### Positioning ###

    def seek(self, pos, whence=0):

        if not (0 <= whence <= 2):
            raise ValueError("invalid whence value")   
        
        if self._write_buf:
            self._flush_write_buffer()
        else:
            if whence == 1:
                pos -= len(self._read_buf) - self._read_pos    
            self._rewind_read_buf(rewind_raw_stream=False)
            
        new_pos = self.raw.seek(pos, whence)    
        
        if new_pos < 0:
            raise IOError("seek() returned invalid position")
        
        return new_pos
        
        
    def tell(self):
        
        if self._write_buf:
            pos = self.raw.tell() + len(self._write_buf) 
        else:
            pos = self.raw.tell() - len(self._read_buf) + self._read_pos

        if pos < 0:
            raise IOError("tell() returned an invalid position")
        return pos




    def truncate(self, pos=None):
        # Flush the stream.  We're mixing buffered I/O with lower-level I/O,
        # and a flush may be necessary to synch both views of the current
        # file state.
        
        self._flush_write_buffer()
  
        if pos is None:
            pos = self.tell()
        return self.raw.truncate(pos)


    ### Flush and close ###

    def flush(self):
        
        if self._write_buf:
            self._flush_write_buffer()
        else:
            self._rewind_read_buf(rewind_raw_stream=True)
        
    def close(self):
        if not self.closed and self.raw is not None:
            self.flush()
            self.raw.close()

    def detach(self):
        if self.raw is None:
            raise ValueError("raw stream already detached")
        self.flush()
        raw = self.raw
        self.raw = None
        return raw




    ### Inquiries ###

    def seekable(self):
        return self.raw.seekable()

    def readable(self):
        return self.raw.readable()

    def writable(self):
        return self.raw.writable()

    @property
    def closed(self):
        return self.raw.closed

    @property
    def name(self):
        return self.raw.name

    @property
    def mode(self):
        return self.raw.mode

    def __repr__(self):
        clsname = self.__class__.__name__
        try:
            name = self.name
        except AttributeError:
            return "<rsio.{0}>".format(clsname)
        else:
            return "<rsio.{0} name={1!r}>".format(clsname, name)

    ### Lower-level APIs ###

    def fileno(self):
        return self.raw.fileno()


    def isatty(self):
        return self.raw.isatty()

if USE_ABC:
    io.BufferedIOBase.register(RSBufferedRandom)




class RSTextIOWrapper(io.TextIOWrapper, RSIOBase):


    def flush(self):
        self.buffer.flush()
        self._telling = self._seekable

    def close(self):
        if self.buffer is not None:
            try:
                self.flush()
            except IOError:
                pass  # If flush() fails, just give up
            self.buffer.close()
           
'''
           