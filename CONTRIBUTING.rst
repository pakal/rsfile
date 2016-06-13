Contributing to RSFile
========================

RSFile welcomes contributions like Reporting Bugs and Pull Requests.


TESTING
-----------

To launch the test suite (which reuses some stdlib testcases, and adds specific ones), install the stdlib test suite if needed (eg. on Ubuntu, install packages like "libpython2.7-testsuite"). Note that these tests can't all be executed inside the same runner process, since they monkey-patch their python environment differently.

    $ python -m  rsfile.rstest.test_rsfile_streams
    $ python -m  rsfile.rstest.test_rsfile_locking
    $ python -m  rsfile.rstest.test_rsfile_retrocompatibility

If you have installed python-tabulate (https://pypi.python.org/pypi/tabulate), the retrocompatibility test will display a table listing the different opening modes and their features.

To launch the performance benchmark, tweak the flags in rsfile/rstest/run_iobench.py to your liking,
maybe modify rsfileio_win32 to force a specific low-level backend (on windows), and then run:

    $ python -m  rsfile.rstest.run_iobench


BUILDING
-----------

To build the rsfile package:

    $ python setup.py sdist --formats=gztar,zip

No need for `bdist_msi` or the weaker `bdist_wininst`: there is no automated 2to3 conversion with them, and rsfile is pure-python anyway, so no binary distribution is needed.


