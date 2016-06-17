Contributing to RSFile
========================

RSFile welcomes contributions like Reporting Bugs and Pull Requests.


TESTING
++++++++++


The test suites of RSFile can be run against any compatible python2/3 interpreter installed on your system.
Since they reuse many stdlib testcases, you must have the "python test suite" installed for the selected interpreter version, else only a subset of RSFile tests will be run.
On Windows this test suite must have been selected during install, on Linux you must install separate packages like "libpythonX.Y-testsuite", etc.


Testing using TOX
---------------------

- install the latest versions of pip, virtualenv and tox
- run tox from the folder containing setup.py (possibly with "-e pyXY" or "-e doc" to select a specific environement):

$ tox

This will install RSFile into a virtual environment, and launch the test suites.

If tox fails when creating py35 environment on windows ("The program can't start because VCRUNTIME140.dll is missing from your computer."), you might need to use "virtualenv-rewrite" instead of "virtualenv", for details see https://github.com/pypa/virtualenv/issues/796


Testing manually
-----------------

To manually launch the test suites against a specific "python" interpreter, use the different commands visible in the "tox.ini", in the form **python -m rsfile.rstest.xxxxxxx**

Note that these *.py test files can't all be executed inside the same runner process, since they monkey-patch their python environment differently.

Also, double-check that the "rsfile" package imported is well the one you meant, since the current working directory is usually automatically added to your python "sys.path" on launch.

If you have installed python-tabulate (https://pypi.python.org/pypi/tabulate), the retrocompatibility test will display a table listing the different file opening modes, and their features.


Benchmarking
+++++++++++++

To launch performance benchmarks, tweak the flags in rsfile/rstest/run_iobench.py to your liking,
maybe modify rsfileio_win32.py to force a specific low-level backend (if on Windows), and then run:

    $ python -m  rsfile.rstest.run_iobench

Again, be aware of possible confusion between an installed and a "current dir" rsfile packages.


BUILDING
++++++++++

To build the rsfile package:

    $ python setup.py sdist --formats=gztar,zip

No need for `bdist_msi` or the weaker `bdist_wininst`: there is no automated 2to3 conversion when using them, and rsfile is pure-python anyway, so no binary distribution is needed.


