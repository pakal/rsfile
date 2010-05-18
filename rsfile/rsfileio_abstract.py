#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals

import sys, os, time, threading, multiprocessing, collections, functools
from array import array
from contextlib import contextmanager
import rsfile_definitions as defs
from rsfile_registries import IntraProcessLockRegistry, _default_rsfile_options




class RSFileIOAbstract(defs.io_module.RawIOBase):

    
    
    def __init__(self,
                 path=None, # it seems pywin32 already uses unicode versions of these functions, so it's cool  :-)
                 fileno=None, 
                 handle=None, 
                 closefd=True,
                 
                 read=False, 
                 write=False, append=False,  # writing to a file in append mode AUTOMATICALLY moves the file pointer to EOF # PAKAL -A TESTER
                 
                 must_create=False, must_not_create=False,# only used on file opening
                 
                 synchronized=False,
                 inheritable=False,
                 permissions=0777
                 ):

        """
        
        This class is an improved version of the raw stream :class:`io.FileIO`, relying on native OS primitives, 
        and offering much more control over the behaviour of the file stream.
        
        Hopefully you won't have to deal directly with its constructor, since factory 
        functions like :func:`rsopen` give you a much easier access to 
        streams chain, including buffering and encoding aspects.
        
    
        
        .. rubric::
            Target determination parameters
        
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
        
        
        .. rubric::
            Mode parameters
        
        These parameters determine the access checking that will be done while manipulating
        the stream. The file must necessarily be opened at least with read or write access,
        and can naturally be opened with both.
        
        - *read* (boolean): Open the file with read access (file truncation is not allowed).
        - *write* (boolean): Open the file with write access (file truncation is allowed).
        - *append* (boolean): Open the file in append mode, i.e all write operations
          will automatically move the file pointer to the end of file 
          before actually writing (the file pointer is not restored 
          afterwards). ``append`` implicitly forces ``write`` to *True*.
        
        
        .. rubric::
            File creation parameters
        
        These parameters are only taken in account when creating a new raw stream, 
        not wrapping an existing fileno or handle. 
        
        - *must_create* (boolean): File opening fails if the file already exists.
          This is the same semantic as (O_CREATE | O_EXCL) flags, which can be used to
          handle some security issues on unix filesystems. Note that O_EXCL is broken
          on NFS shares with a linux kernel < 2.6.5, so race conditions may occur in this case.        
        - *must_not_create* (boolean): File creation fails if the file doesn't already exist. 
          This is then negation of the O_CREATE semantic, which is the default behaviour
          of file opening via RSFileIo (i.e, files are created if not existing, else they're 
          simply opened).
        - *synchronized* (boolean): Opens the stream so that write operations don't return before
          data gets pushed to physical device. Note that due to potential caching in your HDD, it 
          doesn't fully guarantee that your data will be safe in case of immediate crash. Using this 
          flag for programs running on laptops might increase HDD power consumption, and thus reduce
          battery life.
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

        """
        
        self.enforced_locking_timeout_value = _default_rsfile_options["enforced_locking_timeout_value"]
        self.default_spinlock_delay = _default_rsfile_options["default_spinlock_delay"]


        # Preliminary normalization
        if append: 
            write = True # append implies write
        
        # we retrieve the dict of provided arguments, except self
        kwargs = locals()
        del kwargs["self"]
        del kwargs["closefd"] # not needed at inner level
        


        # HERE WE CHECK EVERYTHING !!! PAKAL
        
        if path is not None and not isinstance(path, (bytes, unicode)):
            raise ValueError("If provided, path must be a string.")
                
        if bool(path) + (fileno is not None) + (handle is not None) != 1: 
            #print ("##################", locals())
            raise ValueError("File must provide path, fileno or handle value, and only one of these.")
            
        if not read and not write:
            raise ValueError("File must be opened at least in 'read', 'write' or 'append' mode.")

        if must_create and must_not_create :
            raise ValueError("File can't be wanted both existing and unexisting.")

        if not closefd and not (fileno or handle):
            raise ValueError("Cannot use closefd=False without providing a descriptor to wrap.")
        
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
        if path is not None:
            self._name = path
            self._origin = "path"
        elif fileno is not None:
            if int(fileno) < 0:
                raise ValueError("A fileno to be wrapped can't be negative.")
            self._name = fileno
            self._origin = "fileno"
        elif handle is not None:
            if int(handle) < 0:
                raise ValueError("A handle to be wrapped can't be negative.")
            self._name = handle
            self._origin = "handle"
     
  
        """ Aborted - don't mix stream and filesystem methods !!
        self._path = None
        if isinstance(path, basestring):
            try: 
                self._path = os.path.normcase(os.path.normpath(os.path.realpath(path)))
            except EnvironmentError: # weirdo path, just make it absolue...
                self._path = os.path.abspath(path)
        """
        
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
        
        with self._multi_syscall_lock: # we must avoid having several threads entering this # TODO - remove lock

            if not self.closed:
                
                defs.io_module.RawIOBase.close(self) # we first mark the stream as closed... it flushes, also.

                # Unlock-On-Close and fcntl() safety mechanisms
                with IntraProcessLockRegistry.mutex:
                    
                    for (handle, shared, start, end) in IntraProcessLockRegistry.remove_file_locks(self._lock_registry_inode, self._lock_registry_descriptor):
                        #print (">>>>>>>> ", (handle, shared, start, end))
                        length = None if end is None else (end-start)
                        self._inner_file_unlock(length, start)
                    
                    self._inner_close_streams()


    def __del__(self):
        """Destructor.  Calls close()."""
        # The try/except block is in case this is called at program
        # exit time, when it's possible that globals have already been
        # deleted, and then the close() call might fail.  Since
        # there's nothing we can do about such failures and they annoy
        # the end users, we suppress the traceback.
        try:
            self.close()
        except:
            pass


    def seekable(self):
        self._checkClosed()
        return self._seekable
    def readable(self):
        self._checkClosed()
        return self._readable
    def writable(self):
        self._checkClosed()
        return self._writable
    
    
    
    # # # Read-only Attributes # # #
    

    @property 
    def mode(self):  # TODO - improve this
        """
        At the moment, this property behaves like its sibling from the stdlib io module, 
        i.e it computes and returns one of "rb", "wb" and "rb+" for binary streams, 
        and the actual opening mode for text streams. This might change in the future.
        """
        # we mimic the _fileio.c implementation, that's weird but well...
        if self.readable():
            return "rb+" if self.writable() else "rb"
        else:
            return "wb"    

    @property
    def name(self):  
        """
        Contains the path, fileno, or handle of the stream, 
        depending on the way the stream was created.
        To interpret this attribute, refer to the :attr:`origin` property.
        """
        return self._name    

    @property
    def origin(self):  
        """Returns a string indicating the origin of the stream, 
        as well as the meaning of its :attr:`name`.
        Possible values are 'path', 'fileno' and 'handle'."""
        return self._origin    

    @property 
    def closefd(self): # WARNING - NOT REQUIRED BY IO SPECS !!!
        return self._closefd
        

        
    # # # Methods that must be overridden in OS-specific file types # # #    

    def fileno(self):
        self._checkClosed()
        return self._inner_fileno()

    def handle(self):
        self._checkClosed()
        return self._inner_handle()  
    
    def uid(self):
        self._checkClosed()
        if self._uid is not None:
            return self._uid
        else:
            return self._inner_uid()
    
    def times(self):
        self._checkClosed()
        return self._inner_times()
        
    def size(self): # non standard method    
        self._checkClosed()
        return self._inner_size()

    def tell(self):
        self._checkClosed()
        res = self._inner_tell()
        return res

    def seek(self, offset, whence=os.SEEK_SET):
        self._checkClosed()
        
        #print ("raw seek called to offset ", offset, " - ", whence, "with size", self._inner_size())
        if not isinstance(offset, (int, long)):
            raise TypeError("Expecting an integer as argument for seek")
        res = self._inner_seek(offset, whence)
        
        return res
        

    def readall(self):
        """Reads until EOF, using multiple read() calls.
      
        No limit is set on the amount of data read, so you might
        fill up your RAM with this method.
        
        """ # Beware - TODO - TO BE OPTIMIZED AND SENT TO RSIOBASE !!!
        res = bytearray()
        while True:
            data = self.read(defs.DEFAULT_BUFFER_SIZE)
            if not data:
                break
            res += data
        return bytes(res)
    
            
    def read(self, n = -1): 
        """Reads and returns up to n bytes (a negative value for n means *infinity*).

        Returns an empty bytes object on EOF, or None if the object is
        set not to block and has no data to read.
        """
        # PAKAL - to be checked !!!!
        if n is None:
            n = -1
        if n < 0:
            return self.readall() # PAKAL - TODO - REMOVE THIS, we SAID ONE system call !!!!
        b = bytearray(n.__index__())
        n = self.readinto(b)
        del b[n:]
        return bytes(b)        
        
        ## NOOOO <inherited> - read() uses readinto() to do its job !
        # PAKAL - TODO - allow overriding of an _inner_read method !!!!!!!!!!!!!!
    
    
    def readinto(self, buffer):
        """Reads up to len(b) bytes into b.

        Returns number of bytes read (0 for EOF), or None if the object
        is set not to block as has no data to read.
        """
        self._checkClosed()
        self._checkReadable()
        return self._inner_readinto(buffer)


    def write(self, buffer):
        """Writes the given buffer data to the IO stream.

        Returns the number of bytes written, which may be less than len(b).
        
        """
        
        self._checkClosed()
        self._checkWritable()

        if isinstance(buffer, unicode):
            raise TypeError("can't write unicode to binary stream")
        
        if defs.HAS_MEMORYVIEW and isinstance(buffer, memoryview):
            buffer = buffer.tobytes() # TO BE IMPROVED - try to avoid copies !!
        elif isinstance(buffer, array):
            buffer = buffer.tostring() # To be improved hell a lot...
        
        
        if not isinstance(buffer, (bytes, bytearray)):
            pass # WARNING - todo - fix stlib test suite first !!! raise TypeError("Only buffer-like objects can be written to raw files, not %s objects" % type(buffer))
        
        res = self._inner_write(buffer)
        #assert res == len(buffer), str(res, len(buffer)) # NOOO - we might have less than that actually if disk full !
        
        if not res and len(buffer): 
            # weird, no error detected but no bytes written...
            raise IOError("Unknown error, no bytes could be written to the device.")
        
        if res <0 or res > len(buffer):
            raise RuntimeError("Madness - %d bytes written instead of max %d for buffer '%r'" %(res, len(buffer), buffer))
    
        return res


    def truncate(self, size=None, zero_fill=True):
        """
        Truncates the file to the given size (or the current position), without moving the file pointer.
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
                    (q, r) = divmod(bytes_to_write, defs.DEFAULT_BUFFER_SIZE)

                    for _ in range(q):
                        padding = b'\0'*defs.DEFAULT_BUFFER_SIZE
                        self._inner_write(padding)
                    self._inner_write(b'\0'*r)
                    self._inner_seek(old_pos) #important
            return self.size()

    def flush(self):
        """
        Flushes read and/or write buffers, if applicable.
        
        These operations ensure that all bytes written get pushed 
        at least from the application to the kernel I/O cache, and
        that the file pointer of underlying low level stream becomes 
        the same as the 'virtual' file position returned by tell().
        
        Returns None.
        """
        self._checkClosed() # that raw stream should have no buffering except the kernel's one, which gets flushed by sync calls
    
    def sync(self, metadata=True, full_flush=True):
        """Synchronizes file data between kernel cache and physical device. 
        
        If ``metadata`` is False, and if the platform supports it (win32 and Mac OS X don't), 
        this sync is a "datasync", i.e only data and file sizes are written to disk, not 
        file times and other metadata (this can improve performance, but also i).
        
        If ``full_flush`` is True, RSFileIO will whenever possible force the flushing of device
        cache too.
        
        For a constant synchronization between the kernel cache and the disk oxyde, 
        CF the "synchronized" argument at stream opening.
        
        Raises an IOError if no sync operation is available for the stream.
        No return value is expected.
        """
        self._checkClosed()
        self._inner_sync(metadata, full_flush)        



    def _convert_relative_offset_to_absolute(self, offset, whence):
        
        if offset is None:
            offset = 0
            
        if whence == os.SEEK_SET:
            abs_offset = offset
        elif whence == os.SEEK_CUR:
            abs_offset = self._inner_tell() + offset
        else:
            abs_offset = self._inner_size() + offset
        
        return abs_offset
    
    @contextmanager
    def _lock_remover(self, length, offset, whence):
        # we do nothing on __enter__()
        yield
        # we unlock on __exit__()
        self.unlock_file(length=length, offset=offset, whence=whence) 
    
    def lock_file(self, timeout=None, length=None, offset=None, whence=os.SEEK_SET, shared=None):
        
        self._checkClosed()
        
        if timeout is not None and (not isinstance(timeout, (int, long, float)) or timeout<0):
            raise ValueError("timeout must be None or positive float.")

        if length is not None and (not isinstance(length, (int, long)) or length<0):
            raise ValueError("length must be None or positive integer.")        
        
        if offset is not None and not isinstance(offset, (int, long)):
            raise ValueError("offset must be None or an integer.") 
        
        if whence not in defs.SEEK_VALUES:
            raise ValueError("whence must be a valid SEEK_\* value") 
            
        if shared is not None and shared not in (True, False):
            raise ValueError("shared must be None or True/False.")        
        
        
        
        if shared is None:
            if self._writable:
                shared = False
            else:
                shared = True
        
        if (shared and not self._readable) or (not shared and not self._writable):
            raise IOError("Can't obtain exclusive lock on non-writable stream, or share lock on non-writable stream.") # TODO - improve this exception
        
        abs_offset = self._convert_relative_offset_to_absolute(offset, whence)      
        blocking = timeout is None # here, it means "forever waiting for the lock"
        low_level_blocking = blocking if (self.enforced_locking_timeout_value is None) else False # we enforce spin-locking if a global timeout exists

        start_time = time.time()
        def check_timeout(env_error):
            """
            If timeout has expired, raises the exception given as parameter.
            Else, sleeps for a short period.
            """
            delay = time.time() - start_time
            if not blocking: # we have a timeout set
                
                if(delay >= timeout): # else, we try again until success or timeout
                    (error_code, title) = env_error.args
                    filename = getattr(self, 'name', 'Unkown File') # to be improved
                    raise defs.LockingException(error_code, title, filename)
            
            elif (self.enforced_locking_timeout_value is not None) and (delay >= self.enforced_locking_timeout_value): # for blocking attempts only
                raise RuntimeError("Locking delay exceeded 'enforced_locking_timeout_value' option (%d s)." % self.enforced_locking_timeout_value)
            
            time.sleep(self.default_spinlock_delay)
            

        success = False

        while(not success):     
        
            # STEP ONE : acquiring ownership on the lock inside current process
            res = IntraProcessLockRegistry.register_file_lock(self._lock_registry_inode, self._lock_registry_descriptor, 
                                                              length, abs_offset, low_level_blocking, shared, self.enforced_locking_timeout_value)

            if not res:
                check_timeout(IOError(100, "Current process has already locked this byte range")) # TODO CHANGE errno.EPERM
                continue

            try:
                
                while(not success): 
   
                    # STEP TWO : acquiring the lock for real, at kernel level
                    try:
                        
                        #import multiprocessing
                        #print ("---------->", multiprocessing.current_process().name, " LOCKED ", (length, abs_offset))
                        
                        self._inner_file_lock(length=length, abs_offset=abs_offset, blocking=low_level_blocking, shared=shared) 
                        
                        success = True # we leave the two loops
                        
                    except EnvironmentError, e:
                        check_timeout(e)

            finally:
                if not success:
                    res = IntraProcessLockRegistry.unregister_file_lock(self._lock_registry_inode, self._lock_registry_descriptor, length, abs_offset)
                    assert res # there shall be no problem, since arguments MUST be valid there                        

        return self._lock_remover(length, abs_offset, os.SEEK_SET)     
        


    def unlock_file(self, length=None, offset=0, whence=os.SEEK_SET):
    
        self._checkClosed()
        
        if length is not None and (not isinstance(length, (int, long)) or length<0):
            raise ValueError("length must be None or positive integer.")        
        
        if offset is not None and (not isinstance(offset, (int, long)) or offset<0):
            raise ValueError("offset must be None or positive integer.") 
        
        if whence not in defs.SEEK_VALUES:
            raise ValueError("whence must be a valid SEEK_\* value") 
        
        
        #import multiprocessing
        #print ("---------->", multiprocessing.current_process().name, " UNLOCKED ", (unix.LOCK_UN, length, abs_offset, os.SEEK_SET))
        abs_offset = self._convert_relative_offset_to_absolute(offset, whence) 
        
        with IntraProcessLockRegistry.mutex: # IMPORTANT - keep the registry lock during the whole operation
            IntraProcessLockRegistry.unregister_file_lock(self._lock_registry_inode, self._lock_registry_descriptor, length, abs_offset)
            self._inner_file_unlock(length, abs_offset)
        
    
        
    # # Private methods - no check is made on their argument or the file object state ! # #
        
    def _inner_create_streams(self, path, read, write, append, must_create, must_not_create, synchronized, inheritable, fileno, handle, closefd, permissions):
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
        self._unsupported("fileno")

    def _inner_handle(self):
        self._unsupported("handle") 

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
    
    def _inner_file_lock(self, length, abs_offset, blocking, shared):
        self._unsupported("file_lock")

    def _inner_file_unlock(self, length, abs_offset):
        self._unsupported("file_unlock")

defs.io_module.RawIOBase.register(RSFileIOAbstract)

        
