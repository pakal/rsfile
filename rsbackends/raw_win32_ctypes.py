from ctypes import *

from ctypes.wintypes import DWORD
_stdcall_libraries = {}
_stdcall_libraries['kernel32'] = WinDLL('kernel32')
from ctypes.wintypes import BOOL
from ctypes.wintypes import HANDLE
from ctypes.wintypes import LARGE_INTEGER
from ctypes.wintypes import LPCVOID
from ctypes.wintypes import LPVOID
from ctypes.wintypes import LONG
from ctypes.wintypes import LPCSTR
from ctypes.wintypes import LPCWSTR
_libraries = {}
_libraries['msvcrt'] = CDLL('msvcrt')
from ctypes.wintypes import _FILETIME
from ctypes.wintypes import FILETIME


class _OVERLAPPED(Structure):
    pass
OVERLAPPED = _OVERLAPPED
class _SECURITY_ATTRIBUTES(Structure):
    pass
SECURITY_ATTRIBUTES = _SECURITY_ATTRIBUTES
GetLastError = _stdcall_libraries['kernel32'].GetLastError
GetLastError.restype = DWORD
GetLastError.argtypes = []
LPOVERLAPPED = POINTER(_OVERLAPPED)
LockFileEx = _stdcall_libraries['kernel32'].LockFileEx
LockFileEx.restype = BOOL
LockFileEx.argtypes = [HANDLE, DWORD, DWORD, DWORD, DWORD, LPOVERLAPPED]
UnlockFileEx = _stdcall_libraries['kernel32'].UnlockFileEx
UnlockFileEx.restype = BOOL
UnlockFileEx.argtypes = [HANDLE, DWORD, DWORD, DWORD, LPOVERLAPPED]
class _BY_HANDLE_FILE_INFORMATION(Structure):
    pass
BY_HANDLE_FILE_INFORMATION = _BY_HANDLE_FILE_INFORMATION
LPBY_HANDLE_FILE_INFORMATION = POINTER(_BY_HANDLE_FILE_INFORMATION)
GetFileInformationByHandle = _stdcall_libraries['kernel32'].GetFileInformationByHandle
GetFileInformationByHandle.restype = BOOL
GetFileInformationByHandle.argtypes = [HANDLE, LPBY_HANDLE_FILE_INFORMATION]
LPDWORD = POINTER(DWORD)
GetFileSize = _stdcall_libraries['kernel32'].GetFileSize
GetFileSize.restype = DWORD
GetFileSize.argtypes = [HANDLE, LPDWORD]
PLARGE_INTEGER = POINTER(LARGE_INTEGER)
GetFileSizeEx = _stdcall_libraries['kernel32'].GetFileSizeEx
GetFileSizeEx.restype = BOOL
GetFileSizeEx.argtypes = [HANDLE, PLARGE_INTEGER]
WriteFile = _stdcall_libraries['kernel32'].WriteFile
WriteFile.restype = BOOL
WriteFile.argtypes = [HANDLE, LPCVOID, DWORD, LPDWORD, LPOVERLAPPED]
ReadFile = _stdcall_libraries['kernel32'].ReadFile
ReadFile.restype = BOOL
ReadFile.argtypes = [HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED]
FlushFileBuffers = _stdcall_libraries['kernel32'].FlushFileBuffers
FlushFileBuffers.restype = BOOL
FlushFileBuffers.argtypes = [HANDLE]
SetEndOfFile = _stdcall_libraries['kernel32'].SetEndOfFile
SetEndOfFile.restype = BOOL
SetEndOfFile.argtypes = [HANDLE]
PLONG = POINTER(LONG)
SetFilePointer = _stdcall_libraries['kernel32'].SetFilePointer
SetFilePointer.restype = DWORD
SetFilePointer.argtypes = [HANDLE, LONG, PLONG, DWORD]
SetFilePointerEx = _stdcall_libraries['kernel32'].SetFilePointerEx
SetFilePointerEx.restype = BOOL
SetFilePointerEx.argtypes = [HANDLE, LARGE_INTEGER, PLARGE_INTEGER, DWORD]
CloseHandle = _stdcall_libraries['kernel32'].CloseHandle
CloseHandle.restype = BOOL
CloseHandle.argtypes = [HANDLE]
LPOVERLAPPED_COMPLETION_ROUTINE = WINFUNCTYPE(None, DWORD, DWORD, LPOVERLAPPED)
ReadFileEx = _stdcall_libraries['kernel32'].ReadFileEx
ReadFileEx.restype = BOOL
ReadFileEx.argtypes = [HANDLE, LPVOID, DWORD, LPOVERLAPPED, LPOVERLAPPED_COMPLETION_ROUTINE]
WriteFileEx = _stdcall_libraries['kernel32'].WriteFileEx
WriteFileEx.restype = BOOL
WriteFileEx.argtypes = [HANDLE, LPCVOID, DWORD, LPOVERLAPPED, LPOVERLAPPED_COMPLETION_ROUTINE]
LPSECURITY_ATTRIBUTES = POINTER(_SECURITY_ATTRIBUTES)
CreateFileA = _stdcall_libraries['kernel32'].CreateFileA
CreateFileA.restype = HANDLE
CreateFileA.argtypes = [LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE]
CreateFileW = _stdcall_libraries['kernel32'].CreateFileW
CreateFileW.restype = HANDLE
CreateFileW.argtypes = [LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE]
intptr_t = c_int
_get_osfhandle = _libraries['msvcrt']._get_osfhandle
_get_osfhandle.restype = intptr_t
_get_osfhandle.argtypes = [c_int]
_open_osfhandle = _libraries['msvcrt']._open_osfhandle
_open_osfhandle.restype = c_int
_open_osfhandle.argtypes = [intptr_t, c_int]
ULONG_PTR = c_ulong
class N11_OVERLAPPED4DOLLAR_81E(Union):
    pass
class N11_OVERLAPPED4DOLLAR_814DOLLAR_82E(Structure):
    pass
N11_OVERLAPPED4DOLLAR_814DOLLAR_82E._fields_ = [
    ('Offset', DWORD),
    ('OffsetHigh', DWORD),
]
PVOID = c_void_p
N11_OVERLAPPED4DOLLAR_81E._anonymous_ = ['_0']
N11_OVERLAPPED4DOLLAR_81E._fields_ = [
    ('_0', N11_OVERLAPPED4DOLLAR_814DOLLAR_82E),
    ('Pointer', PVOID),
]
_OVERLAPPED._anonymous_ = ['_0']
_OVERLAPPED._fields_ = [
    ('Internal', ULONG_PTR),
    ('InternalHigh', ULONG_PTR),
    ('_0', N11_OVERLAPPED4DOLLAR_81E),
    ('hEvent', HANDLE),
]
_SECURITY_ATTRIBUTES._fields_ = [
    ('nLength', DWORD),
    ('lpSecurityDescriptor', LPVOID),
    ('bInheritHandle', BOOL),
]
_BY_HANDLE_FILE_INFORMATION._fields_ = [
    ('dwFileAttributes', DWORD),
    ('ftCreationTime', FILETIME),
    ('ftLastAccessTime', FILETIME),
    ('ftLastWriteTime', FILETIME),
    ('dwVolumeSerialNumber', DWORD),
    ('nFileSizeHigh', DWORD),
    ('nFileSizeLow', DWORD),
    ('nNumberOfLinks', DWORD),
    ('nFileIndexHigh', DWORD),
    ('nFileIndexLow', DWORD),
]
__all__ = ['GetLastError', '_BY_HANDLE_FILE_INFORMATION',
           '_open_osfhandle', 'FlushFileBuffers',
           'LPOVERLAPPED_COMPLETION_ROUTINE', 'ULONG_PTR',
           '_get_osfhandle', '_SECURITY_ATTRIBUTES',
           'LPBY_HANDLE_FILE_INFORMATION', 'GetFileSize',
           'LPOVERLAPPED', 'SECURITY_ATTRIBUTES',
           'LPSECURITY_ATTRIBUTES', 'SetFilePointerEx',
           'GetFileInformationByHandle', 'PLARGE_INTEGER',
           'N11_OVERLAPPED4DOLLAR_81E', 'intptr_t', 'LockFileEx',
           'GetFileSizeEx', 'SetFilePointer', 'ReadFile',
           'WriteFileEx', '_OVERLAPPED', 'WriteFile', 'CloseHandle',
           'UnlockFileEx', 'OVERLAPPED',
           'N11_OVERLAPPED4DOLLAR_814DOLLAR_82E', 'CreateFileW',
           'LPDWORD', 'BY_HANDLE_FILE_INFORMATION', 'SetEndOfFile',
           'ReadFileEx', 'CreateFileA', 'PVOID', 'PLONG']
