

    
class ThreadSafeWrapper(object):
    """A quick wrapper, to ensure thread safety !
    If a threading or multiprocessing mutex is provided, it will be used for locking,
    else a multiprocessing or multithreading (depending on *interprocess* boolean value) will be created."""
    def __init__(self, wrapped_obj, mutex=None, interprocess=False):
        self.wrapped_obj = wrapped_obj
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
            return getattr(self.wrapped_obj, name)(*args, **kwargs)
    
    
    def __getattr__(self, name):
        attr = getattr(self.wrapped_obj, name) # might raise AttributeError
        if isinstance(attr, collections.Callable):  # actually, we shouldn't care about others than types.MethodType, types.LambdaType, types.FunctionType
            return functools.partial(self._secure_call, name)
        else:
            return attr
    
    def __iter__(self):
        return iter(self.wrapped_obj)
        
    def __str__(self):
        return "Thread Safe Wrapper around %s" % self.wrapped_obj
    
    def __repr__(self):
        return "ThreadSafeWrapper(%r)" % self.wrapped_obj


    def __enter__(self):
        """Context management protocol.  Returns self."""
        self._checkClosed()
        return self

    def __exit__(self, *args):
        """Context management protocol.  Calls close()"""
        self.close()
    
   




### HERE DEFINE ADVANCED BUFFER AND TEXT INTERFACES !!!!!!!!!!!



