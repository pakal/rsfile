#-*- coding: utf-8 -*-
from __future__ import with_statement


import sys, os
import functools


from rsfileio_abstract import RSFileIOAbstract

from rsfile_definitions import * # constants, base types and exceptions
from rsfile_streams import *
from rsfile_factories import *
from rsfile_registries import set_rsfile_options, get_rsfile_options
from rsfile_utilities import *



 
def monkey_patch_original_io_module(module=None): 
    """
    Replaces standard file streams of module *module* (FileIO, BufferedReader, BufferedWriter,
    BufferedRandom, and TextIOWrapper), as well as its open() factory, by RsFile versions with compatible signatures.
    
    By default *module* is the standard *io* module, but you may specify *_pyio* (the stdlib pure python version)
    or another io implementations to be patched.
    """
    
    if module is None:
        import io
        module = io
    
    if not hasattr(module, "UnsupportedOperation"):
        module.UnsupportedOperation = io_module.UnsupportedOperation # old io hasn't it
        
    
    # we replace the most basic file io type by a backward-compatible but enhanced version
    class RSFileIORawWrapper(RSFileIO):
        """
        Interface to rsFile accepting the limited "fopen()" modes (no file locking, no O_EXCL|O_CREAT semantic...)
        """
        def __init__(self, name, mode="r", closefd=True):
            
            (raw_kwargs, extended_kwargs) = parse_standard_args(name, mode, None, None, closefd)
            if extended_kwargs["text"]:
                raise ValueError("Raw stream can't be created in text mode")
            
            RSFileIO.__init__(self, **raw_kwargs)
            if extended_kwargs["truncate"]:
                # HERE, ERROR IF FILE NOT WRITABLE !!!! PAKAL
                self.truncate(0) # Warning - this raw wrapper mimics basic rawFileIO, and doesn't use locking !!!!
    
    # Important Patching ! #
    module.FileIO = RSFileIORawWrapper  
    module.BufferedReader = RSBufferedReader
    module.BufferedWriter = RSBufferedWriter
    module.BufferedRandom = RSBufferedRandom
    module.TextIOWrapper = RSTextIOWrapper
    module.open = functools.partial(rsopen, handle=None, locking=False, timeout=0, thread_safe=False, mutex=None, permissions=0777) 

    
    """ # OLD, very magical monkey patching of buffer/text classes
        # New, use inherited classes of rsfile_streams instead
    
    # We implant proxies for new rawFileIo methods, in buffer and text base classes
    def generate_method_forwarder(underlying_object, attribute_name, must_reset):
        import rsfileio_abstract
        @functools.wraps(getattr(rsfileio_abstract.AbstractRSFileIO, attribute_name))
        def method_forwarder(self, *args, **kwargs):
            if must_reset:
                self.seek(self.tell()) # Pakal - to change when io module fixed !!!
                # # # # self.seek(0, os.SEEK_CUR) # we flush i/o buffers !
            return getattr(getattr(self, underlying_object), attribute_name)(*args, **kwargs) # we call the method of the underlying object
        return method_forwarder
    
    new_methods = ("uid", "times", "size", "sync", "lock_file", "unlock_file")
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
    
    """
    
    
if __name__ == '__main__':
    monkey_patch_original_io_module()
    
        
#contract.checkmod(module)  # UNCOMMENT THIS TO ACTIVATE PYCONTRACT CHECKING    

