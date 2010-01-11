

# Large files linux : http://www.suse.de/~aj/linux_lfs.html
"""

SEE : http://publib.boulder.ibm.com/iseries/v5r2/ic2928/index.htm?info/ifs/rzaaxmstlargefile.htm

The fseeko() and ftello() functions are identical to fseek() 
and ftell() (see fseek(3)), respectively, except that the offset 
argument of fseeko() and the return value of ftello() is of type 
off_t instead of long. 

fstat64() (Get file information by descriptor (large file enabled))
 gets status information about the file specified by the 
 open file descriptor file_descriptor and stores the information 
 in the area of memory indicated by the buf argument.
 
 ftruncate64() (Truncate file (large file enabled)) truncates the file 
 indicated by the open file descriptor file_descriptor to the indicated length.
 
 open64() (Open file (large file enabled)) opens a file and returns a number called a file descriptor.


BETTER : Function: off64_t lseek64 (int filedes, off64_t offset, int whence) 

SUMMARY : on darwin and *bsd, no problems, off_t is 64bits
on solaris and linux, search for 64 bits extensions !!

LINUX - If the two processes are communicating over some sort 
of socket, you can pass the file descriptor between them. Here's 
a good explanation, from the postfix archive, of how to actually do 
it. Basically you use the sendmsg function with a special flag that 
lets the kernel know you are sending a file descriptor, and it will 
duplicate the descriptor and give it to the target process. Very handy.
"""

"""

IDEA - thread-private working directory ???


IN PYWIN32 - ctypes : warning 
    if isinstance(data, bytearray):
        PAKAL TO REDO !!!!!
        #data_to_write = ctypes.POINTER(ctypes.c_char).from_buffer(data) # NOT WORKING - TODO - WARNING
    else:

In pywin32 : import AllocateReadBuffer(bufSize) for readfile

To write to the end of file, specify both the Offset and OffsetHigh members of the OVERLAPPED structure as 0xFFFFFFFF. This is functionally equivalent to previously calling the CreateFile function to open hFile using FILE_APPEND_DATA access.


Q: what's he point of readinto ??????? Why not use it for files ???

Hyrule castle http://www.youtube.com/watch?v=CADHl-iZ_Kw&feature=channel


FCNTL LOCKS ARE BULLSHIT - removed when ANY fd to the file is closed !!!
FLOCK better, but not NFS....
-----> file ops must be SHORT 
---------> faire system qui ne ferle pas reellement les fd !!! 
---------> laisser à l'utilisateur le choix entre flock (pas nfs ni chunks) et fcntl (broken)
If a process uses open(2) (or similar) to obtain more than one 
descriptor for the same file, these descriptors are treated independently by flock(). 
An attempt to lock the file using one of these file descriptors 
may be denied by a lock that the calling process has already placed via another descriptor.
"""


error = OSError # we expose the type of errors that this backend uses

from ctypes import create_string_buffer # R/W fixed-length buffer

import os as _os
from os import (open, 
               close, # not return value
               fstat,
               lseek,
               ftruncate, # not return value
               write, # arguments : (fd, string), returns number of bytes written
               fsync, fdatasync,
               read) # directly returns a string

# WARNING - On at least some systems, LOCK_EX can 
# only be used if the file descriptor refers to a file opened for writing !!!!!
# -> TO BE ENFORCED


from fcntl import lockf # used both to lock and unlock !
"""
The default for start is 0, which means to start at the 
beginning of the file. The default for length is 0 which 
means to lock to the end of the file. The default for whence is also 0.
"""


def ltell(fd):
    return lseek(fd, 0, _os.SEEK_CUR)



def readinto(fd, buffer, count):
    """
    We mimic the posix read() system call, which works with buffers.
    """
    data = _os.read(fd, count)
    buffer[0:len(data)] = data

    
from 






        
    # # Private methods - no check is made on their argument or the file object state ! # #
        
    def _inner_create_streams(self, **kwargs):  # TO BE CHANGED !!!!!!!!!!
        self._unsupported("_inner_create_streams")

    def _inner_close_streams(self):  
        self._unsupported("_inner_close_streams")  

    def _inner_reduce_file(self, size): 
        self._unsupported("_inner_reduce_file")  

    def _inner_extend_file(self, size, zero_fill): 
        self._unsupported("_inner_extend_file")

    def _inner_sync(self, metadata):
        self._unsupported("sync")
        
    def _inner_fileno(self):
        self._unsupported("fileno") # io.UnsupportedOperation subclasses IOError, so we're OK with the official specs

    def _inner_handle(self):
        self._unsupported("handle") # io.UnsupportedOperation subclasses IOError, so we're OK with the official specs

    def _inner_uid(self):
        self._unsupported("uid")
 
    def _inner_times(self):
        self._unsupported("times")
        
    def _inner_size(self):  
        self._unsupported("size")

    def _inner_tell(self):
        self._unsupported("tell")

    def _inner_seek(self, offset, whence):
        self._unsupported("seek")

    def _inner_readinto(self, buffer):
        self._unsupported("readinto")

    def _inner_write(self, buffer):
        self._unsupported("write")

    def _inner_file_lock(self,shared, timeout, length, offset, whence):
        self._unsupported("lock_chunk")

    def _inner_file_unlock(self, length, offset, whence):
        self._unsupported("unlock_chunk")
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    