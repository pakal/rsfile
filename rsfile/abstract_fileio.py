#-*- coding: utf-8 -*-

import sys, os, time, threading, multiprocessing, collections, functools
from contextlib import contextmanager
import io
from io import RawIOBase
import rsfile_defines as defs



    
class ThreadSafeWrapper(object):
    """A quick wrapper, to ensure thread safety !
    If a threading or multiprocessing mutex is provided, it will be used for locking,
    else a default threading.RLock instance gets created."""
    def __init__(self, wrapped_obj, interprocess=False, mutex=None):
        self.wrapped_obj = wrapped_obj
        self.interprocess = interprocess
        
        if mutex is not None:
            self.mutex = mutex
        else:
            if interprocess:
                self.mutex = multiprocessing.RLock()
            else:
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
    
    # TODO - MAKE THIS STUFF PICKLABLE !!





class IntraProcessLockRegistry(object):
    
    _original_pid = os.getpid()
    
    # keys : file uid
    # values : event + (list of locked ranges [handle, shared, start, end] where end=None means 'infinity') + attached data
    _lock_registry = {} 
    
    mutex = threading.RLock()
    
    @classmethod
    def _check_forking(cls):
        # unprotected method - beware
        
        # reset is required only when the current thread has just forked !
        # we've then lost all locks in the forking, so just flush the registry
        
        if os.getpid() != cls._original_pid:
            cls._lock_registry = {}
            cls._original_pid = os.getpid()
    
    
    @classmethod
    def _ensure_entry_exists(cls, uid, create=False):
        """
        Returns True iff the entry existed before the call.
        """
        if cls._lock_registry.has_key(uid):
            return True
        else:
            if create:
                cls._lock_registry[uid] = [threading.Condition(cls.mutex), [], []]  # [condition, locks, data]       
            return False
            
            
    @classmethod
    def _try_locking_range(cls, uid, new_handle, new_length, new_start, new_shared):
        # unprotected method - beware
        
        new_end = (new_start+new_length) if new_length else None # None -> infinity
        
        if cls._ensure_entry_exists(uid, create=True):
            
            for (handle, shared, start, end) in cls._lock_registry[uid][1]:
                
                if handle != new_handle and shared == new_shared== True:
                    continue # there won't be problems with shared locks from different file handles 
                
                max_start = max(start, new_start)
                
                min_end = end
                if min_end is None or (new_end is not None and new_end < min_end):
                    min_end = new_end
                
                if min_end is None or max_start < min_end: # areas are overlapping
                    if handle == new_handle:
                        raise RuntimeError("Same area of file locked twice by the same file descriptor")
                    else:
                        return False

        cls._lock_registry[uid][1].append((new_handle, new_shared, new_start, new_end)) # we register as owner of this lock inside this process
        return True # no badly overlapping range was found
    
 
    @classmethod
    def _try_unlocking_range(cls, uid, new_handle, new_length, new_start):    
        """
        Retursn True if there are not locks left for that uid
        """
        
        # unprotected method - beware
        if not cls._ensure_entry_exists(uid, create=False):
            return True
        
        new_end = (new_start+new_length) if new_length else None # None -> infinity
        locks = cls._lock_registry[uid][1]
        for index, (handle, shared, start, end) in enumerate(locks):
            if (handle == new_handle and start == new_start and end == new_end):
                del locks[index]
                if not locks:
                    return True
                else:
                    cls._lock_registry[uid][0].notify() # we awake potential waiters
                    return False
      
        # no matching lock was found
        raise RuntimeError("Trying to unlock a file area not owned by this handle")
            
    
    @classmethod
    def register_file_lock(cls, uid, handle, length, offset, blocking, shared):
        with cls.mutex:
            
            cls._check_forking()
            
            # we handle both blocking and non-blocking locks there
            res = False
            while not res:
                res = cls._try_locking_range(uid, handle, length, offset, shared)
                if res or not blocking:
                    break
                else:
                    cls._lock_registry[uid][0].wait() # we wait on the condition until locks get removed
 
            return res
              
              
    @classmethod
    def unregister_file_lock(cls, uid, handle, length, offset):  
        with cls.mutex:  
            
            cls._check_forking()
            
            return cls._try_unlocking_range(uid, handle, length, offset)


    @classmethod
    def remove_file_locks(cls, uid, new_handle):
        with cls.mutex:  
            
            cls._check_forking()
            
            if not cls._ensure_entry_exists(uid, create=False):
                return []
            
            removed_locks = []
            remaining_locks = []
            for record in cls._lock_registry[uid][1]:
                if record[0] == new_handle:
                    removed_locks.append(record)
                else:
                    remaining_locks.append(record)
                    
            cls._lock_registry[uid][1] = remaining_locks
            
            return removed_locks


    @classmethod
    def delete_uid_entry(cls, uid):
        """
        Returns True iff there was well a structure to delete.
        Raise RuntimeError if locks or data were remaining for this uid.
        """
        with cls.mutex:  
            
            cls._check_forking()
            
            if not cls._ensure_entry_exists(uid, create=False):
                return False
            else:
                if cls._lock_registry[uid][1] or cls._lock_registry[uid][2]:
                    raise RuntimeError("Trying to delete a lock registry structure with locks/data remaining.")
                del cls._lock_registry[uid]
                return True
        
    @classmethod
    def add_uid_data(cls, uid, data):
        with cls.mutex:  
            
            cls._check_forking()
            
            cls._ensure_entry_exists(uid, create=True)
            cls._lock_registry[uid][2].append(data)
                
    @classmethod
    def remove_uid_data(cls, uid):
        with cls.mutex:  
            
            cls._check_forking()
            
            if cls._ensure_entry_exists(uid, create=False):
                data = cls._lock_registry[uid][2]
                cls._lock_registry[uid][2] = []
                return data
            else:
                return []
                
    @classmethod
    def uid_has_locks(cls, uid):
        with cls.mutex:  
            
            cls._check_forking()        
            
            if cls._lock_registry.has_key(uid) and cls._lock_registry[1]:
                return True
            else:
                return False
        
        
        
        
        
class AbstractFileIO(RawIOBase):  
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
        
        
        # variables to determine future write/read operations 
        self._seekable = True
        self._readable = read
        self._writable = write # 'append' enforced the value of 'write' to True, just above
        self._append = append
        
        self._synchronized = synchronized
        self._inheritable = inheritable
        self._hidden = hidden # TO BE REMOVED - DEPRECATED
    

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
        
        
        self._uid = None # unique identifier of the file, eg. (device, inode) pair
        self._fileno = None # C style file descriptor, might be created only on request
        self._handle = None # native platform handle other than fileno - if existing
        self._closefd = closefd        
        
        # These two keys are used to identify the file and handle near the intra process lock registry
        self._lock_registry_inode = None
        self._lock_registry_descriptor = None
        
        self._inner_create_streams(**kwargs)

        if append:
            self.seek(0, os.SEEK_END) # required by unit tests...      

            
    def close(self):
        with self._multi_syscall_lock: # we must avoid having several threads entering this

            if not self.closed:
                
                RawIOBase.close(self) # we first mark the stream as closed... it flushes, also.

                # Unlock-On-Close and fcntl() safety mechanisms
                with IntraProcessLockRegistry.mutex:
                    
                    for (handle, shared, start, end) in IntraProcessLockRegistry.remove_file_locks(self._lock_registry_inode, self._lock_registry_descriptor):
                        #print ">>>>>>>> ", (handle, shared, start, end)
                        length = None if end is None else (end-start)
                        self._inner_file_unlock(length, start)
                    
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
        if self._uid is not None:
            return self._uid
        else:
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
        
        if not isinstance(offset, (int, long)):
            raise TypeError("Expecting an integer as argument for seek")
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
        
        if not isinstance(buffer, (bytes, bytearray)):
            raise TypeError("Only buffer-like objects can be written to raw files, not %s objects" % type(buffer))
                
        return self._inner_write(buffer)

    def truncate(self, size=None, zero_fill=True):
        """
        TODO PAKAL - what about file pointers ? -> we must change them to new bhevaiour !!!
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
    def _lock_remover(self, length, offset, whence):
        # we do nothing on __enter__()
        yield
        # we unlock on __exit__()
        self.unlock_file(length=length, offset=offset, whence=whence) 
    
    def lock_file(self, timeout=None, length=None, offset=0, whence=os.SEEK_SET, shared=None):
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
        
        if shared is None:
            if self._writable:
                shared = False
            else:
                shared = True
        
        if not shared and not self._writable:
            raise IOError("Can't obtain exclusive lock on non-writable stream") # TODO - improve this exception
        
        # TODO - PYCONTRACT THIS !!!

        
        abs_offset = self._convert_relative_offset_to_absolute(offset, whence)      
        blocking = timeout is None
        
        start_time = time.time()
        def check_timeout(env_error):
            """
            If the timeout has expired, raises the exception given as parameter.
            Else, sleeps for a short period.
            """
        
            if not blocking: # else, we try again indefinitely
                delay = time.time() - start_time
                if(delay >= timeout): # else, we try again until success or timeout
                    (error_code, title) = e.args
                    filename = getattr(self, 'name', 'Unkown File') # to be improved
                    raise defs.LockingException(error_code, title, filename)
            
            time.sleep(1) # TODO - PAKAL - make this use global parameters !
            

        success = False

        while(not success):     
        
        
                # STEP ONE : acquiring ownership on the lock inside current process
                res = IntraProcessLockRegistry.register_file_lock(self._lock_registry_inode, self._lock_registry_descriptor, length, abs_offset, blocking, shared)
                if not res:
                    check_timeout(IOError(100, "Current process has already locked this byte range")) # TODO CHANGE errno.EPERM
                try:
                    
                    while(not success): 
                        
                        # STEP TWO : acquiring the lock for real, at kernel level
                        try:
                            
                            #import multiprocessing
                            #print "---------->", multiprocessing.current_process().name, " LOCKED ", (operation, length, abs_offset, os.SEEK_SET)
                            
                            self._inner_file_lock(length=length, abs_offset=abs_offset, blocking=blocking, shared=shared) 
                            
                            success = True # we leave the two loops
                            
                        except EnvironmentError, e:
                            check_timeout(e)

                finally:
                    if not success:
                        res = IntraProcessLockRegistry.unregister_file_lock(self._lock_registry_inode, self._lock_registry_descriptor, length, abs_offset)
                        assert res # there shall be no problem, since arguments MUST be valid there                        

        return self._lock_remover(length, abs_offset, os.SEEK_SET)     
        

    
    def unlock_file(self, length=None, offset=0, whence=os.SEEK_SET):
        """Unlocks a file portion previously locked by the same process. 
        
        The specifications of the locked area (absolute offset and length) must be the same as those used when calling locking methods,
        else errors will occur; its is thus not possible to release only a part of a locked area, or to unlock with only one call
        two consecutive parts (well, posix locks allow it, but for portability's sake you had better not count on it ??? TRUE ??)
        
        ??? PAKAL - TELL ABOUT EXCEPTIONS THERE
        """  
        
        #import multiprocessing
        #print "---------->", multiprocessing.current_process().name, " UNLOCKED ", (unix.LOCK_UN, length, abs_offset, os.SEEK_SET)
        abs_offset = self._convert_relative_offset_to_absolute(offset, whence) 
        
        with IntraProcessLockRegistry.mutex: # IMPORTANT - keep the registry lock during the whole operation
            IntraProcessLockRegistry.unregister_file_lock(self._lock_registry_inode, self._lock_registry_descriptor, length, abs_offset)
            self._inner_file_unlock(length, abs_offset)
        
    
    
        

    def _convert_relative_offset_to_absolute(self, offset, whence):
        
        if whence == os.SEEK_SET:
            abs_offset = offset
        elif whence == os.SEEK_CUR:
            abs_offset = self._inner_tell() + offset
        else:
            abs_offset = self._inner_size() + offset
        
        return abs_offset
    
    
 
 
 
        
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

    """
    def _inner_register_file_lock(self, length, abs_offset, blocking, shared):
        self._unsupported("register_file_lock")

    def _inner_unregister_file_lock(self, length, abs_offset):
        self._unsupported("unregister_file_lock")
    """
    
    def _inner_file_lock(self, length, abs_offset, blocking, shared):
        self._unsupported("file_lock")

    def _inner_file_unlock(self, length, abs_offset):
        self._unsupported("file_unlock")

        
        