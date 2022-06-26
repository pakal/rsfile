# -*- coding: utf-8 -*-
"""
Launch coverage.py on all test suites, aggregate data and generate HTML report.
"""

import sys, os
import glob
import subprocess

import coverage  # "coverage" python package must be installed

python_exe = sys.executable
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

custom_env = os.environ.copy()
custom_env["PYTHONPATH"] = str(ROOT_DIR)

subprocess.check_call("%s -m coverage erase" % python_exe, shell=True, cwd=ROOT_DIR, env=custom_env)


for test_file in glob.glob("rsfile/rstest/test_*.py"):
    subprocess.check_call("%s -m coverage run -a %s" % (python_exe, test_file), shell=True, cwd=ROOT_DIR, env=custom_env)
    
subprocess.check_call("%s -m coverage html -d htmlcov" % python_exe, shell=True, cwd=ROOT_DIR, env=custom_env)

print(">> Coverage report is available in 'htmlcov' folder <<")
