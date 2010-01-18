#-*- coding: utf-8 -*-

from __future__ import with_statement

import sys, os
import functools
import io

from rsfile_defines import * # constants and base types
from abstract_fileio import AbstractFileIO, ThreadSafeWrapper

if sys.platform == 'win32':
    try:
        from win32_fileio import rsFileIO
        FILE_IMPLEMENTATION = "win32"
    except Exception, e:
        raise ImportError("No win32 backend available : %s" % e)
else:
    try:
        from unix_fileio import rsFileIO
        FILE_IMPLEMENTATION = "unix"
    except Exception, e:
        raise ImportError("No unix backend available : %s" % e)



# # # TODO list # # #

"""
TODO : check if this is true, or if only dup2() descriptors have this effect :
Locks are associated with processes. A process can only have one kind of lock set for each byte of a given file. 
When any file descriptor for that file is closed by the process, all of the locks that process holds on that file 
are released, even if the locks were made using other descriptors that remain open. Likewise, locks are released when 
a process exits, and are not inherited by child processes created using fork (see Creating a Process). 
"""
# TODO - allow permissions/umask settings
# TODO - prevent bad locking when non writing mode !!! exclusive vs shared
# TODO - test on python 2.5, with statements !!!!
# warning - we must take care of file deletion on windows and linux !!! share_delete renaming etc.!! avoid broken file waiting deletion

#TODO py2.7 he file object will now set the filename attribute on the IOError exception when trying to open a directory on POSIX platforms. (Noted by Jan Kaliszewski; issue 4764.)
#TODO - The io.FileIO class now raises an OSError when passed an invalid file descriptor. (Implemented by Benjamin Peterson; issue 4991.)
# COOL STUFFS :
# TODO : add upgrade/downgrade of shared/nonshared full file locks !!!! (fcntl does it atomically !)
# TODO : grab the ctypes locking found in bazaar code - lockfile, overlapped etc !!!!

# TODO - implement thread safe and win32-compatible "umask" system for file creation, with "hidden" and "permissions" arguments offered !!!!
#Todo - think about way of having full-locked fcntl files work together !!!!


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
                raw.truncate(0)
        else: # if already locked, or if we don't care about locks...
            raw.truncate(0)            
    
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
        @functools.wraps(getattr(AbstractFileIO, attribute_name))
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







    








