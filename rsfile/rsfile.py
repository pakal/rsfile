#-*- coding: utf-8 -*-

from __future__ import with_statement

import sys, os, locale, time, random, threading, multiprocessing
import functools, traceback
import types
from contextlib import contextmanager
import collections
import functools
import io
from io import RawIOBase


module = sys.modules[__name__]


try:
    import fcntl	
    import errno
    FILE_IMPLEMENTATION = "unix"
except ImportError:
    try:
        # ALTERNATIVE BACKENDS #
        from rsbackends import pywin32_extensions as win32
        #from rsbackends import pywin32_ctypes as win32 
        FILE_IMPLEMENTATION = "win32"
    except ImportError:
        raise ImportError("Neither fcntl nor pywin32 available... unable to use file locking") # we let propagate



DEFAULT_BUFFER_SIZE = 8 * 1024  # bytes


# # # TODO list # # #



"""
TODO : check if this is true, or if only dup2() descriptors have this effect :
Locks are associated with processes. A process can only have one kind of lock set for each byte of a given file. 
When any file descriptor for that file is closed by the process, all of the locks that process holds on that file 
are released, even if the locks were made using other descriptors that remain open. Likewise, locks are released when 
a process exits, and are not inherited by child processes created using fork (see Creating a Process). 
"""
# warning - we must take care of file deletion on windows and linux !!! share_delete renaming etc.!! avoid broken file waiting deletion

#TODO py2.7 he file object will now set the filename attribute on the IOError exception when trying to open a directory on POSIX platforms. (Noted by Jan Kaliszewski; issue 4764.)
#TODO - The io.FileIO class now raises an OSError when passed an invalid file descriptor. (Implemented by Benjamin Peterson; issue 4991.)
# COOL STUFFS :
# TODO : add upgrade/downgrade of shared/nonshared full file locks !!!! (fcntl does it atomically !)
# TODO : grab the ctypes locking found in bazaar code - lockfile, overlapped etc !!!!


# Todo : make errors explicit when closing streams, eg. if flush fails !!!! (buggy in current io)


# TODO : recheck again what happens with IOBase.truncate() and file pointer in the bug tracker !
#-> first, PATCH THE C SOURCES

# Todo : check that current buffer class work well when seeking (pos, seek_cur) ! (buggy in 2.6.1)
# -> Could you construct a test case? (it's even better if you fix the offending code as well of course)

# Todo : use integer handles instead of win32.HANDLE(128)
# GetFileInformationByHandleEx and GetFileInformationByHandle Functions - Retrieve file information for the specified file.
# exception io.UnsupportedOperation - An exception inheriting IOError and ValueError that is raised when an unsupported operation is called on a stream.

# Todo - test truncation with zerofill, and closing of descriptors, and INHERITANCE via spawn and fork !!!!!!

# Todo - discuss the use of name, mode, closefd etc. as attributes of raw streams only ????
# Todo - recheck messy docs on write() methods - which one fail and which one return number of bytes < expected - 'Returns the number of bytes written, which may be less than len(b).'
# Todo - advocate thread-safe interface, globalized check_closed() checking, and public interface only win32 error converter !!! @_win32_error_converter not on private methods !!
# # exception BlockingIOError - to implement

# file handle duplication or inheritance: warn about the filepointer sensitivity, which may cause big troubles if you don't lock files !!!

"""
when truncating file which is not writable :
 # CPython actually raises "[Errno 13] Permission denied", but well... err 9 is fine too - PAKAL WTF ????
 Warning - the file pointer goes to the new file end ??? or not ???
"""
# On win32, it seems no datasync exists - metadata is always written with data

        
        




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
    return module._default_safety_options.copy()

def set_default_safety_options(**options):
    new_options = set(options.keys())
    all_options = set(_default_safety_options.keys())
    if not new_options <= all_options:
        raise ValueError("Unknown safety option : "+", ".join(list(new_options - all_options)))
    _default_safety_options.update(options)

############################################




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


        
class genericFileIO(RawIOBase):  
    """    GRANDE QUESTION : peut-on obtenir atomic appends on all platforms, en perdant la truncation ?????    """   
    
    def __init__(self,
                 path=None, # it seems pywin32 already uses unicode versions of these functions, so it's cool  :-)
                 read=False, 
                 write=False, append=False,  # writing to a file in append mode AUTOMATICALLY moves the file pointer to EOF # PAKAL -A TESTER
                 
                 must_exist=False, must_not_exist=False, # only used on file opening
                 synchronized=False,
                 inheritable=False, 
                 hidden=False,
                 
                 fileno=None, 
                 handle=None, 
                 closefd=True
                 ):

        """
        pre:
            path is None or isinstance(path, basetring)  # if specified
            not (fileno and handle)
            closefd or (fileno or handle) 
            
            read or write or append
            not (must_exist and must_not_exist)
            # we don't care about other parameters, as these are independant boolean flags
        post:
            __return__ is None
        """
        
        # Preliminary normalization
        if append: 
            write = True # append implies write
        
        # we retrieve the dict of provided arguments, except self
        kwargs = locals()
        del kwargs["self"]
        del kwargs["closefd"] # not needed at inner level
        


        # HERE WE CHECK EVERYTHING !!! PAKAL
        
        if not path and not fileno and not handle: 
            #print "##################", locals()
            raise ValueError("File must provide at least path, fileno or handle value")
        
        if not read and not write and not append:
            raise ValueError("File must be opened at least in 'read', 'write' or 'append' mode")

        if must_exist and must_not_exist:
            raise ValueError("File can't be wanted both existing and unexisting")

        if not closefd and not (fileno or handle):
            raise ValueError("Cannot use closefd=False without providing a descriptor to wrap")
                

        # Inner lock used when several field operations are involved, eg. when truncating with zero-fill
        # The rule is : public methods must protect themselves, whereas inner ones are clueless 
        # about multithreading and other concurrency issues ?????
        self._multi_syscall_lock = threading.Lock() # Pakal - shouldn't it be removed after full locking enforcement ????
        
        self._full_file_locking_activated = False # if set to True, we must unlock() the whole file on close
        
        # variables to determine future write/read operations 
        self._seekable = True
        self._readable = read
        self._writable = write # 'append' enforced the value of 'write' to True, just above
        self._append = append
        
        self._synchronized = synchronized
        self._inheritable = inheritable
        self._hidden = hidden
    

        self._name = None # 'name' : descriptor exposed just for retrocompatibility !!!
        if fileno is not None:
            self._name = fileno
        if path is not None:
            self._name = path
     
        # TODO - replace this by rsfs methods !!
        self._path = None
        if isinstance(path, basestring):
            try: 
                self._path = os.path.normcase(os.path.normpath(os.path.realpath(path)))
            except EnvironmentError: # weirdo path, just make it absolue...
                self._path = os.path.abspath(path)
        
        self._fileno = None # C style file descriptor, might be created only on request
        self._handle = None # native platform handle other than fileno - if existing
        self._closefd = closefd        
        
        self._inner_create_streams(**kwargs)

        if append:
            self.seek(0, os.SEEK_END) # required by unit tests...      

            
    def close(self):
        with self._multi_syscall_lock: # we must avoid having several threads entering this

            if not self.closed:
                
                RawIOBase.close(self) # we first mark the stream as closed... it flushes, also.
                
                if self._full_file_locking_activated:
                    self.unlock_file() # we must use the public function, not to bypass whole_locking logic !              
            
                self._inner_close_streams()


    def seekable(self):
        return self._seekable
    def readable(self):
        return self._readable
    def writable(self):
        return self._writable
    
    
    
    # # # Read-only Attributes # # #
    
    # Pakal - to be removed ????
    @property
    def mode(self): 
        # we mimic the _fileio.c implementation, that's weird but well...
        if self.readable():
            return "rb+" if self.writable() else "rb"
        else:
            return "wb"    

    @property
    def name(self):  # DEPRECATED !!!
        return self._name    

    @property
    def path(self):  # Normalized, absolute path !!
        return self._path    

    @property 
    def closefd(self): # WARNING - NOT REQUIRED BY IO SPECS !!!
        return self._closefd
        

        
    # # # Methods that must be overriden in OS-specific file types # # #    

    def fileno(self):
        self._checkClosed()
        return self._inner_fileno()

    def handle(self):
        """Returns the OS-specific native file handle, if it exists, else raises an 
        UnsupportedOperation exception (inheriting IOError and ValueError).
        Currently, only win32 handles are supported (posix systems only use file descriptors as returned by fileno()
        """
        self._checkClosed()
        return self._inner_handle()  
    
    def uid(self):
        """Returns a tuple (device, inode) identifying the node (disk file) targetted by the underlying OS handle.
    
        Raises IOError in case it is impossible to retrieve this information (network filesystems etc.)
        Several file objects refer to the same disk file if and only if they have the same uid.
        
        Nota : the file path can't be used as an unique identifier, since it is often possible to delete/recreate 
        a filesystem entry and make it point to different nodes, while streams born from that path are in use.  
        """
        self._checkClosed()
        return self._inner_uid()
    
    def times(self):
        """Returns a FileTimes instance with portable file time attributes, as integers or floats. 
        Their precision may vary depending on the platform, but they're always expressed in seconds.
        Currently supported attributes: access_time and modification_time:
        """
        self._checkClosed()
        return self._inner_times()
        
    def size(self): # non standard method    
        """Returns the size, in bytes, of the opened file.
        """
        self._checkClosed()
        return self._inner_size()

    def tell(self):
        self._checkClosed()
        return self._inner_tell()

    def seek(self, offset, whence=os.SEEK_SET):
        self._checkClosed()
        return self._inner_seek(offset, whence)

        
    #def readall(self): <inherited>

    #def read(self, n = -1): ## NOOOO <inherited> - read() uses readinto() to do its job !
    # PAKAL - TODO - allow overriding of an _inner_read method !!!!!!!!!!!!!!
    
    def readinto(self, buffer):
        self._checkClosed()
        self._checkReadable()
        return self._inner_readinto(buffer)

    def write(self, buffer):
        """Write the given buffer to the IO stream. #PAKAL - TO FIX !!!!!
        Returns the number of bytes written, which may be less than len(b) ???????????
        """
        self._checkClosed()
        self._checkWritable()
        return self._inner_write(buffer)

    def truncate(self, size=None, zero_fill=True):
        """
        TODO PAKAL - what about file pointers ?
        TODO - recheeck code coverage on this, and fallback extend-with-zeros
        """
        with self._multi_syscall_lock: # to be removed, with threadsafe interface ???
            self._checkClosed()
            self._checkWritable() # Important !

            if size is None:
                size = self.tell()
            elif size < 0: 
                raise IOError(22, "Invalid argument : truncation size must be None or positive integer, not '%s'"%size)

            current_size = self.size()
            if size < current_size:
                self._inner_reduce(size)
            else:
                self._inner_extend(size, zero_fill)        

                current_size = self.size()
                if(current_size != size): # no native operation worked for it. so we fill with zeros by ourselves

                    assert current_size < size
                    self._inner_seek(current_size, os.SEEK_SET)
                    bytes_to_write = size - current_size
                    (q, r) = divmod(bytes_to_write, io.DEFAULT_BUFFER_SIZE)

                    for _ in range(q):
                        padding = '\0'*io.DEFAULT_BUFFER_SIZE
                        self._inner_write(padding)
                    self._inner_write('\0'*r)
                    
            return self.size()

    def flush(self):
        pass # that raw stream should have no buffering except the kernel's one, which gets flush by sync calls
    
    def sync(self, metadata=True):
        """
        Synchronizes file data between kernel cache and physical disk. 
            If metadata is False, and if the platform supports it (win32 and Mac OS X don't), this sync is only a "datasync", i.e file metadata (file size, file times...) 
            is not written to disk ; note that in this case, performance gains can be expected, but data appended to the file might be lost in case of crash, 
            since the file size increasement won't have become persistent.
            For a constant synchronization between the kernel cache and the disk oxyde, CF the "synchronized" argument of the stream opening.
        """
        self._inner_sync(metadata)        


    @contextmanager
    def _fullLockRemover(self):
        # we do nothing on __enter__()
        yield
        # we unlock on __exit__()
        self.unlock_file() 
      
    
    def lock_file(self, shared=False, timeout=None):
        
        self._inner_file_lock(shared, timeout, None, 0, os.SEEK_SET) # we lock the whole data 
        # no exception was raised ? Cool...
        self._full_file_locking_activated = True
        return self._fullLockRemover()  
       
    
    @contextmanager
    def _chunkLockRemover(self, length, offset, whence):
        # we do nothing on __enter__()
        yield
        # we unlock on __exit__()
        self.unlock_chunk(length=length, offset=offset, whence=whence) 
            
    def lock_chunk(self, shared=False, timeout=None, length=None, offset=0, whence=os.SEEK_SET):
        """Locks the whole file or a portion of it, depending on the arguments provided.
        
        If shared is True, the lock is a "reader", non-exclusive lock, which can be shared by several 
        processes, but prevents "writer" locks from being taken on the locked portion. 
        Else, the lock is a "writer" lock which is fully exclusive, preventing both writer 
        and reader locks from being taken by other processes on the locked portion.
        
        If timeout is None, the process will block on this operation until it manages to get the lock; 
        else, it must be a number indicating how many seconds
        the operation will wait before raising a timeout????? exception 
        (thus, timeout=0 means a non-blocking locking attempt).
        
        Offset and/or length can be used to specify a portion of file to lock. 
        They must both be None or integers. If length is an integer, it must be positive or null, 
        and if its is 0 or None, this means all the rest of the file will be locked, from the specified 
        offset. Whence is the same as in seek(), and specifies where the offset is calculated from (beginning, current position, or end of file).
        
        The strength of the locking depends on the underlying platform. On windows, all file locks are mandatory, i.e even programs which are not using 
        file locks won't be able to access locked parts of files for reading or writing (depending on the type of lock used).
        On posix platforms, most of the time locking is only advisory, i.e unless they use the same type of lock as rsFile's ones (currently, fcntl calls),
        programs will be able to freely access your files if they have proper permissions. Note that it is possible to enforce mandatory locking thanks to some
        mount options and file flags (see XXX???urls)
        
        Note that file locking is not reentrant: calling this function several times, on overlapping areas, would result in a deadlock (as with threading.Lock);
        but you can still get different locks at the same time, for different parts of the same file (beware of deadlocks still,
        in case several process try to get them in different orders).
        ??? TELL EXCEPTIONS HERE
        
        Warning - posix fork : Locks are associated with processes. 
        A process can only have one kind of lock set for each byte of a given file
        When any file descriptor for that file is closed by the process, 
        all of the locks that process holds on that file are released, 
        even if the locks were made using other descriptors that remain open.
        
        # TO BE ADDED : MORE ASSERTIONS PYCONTRACT !!! 
        pre:
            offset is None or isistance(offset, int)
            length is None or (isistance(length, int) and length >= 0)
        post:
            isinstance(__return__, bool)

        WARNING : WIN32 - Locking a portion of a file for shared access denies all processes write access to the specified region of the file, including the process that first locks the region. All processes can read the locked region.
        
        """
        
        self._inner_file_lock(shared=shared, timeout=timeout, length=length, offset=offset, whence=whence) 
            

        return self._chunkLockRemover(length, offset, whence)
    
    
    
    def unlock_file(self):
        self._inner_file_unlock(None, 0, os.SEEK_SET) # we unlock the whole data 
        # no exception was raised ? Cool...
        self._full_file_locking_activated = False   

    
    def unlock_chunk(self, length=None, offset=0, whence=os.SEEK_SET):
        """Unlocks a file portion previously locked by the same process. 
        
        The specifications of the locked area (absolute offset and length) must be the same as those used when calling locking methods,
        else errors will occur; its is thus not possible to release only a part of a locked area, or to unlock with only one call
        two consecutive parts (well, posix locks allow it, but for portability's sake you had better not count on it ??? TRUE ??)
        
        ??? PAKAL - TELL ABOUT EXCEPTIONS THERE
        """  
        
        self._inner_file_unlock(length=length, offset=offset, whence=whence)
 
 
        
    # # Private methods - no check is made on their argument or the file object state ! # #
        
    def _inner_create_streams(self, path, read, write, append, must_exist, must_not_exist, synchronized, inheritable, hidden, fileno, handle, closefd):
        self._unsupported("_inner_create_streams")

    def _inner_close_streams(self):  
        self._unsupported("_inner_close_streams")  

    def _inner_reduce(self, size): 
        self._unsupported("_inner_reduce")  

    def _inner_extend(self, size, zero_fill): 
        self._unsupported("_inner_extend")

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

    def _inner_file_lock(self, shared, timeout, length, offset, whence):
        self._unsupported("lock_chunk")

    def _inner_file_unlock(self, length, offset, whence):
        self._unsupported("unlock_chunk")

        
        
        

        

        
if FILE_IMPLEMENTATION == "win32":   
    
    from rsbackends import _utilities as utilities
    
    class win32FileIO(genericFileIO):        

  
        __POSITION_REFERENCES = {os.SEEK_SET:win32.FILE_BEGIN , os.SEEK_CUR:win32.FILE_CURRENT, os.SEEK_END:win32.FILE_END}

        # Warning - this is to be used as a static method ! #
        def _win32_error_converter(f): #@NoSelf
            @functools.wraps(f)
            def wrapper(self, *args, **kwds):
                try:
                    return f(self, *args, **kwds)
                except win32.error, e: # WARNING - this is not a subclass of OSERROR !!!!!!!!!!!!!
                    traceback = sys.exc_info()[2]
                    #print repr(e)str(e[1])+" - "+str(e[2
                    raise IOError(e[0], str(e[1]), str(self._name)), None, traceback
            return wrapper
        
        
        
        @_win32_error_converter        
        def _inner_create_streams(self, path, read, write, append, must_exist, must_not_exist, synchronized, inheritable, hidden, fileno, handle):

            #print("Creating file with : ",locals()) #PAKAL
            self._close_via_fileno = False
            
            # # # real opening of the file stream # # #
            if handle is not None:
                self._handle = int(handle)
                #print "FILE OPENED VIA HANDLE ", handle
                
            elif fileno is not None:
                self._close_via_fileno = True # we shall close stream via its C wrapper
                self._fileno = fileno
                #print "FILE OPENED VIA FILENO ", fileno
                self._handle = win32._get_osfhandle(fileno) # required immediately
                
            else: #we open the file with CreateFile
                #print "FILE OPENED VIA PATH ", path
                desiredAccess = 0
                if read : # we mimic the POSIX behaviour : we must have at least read or write
                    desiredAccess |= win32.GENERIC_READ
                if write: 
                    desiredAccess |= win32.GENERIC_WRITE
                assert desiredAccess
                
                # we reproduce the Unix sharing behaviour : full sharing, and we can move/delete files while they're open
                shareMode = win32.FILE_SHARE_READ | win32.FILE_SHARE_WRITE | win32.FILE_SHARE_DELETE

                creationDisposition = 0
                if must_exist:
                    creationDisposition = win32.OPEN_EXISTING # 3
                elif must_not_exist: 
                    creationDisposition = win32.CREATE_NEW # 1
                else:
                    creationDisposition = win32.OPEN_ALWAYS # 4

                if inheritable:
                    securityAttributes = win32.SECURITY_ATTRIBUTES()
                    securityAttributes.bInheritHandle = True
                    securityAttributes.SECURITY_DESCRIPTOR = None
                else:
                    securityAttributes = None
                
                flagsAndAttributes = win32.FILE_ATTRIBUTE_NORMAL   
                
                #### NO - TODO - PAKAL - use RSFS to delete it immediately !!!
                if hidden:
                    flagsAndAttributes |= win32.FILE_FLAG_DELETE_ON_CLOSE
                    
                if synchronized:
                    flagsAndAttributes |= win32.FILE_FLAG_WRITE_THROUGH 
                    # DO NOT USE FILE_FLAG_NO_BUFFERING - too many constraints on data alignments
                    # thanks to this flag, no need to "fsync" the file with FlushFileBuffers(), it's immediately stored on the disk
                    # Warning - it seems that for some people, metadata is actually NOT written to disk along with data !!!
                    

                args = (
                    path, # accepts both unicode and bytes
                    desiredAccess, 
                    shareMode,
                    securityAttributes,
                    creationDisposition,
                    flagsAndAttributes,
                    None # hTemplateFile  
                    )
                    
                #print ">>>File creation arguments : ",args
                handle = win32.CreateFile(*args)
                self._handle = int(handle)
                if hasattr(handle, "Detach"): # pywin32
                    handle.Detach()
                

        @_win32_error_converter
        def _inner_close_streams(self):
            """
            MSDN note : To close a file opened with _get_osfhandle, call _close. The underlying handle 
            is also closed by a call to _close, so it is not necessary to 
            call the Win32 function CloseHandle on the original handle.

            This function may raise IOError !
            """
            
            if self._closefd: # always True except when wrapping external file descriptors
                if self._close_via_fileno:
                    os.close(self._fileno) # this closes the underlying native handle as well
                else:
                    win32.CloseHandle(self._handle)


        @_win32_error_converter    
        def _inner_reduce(self, size): # warning - no check is done !!! 
            
            self.seek(size) 
            #print "---> inner reduce to ", self.tell()
            win32.SetEndOfFile(self._handle) #WAAARNING - doesn't raise exceptions !!!!  

        
        @_win32_error_converter    
        def _inner_extend(self, size, zero_fill): # warning - no check is done !!!  
            
            if(not zero_fill):
                self.seek(size)
                win32.SetEndOfFile(self._handle) # this might fail silently !!!   
    
            else:
                pass # we can't directly truncate with zero-filling on win32, so just upper levels handle it

                
                
        @_win32_error_converter         
        def _inner_sync(self, metadata):
            win32.FlushFileBuffers(self._handle) 
        
        
        @_win32_error_converter         
        def _inner_uid(self):
            """
            (dwFileAttributes, ftCreationTime, ftLastAccessTime, 
             ftLastWriteTime, dwVolumeSerialNumber, nFileSizeHigh, 
             nFileSizeLow, nNumberOfLinks, nFileIndexHigh, nFileIndexLow) """
            
            handle_info = win32.GetFileInformationByHandle(self._handle)
            
            inode = utilities.double_dwords_to_pyint(handle_info.nFileIndexLow, handle_info.nFileIndexHigh)
            
            if not handle_info.dwVolumeSerialNumber or not inode:
                raise IOError(77, "Impossible to retrieve win32 device/file-id information") # Pakal - to be unified
            
            return (handle_info.dwVolumeSerialNumber, inode)
            
        
        @_win32_error_converter    
        def _inner_fileno(self):
        
           
            if self._fileno is None:
                #print "EXTRACTING FILENO !"
                #traceback.print_stack()
                if self._readable and self._writable:
                    flags = os.O_RDWR
                elif self._writable:
                    flags = os.O_WRONLY
                    if self._append:
                        flags |= os.O_APPEND
                else:
                    assert self._readable
                    flags = os.O_RDONLY
                # NEVER use flag os.O_TEXT, we're in raw IO here !
                self._fileno = win32._open_osfhandle(self._handle, flags)
                
            return self._fileno    


        def _inner_handle(self):
            return self._handle
        
        
        @_win32_error_converter
        def _inner_times(self):
  
            handle_info = win32.GetFileInformationByHandle(self._handle)
            
            # for now, just use the C compatibility layer !!
            mystat = os.fstat(self.fileno())
            return FileTimes(access_time = utilities.win32_filetime_to_python_timestamp(handle_info.ftLastAccessTime.dwLowDateTime,
                                                                                        handle_info.ftLastAccessTime.dwHighDateTime), 
                             modification_time = utilities.win32_filetime_to_python_timestamp(handle_info.ftLastWriteTime.dwLowDateTime,
                                                                                               handle_info.ftLastAccessTime.dwHighDateTime)) 
            

        @_win32_error_converter    
        def _inner_size(self):
            size = win32.GetFileSize(self._handle)
            return size    


        @_win32_error_converter        
        def _inner_tell(self):
            pos = win32.SetFilePointer(self._handle, 0, win32.FILE_CURRENT)
            return pos    


        @_win32_error_converter    
        def _inner_seek(self, offset, whence=os.SEEK_SET):
            """
            NOTE : in both linux and windows :
            It is not an error to set a file pointer to a position beyond the end of the file. The size of the file does 
            not increase until you call the  SetEndOfFile,  WriteFile, or  WriteFileEx function. A write operation increases 
            the size of the file to the file pointer position plus the size of the buffer written, which results in the 
            intervening bytes uninitialized.
            """       
            
            if not isinstance(offset, (int,long)):
                raise TypeError("Offset should be an integer in seek(), not %s object"%type(offset))

            reference = self.__POSITION_REFERENCES[whence]
            new_offset = win32.SetFilePointer(self._handle, offset, reference)
            return new_offset



        @_win32_error_converter
        def _inner_readinto(self, buffer):
            """ PAKAL - Warning - this method is currently inefficient since it converts C string into
                python str and then into bytearray, but this will be optimized later by rewriting in C module
                Warning2 - what if buffer length is ZERO ? Shouldnt we make explicit the problem, that we are not at EOF but... ?
                -> in default implementation, no error is raised !!
            """

            (res, string) = win32.ReadFile(self._handle, len(buffer))
            buffer[0:len(string)] = string
            return len(string)


        @_win32_error_converter    
        def _inner_write(self, buffer):
            """
            Gerer write avec filepointer after eof !! que se passe t il sous linux ????????
            La doc se contredit, est-ce qu'il faut retourner num written ou lancer ioerror ?? PAKAL
            """

            if not isinstance(buffer, (basestring, bytearray)):
                raise TypeError("Only buffer-like objects can be written to files, not %s objects"%str(type(buffer)))

            if self._append: # yep, no atomicity around here, as in truncate()
                self._inner_seek(0, os.SEEK_END)

            cur_pos = self._inner_tell()
            if cur_pos > self._inner_size(): # TODO - document this !!!
                self._inner_extend(cur_pos, zero_fill=True) # we extend the file with zeros until current file pointer position

            (res, bytes_written) = win32.WriteFile(self._handle, bytes(buffer))
            # nothing to do with res, for files, it seems

            # we let the file pointer where it is, even if we're in append mode (no come-back to previous reading position)
            return bytes_written


        # no need for @_win32_error_converter    
        def _win32_convert_file_range_arguments(self, length, offset, whence):

            if offset is None:
                offset = 0
            
            if(not length): # 0 or None
                (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh) = (utilities.MAX_DWORD, utilities.MAX_DWORD)
            else:
                (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh) = utilities.pyint_to_double_dwords(length)

            if(whence == os.SEEK_CUR):
                offset = offset + self._inner_tell()
            elif(whence == os.SEEK_END):
                offset = offset + self._inner_size()

            overlapped = win32.OVERLAPPED() # contains ['Internal', 'InternalHigh', 'Offset', 'OffsetHigh', 'dword', 'hEvent', 'object']
            (overlapped.Offset, overlapped.OffsetHigh) = utilities.pyint_to_double_dwords(offset)
            overlapped.hEvent = 0

            return (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)


        
        @_win32_error_converter
        def _inner_file_lock(self, shared, timeout, length, offset, whence):

            """
            # PAKAL - to remove - 
            timeout = 0
            print "TIMEOUT IS SET TO 0 TO BE REMOVEd !!!"
            # TODO PAKAL - HERE, replace timeout by default global value if it is None !!
            """
            hfile = self._handle

            flags = 0 if shared else win32.LOCKFILE_EXCLUSIVE_LOCK
            if(timeout is not None):
                flags |= win32.LOCKFILE_FAIL_IMMEDIATELY

            (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped) = self._win32_convert_file_range_arguments(length, offset, whence)

            start_time = time.time()
            try_again = True

            while(try_again):

                try:

                    #print "lock calling win32 with args (%s, %s ,%s ,%s ,%s :(%s, %s))"%(hfile, flags, nNumberOfBytesToLockLow, 
                    #        nNumberOfBytesToLockHigh, overlapped, overlapped.Offset, overlapped.OffsetHigh)
                    print ">>>>>>> %s tries locking file %s on range %u/%u (unsigned integers)"%(multiprocessing.current_process().name, self._path, overlapped.Offset, overlapped.Offset+nNumberOfBytesToLockLow-1) 

                    win32.LockFileEx(hfile, flags, nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)

                except win32.error, exc_value:
                    #print repr(exc_value)
                    
                    if(timeout is not None): # else, we try again indefinitely

                        current_time = time.time()
    
                        if(timeout <= current_time - start_time): # here failure - else, we try again until success or timeout

                            error_code, title = exc_value[0:2]
                            filename = "File"
                            try:
                                filename = self.name #PAKAL - to change
                            except AttributeError:
                                pass # surely a pseudo file object...

                            if error_code in (32, 33, 167, 307):
                                    # ### NAAAn mieux !!!!!!! winerror 
                                # error: 32 - ERROR_SHARING_VIOLATION - The process cannot access the file because it is being used by another process.
                                # error: 33 - ERROR_LOCK_VIOLATION - The process cannot access the file because another process has locked a portion of the file.
                                # error: 167 - ERROR_LOCK_FAILED - Unable to lock a region of a file.
                                # error: 307 - ERROR_INVALID_LOCK_RANGE - A requested file lock operation cannot be processed due to an invalid byte range. -> shouldn't happen due to previous value checks
                                raise LockingException(error_code, title, filename)
                            else:
                                # Q:  Are there other exceptions/codes we should be dealing with here?
                                raise
                    
                    # Whatever the value of "timeout", we must sleep a little
                    time.sleep(0.1) # TODO - PAKAL - make this use global parameters !

                else: # success, we exit the loop

                    try_again = False

            return True

            
        @_win32_error_converter  
        def _inner_file_unlock(self, length, offset, whence):

            hfile = self._handle
            
            (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped) = self._win32_convert_file_range_arguments(length, offset, whence)

            print >>sys.stderr, "-------------->", locals()    
            #traceback.print_stack()
            try:

                #print "unlock calling win32 with args (%s ,%s ,%s ,%s :(%s, %s))"%(hfile, nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped, overlapped.Offset, overlapped.OffsetHigh)
                print "%s unlocking file %s on range %u/%u<<<<<<<<<"%(multiprocessing.current_process().name, self._path, overlapped.Offset+overlapped.OffsetHigh, overlapped.Offset+overlapped.OffsetHigh++nNumberOfBytesToLockLow+nNumberOfBytesToLockHigh-1) 
                win32.UnlockFileEx(hfile, nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)
                
            except win32.error, exc_value:
                if exc_value[0] == 158:
                    # error: 158 - ERROR_NOT_LOCKED - The segment is already unlocked.
                    # To match the 'posix' implementation, silently ignore this error ???
                    raise # PAKAL - TODO - what should we raise here !!!
                else:
                    # Q:  Are there other exceptions/codes we should be dealing with here?
                    raise

            return True


    rsFileIO = win32FileIO
    
    

elif FILE_IMPLEMENTATION == "unix":

    import fcntl
    import rsbackends.posix_stdlib as unix
    
    class posixFileIO(genericFileIO):      

        """

        O_EXCL
        En conjonction avec O_CREAT, déclenchera une erreur si le fichier existe, 
        et open échouera. O_EXCL ne fonctionne pas sur les systèmes de fichiers NFS. 
        Les programmes qui ont besoin de cette fonctionnalité pour verrouiller des
         tâches risquent de rencontrer une concurrence critique (race condition). 
         La solution consiste à créer un fichier unique sur le même système de fichiers 
         (par exemple avec le pid et le nom de l'hôte), utiliser link(2) pour créer un lien 
         sur un fichier de verrouillage et d'utiliser stat(2) sur ce fichier unique pour 
         vérifier si le nombre de liens a augmenté jusqu'à 2. Ne pas utiliser la valeur 
         de retour de link(). 
        
            """

        # # Private methods - no check is made on their argument or the file object state ! # #
        
        def _inner_create_streams(self, path, read, write, append, must_exist, must_not_exist, synchronized, inheritable, hidden, fileno, handle):

            
            # TODO - For delete on close ->  unlink immediately 
            
            if handle is not None:
                self._unsupported("Stream creation from a posix handle")
                
            if fileno is not None:
                self._file = fileno
            
            else: #we open the file with low level posix IO - the unix "open()"  function
            
                if isinstance(path, unicode):
                    strname = path.encode(sys.getfilesystemencoding()) # let's take no risks - and do not use locale.getpreferredencoding() here 
                else: 
                    strname = path
            
            
                flags = 0
                
                if synchronized :
                    flags |= unix.O_SYNC
                    
                if read and write: 
                    flags |= unix.O_RDWR
                elif write: 
                    flags |= unix.O_WRONLY
                else:
                    flags |= unix.O_RDONLY
            
            
                if must_exist:
                    pass # it's the default case for open() function
                elif must_not_exist: 
                    flags |= unix.O_CREAT | unix.O_EXCL
                else:
                    flags |= unix.O_CREAT # by default - we create the file iff it doesn't exists
            
                # TODO - use linux O_CLOEXEC when available
                # TODO - use F_FULLFSYNC on MAC OS X !!!   -> fcntl(fd, F_FULLFSYNC, 0);  51
                self._fileno = unix.open(strname, flags)
                
                if not inheritable:
                    old_flags = fcntl.fcntl(self._fileno, fcntl.F_GETFD, 0);
                    if not (old_flags & fcntl.FD_CLOEXEC):
                        fcntl.fcntl(self._fileno, fcntl.F_SETFD, old_flags | fcntl.FD_CLOEXEC);
                
                # Here, if delete on close : unlink filepath !!!
                #### NO - TODO - PAKAL - use RSFS to delete it immediately !!!
                
        def _inner_close_streams(self):  
            """
            Warning - unlink official stdlib modules, this function may raise IOError !
            """
            if self._closefd:
                unix.close(self._fileno) 
    
    
    
        def _inner_reduce(self, size): 
            unix.ftruncate(self._fileno, size)
    
        def _inner_extend(self, size, zero_fill): 
            # posix truncation is ALWAYS "zerofill"
            unix.ftruncate(self._fileno, size)
    
        def _inner_sync(self, metadata):
            if not metadata:
                try:
                    # WARNING - file size will ALWAYS be updated if necessary to preserve data integrity, theoretically
                    unix.fdatasync(self._fileno) # not supported on Mac Os X
                    return
                except unix.error:
                    pass
            
            try:
                unix.fcntl(self._fileno, unix.F_FULLFSYNC, 0) 
            except NameError:
                unix.fsync(self._fileno)
            
                
        def _inner_fileno(self):
            return self._fileno
    
        # Inherited :
        #def _inner_handle(self):
        #   self._unsupported("handle") # io.UnsupportedOperation subclasses IOError, so we're OK with the official specs
    
    
        def _inner_uid(self):
            stats = unix.fstat(self._fileno)
            return (stats.st_dev, st_ino)
     
        def _inner_times(self):
            stats = unix.fstat(self._fileno)
            return FileTimes(access_time=stats.st_atime, modification_time=stats.st_mtime)
            
        def _inner_size(self):  
            return unix.fstat(self._fileno).st_size
    
        def _inner_tell(self):
            return unix.ltell(self._fileno)
    
        def _inner_seek(self, offset, whence):
            return unix.lseek(self._fileno, offset, whence)
    
        def _inner_readinto(self, buffer):
            count = unix.readinto(self._fileno, buffer)
            return count
    
        def _inner_write(self, bytes):
            return unix.write(self._fileno, bytes)
        
        
        
        def _fcntl_convert_file_range_arguments(self, length, offset, whence): # some normalization of arguments
            if(length is None):
                length = 0 # maximal range for fcntl/lockf
            return (length, offset, whence)


        def _lock_file(self, shared, timeout, length, offset, whence):

            """ MEGAWARNING : On at least some systems, 
            LOCK_EX can only be used if the file descriptor refers to a file opened for writing."""

            fd = self.fileno()

            if(shared):
                operation = fcntl.LOCK_SH
            else:
                operation = fcntl.LOCK_EX

            if(timeout is not None):
                operation |= fcntl.LOCK_NB

            (length, offset, whence) = self._fcntl_convert_file_range_arguments(length, offset, whence)


            start_time = time.time()
            try_again = True

            while(try_again):

                try :

                    unix.lockf(fd, operation, length, offset, whence)

                except unix.error, e:

                    if(timeout is not None): # else, we try again indefinitely

                        current_time = time.time()

                        if(timeout <= current_time - start_time): # else, we try again until success or timeout

                            (error_code, title) = e.args

                            filename = "File"
                            try:
                                filename = str(self.name)
                            except AttributeError:
                                pass # surely a pseudo file object...

                            if(error_code in (errno.EACCES, errno.EAGAIN)):
                                raise LockingException(error_code, title, filename)
                            else:
                                raise

                else: # success, we exit the loop

                    try_again = False

            return True


        def _unlock_file(self, length, offset, whence):

            fd = self.fileno()
            (length, offset, whence) = self._fcntl_convert_file_range_arguments(length, offset, whence)
            try:
                unix.lockf(fd, fcntl.LOCK_UN, length, offset, whence)
            except IOError:
                raise # are there special cases to handle ?

            return True

    rsFileIO = posixFileIO 


    

    
def parse_standard_args(name, mode, closefd): # warning - name can be a fileno here ...
    
    modes = set(mode)
    if modes - set("arwb+tU") or len(mode) > len(modes):
        raise ValueError("invalid mode: %r" % mode)
    
    # raw analysis
    modes = set(mode)
    reading_flag = "r" in modes or "U" in modes
    writing_flag = "w" in modes
    appending_flag = "a" in modes
    updating_flag = "+" in modes
    
    truncate = writing_flag
    binary = "b" in modes
    text = "t" in modes
    
    if "U" in modes:
        if appending_flag or appending_flag:
            raise ValueError("can't use U and writing mode at once")
        reading_flag = True # we enforce reading 
    if text and binary:
        raise ValueError("can't have text and binary mode at once")
    if reading_flag + writing_flag + appending_flag > 1:
        raise ValueError("can't have read/write/append mode at once")
    if not (reading_flag or writing_flag or appending_flag):
        raise ValueError("must have exactly one of read/write/append mode")
    
    # real semantic
    if isinstance(name, int):
        fileno = name
        path = None
    else:
        fileno = None
        path = name

    read = reading_flag or updating_flag
    write = writing_flag or appending_flag or updating_flag
    append = appending_flag
    must_exist = reading_flag # "r" and "r+" modes require the file to exist, but no flag enforced "must_not_exist"
    
    raw_kwargs = dict(path=path,
                    read=read, 
                    write=write, append=append,
                    must_exist=must_exist,
                    must_not_exist=False,
                    synchronized=False,
                    inheritable=True, 
                    hidden=False,
                    fileno=fileno, handle=None, closefd=closefd)
    
    extended_kwargs = dict(truncate=truncate, 
                            binary=binary,
                            text=text)
                    
    return (raw_kwargs, extended_kwargs)
    


def parse_advanced_args(path, mode, fileno, handle, closefd):

    
    modes = set(mode)
    if modes - set("RAW+-SIHEBT") or len(mode) > len(modes):
        raise ValueError("invalid mode: %r" % mode)    
    
    path = path # The file name  # PAKAL - MUST BE NONE OR A STRING IN ANYWAY - PYCONTRACT THIS PLZ !!!
    
    read = "R" in mode
    append = "A" in mode
    write = "W" in mode or append 
    
    must_exist = "+" in mode
    must_not_exist = "-" in mode
    
    synchronized = "S" in mode
    inheritable = "I" in mode
    hidden = "H" in mode
    
    truncate = "E" in mode # for "Erase"  
    binary = "B" in modes
    text = "T" in modes
    
    raw_kwargs = dict(path=path,
                    read=read, 
                    write=write, append=append,
                    must_exist=must_exist, 
                    must_not_exist=must_not_exist,
                    synchronized=synchronized,
                    inheritable=inheritable, 
                    hidden=hidden,
                    fileno=fileno, handle=handle, closefd=closefd)
    
    extended_kwargs = dict(truncate=truncate, 
                      binary=binary,
                      text=text)
                      
    return (raw_kwargs, extended_kwargs)



# Constants #

LOCK_ALWAYS=2
LOCK_AUTO=1
LOCK_NEVER=0

    
def rsOpen(name=None, mode="R", buffering=None, encoding=None, errors=None, newline=None, fileno=None, handle=None, closefd=True, locking=LOCK_ALWAYS, timeout=None, thread_safe=True):
    
    """
    Warning : setting lockingFalse allows you to benefit from new-style modes without dealing with any automated locking, but be aware that in this configuration, 
    file truncation on opening will become rather sensitive, as nothing will prevent it from disrupting other processes using the same file.
    
    Buffering:
        <0 or None -> full buffering
        0 -> disabled
        1 -> line buffering
        >1 -> take that buffer size
    
    thread_safe : if true, wraps the top-most stream object into a thread-safe interface
    """
    
    # TODO - PYCONTRACT !!!
    
    # Quick type checking
    if name and not isinstance(name, (basestring, int)):
        raise TypeError("invalid file: %r" % name)
    if not isinstance(mode, basestring):
        raise TypeError("invalid mode: %r" % mode)
    if buffering is not None and not isinstance(buffering, int):
        raise TypeError("invalid buffering: %r" % buffering)
    if encoding is not None and not isinstance(encoding, basestring):
        raise TypeError("invalid encoding: %r" % encoding)
    if errors is not None and not isinstance(errors, basestring):
        raise TypeError("invalid errors: %r" % errors)
    
    cleaned_mode = mode.replace("U", "")
    if cleaned_mode.lower() == cleaned_mode:
        assert handle is None and fileno is None # to handle these, use advanced open mode
        (raw_kwargs, extended_kwargs) = parse_standard_args(name, mode, closefd)
    elif cleaned_mode.upper() == cleaned_mode:
        (raw_kwargs, extended_kwargs) = parse_advanced_args(name, mode, fileno, handle, closefd)
    else:
        raise ValueError("bad mode string %r : it must contain only lower case (standard mode) or upper case (advanced mode) characters" % mode)

    if extended_kwargs["binary"] and encoding is not None:
        raise ValueError("binary mode doesn't take an encoding argument")
    if extended_kwargs["binary"] and errors is not None:
        raise ValueError("binary mode doesn't take an errors argument")
    if extended_kwargs["binary"] and newline is not None:
        raise ValueError("binary mode doesn't take a newline argument")     
    
    raw = rsFileIO(**raw_kwargs)
    
    if extended_kwargs["truncate"] and not raw.writable(): 
        raise ValueError("Can't truncate file opened in read-only mode")
    
    if locking == LOCK_ALWAYS:   
        # we enforce file locking immediately
        if raw.writable():
            shared = False
        else:
            shared = True
        
        print "we enforce file locking with %s - %s" %(shared, timeout)            
        raw.lock_file(shared=shared, timeout=timeout) # since it's a whole-file locking, auto-unlocking-on-close will be activated ! Cool !
    
    if extended_kwargs["truncate"]:    
        if locking == LOCK_AUTO:
            with raw.lock_file():
                res = raw.truncate(0)
        else: # if already locked, or if we don't care about locks...
            res = raw.truncate(0)            
    
    if buffering is None:
        buffering = -1
    line_buffering = False
    if buffering == 1 or buffering < 0 and raw.isatty():
        buffering = -1
        line_buffering = True
    if buffering < 0:
        buffering = DEFAULT_BUFFER_SIZE
        try:
            bs = os.fstat(raw.fileno()).st_blksize # PAKAL - TO BE IMPROVED
        except (os.error, AttributeError):
            pass
        else:
            if bs > 1:
                buffering = bs
    if buffering < 0:
        raise ValueError("invalid buffering size")
    if buffering == 0:
        if extended_kwargs["binary"]:
            if thread_safe:
                return ThreadSafeWrapper(raw)
            else:
                return raw
        raise ValueError("can't have unbuffered text I/O")
    
    if raw.readable() and raw.writable():
        buffer = io.BufferedRandom(raw, buffering)
    elif raw.writable():
        buffer = io.BufferedWriter(raw, buffering)
    elif raw.readable():
        buffer = io.BufferedReader(raw, buffering)
    else:
        raise ValueError("unknown mode: %r" % mode)
    
    if extended_kwargs["binary"]:
        if thread_safe:
            return ThreadSafeWrapper(buffer)
        else:
            return buffer
        
    text = io.TextIOWrapper(buffer, encoding, errors, newline, line_buffering)
    text.mode = mode
    
    if thread_safe:
        return ThreadSafeWrapper(text)    
    else:
        return text
    

    
    
    
class ThreadSafeWrapper(object):
    """A quick wrapper, to ensure thread safety !"""
    def __init__(self, wrapped_obj):
        self.wrapped_obj = wrapped_obj
        self.mutex = threading.RLock()
        
    def _secure_call(self, name, *args, **kwargs):
        with self.mutex:
            #print "protected!"
            return getattr(self.wrapped_obj, name)(*args, **kwargs)
    
    
    def __getattr__(self, name):
        attr = getattr(self.wrapped_obj, name) # might raise AttributeError
        if isinstance(attr, collections.Callable):  # actually, we shouldn't care about others than types.MethodType, types.LambdaType, types.FunctionType
            return functools.partial(self._secure_call, name)
        else:
            return attr
    
    def __iter__(self):
        return iter(self.wrapped_obj)
        
    def __str__(self):
        return "Thread Safe Wrapper around %s" % self.wrapped_obj
    
    def __repr__(self):
        return "ThreadSafeWrapper(%r)" % self.wrapped_obj


    def __enter__(self):
        """Context management protocol.  Returns self."""
        self._checkClosed()
        return self

    def __exit__(self, *args):
        """Context management protocol.  Calls close()"""
        self.close()
    

    
 
def monkey_patch_original_io_module(): 
    
    
    # we replace the most basic file io type by a backward-compatible but enhanced version
    class rsFileIORawWrapper(rsFileIO):
        """
        Interface to rsFile accepting the limited "fopen()" modes (no file locking, no O_EXCL|O_CREAT semantic...)
        """
        def __init__(self, name, mode="r", closefd=True):
            (raw_kwargs, extended_kwargs) = parse_standard_args(name, mode, closefd)
            rsFileIO.__init__(self, **raw_kwargs)
            if extended_kwargs["truncate"]:
                # HERE, ERROR IF FILE NOT WRITABLE !!!! PAKAL
                self.truncate(0) # Warning - this raw wrapper mimics basic rawFileIO, and doesn't use locking !!!!
    
    # Important Patching ! #
    io.FileIO = rsFileIORawWrapper  
    io.open = functools.partial(rsOpen, locking=LOCK_NEVER, timeout=0) # PAKAL - todo - remove - just for testing !!!
    
    
    # We implant proxies for new rawFileIo methods, in buffer and text base classes
    
    def generate_method_forwarder(underlying_object, attribute_name, must_reset):
        @functools.wraps(getattr(genericFileIO, attribute_name))
        def method_forwarder(self, *args, **kwargs):
            if must_reset:
                self.seek(self.tell()) # Pakal - to change when io module fixed !!!
                # # # # self.seek(0, os.SEEK_CUR) # we flush i/o buffers !
            return getattr(getattr(self, underlying_object), attribute_name)(*args, **kwargs) # we call the method of the underlying object
        return method_forwarder
    
    new_methods = ("uid", "times", "size", "sync", "lock_file", "unlock_file", "lock_chunk", "unlock_chunk")
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
    

    
    
# TODO - TEST THESE UTILITY METHODS !!!!
    
def write_to_file(filename, data, sync=False, must_exist=False, must_not_exist=False, **open_kwargs):    

    assert "mode" not in open_kwargs # mode is automatically determined by this function

    mode = "WE" # we erase the file
    if sync: 
        mode += "S"
    if must_exist:
        mode += "+"
    if must_not_exist:
        mode += "-"
    if not isinstance(data, unicode):
        mode += "B"
    
    with rsOpen(filename, mode=mode, **open_kwargs) as myfile:
        myfile.write(data)
        myfile.flush()
        if sync:
            myfile.sync()
   
    
def append_to_file(filename, data, sync=False, must_exist=False, **open_kwargs):

    assert "mode" not in open_kwargs # mode is automatically determiend by this function

    mode = "WA"
    if sync: 
        mode += "S"
    if must_exist:
        mode += "+"
    if not isinstance(data, unicode):
        mode += "B"
    
    with rsOpen(filename, mode=mode, **open_kwargs) as myfile:
        myfile.write(data)
        myfile.flush()
        if sync:
            myfile.sync()
    
   
def read_from_file(filename, binary=False, **open_kwargs): 
    assert "mode" not in open_kwargs # mode is automatically determined by this function
    # TODO - To be added - "limit" argument, to retrieve only part of a file ????????
    
    mode = "R+"
    if binary: 
        mode += "B"
    
    with rsOpen(filename, mode=mode, **open_kwargs) as myfile:

        data_blocks = []
        while True:
            temp = myfile.read()
            if not temp:
                break
            data_blocks.append(temp)
            
        if binary: joiner = ""
        else: joiner = u""   
            
        return joiner.join(data_blocks)
    
    
    
if __name__ == '__main__':
    monkey_patch_original_io_module()
    
    """
    a = io.rsOpen("@TESTER", "w+b")
    with a.lock_file():
       print "yooow"    
    a.close()
    """
        
        
#contract.checkmod(module) 	   # UNCOMMENT THIS TO ACTIVATE CONTRACT CHECKING    







    








