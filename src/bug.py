#-*- coding: utf-8 -*-

'''
Created on 11 févr. 2010

@author: Admin
'''
import sys, os, subprocess


child = subprocess.Popen(("python", r"C:\Documents and Settings\Admin\Bureau\RockSolidTools\rstest\_inheritance_tester.py")+
                         ('True', 'True', 'True', '-', '3660'), 
                         executable=r"C:\Python26\python.exe",
                         shell=False, close_fds=False)



"""

COMMAND LINE :  python "C:\Documents and Settings\Admin\Bureau\RockSolidTools\rstest\_inheritance_tester.py" True True True - 3660
executing  C:\Python26\python.exe with args:  python "C:\Documents and Settings\Admin\Bureau\RockSolidTools\rstest\_inheritance_tester.py" True True True - 3660


COMMAND LINE :  python "C:\Documents and Settings\Admin\Bureau\RockSolidTools\rstest\_inheritance_tester.py" True True True - 3660
executing  C:\Python26\python.exe with args:  python "C:\Documents and Settings\Admin\Bureau\RockSolidTools\rstest\_inheritance_tester.py" True True True - 3660
python: can't open file 'C:\Documents': [Errno 2] No such file or directory

"""