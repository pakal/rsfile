# -*- coding: utf-8 -*-
"""
Run iobench against rsfile drop-in replacements.

"""


import sys

import rsfile
from rsfile.rstest.stdlib import iobench

# Select here the versions of the IO API which need to be benchmarked #
RUN_STDLIB_CIO = True
RUN_STDLIB_PYIO = True
RUN_RSFILE = True  # exact OS backend depends on what's installed, see rsfileio_xxx.py and rsbackend


def launch_benchmark():
    # HACK to ignore iobench.pyc file automatically, so that when iobench tries to access his "__file__", it works.
    # This should solve "UnicodeDecodeError: 'utf8' codec can't decode byte 0xf3 in position 1: invalid continuation
    # byte" error when running iobench.
    iobench.__file__ = iobench.__file__.rstrip("c")
    assert iobench.text_open, vars(iobench)

    def _launch_iobench_tests():
        iobench.prepare_files()
        iobench.run_all_tests("rwtb")

    if RUN_STDLIB_CIO:
        import io

        print(">>> benchmarking stdlib io module on python %s: module %r <<<" % (sys.version_info, io))

        iobench.open = io.open
        iobench.text_open = io.open
        _launch_iobench_tests()

        print("\n-----------\n")

    if RUN_STDLIB_PYIO:
        import _pyio

        print(">>> benchmarking stdlib pyio module on python %s: module %r <<<" % (sys.version_info, _pyio))

        iobench.open = _pyio.open
        iobench.text_open = _pyio.open
        _launch_iobench_tests()

        print("\n-----------\n")

    if RUN_RSFILE:
        print(">>> benchmarking rsfile module <<<")

        iobench.open = rsfile.rsopen
        iobench.text_open = rsfile.rsopen
        _launch_iobench_tests()

        print("\n-----------\n")


if __name__ == "__main__":
    launch_benchmark()

    
""" # BACKUP OF LATEST BENCHMARK ITERATION #

>>> benchmarking stdlib io module on python sys.version_info(major=3, minor=12, micro=0, releaselevel='beta', serial=4): module <module 'io' (frozen)> <<<
Preparing files...
Python 3.12.0b4 (tags/v3.12.0b4:97a6a41, Jul 11 2023, 13:49:15) [MSC v.1935 64 bit (AMD64)]
Unicode: PEP 393
Windows-11-10.0.22621-SP0
Binary unit = one byte
Text unit = one character (utf8-decoded)

** Binary input **

[ 400KiB] read one unit at a time...                  35.6 MiB/s
 warning: test above used only 60.246130% CPU, result may be flawed!
[ 400KiB] read 20 units at a time...                   543 MiB/s
 warning: test above used only 46.844480% CPU, result may be flawed!
[ 400KiB] read 4096 units at a time...                4945 MiB/s
 warning: test above used only 59.362064% CPU, result may be flawed!

[ 20KiB ] read whole contents at once...              1332 MiB/s
 warning: test above used only 60.411011% CPU, result may be flawed!
[ 400KiB] read whole contents at once...             17129 MiB/s
 warning: test above used only 72.881844% CPU, result may be flawed!
[ 10MiB ] read whole contents at once...              6855 MiB/s
 warning: test above used only 58.294010% CPU, result may be flawed!

[ 400KiB] seek forward one unit at a time...          2.22 MiB/s
 warning: test above used only 51.405964% CPU, result may be flawed!
[ 400KiB] seek forward 1000 units at a time...        2163 MiB/s
 warning: test above used only 62.460438% CPU, result may be flawed!
[ 400KiB] alternate read & seek one unit...           26.9 MiB/s
 warning: test above used only 50.777507% CPU, result may be flawed!
[ 400KiB] alternate read & seek 1000 units...         3893 MiB/s
 warning: test above used only 68.730555% CPU, result may be flawed!

** Text input **

[ 400KiB] read one unit at a time...                  29.2 MiB/s
 warning: test above used only 47.535803% CPU, result may be flawed!
[ 400KiB] read 20 units at a time...                   306 MiB/s
 warning: test above used only 52.026357% CPU, result may be flawed!
[ 400KiB] read one line at a time...                   624 MiB/s
 warning: test above used only 51.024781% CPU, result may be flawed!
[ 400KiB] read 4096 units at a time...                1025 MiB/s
 warning: test above used only 51.024360% CPU, result may be flawed!

[ 20KiB ] read whole contents at once...               674 MiB/s
 warning: test above used only 53.119630% CPU, result may be flawed!
[ 400KiB] read whole contents at once...               737 MiB/s
 warning: test above used only 46.854259% CPU, result may be flawed!
[ 10MiB ] read whole contents at once...               954 MiB/s
 warning: test above used only 54.908562% CPU, result may be flawed!

[ 400KiB] seek forward one unit at a time...          1.09 MiB/s
 warning: test above used only 51.348388% CPU, result may be flawed!
[ 400KiB] seek forward 1000 units at a time...        1058 MiB/s
 warning: test above used only 70.797223% CPU, result may be flawed!

** Binary append **

[ 20KiB ] write one unit at a time...                 13.6 MiB/s
 warning: test above used only 77.061274% CPU, result may be flawed!
[ 400KiB] write 20 units at a time...                  242 MiB/s
 warning: test above used only 38.498203% CPU, result may be flawed!
[ 400KiB] write 4096 units at a time...               7673 MiB/s
 warning: test above used only 44.782100% CPU, result may be flawed!
[ 10MiB ] write 1e6 units at a time...               15452 MiB/s
 warning: test above used only 62.495262% CPU, result may be flawed!

** Text append **

[ 20KiB ] write one unit at a time...                 5.28 MiB/s
 warning: test above used only 53.074401% CPU, result may be flawed!
[ 400KiB] write 20 units at a time...                 38.5 MiB/s
 warning: test above used only 78.075932% CPU, result may be flawed!
[ 400KiB] write 4096 units at a time...                266 MiB/s
 warning: test above used only 70.769813% CPU, result may be flawed!
[ 10MiB ] write 1e6 units at a time...                 268 MiB/s
 warning: test above used only 36.862531% CPU, result may be flawed!

** Binary overwrite **

[ 20KiB ] modify one unit at a time...                13.1 MiB/s
 warning: test above used only 44.790293% CPU, result may be flawed!
[ 400KiB] modify 20 units at a time...                 233 MiB/s
 warning: test above used only 78.075559% CPU, result may be flawed!
[ 400KiB] modify 4096 units at a time...              3712 MiB/s
 warning: test above used only 73.922779% CPU, result may be flawed!

[ 400KiB] alternate write & seek one unit...         0.979 MiB/s
 warning: test above used only 70.466597% CPU, result may be flawed!
[ 400KiB] alternate write & seek 1000 units...         869 MiB/s
 warning: test above used only 47.901454% CPU, result may be flawed!
[ 400KiB] alternate read & write one unit...          17.9 MiB/s
 warning: test above used only 53.000036% CPU, result may be flawed!
[ 400KiB] alternate read & write 1000 units...        1356 MiB/s
 warning: test above used only 41.654041% CPU, result may be flawed!

** Text overwrite **

[ 20KiB ] modify one unit at a time...                4.44 MiB/s
 warning: test above used only 52.045793% CPU, result may be flawed!
[ 400KiB] modify 20 units at a time...                55.8 MiB/s
 warning: test above used only 50.834417% CPU, result may be flawed!
[ 400KiB] modify 4096 units at a time...               237 MiB/s
 warning: test above used only 46.861861% CPU, result may be flawed!


-----------

>>> benchmarking stdlib pyio module on python sys.version_info(major=3, minor=12, micro=0, releaselevel='beta', serial=4): module <module '_pyio' from 'C:\\Program Files\\Python312\\Lib\\_pyio.py'> <<<
Preparing files...
Python 3.12.0b4 (tags/v3.12.0b4:97a6a41, Jul 11 2023, 13:49:15) [MSC v.1935 64 bit (AMD64)]
Unicode: PEP 393
Windows-11-10.0.22621-SP0
Binary unit = one byte
Text unit = one character (utf8-decoded)

** Binary input **

[ 400KiB] read one unit at a time...                  3.59 MiB/s
 warning: test above used only 46.206939% CPU, result may be flawed!
[ 400KiB] read 20 units at a time...                  68.7 MiB/s
 warning: test above used only 61.194005% CPU, result may be flawed!
[ 400KiB] read 4096 units at a time...                2765 MiB/s
 warning: test above used only 53.103114% CPU, result may be flawed!

[ 20KiB ] read whole contents at once...              1002 MiB/s
 warning: test above used only 61.446535% CPU, result may be flawed!
[ 400KiB] read whole contents at once...              4978 MiB/s
 warning: test above used only 48.958256% CPU, result may be flawed!
[ 10MiB ] read whole contents at once...              2563 MiB/s
 warning: test above used only 48.907028% CPU, result may be flawed!

[ 400KiB] seek forward one unit at a time...          1.01 MiB/s
 warning: test above used only 49.451786% CPU, result may be flawed!
[ 400KiB] seek forward 1000 units at a time...        1074 MiB/s
 warning: test above used only 48.926162% CPU, result may be flawed!
[ 400KiB] alternate read & seek one unit...          0.507 MiB/s
 warning: test above used only 43.611929% CPU, result may be flawed!
[ 400KiB] alternate read & seek 1000 units...          483 MiB/s
 warning: test above used only 52.073848% CPU, result may be flawed!

** Text input **

[ 400KiB] read one unit at a time...                  2.63 MiB/s
 warning: test above used only 46.939458% CPU, result may be flawed!
[ 400KiB] read 20 units at a time...                  43.9 MiB/s
 warning: test above used only 51.934467% CPU, result may be flawed!
[ 400KiB] read one line at a time...                    63 MiB/s
 warning: test above used only 52.922042% CPU, result may be flawed!
[ 400KiB] read 4096 units at a time...                 342 MiB/s
 warning: test above used only 52.057542% CPU, result may be flawed!

[ 20KiB ] read whole contents at once...               408 MiB/s
 warning: test above used only 59.355037% CPU, result may be flawed!
[ 400KiB] read whole contents at once...               647 MiB/s
 warning: test above used only 51.024238% CPU, result may be flawed!
[ 10MiB ] read whole contents at once...               440 MiB/s
 warning: test above used only 18.471491% CPU, result may be flawed!

[ 400KiB] seek forward one unit at a time...         0.493 MiB/s
 warning: test above used only 14.801335% CPU, result may be flawed!
[ 400KiB] seek forward 1000 units at a time...         551 MiB/s
 warning: test above used only 46.865659% CPU, result may be flawed!

** Binary append **

[ 20KiB ] write one unit at a time...                 2.79 MiB/s
 warning: test above used only 76.796579% CPU, result may be flawed!
[ 400KiB] write 20 units at a time...                   53 MiB/s
 warning: test above used only 61.309889% CPU, result may be flawed!
[ 400KiB] write 4096 units at a time...               4136 MiB/s
 warning: test above used only 66.662375% CPU, result may be flawed!
[ 10MiB ] write 1e6 units at a time...                6474 MiB/s
 warning: test above used only 65.565442% CPU, result may be flawed!

** Text append **

[ 20KiB ] write one unit at a time...                 1.32 MiB/s
 warning: test above used only 71.270317% CPU, result may be flawed!
[ 400KiB] write 20 units at a time...                 16.5 MiB/s
 warning: test above used only 70.301667% CPU, result may be flawed!
[ 400KiB] write 4096 units at a time...                253 MiB/s
 warning: test above used only 68.746711% CPU, result may be flawed!
[ 10MiB ] write 1e6 units at a time...                 218 MiB/s
 warning: test above used only 65.091220% CPU, result may be flawed!

** Binary overwrite **

[ 20KiB ] modify one unit at a time...                2.41 MiB/s
 warning: test above used only 74.597492% CPU, result may be flawed!
[ 400KiB] modify 20 units at a time...                46.7 MiB/s
 warning: test above used only 74.793681% CPU, result may be flawed!
[ 400KiB] modify 4096 units at a time...              2824 MiB/s
 warning: test above used only 63.500789% CPU, result may be flawed!

[ 400KiB] alternate write & seek one unit...         0.654 MiB/s
 warning: test above used only 72.408635% CPU, result may be flawed!
[ 400KiB] alternate write & seek 1000 units...         604 MiB/s
 warning: test above used only 63.503039% CPU, result may be flawed!
[ 400KiB] alternate read & write one unit...         0.336 MiB/s
 warning: test above used only 64.514719% CPU, result may be flawed!
[ 400KiB] alternate read & write 1000 units...         319 MiB/s
 warning: test above used only 56.178209% CPU, result may be flawed!

** Text overwrite **

[ 20KiB ] modify one unit at a time...                1.25 MiB/s
 warning: test above used only 45.507096% CPU, result may be flawed!
[ 400KiB] modify 20 units at a time...                21.1 MiB/s
 warning: test above used only 43.741275% CPU, result may be flawed!
[ 400KiB] modify 4096 units at a time...               231 MiB/s
 warning: test above used only 44.739556% CPU, result may be flawed!


-----------

>>> benchmarking rsfile module <<<
Preparing files...
Python 3.12.0b4 (tags/v3.12.0b4:97a6a41, Jul 11 2023, 13:49:15) [MSC v.1935 64 bit (AMD64)]
Unicode: PEP 393
Windows-11-10.0.22621-SP0
Binary unit = one byte
Text unit = one character (utf8-decoded)

** Binary input **

[ 400KiB] read one unit at a time...                  1.69 MiB/s
 warning: test above used only 46.293826% CPU, result may be flawed!
[ 400KiB] read 20 units at a time...                  32.1 MiB/s
 warning: test above used only 64.221815% CPU, result may be flawed!
[ 400KiB] read 4096 units at a time...                1563 MiB/s
 warning: test above used only 68.720159% CPU, result may be flawed!

[ 20KiB ] read whole contents at once...              1018 MiB/s
 warning: test above used only 60.389378% CPU, result may be flawed!
[ 400KiB] read whole contents at once...              2203 MiB/s
 warning: test above used only 52.068486% CPU, result may be flawed!
[ 10MiB ] read whole contents at once...              1124 MiB/s
 warning: test above used only 64.441574% CPU, result may be flawed!

[ 400KiB] seek forward one unit at a time...          0.45 MiB/s
 warning: test above used only 47.749500% CPU, result may be flawed!
[ 400KiB] seek forward 1000 units at a time...         437 MiB/s
 warning: test above used only 62.463196% CPU, result may be flawed!
[ 400KiB] alternate read & seek one unit...          0.284 MiB/s
 warning: test above used only 61.905037% CPU, result may be flawed!
[ 400KiB] alternate read & seek 1000 units...          276 MiB/s
 warning: test above used only 53.090090% CPU, result may be flawed!

** Text input **

[ 400KiB] read one unit at a time...                  1.39 MiB/s
 warning: test above used only 55.650725% CPU, result may be flawed!
[ 400KiB] read 20 units at a time...                  24.8 MiB/s
 warning: test above used only 60.928206% CPU, result may be flawed!
[ 400KiB] read one line at a time...                  51.5 MiB/s
 warning: test above used only 53.016422% CPU, result may be flawed!
[ 400KiB] read 4096 units at a time...                 321 MiB/s
 warning: test above used only 51.018337% CPU, result may be flawed!

[ 20KiB ] read whole contents at once...               407 MiB/s
 warning: test above used only 56.223450% CPU, result may be flawed!
[ 400KiB] read whole contents at once...               574 MiB/s
 warning: test above used only 55.176963% CPU, result may be flawed!
[ 10MiB ] read whole contents at once...               427 MiB/s
 warning: test above used only 66.810739% CPU, result may be flawed!

[ 400KiB] seek forward one unit at a time...         0.295 MiB/s
 warning: test above used only 51.338271% CPU, result may be flawed!
[ 400KiB] seek forward 1000 units at a time...         291 MiB/s
 warning: test above used only 58.280171% CPU, result may be flawed!

** Binary append **

[ 20KiB ] write one unit at a time...                 1.42 MiB/s
 warning: test above used only 43.492074% CPU, result may be flawed!
[ 400KiB] write 20 units at a time...                 27.2 MiB/s
 warning: test above used only 52.762799% CPU, result may be flawed!
[ 400KiB] write 4096 units at a time...               1335 MiB/s
 warning: test above used only 54.142364% CPU, result may be flawed!
[ 10MiB ] write 1e6 units at a time...                1335 MiB/s
 warning: test above used only 52.965291% CPU, result may be flawed!

** Text append **

[ 20KiB ] write one unit at a time...                0.664 MiB/s
 warning: test above used only 55.177655% CPU, result may be flawed!
[ 400KiB] write 20 units at a time...                 6.29 MiB/s
 warning: test above used only 53.351462% CPU, result may be flawed!
[ 400KiB] write 4096 units at a time...                189 MiB/s
 warning: test above used only 46.800137% CPU, result may be flawed!
[ 10MiB ] write 1e6 units at a time...                 208 MiB/s
 warning: test above used only 42.729265% CPU, result may be flawed!

** Binary overwrite **

[ 20KiB ] modify one unit at a time...                1.34 MiB/s
 warning: test above used only 47.734551% CPU, result may be flawed!
[ 400KiB] modify 20 units at a time...                24.6 MiB/s
 warning: test above used only 51.825452% CPU, result may be flawed!
[ 400KiB] modify 4096 units at a time...              1101 MiB/s
 warning: test above used only 56.232062% CPU, result may be flawed!

[ 400KiB] alternate write & seek one unit...         0.214 MiB/s
 warning: test above used only 66.014191% CPU, result may be flawed!
[ 400KiB] alternate write & seek 1000 units...         192 MiB/s
 warning: test above used only 68.716218% CPU, result may be flawed!
[ 400KiB] alternate read & write one unit...         0.138 MiB/s
 warning: test above used only 53.927057% CPU, result may be flawed!
[ 400KiB] alternate read & write 1000 units...         134 MiB/s
 warning: test above used only 66.510609% CPU, result may be flawed!

** Text overwrite **

[ 20KiB ] modify one unit at a time...               0.686 MiB/s
 warning: test above used only 73.495361% CPU, result may be flawed!
[ 400KiB] modify 20 units at a time...                12.2 MiB/s
 warning: test above used only 56.933845% CPU, result may be flawed!
[ 400KiB] modify 4096 units at a time...               201 MiB/s
 warning: test above used only 46.833626% CPU, result may be flawed!

"""