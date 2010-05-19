#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals

import sys, os, functools, time, errno, stat, locale
from array import array

import rsfileio_abstract
import rsfile_definitions as defs
from rsbackends import _utilities as utilities


try:
    import rsbackends.pywin32_extensions as win32
except ImportError:
    import rsbackends.pywin32_ctypes as win32 
        

WIN32_MSG_ENCODING = locale.getpreferredencoding()


class RSFileIO(rsfileio_abstract.RSFileIOAbstract):        


    __POSITION_REFERENCES = {defs.SEEK_SET:win32.FILE_BEGIN , defs.SEEK_CUR:win32.FILE_CURRENT, defs.SEEK_END:win32.FILE_END}

    # Warning - this is to be used as a static method ! #
    def _win32_error_converter(f): #@NoSelf
        @functools.wraps(f)
        def wrapper(self, *args, **kwds):
            try:
                return f(self, *args, **kwds)
            except win32.error, e: # WARNING - this is not a subclass of OSERROR !!!!!!!!!!!!!
                traceback = sys.exc_info()[2]
                #print repr(e)str(e[1])+" - "+str(e[2
                
                # pywin32's pywintypes.error instances have no errno
                if hasattr(e, "errno"): 
                    errno = e.errno
                else:
                    errno = utilities.winerror_to_errno(e.winerror)
                
                # we must convert to unicode the local error message           
                if isinstance(e.strerror, unicode):
                    strerror = e.strerror
                else:
                    strerror = e.strerror.decode(WIN32_MSG_ENCODING, 'replace')
   
                raise IOError, (errno, strerror, unicode(self._name)), traceback
        return wrapper
    
    
    
    
    @_win32_error_converter        
    def _inner_create_streams(self, path, read, write, append, must_create, must_not_create, synchronized, inheritable, fileno, handle, permissions):

        
        # # # real opening of the file stream # # #
        if handle is not None:
            self._handle = int(handle)
            #print "FILE OPENED VIA HANDLE ", handle
            
        elif fileno is not None:
            self._fileno = fileno
            #print "FILE OPENED VIA FILENO ", fileno
            import msvcrt
            assert msvcrt.get_osfhandle == win32._get_osfhandle
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
            if must_not_create:
                creationDisposition = win32.OPEN_EXISTING # 3
            elif must_create: 
                creationDisposition = win32.CREATE_NEW # 1
            else:
                creationDisposition = win32.OPEN_ALWAYS # 4

            if inheritable:
                securityAttributes = win32.SECURITY_ATTRIBUTES()
                securityAttributes.bInheritHandle = True
                securityAttributes.SECURITY_DESCRIPTOR = None
            else:
                securityAttributes = None
            
            
            if not permissions & stat.S_IWUSR:
                flagsAndAttributes = win32.FILE_ATTRIBUTE_READONLY
            else:
                flagsAndAttributes = win32.FILE_ATTRIBUTE_NORMAL   
            
            
            #### NO - TODO - PAKAL - use RSFS to delete it immediately !!!
            """
            if hidden:
                flagsAndAttributes |= win32.FILE_FLAG_DELETE_ON_CLOSE""" # TO BE REMOVED
                
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
                
            
            handle = win32.CreateFile(*args)
            #print ">>>File opened : ", path
            
            self._handle = int(handle)
            if hasattr(handle, "Detach"): # pywin32
                handle.Detach()
            
            self._lock_registry_inode = self._handle # we don't care about real inode uid, since win32 already distinguishes which handle owns a lock
            self._lock_registry_descriptor = self._handle
            

    @_win32_error_converter
    def _inner_close_streams(self):
        """
        MSDN note : To close a file opened with _get_osfhandle, call _close. The underlying handle 
        is also closed by a call to _close, so it is not necessary to 
        call the Win32 function CloseHandle on the original handle.

        This function may raise IOError !
        """
        
        #print "<<<File closed : ", self._name
        if self._closefd: # always True except when wrapping external file descriptors
            if self._fileno:
                # WARNING - necessary to avoid leaks of C file descriptors !!!!!!!!!
                try:
                    os.close(self._fileno) # this closes the underlying native handle as well
                except OSError, e:
                    raise IOError(errno.EBADF, "bad file descriptor")
            else:
                win32.CloseHandle(self._handle)


    @_win32_error_converter    
    def _inner_reduce(self, size): # warning - no check is done !!! 
        old_pos = self._inner_tell()
        self.seek(size) 
        #print ("---> inner reduce to ", self.tell())
        win32.SetEndOfFile(self._handle) #WAAARNING - doesn't raise exceptions !!!!  
        self._inner_seek(old_pos)
    
    @_win32_error_converter    
    def _inner_extend(self, size, zero_fill): # warning - no check is done !!!  
        
        if(not zero_fill):
            old_pos = self._inner_tell()
            self.seek(size)
            win32.SetEndOfFile(self._handle) # this might fail silently !!!   
            self._inner_seek(old_pos)
        else:
            pass # we can't directly truncate with zero-filling on win32, so just upper levels handle it

            
            
    @_win32_error_converter         
    def _inner_sync(self, metadata, full_flush):
        # only one type of synchronization : full_flush + metadata
        win32.FlushFileBuffers(self._handle) 
    
    
    @_win32_error_converter         
    def _inner_uid(self):
        """
        (dwFileAttributes, ftCreationTime, ftLastAccessTime, 
         ftLastWriteTime, dwVolumeSerialNumber, nFileSizeHigh, 
         nFileSizeLow, nNumberOfLinks, nFileIndexHigh, nFileIndexLow) """
        
        handle_info = win32.GetFileInformationByHandle(self._handle)
        device = handle_info.dwVolumeSerialNumber
        inode = utilities.double_dwords_to_pyint(handle_info.nFileIndexLow, handle_info.nFileIndexHigh)
        
        if device <= 0 or inode <= 0: # File info  might be incomplete, according to MSDN
            raise win32.error(win32.ERROR_NOT_SUPPORTED, "Impossible to retrieve win32 device/file-id information") # Pakal - to be unified
        
        self._uid = (device, inode)
        return self._uid
        
    
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
        
        return defs.FileTimes(access_time = utilities.win32_filetime_to_python_timestamp(handle_info.ftLastAccessTime.dwLowDateTime,
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
    def _inner_seek(self, offset, whence=defs.SEEK_SET):
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

        (res, mybytes) = win32.ReadFile(self._handle, len(buffer))
        if isinstance(buffer, array):
            try:
                buffer[0:len(mybytes)] = array(b"b", mybytes)
            except TypeError:
                buffer[0:len(mybytes)] = array("b", mybytes) # mess between py2k and py3k...
        else:
            buffer[0:len(mybytes)] = mybytes
        return len(mybytes)


    @_win32_error_converter    
    def _inner_write(self, buffer):
        """
        Gerer write avec filepointer after eof !! que se passe t il sous linux ????????
        La doc se contredit, est-ce qu'il faut retourner num written ou lancer ioerror ?? PAKAL
        """

        if self._append: # yep, no atomicity around here, as in truncate()
            self._inner_seek(0, defs.SEEK_END)

        cur_pos = self._inner_tell()
        if cur_pos > self._inner_size(): # TODO - document this !!!
            self._inner_extend(cur_pos, zero_fill=True) # we extend the file with zeros until current file pointer position

        (res, bytes_written) = win32.WriteFile(self._handle, bytes(buffer))
        # nothing to do with res, for files, it seems

        # we let the file pointer where it is, even if we're in append mode (no come-back to previous reading position)
        return bytes_written


    # no need for @_win32_error_converter    
    def _win32_convert_file_range_arguments(self, length, abs_offset):

        if abs_offset is None:
            abs_offset = 0
        
        if(not length): # 0 or None
            (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh) = (utilities.MAX_DWORD, utilities.MAX_DWORD)
        else:
            (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh) = utilities.pyint_to_double_dwords(length)


        overlapped = win32.OVERLAPPED() # contains ['Internal', 'InternalHigh', 'Offset', 'OffsetHigh', 'dword', 'hEvent', 'object']
        (overlapped.Offset, overlapped.OffsetHigh) = utilities.pyint_to_double_dwords(abs_offset)
        overlapped.hEvent = 0

        return (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)


    
    @_win32_error_converter
    def _inner_file_lock(self, length, abs_offset, blocking, shared):

        """
        # PAKAL - to remove - 
        timeout = 0
        print "TIMEOUT IS SET TO 0 TO BE REMOVEd !!!"
        # TODO PAKAL - HERE, replace timeout by default global value if it is None !!
        """
        hfile = self._handle

        flags = 0 if shared else win32.LOCKFILE_EXCLUSIVE_LOCK
        if not blocking:
            flags |= win32.LOCKFILE_FAIL_IMMEDIATELY

        (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped) = self._win32_convert_file_range_arguments(length, abs_offset)

        win32.LockFileEx(hfile, flags, nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)
        # error: 32 - ERROR_SHARING_VIOLATION - The process cannot access the file because it is being used by another process.
        # error: 33 - ERROR_LOCK_VIOLATION - The process cannot access the file because another process has locked a portion of the file.
        # error: 167 - ERROR_LOCK_FAILED - Unable to lock a region of a file.
        # error: 307 - ERROR_INVALID_LOCK_RANGE - A requested file lock operation cannot be processed due to an invalid byte range. -> shouldn't happen due to previous value checks        




        
    @_win32_error_converter  
    def _inner_file_unlock(self, length, abs_offset):

        hfile = self._handle
        
        (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped) = self._win32_convert_file_range_arguments(length, abs_offset)

        win32.UnlockFileEx(hfile, nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh, overlapped)
        # error: 158 - ERROR_NOT_LOCKED - The segment is already unlocked.
      

