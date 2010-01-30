#-*- coding: utf-8 -*-

from os import SEEK_SET, SEEK_CUR, SEEK_END

DEFAULT_BUFFER_SIZE = 8 * 1024  # bytes


LOCK_ALWAYS = 2
LOCK_AUTO = 1
LOCK_NEVER = 0


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




# ######### DEFAULT PARAMETERS ######## #

_default_safety_options = {
    "unified_locking_behaviour": True, # TODO ???
    "default_locking_timeout": None, # all locking attempts which have no timeout set will actually fail after this time (prevents denial of service)
    "default_locking_exception": IOError, # exception raised when an enforced timeout occurs (helps detecting deadlocks)
    "max_input_load_bytes": None,  # makes readall() and other greedy operations to fail when the data gotten exceeds this size (prevents memory overflow)
    "default_spinlock_delay": 0.1 # how many seconds the program must sleep between attempts at locking a file
    }

_locked_chunks_registry = {} # for unified_locking_behaviour ?? # keys are absolute file paths, values are lists of inodes identified by their uuid, and each inode has a list of (slice_start, slice_end or None) tuples - "None" meaning "until infinity"


def get_default_safety_options():
    return _default_safety_options.copy()

def set_default_safety_options(**options):
    new_options = set(options.keys())
    all_options = set(_default_safety_options.keys())
    if not new_options <= all_options:
        raise ValueError("Unknown safety option : "+", ".join(list(new_options - all_options)))
    _default_safety_options.update(options)

############################################
        