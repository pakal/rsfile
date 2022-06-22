# -*- coding: utf-8 -*-


import sys, os

import win32con, win32api, win32file, pywintypes

from pywintypes import OVERLAPPED, SECURITY_ATTRIBUTES

from win32file import (FILE_BEGIN, FILE_CURRENT, FILE_END, CreateFile, CloseHandle, FlushFileBuffers,
                       GetFileInformationByHandle, LockFileEx, UnlockFileEx,
                       GetFileSize, SetFilePointer, WriteFile, ReadFile, SetEndOfFile,
                       GENERIC_READ, GENERIC_WRITE, FILE_SHARE_READ, FILE_SHARE_WRITE, FILE_SHARE_DELETE,
                       OPEN_EXISTING, OPEN_ALWAYS, CREATE_NEW, FILE_ATTRIBUTE_READONLY,
                       FILE_ATTRIBUTE_NORMAL)
from win32con import (LOCKFILE_EXCLUSIVE_LOCK, LOCKFILE_FAIL_IMMEDIATELY, FILE_FLAG_WRITE_THROUGH)
from win32api import error

# USE THESE ONES ! They're safe concerning bad file descriptors !
from msvcrt import open_osfhandle as _open_osfhandle, get_osfhandle as _get_osfhandle

from .raw_win32_defines import ERROR_NOT_SUPPORTED

from rsfile.rsbackend import _utilities


# we override buggy pywin32 functions


def SetEndOfFile(handle):
    res = win32file.SetEndOfFile(handle)

    if not res:
        raise pywintypes.error(win32api.GetLastError(), "SetEndOfFile")
    #TODO : use a REAL error message !!!



class BY_HANDLE_FILE_INFORMATION(object):
    pass


from ctypes.wintypes import FILETIME


def GetFileInformationByHandle(handle):
    """
    Note that pywin32 FILETIME structure is buggy,
    and here nFileSizeHigh/nFileSizeLow return 0 on FAT32
    whereas on ctypes backend they have a proper value.
    """

    info = BY_HANDLE_FILE_INFORMATION()

    (info.dwFileAttributes,
     _ftCreationTime,
     _ftLastAccessTime,
     _ftLastWriteTime,
     info.dwVolumeSerialNumber,
     info.nFileSizeHigh,
     info.nFileSizeLow,
     info.nNumberOfLinks,
     info.nFileIndexHigh,
     info.nFileIndexLow) = win32file.GetFileInformationByHandle(handle)

    ##print(">>>>>>", info.__dict__)

    # to workaround bugs, we don't deal with "PyTime" objects, we fallback to stdlib...
    mystat = os.fstat(_open_osfhandle(handle, 0))
    info.ftCreationTime = FILETIME(*_utilities.python_timestamp_to_win32_filetime(mystat.st_ctime))
    info.ftLastAccessTime = FILETIME(*_utilities.python_timestamp_to_win32_filetime(mystat.st_atime))
    info.ftLastWriteTime = FILETIME(*_utilities.python_timestamp_to_win32_filetime(mystat.st_mtime))

    return info


def LockFileEx(handle, dwFlags, nbytesLow, nbytesHigh, overlapped):
    # warning - pywin32 expects dwords as signed integer, so that -1 <-> max_int
    nbytesLow = _utilities.unsigned_to_signed(nbytesLow)
    nbytesHigh = _utilities.unsigned_to_signed(nbytesHigh)

    result = win32file.LockFileEx(handle,  # HANDLE hFile
                                  dwFlags,  # DWORD dwFlags
                                  nbytesLow,  # DWORD nNumberOfBytesToLockLow
                                  nbytesHigh,  # DWORD nNumberOfBytesToLockHigh
                                  overlapped  # lpOverlapped
                                  )


def UnlockFileEx(handle, nbytesLow, nbytesHigh, overlapped):
    # warning - pywin32 expects dwords as signed integer, so that -1 <-> max_int
    nbytesLow = _utilities.unsigned_to_signed(nbytesLow)
    nbytesHigh = _utilities.unsigned_to_signed(nbytesHigh)

    result = win32file.UnlockFileEx(handle,  # HANDLE hFile
                                    nbytesLow,  # DWORD nNumberOfBytesToLockLow
                                    nbytesHigh,  # DWORD nNumberOfBytesToLockHigh
                                    overlapped  # lpOverlapped
                                    )
