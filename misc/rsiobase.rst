
Advanced Streams
================

.. module:: rsfile.rsiobase


.. rubric::
    **Intermediary Streams**
    
    
Miscellaneous I/O streams have been created/modified to give access to the
advanced raw FileIO class described below. They can be found in the *rsfile*
module, as classes named *RSBufferedReader*, *RSBufferedWriter*, *RSBufferedRandom*,
*RSTextIOWrapper* and *RSThreadSafeWrapper*. They implement all methods from the original
io.IOBase abstract class, with the new methods and semantics described below in their parent class *RSIOBase*.




.. autoclass:: RSIOBase
    
    
    .. rubric::
        **SPECIFIC OR MODIFIED METHODS**
    
    .. automethod:: close
    
    .. automethod:: fileno
    
    .. automethod:: handle
    
    .. automethod:: size
    
    .. automethod:: sync
    
    .. automethod:: times
    
    .. automethod:: uid
    
    
    .. rubric::
        **LOCKING SYSTEM**
    
    .. automethod:: lock_file
    
    .. automethod:: unlock_file
    
    

    
    
    
    
    
..    
    :show-inheritance:
    automethod:: lock_file
    :undoc-members:
    :member-order: groupwise
    :members: lock_file, seekable, closed