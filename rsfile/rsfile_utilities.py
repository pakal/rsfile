# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from .rsfile_definitions import *  # constants, base types and exceptions
from .rsfile_streams import *
from .rsfile_factories import *


def BUILTIN_OPEN_FUNC_REPLACEMENT(*args, **kwargs):
    """
    Replacement for the built-in open() function,
    with rectified default arguments, and
    tolerant mode for str/unicode mixes in python2.
    """
    params = dict(handle=None, locking=False, timeout=0,
                    thread_safe=False, mutex=None, permissions=0o777)
    params.update(kwargs)
    stream = rsopen(*args, **params)
    stream._tolerant_mode = True  # py27 str/unicode coercion when using open() builtin
    return stream

# HACK, else, it becomes a bound method in test suites...
BUILTIN_OPEN_FUNC_REPLACEMENT = functools.partial(BUILTIN_OPEN_FUNC_REPLACEMENT)

def monkey_patch_io_module(module=None):
    """
    Replaces standard file streams of module *module* (i.e classes FileIO, BufferedReader, BufferedWriter,
    BufferedRandom, and TextIOWrapper), as well as its open() factory, by RSFile versions with compatible signatures.
    
    By default *module* is the standard *io* module, but you may provide *_pyio* (the stdlib pure python version),
    *_io* (the C extension module behind *io*) instead.
    """

    if module is None:
        import io
        module = io

    # we replace the most basic file io type by a backward-compatible but enhanced version
    class RSFileIORawWrapper(RSFileIO):
        """
        Interface to rsFile accepting the limited "fopen()" modes (no file locking, no O_EXCL|O_CREAT semantic...)
        """

        def __init__(self, name, mode="r", closefd=True):

            (raw_kwargs, extended_kwargs) = parse_standard_args(name, mode, None, None, closefd)
            if extended_kwargs["text"]:
                raise BadValueTypeError("Raw stream can't be created in text mode")
            RSFileIO.__init__(self, **raw_kwargs)
            if extended_kwargs["truncate"]:
                self.truncate(0)  # this mimicks basic rawFileIO, without file locking

    # Important Patching ! #
    module.FileIO = RSFileIORawWrapper
    module.BufferedReader = RSBufferedReader
    module.BufferedWriter = RSBufferedWriter
    module.BufferedRandom = RSBufferedRandom
    module.TextIOWrapper = RSTextIOWrapper

    new_open = BUILTIN_OPEN_FUNC_REPLACEMENT
    module.open = new_open


def monkey_patch_open_builtin():
    """
    Replaces the default open() builtin with a version compatible in signature and semantic (no file locking or
    thread safety on stream opening), which returns rsfile streams on invocation.
    """

    new_open = BUILTIN_OPEN_FUNC_REPLACEMENT

    try:
        import __builtin__
        __builtin__.open = new_open
    except ImportError:
        import builtins
        builtins.open = new_open


# ---------------------


def read_from_file(filename, binary=False, buffering=None, encoding=None, errors=None, newline=None, locking=True,
                   timeout=None):
    """
    Returns the *whole* content of the file ``filename``, as a binary or unicode string
    depending on the boolean ``binary``.
    
    Other arguments are similar to those of :func:`rsfile.rsopen`.

    Don't use on huge files, of course.

    This function may raise *EnvironmentError* exceptions.
    """

    mode = "R+"
    if binary:
        mode += "B"

    with rsopen(filename, mode=mode, buffering=buffering, encoding=encoding, errors=errors,
                newline=newline, locking=locking, timeout=timeout, thread_safe=False) as myfile:

        data_blocks = []
        while True:
            temp = myfile.read()  # if unbuffered, might return very little data, so we have to "loop while"
            if not temp:
                break

            data_blocks.append(temp)

        if binary:
            joiner = b""
        else:
            joiner = ""

        full_data = joiner.join(data_blocks)
        return full_data


def write_to_file(filename, data, sync=False, must_create=False, must_not_create=False,
                  buffering=None, encoding=None, errors=None, newline=None, locking=True, timeout=None):
    """
    Write the binary or unicode string ``data`` to the file ``filename``.
    
    Other arguments are similar to those of :func:`rsfile.rsopen`.
    
    This function may raise *EnvironmentError* exceptions.
    """

    mode = "WE"  # we erase the file, no need for "S", final sync() will suffice
    if must_not_create:
        mode += "N"
    if must_create:
        mode += "C"
    if not isinstance(data, unicode):
        mode += "B"

    with rsopen(filename, mode=mode,
                buffering=buffering, encoding=encoding, errors=errors,
                newline=newline, locking=locking, timeout=timeout, thread_safe=False) as myfile:

        myfile.write(data)
        myfile.flush()
        if sync:
            myfile.sync()


def append_to_file(filename, data, sync=False, must_not_create=False,
                   buffering=None, encoding=None, errors=None, newline=None, locking=True, timeout=None):
    """
    Append the binary or unicode string ``data`` to the file ``filename``.
    
    Other arguments are similar to those of :func:`rsfile.rsopen`.
    
    This function may raise *EnvironmentError* exceptions.
    """

    mode = "A"  # no need for "S", final sync() will suffice

    if must_not_create:
        mode += "N"
    if not isinstance(data, unicode):
        mode += "B"

    with rsopen(filename, mode=mode,
                buffering=buffering, encoding=encoding, errors=errors,
                newline=newline, locking=locking, timeout=timeout, thread_safe=False) as myfile:

        myfile.write(data)
        myfile.flush()
        if sync:
            myfile.sync()
