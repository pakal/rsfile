
import sys, os
#print "we enter function with path : ", sys.path, " | ", sys.executable
import time, random, string
from rstest import _workerProcess


(read, write, append, fileno, handle) = sys.argv[1:]

_workerProcess.inheritance_tester(read=="True", write=="True", append=="True", 
                                 int(fileno) if fileno!="-" else None, 
                                 int(handle) if handle!="-" else None)

sys.exit(0)
