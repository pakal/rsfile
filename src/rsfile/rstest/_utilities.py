# -*- coding: utf-8 -*-


import sys, unittest


def launch_rsfile_tests_on_backends(test_main):
    backends = []

    if sys.platform == "win32":
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
    try:
        # in python3, test.test_support contains almost nothing, stuffs have moved to test.support...
        from test.test_support import run_unittest
    except ImportError:
        import test
        from test import support as test_support

        sys.modules["test.test_support"] = test_support
        test.test_support = test_support

        try:
            from test.support import run_unittest  # Python 3.11+ removed this utilituy
        except ImportError:

            # RESTORE DELETED UTILITIES #

            # By default, don't filter tests
            _test_matchers = ()
            _test_patterns = ()

            def match_test(test):
                # Function used by support.run_unittest() and regrtest --list-cases
                result = False
                for matcher, result in reversed(_test_matchers):
                    if matcher(test.id()):
                        return result
                return not result

            def _filter_suite(suite, pred):
                """Recursively filter test cases in a suite based on a predicate."""
                newtests = []
                for test in suite._tests:
                    if isinstance(test, unittest.TestSuite):
                        _filter_suite(test, pred)
                        newtests.append(test)
                    else:
                        if pred(test):
                            newtests.append(test)
                suite._tests = newtests

            def run_unittest(*classes):
                """Run tests from unittest.TestCase-derived classes."""
                valid_types = (unittest.TestSuite, unittest.TestCase)
                loader = unittest.TestLoader()
                suite = unittest.TestSuite()
                for cls in classes:
                    if isinstance(cls, str):
                        if cls in sys.modules:
                            suite.addTest(loader.loadTestsFromModule(sys.modules[cls]))
                        else:
                            raise ValueError("str arguments must be keys in sys.modules")
                    elif isinstance(cls, valid_types):
                        suite.addTest(cls)
                    else:
                        suite.addTest(loader.loadTestsFromTestCase(cls))
                _filter_suite(suite, match_test)
                from test.libregrtest.single import _run_suite
                return _run_suite(suite)

            test_support.run_unittest = run_unittest
