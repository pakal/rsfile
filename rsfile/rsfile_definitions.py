#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals


import sys
from os import SEEK_SET, SEEK_CUR, SEEK_END


SEEK_VALUES = (SEEK_SET, SEEK_CUR, SEEK_END)

DEFAULT_BUFFER_SIZE = 8 * 1024  # in bytes

try:
    memoryview
    HAS_MEMORYVIEW = True
except NameError:
    HAS_MEMORYVIEW = False


if sys.version_info[:2] >= (2,7):
    import _pyio as io_module  # real io module doesn't work atm because buffer reset is not implemented !!! seek() doesn't always reset !!!
else:
    import io # we must patch older io modules (eg py2.6)
    io.SEEK_SET = SEEK_SET
    io.SEEK_CUR = SEEK_CUR
    io.SEEK_END = SEEK_END
    import rsfile.stdlib._pyio as io_module # old stdlib io modules are buggy...

BlockingIOError = io_module.BlockingIOError
UnsupportedOperation = io_module.UnsupportedOperation



class OverFlowException(IOError):
    pass 

class LockingException(IOError):
    pass
class TimeoutException(LockingException):
    pass
class ViolationException(LockingException):
    pass # only raised for mandatory locking
    
    
    
class FileTimes(object):
    def __init__(self, access_time, modification_time):
        self.access_time = access_time
        self.modification_time = modification_time
        