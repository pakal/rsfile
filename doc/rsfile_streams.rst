
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
        **IMPROVED METHODS**

    .. automethod:: truncate

    .. automethod:: close


    .. rubric::
        **ADDED METHODS**

    .. automethod:: fileno

    .. automethod:: handle

    .. automethod:: unique_id

    .. automethod:: size

    .. automethod:: times

    .. automethod:: sync
    
    .. automethod:: lock_file
    
    .. automethod:: unlock_file


    .. rubric::
        **IMPROVED OR ADDED ATTRIBUTES**

    .. autoattribute:: name

    .. autoattribute:: origin

    .. autoattribute:: mode

 
    

New Raw Streams
---------------------

.. module:: rsfile

The replacement for **io.FileIO** has a quite different constructor, 
giving a far broader range of possible semantics, as well as some new attributes.

Note that the "share-delete" semantic has been on enforced on windows as on unix, which means
that files opened with this library can still be moved/deleted in the filesystem while they're open.
However, on windows it may result in "stale files", which are not really deleted until the last handle to them is closed.

.. note::
    Rsfile streams implement __getattr__(), so that attributes are searched on wrapped streams if they can't be found on upper streams. Thus, the attributes of RSFileIO listed below, *name, origin and mode*, also exist on buffered
    and text streams from Rsfile.


	
..	
	:show-inheritance:
	automethod:: lock_file
	:undoc-members:
	:member-order: groupwise
	:members: lock_file, seekable, closed
