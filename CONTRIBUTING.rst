Contributing to RSFile
========================

RSFile welcomes contributions like Reporting Bugs and Pull Requests.


TESTING
++++++++++


The test suites of RSFile can be run against any compatible python3 interpreter installed on your system.
Since they reuse many stdlib testcases, you must have the "python test suite" installed for the selected interpreter version, else only a subset of RSFile tests will be run.
On Windows this test suite must have been selected during install, on Linux you must install separate packages like "libpythonX.Y-testsuite", etc.

.. note::
    Some tests, like those concerning open() mode equivalences, or locking, are long to execute,
    so as long as the test process consumes CPU, they're probably still working normally. Other tests, mainly
    concerning large files, are disabled by default and must be manually enabled by editing flags in test
    files (see ENABLE_LARGE_FILE_TESTS variable).



Testing using TOX
---------------------

- Install the latest versions of pip, virtualenv and tox
- Run tox from the root folder (possibly with "-e pyXY" or "-e doc" to select a specific environment):

$ tox

This will install RSFile into a virtual environment, and launch the test suites.


Testing manually
-----------------

To manually launch the test suites against a specific "python" interpreter, use the different commands visible in the "tox.ini", in the form **python -m rsfile.rstest.xxxxxxx**. The "src/" folder must be in your current python paths (ex. by using PYTHONPATH environment variable, or by pip-installing the repository in "editable" mode).

Note that these *.py test files can't all be executed inside the same runner process (ex. using pytest), since they monkey-patch their python environment differently.

If you have installed python-tabulate (https://pypi.python.org/pypi/tabulate), the retrocompatibility test will display a table listing the different file opening modes, and their features.


Checking code coverage
------------------------

The "generate_coverage_report.py" script launches the different tests, and aggregates their results in an HTML coverage report.

Note that because some tests launch subprocesses, not all code executions might be detected, see
http://coverage.readthedocs.io/en/coverage-4.1/subprocess.html
for information on how to workaround this problem.


Benchmarking
+++++++++++++

To launch performance benchmarks, tweak the flags in rsfile/rstest/run_iobench.py to your liking,
maybe modify rsfileio_win32.py to force a specific low-level backend (if on Windows), and then run:

    $ python -m  rsfile.rstest.run_iobench


BUILDING
++++++++++

To build the rsfile package, use the standard setuptools "build" command: https://setuptools.pypa.io/en/latest/userguide/quickstart.html

Rsfile is pure-python, so buildings wheels is not necessary.


