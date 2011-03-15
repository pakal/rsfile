.. RockSolidTools documentation master file, created by Pascal Chambon

Welcome to RockSolidTools' documentation!
==========================================

This mini-framework aims at providing cross-platform (unix/linux/mac/windows) object-oriented APIs for widely needed functionalities
like I/O streams, filesystem operations, inter-process communication, and generic transactional systems.

The focus is currently set on security and code robustness more than on execution speed, on comprehensive testing and documentation
more than on code optimization. 

RockSolidTools currently features three packages : **rsbackends** (a set of bridges to
native OS APIs - you shouldn't have to use it directly) and **rsfile** (a partial reimplementation 
of the standard io module, with advanced features), plus an optional **rstest** package to validate these. 


..
    However, on the long term cython augmentations might be developed in parallel, and compensate
    the slowness of these pure-python modules compared to stdlib C extensions.

    But below is an optimistic (megalomaniac?) dependency diagram of what RockSolidTools might 
    eventually contain.
    
    .. image:: rsModulesDiagram.png
        :width: 600


.. rubric::
	**Browse the documentation:**

.. toctree::
	:maxdepth: 4
	
	rsfile.rst	

.. rubric::
	**Sources, downloads, bugs:**

All is in the `Bitbucket Repository <http://bitbucket.org/pchambon/python-rock-solid-tools/>`_.
	
.. rubric::
	**Contacts:**

.. image:: email_pythoniks.png  

Any feedback / bug report is highly appreciated; but if you don't feel like subscribing to mailing-lists or bug trackers,
feel free to send an email at the address above.


	
	
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

