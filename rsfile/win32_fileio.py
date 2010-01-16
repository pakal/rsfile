

import sys, os, functools, time

from abstract_fileio import AbstractFileIO
import rsfile_defines as defs
from rsbackends import _utilities as utilities
        
try:
    import rsbackends.pywin32_extensions as win32
except ImportError:
    import rsbackends.pywin32_ctypes as win32 
        



class win32FileIO(AbstractFileIO):        


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

        (res, string) = win32.ReadFile(self._handle, len(buffer))
        buffer[0:len(string)] = string
        return len(string)


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
    def _win32_convert_file_range_arguments(self, length, offset, whence):

        if offset is None:
            offset = 0
        
        if(not length): # 0 or None
            (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh) = (utilities.MAX_DWORD, utilities.MAX_DWORD)
        else:
            (nNumberOfBytesToLockLow, nNumberOfBytesToLockHigh) = utilities.pyint_to_double_dwords(length)

        if(whence == defs.SEEK_CUR):
            offset = offset + self._inner_tell()
        elif(whence == defs.SEEK_END):
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
                print ">>>>>>> process tries locking file %s on range %u/%u (unsigned integers)"%(self._path, overlapped.Offset, overlapped.Offset+nNumberOfBytesToLockLow-1) 

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
                            raise defs.LockingException(error_code, title, filename)
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
            print "Process unlocking file %s on range %u/%u<<<<<<<<<"%(self._path, overlapped.Offset+overlapped.OffsetHigh, overlapped.Offset+overlapped.OffsetHigh++nNumberOfBytesToLockLow+nNumberOfBytesToLockHigh-1) 
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