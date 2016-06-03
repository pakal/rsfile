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

import tempfile
import time
import itertools
import threading
import random
import multiprocessing, subprocess


import rsfile

TESTFN = "@TESTING" # we used our own one, since the test_support version is broken

import io, _io, _pyio

"""
Binary buffered objects (instances of BufferedReader, BufferedWriter, BufferedRandom and BufferedRWPair) are not reentrant. While reentrant calls will not happen in normal situations, they can arise from doing I/O in a signal handler. If a thread tries to re-enter a buffered object which it is already accessing, a RuntimeError is raised. Note this doesn’t prohibit a different thread from entering the buffered object.
"""
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

    from test import test_io, test_memoryio, test_file, test_bufio, test_fileio, test_largefile
    from test.test_largefile import LargeFileTest # TODO REVIVE THIS ?? it excludes py26

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

    # Warning - HEAVY
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

    test_fileio._FileIO = rsfile.io_module.FileIO
    test_fileio.AutoFileTests.testMethods = dummyfunc # messy C functions signatures...
    test_fileio.AutoFileTests.testErrors = dummyfunc # incoherent errors returned on bad fd, between C and Py implementations...
    test_fileio.OtherFileTests.testInvalidFd = dummyfunc  # different exception types...

    test_fileio.AutoFileTests.testRepr = dummyfunc  # repr() of streams changes of course

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

    for stdlib_test_module in (test_io, test_file, test_fileio, test_bufio, test_memoryio):

        if hasattr(stdlib_test_module, "test_main"):
            stdlib_test_module.test_main()  # OLD STYLE
        else:
            # NOTE: this calls stdlib_test_module.load_tests() if present
            new_tests = unittest.defaultTestLoader.loadTestsFromModule(stdlib_test_module)
            all_test_suites.extend(new_tests)

    if all_test_suites:
        test_support.run_unittest(*all_test_suites)







def _cleanup():
    if os.path.exists(TESTFN):
        os.chmod(TESTFN, 0o777)
        os.remove(TESTFN)
    if os.path.exists(TESTFN + ".temp"):
        os.chmod(TESTFN + ".temp", 0o777)
        os.remove(TESTFN + ".temp")



class TestRawFileViaWrapper(unittest.TestCase):

    def setUp(self):
        _cleanup()


    def tearDown(self):
        _cleanup()



    def ___testInvalidFd(self): # Pakal todo - put it back when msvcrt fixed in py trunk !
        self.assertRaises(ValueError, io.open, -10, 'wb', buffering=0,)
        bad_fd = test_support.make_bad_fd()
        self.assertRaises(IOError, io.open, bad_fd, 'wb', buffering=0)


    def test_garbage_collection(self):
        # FileIO objects are collected, and collecting them flushes
        # all data to disk.

        # WARNING - cyclic garbage collection can't work with python objects having a __del__ method !

        import weakref

        f = io.open(TESTFN, 'wb', buffering=0)
        f.write(b"abcxxx")

        wr = weakref.ref(f)
        del f

        test_support.gc_collect()

        #print (gc.garbage) - in case of trouble

        self.assertTrue(wr() is None, wr)
        with io.open(TESTFN, "rb") as f:
            self.assertEqual(f.read(), b"abcxxx")



    def testProperties(self):
        with io.open(TESTFN, 'wb', buffering=0) as f:

            self.assertEqual(f.writable(), True)
            self.assertEqual(f.seekable(), True)
            self.assertEqual(f.readable(), False)

            self.assertEqual(f.name, TESTFN)
            self.assertEqual(f.origin, "path")
            self.assertEqual(f.mode, 'wb')

            #self.assertEqual(f._zerofill, True)
            self.assertEqual(f._append, False)

            self.assertRaises(IOError, f.read, 10)
            self.assertRaises(IOError, f.readinto, sys.stdout)

        #TODO - complete this !!!!!!!!!!!!!!!


    def testDirectoryOpening(self):

        DIRNAME = "DUMMYDIR"
        try:
            os.rmdir(DIRNAME)
        except EnvironmentError:
            pass # not existing surely...

        os.mkdir(DIRNAME)

        # we must NOT be able to open directories via rsfile !
        self.assertRaises(IOError, io.open, DIRNAME, 'rb', buffering=0)
        self.assertRaises(IOError, io.open, DIRNAME, 'wb', buffering=0)

        os.rmdir(DIRNAME)


    def testSizeAndPos(self):
        with io.open(TESTFN, 'wb', buffering=0) as f:
            nbytes = random.randint(0, 10000)

            self.assertEqual(f.tell(), 0)
            x_written = f.write(b"x" * nbytes)

            self.assertEqual(f.size(), x_written)
            self.assertEqual(f.tell(), x_written)

            f.seek(nbytes, os.SEEK_CUR)
            y_written = f.write(b"y" * nbytes)

            self.assertEqual(f.size(), x_written + nbytes + y_written)
            self.assertEqual(f.tell(), x_written + nbytes + y_written)

            oldpos = f.tell()
            self.assertRaises(IOError, f.seek, -random.randint(1, 10))
            self.assertEqual(f.tell(), oldpos) # we must not have moved !

            f.seek(0, os.SEEK_END)
            self.assertEqual(f.tell(), f.size())

        with io.open(TESTFN, "rb", buffering=0) as a:

            string = a.read(4 * nbytes)
            self.assertEqual(a.read(10), b"") # we should have read until EOF here, else pb !!

            self.assertEqual(string, b"x" * x_written + b"\0" * nbytes + b"y" * y_written)


    def testTruncation(self):
        with io.open(TESTFN, 'wb', buffering=0) as f:

            nbytes = random.randint(0, 100)

            i_written = f.write(b"i" * nbytes)
            pos = f.tell()
            self.assertEqual(pos, i_written)

            # we reduce the file
            f.truncate(nbytes)
            self.assertEqual(f.size(), nbytes)
            self.assertEqual(f.tell(), pos)

            # we extend the file, by default it should fill the space with zeros !
            f.truncate(10 * nbytes)
            self.assertEqual(f.size(), 10 * nbytes)
            self.assertEqual(f.tell(), pos)

            #print ("WE AVE CHOSEN ", x_written+nbytes+y_written)
            # we try illegal, negative truncation
            self.assertRaises(IOError, f.truncate, -random.randint(1, 10))
            self.assertEqual(f.size(), 10 * nbytes)
            self.assertEqual(f.tell(), pos)


        with io.open(TESTFN, "rb", buffering=0) as a:

            string = a.read(20 * nbytes)
            self.assertEqual(a.read(10), b"") # we should have read until EOF here, else pb !!

            self.assertEqual(string, b"i" * i_written + b"\0" * (10 * nbytes - i_written))

    def testAppending(self):

        with io.open(TESTFN, 'ab', buffering=0) as f:

            nbytes = random.randint(0, 100)
            f.write(b"i" * nbytes)
            f.seek(0)
            f.write(b"j" * nbytes)

            self.assertEqual(f.tell(), 2 * nbytes)


        with io.open(TESTFN, "rb", buffering=0) as a:
            string = a.read(3 * nbytes)
            a.close()

        self.assertEqual(string, b"i" * nbytes + b"j" * nbytes)




class TestRawFileSpecialFeatures(unittest.TestCase):

    def setUp(self):
        _cleanup()

    def tearDown(self):
        _cleanup()


    def testNewAccessors(self):
        with io.open(TESTFN, 'wb', buffering=0) as f:

            (dev, inode) = f.uid()
            self.assertTrue(dev)
            self.assertTrue(inode)

            f.write(b"hhhh")

            time.sleep(2)

        with io.open(TESTFN, 'rb', buffering=0) as stream:
            stream.read()
            #we enforce access time by closing

        time.sleep(1)

        with io.open(TESTFN, 'rb', buffering=0) as stream:
            self.assertEqual(int(stream.times().access_time), int(os.fstat(stream.fileno()).st_atime))
            self.assertEqual(int(stream.times().modification_time), int(os.fstat(stream.fileno()).st_mtime))

        """ TO DEBUG NATIVE FILETIME INFO
        print ("---")
        print (time())
        print (strftime("%a, %d %b %Y %H:%M:%S +0000", localtime(time())))
        print (strftime("%a, %d %b %Y %H:%M:%S +0000", localtime(os.fstat(f.fileno()).st_atime)))
        print (strftime("%a, %d %b %Y %H:%M:%S +0000", localtime(f.times().access_time)))
        print ("=====")
        print ("---")
        print (int(f.times().access_time))
        print (int(os.fstat(f.fileno()).st_atime))
        print ("---")
        print (int(f.times().modification_time))
        print (int(os.fstat(f.fileno()).st_mtime))
        """

    def testCloseFd(self):

        f = io.open(TESTFN, 'wb', buffering=0) # low-level default python open()
        f.write(b"aaa")

        copy1 = io.open(f.fileno(), 'ab', buffering=0, closefd=False)
        copy1.write(b"bbb")

        copy2 = io.open(f.fileno(), 'ab', buffering=0, closefd=True)
        copy2.write(b"ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEqual(reader.read(), b"aaabbbccc")

        copy1.close()
        f.write(b"---")

        copy2.close()
        self.assertRaises(IOError, f.write, b"---")

        try:
            f.close() # this is normally buggy since the fd was closed through copy2...
        except EnvironmentError:
            pass

        # ------------

        f = io.open(TESTFN, 'wb', buffering=0) # low-level default python open()
        f.write(b"aaa")

        copy1 = io.open(mode='AB', buffering=0, fileno=f.fileno(), closefd=False)
        self.assertEqual(copy1.origin, "fileno")
        copy1.write(b"bbb")

        copy2 = io.open(mode='AB', buffering=0, fileno=f.fileno(), closefd=True)
        self.assertEqual(copy2.origin, "fileno")
        copy2.write(b"ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEqual(reader.read(), b"aaabbbccc")

        copy1.close()
        f.write(b"---")

        copy2.close()
        self.assertRaises(IOError, f.write, b"---")

        try:
            f.close() # this is normally buggy since the fd was closed through copy2...
        except EnvironmentError:
            pass

        # ------------

        f = io.open(TESTFN, 'wb', buffering=0) # low-level version
        f.write(b"aaa")

        copy1 = io.open(mode='AB', buffering=0, handle=f.handle(), closefd=False) # We trick the functools.partial object there...
        self.assertEqual(copy1.origin, "handle")
        copy1.write(b"bbb")

        copy2 = io.open(mode='AB', buffering=0, handle=f.handle(), closefd=True) # We trick the functools.partial object there...
        self.assertEqual(copy2.origin, "handle")
        copy2.write(b"ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEqual(reader.read(), b"aaabbbccc")

        copy1.close()
        f.write(b"---")

        copy2.close()
        self.assertRaises(IOError, f.write, b"---")


        try:
            f.close() # this is normally buggy since the fd was closed through copy2...
        except IOError:
            pass





    def testCreationOptions(self):

        kargs = dict(path=TESTFN,
                     read=True,
                     write=True, append=True,
                     must_not_create=True, must_create=False, # only used on file opening
                     )

        with io.open(TESTFN, "wb") as f:
            f.write(b"-----")


        f = rsfile.RSFileIO(**kargs)
        f.close()


        kargs["must_not_create"] = False
        kargs["must_create"] = True
        self.assertRaises(IOError, rsfile.RSFileIO, **kargs)


        os.remove(TESTFN) # important
        f = rsfile.RSFileIO(**kargs)
        f.close()

        os.remove(TESTFN) # important
        kargs["must_not_create"] = True
        kargs["must_create"] = False
        self.assertRaises(IOError, rsfile.RSFileIO, **kargs)



    def testCreationPermissions(self):

        with rsfile.rsopen(TESTFN, "RWB-", buffering=0, locking=False, permissions=0o555) as f: # creating read-only file

            with rsfile.rsopen(TESTFN, "RB+", buffering=0, locking=False) as g:
                pass # no problem

            self.assertRaises(IOError, rsfile.rsopen, TESTFN, "WB+", buffering=0, locking=False) # can't open for writing

        # no need to test further, as other permissions are non-portable and simply forwarded to underlying system calls...


    def testDeletions(self): # PAKAL - TODO - WARNING # tests both normal share-delete semantic, and delete-on-close flag

        TESTFNBIS = TESTFN + "X"
        if os.path.exists(TESTFNBIS):
            os.remove(TESTFNBIS)

        with rsfile.rsopen(TESTFN, "RB", buffering=0) as h:
            self.assertTrue(os.path.exists(TESTFN))
            os.rename(TESTFN, TESTFNBIS)
            os.remove(TESTFNBIS)
            self.assertRaises(IOError, rsfile.rsopen, TESTFN, "R+", buffering=0)
            self.assertRaises(IOError, rsfile.rsopen, TESTFNBIS, "R+", buffering=0) # on windows the file remains but in a weird state, awaiting deletion...

        """
        
        # NO NEED FOR BUILTIN DELETE ON CLOSE SEMANTIC
        with rsfile.rsopen(TESTFN, "RB", buffering=0) as f:
            
            with rsfile.rsopen(TESTFN, "RBH", buffering=0) as g: # hidden file -> deleted on opening
                self.assertTrue(os.path.exists(TESTFN))
                self.assertEqual(f.uid(), g.uid())
                old_uid = f.uid()
            # Here, Delete On Close takes effect
            fullpath = os.path.join(os.getcwd(), TESTFN)
            self.assertFalse(os.path.exists(fullpath))
            self.assertRaises(IOError, rsfile.rsopen, TESTFN, "R") # on win32, deleted file is in a weird state until all handles are closed !!
        """




    def testRsopenBehaviour(self):

        # for ease of use, we just test binary unbuffered files...

        with rsfile.rsopen(TESTFN, "RAEB", buffering=0, locking=False) as f:
            self.assertEqual(f.readable(), True)
            self.assertEqual(f.writable(), True)
            self.assertEqual(f._append, True)
            self.assertEqual(f.size(), 0)
            f.write(b"abcde")

        with rsfile.rsopen(TESTFN, "RAEB", buffering=0) as f:
            #PAKAL TO REPUT self.assertEqual(f.size(), 0)
            f.write(b"abcdef")
            f.seek(0)
            f.write(b"abcdef")
            self.assertEqual(f.size(), 12)
            self.assertEqual(f.tell(), 12)

        self.assertRaises(IOError, rsfile.rsopen, TESTFN, "RB-", buffering=0)

        with rsfile.rsopen(TESTFN, "RAEB", buffering=0) as f:
            os.rename(TESTFN, TESTFN + ".temp") # for windows platforms...
            os.remove(TESTFN + ".temp")

        self.assertRaises(IOError, rsfile.rsopen, TESTFN, "WB+", buffering=0)



    def testInheritance(self):
        # # """Checks that handles are well inherited iff this creation option is set to True"""
        kargs = dict(path=TESTFN,
                     read=False,
                     write=True, append=True,
                     inheritable=True)

        target = _worker_process.inheritance_tester

        bools = [True, False]
        permutations = [(a, b, c) for a in bools for b in bools for c in bools if (a or b or c)]

        for (inheritance, EXPECTED_RETURN_CODE) in [(True, 4), (False, 5)]:
            #print ("STATUS : ", (inheritance, EXPECTED_RETURN_CODE))
            for perm in permutations:
                (read, write, append) = perm
                #print ("->", perm)

                kwargs = dict(read=read, write=write, append=append)

                # We create the file and write something in it
                if os.path.exists(TESTFN):
                    os.remove(TESTFN)
                with io.open(TESTFN, "wb", 0) as temp:
                    temp.write(b"ABCDEFG")


                with rsfile.RSFileIO(TESTFN, inheritable=inheritance, **kwargs) as myfile:


                    if rsfile.FILE_IMPLEMENTATION == "win32":
                        kwargs["handle"] = int(myfile.handle()) # we transform the PyHandle into an integer to ensure serialization
                    else:
                        kwargs["fileno"] = myfile.fileno() # already an integer


                    executable = sys.executable
                    pre_args = ("python", "-m", "rsfile.rstest._inheritance_tester") #.os.path.join(os.path.dirname(__file__), "_inheritance_tester.py"))
                    args = (str(read), str(write), str(append), str(kwargs.get("fileno", "-")), str(kwargs.get("handle", "-")))

                    myfile.seek(0, os.SEEK_END) # to fulfill the expectations of the worker process
                    child = subprocess.Popen(pre_args + args, executable=executable, shell=False, close_fds=False)
                    retcode = child.wait()
                    self.assertEqual(retcode, EXPECTED_RETURN_CODE, "Spawned child returned %d instead of %d" % (retcode, EXPECTED_RETURN_CODE))


                    myfile.seek(0, os.SEEK_END) # to fulfill the expectations of the worker process

                    if rsfile.FILE_IMPLEMENTATION == "win32":
                        cmdline = subprocess.list2cmdline(pre_args + args) # Important for space escaping, with the buggy windows spawn implementation...
                        retcode = os.spawnl(os.P_WAIT, executable, cmdline)  # 1st argument must be the program itself !
                    else:
                        cmdline = pre_args + args
                        retcode = os.spawnv(os.P_WAIT, executable, cmdline)

                    self.assertEqual(retcode, EXPECTED_RETURN_CODE, "Spawned process returned %d instead of %d" % (retcode, EXPECTED_RETURN_CODE))


    def testSynchronization(self):

        kargs = dict(path=TESTFN,
                     read=False,
                     write=True, append=True,
                     must_not_create=False, must_create=False, # only used on file opening
                     synchronized=True)

        string = b"abcdefghijklmnopqrstuvwxyz" * 1014 * 1024
        f = rsfile.RSFileIO(**kargs)
        self.assertEqual(f._synchronized, True)
        res = f.write(string)
        self.assertEqual(res, len(string))

        f.sync(metadata=True, full_flush=True)
        f.sync(metadata=False, full_flush=True)
        f.sync(metadata=True, full_flush=False)
        f.sync(metadata=False, full_flush=False)

        f.close()

        # We have no easy way to check that the stream is REALLY in sync mode, except manually crashing the computer...



class TestMiscStreams(unittest.TestCase):

    def setUp(self):
        _cleanup()

    def tearDown(self):
        _cleanup()




    def test_builtin_patching(self):

        with open(TESTFN, "wb", buffering=0) as f:
            self.assertTrue(isinstance(f, rsfile.RSFileIO)) # no thread safe interface


    def testIOErrorOnClose(self):

        def assertCloseOK(stream):
            def ioerror():
                raise IOError("dummy error again")

            stream.flush = ioerror
            self.assertRaises(IOError, stream.close)
            self.assertEqual(True, stream.closed) # stream HAS been closed

        assertCloseOK(io.open(TESTFN, "RB", buffering=100))
        assertCloseOK(io.open(TESTFN, "WB", buffering=100))
        assertCloseOK(io.open(TESTFN, "RWB", buffering=100))
        assertCloseOK(io.open(TESTFN, "RT", buffering=100))
        assertCloseOK(io.open(TESTFN, "WT", buffering=100))
        assertCloseOK(io.open(TESTFN, "RWT", buffering=100))


    def testMethodForwarding(self):

        def test_new_methods(myfile, raw, char):

            myfile.sync()
            myfile.uid()
            myfile.times().access_time
            myfile.size()

            myfile.mode # Pakal - todo - check how it works !!!
            myfile.name
            myfile.origin
            myfile.closefd

            myfile.write(char)
            self.assertEqual(raw.size(), 0) # not yet flushed
            myfile.lock_file()
            self.assertEqual(raw.size(), 1) # has been flushed
            myfile.write(char)
            self.assertEqual(raw.size(), 1) # not yet flushed
            myfile.unlock_file()
            self.assertEqual(raw.size(), 2) # has been flushed

            myfile.truncate(0)
            self.assertEqual(myfile.tell(), 2) # file pointer is unmoved
            myfile.write(char)
            self.assertEqual(raw.size(), 0) # not yet flushed
            myfile.lock_file()
            self.assertEqual(raw.size(), 3) # has been flushed, extending file as well
            myfile.write(char)
            self.assertEqual(raw.size(), 3) # not yet flushed
            myfile.unlock_file()
            self.assertEqual(raw.size(), 4) # has been flushed

            myfile.seek(0)
            myfile.write(char * 10)
            myfile.seek(0)

            self.assertEqual(myfile.read(1), char)
            self.assertTrue(raw.tell() > 1) # read ahead buffer full
            myfile.lock_file()

            self.assertEqual(raw.tell(), 1) # read ahead buffer reset
            self.assertEqual(myfile.read(1), char)

            self.assertTrue(raw.tell() > 2) # read ahead buffer full
            myfile.unlock_file()
            self.assertEqual(raw.tell(), 2) # read ahead buffer reset

            myfile.seek(0)

            self.assertEqual(myfile.read(1), char)
            self.assertTrue(raw.tell() > 1) # read ahead buffer full
            myfile.lock_file()
            self.assertEqual(raw.tell(), 1) # read ahead buffer reset
            self.assertEqual(myfile.read(1), char)
            self.assertTrue(raw.tell() > 2) # read ahead buffer full
            myfile.unlock_file()
            self.assertEqual(raw.tell(), 2) # read ahead buffer reset


        with rsfile.rsopen(TESTFN, "RWEB", buffering=100, locking=False, thread_safe=False) as myfile: # RW buffered binary stream
            test_new_methods(myfile, myfile.raw, b"x")

        with rsfile.rsopen(TESTFN, "RWET", buffering=100, locking=False, thread_safe=False) as myfile: # text stream
            test_new_methods(myfile, myfile.buffer.raw, "x")


    def testReturnedStreamTypes(self):

        with rsfile.rsopen(TESTFN, "RWB", buffering=0, thread_safe=True) as f:
            self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))
            f.write(b"abc")
        with rsfile.rsopen(TESTFN, "RWB", buffering=0, thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.RawIOBase))
            f.write(b"abc")

        with rsfile.rsopen(TESTFN, "RWB") as f:
            self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))  # by default, thread-safe
            f.write(b"abc")
        with rsfile.rsopen(TESTFN, "RWB", thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.BufferedIOBase))
            f.write(b"abc")

        with rsfile.rsopen(TESTFN, "RWT",) as f:
            self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))
            f.write("abc")
        with rsfile.rsopen(TESTFN, "RWT", thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.TextIOBase))
            f.write("abc")


    def testStreamUtilities(self):

        # TODO IMPROVE THIS WITH OTHER ARGUMENTS

        self.assertRaises(ValueError, rsfile.write_to_file, TESTFN, b"abc", must_not_create=True, must_create=True)
        self.assertRaises(IOError, rsfile.append_to_file, TESTFN, b"abc", must_not_create=True)

        rsfile.write_to_file(TESTFN, b"abcdef", sync=True, must_create=True)
        rsfile.write_to_file(TESTFN, "abcdef", sync=False, must_not_create=True) # we overwrite TESTFN with unicode data

        rsfile.append_to_file(TESTFN, "ghijkl", sync=True, must_not_create=True)
        rsfile.append_to_file(TESTFN, "mnopqr", sync=True, must_not_create=False)

        mystr = rsfile.read_from_file(TESTFN, binary=True, buffering=0)
        mytext = rsfile.read_from_file(TESTFN, binary=False, buffering=5)

        self.assertEqual(mytext, mystr.decode("ascii"))
        self.assertEqual(mytext, "abcdefghijklmnopqr")





def test_main():
    def _launch_test_on_single_backend():
        # Historically, these tests have been sloppy about removing TESTFN.
        # So get rid of it no matter what.
        try:
            test_support.run_unittest(TestRawFileViaWrapper, TestRawFileSpecialFeatures, TestMiscStreams)
            test_original_io()
        finally:
            if os.path.exists(TESTFN):
                try:
                    os.unlink(TESTFN)
                except OSError:
                    pass

    backends = _utilities.launch_rsfile_tests_on_backends(_launch_test_on_single_backend)
    print("** RSFILE_STREAMS Test Suite has been run on backends %s **" % backends)


if __name__ == '__main__':
    test_main()

    ##_cleanup()
    #test_original_io()
    #run_unittest(TestMiscStreams)
    ##TestMiscStreams("testInheritance").testInheritance()










