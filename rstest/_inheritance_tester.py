# SCRIPT

import sys, os
#print "we enter function with path : ", sys.path, " | ", sys.executable
import time, random, string
from rstest import _worker_process


(read, write, append, fileno, handle) = sys.argv[1:]

_worker_process.inheritance_tester(read == "True", write == "True", append == "True",
                                 int(fileno) if fileno != "-" else None,
                                 int(handle) if handle != "-" else None)

sys.exit(0)
