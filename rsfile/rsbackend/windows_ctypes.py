# -*- coding: utf-8 -*-


import sys, os
from rsfile.rsbackend import _utilities
from array import array

import ctypes
import ctypes.wintypes as wintypes

from . import raw_win32_ctypes as win32api
from .raw_win32_ctypes import GetLastError, OVERLAPPED, FILETIME, BY_HANDLE_FILE_INFORMATION, SECURITY_ATTRIBUTES

from .raw_win32_defines import (
    ERROR_IO_PENDING,
    ERROR_MORE_DATA,
    ERROR_NOT_SUPPORTED,
    GENERIC_READ,
    GENERIC_WRITE,
    FILE_SHARE_WRITE,
    OPEN_ALWAYS,
    FILE_ATTRIBUTE_NORMAL,
    FILE_BEGIN,
    LOCKFILE_EXCLUSIVE_LOCK,
    FILE_SHARE_READ,
    OPEN_EXISTING,
    CREATE_NEW,
    FILE_CURRENT,
    FILE_ATTRIBUTE_READONLY,
    FILE_ATTRIBUTE_NORMAL,
    FILE_FLAG_WRITE_THROUGH,
    FILE_END,
    FILE_SHARE_DELETE,
    LOCKFILE_FAIL_IMMEDIATELY,
)

# as long as they're supported by the stdlib, let's enjoy these safer version !
from msvcrt import open_osfhandle as _open_osfhandle, get_osfhandle as _get_osfhandle

INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value  # for safety, convert to unsigned DWORD

"""
QUESTION : can we use buffers via array.Array() ? We must NOT change size !!!

IDLE 2.6.4      
>>> import ctypes
>>> a ctypes.create_string_buffer(10)
SyntaxError: invalid syntax
>>> a = ctypes.create_string_buffer(10)
>>> a
<ctypes.c_char_Array_10 object at 0x02728350>
>>> a[:]
'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
>>> a = bytearray(3)
>>> a
bytearray(b'\x00\x00\x00')
>>> b = ctypes.create_string_buffer(10)
>>> mytype = ctypes.c_char * 10
>>> mytype = ctypes.c_char * 3
>>> h = mytype.from_buffer(a)
>>> h
<__main__.c_char_Array_3 object at 0x02B06350>
>>> h[:] = "abc"
>>> a
bytearray(b'abc')
>>> h[0] = "k"
>>> a
bytearray(b'kbc')
>>>
"""

error = WindowsError  # we inform client apps that we may throw THIS exception type


def CreateFile(fileName, desiredAccess, shareMode, attributes, creationDisposition, flagsAndAttributes, hTemplateFile):
    if isinstance(fileName, str):
        CreateFile = win32api.CreateFileW
    else:
        CreateFile = win32api.CreateFileA

    handle = CreateFile(
        fileName, desiredAccess, shareMode, attributes, creationDisposition, flagsAndAttributes, hTemplateFile
    )

    if handle == INVALID_HANDLE_VALUE:
        raise ctypes.WinError()

    return handle


def CloseHandle(handle):
    res = win32api.CloseHandle(handle)

    if not res:
        raise ctypes.WinError()


def GetFileInformationByHandle(handle):
    info = BY_HANDLE_FILE_INFORMATION()

    res = win32api.GetFileInformationByHandle(handle, ctypes.byref(info))  # side effects

    if not res:
        raise ctypes.WinError()

    return info
    """
    (info.dwFileAttributes,
    info.ftCreationTime,
    info.ftLastAccessTime,
    info.ftLastWriteTime,
    info.dwVolumeSerialNumber,
    info.nFileSizeHigh,
    info.nFileSizeLow,
    info.nNumberOfLinks,
    info.nFileIndexHigh,
    info.nFileIndexLow)
    """


def GetFileSize(handle):
    size = wintypes.LARGE_INTEGER(0)

    res = win32api.GetFileSizeEx(handle, ctypes.byref(size))

    if not res:
        raise ctypes.WinError()

    return size.value


""" Useless non-extended version of GetFileSize...

def GetFileSize(handle): 
    
    size = wintypes.DWORD(0)
    res = win32api.GetFileSize(handle, None)
    #print "res is %d != %d" % (res, 0xffffffff)
    #print type(res), type(0xffffffff)
    if res == 0xffffffff:
        # NO - here first check that we don't have NOERROR(0) in GetLastError...
        # raise ctypes.WinError() 
    return res          
"""


def SetFilePointer(handle, offset, moveMethod):  # we match the naming of pywin32

    newPos = wintypes.LARGE_INTEGER(5)

    res = win32api.SetFilePointerEx(handle, offset, ctypes.byref(newPos), moveMethod)

    if not res:
        raise ctypes.WinError()

    return newPos.value


def SetEndOfFile(handle):
    res = win32api.SetEndOfFile(handle)

    if not res:
        raise ctypes.WinError()


def WriteFile(handle, data, overlapped=None):
    """
    data can be a buffer (no copy takes place) or an immutable sequence of bytes (a copy occurs).
    """

    if isinstance(data, bytearray):
        # data_to_write = ctypes.addressof(ctypes.POINTER(ctypes.c_char).from_buffer(data)) # erroneous
        data_to_write = ctypes.create_string_buffer(bytes(data))
    else:  # bytes
        # data_to_write = ctypes.c_char_p(data) # doesn't work, buffer size too small problems...
        data_to_write = ctypes.create_string_buffer(data)

    """ Not required ATM:
    elif isinstance(data, memoryview):
        data_to_write = ctypes.c_char_p(data.tobytes()) 
    elif isinstance(data, array):
        data_to_write = ctypes.POINTER(ctypes.c_char).from_buffer_copy(data)
        # TO BE COMPARED WITH - ctypes.c_char_p(data.tostring()) 
    """

    address = data_to_write  # ctypes.addressof(data_to_write)

    bytes_written = wintypes.DWORD(0)

    # no need to use WriteFileEx here...
    res = win32api.WriteFile(handle, address, len(data), ctypes.byref(bytes_written), overlapped)

    if not res:
        err = ctypes.GetLastError()
        if err != ERROR_IO_PENDING:
            raise ctypes.WinError(err)
    else:
        err = 0

    return (err, bytes_written.value)


def FlushFileBuffers(handle):
    res = win32api.FlushFileBuffers(handle)

    if not res:
        raise ctypes.WinError()


def ReadFile(handle, buffer_or_int, overlapped=None):
    # TODO - optimize to work directly with ctypes array types, and to avoid copies for readinto() ?

    if isinstance(buffer_or_int, int):
        bytes_to_read = buffer_or_int
        target_buffer = ctypes.create_string_buffer(bytes_to_read)
    else:
        bytes_to_read = len(buffer_or_int)

        if isinstance(buffer_or_int, bytearray):
            target_buffer = ctypes.c_void_p.from_buffer(buffer_or_int)
            # target_buffer = ctypes.POINTER(ctypes.c_char).from_buffer(buffer_or_int)
        elif isinstance(buffer_or_int, array):
            target_buffer = ctypes.c_void_p.from_buffer(buffer_or_int)
        else:
            raise TypeError("Unsupported target buffer %r" % buffer_or_int)

    bytes_read = wintypes.DWORD(0)

    address = ctypes.addressof(target_buffer)

    # print (locals())
    # no need to use ReadFileEx here...
    res = win32api.ReadFile(handle, address, bytes_to_read, ctypes.byref(bytes_read), overlapped)

    if not res:
        err = ctypes.GetLastError()
        if err not in (ERROR_IO_PENDING, ERROR_MORE_DATA):
            raise ctypes.WinError(err)
    else:
        err = 0

    if overlapped:
        return (err, bytearray(target_buffer))  # untested feature
    elif isinstance(buffer_or_int, int):
        return (err, target_buffer.raw[0 : bytes_read.value])
    else:
        return (err, buffer_or_int[0 : bytes_read.value])


def LockFileEx(handle, dwFlags, nbytesLow, nbytesHigh, overlapped):
    result = win32api.LockFileEx(
        handle,  # HANDLE hFile
        dwFlags,  # DWORD dwFlags
        0,  # DWORD dwReserved
        nbytesLow,  # DWORD nNumberOfBytesToLockLow
        nbytesHigh,  # DWORD nNumberOfBytesToLockHigh
        ctypes.byref(overlapped) if overlapped else None,  # lpOverlapped
    )
    if not result:
        raise ctypes.WinError()  # can take an error code as argument, else uses GetLastError()


def UnlockFileEx(handle, nbytesLow, nbytesHigh, overlapped):
    result = win32api.UnlockFileEx(
        handle,  # HANDLE hFile
        0,  # DWORD dwReserved
        nbytesLow,  # DWORD nNumberOfBytesToLockLow
        nbytesHigh,  # DWORD nNumberOfBytesToLockHigh
        ctypes.byref(overlapped) if overlapped else None,  # lpOverlapped
    )
    if not result:
        raise ctypes.WinError()


if __name__ == "__main__":

    try:
        handle = CreateFile(
            "", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_WRITE, None, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0
        )
    except:
        pass
    else:
        raise RuntimeError(str(INVALID_HANDLE_VALUE) + " - " + str(handle))

    fd = open("@TESTFN", "w")
    fd.write("abcdefghijk")
    fd.close()

    filename = "@TESTFN"

    handle = CreateFile(
        filename, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_WRITE, None, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0
    )

    string = "hello"

    f = bytearray("helloeveryone", "ascii")
    res = WriteFile(handle, f)
    print("WRITE BYTEARRAY: ", res)
    assert 0 <= res[1] <= len("helloeveryone")

    string = b"hheyo"
    res = WriteFile(handle, string)
    print("WRITE BYTES : ", res)
    assert 0 <= res[1] <= 5

    g = array(b"b", b"vvvvv")
    res = WriteFile(handle, g)
    print("WRITE ARRAY : ", res)
    assert 0 <= res[1] <= 5

    h = memoryview(string)
    res = WriteFile(handle, h)
    print("WRITE MEMORYVIEW : ", res)
    assert 0 <= res[1] <= 5

    res = SetFilePointer(handle, 10, FILE_BEGIN)

    assert res == 10

    SetEndOfFile(handle)

    res = GetFileSize(handle)
    assert res == 10

    LockFileEx(handle, LOCKFILE_EXCLUSIVE_LOCK, 0xFFFFFFFF, 0xFFFFFFFF, OVERLAPPED())

    UnlockFileEx(handle, 0xFFFFFFFF, 0xFFFFFFFF, OVERLAPPED())

    assert GetFileInformationByHandle(handle)

    SetFilePointer(handle, 0, FILE_BEGIN)

    res = ReadFile(handle, 3)
    print("Read number", repr(res[1]))

    f = bytearray("hello", "ascii")
    res = ReadFile(handle, f)
    print("Readinto bytearray", repr(res[1]))

    g = array(b"b", b"vvvvv")
    res = ReadFile(handle, g)
    print("Readinto array", repr(res[1]))

    """
    h = memoryview(string)
    res = ReadFile(handle, h) 
    print("Readinto memoryview", res) 
    """

    # we shall test overlapped behaviour too...

    CloseHandle(handle)

    print("OVER !")

    # fd = open("AAAAA", "w")
    # handle = msvcrt.get_osfhandle(fd.fileno())
    # msvcrt.open_osfhandle(handle, cflags)
    # fd.close()
