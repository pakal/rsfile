#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os, stat
from . import rsfile_definitions as defs
from .rsfile_streams import *



def rsopen(name=None, mode="r", buffering=None, encoding=None, errors=None, newline=None,
           fileno=None, handle=None, closefd=True, opener=None,
           locking=True, timeout=None, thread_safe=True, mutex=None, permissions=0o777):

    """
    This function is a factory similar to :func:`io.open` (alias of the builtin "open()"), and returns chains of I/O streams with a focus on security and concurrency. If you need high performance file operations, use standard io.open() instead.

    See the `open() builtin documentation <https://docs.python.org/3/library/functions.html#open>`
    
    ``name`` is the path to the file, in case no existing fileno or handle is provided for wrapping 
    through the ``fileno``/``handle`` arguments.

    ``mode`` is the access mode of the stream, it can be given either as a standard mode string, or as an advanced mode string (see :ref:`file opening modes<file_opening_modes>`).

    The ``buffering``, ``encoding``, ``errors``, and ``newline`` arguments have the same meaning as in :func:`io.open`.

    ``fileno`` and ``handle``, mutually exclusive, allow you to provide a C-style file descriptor or an OS-specific handle to be wrapped. Please ensure, of course, that these raw streams are compatible with the ``mode`` requested.

    ``opener`` is supported, and must be return a ``mode``-compatible C-style file descriptor, like in the stdlib, not an OS-specific handle.

    ``closefd`` (boolean) may only be False when wrapping a fileno or a handle, and in this case this wrapped raw stream will not be closed when the file object is closed.
 
    .. note:: 
            For backward compatibility, when using standard modes, it is still possible to provide 
            a fileno for wrapping directly as the ``name`` argument, but this way of doing is deprecated.
    
    .. warning::
    
        Like io.open(), if buffering is 0, this function returns a raw stream, the methods of which
        only issue one system call. So in this case, checking the number of bytes written/read after 
        each operation is highly advised.
    
    If ``locking`` is True, the whole file will be immediately locked on opening, with an automatically determined share mode (exclusive for writable streams, shared for read-only streams), and the ``timeout`` argument provided.
    This is particularly useful is the file is opened in "truncation" mode, as it prevents this truncation from happening without inter-process protection.
    Note that it is still possible to abort that locking later, with a call to :meth:`unlock` (without arguments).

    If ``thread_safe`` is True, the chain of streams returned by the function will be wrapped into 
    a thread-safe interface ; in this case, if ``mutex`` is provided, it is used as the concurrency lock, 
    else a new lock is created (a multiprocessing RLock() if the stream is inheritable, else a threading RLock().
    Note that, for performance reasons, there are currently no checks to prevent reentrant calls from occurring on file object methods (eg. calls issued by OS signal handler), unlike the original C-backed io module does by raising RuntimeError. So reentrant calls may cause deadlocks if the file is buffered or thread-safe-wrapped.

    The ``permissions`` argument will simply be forwarded to the lowest level stream, 
    so as to be applied in case a file creation occurs (note : decimal '511' corresponds to octal '0o777', i.e whole permissions).

    .. _file_opening_modes:
    
    .. rubric::
        FILE OPENING MODES
    
    In addition to standard modes as described in the documentation of :func:`io.open`,
    a set of advanced modes is available, as capital-cased flags. These advanced modes
    should be combined in the order listed below, for ease of reading. Standard and advanced
    modes may not be mixed together.
    
    ========= ========================================================================================
    Character Meaning
    ========= ========================================================================================
    'R'       Stream is Readable
    'W'       Stream is Writable
    'A'       Stream is in Append mode (implicitly enforces W)

    'N'       File MUST already exist (i.e it must not be created, was "+" previously)
    'C'       File must NOT already exist (i.e it must be created, was "-" previously)

    'S'       Stream is Synchronized (flush() tries to ensure that file metadata and data reach
              the disk device before returning, even though the disk itself might have a cache)

    'I'       Stream is Inheritable by children processes (by default, it's not)

    'E'       File is Erased on opening (ignored when "C" is set, since new file will be empty anyway)

    'B'       Stream is in Binary mode
    'T'       Stream is in Text mode (default)
    ========= ========================================================================================

    Any combination of "R", "W", and "A" is possible.

    "N" and "C" flags are mutually exclusive, if none is set then the file will be opened
    whatever its current existence status. Old "+" and "-" flags, ambiguous, are deprecated but still supported.

    "S" and "I" flags may be applied to any kind of opening mode.

    "E" requires the stream to be writable (W or A), except if "C" is set (because then we're sure that the file will be empty on opening).

    "B" and "T" are mutually exclusive.

    .. note:: 
        The "C" flag doesn't work well on NFS shares with a linux kernel < 2.6.5, race conditions may occur.

    Here is an (autogenerated) table describing the different standard open modes, and their advanced equivalents.
    That the deprecated "U" flag, as well as binary/text flags, are not mentioned here for clarity. The "x" mode flag was added in python3.3, for exclusive file creation.

    ==========  ==========  ======  =======  ========  =============  =================  ==========
    std_mode    adv_mode    read    write    append    must_create    must_not_create    truncate
    ==========  ==========  ======  =======  ========  =============  =================  ==========
    r           RN          true                                      true
    r+          RWN         true    true                              true
    w           WE                  true                                                 true
    w+          RWE         true    true                                                 true
    a           A                   true     true
    a+          RA          true    true     true
    x           WC                  true               true
    x+          RWC         true    true               true
    ==========  ==========  ======  =======  ========  =============  =================  ==========

    """

    # TODO - PYCONTRACT !!! check that no mutex if not thread-safe

    # Quick type checking
    if name and not isinstance(name, (basestring, int, long)):
        raise defs.BadValueTypeError("invalid file: %r" % name)
    if not isinstance(mode, basestring):
        raise defs.BadValueTypeError("invalid mode: %r" % mode)
    if buffering is not None and not isinstance(buffering, (int, long)):
        raise defs.BadValueTypeError("invalid buffering: %r" % buffering)
    if encoding is not None and not isinstance(encoding, basestring):
        raise defs.BadValueTypeError("invalid encoding: %r" % encoding)
    if errors is not None and not isinstance(errors, basestring):
        raise defs.BadValueTypeError("invalid errors: %r" % errors)

    if not thread_safe and mutex:
        raise defs.BadValueTypeError("providing a mutex for a non thread-safe stream is abnormal")

    cleaned_mode = mode.replace("U", "")
    if cleaned_mode.lower() == cleaned_mode:
        assert handle is None and fileno is None # to handle these, use advanced open mode
        (raw_kwargs, extended_kwargs) = parse_standard_args(name, mode, fileno, handle, closefd)
    elif cleaned_mode.upper() == cleaned_mode:
        (raw_kwargs, extended_kwargs) = parse_advanced_args(name, mode, fileno, handle, closefd)
    else:
        raise defs.BadValueTypeError("bad mode string %r : it must contain only lower case (standard mode) or upper case (advanced mode) characters" % mode)

    if opener:
        if raw_kwargs["fileno"]:
            raise defs.BadValueTypeError("can't provide both fileno and opener")
        raw_kwargs["fileno"] = opener(name, mode)  # we give it the original "name" as parameter, not the normalized path
        raw_kwargs["path"] = None  # irrelevant in this case

    if extended_kwargs["truncate"]:
        if not (raw_kwargs["write"] or raw_kwargs["append"]):
            raise defs.BadValueTypeError("can't truncate a non-writable file")
        if raw_kwargs["fileno"] or raw_kwargs["handle"]:
            # IMPORTANT: when wrapping an existing stream, we dont NOT truncate it, to respect with the stdlib behaviour
            extended_kwargs["truncate"] = False

    if extended_kwargs["binary"] and extended_kwargs["text"]:
        raise defs.BadValueTypeError("can't have text and binary mode at once")
    if extended_kwargs["binary"] and encoding is not None:
        raise defs.BadValueTypeError("binary mode doesn't take an encoding argument")
    if extended_kwargs["binary"] and errors is not None:
        raise defs.BadValueTypeError("binary mode doesn't take an 'errors' argument")
    if extended_kwargs["binary"] and newline is not None:
        raise defs.BadValueTypeError("binary mode doesn't take a newline argument")

    raw_kwargs['permissions'] = permissions
    #print("We get RSFileIO", RSFileIO)
    raw = RSFileIO(**raw_kwargs)
    result = raw
    try:

        if locking:
            #print "we enforce file locking with %s - %s" %(shared, timeout)
            raw.lock_file(timeout=timeout)

        if extended_kwargs["truncate"]:
            # NOW that we've potentially locked the file, we may truncate
            raw.truncate(0)  # does nothing on PIPES

        if buffering is None:
            buffering = -1
        line_buffering = False
        if buffering == 1 or buffering < 0 and raw.isatty():
            buffering = -1
            line_buffering = True
        if buffering < 0:
            buffering = defs.DEFAULT_BUFFER_SIZE
            try:
                bs = os.fstat(raw.fileno()).st_blksize # TODO - TO BE IMPROVED, on windows it uselessly puts to work the libc compatibility layer !
            except (os.error, AttributeError):
                pass
            else:
                if bs > 1:
                    buffering = bs
        if buffering < 0:
            raise defs.BadValueTypeError("invalid buffering size")
        if buffering == 0:
            if extended_kwargs["binary"]:
                if thread_safe:
                    result = RSThreadSafeWrapper(raw, mutex=mutex, is_interprocess=raw_kwargs["inheritable"])
                return result
            raise defs.BadValueTypeError("can't have unbuffered text I/O")

        if raw.readable() and raw.writable():
            buffer = RSBufferedRandom(raw, buffering)
        elif raw.writable():
            buffer = RSBufferedWriter(raw, buffering)
        elif raw.readable():
            buffer = RSBufferedReader(raw, buffering)
        else:
            raise defs.BadValueTypeError("unknown mode: %r" % mode)
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
    if not mode or modes - defs.STDLIB_OPEN_FLAGS or len(mode) > len(modes):
        raise defs.BadValueTypeError("invalid mode: %r" % mode)

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
            raise defs.BadValueTypeError("can't use U and writing mode at once")
        reading_flag = True # we enforce reading 

    if creating_flag + reading_flag + writing_flag + appending_flag != 1:
        raise defs.BadValueTypeError("must have exactly one of create/read/write/append mode flags")

    # real semantic
    if isinstance(name, (int, long)):
        if fileno is not None:
            raise defs.BadValueTypeError("Impossible to provide a file descriptor via both name and fileno arguments")
        fileno = name
        path = None
    else:
        fileno = None
        path = name

    read = reading_flag or updating_flag
    write = creating_flag or writing_flag or appending_flag or updating_flag
    append = appending_flag
    must_create = creating_flag
    must_not_create = reading_flag and not (creating_flag or writing_flag or appending_flag)

    if must_create:
        truncate = False  # ignored

    raw_kwargs = dict(path=path,
                    read=read,
                    write=write,
                    append=append,
                    must_create=must_create,
                    must_not_create=must_not_create,
                    synchronized=False,
                    inheritable=False,  # was changed in python stdlib, no more inheritability by default!
                    fileno=fileno, handle=handle, closefd=closefd)

    extended_kwargs = dict(truncate=truncate,
                            binary=binary,
                            text=text)

    return (raw_kwargs, extended_kwargs)




def parse_advanced_args(path, mode, fileno, handle, closefd):

    modes = set(mode)
    if modes - set(defs.ADVANCED_OPEN_FLAGS) or len(mode) > len(modes):
        raise defs.BadValueTypeError("invalid mode: %r" % mode)

    path = path # must be None or a string

    read = "R" in mode
    append = "A" in mode
    write = "W" in mode or append

    must_create = "C" in mode or "-" in mode
    must_not_create = "N" in mode or "+" in mode

    synchronized = "S" in mode
    inheritable = "I" in mode

    truncate = "E" in mode # for "Erase"  
    binary = "B" in modes
    text = "T" in modes

    if must_create:
        truncate = False  # ignored

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







