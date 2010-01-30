# -*- coding: utf-8 -*-

import os

path = os.path.join(os.path.dirname(__file__), "__inheritance_tester.py")
args = (path,)
print "--->", path, "-", args
retcode = os.spawnvp(os.P_WAIT, "path", "__inheritance_tester.py", ())
print "=>", retcode