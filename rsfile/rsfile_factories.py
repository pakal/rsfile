#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os, stat
from . import rsfile_definitions as defs
from .rsfile_streams import *



def rsopen(name=None, mode="r", buffering=None, encoding=None, errors=None, newline=None,
           fileno=None, handle=None, closefd=True, opener=None,
           locking=True, timeout=None, thread_safe=True, mutex=None, permissions=0o777):

    """
    This function is a factory retrocompatible with :func:`io.open` (wich is an alias of the "open()" builtin). It returns chains of I/O streams, with a focus on security and concurrency.

    For background information see the `open() builtin documentation <https://docs.python.org/3/library/functions.html#open>`_.

    .. rubric::
        PARAMETERS
    
    ``name`` is the path to the file, required if no existing fileno or handle is provided for wrapping
    through the ``fileno``/``handle`` arguments.

    ``mode`` is the access mode of the stream, it can be given either as a standard mode string, or as an advanced mode string (see :ref:`file opening modes<file_opening_modes>`).

    The ``buffering``, ``encoding``, ``errors``, ``newline`` and ``opener`` arguments have the same meaning as in :func:`io.open`. Note that the ``opener`` callable must return a ``mode``-compatible C-style file descriptor, like in the stdlib, not an OS-specific handle.

    ``fileno`` and ``handle``, mutually exclusive, allow you to provide a C-style file descriptor or an OS-specific handle to be wrapped. Please ensure, of course, that these raw streams are compatible with the ``mode`` requested.

    ``closefd`` (boolean) may only be False when wrapping a fileno or a handle, and in this case this wrapped raw stream will not be closed when the file object gets closed.
 
    .. note:: 
            For backward compatibility, when using standard modes, it is also possible to provide
            an integer fileno for wrapping directly as the ``name`` argument.
    
    .. warning::
    
        Like for io.open(), if buffering is 0, this function returns a raw stream, the methods of which
        only issue one system call. So in this case, checking the number of bytes written/read after 
        each operation is highly advised.
    
    If ``locking`` is True, the *whole* file will be immediately locked on opening, with an automatically determined share mode (exclusive for writable streams, shared for read-only streams), and the ``timeout`` argument provided (see the :meth:`lock_file() <rsfile.rsiobase.RSIOBase.lock_file>` method for details).
    This is particularly useful is the file is opened with "truncate" flag, as it prevents this truncation from happening without inter-process protection.
    It is still possible to abort that locking later, with a call to :meth:`unlock` (without arguments).

    If ``thread_safe`` is True, the chain of streams returned by the function will be wrapped into 
    a thread-safe interface ; in this case, if ``mutex`` is provided, it is used as the concurrency lock, 
    else a new lock is created (a multiprocessing RLock() if the stream is inheritable and OS supports fork(),
    else a threading RLock().
    If a multiprocessing lock is in place, multiprocessing done via forking (without exec) allows all processes to
    issue atomic calls (read(), write()...) on the stream they have inherited, and to protect themselves by a
    "with myfile.mutex", if they must do several operations in an atomic way. For now streams are not pickleable,
    so on windows (or after a fork+exec), each child process must open its own rsfile stream, and possibly provide it
    a shared interprocess ``mutex`` transferred separately.
    Note that, for performance reasons, there are currently no checks done to prevent reentrant calls from occurring on
    file object methods (eg. calls issued by OS signal handler). So reentrant calls may cause deadlocks if the file
    is buffered or thread-safe-wrapped (the original C-backed io module, on the other hand, has protections:
    https://docs.python.org/3/library/io.html#reentrancy).

    The ``permissions`` argument must be an integer, eg. a valid combination of :mod:`stat` permission flags.
    It defaults to octal '777', i.e decimal '511', i.e whole permissions.

    - It is taken into account ONLY when creating a new file, to set its permission flags (on unix,
      the umask will be applied on these permissions first).
    - On windows, only the "user-write" flag is meaningful, its absence corresponding to a
      read-only file (note that contrary to unix, windows folders always behave as
      if they had a "sticky bit", so read-only files can't be moved/deleted).
    - These permissions have no influence on the ``open mode`` of the new stream,
      they only apply to future accesses to the newly created file.

    .. _file_opening_modes:
    
    .. rubric::
        ADVANCED FILE OPEN MODES
    
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

    'C'       File must NOT already exist (i.e it must be created, was "-" previously)
    'N'       File MUST already exist (i.e it must not be created, was "+" previously)

    'S'       Stream is Synchronized (by default, it's not)

    'I'       Stream is Inheritable by children processes (by default, it's not)

    'E'       File is Erased on opening (ignored when "C" is set, new file will be empty anyway)

    'B'       Stream is in Binary mode
    'T'       Stream is in Text mode (default)
    ========= ========================================================================================

    **Except readability/writability, all these flags are only taken into account when opening a new raw stream, not wrapping an existing fileno or handle.**

    Any combination of "R", "W", and "A" is possible, even though "W" is useless is "A" is set.

    "Append mode" is emulated by using seek() on windows (since FILE_APPEND_DATA flag would prevent any truncation
    of file) ; so file locking and thread-safe interface are necessary to ensure each single write is really
    done at the end of file. On unix-like systems, rsfile relies on a properly working O_APPEND flag ; note that
    locking and thread-safe interface might still be necessary, since multiple raw write() calls (which might
    happen during a single flush()) might end up writing disjoint bytes chunks on disk file, in case of concurrent
    access.

    By default, RSFile opening follows the "O_CREATE alone" semantic : files are created if not existing, else they're simply opened. "C" and "N" flags,  mutually exclusive, alter this behaviour. The old corresponding "-" and "+" flags, ambiguous, are deprecated but still supported.

    - with "C" (exclusive creation): file opening fails if the file already exists.
      This is the same semantic as (O_CREATE | O_EXCL) flags, which can be used to
      handle some security issues on unix filesystems. Note that O_EXCL is broken
      on NFS shares with a linux kernel < 2.6.5, so race conditions may occur in this case.
    - with "N" (must Not create) : file creation fails if the file doesn't exist already.

    If "S" (Synchronized) : opens the stream so that write operations don't return before file
    data *and* metadata get pushed to physical device. Note that due to potential caching in your hardware, it
    doesn't fully guarantee that your data will be safe in case of immediate crash. Using this
    flag for programs running on laptops might increase HDD power consumption, and thus reduce
    battery life. See also the :meth:`sync() <rsfile.rsiobase.RSIOBase.sync>` method of rsfile streams.

    If "I" (inheritable) : the raw file stream will be inheritable by child processes
    created via native subprocessing calls (spawn, fork+exec, CreateProcess...). By default, as was
    enforced in the stdlib since python3.4, streams are not inheritable.
    Note that sometimes child processes must be made aware of the file descriptors/handles
    that they own (this can be done through command-line arguments or other IPC means).

    "E" requires the stream to be writable ("W" or "A"), except if "C" is set (because then
    we're sure that the file will be empty on opening) ; note that this flag is ignored
    when wrapping an existing fileno/handle.

    "B" and "T" are mutually exclusive, and behave exactly like in :func:`io.open`.

    .. note::

        The "share-delete" semantic has been on enforced on windows as on unix, which means
        that files opened with this library can still be moved/deleted in the filesystem while
        they're open.

        However, on windows, deleting an open file may make it "stale": deletion
        returns a success status, but the filesystem enry is not really remove until the last
        handle to it is closed ; in the meantime, trying to reopen this file path will fail
        with a "busy" error. That's why "rename then remove" is a safier workflow when heavily
        interacting with the same file path.

    .. rubric::
        MODES COMPATIBILITY TABLE

    Here is an (autogenerated) table describing the different standard open modes,
    and their advanced equivalents.
    The deprecated "U" flag, as well as binary/text flags, are not mentioned here for clarity.
    The "x" mode flag was added in python3.3, for exclusive file creation.

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
        (raw_kwargs, extended_kwargs) = parse_standard_args(name, mode, fileno, handle, closefd)
    elif cleaned_mode.upper() == cleaned_mode:
        (raw_kwargs, extended_kwargs) = parse_advanced_args(name, mode, fileno, handle, closefd)
    else:
        raise defs.BadValueTypeError("bad mode string %r : it must contain only lower case (standard mode) or upper case (advanced mode) characters" % mode)

    # don't use interprocess facilities if fork() isn't supported, because file objects aren't pickleable for now...
    is_interprocess = raw_kwargs["inheritable"] and hasattr(os, "fork")
    thread_safe_interface = functools.partial(RSThreadSafeWrapper, mutex=mutex, is_interprocess=is_interprocess)

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
            # do not trigger the libc compatibility layer on windows,
            # since anyway it seems to have no st_blksize...
            if raw._fileno:
                try:
                    bs = os.fstat(raw._fileno).st_blksize
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
                    result = thread_safe_interface(raw)
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
                result = thread_safe_interface(buffer)
            return result

        text = RSTextIOWrapper(buffer, encoding, errors, newline, line_buffering)
        text.mode = mode # TODO - shouldn't we change that weird artefact of the stdlib ?
        result = text

        if thread_safe:
            result = thread_safe_interface(text)
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
        assert name is None or isinstance(name, basestring), name
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







