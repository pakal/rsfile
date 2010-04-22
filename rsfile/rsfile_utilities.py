
from rsfile_factories import rsopen


    
# TODO - TEST THESE UTILITY METHODS !!!!

   
def read_from_file(filename, binary=False, buffering=None, encoding=None, errors=None, newline=None, locking=True, timeout=None): 
    """
    Returns the whole content of the file ``filename``, as a binary or unicode string 
    depending on the boolean ``binary``.
    
    Other arguments are the same as in :func:`rsfile.rsopen`.
    
    This function may raise **EnvironmentError** exceptions.
    """
    
    # TODO - To be added - "limit" argument, to retrieve only part of a file ???????? Nope ?
    
    mode = "R+"
    if binary: 
        mode += "B"
        
    
    with rsopen(filename, mode=mode, buffering=buffering, encoding=encoding, errors=errors, 
                newline=newline, locking=locking, timeout=timeout, thread_safe=False) as myfile:

        data_blocks = []
        while True:
            temp = myfile.readall() # Warning - change rsiopen so that we never get a raw file here !!!
            if not temp:
                break
            data_blocks.append(temp)
            
        if binary: joiner = ""
        else: joiner = u""   
            
        return joiner.join(data_blocks)
    
    
    
def write_to_file(filename, data, sync=False, must_create=False, must_not_create=False,
                  buffering=None, encoding=None, errors=None, newline=None, locking=True, timeout=None):    
    """
    Write the binary or unicode string ``data`` to the file ``filename``.
    
    Other arguments are the same as in the constructor of :class:`rsfile.RSFileIO` and in :func:`rsfile.rsopen`.
    
    This function may raise **EnvironmentError** exceptions.
    """

    mode = "WE" # we erase the file
    #if sync: mode += "S"   #  NO - final sync() will suffice
    if must_not_create:
        mode += "+"
    if must_create:
        mode += "-"
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
    
    Other arguments are the same as in the constructor of :class:`rsfile.RSFileIO` and in :func:`rsfile.rsopen`.
    
    This function may raise **EnvironmentError** exceptions.
    """
    
    mode = "A"
    #if sync: mode += "S"   #  NO - final sync() will suffice
    if must_not_create:
        mode += "+"
    if not isinstance(data, unicode):
        mode += "B"
    
    with rsopen(filename, mode=mode,
                buffering=buffering, encoding=encoding, errors=errors, 
                newline=newline, locking=locking, timeout=timeout, thread_safe=False) as myfile:
        
        myfile.write(data)
        myfile.flush()
        if sync:
            myfile.sync()
    

    
    
    