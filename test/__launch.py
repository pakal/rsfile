

import os
args = ()
path = os.path.join(os.path.dirname(__file__), "inheritance_tester.py")
print path
retcode = os.spawnv(os.P_WAIT, path, args)
print retcode
