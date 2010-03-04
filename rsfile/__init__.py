#-*- coding: utf-8 -*-

from __future__ import with_statement

import sys, os
import functools
import io

from rsfileio_abstract import RSFileIOAbstract

from rsfile_definitions import * # constants, base types and exceptions
from rsfile_streams import *
from rsfile_factories import *
from rsfile_registries import set_rsfile_options, get_rsfile_options
from rsfile_utilities import *


# # # TODO list # # #

"""

TODO : test if this is true, or if only dup2() descriptors have this effect :
Locks are associated with processes. A process can only have one kind of lock set for each byte of a given file. 
When any file descriptor for that file is closed by the process, all of the locks that process holds on that file 
are released, even if the locks were made using other descriptors that remain open. Likewise, locks are released when 
a process exits, and are not inherited by child processes created using fork (see Creating a Process). 
"""
# WARNING - shall we not modify close() of buffered streams to let exceptions propagate !!

# A inclure dans la doc : atomic operations = bad idea... delete on close too..

#TODO py2.7 the file object will now set the filename attribute on the IOError exception when trying to open a directory on POSIX platforms. (Noted by Jan Kaliszewski; issue 4764.)
#TODO - The io.FileIO class now raises an OSError when passed an invalid file descriptor. (Implemented by Benjamin Peterson; issue 4991.)
#---> valueerror on negative FD, and oserror on fstat-EBADF

# TODO - warn in doc about the fact that writing on read-locked portion by current process fails on win32, NOT unix

# Todo : check that current buffer class work well when seeking (pos, seek_cur) ! (buggy in 2.6.1)
# -> Could you construct a test case? (it's even better if you fix the offending code as well of course)

# exception io.UnsupportedOperation - An exception inheriting IOError and ValueError that is raised when an unsupported operation is called on a stream.

# Todo : in doc : tell that errors are left explicit when closing streams, eg. if flush fails !!!! (buggy in current io)

# Todo - discuss the use of name, mode, closefd etc. as attributes of raw streams only ????

# Todo - advocate thread-safe interface, globalized check_closed() checking, and public interface only win32 error converter !!! @_win32_error_converter not on private methods !!
## exception BlockingIOError - to implement

# file handle duplication or inheritance: warn about the file pointer sensitivity, which may cause big troubles if you don't lock files !!! 
#-> use interprocess mutex ! patch atfork()


# poursuiver discussion bug - multiprocessing module ne met pas en garde contre multithreading et thread-safety des synchronization primitives !
# TODO - discuss threads in multiprocessing when forking - why not spawn like win32 ??

"""
EN FAIT, DANS WINDOWS AUSSI LES HANDLES SONT DANS TABLE "per process"

TODO ADD :
       O_CLOEXEC (Since Linux 2.6.23)
              Enable the close-on-exec flag for the new file descriptor.  Specifying
              this flag permits a program to avoid additional fcntl(2) F_SETFD
              operations to set the FD_CLOEXEC flag.  Additionally, use of this flag
              is essential in some multithreaded programs since using a separate
              fcntl(2) F_SETFD operation to set the FD_CLOEXEC flag does not suffice
              to avoid race conditions where one thread opens a file descriptor at
              the same time as another thread does a fork(2) plus execve(2).

    IMPORTANT
    The pthread_atfork() function shall declare fork handlers to be called before and after fork(), in the context of the thread that called fork(). The prepare fork handler shall be called before fork() processing commences. The parent fork handle shall be called after fork() processing completes in the parent process. The child fork handler shall be called after fork() processing completes in the child process. If no handling is desired at one or more of these three points, the corresponding fork handler address(es) may be set to NULL.
    The order of calls to pthread_atfork() is significant. The parent and child fork handlers shall be called in the order in which they were established by calls to pthread_atfork(). The prepare fork handlers shall be called in the opposite order.


when truncating file which is not writable :
 # CPython actually raises "[Errno 13] Permission denied", but well... err 9 is fine too - PAKAL WTF ????
 Warning - the file pointer goes to the new file end ??? or not ???
"""

        

 
def monkey_patch_original_io_module(): 
    
    
    # we replace the most basic file io type by a backward-compatible but enhanced version
    class RSFileIORawWrapper(RSFileIO):
        """
        Interface to rsFile accepting the limited "fopen()" modes (no file locking, no O_EXCL|O_CREAT semantic...)
        """
        def __init__(self, name, mode="r", closefd=True):
            (raw_kwargs, extended_kwargs) = parse_standard_args(name, mode, None, None, closefd)
            RSFileIO.__init__(self, **raw_kwargs)
            if extended_kwargs["truncate"]:
                # HERE, ERROR IF FILE NOT WRITABLE !!!! PAKAL
                self.truncate(0) # Warning - this raw wrapper mimics basic rawFileIO, and doesn't use locking !!!!
    
    # Important Patching ! #
    io.FileIO = RSFileIORawWrapper  
    io.BufferedReader = RSBufferedReader
    io.BufferedWriter = RSBufferedWriter
    io.BufferedRandom = RSBufferedRandom
    io.TextIOWrapper = RSTextIOWrapper
    io.open = functools.partial(rsopen, handle=None, locking=False, timeout=0, thread_safe=False, mutex=None, permissions=0777) 

    
    """ # OLD, very magical monkey patching of buffer/text classes
        # New, use inherited classes of rsfile_streams instead
    
    # We implant proxies for new rawFileIo methods, in buffer and text base classes
    def generate_method_forwarder(underlying_object, attribute_name, must_reset):
        import rsfileio_abstract
        @functools.wraps(getattr(rsfileio_abstract.AbstractRSFileIO, attribute_name))
        def method_forwarder(self, *args, **kwargs):
            if must_reset:
                self.seek(self.tell()) # Pakal - to change when io module fixed !!!
                # # # # self.seek(0, os.SEEK_CUR) # we flush i/o buffers !
            return getattr(getattr(self, underlying_object), attribute_name)(*args, **kwargs) # we call the method of the underlying object
        return method_forwarder
    
    new_methods = ("uid", "times", "size", "sync", "lock_file", "unlock_file")
    reset_methods = new_methods[2:] # size, sync and locks need a flushing of buffers !
    for attr in new_methods:
        forwarder = generate_method_forwarder("raw", attr, must_reset=(attr in reset_methods))
        setattr(io.BufferedIOBase, attr, forwarder)
    for attr in new_methods:
        forwarder = generate_method_forwarder("buffer", attr, must_reset=(attr in reset_methods))
        setattr(io.TextIOBase, attr, forwarder)
    
    
    
    # Forwarders to get attributes like name, mode, closefd etc... #
    
    def get_raw_attr(self, name):
        # print "--> taking ", name, "in ", self
        raw = object.__getattribute__(self, "raw") # warning - avoid infinite recursion on getattr !
        return getattr(raw, name)
    setattr(io.BufferedIOBase, "__getattr__", get_raw_attr)
 
    def get_buffer_attr(self, name):
        # print "--> taking ", name, "in ", self
        buffer = object.__getattribute__(self, "buffer") # warning - avoid infinite recursion on getattr !
        return getattr(buffer, name)
    setattr(io.TextIOBase, "__getattr__", get_buffer_attr)
    
    """
    
    
if __name__ == '__main__':
    monkey_patch_original_io_module()
    
        
#contract.checkmod(module)        # UNCOMMENT THIS TO ACTIVATE CONTRACT CHECKING    

