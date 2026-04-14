
RSFile Streams
=======================

.. module:: rsfile.rsiobase


For filesystem-backed streams, RSFile follows the stdlib path protocol: wherever a file path is accepted,
you may pass a :class:`str`, :class:`bytes`, or :class:`os.PathLike` object such as :class:`pathlib.Path`.


Raw file stream constructor
---------------------------

.. currentmodule:: rsfile

.. autoclass:: RSFileIO


.. currentmodule:: rsfile.rsiobase


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

 
