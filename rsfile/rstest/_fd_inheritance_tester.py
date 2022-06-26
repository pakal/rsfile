# -*- coding: utf-8 -*-
# CHILD SCRIPT FOR TESTS


import sys

# print "we enter function with path : ", sys.path, " | ", sys.executable
from rsfile.rstest import _worker_process

(read, write, append, fileno, handle) = sys.argv[1:]

_worker_process.fd_inheritance_tester(
    read == "True",
    write == "True",
    append == "True",
    int(fileno) if fileno != "-" else None,
    int(handle) if handle != "-" else None,
)

sys.exit(0)
