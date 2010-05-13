
Advanced Streams
================

.. module:: rsfile.rsiobase



RS Streams
-------------------------- 
    
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
    
    

    
 
    

New Raw Streams
---------------------

.. module:: rsfile

The replacement for **io.FileIO** has a quite different constructor, 
giving a far broader range of possible semantics, as well as some new attributes.

Note that the "share-delete" semantic has been on enforced on win32 as on unix, which means
that files opened with this library can still be moved/deleted in the filesystem while they're open.
However, on win32 it may result in "stale files", which are not really deleted until the last handle to them is closed.

.. autoclass:: RSFileIO
	
	
	.. rubric::
		**SPECIFIC OR MODIFIED ATTRIBUTES**
	
	.. autoattribute:: name
	
	.. autoattribute:: origin
	
	.. autoattribute:: mode
	
	
	
	
	
..	
	:show-inheritance:
	automethod:: lock_file
	:undoc-members:
	:member-order: groupwise
	:members: lock_file, seekable, closed