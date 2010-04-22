
import sys, multiprocessing, threading, functools, collections, io


if sys.platform == 'win32':
    try:
        from rsfileio_win32 import RSFileIO
        FILE_IMPLEMENTATION = "win32"
    except Exception, e:
        raise ImportError("No win32 backend available : %s" % e)
else:
    try:
        from rsfileio_unix import RSFileIO
        FILE_IMPLEMENTATION = "unix"
    except Exception, e:
        raise ImportError("No unix backend available : %s" % e)



class _buffer_forwarder_mixin(object):
    
    def _reset_buffers(self):
        self.seek(self.tell()) # Warning - does not work in Py2.6, buffered seek is buggy there !
        # # # # self.seek(0, os.SEEK_CUR) # we flush i/o buffers !

    def uid(self):
        return self.raw.uid()
    
    def times(self):
        return self.raw.times()
    
    def size(self):
        self.flush()
        return self.raw.size()
    
    def sync(self, *args, **kwargs):
        return self.raw.sync(*args, **kwargs)
    
    def lock_file(self, *args, **kwargs):
        self._reset_buffers()
        return self.raw.lock_file(*args, **kwargs)

    def unlock_file(self, *args, **kwargs):
        self._reset_buffers()
        return self.raw.unlock_file(*args, **kwargs)

    def close(self):
        if not self.closed:
            self.flush() # we do NOT swallow exceptions !
            self.raw.close()
                  
    def __getattr__(self, name):
        # print "--> taking ", name, "in ", self
        raw = object.__getattribute__(self, "raw") # warning - avoid infinite recursion on getattr !
        return getattr(raw, name)  



class _text_forwarder_mixin(object):    
    
    def _reset_buffers(self):
        self.seek(self.tell()) # Pakal - todo - change when io module fixed !!!
        # # # # self.seek(0, os.SEEK_CUR) # we flush i/o buffers !

    def uid(self):
        return self.buffer.uid()
    
    def times(self):
        return self.buffer.times()
    
    def size(self):
        self.flush()
        return self.buffer.size()
    
    def sync(self, *args, **kwargs):
        return self.buffer.sync(*args, **kwargs)
    
    def lock_file(self, *args, **kwargs):
        self._reset_buffers()
        return self.buffer.lock_file(*args, **kwargs)

    def unlock_file(self, *args, **kwargs):
        self._reset_buffers()
        return self.buffer.unlock_file(*args, **kwargs)
    
    def close(self):
        if not self.closed:
            self.flush() # we do NOT swallow exceptions !
            self.buffer.close()
            
    def __getattr__(self, name):
        # print "--> taking ", name, "in ", self
        buffer = object.__getattribute__(self, "buffer") # warning - avoid infinite recursion on getattr !
        return getattr(buffer, name)    
    
    
    
### HERE EXTEND ADVANCED BUFFER AND TEXT INTERFACES !!!!!!!!

class RSBufferedReader(_buffer_forwarder_mixin, io.BufferedReader):
    pass

class RSBufferedWriter(_buffer_forwarder_mixin, io.BufferedWriter):
    pass

# awkward structure to have all methods/inheritance-relations OK even when monkey patching
class RSBufferedRandom(io.BufferedRandom, RSBufferedWriter, RSBufferedReader): 
    pass
    
class RSTextIOWrapper(_text_forwarder_mixin, io.TextIOWrapper):
    pass




    
class RSThreadSafeWrapper(object):
    """A quick wrapper, to ensure thread safety !
    If a threading or multiprocessing mutex is provided, it will be used for locking,
    else a multiprocessing or multithreading (depending on *interprocess* boolean value) will be created."""
    def __init__(self, wrapped_stream, mutex=None, interprocess=False):
        self.wrapped_stream = wrapped_stream
        self.interprocess = interprocess
        
        if mutex is not None:
            self.mutex = mutex
        else:
            if interprocess:
                self.mutex = multiprocessing.RLock()
            else:
                self.mutex = threading.RLock()
                
    def _secure_call(self, name, *args, **kwargs):
        with self.mutex:
            #print "protected!"
            return getattr(self.wrapped_stream, name)(*args, **kwargs)
    
    
    def __getattr__(self, name):
        attr = getattr(self.wrapped_stream, name) # might raise AttributeError
        if isinstance(attr, collections.Callable):  # actually, we shouldn't care about others than types.MethodType, types.LambdaType, types.FunctionType
            return functools.partial(self._secure_call, name)
        else:
            return attr
    
    def __iter__(self):
        return iter(self.wrapped_stream)
        
    def __str__(self):
        return "Thread Safe Wrapper around %s" % self.wrapped_stream
    
    def __repr__(self):
        return "RSThreadSafeWrapper(%r)" % self.wrapped_stream


    def __enter__(self):
        """Context management protocol.  Returns self."""
        self._checkClosed()
        return self

    def __exit__(self, *args):
        """Context management protocol.  Calls close()"""
        self.close()
    
   




