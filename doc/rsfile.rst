
rsfile package v1.0 alpha1
==========================

This modules currently provides pure-python reimplementations of parts of the stdlib **io** modules,
and is compliant with stdlib test suites.

It relies on the stdlib, ctypes extensions, and if available on pywin32 for the windows port.

The main goals of the current release are to get feedback on the API design, to stabilize it,
and to improve test suites in order to handle rare gotchas and platform-specific details.

.. toctree::
	:maxdepth: 2

	rsopen.rst
	rsfileio.rst
	utilities_options.rst	
	