# -*- coding: utf-8 -*-


import os, sys
import subprocess


def launch_rsfile_tests_on_backends(test_main):
    backends = []

    if sys.platform == 'win32':
        import rsfile.rsfileio_windows as rsfileio_win32

        try:
            import rsfile.rsbackend.windows_pywin32
        except ImportError:
            pass
        else:
            print("<Launching test on pywin32 extensions backend !>\n")
            assert rsfileio_win32.win32
            rsfileio_win32.win32 = rsfile.rsbackend.windows_pywin32
            test_main()
            backends.append("pywin32_extensions")

        try:
            import rsfile.rsbackend.windows_ctypes
        except ImportError:
            pass
        else:
            print("<Launching test on win32 ctypes backend !>\n")
            assert rsfileio_win32.win32
            rsfileio_win32.win32 = rsfile.rsbackend.windows_ctypes
            test_main()
            backends.append("pywin32_ctypes")

    else:
        print("<Launching test on UNIX backend !>\n")
        test_main()  # only one backend in unix at the moment
        backends.append("unix")

    return backends


def patch_test_supports():
    import unittest
    from unittest import TestCase

    try:
        # in python3, test.test_support contains almost nothing, stuffs have moved to test.support...
        from test.test_support import run_unittest
    except ImportError:
        import test
        from test import support as test_support
        sys.modules["test.test_support"] = test_support
        test.test_support = test_support
