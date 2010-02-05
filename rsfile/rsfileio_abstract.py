#-*- coding: utf-8 -*-

import sys, os, time, threading, multiprocessing, collections, functools
from contextlib import contextmanager
import io
from io import RawIOBase
import rsfile_definitions as defs
from rsfile_registries import IntraProcessLockRegistry






class RSFileIO(RawIOBase):  # we're forced to use this name, because of autodocumentation constraints...
    """
    This class is an improved version of :class:`io.FileIO`, relying on native OS primitives, 
    and offering much more control over the behaviour of the file stream.
    
    """
    
    
    def __init__(self,
                 path=None, # it seems pywin32 already uses unicode versions of these functions, so it's cool  :-)
                 fileno=None, 
                 handle=None, 
                 closefd=True,
                 
                 read=False, 
                 write=False, append=False,  # writing to a file in append mode AUTOMATICALLY moves the file pointer to EOF # PAKAL -A TESTER
                 
                 must_exist=False, must_not_exist=False, # only used on file opening
                 synchronized=False,
                 inheritable=False,
                 permissions=0777
                 ):


        """
        This constructor exhibits the whole sets of functions offered by 
        :class:`RSFileIO` instances.
        
        Hopefully you won't have to deal with it, anyway, since factory 
        functions like :func:`rsOpen` give you a way easier access to 
        streams chain, including buffering and encoding aspects.
        
        The file must necessarily be opened at least with read or write access,
        and can naturally be opened with both.
        
        **Target determination parameters**
        
        These parameters determine if a new raw file stream will be opened from the filesystem, or
        if an existing one will be wrapped by the new RSFileIo instance.
        
        - *path* (unicode/bytes or None): The path of the regular file to be opened. 
          If ``fileno`` or ``handle`` is provided, ``path`` is only used as additional 
          information. 
        - *fileno* (integer or None): if provided, it must be an open C-style file
          descriptor, compatible with the *Mode parameters* requested, and which will be used
          as an underlying raw stream. Such file descriptors should be available on all platforms,
          but on windows (where they are only emulated) they might be too buggy to benefit 
          from file locking and other advanced features.
        - *handle* (handle or None): if provided, it must be a native open file
          handle, compatible with the *Mode parameters* requested, and which will be used
          as an underlying raw stream. On unix platforms, it is the same as a ``fileno``, 
          and on windows it must be a win32 handle (an integer) or a pyHandle instance from pywin32.
        - *closefd* (boolean): if ``fileno`` or ``handle``, this parameter determines whether or not
          the wrapped raw file stream will be closed when the instance will be closed or deleted, or if
          it will be left open. When creating a new rew file stream from ``path``, ``closefd`` must 
          necessarily be True.
        
        
        **Mode parameters**
        
        These parameters determine the access checking that will be done while manipulating
        the stream.
        
        - *read* (boolean) : Open the file with read access (file truncation is not allowed).
        - *write* (boolean) : Open the file with write access (file truncation is allowed).
        - *append* (boolean) : Open the file in append mode, i.e all write operations
          will automatically move the file pointer to the end of file 
          before actually writing (the file pointer is not restored 
          afterwards). ``append`` implicitly forces ``write`` to *True*.
        
        
        **File creation parameters**
        
        These parameters are only taken in account when creating a new raw stream, 
        not wrapping an existing fileno or handle. 
        
        - *must_exist* (boolean): File creation fails if the file doesn't exist. 
          This is then negation of the O_CREATE semantic, which is the default behaviour
          of file opening via RSFileIo (i.e, files are created if not existing, else they're 
          simply opened).
        - *must_not_exist* (boolean): File opening fails if the file already exists.
          This is the same semantic as (O_CREATE | O_EXCL) flags, which can be used to
          handle some security issues on unix filesystems.
        - *synchronized* (boolean): Opens the stream so that write operations don't return before
          data gets pushed to physical device. Note that due to potential caching in your HDD, it 
          doesn't fully guarantee that your data will be safe in case of immediate crash.        
        - *inheritable* (boolean): If True, the raw file stream will be inheritable by child processes,
          at least those created via native subprocessing calls (spawn, fork+exec, CreateProcess...). 
          Note that streams are always "inheritable" by fork (no close-on-fork semantic is widespread). 
          Child processes must anyway be aware of the file streams they own, which can be
          done through command-line arguments or other IPC means.
        - *permissions* (integer): this shall be a valid combination of :mod:`stat` permission flags, 
          which will be taken into only when creating a new file, to set its permission flags (on unix, 
          the umask will be applied on these permissions first).
                     
          On windows, only the "user-write" flag is meaningful, its absence corresponding to a 
          read-only file (note that contrary to unix, windows folders always behave as 
          if they had a "sticky bit", so read-only files can't be moved/deleted).
          
          These permissions have no influence on the ``mode parameters`` of the new stream - you can very well
          open in read-write mode a new file, giving it no permissions at all.

        
        
        
        Needless to say that having both *must_exist* and *must_not_exist* set to True might
        irritate logical circuits of the __init__() method, and that creating a synchronized 
        read-only stream is of little interest. ^^

        pre::
            path is None or isinstance(path, basetring)  # if specified
            not (fileno and handle)
            closefd or (fileno or handle) 
            
            read or write or append
            not (must_exist and must_not_exist)
            # we don't care about other parameters, as these are independant boolean flags
        post::
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
        
        if not path and fileno is None and handle is None: 
            print "##################", locals()
            raise ValueError("File must provide at least path, fileno or handle value")
        
        if not read and not write:
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
        """""" # todo, deal with problems here, and with name property !!
        return self._path    

    @property 
    def closefd(self): # WARNING - NOT REQUIRED BY IO SPECS !!!
        return self._closefd
        

        
    # # # Methods that must be overriden in OS-specific file types # # #    

    def fileno(self):
        self._checkClosed()
        return self._inner_fileno()

    def handle(self):
        """Returns the native file handle associated with the stream.
        On most systems, it's the same as fileno, but on win32 it's a specific Handle value.
        """
        self._checkClosed()
        return self._inner_handle()  
    
    def uid(self):
        """Returns a (device, inode) tuple, identifying unambiguously the node (disk file) 
        targeted by the stream. Thus, several file objects refer to the same disk file if 
        and only if they have the same uid.
    
        Raises IOError if it is impossible to retrieve this information (network or virtual filesystems, etc.)
        
        Nota : the file path can't be used as an unique identifier, since it is often possible to delete/recreate 
        a file, while streams born from that path are still in use.  
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
            pass # WARNING - todo - fix stlib test suite first !!! raise TypeError("Only buffer-like objects can be written to raw files, not %s objects" % type(buffer))
                
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
                    old_pos = self._inner_tell()
                    self._inner_seek(current_size, os.SEEK_SET)
                    bytes_to_write = size - current_size
                    (q, r) = divmod(bytes_to_write, io.DEFAULT_BUFFER_SIZE)

                    for _ in range(q):
                        padding = '\0'*io.DEFAULT_BUFFER_SIZE
                        self._inner_write(padding)
                    self._inner_write('\0'*r)
                    self._inner_seek(old_pos) #important
            return self.size()

    def flush(self):
        pass # that raw stream should have no buffering except the kernel's one, which gets flush by sync calls
    
    def sync(self, metadata=True, full_flush=True):
        """
        Synchronizes file data between kernel cache and physical device. 
        
            If``metadata`` is False, and if the platform supports it (win32 and Mac OS X don't), 
            this sync is a "datasync", i.e only data and file sizes are written to disk, not 
            file times and other metadata (this can improve performance, but also i).
            
            If ``full_flush`` is True, RSFileIO will whenever possible force the flushing of the disk
            cache too
            
            For a constant synchronization between the kernel cache and the disk oxyde, 
            CF the "synchronized" argument of the stream opening.
        """
        self._inner_sync(metadata, full_flush)        





    
    @contextmanager
    def _lock_remover(self, length, offset, whence):
        # we do nothing on __enter__()
        yield
        # we unlock on __exit__()
        self.unlock_file(length=length, offset=offset, whence=whence) 
    
    def lock_file(self, timeout=None, length=None, offset=0, whence=os.SEEK_SET, shared=None):
        
        
        ___ = 222222222222222222222222222222222222222
        """
        Locks the whole file or a portion of it, depending on the arguments provided.
        
        WARNING -> shared = NONE !
        
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
        
        Note that file locking is not reentrant: calling this function several times, on overlapping areas, 
        would result in a deadlock (as with threading.Lock);
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

        WARNING : WIN32 - Locking a portion of a file for shared access denies all 
        processes write access to the specified region of the file, including the 
        process that first locks the region. All processes can read the locked region.
        
        """
        
        if shared is None:
            if self._writable:
                shared = False
            else:
                shared = True
        
        if (shared and not self._readable) or (not shared and not self._writable):
            raise IOError("Can't obtain exclusive lock on non-writable stream, or share lock on non-writable stream.") # TODO - improve this exception
        
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
                    (error_code, title) = env_error.args
                    filename = getattr(self, 'name', 'Unkown File') # to be improved
                    raise defs.LockingException(error_code, title, filename)
            
            time.sleep(1) # TODO - PAKAL - make this use global parameters !
            

        success = False

        while(not success):     
        
    
            # STEP ONE : acquiring ownership on the lock inside current process
            res = IntraProcessLockRegistry.register_file_lock(self._lock_registry_inode, self._lock_registry_descriptor, length, abs_offset, blocking, shared)
            if not res:
                check_timeout(IOError(100, "Current process has already locked this byte range")) # TODO CHANGE errno.EPERM
                continue

            try:
                
                while(not success): 
                    
                    # STEP TWO : acquiring the lock for real, at kernel level
                    try:
                        
                        #import multiprocessing
                        #print "---------->", multiprocessing.current_process().name, " LOCKED ", (length, abs_offset)
                        
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
        
    def _inner_create_streams(self, path, read, write, append, must_exist, must_not_exist, synchronized, inheritable, fileno, handle, closefd, permissions):
        self._unsupported("_inner_create_streams")

    def _inner_close_streams(self):  
        self._unsupported("_inner_close_streams")  

    def _inner_reduce(self, size): 
        self._unsupported("_inner_reduce")  

    def _inner_extend(self, size, zero_fill): 
        self._unsupported("_inner_extend")

    def _inner_sync(self, metadata, full_flush):
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


        
