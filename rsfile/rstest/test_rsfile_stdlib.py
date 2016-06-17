#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import rsfile.rsfile_definitions as defs

from rsfile.rstest import _utilities
_utilities.patch_test_supports()

from rsfile.rstest import _worker_process

import sys
import os
import unittest
from pprint import pprint

import array
import tempfile
import time
import itertools
import threading
import random
import multiprocessing, subprocess
from datetime import datetime, timedelta

import rsfile
import io, _io, _pyio


# IMPORTANT - we monkey-patch the original io modules !!!
rsfile.monkey_patch_io_module(_io)  # C-backed version
rsfile.monkey_patch_io_module(io)  # python interface to C-backed version
rsfile.monkey_patch_io_module(_pyio)  # (almost) pure python version
rsfile.monkey_patch_open_builtin()


from test import test_support  # NOW ONLY we can import it



def test_original_io():
    """
    Beware, We patch stdlib tests to remove C extension tests, or other tests that can't apply to our python implementation.

    Original cmd : " python -m test.regrtest -uall -v test_fileio test_file test_io test_bufio test_memoryio test_largefile "
    """

    import _io

    from test import test_io, test_memoryio, test_file, test_bufio, test_fileio, test_largefile  # python stdlib test suite must be installed for current python interpreter

    class dummyklass(unittest.TestCase):
        pass
    def dummyfunc(*args, **kwargs):
        print("<DUMMY>", end='')

    def clean_unlink(filename):
        try:
            newname = filename + ".tmp" + str(int(time.time()))
            os.rename(filename, newname) # to deal with stale windows files due to SHARE_DELETE flag!
            os.remove(newname) # on windows, file only removed when last handle is closed !
        except:
            pass
    test_support.unlink = clean_unlink

    # Obsolete
    #test_support.use_resources = ["largefile"]# -> uncomment this to try 2Gb file operations (long on win32) !

    """ OLDIE
    if not hasattr(unittest.TestCase, "skipTest"):
        # we can't just deactivate C tests, considered the way it's implemented...
        test_largefile.LargeFileTest.test_seekable = dummyfunc
    #test_largefile.test_main() # beware !
    """

    # Skip C-specific tests, which are anyway often skipped for "_pyio" itself
    test_io.CBufferedRandomTest = dummyklass
    test_io.CBufferedReaderTest = dummyklass
    test_io.CBufferedWriterTest = dummyklass
    test_io.CBufferedRWPairTest = dummyklass
    test_io.CIncrementalNewlineDecoderTest = dummyklass
    test_io.CTextIOWrapperTest = dummyklass
    test_io.CMiscIOTest = dummyklass
    test_io.CIOTest = dummyklass

    test_io.IOTest.test_garbage_collection = dummyfunc # cyclic GC can't work with python classes having __del__() method
    test_io.PyIOTest.test_garbage_collection = dummyfunc # idem

    test_io.PyIOTest.test_large_file_ops = dummyfunc  # we just skip because HEAVY AND LONG

    test_io.TextIOWrapperTest.test_repr = dummyfunc  # repr() of streams changes of course


    # TESTCASES TO FIX !!!!!!!!!!!  #
    ####test_io.PyIOTest.test_invalid_newline = dummyfunc  # FIXME

    """ OLDIE
    #test_io.PyBufferedReaderTest.test_uninitialized = dummyfunc  #FIXME
    test_io.PyBufferedWriterTest.test_uninitialized = dummyfunc  #FIXME
    test_io.BufferedRWPairTest.test_uninitialized = dummyfunc  #FIXME
    test_io.PyBufferedRandomTest.test_uninitialized = dummyfunc  #FIXME
    test_io.PyTextIOWrapperTest.test_uninitialized = dummyfunc  #FIXME
    """

    """ OLD

    test_io.PyIOTest.test_garbage_collection = dummyfunc # test_support.skip() unexisting
    test_io.PyIOTest.test_flush_error_on_close = dummyfunc  #FIXME flush on close on rsfile !!

    test_io.PyBufferedWriterTest.test_max_buffer_size_deprecation = dummyfunc  # sometimes lacking check_warnings() implementation
    test_io.PyBufferedRWPairTest.test_max_buffer_size_deprecation = dummyfunc
    test_io.PyBufferedRWPairTest.test_constructor_max_buffer_size_deprecation = dummyfunc
    test_io.PyBufferedRandomTest.test_max_buffer_size_deprecation = dummyfunc

    test_io.BufferedRWPairTest.UnsupportedOperation = rsfile.io_module.UnsupportedOperation
    if not hasattr(unittest.TestCase, "skipTest"):
        test_io.IOTest.test_unbounded_file = dummyfunc

    """

    # like in _pyio, in rsfile, we do not detect reentrant access, nor raise RuntimeError to avoid deadlocks
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
    test_fileio.AutoFileTests.testMethods = dummyfunc # messy C functions signatures...
    test_fileio.AutoFileTests.testErrors = dummyfunc # incoherent errors returned on bad fd, between C and Py implementations...
    test_fileio.OtherFileTests.testInvalidFd = dummyfunc  # different exception types...
    test_fileio.AutoFileTests.testBlksize = dummyfunc  # rsfile doesn't use raw._blksize optimizations for now

    test_fileio.AutoFileTests.testRepr = dummyfunc  # repr() of streams changes of course
    test_fileio.AutoFileTests.testReprNoCloseFD = dummyfunc  # repr() of streams changes of course

    """ OLD
    test_fileio.OtherFileTests.testWarnings = dummyfunc


    """

    # bugfix of testErrnoOnClosedWrite() test in python2.7
    deco = test_fileio.AutoFileTests.__dict__["ClosedFDRaises"] # decorator must not become unbound method !
    @deco
    def bugfixed(self, f):
        f.write(b'a') # in py27 trunk "binary" was lacking...
    test_fileio.AutoFileTests.testErrnoOnClosedWrite = bugfixed


    # Skip C-oriented tests
    test_memoryio.CStringIOPickleTest = dummyklass
    test_memoryio.CBytesIOTest = dummyklass
    test_memoryio.CStringIOTest = dummyklass


    # Skip C-oriented tests
    test_file.CAutoFileTests = dummyklass


    ## Custom launching iof single test ##
    #mytest = test_io.PyIOTest('test_invalid_newline')
    #res = mytest.run()
    #print(res)


    all_test_suites = []

    test_modules = [test_io, test_file, test_fileio, test_bufio, test_memoryio]

    if False:
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


if __name__ == '__main__':
    test_main()
