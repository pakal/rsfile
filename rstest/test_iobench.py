
#import pyximport; pyximport.install()
#import Cython
#import rsfile.rsfile_registries


import sys, io, rsfile
from rstest import iobench

"""
print ">>> benchmarking stdlib io modules of %s, module %r <<<" % (sys.version_info, io)

iobench.open = io.open
iobench.text_open = io.open

iobench.prepare_files()
iobench.run_all_tests("rwtb")
"""

print "\n"
print ">>> benchmarking rsfile module <<<"



iobench.open = rsfile.rsopen
iobench.text_open = rsfile.rsopen

iobench.prepare_files()
iobench.run_all_tests("rwtb")




"""
>>> benchmarking stdlib io modules of 2.6.4 (r264:75708, Oct 26 2009, 08:23:19) [MSC v.1500 32 bit (Intel)], module <module 'io' from 'C:\Python26\lib\io.py'> <<<
Preparing files...
Binary unit = one byte
Text unit = one character (utf8-decoded)

** Binary input **

[ 400KB ] read one unit at a time...                  0.219 MB/s
[ 400KB ] read 20 units at a time...                   3.57 MB/s
   warning: test above used only 84% CPU, result may be flawed!
[ 400KB ] read 4096 units at a time...                  160 MB/s
   warning: test above used only 78% CPU, result may be flawed!

[  20KB ] read whole contents at once...                251 MB/s
   warning: test above used only 86% CPU, result may be flawed!
[ 400KB ] read whole contents at once...                124 MB/s
   warning: test above used only 88% CPU, result may be flawed!
[  10MB ] read whole contents at once...              0.416 MB/s
   warning: test above used only 83% CPU, result may be flawed!

[ 400KB ] seek forward one unit at a time...          0.204 MB/s
[ 400KB ] seek forward 1000 units at a time...          191 MB/s
[ 400KB ] alternate read & seek one unit...          0.0507 MB/s
   warning: test above used only 88% CPU, result may be flawed!
[ 400KB ] alternate read & seek 1000 units...          51.5 MB/s

** Text input **

[ 400KB ] read one unit at a time...                  0.281 MB/s
   warning: test above used only 89% CPU, result may be flawed!
[ 400KB ] read 20 units at a time...                   1.91 MB/s
   warning: test above used only 78% CPU, result may be flawed!
[ 400KB ] read one line at a time...                   1.98 MB/s
[ 400KB ] read 4096 units at a time...                 3.39 MB/s

[  20KB ] read whole contents at once...               25.9 MB/s
[ 400KB ] read whole contents at once...               23.7 MB/s
   warning: test above used only 73% CPU, result may be flawed!
[  10MB ] read whole contents at once...              0.487 MB/s

[ 400KB ] seek forward one unit at a time...         0.0632 MB/s
[ 400KB ] seek forward 1000 units at a time...         62.9 MB/s

** Binary append **

[  20KB ] write one unit at a time...                 0.167 MB/s
[ 400KB ] write 20 units at a time...                  3.19 MB/s
[ 400KB ] write 4096 units at a time...                 254 MB/s
[  10MB ] write 1e6 units at a time...                  163 MB/s

** Text append **

[  20KB ] write one unit at a time...                 0.075 MB/s
[ 400KB ] write 20 units at a time...                 0.963 MB/s
[ 400KB ] write 4096 units at a time...                15.2 MB/s
[  10MB ] write 1e6 units at a time...                 15.1 MB/s

** Binary overwrite **

[  20KB ] modify one unit at a time...                0.115 MB/s
[ 400KB ] modify 20 units at a time...                 2.03 MB/s
[ 400KB ] modify 4096 units at a time...                142 MB/s

[ 400KB ] alternate write & seek one unit...         0.0574 MB/s
[ 400KB ] alternate write & seek 1000 units...         54.6 MB/s
[ 400KB ] alternate read & write one unit...          0.025 MB/s
[ 400KB ] alternate read & write 1000 units...         25.2 MB/s

** Text overwrite **

[  20KB ] modify one unit at a time...               0.0617 MB/s
[ 400KB ] modify 20 units at a time...                0.848 MB/s
[ 400KB ] modify 4096 units at a time...               13.4 MB/s



>>> benchmarking rsfile module <<<
Preparing files...
Binary unit = one byte
Text unit = one character (utf8-decoded)

** Binary input **

[ 400KB ] read one unit at a time...                 0.0568 MB/s
[ 400KB ] read 20 units at a time...                    1.2 MB/s
[ 400KB ] read 4096 units at a time...                 82.4 MB/s

[  20KB ] read whole contents at once...               41.6 MB/s
[ 400KB ] read whole contents at once...               51.5 MB/s
[  10MB ] read whole contents at once...               23.9 MB/s

[ 400KB ] seek forward one unit at a time...         0.0415 MB/s
[ 400KB ] seek forward 1000 units at a time...         41.1 MB/s
[ 400KB ] alternate read & seek one unit...         0.00823 MB/s
[ 400KB ] alternate read & seek 1000 units...            10 MB/s

** Text input **

[ 400KB ] read one unit at a time...                 0.0628 MB/s
[ 400KB ] read 20 units at a time...                  0.907 MB/s
[ 400KB ] read one line at a time...                   1.96 MB/s
[ 400KB ] read 4096 units at a time...                 2.72 MB/s
   warning: test above used only 76% CPU, result may be flawed!

[  20KB ] read whole contents at once...               13.9 MB/s
   warning: test above used only 82% CPU, result may be flawed!
[ 400KB ] read whole contents at once...               16.1 MB/s
[  10MB ] read whole contents at once...               14.3 MB/s

[ 400KB ] seek forward one unit at a time...         0.0242 MB/s
[ 400KB ] seek forward 1000 units at a time...         24.2 MB/s

** Binary append **

[  20KB ] write one unit at a time...                0.0497 MB/s
[ 400KB ] write 20 units at a time...                 0.442 MB/s
   warning: test above used only 41% CPU, result may be flawed!
[ 400KB ] write 4096 units at a time...                39.3 MB/s
   warning: test above used only 55% CPU, result may be flawed!
[  10MB ] write 1e6 units at a time...                 91.9 MB/s
   warning: test above used only 82% CPU, result may be flawed!

** Text append **

[  20KB ] write one unit at a time...                0.0128 MB/s
   warning: test above used only 38% CPU, result may be flawed!
[ 400KB ] write 20 units at a time...                 0.204 MB/s
   warning: test above used only 34% CPU, result may be flawed!
[ 400KB ] write 4096 units at a time...                9.62 MB/s
   warning: test above used only 74% CPU, result may be flawed!
[  10MB ] write 1e6 units at a time...                   14 MB/s

** Binary overwrite **

[  20KB ] modify one unit at a time...               0.0164 MB/s
   warning: test above used only 39% CPU, result may be flawed!
[ 400KB ] modify 20 units at a time...                0.247 MB/s
   warning: test above used only 32% CPU, result may be flawed!
[ 400KB ] modify 4096 units at a time...               21.3 MB/s
   warning: test above used only 32% CPU, result may be flawed!

[ 400KB ] alternate write & seek one unit...         0.0135 MB/s
   warning: test above used only 60% CPU, result may be flawed!
[ 400KB ] alternate write & seek 1000 units...         19.1 MB/s
[ 400KB ] alternate read & write one unit...        0.00688 MB/s
[ 400KB ] alternate read & write 1000 units...         7.11 MB/s
   warning: test above used only 83% CPU, result may be flawed!

** Text overwrite **

[  20KB ] modify one unit at a time...               0.0246 MB/s
   warning: test above used only 81% CPU, result may be flawed!
[ 400KB ] modify 20 units at a time...                0.446 MB/s
   warning: test above used only 81% CPU, result may be flawed!
[ 400KB ] modify 4096 units at a time...               11.9 MB/s
"""