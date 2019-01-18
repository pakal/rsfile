# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

"""
Reimplementation of raw streams for unix-like OS, with advanced abilities.
"""

import sys, os, functools, errno, time, stat, threading, locale
from . import rsfileio_abstract
from . import rsfile_definitions as defs

from .rsbackend import unix_stdlib as unix
from .rsfile_registries import IntraProcessLockRegistry

UNIX_MSG_ENCODING = locale.getpreferredencoding()


class RSFileIO(rsfileio_abstract.RSFileIOAbstract):
    # Warning - this is to be used as a static method ! #
    def _unix_error_converter(f):  # @NoSelf
        @functools.wraps(f)
        def wrapper(self, *args, **kwds):
            try:
                return f(self, *args, **kwds)
            except unix.error as e:
                # WARNING - this is not always a subclass of OSERROR on python2
                if isinstance(e, IOError):
                    raise
                else:
                    traceback = sys.exc_info()[2]

                    if not isinstance(e.strerror, unicode):
                        strerror = e.strerror.decode(UNIX_MSG_ENCODING, 'replace')
                    else:
                        strerror = e.strerror

                    raise IOError, (e.errno, strerror, unicode(self._name)), traceback

        return wrapper

    @_unix_error_converter
    def _purge_pending_related_file_descriptors(self):
        """
        Returns True iff this unique_id has no more locks left and data left, i/e really closing descriptors is OK.
        """

        with IntraProcessLockRegistry.mutex:
            res = IntraProcessLockRegistry.unique_id_has_locks(self._lock_registry_inode)
            if not res:  # no more locks left for that unique_id
                data_list = IntraProcessLockRegistry.remove_unique_id_data(self._lock_registry_inode)
                for fd in data_list:  # we close all pending file descriptors (which were left opened to prevent
                    # fcntl() lock autoremoving)
                    unix.close(fd)

            return not res

    # # Private methods - no check is made on their argument or the file object state ! # #
    @_unix_error_converter
    def _inner_create_streams(self, path, read, write, append, must_create, must_not_create, synchronized, inheritable,
                              fileno, handle, permissions):

        # Note : opening broken links works if we're in "w" mode, and raises error in "r" mode,
        # like for normal unexisting files.

        if handle is not None:
            assert fileno is None
            self._fileno = self._handle = handle

        elif fileno is not None:
            assert handle is None
            self._fileno = self._handle = fileno

        else:  # we open the file with low level posix IO - the unix "open()"  function

            if isinstance(path, unicode):
                strname = path.encode(
                    sys.getfilesystemencoding())  # let's take no risks - and do not use locale.getpreferredencoding(
                # ) here
            else:
                strname = path

            flags = 0  # Note that unix.O_LARGEFILE is actually irrelevant

            if synchronized:
                flags |= unix.O_SYNC

            if read and write:
                flags |= unix.O_RDWR
            elif write:
                flags |= unix.O_WRONLY
            else:
                flags |= unix.O_RDONLY

            if append:
                flags |= unix.O_APPEND

            if must_not_create:
                pass  # it's the default case for open() function
            elif must_create:
                flags |= unix.O_CREAT | unix.O_EXCL
            else:
                flags |= unix.O_CREAT  # by default - we create the file iff it doesn't exists

            # print("Creating unix stream with context", locals())
            self._fileno = self._handle = unix.open(strname, flags, permissions)

            # on unix we must prevent the opening of directories, but not named fifos or other special files
            stats = unix.fstat(self._fileno).st_mode
            if stat.S_ISDIR(stats):
                raise IOError(errno.EISDIR, "RSFile can't open directories", self.name)

            # we don't use O_CLOEXEC flag (available since Linux 2.6.23) for compatibility and safety
            if hasattr(os, "set_inheritable"):
                os.set_inheritable(self._fileno, inheritable)  # for safety we call it in any case
            else:
                # before PEP0446, newly created file descriptors were inheritable by default
                if not inheritable:
                    old_flags = unix.fcntl(self._fileno, unix.F_GETFD, 0);
                    if not (old_flags & unix.FD_CLOEXEC):
                        unix.fcntl(self._fileno, unix.F_SETFD, old_flags | unix.FD_CLOEXEC);

        # WHATEVER the origin of the stream, we initialize these fields:
        self._lock_registry_inode = self.unique_id()  # enforces caching of unique_id
        self._lock_registry_descriptor = self._fileno

    @_unix_error_converter
    def _inner_close_streams(self):
        if self._closefd:
            with IntraProcessLockRegistry.mutex:
                # safety mechanisms for fcntl() and its Unlock-All-On-Single-Close semantic
                IntraProcessLockRegistry.add_unique_id_data(self._lock_registry_inode, self._lock_registry_descriptor)
                self._purge_pending_related_file_descriptors()
                # we assume that there are chances for this to be the only handle pointing this precise file
                IntraProcessLockRegistry.try_deleting_unique_id_entry(self._lock_registry_inode)

    @_unix_error_converter
    def _inner_reduce(self, size):
        assert size >= 0, size
        unix.ftruncate(self._fileno, size)

    @_unix_error_converter
    def _inner_extend(self, size, zero_fill):
        assert size >= 0, size
        assert zero_fill in (True, False), zero_fill
        # posix truncation is ALWAYS "zerofill" actually...
        unix.ftruncate(self._fileno, size)

    @_unix_error_converter
    def _inner_sync(self, metadata, full_flush):

        if full_flush:  # full_flush is more important than metadata
            try:
                unix.fcntl(self._fileno, unix.F_FULLFSYNC, 0)  # Mac OS X only
                # print("FULLFLUSH_UNIX_DONE")
                return
            except unix.error:
                pass

        if not metadata and hasattr(unix, "fdatasync"):
            try:
                # theoretically, file size will properly be updated, if it is necessary to preserve data integrity
                unix.fdatasync(self._fileno)  # not supported on Mac OS X
                # print("FDATASYNC_UNIX_DONE")
                return
            except unix.error:
                pass

        unix.fsync(self._fileno)  # last attempt : metadata flush without full_sync guarantees
        # print("FSYNC_UNIX_DONE")

    def _inner_fileno(self):
        assert self._fileno
        return self._fileno

    def _inner_handle(self):
        assert self._handle
        return self._handle

    @_unix_error_converter
    def _inner_unique_id(self):
        """
        Unix-like systems SHOULD always provide meaningful device/inode values.

        According to specs: http://pubs.opengroup.org/onlinepubs/009695399/basedefs/sys/stat.h.html

        The st_ino and st_dev fields taken together uniquely identify the file within the system.

        Unless otherwise specified, the structure members st_mode, st_ino, st_dev, st_unique_id, st_gid, st_atime,
        st_ctime, and st_mtime shall have meaningful values for all file types defined in IEEE Std 1003.1-2001.
        """
        stats = unix.fstat(self._fileno)
        _unique_id = (stats.st_dev, stats.st_ino)
        if not all(_unique_id):
            raise IOError(errno.ENOSYS, "No unique dev/inode identifier available")
        return _unique_id

    @_unix_error_converter
    def _inner_times(self):
        """
        See STAT() docs:

        Not all of the Linux file systems implement all of the time fields. Some file system types allow mounting in
        such a way that file and/or directory accesses do not cause an update of the st_atime field. (See noatime,
        nodiratime, and relatime in mount(8), and related information in mount(2).) In addition, st_atime is not
        updated if a file is opened with the O_NOATIME; see open(2).
        """
        stats = unix.fstat(self._fileno)
        return defs.FileTimes(access_time=stats.st_atime,
                              modification_time=stats.st_mtime)

    @_unix_error_converter
    def _inner_size(self):
        return unix.fstat(self._fileno).st_size

    @_unix_error_converter
    def _inner_tell(self):
        return unix.ltell(self._fileno)

    @_unix_error_converter
    def _inner_seek(self, offset, whence):
        """
        It's OK to seek past the end of file, writing there will extend the file and fill the hole with null bytes.
        """
        return unix.lseek(self._fileno, offset, whence)

    @_unix_error_converter
    def _inner_read(self, n):
        try:
            return unix.read(self._fileno, n)
        except OSError as e:
            # print ("<<< inner read", e.__class__)
            if e.args[0] == errno.EAGAIN:
                return None
            if e.__class__.__name__ == "BrokenPipeError":  # only in Python3
                return b''  # conform to stdlib behaviour
            raise

    '''
    @_unix_error_converter
    def _inner_readinto(self, buffer):
        return unix.readinto(self._fileno, buffer, len(buffer))
    '''

    @_unix_error_converter
    def _inner_write(self, bytes):
        # 'append' is already handled at file opening
        try:
            return unix.write(self._fileno, bytes)
        except OSError as e:
            # print(">>>>>>>>>_inner_write", e.__class__)
            if e.args[0] == errno.EAGAIN:
                return None
            raise

    @_unix_error_converter
    def _inner_file_lock(self, length, abs_offset, blocking, shared):

        # TODO - switch to "Open file description locks (non-POSIX)" on recent Linux one day,
        # to have per-file-descriptor (but inheritable alas) locks

        fd = self._fileno

        if (shared):
            operation = unix.LOCK_SH
        else:
            operation = unix.LOCK_EX

        if not blocking:
            operation |= unix.LOCK_NB
        if length is None:
            length = 0  # that's the "infinity" value for fcntl

        unix.lockf(fd, operation, length, abs_offset, os.SEEK_SET)

    @_unix_error_converter
    def _inner_file_unlock(self, length, abs_offset):

        if length is None:
            length = 0  # that's the "infinity" value for fcntl

        try:
            unix.lockf(self._fileno, unix.LOCK_UN, length, abs_offset, os.SEEK_SET)
        finally:
            self._purge_pending_related_file_descriptors()
