#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys
from os import SEEK_SET, SEEK_CUR, SEEK_END


SEEK_VALUES = (SEEK_SET, SEEK_CUR, SEEK_END)

DEFAULT_BUFFER_SIZE = 8 * 1024  # in bytes


# we backup these, just in case
from io import open as original_io_open
from _pyio import open as original_pyio_open


STDLIB_OPEN_FLAGS = set("xarw+btU")
ADVANCED_OPEN_FLAGS = set("RAW+-CNSIEBT")  # + and - are only left for retrocompatibility


# beware, using C-backed IO doesn't work ATM because of class layout conflicts
import _pyio as io_module

BlockingIOError = io_module.BlockingIOError
UnsupportedOperation = io_module.UnsupportedOperation


class BadValueTypeError(ValueError, TypeError):
    pass  # class to handle differences


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


