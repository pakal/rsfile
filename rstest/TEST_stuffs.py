

from __future__ import print_function
from __future__ import unicode_literals

def myfunc(**kwargs):
    print("##", kwargs)
    
myfunc(**{"mode": "w"})