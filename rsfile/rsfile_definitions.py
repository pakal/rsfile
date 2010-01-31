#-*- coding: utf-8 -*-

from os import SEEK_SET, SEEK_CUR, SEEK_END

DEFAULT_BUFFER_SIZE = 8 * 1024  # bytes



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
        