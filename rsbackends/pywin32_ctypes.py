#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals

import sys, os
from rsbackends import _utilities 


import ctypes
import ctypes.wintypes as wintypes

import raw_win32_ctypes as win32api
from raw_win32_ctypes import GetLastError, OVERLAPPED, FILETIME, BY_HANDLE_FILE_INFORMATION, SECURITY_ATTRIBUTES


from raw_win32_defines import * 

# as long as they're supported by the stdlib, let's enjoy these safer version !
from msvcrt import open_osfhandle as _open_osfhandle, get_osfhandle as _get_osfhandle 



INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value # for safety, convert to unsigned DWORD



"""
QUESTION : can we use buffers via array.Array() ? We must NOT change size !!!

YEEEEEEEEEEEEEEEEEEEh
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







### Values extracted from pywin32 modules ###



CREATE_ALWAYS = 0x2
CREATE_FOR_DIR = 0x2
CREATE_FOR_IMPORT = 0x1
CREATE_NEW = 0x1
OPEN_ALWAYS = 0x4
OPEN_EXISTING = 0x3
TRUNCATE_EXISTING = 0x5

FILE_ALL_ACCESS = 0x1f01ff
FILE_ATTRIBUTE_ARCHIVE = 0x20
FILE_ATTRIBUTE_COMPRESSED = 0x800
FILE_ATTRIBUTE_DIRECTORY = 0x10
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_READONLY = 0x1
FILE_ATTRIBUTE_SYSTEM = 0x4
FILE_ATTRIBUTE_TEMPORARY = 0x100

FILE_BEGIN = 0x0
FILE_CURRENT = 0x1
FILE_END = 0x2

FILE_ENCRYPTABLE = 0x0
FILE_IS_ENCRYPTED = 0x1

FILE_FLAG_BACKUP_SEMANTICS = 0x2000000
FILE_FLAG_DELETE_ON_CLOSE = 0x4000000
FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_OPEN_REPARSE_POINT = 0x200000
FILE_FLAG_OVERLAPPED = 0x40000000
FILE_FLAG_POSIX_SEMANTICS = 0x1000000
FILE_FLAG_RANDOM_ACCESS = 0x10000000
FILE_FLAG_SEQUENTIAL_SCAN = 0x8000000
FILE_FLAG_WRITE_THROUGH = 0x80000000

FILE_GENERIC_READ = 0x120089
FILE_GENERIC_WRITE = 0x120116

FILE_READ_ONLY = 0x8
FILE_ROOT_DIR = 0x3
FILE_SHARE_DELETE = 0x4
FILE_SHARE_READ = 0x1
FILE_SHARE_WRITE = 0x2
FILE_SYSTEM_ATTR = 0x2
FILE_SYSTEM_DIR = 0x4
FILE_SYSTEM_NOT_SUPPORT = 0x6
FILE_TYPE_CHAR = 0x2
FILE_TYPE_DISK = 0x1
FILE_TYPE_PIPE = 0x3
FILE_TYPE_UNKNOWN = 0x0
FILE_UNKNOWN = 0x5
FILE_USER_DISALLOWED = 0x7

GENERIC_EXECUTE = 0x20000000
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000

LOCKFILE_FAIL_IMMEDIATELY = 1
LOCKFILE_EXCLUSIVE_LOCK = 2

SECURITY_ANONYMOUS = 0x0
SECURITY_CONTEXT_TRACKING = 0x40000
SECURITY_DELEGATION = 0x30000
SECURITY_EFFECTIVE_ONLY = 0x80000
SECURITY_IDENTIFICATION = 0x10000
SECURITY_IMPERSONATION = 0x20000
"""




# Constant taken from winerror.py module
# ERROR_LOCK_VIOLATION = 33
# Grab othe rerrors !!!!!!!!!


"""
class _inner_struct(ctypes.Structure):
    _fields_ = [('Offset', wintypes.DWORD),
                ('OffsetHigh', wintypes.DWORD), 
               ]

class _inner_union(ctypes.Union):
    _fields_  = [('anon_struct', _inner_struct), # struct
                 ('Pointer', ctypes.c_void_p), # PVOID
                ]

class OVERLAPPED(ctypes.Structure):
    _fields_ = [('Internal', ctypes.c_void_p), # ULONG_PTR
                ('InternalHigh', ctypes.c_void_p), # ULONG_PTR
                ('_inner_union', _inner_union),
                ('hEvent', ctypes.c_void_p), # HANDLE
               ]
               
_LockFileEx = ctypes.windll.kernel32.LockFileEx
_LockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(OVERLAPPED)]
_LockFileEx.restype = wintypes.BOOL

_UnlockFileEx = ctypes.windll.kernel32.UnlockFileEx
_UnlockFileEx.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(OVERLAPPED)] 
_UnlockFileEx.restype = wintypes.BOOL


_SetFilePointerEx = ctypes.windll.kernel32.SetFilePointerEx
_SetFilePointerEx.argtypes = [wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD]
_SetFilePointerEx.restype = wintypes.BOOL        
        
        
_SetEndOfFile = ctypes.windll.kernel32.SetEndOfFile
_SetEndOfFile.argtypes = [wintypes.HANDLE]
_SetEndOfFile.restype = wintypes.BOOL  

    
if os.path.supports_unicode_filenames:
    _CreateFile_function_name = "CreateFileW"
    myLPTSTR = wintypes.LPCWSTR
else:
    _CreateFile_function_name = "CreateFileA"
    class myLPTSTR(wintypes.LPCSTR):
      def __new__(cls, obj):
          if isinstance(obj, unicode) :
            obj = obj.encode("mbcs")
          return wintypes.LPCSTR.__new__(cls, obj)

_CreateFile = ctypes.WINFUNCTYPE(
      wintypes.HANDLE,                # return value !
      myLPTSTR,                # lpFileName
      wintypes.DWORD,                 # dwDesiredAccess
      wintypes.DWORD,                 # dwShareMode
      ctypes.c_void_p,                # lpSecurityAttributes
      wintypes.DWORD,                 # dwCreationDisposition
      wintypes.DWORD,                 # dwFlagsAndAttributes
      wintypes.HANDLE                 # hTemplateFile
  )((_CreateFile_function_name, ctypes.windll.kernel32))

  
_CloseHandle = ctypes.windll.kernel32.CloseHandle
_CloseHandle.argtypes = [wintypes.HANDLE] 
_CloseHandle.restype = wintypes.BOOL  



    USELESS:
    _GetLastError = ctypes.windll.kernel32.GetLastError
    _GetLastError.argtypes = [] 
    _GetLastError.restype = wintypes.BOOL

    Note : If we need an error message :
    
    LPVOID lpMsgBuf;
    DWORD dw = GetLastError(); 
    FormatMessage(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | 
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        dw,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPTSTR) &lpMsgBuf,
        0, NULL );
        
        
ERROR_ACCESS_DENIED = 5
ERROR_SHARING_VIOLATION = 32
    
        
"""        

error = WindowsError # we inform client apps that we may throw THIS exception type
    
  
def CreateFile(fileName, desiredAccess, shareMode, attributes, creationDisposition, flagsAndAttributes, hTemplateFile):    
    
    if isinstance(fileName, unicode):
        CreateFile = win32api.CreateFileW
    else:
        CreateFile = win32api.CreateFileA
        
    handle = CreateFile(fileName, desiredAccess, shareMode, attributes, creationDisposition, flagsAndAttributes, hTemplateFile)
    
    if handle == INVALID_HANDLE_VALUE:
        raise ctypes.WinError()
    
    return handle


def CloseHandle(handle):    

    res = win32api.CloseHandle(handle)
    
    if not res:
        raise ctypes.WinError()       
    

def GetFileInformationByHandle(handle):
    
    info = BY_HANDLE_FILE_INFORMATION()
    
    res = win32api.GetFileInformationByHandle(handle, ctypes.byref(info))
    
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
                
                
        
def SetFilePointer(handle, offset, moveMethod): # we match the naming of pywin32
    
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
    
    
    """
    a = bytearray("12345")
    
    
        print "ywooowhh"
        # NOT WORKING : from_buffer(a) -> WindowsError: [Error 1784]
    else:
        data_to_write = data # casting will be implicit
    """
    
    """
    if isinstance(data, memoryview):
        data_to_write = ctypes.create_string_buffer(len(data))
        data_to_write.raw = data                                          
        #address = ctypes.c_void_p(data.raw)
    else:
    """
    if isinstance(data, bytearray):
        data_to_write = ctypes.POINTER(ctypes.c_char).from_buffer(data) # NOT WORKING - TODO - WARNING
    else:
        #data_to_write = ctypes.c_char_p(data)  # doesn't work...
        data_to_write = ctypes.create_string_buffer(data)

    address =  ctypes.addressof(data_to_write)
        
    bytes_written = wintypes.DWORD(0)
   
    # no need to use WriteFileEx here...
    res = win32api.WriteFile(handle,
                          address,
                          len(data),
                          ctypes.byref(bytes_written),
                          overlapped)

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
    # TODO - improve to work directly with ctypes array types !
    
    assert overlapped or isinstance(buffer_or_int, int) # buffers can only be provided in overlapped mode
    
    if isinstance(buffer_or_int, bytearray):
        bytes_to_read = len(buffer_or_int)
        target_buffer = ctypes.c_void_p.from_buffer(buffer_or_int)
    else:
        bytes_to_read = int(buffer_or_int)
        target_buffer = ctypes.create_string_buffer(bytes_to_read) # casting will be implicit
    
    bytes_read = wintypes.DWORD(0)
    
    # no need to use WriteFileEx here...
    res = win32api.ReadFile(handle,
                          target_buffer,
                          bytes_to_read,
                          ctypes.byref(bytes_read),
                          overlapped)

    if not res:
        err = ctypes.GetLastError()
        if err not in (ERROR_IO_PENDING, ERROR_MORE_DATA):
            raise ctypes.WinError(err) 
    else:
        err = 0
    
    
        
    if overlapped :
        return (err, buffer(target_buffer))
    else:
        res = target_buffer.raw[0:bytes_read.value]
        return (err, res)               
                          


def LockFileEx(handle, dwFlags, nbytesLow, nbytesHigh, overlapped):

    result = win32api.LockFileEx(handle, # HANDLE hFile
                                 dwFlags,   # DWORD dwFlags
                                 0,          # DWORD dwReserved
                                 nbytesLow, # DWORD nNumberOfBytesToLockLow
                                 nbytesHigh, # DWORD nNumberOfBytesToLockHigh
                                 ctypes.byref(overlapped) if overlapped else None, # lpOverlapped
                                 )           
    if not result:
        raise ctypes.WinError() # can take an error code as argument, else uses GetLastError()
        
        
        
def UnlockFileEx(handle, nbytesLow, nbytesHigh, overlapped):
 
    result = win32api.UnlockFileEx(handle, # HANDLE hFile
                                     0,          # DWORD dwReserved
                                     nbytesLow, # DWORD nNumberOfBytesToLockLow
                                     nbytesHigh, # DWORD nNumberOfBytesToLockHigh
                                     ctypes.byref(overlapped) if overlapped else None, # lpOverlapped
                                     )              
    if not result:
        raise ctypes.WinError()
        
    

        

        

if (__name__ == "__main__"):


    try:
        handle = CreateFile("", GENERIC_READ | GENERIC_WRITE, FILE_SHARE_WRITE, None, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0)
    except:
        pass
    else:
        raise RuntimeError(str(INVALID_HANDLE_VALUE)+" - "+str(handle))
    
        
    fd = open("@TESTFN", "w")
    fd.write("abcdefghijk")
    fd.close()
    
    filename = "@TESTFN"
    
    handle = CreateFile(filename, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_WRITE, None, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0)

    string = "hello"
    

    f = bytearray("hello")

    res = WriteFile(handle, f)
    print ("WRITEFILE : ", res)
    assert 0 <= res[1] <= 5
    
    
    """ 
    h = memoryview(string)
    
    res = WriteFile(handle, h)
    print "WRITEFILE : ", res
    assert 0 <= res[1] <= 5
    """
    
    
    res = SetFilePointer(handle, 10, FILE_BEGIN)

    assert res == 10
    
    SetEndOfFile(handle)

    res = GetFileSize(handle)
    assert res == 10
    
    LockFileEx(handle, LOCKFILE_EXCLUSIVE_LOCK, 0xffffffff, 0xffffffff, OVERLAPPED())
    
    
    UnlockFileEx(handle, 0xffffffff, 0xffffffff, OVERLAPPED())

    assert GetFileInformationByHandle(handle)
    

    res =  WriteFile(handle, bytes("abc"))
    assert res == (0, 3)
    
   #assert WriteFile(handle, bytearray("abc")) == (0, 3)
    
    SetFilePointer(handle, -3, FILE_CURRENT)

    assert ReadFile(handle, 3) == (0, b"abc")
    # we shall test overlapped behaviour too...
       
    CloseHandle(handle)
    
    print ("OVER !")

    #fd = open("AAAAA", "w")
    #handle = msvcrt.get_osfhandle(fd.fileno())
    #msvcrt.open_osfhandle(handle, cflags)
    #fd.close()







