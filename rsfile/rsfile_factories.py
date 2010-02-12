
import os
import rsfile_definitions as defs
from rsfile_streams import *

    
def rsopen(name=None, mode="r", buffering=None, encoding=None, errors=None, newline=None, fileno=None, handle=None, closefd=True, 
            locking=True, timeout=None, thread_safe=True, mutex=None, permissions=0777):
    
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
    
    # TODO - PYCONTRACT !!! check that no mutex if not thread-safe
    
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
    
    raw_kwargs['permissions'] = permissions 

    raw = RSFileIO(**raw_kwargs)
    
    if extended_kwargs["truncate"] and not raw.writable(): 
        raise ValueError("Can't truncate file opened in read-only mode")
    
    if locking:   
        #print "we enforce file locking with %s - %s" %(shared, timeout)            
        raw.lock_file(timeout=timeout) 
    
    if extended_kwargs["truncate"]:    
            raw.truncate(0)            
    
    if buffering is None:
        buffering = -1
    line_buffering = False
    if buffering == 1 or buffering < 0 and raw.isatty():
        buffering = -1
        line_buffering = True
    if buffering < 0:
        buffering = defs.DEFAULT_BUFFER_SIZE
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
                return RSThreadSafeWrapper(raw, mutex=mutex, interprocess=raw_kwargs["inheritable"])
            else:
                return raw
        raise ValueError("can't have unbuffered text I/O")
    
    if raw.readable() and raw.writable():
        buffer = RSBufferedRandom(raw, buffering)
    elif raw.writable():
        buffer = RSBufferedWriter(raw, buffering)
    elif raw.readable():
        buffer = RSBufferedReader(raw, buffering)
    else:
        raise ValueError("unknown mode: %r" % mode)
    
    if extended_kwargs["binary"]:
        if thread_safe:
            return RSThreadSafeWrapper(buffer, mutex=mutex, interprocess=raw_kwargs["inheritable"])
        else:
            return buffer
        
    text = RSTextIOWrapper(buffer, encoding, errors, newline, line_buffering)
    text.mode = mode # Pakal - weird TODO change that !!!!!
    
    if thread_safe:
        return RSThreadSafeWrapper(text, mutex=mutex, interprocess=raw_kwargs["inheritable"])    
    else:
        return text
    

    



    
def parse_standard_args(name, mode, fileno, handle, closefd): # warning - name can be a fileno here ...
    # PAKAL - todo - insert fileno and handle into processing !!!!!!!!!!!!!!!!!!!!!!!!!
    
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
                    fileno=fileno, handle=None, closefd=closefd)
    
    extended_kwargs = dict(truncate=truncate, 
                            binary=binary,
                            text=text)
                    
    return (raw_kwargs, extended_kwargs)
    


def parse_advanced_args(path, mode, fileno, handle, closefd):

    
    modes = set(mode)
    if modes - set("RAW+-SIHEBT") or len(mode) > len(modes):
        raise ValueError("invalid mode: %r" % mode)    
    
    path = path # MUST BE NONE OR A STRING IN ANY WAY 
    
    read = "R" in mode
    append = "A" in mode
    write = "W" in mode or append 
    
    must_exist = "+" in mode
    must_not_exist = "-" in mode
    
    synchronized = "S" in mode
    inheritable = "I" in mode
    
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
                    fileno=fileno, handle=handle, closefd=closefd)
    
    extended_kwargs = dict(truncate=truncate, 
                      binary=binary,
                      text=text)
                      
    return (raw_kwargs, extended_kwargs)

    

    





    








