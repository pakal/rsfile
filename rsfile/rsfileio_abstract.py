# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys, os, time, threading, multiprocessing, collections, functools, stat
from array import array
from contextlib import contextmanager

import errno

from . import rsfile_definitions as defs
from .rsfile_registries import IntraProcessLockRegistry, _default_rsfile_options

USE_MEMORYVIEW_CAST = hasattr(memoryview, "cast")

class RSFileIOAbstract(defs.io_module.RawIOBase):
    """
    This class is an improved version of the raw stream :class:`io.FileIO`, relying on native OS primitives,
    and offering much more control over the behaviour of the file stream.

    Hopefully you won't have to deal directly with its constructor, since factory
    functions like :func:`rsopen` give you a much easier access to streams chain,
    including buffering and encoding aspects.

    .. rubric::
        Target determination parameters

    These parameters determine if a new raw file stream will be opened from the filesystem, or
    if an existing one will be wrapped by the new RSFileIo instance.

    - *path* (unicode/bytes or None): The path of the regular file to be opened.
      If ``fileno`` or ``handle`` is provided, ``path`` is only used as additional
      information.
    - *fileno* (integer or None): if provided, it must be an open C-style file
      descriptor, compatible with the *Mode parameters* requested, and which will be used
      as an underlying raw stream. Such file descriptors should be available on all platforms,
      but on windows (where they are only emulated) they might be too buggy to benefit
      from file locking and other advanced features.
    - *handle* (handle or None): if provided, it must be a native open file
      handle, compatible with the *Mode parameters* requested, and which will be used
      as an underlying raw stream. On unix platforms, it is the same as a ``fileno``,
      and on windows it must be a win32 Handle (an integer) or a pyHandle instance from pywin32.
    - *closefd* (boolean): if ``fileno`` or ``handle`` is given, this parameter determines whether
      the wrapped raw file stream will be closed when the stream gets closed or deleted, or whether
      it will be left open. When creating a new raw file stream from ``path``, ``closefd`` must
      necessarily be True.

    .. rubric::
        Mode parameters

    These parameters determine the access checking that will be done while manipulating
    the stream. The file must necessarily be opened at least with read or write access,
    and can naturally be opened with both.

    - *read* (boolean): Open the file with read access (doesn't allow file truncation).
    - *write* (boolean): Open the file with write access (allows file truncation).
    - *append* (boolean): Open the file in append mode, i.e on most OSes, write operations
      will automatically move the file pointer to the end of file  before actually writing
      (the file pointer is not restored afterwards). ``append`` implicitly forces ``write`` to *True*.

    See RSOpen() docs for the semantic of other parameters.
    """

    def __init__(self,
                 path=None,  # it seems pywin32 already uses unicode versions of these functions, so it's cool  :-)
                 fileno=None,
                 handle=None,
                 closefd=True,

                 read=False,
                 write=False,
                 append=False,

                 must_create=False, must_not_create=False,  # only used on file opening

                 synchronized=False,
                 inheritable=False,
                 permissions=0o777):

        self.enforced_locking_timeout_value = _default_rsfile_options["enforced_locking_timeout_value"]
        self.default_spinlock_delay = _default_rsfile_options["default_spinlock_delay"]

        # Preliminary normalization
        if append:
            write = True  # append implies write

        # we retrieve the dict of provided arguments, except self
        kwargs = locals()
        del kwargs["self"]
        del kwargs["closefd"]  # not needed at inner level

        # HERE WE CHECK EVERYTHING !!!

        if path is not None and not isinstance(path, (bytes, unicode)):
            raise defs.BadValueTypeError("If provided, path must be a string.")

        if bool(path) + (fileno is not None) + (handle is not None) != 1:
            raise defs.BadValueTypeError("File must provide path, fileno or handle value, and only one of these.")

        if not read and not write:
            raise defs.BadValueTypeError("File can't be both non-writable and non-readable.")

        if must_create and must_not_create:
            raise defs.BadValueTypeError("File can't be wanted both as existing and unexisting.")

        if not closefd and not (fileno or handle):
            raise defs.BadValueTypeError("Cannot use closefd=False without providing a descriptor to wrap.")

        # variables to determine future write/read operations
        self._readable = read
        self._writable = write  # 'append' enforced the value of 'write' to True, just above
        self._append = append
        self._must_create = must_create
        self._must_not_create = must_not_create

        self._synchronized = synchronized
        self._inheritable = inheritable

        name = None  # 'name' : descriptor exposed just for retrocompatibility !!!
        if path is not None:
            name = path
            self._origin = "path"
        elif fileno is not None:
            if int(fileno) < 0:
                raise defs.BadValueTypeError("A fileno to be wrapped can't be negative.")
            name = fileno
            self._origin = "fileno"
        elif handle is not None:
            if int(handle) < 0:
                raise defs.BadValueTypeError("A handle to be wrapped can't be negative.")
            name = handle
            self._origin = "handle"
        self.name = name  # do not use self._name, else unit-tests corner cases don't work anymore...

        """ Aborted - don't mix stream and filesystem methods !!
        self._path = None
        if isinstance(path, basestring):
            try: 
                self._path = os.path.normcase(os.path.normpath(os.path.realpath(path)))
            except EnvironmentError: # weirdo path, just make it absolue...
                self._path = os.path.abspath(path)
        """

        self._unique_id = None  # unique identifier of the file, eg. (device, inode) pair
        self._fileno = None  # C style file descriptor, might be created only on request
        self._handle = None  # native platform handle other than fileno - if existing
        self._closefd = closefd  # set BEFORE creating streams

        if path:
            null_char = ("\0" if isinstance(path, str) else b"\0")
            if null_char in path:
                raise defs.BadValueTypeError("NULL characters forbidden in file path")

        try:
            self._inner_create_streams(**kwargs)

            seekable = True
            if isinstance(self._fileno, (int, long)):
                # we bypass Rsfile for file descriptors that are pipes, devices, directories, symlinks etc.
                st_mode = os.fstat(self._fileno).st_mode  # might raise
                if stat.S_ISDIR(st_mode):
                    assert fileno or handle, (fileno, handle)  # it must NOT be a newly created file object, else bug
                    self._closefd = False  # disown file descriptor
                    raise IOError(errno.EISDIR, "Can't wrap a directory in FileIO")
                is_regular = stat.S_ISREG(st_mode)
                seekable = is_regular
            else:
                pass  # if we only have a handle, we're on windows, so no such pipe
            self._seekable = seekable

            # These two keys, set by _inner_create_streams(), are used to
            # identify the file and handle in the intraprocess lock registry
            assert self._lock_registry_inode, self._lock_registry_inode
            assert self._lock_registry_descriptor, self._lock_registry_descriptor

        except OverflowError as e:
            raise defs.BadValueTypeError(e)  # probably a too big filedescriptor number

        if append:
            self.seek(0, os.SEEK_END)  # required by unit tests, might raise if non-seekable file...

    def __repr__(self):
        return ('<rsfile.RSFileIO name=%s mode="%s" origin="%s" closefd=%s>' %
                ('"%s"' % self.name if isinstance(self.name, basestring) else self.name,
                 self.mode, self.origin, self._closefd))

    def close(self):

        if not self.closed:

            try:
                defs.io_module.RawIOBase.close(self)  # we first mark the stream as closed... it flushes, also.
            finally:
                # even if implicit flush() failed, we properly close underlying streams

                with IntraProcessLockRegistry.mutex:

                    for (handle, shared, start, end) in IntraProcessLockRegistry.remove_file_locks(
                            self._lock_registry_inode, self._lock_registry_descriptor):
                        # print (">>>>>>>> ", (handle, shared, start, end))
                        length = None if end is None else (end - start)
                        self._inner_file_unlock(length, start)

                    self._inner_close_streams()  # should mark the raw stream as closed even if some operations fail

    def __del__(self):
        """Destructor.  Calls close()."""
        # The try/except block is in case this is called at program
        # exit time, when it's possible that globals have already been
        # deleted, and then the close() call might fail.  Since
        # there's nothing we can do about such failures and they annoy
        # the end users, we suppress the traceback.
        # BEWARE, also called if __init__() itself raised an exception!
        try:
            self.close()
        except:
            pass

    def __reduce__(self):
        raise defs.BadValueTypeError("RSFileIO is not pickleable")

    def seekable(self):
        self._checkClosed()
        return self._seekable

    def readable(self):
        self._checkClosed()
        return self._readable

    def writable(self):
        self._checkClosed()
        return self._writable

    # # # Read-only Attributes # # #

    @property
    def mode(self):

        # see _fileio.c reference implementation

        if defs.HAS_X_OPEN_FLAG:
            if self._must_create:
                if self.writable() and self.readable():
                    return "xb+"
                else:
                    return "xb"
        if self._append:
            if self.readable():
                return "ab+"
            else:
                return "ab"
        elif self.writable():
            if self.readable():
                if self._must_not_create:
                    return "rb+"
                else:
                    return "rb+"  # WARNING - python stdlib returns this instead of wb+... let it be
            else:
                return "wb"
        else:
            assert self.readable()
            return "rb"

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value  # used to please the stdlib tests...

    @property
    def origin(self):
        return self._origin

    @property
    def closefd(self):
        return self._closefd

    # # # Methods that must be overridden in OS-specific file types # # #

    def fileno(self):
        self._checkClosed()
        return self._inner_fileno()

    def handle(self):
        self._checkClosed()
        return self._inner_handle()

    def unique_id(self):
        self._checkClosed()
        if self._unique_id is None:
            self._unique_id = self._inner_unique_id()
        assert self._unique_id, self._unique_id
        return self._unique_id

    uid = unique_id  # deprecated alias

    def times(self):
        self._checkClosed()
        return self._inner_times()

    def size(self):  # non standard method
        self._checkClosed()
        return self._inner_size()

    def tell(self):
        self._checkClosed()
        res = self._inner_tell()
        return res

    def seek(self, offset, whence=os.SEEK_SET):
        self._checkClosed()

        # print ("raw seek called to offset ", offset, " - ", whence, "with size", self._inner_size())
        if not isinstance(offset, (int, long)):
            raise defs.BadValueTypeError("Expecting an integer as argument for seek")
        res = self._inner_seek(offset, whence)

        return res

    def readall(self):
        """Reads until EOF, using multiple read() calls.
      
        No limit is set on the amount of data read, so you might
        fill up your RAM with this method.
        """
        chunks = []
        while True:
            data = self.read(defs.DEFAULT_BUFFER_SIZE)
            if not data:
                break
            chunks.append(data)
        if chunks:
            return b"".join(chunks)
        else:
            # b'' or None
            return data

    def read(self, n=-1):
        """Reads and returns up to n bytes (a negative value for n means *infinity*).

        Returns an empty bytes object on EOF, or None if the object is
        set not to block and has no data ready to be read.
        """
        self._checkClosed()
        self._checkReadable()

        if n is None or n < 0:
            return self.readall()

        mybytes = self._inner_read(n)
        assert mybytes is None or isinstance(mybytes, bytes), type(mybytes)
        return mybytes

    def readinto(self, buffer):
        """Reads up to len(b) bytes into b.

        Inefficient in RSFile, as several data copies can be required
        to obtain the result - use read() instead.
    
        Returns the number of bytes read (0 for EOF or if len(buffer) == 0).
        """
        self._checkClosed()
        self._checkReadable()

        if USE_MEMORYVIEW_CAST:
            buffer = memoryview(buffer).cast('B')

        mybytes = self._inner_read(len(buffer))
        byteslen = len(mybytes)
        assert mybytes is None or isinstance(mybytes, bytes), type(mybytes)

        if isinstance(buffer, array):
            typecode = b"b" if (sys.version_info[:2] < (3, 0)) else "b"  # typecode weirdness...
            buffer[0:byteslen] = array(typecode, mybytes)
        else:
            # for bytearray, memoryview...
            buffer[0:byteslen] = mybytes

        return byteslen

    def write(self, buffer):
        """Writes the given data to the IO stream.

        Returns the number of bytes written, which may be less than len(b), or None if
        write couldn't be done on a non-blocking device.
        
        Accepted buffer types are bytes, bytearray, array.array, and memoryview (the last two being inefficient to
        write).
        """

        # TODO: improve low level routines to accept buffers and arrays as data, so that we don't have to
        # convert/copy stuffs around...

        self._checkClosed()
        self._checkWritable()

        if isinstance(buffer, unicode):
            raise defs.BadValueTypeError("can't write unicode to binary stream")

        if isinstance(buffer, memoryview):
            buffer = buffer.tobytes()
        elif isinstance(buffer, array):
            buffer = buffer.tostring()

        res = self._inner_write(buffer)
        # assert res == len(buffer), str(res, len(buffer)) # NOOO - we might have less than that actually if disk full !

        assert not (len(
            buffer) and res == 0), "Abnormal state, 0 bytes from buffer were written to raw stream, write() should " \
                                   "return None instead, in this case"
        if res is not None and (res < 0 or res > len(buffer)):
            raise RuntimeError(
                "Madness - %d bytes written instead of max %d for buffer '%r'" % (res, len(buffer), buffer))

        return res  # might be None (nonblocking IO)

    def truncate(self, size=None, zero_fill=True):
        """
        See RSOpen() doc.
        """

        self._checkSeekable()  # handles PIPES, already checks if closed
        self._checkWritable()  # Important !


        if size is None:
            size = self.tell()
        elif size < 0:
            raise IOError(errno.EINVAL,
                          "Invalid argument : truncation size must be None or positive integer, not '%s'" % size)

        current_size = self.size()
        if size == current_size:
            pass  # nothing to be done
        elif size < current_size:
            self._inner_reduce(size)
        else:
            assert size > current_size, (size, current_size)
            self._inner_extend(size, zero_fill)

            current_size = self.size()
            if (current_size != size):  # no native operation worked for it. so we fill with zeros by ourselves

                assert current_size < size
                old_pos = self._inner_tell()
                self._inner_seek(current_size, os.SEEK_SET)
                bytes_to_write = size - current_size
                (q, r) = divmod(bytes_to_write, defs.DEFAULT_BUFFER_SIZE)

                for _ in range(q):
                    padding = b'\0' * defs.DEFAULT_BUFFER_SIZE
                    self._inner_write(padding)
                count = self._inner_write(b'\0' * r)
                assert count == r, (count, r)  # no blocking writes for files, theoretically...
                self._inner_seek(old_pos)  # important
        return self.size()

    def flush(self):
        """
        See RSOpen() doc.

        That raw stream should have no buffering except that of the kernel,
        which can be flushed by sync() calls
        """
        self._checkClosed()

    def sync(self, metadata=True, full_flush=True):
        """
        See RSOpen() doc.
        """
        self._checkClosed()
        self._inner_sync(metadata, full_flush)

    def _convert_relative_offset_to_absolute(self, offset, whence):

        if offset is None:
            offset = 0

        if whence == os.SEEK_SET:
            abs_offset = offset
        elif whence == os.SEEK_CUR:
            abs_offset = self._inner_tell() + offset
        else:
            abs_offset = self._inner_size() + offset

        return abs_offset

    @contextmanager
    def _lock_remover(self, length, offset, whence):
        # we do nothing on __enter__()
        yield
        # we unlock on __exit__()
        self.unlock_file(length=length, offset=offset, whence=whence)

    def lock_file(self, timeout=None, length=None, offset=None, whence=os.SEEK_SET, shared=None):

        self._checkSeekable()  # pipes and such can't be locked... already checks if closed

        if timeout is not None and (not isinstance(timeout, (int, long, float)) or timeout < 0):
            raise defs.BadValueTypeError("timeout must be None or positive float.")

        if length is not None and (not isinstance(length, (int, long)) or length < 0):
            raise defs.BadValueTypeError("length must be None or positive integer.")

        if offset is not None and not isinstance(offset, (int, long)):
            raise defs.BadValueTypeError("offset must be None or an integer.")

        if whence not in defs.SEEK_VALUES:
            raise defs.BadValueTypeError("whence must be a valid SEEK_\* value")

        if shared is not None and shared not in (True, False):
            raise defs.BadValueTypeError("shared must be None or True/False.")

        if shared is None:
            if self._writable:
                shared = False
            else:
                shared = True

        if (shared and not self._readable) or (not shared and not self._writable):
            raise IOError("Can't obtain exclusive lock on non-writable stream, or shared lock on non-readable stream.")

        abs_offset = self._convert_relative_offset_to_absolute(offset, whence)
        blocking = timeout is None  # here, it means "forever waiting for the lock"
        # we enforce spin-locking if a global timeout exists
        low_level_blocking = blocking if (self.enforced_locking_timeout_value is None) else False

        start_time = time.time()

        def check_timeout(env_error):
            """
            If timeout has expired, raises the exception given as parameter.
            Else, sleeps for a short period.
            """
            delay = time.time() - start_time
            if not blocking:  # we have a timeout set

                if (delay >= timeout):  # else, we try again until success or timeout
                    (error_code, title) = env_error.args
                    filename = getattr(self, 'name', 'Unknown File')  # to be improved
                    raise defs.LockingException(error_code, title, filename)

            elif (self.enforced_locking_timeout_value is not None) and (
                        delay >= self.enforced_locking_timeout_value):  # for blocking attempts only
                raise RuntimeError(
                    "Locking delay exceeded global 'enforced_locking_timeout_value' option (%d s)." %
                    self.enforced_locking_timeout_value)

            time.sleep(self.default_spinlock_delay)

        success = False

        while (not success):

            # STEP ONE : acquiring ownership on the lock inside current process
            res = IntraProcessLockRegistry.register_file_lock(self._lock_registry_inode, self._lock_registry_descriptor,
                                                              length, abs_offset, low_level_blocking, shared,
                                                              self.enforced_locking_timeout_value)

            if not res:
                check_timeout(IOError(errno.EPERM, "Current process has already locked this byte range"))
                continue

            try:

                while (not success):

                    # STEP TWO : acquiring the lock for real, at kernel level
                    try:

                        # import multiprocessing
                        # print ("---------->", multiprocessing.current_process().name, " LOCKED ", (length,
                        # abs_offset))

                        self._inner_file_lock(length=length, abs_offset=abs_offset, blocking=low_level_blocking,
                                              shared=shared)

                        success = True  # we leave the two loops

                    except EnvironmentError as e:
                        check_timeout(e)

            finally:
                if not success:
                    res = IntraProcessLockRegistry.unregister_file_lock(self._lock_registry_inode,
                                                                        self._lock_registry_descriptor, length,
                                                                        abs_offset)
                    assert res in (True, False)  # there may or may not be locks left after that, we dunno

        return self._lock_remover(length, abs_offset, os.SEEK_SET)

    def unlock_file(self, length=None, offset=0, whence=os.SEEK_SET):

        self._checkSeekable()  # pipes and such can't be locked... already checks if closed

        if length is not None and (not isinstance(length, (int, long)) or length < 0):
            raise defs.BadValueTypeError("length must be None or positive integer.")

        if offset is not None and (not isinstance(offset, (int, long)) or offset < 0):
            raise defs.BadValueTypeError("offset must be None or positive integer.")

        if whence not in defs.SEEK_VALUES:
            raise defs.BadValueTypeError("whence must be a valid SEEK_\* value")

        # import multiprocessing
        # print ("---------->", multiprocessing.current_process().name, " UNLOCKED ", (unix.LOCK_UN, length,
        # abs_offset, os.SEEK_SET))
        abs_offset = self._convert_relative_offset_to_absolute(offset, whence)

        with IntraProcessLockRegistry.mutex:  # IMPORTANT - keep the registry lock during the whole operation
            IntraProcessLockRegistry.unregister_file_lock(self._lock_registry_inode, self._lock_registry_descriptor,
                                                          length, abs_offset)
            self._inner_file_unlock(length, abs_offset)

    # # Private methods - no check is made on their argument or the file object state ! # #

    def _inner_create_streams(self, path, read, write, append, must_create, must_not_create, synchronized, inheritable,
                              fileno, handle, closefd, permissions):
        self._unsupported("_inner_create_streams")

    def _inner_close_streams(self):
        self._unsupported("_inner_close_streams")

    def _inner_reduce(self, size):
        self._unsupported("_inner_reduce")

    def _inner_extend(self, size, zero_fill):
        self._unsupported("_inner_extend")

    def _inner_sync(self, metadata, full_flush):
        self._unsupported("sync")

    def _inner_fileno(self):
        self._unsupported("fileno")

    def _inner_handle(self):
        self._unsupported("handle")

    def _inner_unique_id(self):
        self._unsupported("unique_id")

    def _inner_times(self):
        self._unsupported("times")

    def _inner_size(self):
        self._unsupported("size")

    def _inner_tell(self):
        self._unsupported("tell")

    def _inner_seek(self, offset, whence):
        self._unsupported("seek")

    def _inner_read(self, n):
        self._unsupported("read")

    def _inner_write(self, buffer):
        self._unsupported("write")

    def _inner_file_lock(self, length, abs_offset, blocking, shared):
        self._unsupported("file_lock")

    def _inner_file_unlock(self, length, abs_offset):
        self._unsupported("file_unlock")


defs.io_module.RawIOBase.register(RSFileIOAbstract)
