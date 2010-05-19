#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals

import sys, os, functools, errno, time, stat, threading, locale
import rsfileio_abstract
import rsfile_definitions as defs


try:
    import rsbackends.unix_stdlib as unix
except ImportError:
    raise
    #import rsbackends.unix_ctypes as unix
        



UNIX_MSG_ENCODING = locale.getpreferredencoding()

class RSFileIO(rsfileio_abstract.RSFileIOAbstract):      

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
                
                if not isinstance(e.strerror, unicode):
                    strerror = e.strerror.decode(UNIX_MSG_ENCODING, 'replace')
                else:
                    strerror = e.strerror

                    raise IOError, (e.errno, strerror, unicode(self._name)), traceback
        return wrapper
    
    
    @_unix_error_converter
    def _purge_pending_related_file_descriptors(self):
        """
        Returns True iff this uid has no more locks left and data left, i/e really closing descriptors is OK.
        """
        
        with rsfileio_abstract.IntraProcessLockRegistry.mutex:
            
            res = rsfileio_abstract.IntraProcessLockRegistry.uid_has_locks(self._uid)
            if not res: # no more locks left for that uid
                data_list = rsfileio_abstract.IntraProcessLockRegistry.remove_uid_data(self._uid)
                for fd in data_list: # we close all pending file descriptors (which were left opened to prevent fcntl() lock autoremoving)
                    unix.close(fd) 
  
            return not res
    
        
        
    # # Private methods - no check is made on their argument or the file object state ! # #
    @_unix_error_converter
    def _inner_create_streams(self, path, read, write, append, must_create, must_not_create, synchronized, inheritable, fileno, handle, permissions):

        # Note : opening broken links works if we're in "w" mode, and raises error in "r" mode,
        # like for normal unexisting files.
        
        
        if handle is not None:
            self._fileno = self._handle = handle
        
        elif fileno is not None:
            self._fileno = self._handle = fileno
        
        else: #we open the file with low level posix IO - the unix "open()"  function
        
            if isinstance(path, unicode):
                strname = path.encode(sys.getfilesystemencoding()) # let's take no risks - and do not use locale.getpreferredencoding() here 
            else: 
                strname = path
        
        
            flags = 0 # TODO - use unix.O_LARGEFILE on linux filesystems !!!!
            
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
        
            if must_not_create:
                pass # it's the default case for open() function
            elif must_create: 
                flags |= unix.O_CREAT | unix.O_EXCL
            else:
                flags |= unix.O_CREAT # by default - we create the file iff it doesn't exists
        

            self._fileno = self._handle = unix.open(strname, flags, permissions)

            # on unix we must prevent the opening of directories or pipes !
            stats = unix.fstat(self._fileno).st_mode
            if stat.S_ISDIR(stats):
                raise IOError(errno.EISDIR, "RSFile can't open directories", self.name) 
            if not stat.S_ISREG(stats):
                raise IOError(errno.EINVAL, "RSFile can only open regular files", self.name)     

            if not inheritable:
                old_flags = unix.fcntl(self._fileno, unix.F_GETFD, 0);
                if not (old_flags & unix.FD_CLOEXEC): # we may use O_CLOEXEC instead (Since Linux 2.6.23)
                    unix.fcntl(self._fileno, unix.F_SETFD, old_flags | unix.FD_CLOEXEC);
                    
            self._lock_registry_inode = self._inner_uid()
            self._lock_registry_descriptor = self._fileno
            
    
    
    @_unix_error_converter       
    def _inner_close_streams(self):  
        """
        Warning - unlink official stdlib modules, this function may raise IOError !
        """
        if self._closefd:
            with rsfileio_abstract.IntraProcessLockRegistry.mutex:
                rsfileio_abstract.IntraProcessLockRegistry.add_uid_data(self._uid, self._fileno) 
                self._purge_pending_related_file_descriptors()
                # we assume that there are chances for this to be the only handle pointing this precise file
                rsfileio_abstract.IntraProcessLockRegistry.try_deleting_uid_entry(self._uid)

                         

    @_unix_error_converter
    def _inner_reduce(self, size): 
        unix.ftruncate(self._fileno, size)
        
        
    @_unix_error_converter
    def _inner_extend(self, size, zero_fill): 
        # posix truncation is ALWAYS "zerofill"
        unix.ftruncate(self._fileno, size)


    @_unix_error_converter
    def _inner_sync(self, metadata, full_flush): 
        
        if full_flush: # full_flush is more important than metadata
            try:
                unix.fcntl(self._fileno, unix.F_FULLFSYNC, 0) # Mac OS X only
                return
            except unix.error:
                pass
            
        if not metadata:
            try:
                # theoretically, file size will properly be updated, if it is necessary to preserve data integrity
                unix.fdatasync(self._fileno) # not supported on Mac Os X
                return
            except unix.error:
                pass
        
        unix.fsync(self._fileno) # last attempt : metadata flush without full_sync guarantees
        
           
    def _inner_fileno(self):
        return self._fileno

    def _inner_handle(self):
        return self._handle
    

    @_unix_error_converter
    def _inner_uid(self):
        stats = unix.fstat(self._fileno)
        self._uid = (stats.st_dev, stats.st_ino)
        return self._uid
 
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
    
            
    @_unix_error_converter
    def _inner_file_lock(self, length, abs_offset, blocking, shared):

        """ MEGAWARNING : On at least some systems, 
        LOCK_EX can only be used if the file descriptor refers to a file opened for writing."""
        
        fd = self._fileno
        
        if(shared):
            operation = unix.LOCK_SH
        else:
            operation = unix.LOCK_EX
            
        if not blocking:
            operation |= unix.LOCK_NB
        if length is None:
            length = 0 # that's the "infinity" value for fcntl

        unix.lockf(fd, operation, length, abs_offset, os.SEEK_SET) #  might raise errno.EACCES, errno.EAGAIN and ... ? TODO
        
        
    @_unix_error_converter
    def _inner_file_unlock(self, length, abs_offset):

        if length is None:
            length = 0 # that's the "infinity" value for fcntl
    
        try:
            unix.lockf(self._fileno, unix.LOCK_UN, length, abs_offset, os.SEEK_SET)
        finally:
            self._purge_pending_related_file_descriptors() # todo - optimize this out during unlock-on-close loop
            


