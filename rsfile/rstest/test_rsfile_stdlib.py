# -*- coding: utf-8 -*-

from rsfile.rstest import _utilities

_utilities.patch_test_supports()

import sys
import os
import unittest

import time

import rsfile
import io, _io, _pyio

# IMPORTANT - we monkey-patch the original io modules !!!
rsfile.monkey_patch_io_module(_io)  # C-backed version
rsfile.monkey_patch_io_module(io)  # python interface to C-backed version
rsfile.monkey_patch_io_module(_pyio)  # (almost) pure python version
rsfile.monkey_patch_open_builtin()

from test import test_support  # NOW ONLY we can import it


ENABLE_LARGE_FILE_TESTS = False


def test_original_io():
    """
    Beware, We patch stdlib tests to remove C extension tests, or other tests that can't apply to our python
    implementation.

    Original cmd : " python -m test.regrtest -uall -v test_fileio test_file test_io test_bufio test_memoryio
    test_largefile "
    """

    from test import (
        test_io,
        test_memoryio,
        test_file,
        test_bufio,
        test_fileio,
        test_largefile,
    )  # python stdlib test suite must be installed for current python interpreter

    class dummyklass(unittest.TestCase):
        pass

    def dummyfunc(*args, **kwargs):
        print("<DUMMY>", end="")

    # we patch to deal with stale windows files in spite of SHARE_DELETE flag
    # (files only removed when last handle is closed)
    def clean_unlink(filename):
        try:
            newname = filename + ".tmp" + str(int(time.time()))
            os.rename(filename, newname)
            os.remove(newname)
        except:
            pass

    test_support.unlink = clean_unlink

    # Skip C-specific tests, which are anyway often skipped for "_pyio" itself
    test_io.CBufferedRandomTest = dummyklass
    test_io.CBufferedReaderTest = dummyklass
    test_io.CBufferedWriterTest = dummyklass
    test_io.CBufferedRWPairTest = dummyklass
    test_io.CIncrementalNewlineDecoderTest = dummyklass
    test_io.CTextIOWrapperTest = dummyklass
    test_io.CMiscIOTest = dummyklass
    test_io.CIOTest = dummyklass

    if sys.version_info < (3, 6):
        test_io.CommonBufferedTests.test_override_destructor = dummyfunc  # different flushing

    if hasattr(test_io, "MockUnseekableIO"):
        # missing in python<=3.5
        def truncate_blocker(self, *args):
            raise self.UnsupportedOperation("not seekable")

        test_io.MockUnseekableIO.truncate = truncate_blocker

    if sys.version_info < (3,):
        test_io.MiscIOTest.test_io_after_close = dummyfunc  # confusion ValueError/IOError on closed files

    test_io.IOTest.test_garbage_collection = dummyfunc  # cyclic GC can't work with python classes having __del__()
    # method
    test_io.PyIOTest.test_garbage_collection = dummyfunc  # idem
    test_io.PyIOTest.test_large_file_ops = dummyfunc  # we just skip because HEAVY AND LONG
    test_io.TextIOWrapperTest.test_repr = dummyfunc  # repr() of streams changes of course

    # Skip tests dealing with details of C implementation
    test_io.TestIOCTypes.test_immutable_types = dummyfunc
    test_io.TestIOCTypes.test_class_hierarchy = dummyfunc

    # like in _pyio implementation, in rsfile, we do not detect reentrant access, nor raise RuntimeError to avoid
    # deadlocks
    test_io.PySignalsTest.test_reentrant_write_buffered = dummyfunc
    test_io.PySignalsTest.test_reentrant_write_text = dummyfunc
    test_io.CSignalsTest.test_reentrant_write_buffered = dummyfunc
    test_io.CSignalsTest.test_reentrant_write_text = dummyfunc

    # we have no resource warnings and such in rsfile ATM
    test_io.PyMiscIOTest.test_warn_on_dealloc = dummyfunc
    test_io.PyMiscIOTest.test_warn_on_dealloc_fd = dummyfunc
    test_io.PyMiscIOTest.test_attributes = dummyfunc
    test_io.PyIOTest.test_destructor = dummyfunc

    # very corner case with subprocesses, doesn't apply monkey-patching properly
    test_io.PyTextIOWrapperTest.test_create_at_shutdown_with_encoding = dummyfunc
    test_io.PyTextIOWrapperTest.test_create_at_shutdown_without_encoding = dummyfunc

    # WIP buggy case dues to broken stdlib tests and _pyio (see https://bugs.python.org/issue23796)
    test_io.PyBufferedReaderTest.test_read_on_closed = dummyfunc
    test_io.PyBufferedRandomTest.test_read_on_closed = dummyfunc

    test_fileio._FileIO = rsfile.io_module.FileIO
    test_fileio.AutoFileTests.testMethods = dummyfunc  # messy C functions signatures...
    test_fileio.AutoFileTests.testErrors = dummyfunc  # incoherent errors returned on bad fd, between C and Py
    # implementations...
    test_fileio.OtherFileTests.testInvalidFd = dummyfunc  # different exception types...
    test_fileio.AutoFileTests.testBlksize = dummyfunc  # rsfile doesn't use raw._blksize optimizations for now

    test_fileio.AutoFileTests.testRepr = dummyfunc  # repr() of streams changes of course
    test_fileio.AutoFileTests.testReprNoCloseFD = dummyfunc  # repr() of streams changes of course

    # bugfix of testErrnoOnClosedWrite() test in python2.7
    deco = test_fileio.AutoFileTests.__dict__["ClosedFDRaises"]  # decorator must not become unbound method !

    @deco
    def bugfixed(self, f):
        f.write(b"a")  # in py27 trunk, "binary" modifier was lacking...

    test_fileio.AutoFileTests.testErrnoOnClosedWrite = bugfixed

    # Skip C-oriented tests
    test_memoryio.CStringIOPickleTest = dummyklass
    test_memoryio.CBytesIOTest = dummyklass
    test_memoryio.CStringIOTest = dummyklass

    # Skip C-oriented tests
    test_file.CAutoFileTests = dummyklass

    ## Use this to launch a single test ##
    '''
    from unittest import TextTestResult
	from unittest.runner import _WritelnDecorator
	from rsfile import rsopen
    mytest = test_io.PyMiscIOTest('test_nonblock_pipe_write_smallbuf')
    mytest.open = rsopen
    mytest.BlockingIOError = BlockingIOError
    res = mytest.run(result=TextTestResult(_WritelnDecorator(sys.stdout), "", 1))
    print(res)
    res.printErrors()
    return
    '''

    all_test_suites = []

    test_modules = [test_io, test_file, test_fileio, test_bufio, test_memoryio]

    if ENABLE_LARGE_FILE_TESTS:
        # BEWARE - heavy test, activate it it wisely
        test_modules.insert(0, test_largefile)

    for stdlib_test_module in test_modules:

        if hasattr(stdlib_test_module, "test_main"):
            stdlib_test_module.test_main()  # OLD STYLE
        else:
            # NOTE: this calls stdlib_test_module.load_tests() if present
            new_tests = unittest.defaultTestLoader.loadTestsFromModule(stdlib_test_module)
            all_test_suites.extend(new_tests)

    if all_test_suites:
        test_support.run_unittest(*all_test_suites)


def test_main():
    def _launch_test_on_single_backend():
        test_original_io()

    backends = _utilities.launch_rsfile_tests_on_backends(_launch_test_on_single_backend)
    print("** RSFILE_STDLIB Test Suite has been run on backends %s **\n" % backends)


if __name__ == "__main__":
    test_main()
