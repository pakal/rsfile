#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals


import sys
from os import SEEK_SET, SEEK_CUR, SEEK_END


SEEK_VALUES = (SEEK_SET, SEEK_CUR, SEEK_END)

DEFAULT_BUFFER_SIZE = 8 * 1024  # in bytes


# we backup these, just in case
from io import open as original_io_open
from _pyio import open as original_pyio_open


import _pyio as io_module  #TODO remove that, or use C version ,?

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


