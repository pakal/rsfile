Handy Utilities and Options
============================


.. module:: rsfile
    :noindex:


RSFile Utilities
-------------------

.. autofunction:: read_from_file

.. autofunction:: write_to_file

.. autofunction:: append_to_file


.. _rsfile-options:

RSFile Options
-------------------
	
.. autofunction:: set_rsfile_options

.. autofunction:: get_rsfile_options


.. _rsfile-patching:

RSFile Stdlib Patching
------------------------

These monkey-patchers are used massively to test rsfile against the stdlib test suite.

.. autofunction:: monkey_patch_io_module

.. autofunction:: monkey_patch_open_builtin



