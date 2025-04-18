# -*- coding: utf-8 -*-


import functools
import multiprocessing
import os
import threading

from . import rsfile_definitions as defs

if defs.RSFILE_IMPLEMENTATION == "windows":  # even on 64bits windows OS
    try:
        from .rsfileio_windows import RSFileIO
    except Exception as e:
        raise ImportError("No windows backend available : %s" % e)
else:
    assert defs.RSFILE_IMPLEMENTATION == "unix"
    try:
        from .rsfileio_unix import RSFileIO
    except Exception as e:
        raise ImportError("No unix backend available : %s" % e)


def __rsfile_stream_repr__(self):
    clsname = self.__class__.__name__
    try:
        name = self.name
    except AttributeError:
        return "<%s>" % clsname
    else:
        return "<%s name=%r>" % (clsname, name)

class _buffer_forwarder_mixin(object):
    def _reset_buffers(self):
        self.seek(0, os.SEEK_CUR)  # we flush i/o buffers, didn't work on py26

    def unique_id(self):
        return self.raw.unique_id()

    def times(self):
        return self.raw.times()

    def size(self):
        self.flush()
        return self.raw.size()

    def sync(self, *args, **kwargs):
        self.flush()
        return self.raw.sync(*args, **kwargs)

    def lock_file(self, *args, **kwargs):
        self._reset_buffers()
        return self.raw.lock_file(*args, **kwargs)

    def unlock_file(self, *args, **kwargs):
        self._reset_buffers()
        return self.raw.unlock_file(*args, **kwargs)

    def ___USELESS__close(self):
        if not self.closed:
            try:
                # may raise BlockingIOError or BrokenPipeError etc
                self.flush()
            finally:
                self.raw.close()

    __repr__ = __rsfile_stream_repr__

    def __getattr__(self, name):
        # print ("--> taking ", name, "in ", self)
        raw = self.__dict__.get("_raw")  # beware here - we avoid infinite recursion on getattr !
        if raw is None or callable(raw):
            raise AttributeError("Attribute '_raw' not found on RSBufferedStream (uninitialized?)")  # problem...
        return getattr(raw, name)


class _text_forwarder_mixin(object):
    def _reset_buffers(self):
        self.seek(0, os.SEEK_CUR)  # we flush i/o buffers, didn't work on py26

    def unique_id(self):
        return self.buffer.unique_id()

    def times(self):
        return self.buffer.times()

    def size(self):
        self.flush()  # security
        return self.buffer.size()

    def sync(self, *args, **kwargs):
        self.flush()  # security
        return self.buffer.sync(*args, **kwargs)

    def lock_file(self, *args, **kwargs):
        self._reset_buffers()
        return self.buffer.lock_file(*args, **kwargs)

    def unlock_file(self, *args, **kwargs):
        self._reset_buffers()
        return self.buffer.unlock_file(*args, **kwargs)

    def readinto(self, buffer):  # to please test suite...
        self._checkClosed()
        raise defs.BadValueTypeError("Text stream can't be read into buffer")

    __repr__ = __rsfile_stream_repr__

    def __getattr__(self, name):
        # print ("--> taking ", name, "in ", self)
        buffer = self.__dict__.get("_buffer")  # beware here - we avoid infinite recursion on getattr !
        if buffer is None or callable(buffer):
            raise AttributeError("Attribute '_buffer' not found on RSTextIO (uninitialized?)")  # problem...
        return getattr(buffer, name)


### EXTENDED BUFFER AND TEXT STREAMS !!!!!!!!


# We have to tweak readable/writable methods of RSBufferedReader and RSBufferedWriter, buggy on python<=3.5 #

if defs.io_module._BufferedIOMixin.__dict__.get("readable"):
    del defs.io_module._BufferedIOMixin.readable
if defs.io_module._BufferedIOMixin.__dict__.get("writable"):
    del defs.io_module._BufferedIOMixin.writable


class RSBufferedReader(_buffer_forwarder_mixin, defs.io_module.BufferedReader):
    def readable(self):  # drop when py3.5 not supported anymore
        return self.raw.readable()


class RSBufferedWriter(_buffer_forwarder_mixin, defs.io_module.BufferedWriter):
    def writable(self):  # drop when py3.5 not supported anymore
        return self.raw.writable()


# class RSBufferedRandom(defs.io_module.BufferedRandom, _buffer_forwarder_mixin):  # future C extension version
#    pass

# awkward structure to have all methods/inheritance-relations OK even when monkey patching
class RSBufferedRandom(defs.io_module.BufferedRandom, RSBufferedWriter, RSBufferedReader):
    pass


class RSTextIOWrapper(_text_forwarder_mixin, defs.io_module.TextIOWrapper):
    pass


class RSThreadSafeWrapper(object):
    """
    A quick wrapper, to ensure thread safety !

    If a threading or multiprocessing mutex is provided, it will be used for locking,
    else a multiprocessing or multithreading (depending on *is_interprocess* boolean value) will be created.
    """

    def __init__(self, wrapped_stream, mutex=None, is_interprocess=False):
        self.wrapped_stream = wrapped_stream
        self.is_interprocess = is_interprocess

        if mutex is not None:
            self.mutex = mutex
        else:
            if is_interprocess:
                self.mutex = multiprocessing.RLock()
            else:
                self.mutex = threading.RLock()

    def _secure_call(self, name, *args, **kwargs):
        with self.mutex:
            return getattr(self.wrapped_stream, name)(*args, **kwargs)

    def __getattr__(self, name):

        attr = getattr(self.wrapped_stream, name)  # might raise AttributeError

        if not name.startswith("_") and callable(attr):
            # print ("<<<<<<< WRAPPING METHOD", name)
            def _method_proxy(*args, **kwargs):
                return self._secure_call(name, *args, **kwargs)
            # IMPORTANT : cache the thread-safe caller in object, so that we bypass this __getattr__ next time
            setattr(self, name, _method_proxy)

        return attr

    def __iter__(self):
        return iter(self.wrapped_stream)

    def __str__(self):
        return "Thread Safe Wrapper around %s" % self.wrapped_stream

    def __repr__(self):
        return "<RSThreadSafeWrapper around %r>" % self.wrapped_stream

    def __enter__(self):
        """Context management protocol.  Returns self."""
        self._checkClosed()
        return self

    def __exit__(self, *args):
        """Context management protocol.  Calls close()"""
        self.close()
