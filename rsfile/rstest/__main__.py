# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

# BROKEN ATM - pbs with multiple monkeypatching

from rsfile.rstest.test_rsfile_streams import test_main as streams_test_main
from rsfile.rstest.test_rsfile_locking import test_main as locking_test_main

if __name__ == '__main__':
    # these tests will all stop as soon as one of their suites fails
    locking_test_main()
    streams_test_main()
