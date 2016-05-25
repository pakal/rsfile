#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os, stat
import rsfile_definitions as defs
from .rsfile_streams import *


def rsopen(name=None, mode="r", buffering=None, encoding=None, errors=None, newline=None, fileno=None, handle=None, closefd=True, opener=None,
           locking=True, timeout=None, thread_safe=True, mutex=None, permissions=0o777):

    """
    This function is a factory similar to :func:`io.open`, which returns chains of I/O streams targeting files, with
    a focus set on security and concurrency protections.
    
    ``name`` is the path to the file, in case no existing fileno or handle is provided for wrapping 
    through the ``fileno``/``handle`` arguments.

    ``mode`` is the access mode of the stream, it can be given either as a standard mode string, or as an advanced mode string 
    (see :ref:`file opening modes<file_opening_modes>`). 
    
    ``closefd`` (boolean) may only be False when wrapping a fileno or a handle, and in this case the wrapped
    stream will not be closed when the stream objects are closed.
 
    .. note:: 
            For backward compatibility, when using standard modes, it is still possible to provide 
            a fileno for wrapping directly as the ``name`` argument, but this way of proceeding is deprecated.

    ``buffering``, ``encoding``, ``errors``, and ``newline`` arguments have the same meaning as in :func:`io.open`.
    
    .. warning::
    
        Like io.open(), if buffering is 0, this function returns a raw stream, the methods of which
        only issue one system call. So in this case, checking the number of bytes written/read after 
        each operation is highly advised.
        
    
    If ``locking`` is True, the file will immediately be fully locked on opening, with a 
    default share mode (exclusive for writable streams, shared for read-only streams) 
    and the ``timeout`` argument provided. This is particularly useful is the file is opened in 
    "truncation" mode, as it prevents this truncation from happening without inter-process protection.
    Note that it is still possible to abort that locking with a call to :meth:`unlock` (without arguments).

    If ``thread_safe`` is True, the chain of streams returned by the function will be wrapped into 
    a thread-safe interface ; in this case, if ``mutex`` is provided, it is used as the concurrency lock, 
    else a new lock is created (a multiprocessing RLock() if the stream is inheritable, else a threading RLock().
     Note that, for performance reasons, there are currently no checks to prevent reentrant calls to file methods (eg. made via an OS signal), by raising RuntimeError like the original C-backed io module does, so reentrant calls may cause deadlocks if the file is buffered or thread-safe-wrapped.

    The ``permissions`` argument will simply be forwarded to the lowest level stream, 
    so as to be applied in case a file creation occurs (note : decimal '511' corresponds to octal '0777', i.e whole permissions).


    .. _file_opening_modes:
    
    .. rubric::
        FILE OPENING MODES
    
    In addition to standard modes as described in the documentation of :func:`io.open`,
    a set of advanced modes is available, as capital-case flags. These advanced modes
    should be combined in the order listed below, for ease of reading. Standard and advanced
    modes may not be mixed together.
    
    ========= ===============================================================
    Character Meaning
    ========= ===============================================================
    'R'       Stream is Readable
    'W'       Stream is Writable
    'A'       Stream is in Append mode (implicitly enforces W)
    '+'       File must already exist (i.e it must not be created)
    '-'       File must NOT already exist (i.e it must be created)
    'S'       Stream is Synchronized
    'I'       Stream is Inheritable
    'E'       File is Erased on opening
    'B'       Stream is in Binary mode
    'T'       Stream is in Text mode (default)
    ========= ===============================================================
    
    .. note:: 
        The '+' flag doesn't work on NFS shares with a linux kernel < 2.6.5, race conditions may occur.
    
    ========= =====================
    Mode Equivalences
    ===============================
    'r'           'R+'
    'w'           'WE'
    'a'           'A'
    'r+'          'RW+'
    'w+'          'RWE'
    'a+'          'RA'
    '...b'        '...B'
    '...t'        '...T'
    ========= =====================

    # TODO DOCUMENT that opener is ignored, and document x flag!!
    """

    # TODO - PYCONTRACT !!! check that no mutex if not thread-safe

    # Quick type checking
    if name and not isinstance(name, (basestring, int, long)):
        raise TypeError("invalid file: %r" % name)
    if not isinstance(mode, basestring):
        raise TypeError("invalid mode: %r" % mode)
    if buffering is not None and not isinstance(buffering, (int, long)):
        raise TypeError("invalid buffering: %r" % buffering)
    if encoding is not None and not isinstance(encoding, basestring):
        raise TypeError("invalid encoding: %r" % encoding)
    if errors is not None and not isinstance(errors, basestring):
        raise TypeError("invalid errors: %r" % errors)

    if not thread_safe and mutex:
        raise ValueError("providing a mutex for a non thread-safe stream is abnormal")

    cleaned_mode = mode.replace("U", "")
    if cleaned_mode.lower() == cleaned_mode:
        assert handle is None and fileno is None # to handle these, use advanced open mode
        (raw_kwargs, extended_kwargs) = parse_standard_args(name, mode, fileno, handle, closefd)
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
    result = raw
    try:
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
                bs = os.fstat(raw.fileno()).st_blksize # TODO - TO BE IMPROVED, on win32 it uselessly puts to work the libc compatibility layer !
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
                    result = RSThreadSafeWrapper(raw, mutex=mutex, is_interprocess=raw_kwargs["inheritable"])
                return result
            raise ValueError("can't have unbuffered text I/O")

        if raw.readable() and raw.writable():
            buffer = RSBufferedRandom(raw, buffering)
        elif raw.writable():
            buffer = RSBufferedWriter(raw, buffering)
        elif raw.readable():
            buffer = RSBufferedReader(raw, buffering)
        else:
            raise ValueError("unknown mode: %r" % mode)
        result = buffer
        if extended_kwargs["binary"]:
            if thread_safe:
                result = RSThreadSafeWrapper(buffer, mutex=mutex, is_interprocess=raw_kwargs["inheritable"])
            return result

        text = RSTextIOWrapper(buffer, encoding, errors, newline, line_buffering)
        text.mode = mode # TODO - shouldn't we change that weird artefact of the stdlib ?
        result = text

        if thread_safe:
            result = RSThreadSafeWrapper(text, mutex=mutex, is_interprocess=raw_kwargs["inheritable"])
        return result
    except:
        result.close()
        raise




def parse_standard_args(name, mode, fileno, handle, closefd): # warning - name can be a fileno here ...

    modes = set(mode)
    if not mode or modes - set("xarwb+tU") or len(mode) > len(modes):
        raise ValueError("invalid mode: %r" % mode)


    # raw analysis
    creating_flag = "x" in modes
    reading_flag = "r" in modes or "U" in modes
    writing_flag = "w" in modes
    appending_flag = "a" in modes
    updating_flag = "+" in modes

    truncate = writing_flag
    binary = "b" in modes
    text = "t" in modes

    if "U" in modes: # only for backward compatibility
        if creating_flag or writing_flag or appending_flag or updating_flag:
            raise ValueError("can't use U and writing mode at once")
        reading_flag = True # we enforce reading 

    if text and binary:
        raise ValueError("can't have text and binary mode at once")
    if creating_flag + reading_flag + writing_flag + appending_flag > 1:
        raise ValueError("can't have create/read/write/append mode flags at once")
    if not (creating_flag or reading_flag or writing_flag or appending_flag):
        raise ValueError("must have one of create/read/write/append mode flags")

    # real semantic
    if isinstance(name, (int, long)):
        if fileno is not None:
            raise ValueError("Impossible to provide a file descriptor via both name and fileno arguments")
        fileno = name
        path = None
    else:
        fileno = None
        path = name

    read = reading_flag or updating_flag
    write = creating_flag or writing_flag or appending_flag or updating_flag
    append = appending_flag
    must_create = creating_flag
    must_not_create = read and not write

    raw_kwargs = dict(path=path,
                    read=read,
                    write=write, append=append,
                    must_create=creating_flag,
                    must_not_create=must_not_create,
                    synchronized=False,
                    inheritable=True,
                    fileno=fileno, handle=handle, closefd=closefd)

    extended_kwargs = dict(truncate=truncate,
                            binary=binary,
                            text=text)

    return (raw_kwargs, extended_kwargs)




def parse_advanced_args(path, mode, fileno, handle, closefd):


    modes = set(mode)
    if modes - set("RAW+-SIEBT") or len(mode) > len(modes):
        raise ValueError("invalid mode: %r" % mode)

    path = path # must be None or a string

    read = "R" in mode
    append = "A" in mode
    write = "W" in mode or append

    must_create = "-" in mode
    must_not_create = "+" in mode

    synchronized = "S" in mode
    inheritable = "I" in mode

    truncate = "E" in mode # for "Erase"  
    binary = "B" in modes
    text = "T" in modes

    raw_kwargs = dict(path=path,
                    read=read,
                    write=write, append=append,
                    must_create=must_create,
                    must_not_create=must_not_create,
                    synchronized=synchronized,
                    inheritable=inheritable,
                    fileno=fileno, handle=handle, closefd=closefd)

    extended_kwargs = dict(truncate=truncate,
                      binary=binary,
                      text=text)

    return (raw_kwargs, extended_kwargs)







