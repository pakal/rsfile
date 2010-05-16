



import os, sys
import subprocess




def launch_rsfile_tests_on_backends(test_main):
    backends = []
    
    if sys.platform == 'win32':
        import rsfile.rsfileio_win32 as rsfileio_win32
               
        try:
            import rsbackends.pywin32_extensions as win32
        except ImportError:
            pass
        else:
            rsfileio_win32.win3 = win32
            test_main()
            backends.append("pywin32_extensions")

        
        try:
            import rsbackends.pywin32_ctypes as win32
        except ImportError:
            pass
        else:
            rsfileio_win32.win3 = win32
            test_main()
            backends.append("pywin32_ctypes")

    else:
        test_main() # only one backend in unix at the moment
        backends.append("unix")
    
    
    return backends




def patch_test_supports():
    
    import unittest
    from test import test_support
    import functools, contextlib
        
    if not hasattr(test_support, "gc_collect"):
        # new in py2.7 ...
        def gc_collect():
            import gc
            gc.collect()
            gc.collect()
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


    try:
        import test.script_helper
    except ImportError:
        import rstest.stdlib.script_helper as script_helper
        sys.modules["test.script_helper"] = script_helper


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

  