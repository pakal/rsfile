#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals


import win32con, win32api, win32file, pywintypes

from win32con import *
from win32api import *
from win32file import *

from pywintypes import *

# USE THESE ONES ! They're safe concerning bad file descriptors !
from msvcrt import open_osfhandle as _open_osfhandle, get_osfhandle as _get_osfhandle 



from rsbackends import _utilities 

# we override buggy pywin32 functions


def SetEndOfFile(handle):    

    res = win32file.SetEndOfFile(handle)
    
    if not res:
        raise pywintypes.error(win32api.GetLastError(), "SetEndOfFile")
    """
    TODO : use a REAL error message !!!
    --->
    PyObject *PyWin_SetAPIError(char *fnName, long err /*= 0*/)
    {
    DWORD errorCode = err == 0 ? GetLastError() : err;
    DWORD flags = FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_ALLOCATE_BUFFER | \
                  FORMAT_MESSAGE_IGNORE_INSERTS;
    // try and find the hmodule providing this error.
    HMODULE hmodule = PyWin_GetErrorMessageModule(errorCode);
    if (hmodule)
        flags |= FORMAT_MESSAGE_FROM_HMODULE;
    TCHAR *buf = NULL;
    BOOL free_buf = TRUE;
    if (errorCode)
        ::FormatMessage(flags, hmodule, errorCode, 0, (LPTSTR)&buf, 0, NULL );
    if (!buf) {
        buf = _T("No error message is available");
        free_buf = FALSE;
    
    """


class BY_HANDLE_FILE_INFORMATION(object):
    pass
from ctypes.wintypes import FILETIME


def GetFileInformationByHandle(handle):
    """ pywin32 FILETIME structure is buggy !"""
    
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
    
    mystat = os.fstat(_open_osfhandle(handle, 0))
    info.ftCreationTime = FILETIME(*_utilities.python_timestamp_to_win32_filetime(mystat.st_ctime))
    info.ftLastAccessTime = FILETIME(*_utilities.python_timestamp_to_win32_filetime(mystat.st_atime))
    info.ftLastWriteTime = FILETIME(*_utilities.python_timestamp_to_win32_filetime(mystat.st_mtime))
    
    return info


def LockFileEx(handle, dwFlags, nbytesLow, nbytesHigh, overlapped):

    # warning - pywin32 expects dwords as signed integer, so that -1 <-> max_int
    nbytesLow = _utilities.unsigned_to_signed(nbytesLow)
    nbytesHigh = _utilities.unsigned_to_signed(nbytesHigh)
    
    result = win32file.LockFileEx(handle, # HANDLE hFile
                                     dwFlags,   # DWORD dwFlags
                                     nbytesLow, # DWORD nNumberOfBytesToLockLow
                                     nbytesHigh, # DWORD nNumberOfBytesToLockHigh
                                     overlapped # lpOverlapped
                                    )           

        
def UnlockFileEx(handle, nbytesLow, nbytesHigh, overlapped):

    # warning - pywin32 expects dwords as signed integer, so that -1 <-> max_int
    nbytesLow = _utilities.unsigned_to_signed(nbytesLow)
    nbytesHigh = _utilities.unsigned_to_signed(nbytesHigh)   

    result = win32file.UnlockFileEx(handle, # HANDLE hFile
                                     nbytesLow, # DWORD nNumberOfBytesToLockLow
                                     nbytesHigh, # DWORD nNumberOfBytesToLockHigh
                                     overlapped # lpOverlapped
                                     )              
