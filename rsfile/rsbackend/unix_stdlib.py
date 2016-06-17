# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function


error = (OSError,
         IOError)  
# we expose the types of errors that this backend uses (fcntl uses IOError, unlike os module functions...)

from ctypes import create_string_buffer  # R/W fixed-length buffer
from array import array

import os as _os
from os import (open,
                close,  # not return value
                fstat,
                lseek,
                ftruncate,  # not return value
                write,  # arguments : (fd, string), returns number of bytes written
                fsync,
                read
                )  # directly returns a string

# WARNING - On at least some systems, LOCK_EX can only be used if the file descriptor refers to a file opened for
# writing (RSFile enforces it anyway)


from fcntl import lockf, fcntl  # used both to lock and unlock !


from raw_unix_defines import *  # constants

if hasattr(_os, 'fdatasync'):
    fdatasync = _os.fdatasync
    # else, we just dont't define datasync in the module !


def ltell(fd):
    return lseek(fd, 0, _os.SEEK_CUR)


def readinto(fd, buffer, count):
    # We mimic here the posix read() system call, which works with buffers.

    data = _os.read(fd, count)

    if isinstance(buffer, array):
        try:
            buffer[0:len(data)] = array(b"b", data)
        except TypeError:
            buffer[0:len(data)] = array("b", data)  # mess between py2k and py3k...
    else:
        buffer[0:len(data)] = data

    return len(data)


from os import unlink
