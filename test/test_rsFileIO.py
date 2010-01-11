import sys
import os
import unittest
import time
import itertools
import threading
import random
import multiprocessing
import _workerProcess
from array import array
from weakref import proxy

from test import test_support
from test.test_support import findfile, run_unittest
from UserList import UserList


""" WARNING - HEAVY monkey-patching """

import io, test.test_io
import rsfile

rsfile.monkey_patch_original_io_module()

# here we can force the tests on large files too
import test.test_support as test_support
# test_support.use_resources = ["largefile"]   # -> decomment this to try 2Gb file operations !
"""
ATTENTION - penser a activer ressources for huge files ! Sinon tests zappes !
"""

TESTFN = "@TESTING" # we used our own one, since the test_support version is broken


def test_original_io():
    #del test.test_io.MiscIOTest.test_attributes # buggy tests, bufferredrandom has no MODE properly set !
    test.test_io.test_main()
    
    #mytest = test.test_io.StatefulIncrementalDecoderTest('testDecoder')
    #mytest.run()  
    #mytest = test.test_io.TextIOWrapperTest('testBasicIO')
    #mytest.run()
    
    #test_support.run_unittest(test.test_io.IOTest)
    """BytesIOTest, StringIOTest,
      BufferedReaderTest, BufferedWriterTest,
      BufferedRWPairTest, BufferedRandomTest,
      StatefulIncrementalDecoderTest,
      TextIOWrapperTest, MiscIOTest)"""





class TestRawFileViaWrapper(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TESTFN):
            os.remove(TESTFN)

    
    def tearDown(self):
        if os.path.exists(TESTFN):
            os.remove(TESTFN)

        
    def testProperties(self):
        with io.open(TESTFN, 'wb', buffering=0) as f:

            self.assertEquals(f.writable(), True)
            self.assertEquals(f.seekable(), True)
            self.assertEquals(f.readable(), False)
    
            self.assertEquals(f.name, TESTFN)
            self.assertEquals(f.mode, 'wb')
    
            #self.assertEquals(f._zerofill, True)
            self.assertEquals(f._append, False)
    
            self.assertRaises(IOError, f.read, 10)
            self.assertRaises(IOError, f.readinto, sys.stdout)

        

        
    def testSizeAndPos(self):
        with io.open(TESTFN, 'wb', buffering=0) as f:
            nbytes = random.randint(0, 10000)
    
            self.assertEquals(f.tell(), 0)
            x_written = f.write("x"*nbytes)
    
            self.assertEquals(f.size(), x_written)
            self.assertEquals(f.tell(), x_written)
    
            f.seek(nbytes, os.SEEK_CUR)
            y_written = f.write("y"*nbytes)
    
            self.assertEquals(f.size(), x_written+nbytes+y_written)
            self.assertEquals(f.tell(), x_written+nbytes+y_written) 
    
            oldpos = f.tell()
            self.assertRaises(IOError, f.seek, -random.randint(1, 10))
            self.assertEquals(f.tell(), oldpos) # we must not have moved !
    
            f.seek(0, os.SEEK_END)
            self.assertEquals(f.tell(), f.size()) 
    
        with io.open(TESTFN, "rb", buffering=0) as a:
            
            string = a.read(4*nbytes) 
            self.assertEquals(a.read(10), "") # we should have read until EOF here, else pb !!
    
            self.assertEquals(string, "x"*x_written+"\0"*nbytes+"y"*y_written)


    def testTruncation(self):        
        with io.open(TESTFN, 'wb', buffering=0) as f:
                
            nbytes = random.randint(0, 100) 
    
            i_written = f.write("i"*nbytes)
            pos = f.tell()
            self.assertEquals(pos, i_written) 
    
            # we reduce the file
            f.truncate(nbytes)
            self.assertEquals(f.size(), nbytes) 
            self.assertEquals(f.tell(), f.size())    
    
            # we extend the file, by default it should fill the space with zeros !
            f.truncate(10*nbytes)
            self.assertEquals(f.size(), 10*nbytes) 
            self.assertEquals(f.tell(), f.size())
    
            # we try illegal, negative truncation
            self.assertRaises(IOError, f.truncate, -random.randint(1, 10))
            self.assertEquals(f.size(), 10*nbytes) 
            self.assertEquals(f.tell(), f.size()) 

            
        with io.open(TESTFN, "rb", buffering=0) as a:
            
            string = a.read(20*nbytes)
            self.assertEquals(a.read(10), "") # we should have read until EOF here, else pb !!

            self.assertEquals(string, "i"*i_written+"\0"*(10*nbytes-i_written))

    def testAppending(self):
            
        with io.open(TESTFN, 'ab', buffering=0) as f:
                
            nbytes = random.randint(0, 100) 
            f.write("i"*nbytes)
            f.seek(0)
            f.write("j"*nbytes)
            
            self.assertEqual(f.tell(), 2*nbytes)
            
            
        with io.open(TESTFN, "rb", buffering=0) as a:
            string = a.read(3*nbytes)
            a.close()
            
        self.assertEquals(string, "i"*nbytes+"j"*nbytes)





class TestRawFileSpecialFeatures(unittest.TestCase): 

    def setUp(self):
        pass

    def tearDown(self):
        if os.path.exists(TESTFN):
            os.remove(TESTFN)

            
    def testNewAccessors(self):
        with io.open(TESTFN, 'wb', buffering=0) as f:
        
            (dev, inode) = f.uid()
            self.assertTrue(dev)
            self.assertTrue(inode)
            
            f.write("hhhh") 
            
            time.sleep(2) 
        
        with io.open(TESTFN, 'rb', buffering=0) as stream:
            stream.read() 
            #we enforce access time by closing
    
        time.sleep(1)
        
        with io.open(TESTFN, 'rb', buffering=0) as stream:
            self.assertEqual(int(stream.times().access_time), int(os.fstat(stream.fileno()).st_atime))
            self.assertEqual(int(stream.times().modification_time), int(os.fstat(stream.fileno()).st_mtime))
        
        """ TO DEBUG NATIVE FILETIME INFO
        print "---"
        print time()
        print strftime("%a, %d %b %Y %H:%M:%S +0000", localtime(time()))
        print strftime("%a, %d %b %Y %H:%M:%S +0000", localtime(os.fstat(f.fileno()).st_atime))
        print strftime("%a, %d %b %Y %H:%M:%S +0000", localtime(f.times().access_time))
        print "====="
        print "---"
        print int(f.times().access_time)
        print int(os.fstat(f.fileno()).st_atime)
        print "---"
        print int(f.times().modification_time)
        print int(os.fstat(f.fileno()).st_mtime)
        """
        
    def testCloseFd(self):
        
        f = io.open(TESTFN, 'wb', buffering=0) # low-level default python open()
        f.write("aaa")

        copy1 = io.open(f.fileno(), 'ab', buffering=0, closefd=False)
        copy1.write("bbb")

        copy2 = io.open(f.fileno(), 'ab', buffering=0, closefd=True)
        copy2.write("ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEquals(reader.read(), "aaabbbccc")

        copy1.close()
        f.write("---")

        copy2.close()
        self.assertRaises(IOError, f.write, "---")

        try:
            f.close() # this is normally buggy since the fd was closed through copy2...
        except IOError:
            pass
            
        # ------------
        
        f = io.open(TESTFN, 'wb', buffering=0) # low-level default python open()
        f.write("aaa")

        copy1 = io.open(mode='AB', buffering=0, fileno=f.fileno(), closefd=False)
        copy1.write("bbb")

        copy2 = io.open(mode='AB', buffering=0, fileno=f.fileno(), closefd=True)
        copy2.write("ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEquals(reader.read(), "aaabbbccc")

        copy1.close()
        f.write("---")

        copy2.close()
        self.assertRaises(IOError, f.write, "---")

        try:
            f.close() # this is normally buggy since the fd was closed through copy2...
        except IOError:
            pass        
        
        # ------------
            
        f = io.open(TESTFN, 'wb', buffering = 0) # low-level default python open()
        f.write("aaa")

        copy1 = io.open(mode='AB', buffering=0, handle=f.handle(), closefd=False)
        copy1.write("bbb")

        copy2 = io.open(mode='AB', buffering=0, handle=f.handle(), closefd=True)
        copy2.write("ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEquals(reader.read(), "aaabbbccc")

        copy1.close()
        f.write("---")

        copy2.close()
        self.assertRaises(IOError, f.write, "---")

        try:
            f.close() # this is normally buggy since the fd was closed through copy2...
        except IOError:
            pass
                
            
            
            
            
            
            
            

        
    def testCreationOptions(self):

        kargs = dict(path=TESTFN,
                     read=True, 
                     write=True, append=True,
                     must_exist=True, must_not_exist=False, # only used on file opening
                     )  

        with io.open(TESTFN, "wb") as f:
            f.write("-----")


        f = rsfile.rsFileIO(**kargs)
        f.close()
        
        
        kargs["must_exist"] = False
        kargs["must_not_exist"] = True
        self.assertRaises(IOError, rsfile.rsFileIO, **kargs)


        os.remove(TESTFN) # important
        f = rsfile.rsFileIO(**kargs)
        f.close()

        os.remove(TESTFN) # important
        kargs["must_exist"] = True
        kargs["must_not_exist"] = False
        self.assertRaises(IOError, rsfile.rsFileIO, **kargs)



    def testDeletions(self): # tests both normal share-delete semantic, and delete-on-close flag
        
        # BIG PROBLEMS - share_delete doesnt work properly on win32, 
        # TODO - EST-ce que les locks vont affecter le share-delete ici ??????

        
        with rsfile.rsOpen(TESTFN, "RB", buffering=0) as f:
            
            with rsfile.rsOpen(TESTFN, "RBD", buffering=0) as g:
                self.assertTrue(os.path.exists(TESTFN))
                self.assertEqual(f.uid(), g.uid())
                old_uid = f.uid()
            # Here, Delete On Close takes effect
            fullpath = os.path.join(os.getcwd(), TESTFN)
            self.assertFalse(os.path.exists(fullpath))
            self.assertRaises(IOError, rsfile.rsOpen, TESTFN, "R") # on win32, deleted file is in a weird state until all handles are closed !!
        
        with rsfile.rsOpen(TESTFN, "RBD", buffering=0) as h:
            self.assertTrue(os.path.exists(TESTFN))
            self.assertNotEqual(h.uid(), old_uid)
            os.remove(TESTFN)
            self.assertFalse(os.path.exists(TESTFN))
            self.assertRaises(IOError, rsfile.rsOpen, TESTFN, "R", buffering=0)
            
            
    
    
    def testRsOpenBehaviour(self):

        # for ease of use, we just test binary unbuffered files...
        
        with rsfile.rsOpen(TESTFN, "RAEB", buffering=0, locking=rsfile.LOCK_NEVER) as f:
            #self.assertEqual(f._full_file_locking_activated, True)
            self.assertEqual(f.readable(), True)
            self.assertEqual(f.writable(), True)
            self.assertEqual(f._append, True)
            self.assertEqual(f.size(), 0)
            f.write("abcde")
        self.assertEqual(f._full_file_locking_activated, False) # full file locking should automatically be removed on close            

        with rsfile.rsOpen(TESTFN, "RAEB", buffering=0) as f:
            #PAKAL TO REPUT self.assertEqual(f.size(), 0)
            f.write("abcdef")
            f.seek(0)
            f.write("abcdef")
            self.assertEqual(f.size(), 12)
            self.assertEqual(f.tell(), 12)

        self.assertRaises(IOError, rsfile.rsOpen, TESTFN, "RB-", buffering=0)
            
        with rsfile.rsOpen(TESTFN, "RAEBD", buffering=0) as f:
            pass # delete on close flag used !
        
        self.assertRaises(IOError, rsfile.rsOpen, TESTFN, "WB+", buffering=0)
        
        
            
    def testInheritance(self):
        # # """Checks that handles are well inherited iff this creation option is set to True"""   
       
        kargs = dict(path=TESTFN,
                     read=False, 
                     write=True, append=True,
                     inheritable=True)        
                
        target = _workerProcess.inheritance_tester
        
        bools =  [True, False]
        permutations = ((a,b,c) for a in bools for b in bools for c in bools if (a or b or c))
        
        for (inheritance, EXPECTED_RETURN_CODE) in [(True, 4), (False, 5)]: 
            #print (inheritance, EXPECTED_RETURN_CODE)
            for perm in permutations:
                (read, write, append) = perm
                #print perm
                
                kwargs = dict(read=read, write=write, append=append)
                
                # We create the file and write something in it
                if os.path.exists(TESTFN):
                    os.remove(TESTFN)
                with io.open(TESTFN, "wb", 0) as temp:
                    temp.write("ABCDEFG")
                    
                
                with rsfile.rsFileIO(TESTFN, inheritable=inheritance, **kwargs) as myfile:
                    myfile.seek(0, os.SEEK_END) # to fulfill the expectations of the worker process                    
                    
                    if rsfile.FILE_IMPLEMENTATION == "win32":
                        kwargs["handle"] = int(myfile.handle()) # we transform the PyHandle into an integer to ensure serialization
                    else:
                        kwargs["fileno"] = myfile.fileno() # already an integer
                    
                    # We test inheritance via subprocess module
                    process = multiprocessing.Process(name="%s"%(target.__name__), target=target, kwargs=kwargs)   
                    process.start()
                    #myfile.close() # we close our own handle immediately !
                    process.join() 
                    #print process.exitcode
                    self.assertEqual(process.exitcode, EXPECTED_RETURN_CODE, "Subprocess '%s' returned %d instead of %d"%(process.name, process.exitcode, EXPECTED_RETURN_CODE))                    
                    
                    # We test inheritance via spawn() functions
                    """ BUGGY ON WINDOWS - TODO - TRY THIS ON UNIX !!!
                    script = str(os.path.join(os.path.dirname(__file__),"inheritance_tester.py"))# '"'+ +'"'
                    args = (str(read), str(write), str(append), str(kwargs.get("fileno", "-")), str(kwargs.get("handle", "-")))
                    print "we spawn"
                    retcode = os.spawnv(os.P_WAIT, r"C:\Python26\python.exe", ("inheritance_tester.py",))  #
                    print >>sys.stderr, "spawn over"
                    self.assertEqual(retcode, EXPECTED_RETURN_CODE, "Spawned process '%s' returned %d instead of %d"%("inheritance tester", retcode, EXPECTED_RETURN_CODE))                    
                    """
                
    def testSynchronization(self):
        
        kargs = dict(path=TESTFN,
                     read=False, 
                     write=True, append=True,
                     must_exist=False, must_not_exist=False, # only used on file opening
                     synchronized=True)
         
        string = "abcdefghijklmnopqrstuvwxyz"*1014*1024
        f = rsfile.rsFileIO(**kargs)  
        self.assertEqual(f._synchronized, True)
        res = f.write(string)   
        self.assertEqual(res, len(string))
        f.close()
        
        # We have no easy way to check that the stream is REALLY in sync mode, except manually crashing the computer...
        


class TestMiscStreams(unittest.TestCase): 
    
    def setUp(self):
        pass

    def tearDown(self):
        if os.path.exists(TESTFN):
            os.remove(TESTFN)
    
    
    def testMethodForwarding(self): # PAKAL - TODO - buffer reset doesn't work with seek_cur !!!
        
        def test_new_methods(myfile, raw, char):
            
            myfile.sync()
            myfile.uid()
            myfile.times().access_time
            myfile.size()
            
            myfile.mode
            myfile.name
            myfile.path
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
            
            myfile.write(char)
            self.assertEqual(raw.size(), 0) # not yet flushed
            myfile.lock_file()
            self.assertEqual(raw.size(), 1) # has been flushed
            myfile.write(char)
            self.assertEqual(raw.size(), 1) # not yet flushed
            myfile.unlock_file()
            self.assertEqual(raw.size(), 2) # has been flushed
            myfile.write(char)
            
            myfile.seek(0)
            
            self.assertEqual(myfile.read(1), char)
            self.assertTrue(raw.tell() > 1) # read ahead buffer full
            myfile.lock_chunk()
            self.assertEqual(raw.tell(), 1) # read ahead buffer reset
            self.assertEqual(myfile.read(1), char)
            # READ AHEAD BUFFER - print "----->{%s}" % myfile._read_buf
            self.assertTrue(raw.tell() > 2) # read ahead buffer full
            myfile.unlock_chunk()
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
            
        with rsfile.rsOpen(TESTFN, "RWEB", buffering=100, locking=rsfile.LOCK_NEVER) as myfile: # buffered binary stream
            test_new_methods(myfile, myfile.raw, "x")
        with rsfile.rsOpen(TESTFN, "RWET", buffering=100, locking=rsfile.LOCK_NEVER) as myfile: # test stream
            test_new_methods(myfile, myfile.buffer.raw, u"x")     
            
        
        

    def testModeEquivalences(self):
        
        parser1 = rsfile.parse_standard_args
        parser2 = rsfile.parse_advanced_args
        
        filemodes = {
                    "r": "RI+", 
                    "w": "WIE", 
                    "a": "AI", 
                    "r+": "RWI+", 
                    "w+": "RWEI", 
                    "a+": "RWAI"
                    }
        suffixes = {
                    "": "",
                    "b": "B",
                    "t": "T"
                    }
        
        combinations = dict((mode1+suf1, mode2+suf2) for (mode1, mode2) in filemodes.items() for (suf1, suf2) in suffixes.items())
        
        for (mode1, mode2) in combinations.items():
            
            res1 = parser1(TESTFN, mode1, True)
            res2 = parser2(TESTFN, mode2, None, None, True)
            msg = str((mode1,mode2))
            self.assertEqual(res1, res2, msg)
    
    
    def testReturnedStreamTypes(self):
    
        with rsfile.rsOpen(TESTFN, "RWB", buffering=0, thread_safe=True) as f:
            self.assertTrue(isinstance(f, rsfile.ThreadSafeWrapper))
            f.write("abc")
        with rsfile.rsOpen(TESTFN, "RWB", buffering=0, thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.RawIOBase))        
            f.write("abc")
            
        with rsfile.rsOpen(TESTFN, "RWB") as f:
            self.assertTrue(isinstance(f, rsfile.ThreadSafeWrapper))
            f.write("abc")
        with rsfile.rsOpen(TESTFN, "RWB", thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.BufferedIOBase))   
            f.write("abc")
            
        with rsfile.rsOpen(TESTFN, "RWT",) as f:
            self.assertTrue(isinstance(f, rsfile.ThreadSafeWrapper))
            f.write(u"abc")
        with rsfile.rsOpen(TESTFN, "RWT", thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.TextIOBase))     
            f.write(u"abc")    

            
    def testStreamUtilities(self):
        
        self.assertRaises(AssertionError, rsfile.write_to_file, TESTFN, "abc", mode="W")
        self.assertRaises(ValueError, rsfile.write_to_file, TESTFN, "abc", must_exist=True, must_not_exist=True)
        self.assertRaises(IOError, rsfile.append_to_file, TESTFN, "abc", must_exist=True)        
        
        rsfile.write_to_file(TESTFN, "abcdef", sync=True, must_not_exist=True)
        rsfile.write_to_file(TESTFN, u"abcdef", sync=False, must_exist=True) # we overwrite TESTFN with unicode data
        
        rsfile.append_to_file(TESTFN, u"ghijkl", sync=True, must_exist=True)
        rsfile.append_to_file(TESTFN, u"mnopqr", sync=True, must_exist=False)
        
        mystr = rsfile.read_from_file(TESTFN, binary=True, buffering=0)
        mytext = rsfile.read_from_file(TESTFN, binary=False, buffering=5)
        
        self.assertEqual(mytext, unicode(mystr))
        self.assertEqual(mytext, u"abcdefghijklmnopqr")
        
        
        
def test_main():
    # Historically, these tests have been sloppy about removing TESTFN.
    # So get rid of it no matter what.
    try:
        run_unittest(TestRawFileViaWrapper, TestRawFileSpecialFeatures, TestMiscStreams) 
        test_original_io()
    finally:
        if os.path.exists(TESTFN):
            try:
                os.unlink(TESTFN)
            except OSError: 
                pass
            
            
            
if __name__ == '__main__':
    #test_original_io()
    #### run_unittest(TestMiscStreams) 
    
    #TestRawFileSpecialFeatures("testInheritance").testInheritance()
    #print "===OVER==="
    
    test_main()








