#!/usr/local/bin/python

print "we enter function"

import sys, os, time, random, string
import _workerProcess


(read, write, append, fileno, handle) = sys.argv[1:]

_workerProcess.inheritance_tester(read=="True", write=="True", append=="True", 
                                 int(fileno) if fileno!="-" else None, 
                                 int(handle) if handle!="-" else None)

sys.exit(0)
