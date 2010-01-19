#-*- coding: utf-8 -*-

import sys, os, functools, errno, time, threading
from abstract_fileio import AbstractFileIO
import rsfile_defines as defs


try:
    import rsbackends.unix_stdlib as unix
except ImportError:
    import rsbackends.unix_ctypes as unix
        

class lock_registry(object):
    
    _original_pid = os.getpid()
    
class lock_registry(object):
    
    _original_pid = os.getpid()
    
    # keys : file uid
    # values : event + list of locked ranges [fd, exclusive, start, end] where end=None means 'infinity'
    _lock_registry = {} 
    
    mutex = threading.lock()
    
    @classmethod
    def _reset_registry(cls):
        # unprotected method - beware
        # required only when the current thread has just forked !
        # we've lost all locks in the process, so just close pending file descriptors
        for fd in cls._lock_registry.keys():
            os.close(fd)
        cls._lock_registry = {}
        cls._original_pid = os.getpid()
    
    @classmethod
    def _can_lock_range(cls, uid, new_fd, new_exclusive, new_start, new_length, blocking):
        # unprotected method - beware
        if not cls._lock_registry.has_key(uid):
            cls._lock_registry[uid] = (threading.Condition(cls.mutex), [])
        
        new_end = (start+length) if length else None # None -> infinity
        for (fd, exclusive, start, end) in cls._lock_registry[uid][1]:
            
            if
            max_start = max(start, new_start)
            
            min_end = end
            if min_end is None or (new_end is not None and new_end<min_end):
                min_end = new_end
            
            if min_end is None or max_start < min_end: # areas are overlapping
        
    @classmethod
    def lock_file(cls, fd, operation, offset, length):
        with cls.mutex:
            if os.getpid() != cls._original_pid:
                cls._reset_registry()
            
            stats = unix.fstat(fd)
            uid = (stats.st_dev, stats.st_ino)
            
    



class unixFileIO(AbstractFileIO):      

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
        
        
    # Warning - this is to be used as a static method ! #
    def _unix_error_converter(f): #@NoSelf
        @functools.wraps(f)
        def wrapper(self, *args, **kwds):
            try:
                return f(self, *args, **kwds)
            except unix.error, e: # WARNING - this is not a subclass of OSERROR !!!!!!!!!!!!!
                if isinstance(e, IOError):
                    raise
                else:
                    traceback = sys.exc_info()[2]
                    #print repr(e)str(e[1])+" - "+str(e[2
                    raise IOError(e[0], str(e[1]), str(self._name)), None, traceback
        return wrapper
        
        
    # # Private methods - no check is made on their argument or the file object state ! # #
    @_unix_error_converter
    def _inner_create_streams(self, path, read, write, append, must_exist, must_not_exist, synchronized, inheritable, hidden, fileno, handle):

        
        # TODO - For delete on close ->  unlink immediately 
        
        if handle is not None:
            self._unsupported("Stream creation from a posix handle")
            
        if fileno is not None:
            self._fileno = fileno
        
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
        
            if append:
                flags |= unix.O_APPEND
        
            if must_exist:
                pass # it's the default case for open() function
            elif must_not_exist: 
                flags |= unix.O_CREAT | unix.O_EXCL
            else:
                flags |= unix.O_CREAT # by default - we create the file iff it doesn't exists
        
            # TODO - use linux O_CLOEXEC when available
            # TODO - use F_FULLFSYNC on MAC OS X !!!   -> fcntl(fd, F_FULLFSYNC, 0);  51
            """
            if hidden:
                mode = 0000
            else:
                mode = 0777 # umask will apply on it anyway
            """
            self._fileno = unix.open(strname, flags)  #TODO - we shall be able to specify the permissions !!!
            
                
            if not inheritable:
                old_flags = unix.fcntl(self._fileno, unix.F_GETFD, 0);
                if not (old_flags & unix.FD_CLOEXEC):
                    #print "PREVENTING INHERITANCE !!!"
                    unix.fcntl(self._fileno, unix.F_SETFD, old_flags | unix.FD_CLOEXEC);
            """
            if hidden:
                unix.unlink()
            """
            # Here, if delete on close : unlink filepath !!!
            #### NO - TODO - PAKAL - use RSFS to delete it immediately !!!
    
    
    @_unix_error_converter       
    def _inner_close_streams(self):  
        """
        Warning - unlink official stdlib modules, this function may raise IOError !
        """
        if self._closefd:
            unix.close(self._fileno) 


    @_unix_error_converter
    def _inner_reduce(self, size): 
        self._inner_seek(size, defs.SEEK_SET) # TODO BE REMOVED IN NEW VERSION !!!
        unix.ftruncate(self._fileno, size)
        
        
    @_unix_error_converter
    def _inner_extend(self, size, zero_fill): 
        # posix truncation is ALWAYS "zerofill"
        self._inner_seek(size, defs.SEEK_SET) # TODO BE REMOVED IN NEW VERSION !!!
        unix.ftruncate(self._fileno, size)

    @_unix_error_converter
    def _inner_sync(self, metadata): 
        #TODO - refactor arguments with FULLSYNC or not !!!!!!
        if not metadata:
            try:
                # WARNING - file size will ALWAYS be updated if necessary to preserve data integrity, theoretically
                unix.fdatasync(self._fileno) # not supported on Mac Os X
                return
            except unix.error:
                pass
        
        try:
            unix.fcntl(self._fileno, unix.F_FULLFSYNC, 0) 
        except unix.error:
            unix.fsync(self._fileno)
        
           
    def _inner_fileno(self):
        return self._fileno

    # Inherited :
    #def _inner_handle(self):
    #   self._unsupported("handle") # io.UnsupportedOperation subclasses IOError, so we're OK with the official specs

    @_unix_error_converter
    def _inner_uid(self):
        stats = unix.fstat(self._fileno)
        return (stats.st_dev, stats.st_ino)
 
    @_unix_error_converter
    def _inner_times(self):
        stats = unix.fstat(self._fileno)
        return defs.FileTimes(access_time=stats.st_atime, modification_time=stats.st_mtime)
    
    @_unix_error_converter        
    def _inner_size(self):  
        return unix.fstat(self._fileno).st_size

    @_unix_error_converter
    def _inner_tell(self):
        return unix.ltell(self._fileno)

    @_unix_error_converter
    def _inner_seek(self, offset, whence):
        return unix.lseek(self._fileno, offset, whence)
  
            
    @_unix_error_converter
    def _inner_readinto(self, buffer):
        count = unix.readinto(self._fileno, buffer, len(buffer))
        return count

    @_unix_error_converter
    def _inner_write(self, bytes):
        return unix.write(self._fileno, bytes)
    
    
    def _fcntl_convert_file_range_arguments(self, length, offset, whence): # some normalization of arguments
        if(length is None):
            length = 0 # maximal range for fcntl/lockf
        return (length, offset, whence)

        
    @_unix_error_converter
    def _inner_file_lock(self, shared, timeout, length, offset, whence):

        """ MEGAWARNING : On at least some systems, 
        LOCK_EX can only be used if the file descriptor refers to a file opened for writing."""
        
        fd = self._fileno
        
        if(shared):
            operation = unix.LOCK_SH
        else:
            operation = unix.LOCK_EX

        if(timeout is not None):
            operation |= unix.LOCK_NB

        
        (length, offset, whence) = self._fcntl_convert_file_range_arguments(length, offset, whence)


        start_time = time.time()
        try_again = True

        while(try_again):

            try :
                import multiprocessing
                
                unix.lockf(fd, operation, length, offset, whence)
                print "---------->", multiprocessing.current_process().name, " LOCKED ", (operation, length, offset, whence)
                
            except unix.error, e:

                if(timeout is not None): # else, we try again indefinitely

                    current_time = time.time()

                    if(timeout <= current_time - start_time): # else, we try again until success or timeout

                        (error_code, title) = e.args

                        filename = "File"
                        try:
                            filename = str(self.name) # TODO - change this !!!
                        except AttributeError:
                            pass # surely a pseudo file object...

                        if(error_code in (errno.EACCES, errno.EAGAIN)):
                            raise defs.LockingException(error_code, title, filename)
                        else:
                            raise
                        
                 
                # Whatever the value of "timeout", we must sleep a little
                time.sleep(0.9) # TODO - PAKAL - make this use global parameters !
                  
            else: # success, we exit the loop

                try_again = False

        return True

    @_unix_error_converter
    def _inner_file_unlock(self, length, offset, whence):

        
        (length, offset, whence) = self._fcntl_convert_file_range_arguments(length, offset, whence)
        try:
            import multiprocessing
            print "---------->", multiprocessing.current_process().name, " UNLOCKED ", (unix.LOCK_UN, length, offset, whence)
            unix.lockf(self._fileno, unix.LOCK_UN, length, offset, whence)
        except IOError:
            raise # are there special cases to handle ?

        return True

rsFileIO = unixFileIO 