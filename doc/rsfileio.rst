
Advanced Streams
================

.. module:: rsfile


.. rubric::
	**Intermediary Streams**
	
Miscellaneous I/O streams have been created/modified to give access to the
advanced raw FileIO class described below. They can be found in the *rsfile*
as module, as classes named *RSBufferedReader*, *RSBufferedWriter*, *RSBufferedRandom*,
*RSTextIOWrapper* and *RSThreadSafeWrapper*.


.. rubric::
	**RSFileIO Streams**


.. autoclass:: RSFileIO
	
	
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