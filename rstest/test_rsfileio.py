import sys
import os
import unittest
import time
import itertools
import threading
import random
import multiprocessing, subprocess
import _workerProcess
from array import array
from weakref import proxy

from test import test_support
from test.test_support import findfile, run_unittest
from UserList import UserList


""" WARNING - HEAVY monkey-patching """

import io
import rsfile

TESTFN = "@TESTING" # we used our own one, since the test_support version is broken

# IMPORTANT - we monkey-patch the original io module !!!
rsfile.monkey_patch_original_io_module()

def test_original_io():

    import test.test_support, test.test_io, test.test_memoryio, test.test_file, test.test_bufio, test.test_fileio, test.test_largefile
    """
    test_support.use_resources = ["largefile"]  # -> decomment this to try 2Gb file operations !
    test.test_largefile.test_main()
    """
    test.test_io.test_main()
    test.test_memoryio.test_main()
    test.test_file.test_main()
    test.test_bufio.test_main()
    test.test_fileio.test_main()
    
    
    # Custom launching :
    #mytest = test.test_io.TextIOWrapperTest('testBasicIO')
    #mytest.run()




def _cleanup():
    if os.path.exists(TESTFN):
        os.chmod(TESTFN, 0777)
        os.remove(TESTFN)
    
    if os.path.exists(TESTFN+".temp"):
        os.chmod(TESTFN+".temp", 0777)
        os.remove(TESTFN+".temp")



class TestRawFileViaWrapper(unittest.TestCase):

    def setUp(self):
        _cleanup()

    
    def tearDown(self):
        _cleanup()

        
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
            x_written = f.write("x"*nbytes)
    
            self.assertEqual(f.size(), x_written)
            self.assertEqual(f.tell(), x_written)
    
            f.seek(nbytes, os.SEEK_CUR)
            y_written = f.write("y"*nbytes)
    
            self.assertEqual(f.size(), x_written+nbytes+y_written)
            self.assertEqual(f.tell(), x_written+nbytes+y_written) 
    
            oldpos = f.tell()
            self.assertRaises(IOError, f.seek, -random.randint(1, 10))
            self.assertEqual(f.tell(), oldpos) # we must not have moved !
    
            f.seek(0, os.SEEK_END)
            self.assertEqual(f.tell(), f.size()) 
    
        with io.open(TESTFN, "rb", buffering=0) as a:
            
            string = a.read(4*nbytes) 
            self.assertEqual(a.read(10), "") # we should have read until EOF here, else pb !!
    
            self.assertEqual(string, "x"*x_written+"\0"*nbytes+"y"*y_written)


    def testTruncation(self):        
        with io.open(TESTFN, 'wb', buffering=0) as f:
                
            nbytes = random.randint(0, 100) 
    
            i_written = f.write("i"*nbytes)
            pos = f.tell()
            self.assertEqual(pos, i_written) 
    
            # we reduce the file
            f.truncate(nbytes)
            self.assertEqual(f.size(), nbytes) 
            self.assertEqual(f.tell(), pos)    
    
            # we extend the file, by default it should fill the space with zeros !
            f.truncate(10*nbytes)
            self.assertEqual(f.size(), 10*nbytes) 
            self.assertEqual(f.tell(), pos) 
            
            #print "WE AVE CHOSEN ", x_written+nbytes+y_written
            # we try illegal, negative truncation
            self.assertRaises(IOError, f.truncate, -random.randint(1, 10))
            self.assertEqual(f.size(), 10*nbytes) 
            self.assertEqual(f.tell(), pos) 

            
        with io.open(TESTFN, "rb", buffering=0) as a:
            
            string = a.read(20*nbytes)
            self.assertEqual(a.read(10), "") # we should have read until EOF here, else pb !!

            self.assertEqual(string, "i"*i_written+"\0"*(10*nbytes-i_written))

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
            
        self.assertEqual(string, "i"*nbytes+"j"*nbytes)





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
            self.assertEqual(reader.read(), "aaabbbccc")

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
        self.assertEqual(copy1.origin, "fileno")
        copy1.write("bbb")

        copy2 = io.open(mode='AB', buffering=0, fileno=f.fileno(), closefd=True)
        self.assertEqual(copy2.origin, "fileno")
        copy2.write("ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEqual(reader.read(), "aaabbbccc")

        copy1.close()
        f.write("---")

        copy2.close()
        self.assertRaises(IOError, f.write, "---")

        try:
            f.close() # this is normally buggy since the fd was closed through copy2...
        except IOError:
            pass        
        
        # ------------
            
        f = io.open(TESTFN, 'wb', buffering = 0) # low-level version
        f.write("aaa")


        copy1 = io.open(mode='AB', buffering=0, handle=f.handle(), closefd=False) # We trick the functools.partial object there...
        self.assertEqual(copy1.origin, "handle")
        copy1.write("bbb")

        copy2 = io.open(mode='AB', buffering=0, handle=f.handle(), closefd=True) # We trick the functools.partial object there...
        self.assertEqual(copy2.origin, "handle")
        copy2.write("ccc")

        with open(TESTFN, "rb") as reader:
            self.assertEqual(reader.read(), "aaabbbccc")

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
                     must_not_create=True, must_create=False, # only used on file opening
                     )  

        with io.open(TESTFN, "wb") as f:
            f.write("-----")


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
        
        with rsfile.rsopen(TESTFN, "RWB-", buffering=0, locking=False, permissions=0555) as f: # creating read-only file
            
            with rsfile.rsopen(TESTFN, "RB+", buffering=0, locking=False) as g:
                pass # no problem
            
            self.assertRaises(IOError, rsfile.rsopen, TESTFN, "WB+", buffering=0, locking=False) # can't open for writing
        
        # no need to test further, as other permissions are non-portable and simply forwarded to underlying system calls...


    def testDeletions(self): # PAKAL - TODO - WARNING # tests both normal share-delete semantic, and delete-on-close flag
        
        TESTFNBIS = TESTFN+"X"
        if os.path.exists(TESTFNBIS):
            os.remove(TESTFNBIS)
        
        with rsfile.rsopen(TESTFN, "RB", buffering=0) as h:
            self.assertTrue(os.path.exists(TESTFN))
            os.rename(TESTFN, TESTFNBIS)
            os.remove(TESTFNBIS)
            self.assertRaises(IOError, rsfile.rsopen, TESTFN, "R+", buffering=0)
            self.assertRaises(IOError, rsfile.rsopen, TESTFNBIS, "R+", buffering=0) # on win32 the file remains but in a weird state, awaiting deletion...
            
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
            f.write("abcde")          

        with rsfile.rsopen(TESTFN, "RAEB", buffering=0) as f:
            #PAKAL TO REPUT self.assertEqual(f.size(), 0)
            f.write("abcdef")
            f.seek(0)
            f.write("abcdef")
            self.assertEqual(f.size(), 12)
            self.assertEqual(f.tell(), 12)

        self.assertRaises(IOError, rsfile.rsopen, TESTFN, "RB-", buffering=0)
            
        with rsfile.rsopen(TESTFN, "RAEB", buffering=0) as f:
            os.rename(TESTFN, TESTFN+".temp") # for win32 platforms...
            os.remove(TESTFN+".temp") 
        
        self.assertRaises(IOError, rsfile.rsopen, TESTFN, "WB+", buffering=0)
        
        
            
    def testInheritance(self):
        # # """Checks that handles are well inherited iff this creation option is set to True"""   
       
        kargs = dict(path=TESTFN,
                     read=False, 
                     write=True, append=True,
                     inheritable=True)        
                
        target = _workerProcess.inheritance_tester
        
        bools =  [True, False]
        permutations = [(a,b,c) for a in bools for b in bools for c in bools if (a or b or c)]
        
        for (inheritance, EXPECTED_RETURN_CODE) in [(True, 4), (False, 5)]: 
            #print "STATUS : ", (inheritance, EXPECTED_RETURN_CODE)
            for perm in permutations:
                (read, write, append) = perm
                #print "->", perm
                
                kwargs = dict(read=read, write=write, append=append)
                
                # We create the file and write something in it
                if os.path.exists(TESTFN):
                    os.remove(TESTFN)
                with io.open(TESTFN, "wb", 0) as temp:
                    temp.write("ABCDEFG")
                    
                
                with rsfile.RSFileIO(TESTFN, inheritable=inheritance, **kwargs) as myfile:
                                       
                    
                    if rsfile.FILE_IMPLEMENTATION == "win32":
                        kwargs["handle"] = int(myfile.handle()) # we transform the PyHandle into an integer to ensure serialization
                    else:
                        kwargs["fileno"] = myfile.fileno() # already an integer
                    
                    
                    executable = sys.executable
                    pre_args = ("python", os.path.join(os.path.dirname(__file__), "_inheritance_tester.py"))
                    args = (str(read), str(write), str(append), str(kwargs.get("fileno", "-")), str(kwargs.get("handle", "-")))
                   
                    myfile.seek(0, os.SEEK_END) # to fulfill the expectations of the worker process 
                    child = subprocess.Popen(pre_args+args, executable=executable, shell=False, close_fds=False)
                    retcode = child.wait()
                    self.assertEqual(retcode, EXPECTED_RETURN_CODE, "Spawned child returned %d instead of %d"%(retcode, EXPECTED_RETURN_CODE))                               
                    
                    
                    myfile.seek(0, os.SEEK_END) # to fulfill the expectations of the worker process 
                    
                    if rsfile.FILE_IMPLEMENTATION == "win32":
                        cmdline = subprocess.list2cmdline(pre_args+args) # Important for space escaping, with the buggy win32 spawn implementation...
                        retcode = os.spawnl(os.P_WAIT, executable, cmdline)  # 1st argument must be the program itself !
                    else:
                        cmdline = pre_args+args
                        retcode = os.spawnv(os.P_WAIT, executable, cmdline)
                        
                    self.assertEqual(retcode, EXPECTED_RETURN_CODE, "Spawned process returned %d instead of %d"%(retcode, EXPECTED_RETURN_CODE))                    

                
    def testSynchronization(self):
        
        kargs = dict(path=TESTFN,
                     read=False, 
                     write=True, append=True,
                     must_not_create=False, must_create=False, # only used on file opening
                     synchronized=True)
         
        string = "abcdefghijklmnopqrstuvwxyz"*1014*1024
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
    
    def WIP_____testGlobalOptions(self):
        
        old_options = rsfile.get_rsfile_options()
        
        try:
        
            new_options = dict(enforced_locking_timeout_value=2, 
                              default_spinlock_delay=1)
           
            rsfile.set_rsfile_options(**new_options)
            self.assertEqual(rsfile.get_rsfile_options(), new_options)
           
            # we ignore locking options, which are tested in the "locking-related" unit-test
            
            # here, add tests for new option....
                        
        finally:
            rsfile.set_rsfile_options(**old_options)
    
    def testIOErrorOnClose(self):
        
        def assertCloseOK(stream):
            def ioerror():
                raise IOError("dummy error again")
            
            stream.flush = ioerror
            self.assertRaises(IOError, stream.close)
            self.assertEqual(False, stream.closed) # stream has NOT been closed

        assertCloseOK(io.open(TESTFN, "RB", buffering=100))
        assertCloseOK(io.open(TESTFN, "WB", buffering=100))
        assertCloseOK(io.open(TESTFN, "RWB", buffering=100))
        assertCloseOK(io.open(TESTFN, "RT", buffering=100))
        assertCloseOK(io.open(TESTFN, "WT", buffering=100))
        assertCloseOK(io.open(TESTFN, "RWT", buffering=100))
               
    
    def testMethodForwarding(self): # PAKAL - TODO - buffer reset doesn't work with seek_cur in py26 !!!
        
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
            myfile.write(char*10)
            myfile.seek(0)
            
            self.assertEqual(myfile.read(1), char)
            self.assertTrue(raw.tell() > 1) # read ahead buffer full
            myfile.lock_file()
            self.assertEqual(raw.tell(), 1) # read ahead buffer reset
            self.assertEqual(myfile.read(1), char)
            # READ AHEAD BUFFER - print "----->{%s}" % myfile._read_buf
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
            
            
        with rsfile.rsopen(TESTFN, "RWEB", buffering=100, locking=False) as myfile: # buffered binary stream
            test_new_methods(myfile, myfile.raw, "x")
            
        with rsfile.rsopen(TESTFN, "RWET", buffering=100, locking=False) as myfile: # text stream
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
            
            res1 = parser1(TESTFN, mode1, None, None, True)
            res2 = parser2(TESTFN, mode2, None, None, True)
            msg = str((mode1,mode2))
            self.assertEqual(res1, res2, msg)
    
    
    def testReturnedStreamTypes(self):
    
        with rsfile.rsopen(TESTFN, "RWB", buffering=0, thread_safe=True) as f:
            self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))
            f.write("abc")
        with rsfile.rsopen(TESTFN, "RWB", buffering=0, thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.RawIOBase))        
            f.write("abc")
            
        with rsfile.rsopen(TESTFN, "RWB") as f:
            self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))
            f.write("abc")
        with rsfile.rsopen(TESTFN, "RWB", thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.BufferedIOBase))   
            f.write("abc")
            
        with rsfile.rsopen(TESTFN, "RWT",) as f:
            self.assertTrue(isinstance(f, rsfile.RSThreadSafeWrapper))
            f.write(u"abc")
        with rsfile.rsopen(TESTFN, "RWT", thread_safe=False) as f:
            self.assertTrue(isinstance(f, io.TextIOBase))     
            f.write(u"abc")    

            
    def testStreamUtilities(self):
        
        # TODO IMPROVE THIS WITH OTHER ARGUMENTS
        
        self.assertRaises(ValueError, rsfile.write_to_file, TESTFN, "abc", must_not_create=True, must_create=True)
        self.assertRaises(IOError, rsfile.append_to_file, TESTFN, "abc", must_not_create=True)        
        
        rsfile.write_to_file(TESTFN, "abcdef", sync=True, must_create=True)
        rsfile.write_to_file(TESTFN, u"abcdef", sync=False, must_not_create=True) # we overwrite TESTFN with unicode data
        
        rsfile.append_to_file(TESTFN, u"ghijkl", sync=True, must_not_create=True)
        rsfile.append_to_file(TESTFN, u"mnopqr", sync=True, must_not_create=False)
        
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
    
    #_cleanup()
    #TestMiscStreams("testIOErrorOnClose").testIOErrorOnClose()
    #print "===OVER==="
    
    test_main()








