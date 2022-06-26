# -*- coding: utf-8 -*-


"""
Reimplementation of raw streams for windows OS, with advanced abilities.

Note that, like in sys.platform or pywin32, "win32" actually means both x86 and x64 platforms.
"""

import errno
import functools
import locale
import os
import stat
import sys

from . import rsfile_definitions as defs
from . import rsfileio_abstract
from .rsbackend import _utilities as utilities

try:
    from .rsbackend import windows_pywin32 as win32
except ImportError:
    from .rsbackend import windows_ctypes as win32

WIN32_MSG_ENCODING = locale.getpreferredencoding()


class RSFileIO(rsfileio_abstract.RSFileIOAbstract):
    __POSITION_REFERENCES = {
        defs.SEEK_SET: win32.FILE_BEGIN,
        defs.SEEK_CUR: win32.FILE_CURRENT,
        defs.SEEK_END: win32.FILE_END,
    }

    # Warning - this is to be used as a static method ! #
    def _win32_error_converter(f):  # @NoSelf
        @functools.wraps(f)
        def wrapper(self, *args, **kwds):
            try:
                return f(self, *args, **kwds)
            except win32.error as e:
                # WARNING - this is not always a subclass of OSERROR

                traceback = sys.exc_info()[2]
                # print repr(e)str(e[1])+" - "+str(e[2

                # pywin32's pywintypes.error instances have no errno
                if hasattr(e, "errno"):
                    errno = e.errno
                else:
                    errno = utilities.winerror_to_errno(e.winerror)

                # we must convert to unicode the local error message
                if not e.strerror:
                    strerror = "<no error msg>"
                elif isinstance(e.strerror, str):
                    strerror = e.strerror
                else:
                    strerror = e.strerror.decode(WIN32_MSG_ENCODING, "replace")

                raise IOError(errno, strerror, str(self._name)).with_traceback(traceback)

        return wrapper

    def _broken_pipe_ignorer(f):  # @NoSelf
        @functools.wraps(f)
        def wrapper(self, *args, **kwds):
            try:
                return f(self, *args, **kwds)
            except OSError as e:
                if e.__class__.__name__ == "BrokenPipeError":  # only in Python3
                    return b""  # conform to stdlib behaviour
                raise

        return wrapper

    @_win32_error_converter
    def _inner_create_streams(
        self,
        path,
        read,
        write,
        append,
        must_create,
        must_not_create,
        synchronized,
        inheritable,
        fileno,
        handle,
        permissions,
    ):

        assert not (fileno and handle), fileno and handle

        # # # real opening of the file stream # # #
        if handle is not None:
            assert fileno is None
            self._handle = int(handle)
            # print "FILE OPENED VIA HANDLE ", handle

        elif fileno is not None:
            assert handle is None
            self._fileno = fileno
            # print "FILE OPENED VIA FILENO ", fileno
            import msvcrt

            assert msvcrt.get_osfhandle == win32._get_osfhandle
            self._handle = win32._get_osfhandle(fileno)  # required immediately

        else:  # we open the file with CreateFile
            # print "FILE OPENED VIA PATH ", path
            desiredAccess = 0
            if read:  # we mimic the POSIX behaviour : we must have at least read or write
                desiredAccess |= win32.GENERIC_READ
            if write:
                desiredAccess |= win32.GENERIC_WRITE
            assert desiredAccess

            # we reproduce the Unix sharing behaviour : full sharing, and we can move/delete files while they're open
            shareMode = win32.FILE_SHARE_READ | win32.FILE_SHARE_WRITE | win32.FILE_SHARE_DELETE

            creationDisposition = 0
            if must_not_create:
                creationDisposition = win32.OPEN_EXISTING  # 3
            elif must_create:
                creationDisposition = win32.CREATE_NEW  # 1
            else:
                creationDisposition = win32.OPEN_ALWAYS  # 4

            if inheritable:
                securityAttributes = win32.SECURITY_ATTRIBUTES()
                securityAttributes.bInheritHandle = True
                securityAttributes.SECURITY_DESCRIPTOR = None
            else:
                securityAttributes = None

            if not permissions & stat.S_IWUSR:
                flagsAndAttributes = win32.FILE_ATTRIBUTE_READONLY
            else:
                flagsAndAttributes = win32.FILE_ATTRIBUTE_NORMAL

            """  # NOPE, rather a filesystem-level concern here
            if hidden:
                flagsAndAttributes |= win32.FILE_FLAG_DELETE_ON_CLOSE
            """

            if synchronized:
                # DO NOT USE FILE_FLAG_NO_BUFFERING - too many constraints on data alignments
                flagsAndAttributes |= win32.FILE_FLAG_WRITE_THROUGH  # syncs data+metadata
                # Warning - it seems that for some people, metadata is actually NOT written to disk along with data,
                # when using FILE_FLAG_WRITE_THROUGH

            # we can't use FILE_APPEND_DATA flag, because it prevents use from truncating the file later one,
            # so we'll emulate it on each write

            if isinstance(path, bytes):
                path = path.decode(sys.getfilesystemencoding())  # pywin32 wants unicode

            args = (
                path,
                desiredAccess,
                shareMode,
                securityAttributes,
                creationDisposition,
                flagsAndAttributes,
                None,  # hTemplateFile
            )

            handle = win32.CreateFile(*args)  # should raise if it's a DIRECTORY
            # print ">>>File opened : ", path

            self._handle = int(handle)
            if hasattr(handle, "Detach"):  # pywin32
                handle.Detach()

        # WHATEVER the origin of the stream, we initialize these fields:
        self._lock_registry_inode = self._handle  # we don't care about real inode unique_id, since win32 already
        # distinguishes which handle owns a lock
        self._lock_registry_descriptor = self._handle

    @_win32_error_converter
    def _inner_close_streams(self):
        """
        MSDN note : To close a file opened with _get_osfhandle, call _close. The underlying handle
        is also closed by a call to _close, so it is not necessary to
        call the Win32 function CloseHandle on the original handle.

        This function may raise IOError !
        """

        # print "<<<File closed : ", self._name
        if self._closefd:  # always True except when wrapping external file descriptors
            if self._fileno:
                # WARNING - necessary to avoid leaks of C file descriptors
                try:
                    os.close(self._fileno)  # this closes the underlying native handle as well
                except OSError as e:
                    raise IOError(errno.EBADF, "bad file descriptor")
            else:
                win32.CloseHandle(self._handle)

    @_win32_error_converter
    def _inner_reduce(self, size):
        assert size >= 0, size
        old_pos = self._inner_tell()
        self.seek(size)
        # print ("---> inner reduce to ", self.tell())
        win32.SetEndOfFile(self._handle)  # warning - this might fail silently
        self._inner_seek(old_pos)

    @_win32_error_converter
    def _inner_extend(self, size, zero_fill):
        assert size >= 0, size
        assert zero_fill in (True, False), zero_fill
        if not zero_fill:
            old_pos = self._inner_tell()
            self.seek(size)
            win32.SetEndOfFile(self._handle)  # warning - this might fail silently
            self._inner_seek(old_pos)
        else:
            pass  # we can't directly truncate with zero-filling on win32, so just upper levels handle it

    @_win32_error_converter
    def _inner_sync(self, metadata, full_flush):
        # only one type of synchronization : full_flush + metadata
        win32.FlushFileBuffers(self._handle)

    @_win32_error_converter
    def _inner_unique_id(self):
        """
        See docs for GetFileInformationByHandle and BY_HANDLE_FILE_INFORMATION:

        Depending on the underlying network features of the operating system and the type of server connected to,
        the GetFileInformationByHandle function may fail, return partial information, or full information for the
        given file.

        The identifier that is stored in the nFileIndexHigh and nFileIndexLow members is called the file ID. Support
        for file IDs is file system-specific. File IDs are not guaranteed to be unique over time, because file
        systems are free to reuse them. In some cases, the file ID for a file can change over time.

        In the FAT file system, the file ID is generated from the first cluster of the containing directory and the
        byte offset within the directory of the entry for the file. Some defragmentation products change this byte
        offset. (Windows in-box defragmentation does not.) Thus, a FAT file ID can change over time. Renaming a file
        in the FAT file system can also change the file ID, but only if the new file name is longer than the old one.

        handle_info attributes : (dwFileAttributes, ftCreationTime, ftLastAccessTime,
             ftLastWriteTime, dwVolumeSerialNumber, nFileSizeHigh,
             nFileSizeLow, nNumberOfLinks, nFileIndexHigh, nFileIndexLow)
        """

        handle_info = win32.GetFileInformationByHandle(self._handle)
        device = handle_info.dwVolumeSerialNumber
        inode = utilities.double_dwords_to_pyint(handle_info.nFileIndexLow, handle_info.nFileIndexHigh)

        if device <= 0 or inode <= 0:
            raise win32.error(
                win32.ERROR_NOT_SUPPORTED,
                "RsfileInnerUniqueId",
                "Impossible to retrieve win32 device/file-id information",
            )

        _unique_id = (device, inode)
        return _unique_id

    @_win32_error_converter
    def _inner_fileno(self):

        if self._fileno is None:
            # print "EXTRACTING FILENO !"
            # traceback.print_stack()

            # NOTE: these flags seem to be actually IGNORED by libc compatibility
            # layer, but let's be cautious...
            if self._readable and self._writable:
                flags = os.O_RDWR
            elif self._writable:
                flags = os.O_WRONLY
                if self._append:
                    flags |= os.O_APPEND
            else:
                assert self._readable
                flags = os.O_RDONLY

            # NEVER use flag os.O_TEXT, we're in raw IO here !
            self._fileno = win32._open_osfhandle(self._handle, flags)

        assert self._fileno
        return self._fileno

    def _inner_handle(self):
        assert self._handle
        return self._handle

    @_win32_error_converter
    def _inner_times(self):
        """
        See docs for BY_HANDLE_FILE_INFORMATION:

        Not all file systems can record creation and last access time, and not all file systems record them in the
        same manner. For example, on a Windows FAT file system, create time has a resolution of 10 milliseconds,
        write time has a resolution of 2 seconds, and access time has a resolution of 1 day (the access date). On the
        NTFS file system, access time has a resolution of 1 hour. For more information, see File Times.
        """
        handle_info = win32.GetFileInformationByHandle(self._handle)

        return defs.FileTimes(
            access_time=utilities.win32_filetime_to_python_timestamp(
                handle_info.ftLastAccessTime.dwLowDateTime, handle_info.ftLastAccessTime.dwHighDateTime
            ),
            modification_time=utilities.win32_filetime_to_python_timestamp(
                handle_info.ftLastWriteTime.dwLowDateTime, handle_info.ftLastWriteTime.dwHighDateTime
            ),
        )

    @_win32_error_converter
    def _inner_size(self):
        size = win32.GetFileSize(self._handle)
        return size

    @_win32_error_converter
    def _inner_tell(self):
        pos = win32.SetFilePointer(self._handle, 0, win32.FILE_CURRENT)
        return pos

    @_win32_error_converter
    def _inner_seek(self, offset, whence=defs.SEEK_SET):
        """
        It is not an error to set a file pointer to a position beyond the end of the file. The size of the file does
        not increase until you call the  SetEndOfFile,  WriteFile, or  WriteFileEx function. A write operation
        increases the size of the file to the file pointer position plus the size of the buffer written, which results
        in the intervening bytes uninitialized.
        """

        if not isinstance(offset, int):
            raise defs.BadValueTypeError("Offset should be an integer in seek(), not %s object" % type(offset))

        reference = self.__POSITION_REFERENCES[whence]
        new_offset = win32.SetFilePointer(self._handle, offset, reference)
        return new_offset

    @_broken_pipe_ignorer
    @_win32_error_converter
    def _inner_read(self, n):
        (res, mybytes) = win32.ReadFile(self._handle, n)  # returns bytes
        return mybytes

    '''
    @_win32_error_converter  # abandoned for now
    def _inner_readinto(self, buffer):
        """ Warning - this method is currently inefficient since it converts C string into
            python str and then into bytearray, but this will be optimized later by rewriting in C module
        """

        (res, buffer) = win32.ReadFile(self._handle, buffer)
        if isinstance(buffer, array):
            try:
                buffer[0:len(mybytes)] = array(b"b", mybytes)
            except TypeError:
                buffer[0:len(mybytes)] = array("b", mybytes) # mess between py2k and py3k...
        else:
            buffer[0:len(mybytes)] = mybytes
        return len(mybytes)
    '''

    @_win32_error_converter
    def _inner_write(self, buffer):

        if self._append:  # yep, no atomicity around here, as in truncate(), since FILE_APPEND_DATA can't be used
            self._inner_seek(0, defs.SEEK_END)

        cur_pos = self._inner_tell()
        if cur_pos > self._inner_size():
            # we extend the file with zeros until current file pointer position
            self._inner_extend(cur_pos, zero_fill=True)

        (res, bytes_written) = win32.WriteFile(self._handle, buffer)
        # nothing to do with res, for files, it seems

        # we let the file pointer where it is, even if we're in append mode (no come-back to previous reading position)
        return bytes_written

    # no need for @_win32_error_converter
    def _win32_convert_file_range_arguments(self, length, abs_offset):

        if abs_offset is None:
            abs_offset = 0

        if not length:  # 0 or None
            (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh) = (utilities.MAX_DWORD, utilities.MAX_DWORD)
        else:
            (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh) = utilities.pyint_to_double_dwords(length)

        overlapped = win32.OVERLAPPED()  # contains ['Internal', 'InternalHigh', 'Offset', 'OffsetHigh', 'dword',
        # 'hEvent', 'object']
        (overlapped.Offset, overlapped.OffsetHigh) = utilities.pyint_to_double_dwords(abs_offset)
        overlapped.hEvent = 0

        return (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)

    @_win32_error_converter
    def _inner_file_lock(self, length, abs_offset, blocking, shared):

        hfile = self._handle

        # print(">>>>>>> ctypes windows _inner_file_lock", self.name, length, abs_offset, blocking, shared)
        flags = 0 if shared else win32.LOCKFILE_EXCLUSIVE_LOCK
        if not blocking:
            flags |= win32.LOCKFILE_FAIL_IMMEDIATELY

        (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped) = self._win32_convert_file_range_arguments(
            length, abs_offset
        )

        # print(">>>>>>> ctypes windows LockFileEx", hfile, nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh,
        # overlapped.Offset, overlapped.OffsetHigh)
        win32.LockFileEx(hfile, flags, nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)
        # error: 32 - ERROR_SHARING_VIOLATION - The process cannot access the file because it is being used by
        # another process.
        # error: 33 - ERROR_LOCK_VIOLATION - The process cannot access the file because another process has locked a
        # portion of the file.
        # error: 167 - ERROR_LOCK_FAILED - Unable to lock a region of a file.
        # error: 307 - ERROR_INVALID_LOCK_RANGE - A requested file lock operation cannot be processed due to an
        # invalid byte range. -> shouldn't happen due to previous value checks

    @_win32_error_converter
    def _inner_file_unlock(self, length, abs_offset):

        hfile = self._handle

        (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped) = self._win32_convert_file_range_arguments(
            length, abs_offset
        )

        win32.UnlockFileEx(hfile, nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)
        # error: 158 - ERROR_NOT_LOCKED - The segment is already unlocked.
