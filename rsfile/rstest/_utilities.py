# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

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

    '''
    import functools, contextlib

    if not hasattr(test_support, "gc_collect"):
        # new in py2.7 ...
        def gc_collect():
            import gc
            gc.collect()
        test_support.gc_collect = gc_collect
    
    if not hasattr(test_support, "py3k_bytes"):
        def py3k_bytes(b):
            try:
                # memoryview?
                return b.tobytes()
            except AttributeError:
                try:
                    # iterable of ints?
                    return b"".join(chr(x) for x in b)
                except TypeError:
                    return bytes(b)    
        test_support.py3k_bytes = py3k_bytes
    

    if not hasattr(unittest, "skip"):
        def skip(*args):
            def decorator(*args):
                return lambda *args, **kwargs: None
            return decorator
        unittest.skip = skip

    if not hasattr(unittest, "skipUnless"):
        def skipUnless(*args):
            def decorator(*args):
                return lambda *args, **kwargs: None
            return decorator
        unittest.skipUnless = skipUnless

    if not hasattr(TestCase, "assertIsNone"):
        def assertIsNone(self, obj, msg=None):
            """Same as self.assertTrue(obj is None), with a nicer default message."""
            if obj is not None:
                standardMsg = '%s is not None' % (repr(obj),)
                self.fail(standardMsg)
        TestCase.assertIsNone = assertIsNone


    from unittest import TestCase
    if not hasattr(TestCase, "assertIsInstance"):
        
        def assertIsInstance(self, obj, cls, msg=None):
            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (repr(obj), cls)
                self.fail(standardMsg)
        TestCase.assertIsInstance = assertIsInstance
        
        def assertNotIsInstance(self, obj, cls, msg=None):
            if isinstance(obj, cls):
                standardMsg = '%s is an instance of %r' % (repr(obj), cls)
                self.fail(standardMsg)
        TestCase.assertNotIsInstance = assertNotIsInstance

        def assertIs(self, expr1, expr2, msg=None):
            """Just like self.assertTrue(a is b), but with a nicer default message."""
            if expr1 is not expr2:
                standardMsg = '%s is not %s' % (repr(expr1),
                                                 repr(expr2))
                self.fail(standardMsg)
        TestCase.assertIs = assertIs
        '''
