# -*- coding: utf-8 -*-
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

TESTFN = "@TESTING"  # we used our own one, since the test_support version is broken

# FORCE THIS TO TRUE if you want to check that fdatasync is faster than fuller fsync
# linux is often tested in a Virtual Machine for now, so we disable it by default because perfs are incoherent
CHECK_SYNC_PERFS = (defs.RSFILE_IMPLEMENTATION == "windows")

from test import test_support  # NOW ONLY we can import it

# to keep these test functional without mass search-replace, we just monkey-patch:
import io, _io, _pyio

rsfile.monkey_patch_io_module(_io)  # C-backed version
rsfile.monkey_patch_io_module(io)  # python interface to C-backed version
rsfile.monkey_patch_io_module(_pyio)  # (almost) pure python version
rsfile.monkey_patch_open_builtin()


def _cleanup():
    if os.path.exists(TESTFN):
        os.chmod(TESTFN, 0o777)
        os.remove(TESTFN)
    if os.path.exists(TESTFN + ".temp"):
        os.chmod(TESTFN + ".temp", 0o777)
        os.remove(TESTFN + ".temp")


class TestRSFileStreams(unittest.TestCase):
    def setUp(self):
        _cleanup()

    def tearDown(self):
        _cleanup()

    def testInvalidFd(self):  # replaces that of the stdlib
        self.assertRaises(ValueError, io.open, -10, 'wb', buffering=0, )
        bad_fd = test_support.make_bad_fd()
        self.assertRaises(IOError, io.open, bad_fd, 'wb', buffering=0)

    def testRSFileIORepr(self):
        fd = os.open(TESTFN, os.O_WRONLY | os.O_CREAT)
        try:
            with io.FileIO(fd, 'w', closefd=False) as f:
                assert f.closefd == False
                self.assertEqual(repr(f),
                                 """<rsfile.RSFileIO name=%r mode="wb" origin="fileno" closefd=False>""" % fd)
        finally:
            os.close(fd)

        with io.FileIO(TESTFN, 'w') as f:
            assert f.closefd == True
            self.assertEqual(repr(f),
                             """<rsfile.RSFileIO name="%s" mode="wb" origin="path" closefd=True>""" % TESTFN)

    def testRawFileGarbageCollection(self):
        # FileIO objects are collected, and collecting them flushes
        # all data to disk.

        # WARNING - cyclic garbage collection can't work with python objects having a __del__ method !

        import weakref

        f = io.open(TESTFN, 'wb', buffering=0)
        f.write(b"abcxxx")

        wr = weakref.ref(f)
        del f

        test_support.gc_collect()

        # print (gc.garbage) - in case of trouble

        self.assertTrue(wr() is None, wr)
        with io.open(TESTFN, "rb") as f:
            self.assertEqual(f.read(), b"abcxxx")

    def testRawFileLegacyProperties(self):
        with io.open(TESTFN, 'wb', buffering=0) as f:
            self.assertEqual(f.writable(), True)
            self.assertEqual(f.seekable(), True)
            self.assertEqual(f.readable(), False)

            self.assertEqual(f.name, TESTFN)
            self.assertEqual(f.origin, "path")
            self.assertEqual(f.mode, 'wb')

            self.assertEqual(f._append, False)

            self.assertRaises(IOError, f.read, 10)
            self.assertRaises(IOError, f.readinto, sys.stdout)

    def testDirectoryOpening(self):

        DIRNAME = "DUMMYDIR"
        try:
            os.rmdir(DIRNAME)
        except EnvironmentError:
            pass  # not existing surely...

        os.mkdir(DIRNAME)

        # we must NOT be able to open directories via rsfile !
        self.assertRaises(IOError, io.open, DIRNAME, 'rb', buffering=0)
        self.assertRaises(IOError, io.open, DIRNAME, 'wb', buffering=0)

        os.rmdir(DIRNAME)

    def testFileSizeAndPos(self):
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
            self.assertEqual(f.tell(), oldpos)  # we must not have moved !

            f.seek(0, os.SEEK_END)
            self.assertEqual(f.tell(), f.size())

        with io.open(TESTFN, "rb", buffering=0) as a:
            string = a.read(4 * nbytes)
            self.assertEqual(a.read(10), b"")  # we should have read until EOF here, else pb !!

            self.assertEqual(string, b"x" * x_written + b"\0" * nbytes + b"y" * y_written)

    def testFileTruncation(self):
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

            # print ("WE AVE CHOSEN ", x_written+nbytes+y_written)
            # we try illegal, negative truncation
            self.assertRaises(IOError, f.truncate, -random.randint(1, 10))
            self.assertEqual(f.size(), 10 * nbytes)
            self.assertEqual(f.tell(), pos)

        with io.open(TESTFN, "rb", buffering=0) as a:
            string = a.read(20 * nbytes)
            self.assertEqual(a.read(10), b"")  # we should have read until EOF here, else pb !!

            self.assertEqual(string, b"i" * i_written + b"\0" * (10 * nbytes - i_written))

    def testAppendMode(self):

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

    @unittest.skipIf(os.name == 'nt', "test only works on a POSIX-like system")
    def testPipesBehaviour(self):

        named_fifo = "named_fifo_%s" % random.randint(1, 10000)  # local file
        os.mkfifo(named_fifo)
        namedr = os.open(named_fifo, os.O_NONBLOCK)  # important not to block

        use_fileno_for_named_writer = random.choice((True, False))
        if use_fileno_for_named_writer:
            namedw = os.open(named_fifo, os.O_WRONLY)
        else:
            namedw = named_fifo

        piper, pipew = os.pipe()

        import fcntl
        # make reader nonblocking, else read() would keep waiting for more data
        fcntl.fcntl(piper, fcntl.F_SETFL, os.O_NONBLOCK)

        for (case, r, w) in [("anonymous", piper, pipew), ("named", namedr, namedw)]:

            # print("Testing pipe of type %s" % case)

            with io.open(w, "w") as writer, io.open(r, "r") as reader:

                self.assertEqual(reader.name, r)
                self.assertEqual(writer.name, w)
                self.assertEqual(reader.origin, "fileno")
                self.assertEqual(writer.origin,
                                 "path" if (case == "named" and not use_fileno_for_named_writer) else "fileno")
                self.assertEqual(reader.mode, "r")
                self.assertEqual(writer.mode, "w")

                self.assertEqual(reader.fileno(), r)
                self.assertEqual(reader.handle(), r)

                if not (case == "named" and not use_fileno_for_named_writer):
                    self.assertEqual(writer.fileno(), w)
                    self.assertEqual(writer.handle(), w)

                self.assertEqual(writer.size(), 0)
                self.assertEqual(reader.size(), 0)

                old_times = writer.times()

                time.sleep(1.2)
                writer.write("aé")
                writer.flush()

                # PIPES can't be sync'ed!
                self.assertRaises(IOError, writer.sync)
                self.assertRaises(IOError, reader.sync)

                self.assertEqual(writer.size(), 0)
                self.assertEqual(reader.size(), 0)

                res = reader.read()
                assert res == "aé"

                self.assertEqual(writer.size(), 0)
                self.assertEqual(reader.size(), 0)

                unique_id = writer.unique_id()
                assert unique_id and all(unique_id), unique_id
                self.assertEqual(reader.unique_id(), unique_id)  # same PIPE

                times = writer.times()
                assert times, times
                self.assertEqual(reader.times(), times)
                self.assertNotEqual(reader.times(), old_times)

                writer.buffer.raw.truncate(0)
                self.assertRaises(IOError, reader.buffer.raw.truncate)

                writer.truncate(0)
                self.assertRaises(IOError, reader.buffer.raw.truncate, 0)

                self.assertRaises(IOError, writer.truncate)  # fails because "relative truncation"
                self.assertRaises(IOError, reader.truncate)
                self.assertRaises(IOError, writer.truncate, 10)  # fails because "not full truncation"
                self.assertRaises(IOError, reader.truncate, 10)

                self.assertRaises(IOError, writer.tell)
                self.assertRaises(IOError, reader.tell)
                self.assertRaises(IOError, writer.seek, 0)
                self.assertRaises(IOError, reader.seek, 0)

                self.assertRaises(IOError, writer.lock_file)
                self.assertRaises(IOError, reader.lock_file)
                self.assertRaises(IOError, writer.unlock_file)
                self.assertRaises(IOError, reader.unlock_file)

            # these operations make no sense, alright
            self.assertRaises(EnvironmentError, io.open, w, "w+")
            self.assertRaises(EnvironmentError, io.open, w, "r+")
            self.assertRaises(EnvironmentError, io.open, r, "w+")
            self.assertRaises(EnvironmentError, io.open, r, "r+")

        os.unlink(named_fifo)
        # print ("FINISHED")

    def testReadWriteDataTypes(self):

        array_type = b"b" if sys.version_info < (3,) else "b"

        with io.open(TESTFN, 'wb') as f:
            f.write(b"ab")
            f.write(bytes(b"cd"))
            f.write(bytearray(b"ef"))
            f.write(array.array(array_type, [ord(b"g"), ord(b"h")]))

            f.write(memoryview(b"AB"))
            f.write(memoryview(bytes(b"CD")))
            f.write(memoryview(bytearray(b"EF")))

            try:
                f.write(memoryview(array.array(b"b", [ord(b"G"), ord(b"H")])))
                extra = b"GH"
            except TypeError:
                extra = b""
                pass  # in python2.7, array.array() has no buffer interface

        with io.open(TESTFN, 'rb') as f:
            result = b"abcdefghABCDEF" + extra

            self.assertEquals(f.read(), result)
            f.seek(0)
            self.assertEquals(f.read(), result)
            f.seek(0)

            target = array.array(array_type, b" " * 20)
            assert len(target) == 20, target
            f.readinto(target)
            assert len(target) == 20, target
            self.assertEquals(target.tostring().decode("ascii").strip(), result.decode("ascii"))  # actually BYTES

            f.seek(0)

            target = bytearray(b" " * 20)
            assert len(target) == 20, target
            f.readinto(target)
            assert len(target) == 20, target
            self.assertEquals(target.decode("ascii").strip(), result.decode("ascii"))

            f.seek(0)

            target = memoryview(bytearray(b" " * 20))
            assert len(target) == 20, target
            f.readinto(target)
            assert len(target) == 20, target
            self.assertEquals(target.tobytes().decode("ascii").strip(), result.decode("ascii"))

            f.seek(0)

            target = memoryview(bytes(b" " * 20))
            assert len(target) == 20, target
            self.assertRaises(TypeError, f.readinto, target)  # READONLY buffer

    def testNewAccessors(self):

        with io.open(TESTFN, 'wb', buffering=0) as f:
            # immediately initialized on unix actually, for intra process locks registry...
            assert bool(f._unique_id) == (defs.RSFILE_IMPLEMENTATION != "windows")

            unique_id = f.unique_id()

            assert unique_id is f._unique_id  # caching occurs
            assert f.uid() == unique_id  # retrocompatibility alias

            (dev, inode) = unique_id

            self.assertTrue(dev)
            assert isinstance(dev, (int, long))

            self.assertTrue(inode)
            assert isinstance(inode, (int, long))

            f.write(b"hhhh")

            time.sleep(2)

        with io.open(TESTFN, 'rb', buffering=0) as stream:
            stream.read()
            # we enforce access time by closing

        time.sleep(1)

        with io.open(TESTFN, 'rb', buffering=0) as stream:
            times = stream.times()
            self.assertEqual(int(times.access_time), int(os.fstat(stream.fileno()).st_atime))
            self.assertEqual(int(times.modification_time), int(os.fstat(stream.fileno()).st_mtime))

            access_datetime = datetime.fromtimestamp(times.access_time)
            modification_datetime = datetime.fromtimestamp(times.modification_time)

            now = datetime.now()  # local time

            # these timestamp stuffs might fail in FAT32 an the likes...
            assert now - timedelta(seconds=10) <= access_datetime <= now
            assert now - timedelta(seconds=10) <= modification_datetime <= now

        """ USEFUL TO DEBUG NATIVE FILETIME INFO
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

    def testCloseFdAndOrigins(self):

        f = io.open(TESTFN, 'wb', buffering=0)  # low-level default python open()
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
            f.close()  # this is normally buggy since the fd was closed through copy2...
        except EnvironmentError:
            pass

        # ------------

        f = io.open(TESTFN, 'wb', buffering=0)  # low-level default python open()
        f.write(b"aaa")

        copy1 = io.open(mode='AB', buffering=0, fileno=f.fileno(), closefd=False)
        self.assertEqual(copy1.origin, "fileno")
        assert isinstance(copy1.fileno(), (int, long))
        assert isinstance(copy1.handle(), (int, long))
        self.assertEqual(copy1.fileno(), f.fileno())
        if defs.RSFILE_IMPLEMENTATION == "windows":
            self.assertNotEqual(copy1.handle(), f.fileno())
        else:
            self.assertEqual(copy1.handle(), f.fileno())
        self.assertEqual(copy1.name, f.fileno())
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
            f.close()  # this is normally buggy since the fd was closed through copy2...
        except EnvironmentError:
            pass

        # ------------

        f = io.open(TESTFN, 'wb', buffering=0)  # low-level version
        f.write(b"aaa")

        copy1 = io.open(mode='AB', buffering=0, handle=f.handle(),
                        closefd=False)  # We trick the functools.partial object there...
        self.assertEqual(copy1.origin, "handle")
        assert isinstance(copy1.fileno(), (int, long))
        assert isinstance(copy1.handle(), (int, long))
        self.assertEqual(copy1.handle(), f.handle())
        if defs.RSFILE_IMPLEMENTATION == "windows":
            self.assertNotEqual(copy1.fileno(), f.handle())
        else:
            self.assertEqual(copy1.fileno(), f.handle())
        self.assertEqual(copy1.name, f.handle())
        copy1.write(b"bbb")

        copy2 = io.open(mode='AB', buffering=0, handle=f.handle(),
                        closefd=True)  # We trick the functools.partial object there...
        self.assertEqual(copy2.origin, "handle")
        copy2.write(b"ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEqual(reader.read(), b"aaabbbccc")

        copy1.close()
        f.write(b"---")

        copy2.close()
        self.assertRaises(IOError, f.write, b"---")

        try:
            f.close()  # this is normally buggy since the fd was closed through copy2...
        except IOError:
            pass

    def testRawFileCreationParams(self):

        kargs = dict(path=TESTFN,
                     read=True,
                     write=True, append=True,
                     must_not_create=True, must_create=False,  # only used on file opening
                     )

        with io.open(TESTFN, "wb") as f:
            f.write(b"-----")

        f = rsfile.RSFileIO(**kargs)
        f.close()

        kargs["must_not_create"] = False
        kargs["must_create"] = True
        self.assertRaises(IOError, rsfile.RSFileIO, **kargs)

        os.remove(TESTFN)  # important
        f = rsfile.RSFileIO(**kargs)
        f.close()

        os.remove(TESTFN)  # important
        kargs["must_not_create"] = True
        kargs["must_create"] = False
        self.assertRaises(IOError, rsfile.RSFileIO, **kargs)

    def testFileCreationPermissions(self):

        with rsfile.rsopen(TESTFN, "RWB-", buffering=0, locking=False,
                           permissions=0o555) as f:  # creating read-only file

            f.write(b"abc")  # WORKS, because file permissions are only applied on subsequent open()
            f.flush()

            with rsfile.rsopen(TESTFN, "RB+", buffering=0, locking=False) as g:
                pass  # no problem

            self.assertRaises(IOError, rsfile.rsopen, TESTFN, "WB+", buffering=0,
                              locking=False)  # now can't open for writing

            # no need to test further, as other permissions are non-portable and simply forwarded to underlying
            # system calls...

    def testFileDeletions(self):

        TESTFNBIS = TESTFN + "X"
        if os.path.exists(TESTFNBIS):
            os.remove(TESTFNBIS)

        with rsfile.rsopen(TESTFN, "RB", buffering=0, locking=True) as h:
            self.assertTrue(os.path.exists(TESTFN))
            os.rename(TESTFN, TESTFNBIS)
            os.remove(TESTFNBIS)
            self.assertRaises(IOError, rsfile.rsopen, TESTFN, "R+", buffering=0)
            self.assertRaises(IOError, rsfile.rsopen, TESTFNBIS, "R+", buffering=0)

            if (defs.RSFILE_IMPLEMENTATION == "windows"):
                # on windows the file remains but in a weird state, awaiting deletion, so we can't reopen it...
                self.assertRaises(IOError, rsfile.rsopen, TESTFNBIS, "w", buffering=0)
            else:
                with rsfile.rsopen(TESTFN, "wb", buffering=0):
                    pass

        """
        
        # NO NEED FOR BUILTIN DELETE ON CLOSE SEMANTIC
        with rsfile.rsopen(TESTFN, "RB", buffering=0) as f:
            
            with rsfile.rsopen(TESTFN, "RBH", buffering=0) as g: # hidden file -> deleted on opening
                self.assertTrue(os.path.exists(TESTFN))
                self.assertEqual(f.unique_id(), g.unique_id())
                old_unique_id = f.unique_id()
            # Here, Delete On Close takes effect
            fullpath = os.path.join(os.getcwd(), TESTFN)
            self.assertFalse(os.path.exists(fullpath))
            self.assertRaises(IOError, rsfile.rsopen, TESTFN, "R") # on win32, deleted file is in a weird state until
            all handles are closed !!
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
            self.assertEqual(f.size(), 0)
            f.write(b"abcdef")
            f.seek(0)
            f.write(b"abcdef")
            self.assertEqual(f.size(), 12)
            self.assertEqual(f.tell(), 12)

        self.assertRaises(IOError, rsfile.rsopen, TESTFN, "RB-", buffering=0)

        with rsfile.rsopen(TESTFN, "RAEB", buffering=0) as f:
            os.rename(TESTFN, TESTFN + ".temp")  # for windows platforms...
            os.remove(TESTFN + ".temp")

        self.assertRaises(IOError, rsfile.rsopen, TESTFN, "WB+", buffering=0)

    def testFileInheritance(self):
        # # """Checks that handles are well inherited iff this creation option is set to True"""
        kargs = dict(path=TESTFN,
                     read=False,
                     write=True, append=True,
                     inheritable=True)

        target = _worker_process.fd_inheritance_tester

        bools = [True, False]
        permutations = [(a, b, c) for a in bools for b in bools for c in bools if (a or b or c)]

        for (inheritance, EXPECTED_RETURN_CODE) in [(True, 4), (False, 5)]:
            # print ("STATUS : ", (inheritance, EXPECTED_RETURN_CODE))
            for perm in permutations:
                (read, write, append) = perm
                # print ("->", perm)

                kwargs = dict(read=read, write=write, append=append)

                # We create the file and write something in it
                if os.path.exists(TESTFN):
                    os.remove(TESTFN)
                with io.open(TESTFN, "wb", 0) as temp:
                    temp.write(b"ABCDEFG")

                with rsfile.RSFileIO(TESTFN, inheritable=inheritance, **kwargs) as myfile:

                    if defs.RSFILE_IMPLEMENTATION == "windows":
                        kwargs["handle"] = int(
                            myfile.handle())  # we transform the PyHandle into an integer to ensure serialization
                    else:
                        kwargs["fileno"] = myfile.fileno()  # already an integer

                    executable = sys.executable
                    pre_args = ("python", "-m",
                                "rsfile.rstest._fd_inheritance_tester")  # .os.path.join(os.path.dirname(__file__),
                    # "_inheritance_tester.py"))
                    args = (
                        str(read), str(write), str(append), str(kwargs.get("fileno", "-")),
                        str(kwargs.get("handle", "-")))

                    myfile.seek(0, os.SEEK_END)  # to fulfill the expectations of the worker process
                    child = subprocess.Popen(pre_args + args, executable=executable, shell=False, close_fds=False)
                    retcode = child.wait()
                    self.assertEqual(retcode, EXPECTED_RETURN_CODE,
                                     "Spawned child returned %d instead of %d" % (retcode, EXPECTED_RETURN_CODE))

                    myfile.seek(0, os.SEEK_END)  # to fulfill the expectations of the worker process

                    if defs.RSFILE_IMPLEMENTATION == "windows":
                        cmdline = subprocess.list2cmdline(
                            pre_args + args)  # Important for space escaping, with the buggy windows spawn
                        # implementation...
                        retcode = os.spawnl(os.P_WAIT, executable, cmdline)  # 1st argument must be the program itself !
                    else:
                        cmdline = pre_args + args
                        retcode = os.spawnv(os.P_WAIT, executable, cmdline)

                    self.assertEqual(retcode, EXPECTED_RETURN_CODE,
                                     "Spawned process returned %d instead of %d" % (retcode, EXPECTED_RETURN_CODE))

    def testFileSynchronization(self):

        # beware - randomization!
        buffering = random.choice([None, -1, 0, 100])
        synchronized = random.choice((True, False))

        combinations = [dict(metadata=True, full_flush=True),
                        dict(metadata=False, full_flush=True),
                        dict(metadata=True, full_flush=False),
                        dict(metadata=False, full_flush=False)]
        kwargs = dict(name=TESTFN,
                      mode="WB" + ("S" if synchronized else ""),
                      buffering=buffering)

        string = b"abcdefghijklmnopqrstuvwxyz" * 1014 * 1024

        # print("kwargs", kwargs)
        f = rsfile.rsopen(**kwargs)
        self.assertEqual(f._synchronized, synchronized)
        res = f.write(string)
        self.assertEqual(res, len(string))

        for kwargs in combinations:
            f.sync(**kwargs)

        f.close()

        top_level_breakage = random.choice((True, False))

        with rsfile.rsopen(TESTFN, "wt", thread_safe=False) as f:
            for kwargs in combinations:
                f.sync(**kwargs)

            def broken(*args, **kwargs):
                ABCD

            if top_level_breakage:
                f.flush = broken
            else:
                f.buffer.flush = broken

            try:
                # print("-------------->BEFORE", f.flush)
                for kwargs in combinations:
                    self.assertRaises(NameError, f.sync, **kwargs)  # sync implies flush!
            finally:
                if top_level_breakage:
                    del f.flush
                else:
                    del f.buffer.flush
            # print("-------------->AFTER", f.flush)
            pass

        if CHECK_SYNC_PERFS:

            # We have no easy way to check that the stream is REALLY in sync mode, except manually crashing the
            # computer... but we may check if perfs diff, at least

            with rsfile.rsopen(TESTFN, "wb", thread_safe=False) as f:

                N = 10

                # NO SYNC
                a = time.time()
                for i in range(N):
                    f.write(b"a")
                    f.flush()
                b = time.time()
                res1 = b - a

                # LIGHTEST SYNC
                a = time.time()
                for i in range(N):
                    f.write(b"b")
                    f.sync(metadata=False, full_flush=False)
                b = time.time()
                res2 = b - a

                assert res2 > 1.05 * res1, (res1, res2)  # it takes time to datasync()

                # HEAVIEST SYNC
                a = time.time()
                for i in range(N):
                    f.write(b"c")
                    # print("We issue full sync")
                    f.sync(metadata=True, full_flush=True)
                    # print("STOP")
                b = time.time()
                res3 = b - a

                if defs.RSFILE_IMPLEMENTATION == "windows":
                    assert res3 > 1.05 * res1, (res1, res3)  # same as datasync
                else:
                    assert res3 > 1.05 * res2, (res2, res3)  # full sync heavier than datasync, on linux/osx

    def testBuiltinsPatching(self):

        with open(TESTFN, "wb", buffering=0) as f:
            self.assertTrue(isinstance(f, rsfile.RSFileIO))  # no thread safe interface

    def testIOErrorOnFileClose(self):

        def assertCloseOK(stream):
            def ioerror():
                raise IOError("dummy error again")

            stream.flush = ioerror
            self.assertRaises(IOError, stream.close)
            self.assertEqual(True, stream.closed)  # stream HAS been closed

        assertCloseOK(io.open(TESTFN, "RB", buffering=100))
        assertCloseOK(io.open(TESTFN, "WB", buffering=100))
        assertCloseOK(io.open(TESTFN, "RWB", buffering=100))
        assertCloseOK(io.open(TESTFN, "RT", buffering=100))
        assertCloseOK(io.open(TESTFN, "WT", buffering=100))
        assertCloseOK(io.open(TESTFN, "RWT", buffering=100))

    def testFileMethodForwarding(self):

        def test_new_methods(myfile, raw, char):
            myfile.sync()
            myfile.unique_id()
            times = myfile.times()
            assert times.access_time > 0
            assert times.modification_time > 0
            times_repr = repr(times)
            assert "FileTimes" in times_repr and "access" in times_repr and "modification" in times_repr
            myfile.size()

            myfile.mode
            myfile.name
            myfile.origin
            myfile.closefd

            myfile.write(char)
            self.assertEqual(raw.size(), 0)  # not yet flushed
            myfile.lock_file()
            self.assertEqual(raw.size(), 1)  # has been flushed
            myfile.write(char)
            self.assertEqual(raw.size(), 1)  # not yet flushed
            myfile.unlock_file()
            self.assertEqual(raw.size(), 2)  # has been flushed

            myfile.truncate(0)
            self.assertEqual(myfile.tell(), 2)  # file pointer is unmoved
            myfile.write(char)
            self.assertEqual(raw.size(), 0)  # not yet flushed
            myfile.lock_file()
            self.assertEqual(raw.size(), 3)  # has been flushed, extending file as well
            myfile.write(char)
            self.assertEqual(raw.size(), 3)  # not yet flushed
            myfile.unlock_file()
            self.assertEqual(raw.size(), 4)  # has been flushed

            myfile.seek(0)
            myfile.write(char * 10)
            myfile.seek(0)

            self.assertEqual(myfile.read(1), char)
            self.assertTrue(raw.tell() > 1)  # read ahead buffer full
            myfile.lock_file()

            self.assertEqual(raw.tell(), 1)  # read ahead buffer reset
            self.assertEqual(myfile.read(1), char)

            self.assertTrue(raw.tell() > 2)  # read ahead buffer full
            myfile.unlock_file()
            self.assertEqual(raw.tell(), 2)  # read ahead buffer reset

            myfile.seek(0)

            self.assertEqual(myfile.read(1), char)
            self.assertTrue(raw.tell() > 1)  # read ahead buffer full
            myfile.lock_file()
            self.assertEqual(raw.tell(), 1)  # read ahead buffer reset
            self.assertEqual(myfile.read(1), char)
            self.assertTrue(raw.tell() > 2)  # read ahead buffer full
            myfile.unlock_file()
            self.assertEqual(raw.tell(), 2)  # read ahead buffer reset

        with rsfile.rsopen(TESTFN, "RWEB", buffering=100, locking=False,
                           thread_safe=False) as myfile:  # RW buffered binary stream
            test_new_methods(myfile, myfile.raw, b"x")

        with rsfile.rsopen(TESTFN, "RWET", buffering=100, locking=False, thread_safe=False) as myfile:  # text stream
            test_new_methods(myfile, myfile.buffer.raw, "x")

    def testReturnedStreamTypes(self):

        for forced_mutex in [None, threading.RLock(), multiprocessing.RLock()]:
            with rsfile.rsopen(TESTFN, "RWB", buffering=0, mutex=forced_mutex) as f:  # by default, thread-safe
                self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))
                self.assertEqual(f.mutex, forced_mutex if forced_mutex else f.mutex)
                f.write(b"abc")
            with rsfile.rsopen(TESTFN, "RWB", buffering=0, thread_safe=False) as f:
                self.assertTrue(isinstance(f, io.RawIOBase))
                f.write(b"abc")

            with rsfile.rsopen(TESTFN, "RWB", mutex=forced_mutex) as f:
                self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))
                self.assertEqual(f.mutex, forced_mutex if forced_mutex else f.mutex)
                f.write(b"abc")
            with rsfile.rsopen(TESTFN, "RWB", thread_safe=False) as f:
                self.assertTrue(isinstance(f, io.BufferedIOBase))
                f.write(b"abc")

            with rsfile.rsopen(TESTFN, "RWT", mutex=forced_mutex) as f:
                self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))
                self.assertEqual(f.mutex, forced_mutex if forced_mutex else f.mutex)
                f.write("abc")
            with rsfile.rsopen(TESTFN, "RWT", thread_safe=False) as f:
                self.assertTrue(isinstance(f, io.TextIOBase))
                f.write("abc")

    def testFileUtilities(self):

        # quick tests: since most args are just transferred to rsopen, risks of bug are low

        self.assertRaises(ValueError, rsfile.write_to_file, TESTFN, b"abc", must_not_create=True, must_create=True)
        self.assertRaises(IOError, rsfile.append_to_file, TESTFN, b"abc", must_not_create=True)

        rsfile.write_to_file(TESTFN, b"abcdef", sync=True, must_create=True)
        rsfile.write_to_file(TESTFN, "abcdef", sync=False, must_not_create=True,
                             encoding="latin1")  # we overwrite TESTFN with unicode data

        rsfile.append_to_file(TESTFN, b"ghijkl", sync=True, must_not_create=True)
        rsfile.append_to_file(TESTFN, "mnopqr", sync=False, must_not_create=False, errors="replace")

        mystr = rsfile.read_from_file(TESTFN, binary=True, buffering=0)
        mytext = rsfile.read_from_file(TESTFN, binary=False, buffering=5, newline="\n")

        self.assertEqual(mytext, mystr.decode("ascii"))
        self.assertEqual(mytext, "abcdefghijklmnopqr")

    def testDeprecatedRSOpenFlags(self):

        other_args = dict(fileno=None, handle=None, closefd=None)

        resplus1 = rsfile.parse_advanced_args("dummy", "W+", **other_args)
        resplus2 = rsfile.parse_advanced_args("dummy", "WN", **other_args)
        assert resplus1 == resplus2, (resplus1, resplus2)

        resminus1 = rsfile.parse_advanced_args("dummy", "W-", **other_args)
        resminux2 = rsfile.parse_advanced_args("dummy", "WC", **other_args)
        assert resminus1 == resminux2, (resminus1, resminux2)

        assert resplus1 != resminus1, (resplus1, resminus1)

    def testConflictsBetweenLockingAndOperations(self):

        f = rsfile.rsopen(TESTFN, "RWE", thread_safe=False, locking=False)

        f.lock_file(shared=False)
        f.write("héllo")
        f.flush()
        f.seek(0)
        data = f.read()
        self.assertEqual(data, "héllo")
        f.unlock_file()

        f.lock_file(shared=True)
        self.assertEqual(f.read(), "")
        if (defs.RSFILE_IMPLEMENTATION == "windows"):
            f.write("bye")
            self.assertRaises(IOError, f.flush)
            # data in buffers blocks implicit flush...
            self.assertRaises(IOError, f.unlock_file)
            assert f._buffer._write_buf, f._buffer._write_buf
            del f._buffer._write_buf[:]  # else error on closing flush()
            f.flush()
        else:
            f.write("bye")
            f.flush()
        f.unlock_file()

        # no problem if we write OUTSIDE of the locked area though
        f.lock_file(length=1, offset=100, shared=True)
        f.seek(0)
        f.truncate()
        f.write("twist")
        f.flush()
        f.seek(0)
        data = f.read()
        self.assertEqual(data, "twist")
        f.unlock_file(length=1, offset=100)

        f.close()


def test_main():
    def _launch_test_on_single_backend():
        # Historically, these tests have been sloppy about removing TESTFN.
        # So get rid of it no matter what.
        try:
            test_support.run_unittest(TestRSFileStreams)
        finally:
            if os.path.exists(TESTFN):
                try:
                    os.unlink(TESTFN)
                except OSError:
                    pass

    backends = _utilities.launch_rsfile_tests_on_backends(_launch_test_on_single_backend)
    print("** RSFILE_STREAMS Test Suite has been run on backends %s **\n" % backends)


if __name__ == '__main__':
    test_main()

    ##_cleanup()
    # test_original_io()
    # run_unittest(TestMiscStreams)
    ##TestRSFileStreams("testConflictsBetweenLockingAndOperations").testConflictsBetweenLockingAndOperations()
    # print("OK DONE")
