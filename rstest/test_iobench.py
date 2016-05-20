"""
Run iobench againts rsfile drop-in replacements.

In case you have an error like below, remove any pyc files, and run python with "-B" option, because iobench.py tries to read its own source file.
UnicodeDecodeError: 'utf8' codec can't decode byte 0xf3 in position 1: invalid continuation byte

"""
import sys
import rsfile
from rstest.stdlib import iobench
assert iobench.text_open, vars(iobench)


def _launch_iobench_tests():
    iobench.prepare_files()
    iobench.run_all_tests("rwtb")


if True:
    import io
    print ">>> benchmarking stdlib io module on python %s: module %r <<<" % (sys.version_info, io)

    iobench.open = io.open
    iobench.text_open = io.open
    _launch_iobench_tests()

    print "\n-----------\n"

if True:
    import _pyio
    print ">>> benchmarking stdlib pyio module on python %s: module %r <<<" % (sys.version_info, _pyio)

    iobench.open = _pyio.open
    iobench.text_open = _pyio.open
    _launch_iobench_tests()

    print "\n-----------\n"

if True:
    print ">>> benchmarking rsfile module <<<"

    iobench.open = rsfile.rsopen
    iobench.text_open = rsfile.rsopen
    _launch_iobench_tests()

    print "\n-----------\n"


""" # BACKUP OF LATEST BENCHMARK ITERATION #

>>> benchmarking stdlib io module on python sys.version_info(major=2, minor=7, micro=11, releaselevel='final', serial=0): module <module 'io' from 'C:\Python27\lib\io.pyc'> <<<
Preparing files...
Binary unit = one byte
Text unit = one character (utf8-decoded)

** Binary input **

[ 400KB ] read one unit at a time...                   4.07 MB/s
[ 400KB ] read 20 units at a time...                   68.8 MB/s
[ 400KB ] read 4096 units at a time...                  861 MB/s

[  20KB ] read whole contents at once...                297 MB/s
[ 400KB ] read whole contents at once...               2735 MB/s
[  10MB ] read whole contents at once...               1630 MB/s

[ 400KB ] seek forward one unit at a time...          0.672 MB/s
[ 400KB ] seek forward 1000 units at a time...          656 MB/s
[ 400KB ] alternate read & seek one unit...            3.57 MB/s
[ 400KB ] alternate read & seek 1000 units...           687 MB/s

** Text input **

[ 400KB ] read one unit at a time...                   3.71 MB/s
[ 400KB ] read 20 units at a time...                   51.2 MB/s
[ 400KB ] read one line at a time...                    140 MB/s
[ 400KB ] read 4096 units at a time...                  209 MB/s

[  20KB ] read whole contents at once...                150 MB/s
[ 400KB ] read whole contents at once...                310 MB/s
[  10MB ] read whole contents at once...                271 MB/s

[ 400KB ] seek forward one unit at a time...          0.199 MB/s
[ 400KB ] seek forward 1000 units at a time...          192 MB/s

** Binary append **

[  20KB ] write one unit at a time...                   1.6 MB/s
[ 400KB ] write 20 units at a time...                  30.4 MB/s
[ 400KB ] write 4096 units at a time...                1833 MB/s
[  10MB ] write 1e6 units at a time...                 2283 MB/s

** Text append **

[  20KB ] write one unit at a time...                 0.651 MB/s
[ 400KB ] write 20 units at a time...                  6.38 MB/s
[ 400KB ] write 4096 units at a time...                61.6 MB/s
[  10MB ] write 1e6 units at a time...                 62.9 MB/s

** Binary overwrite **

[  20KB ] modify one unit at a time...                 1.57 MB/s
[ 400KB ] modify 20 units at a time...                 28.8 MB/s
[ 400KB ] modify 4096 units at a time...                657 MB/s

[ 400KB ] alternate write & seek one unit...          0.177 MB/s
[ 400KB ] alternate write & seek 1000 units...          166 MB/s
[ 400KB ] alternate read & write one unit...           2.13 MB/s
[ 400KB ] alternate read & write 1000 units...          250 MB/s

** Text overwrite **

[  20KB ] modify one unit at a time...                0.518 MB/s
[ 400KB ] modify 20 units at a time...                 7.92 MB/s
[ 400KB ] modify 4096 units at a time...               59.7 MB/s


-----------

>>> benchmarking stdlib pyio module on python sys.version_info(major=2, minor=7, micro=11, releaselevel='final', serial=0): module <module '_pyio' from 'C:\Python27\lib\_pyio.pyc'> <<<
Preparing files...
Binary unit = one byte
Text unit = one character (utf8-decoded)

** Binary input **

[ 400KB ] read one unit at a time...                  0.511 MB/s
[ 400KB ] read 20 units at a time...                   9.66 MB/s
[ 400KB ] read 4096 units at a time...                  415 MB/s

[  20KB ] read whole contents at once...                214 MB/s
[ 400KB ] read whole contents at once...                992 MB/s
[  10MB ] read whole contents at once...                898 MB/s

[ 400KB ] seek forward one unit at a time...          0.178 MB/s
[ 400KB ] seek forward 1000 units at a time...          174 MB/s
[ 400KB ] alternate read & seek one unit...          0.0777 MB/s
[ 400KB ] alternate read & seek 1000 units...          74.2 MB/s

** Text input **

[ 400KB ] read one unit at a time...                  0.288 MB/s
[ 400KB ] read 20 units at a time...                   5.37 MB/s
[ 400KB ] read one line at a time...                   7.29 MB/s
[ 400KB ] read 4096 units at a time...                 65.4 MB/s

[  20KB ] read whole contents at once...               87.6 MB/s
[ 400KB ] read whole contents at once...                166 MB/s
[  10MB ] read whole contents at once...                149 MB/s

[ 400KB ] seek forward one unit at a time...         0.0672 MB/s
[ 400KB ] seek forward 1000 units at a time...         67.1 MB/s

** Binary append **

[  20KB ] write one unit at a time...                 0.306 MB/s
[ 400KB ] write 20 units at a time...                  5.85 MB/s
[ 400KB ] write 4096 units at a time...                 607 MB/s
[  10MB ] write 1e6 units at a time...                 1138 MB/s

** Text append **

[  20KB ] write one unit at a time...                 0.124 MB/s
[ 400KB ] write 20 units at a time...                   1.8 MB/s
[ 400KB ] write 4096 units at a time...                  53 MB/s
[  10MB ] write 1e6 units at a time...                 60.5 MB/s

** Binary overwrite **

[  20KB ] modify one unit at a time...                0.175 MB/s
[ 400KB ] modify 20 units at a time...                 3.37 MB/s
[ 400KB ] modify 4096 units at a time...                297 MB/s

[ 400KB ] alternate write & seek one unit...         0.0738 MB/s
[ 400KB ] alternate write & seek 1000 units...         68.4 MB/s
[ 400KB ] alternate read & write one unit...         0.0407 MB/s
[ 400KB ] alternate read & write 1000 units...         38.6 MB/s

** Text overwrite **

[  20KB ] modify one unit at a time...               0.0959 MB/s
[ 400KB ] modify 20 units at a time...                 1.77 MB/s
[ 400KB ] modify 4096 units at a time...               50.2 MB/s


-----------

>>> benchmarking rsfile module <<<
Preparing files...
Binary unit = one byte
Text unit = one character (utf8-decoded)

** Binary input **

[ 400KB ] read one unit at a time...                 0.0975 MB/s
[ 400KB ] read 20 units at a time...                   1.83 MB/s
[ 400KB ] read 4096 units at a time...                  171 MB/s

[  20KB ] read whole contents at once...                139 MB/s
[ 400KB ] read whole contents at once...                471 MB/s
[  10MB ] read whole contents at once...                310 MB/s

[ 400KB ] seek forward one unit at a time...         0.0512 MB/s
[ 400KB ] seek forward 1000 units at a time...           56 MB/s
[ 400KB ] alternate read & seek one unit...          0.0374 MB/s
[ 400KB ] alternate read & seek 1000 units...          36.5 MB/s

** Text input **

[ 400KB ] read one unit at a time...                  0.076 MB/s
[ 400KB ] read 20 units at a time...                   1.47 MB/s
[ 400KB ] read one line at a time...                   6.65 MB/s
[ 400KB ] read 4096 units at a time...                 51.7 MB/s

[  20KB ] read whole contents at once...               71.5 MB/s
[ 400KB ] read whole contents at once...                134 MB/s
[  10MB ] read whole contents at once...                114 MB/s

[ 400KB ] seek forward one unit at a time...         0.0341 MB/s
[ 400KB ] seek forward 1000 units at a time...         33.7 MB/s

** Binary append **

[  20KB ] write one unit at a time...                 0.081 MB/s
[ 400KB ] write 20 units at a time...                  1.59 MB/s
[ 400KB ] write 4096 units at a time...                 196 MB/s
[  10MB ] write 1e6 units at a time...                 1099 MB/s

** Text append **

[  20KB ] write one unit at a time...                0.0545 MB/s
[ 400KB ] write 20 units at a time...                  1.04 MB/s
[ 400KB ] write 4096 units at a time...                45.5 MB/s
[  10MB ] write 1e6 units at a time...                 61.2 MB/s

** Binary overwrite **

[  20KB ] modify one unit at a time...               0.0674 MB/s
[ 400KB ] modify 20 units at a time...                 1.31 MB/s
[ 400KB ] modify 4096 units at a time...                143 MB/s

[ 400KB ] alternate write & seek one unit...         0.0319 MB/s
[ 400KB ] alternate write & seek 1000 units...         30.5 MB/s
[ 400KB ] alternate read & write one unit...         0.0216 MB/s
[ 400KB ] alternate read & write 1000 units...         20.6 MB/s

** Text overwrite **

[  20KB ] modify one unit at a time...                0.047 MB/s
[ 400KB ] modify 20 units at a time...                0.903 MB/s
[ 400KB ] modify 4096 units at a time...               40.4 MB/s


"""
