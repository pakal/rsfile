#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals


import os, sys
import unittest, tempfile, threading, multiprocessing, Queue , random, string, time, traceback

from rstest import _workerProcess


""" WARNING - HEAVY monkey-patching """

import rsfile
import io

rsfile.monkey_patch_io_module()

RESULT_FILE = "@RESULTFILE"



def get_character():
    return random.choice(string.ascii_lowercase).encode("ascii")   


class ThreadWithExitCode(threading.Thread):
    def run(self):
        try:
            threading.Thread.run(self)
        except Exception, e:
            print ("THREAD %s TERMINATION ON ERROR" % threading.current_thread().name)
            traceback.print_exc()
            self.exitcode = 1
        except SystemExit, e:
            self.exitcode = e.code
        else:
            self.exitcode = 0





class TestSafeFile(unittest.TestCase):

    SUBPROCESS_COUNT = 10

    def setUp(self):
        tmpFile = tempfile.NamedTemporaryFile(delete=False)
        tmpFile.close()
        
        self.dummyFileName = tmpFile.name
        
        self.processList = []
        
        try:
            self.multiprocessing_lock = multiprocessing.RLock()
        except ImportError:
            self.multiprocessing_lock = None # *bsd platforms without proper synchronization primitives
        
        self.multithreading_lock = threading.RLock()
        
    def tearDown(self):
        
        for process in self.processList:
            try:
                process.terminate()
            except AttributeError:
                pass # process might actually be a thread...
            
        if os.path.exists(RESULT_FILE):
            os.remove(RESULT_FILE)
            
        #try:
        if os.path.exists(self.dummyFileName):
            os.remove(self.dummyFileName)
        #except EnvironmentError:
        #    pass # surely the OS still hasn't released the internal locks on the file
        
        
    def _start_and_check_subprocesses(self):
        
        print ("----Subprocesses Launch ----" ) 
        
        for process in self.processList:
            print ("Process '%s' starting..."%process.name)
            process.daemon = True 
            process.start()

            
        for process in self.processList:
            process.join()

            self.assertEqual(process.exitcode, 0, "Process '%s' detected some synchronization inconsistency : retcode %d" % (process.name, process.exitcode))
            
            print ("Process '%s' exited successfully"%process.name)
    
    
    
    def test_global_locking_options(self):
        
        old_options = rsfile.get_rsfile_options()
        
        try:
                
            rsfile.set_rsfile_options(enforced_locking_timeout_value=2, 
                                      default_spinlock_delay=1)
    
            with rsfile.rsopen(self.dummyFileName, "RWEB", buffering=100, locking=True) as myfile1:
    
                with rsfile.rsopen(self.dummyFileName, "RWEB", buffering=100, locking=False) as myfile2:
                    
                    self.assertEqual(myfile2.enforced_locking_timeout_value, 2)
                    self.assertEqual(myfile2.default_spinlock_delay, 1)
                    
                    self.assertRaises(rsfile.LockingException, myfile2.lock_file, timeout=1)
    
                    self.assertRaises(rsfile.LockingException, myfile2.lock_file, timeout=3)
                    
                    self.assertRaises(RuntimeError, myfile2.lock_file, timeout=None)# blocking mode -> global option applies
      
                    start = time.time()
                    self.assertRaises(rsfile.LockingException, myfile2.lock_file, timeout=0.3)
                    delay = time.time() - start
                    self.assertTrue(0.7 < delay < 1.3, "Delay is %d" %delay) # we check that the 1 s spinlock works
       
       
            target = _workerProcess.lock_tester
    
            lockingKwargs = {'timeout': 0}            
            kwargs = {'resultQueue':None, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':None, 
                        'lockingKwargs':lockingKwargs, 'pause':9 , 'multiprocess':True}
            
            process = multiprocessing.Process(name="%s %s"%(target.__name__, "SEEK_SET"), target=target, kwargs=kwargs)                    
            process.daemon = True       
            process.start()
            
            time.sleep(4) # let the child process start
            with rsfile.rsopen(self.dummyFileName, "RWEB", buffering=100, locking=False) as myfile:
                self.assertRaises(rsfile.LockingException, myfile.lock_file, timeout=1) 
                self.assertRaises(RuntimeError, myfile.lock_file, timeout=None) # global timeout due to interprocess locking conflict
                
            process.join()
            self.assertEqual(process.exitcode, 0, "Process '%s' encountered some trouble during execution"%process.name)
    
        finally:
            rsfile.set_rsfile_options(**old_options)
        
    
    def test_intra_process_locking(self):
        """
        We check the behaviour of locks when opening several times the same file from within a process.
        """

        # the locking type must be compatible with the opening mode (enforced by some OSes)
        with rsfile.rsopen(self.dummyFileName, "RB", buffering=0, locking=False) as f:
            self.assertRaises(IOError, f.lock_file, shared=False)
        with rsfile.rsopen(self.dummyFileName, "WB", buffering=0, locking=False) as f:
            self.assertRaises(IOError, f.lock_file, shared=True)       
  
                    
        # Locking from different open files
        with rsfile.rsopen(self.dummyFileName, "RB", buffering=0, timeout=0) as _:
            
            with rsfile.rsopen(self.dummyFileName, "RB", buffering=0, timeout=0) as _:
                pass # OK - shared locking
            
            # Exclusively locking the same disk file twice from different open file objects should fail (or block...)
            self.assertRaises(rsfile.LockingException, rsfile.rsopen, self.dummyFileName, "WB", buffering=0, timeout=0)


        with rsfile.rsopen(self.dummyFileName, "RWB", buffering=0, locking=False) as f:
            
            f.lock_file(shared=True, timeout=0, length=1, offset=0, whence=os.SEEK_CUR)
            f.lock_file(shared=False, timeout=0, length=1, offset=1, whence=os.SEEK_CUR)
            f.lock_file(shared=True, timeout=0, length=3, offset=2, whence=os.SEEK_CUR)
 
           
            # No double locking !
        
            self.assertRaises(RuntimeError, f.lock_file, shared=True, timeout=None, length=1, offset=0, whence=os.SEEK_CUR) 
            self.assertRaises(RuntimeError, f.lock_file, shared=False, timeout=None, length=1, offset=0, whence=os.SEEK_CUR) 
            
            self.assertRaises(RuntimeError, f.lock_file, shared=True, timeout=0, length=1, offset=1, whence=os.SEEK_CUR) 
            self.assertRaises(RuntimeError, f.lock_file, shared=False, timeout=0, length=1, offset=1, whence=os.SEEK_CUR)
                       
            self.assertRaises(RuntimeError, f.lock_file, length=2, offset=0, whence=os.SEEK_CUR) # no lock merging !
            self.assertRaises(RuntimeError, f.lock_file, length=1, offset=3, whence=os.SEEK_CUR) # no lock splitting !
            
           
            # Todo - test locking with duplicate handles     
            """                     
                if sys.platform == 'win32':
                    self.fail("Exclusively locking the same disk file twice from different open file objects didn't fail on win32")
               if sys.platform != 'win32':
                    self.fail("Exclusively locking the same disk file twice from different open file objects shouldn't fail on unix")
                """
        
        # has the FCNTL gotcha disappeared ?
        with rsfile.rsopen(self.dummyFileName, "RWB", buffering=0, locking=True) as f:
            
            with rsfile.rsopen(self.dummyFileName, "RWB", buffering=0, locking=False) as g:
                pass 
            # we close the file -> in normal conditions, we'd lose all fcntl() locks
            
            target = _workerProcess.lock_tester
            lockingKwargs = {'timeout': 0}            
            kwargs = {'resultQueue':None, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':None, 
                        'lockingKwargs':lockingKwargs, 'pause':0 , 'multiprocess':True, 'res_by_exit_code':True}
            
            process = multiprocessing.Process(name="%s %s"%(target.__name__, "SEEK_SET"), target=target, kwargs=kwargs)                    
            process.daemon = True       
            process.start()
            process.join()
            self.assertEqual(process.exitcode, 2, "Error, we lost all locks when closing a file descriptor - exitcode %s" % process.exitcode)
                
                
            
    def _test_whole_file_mixed_locking(self, Executor, lock):
        """Mixed writer-readers and readers try to work on the whole file.
        """
        
        for i in range(self.SUBPROCESS_COUNT):
            
            if (True): #PAKAL -TODO -REPLACE THIS !!!  #random.randint(0,1)%2 == 0):
                target = _workerProcess.chunk_writer_reader 
                character = get_character()              
            else:
                target = _workerProcess.chunk_reader
                character = None
            
            #lockingKwargs = {'timeout': None} # blocking lock attempts on the whole file
            kwargs = {'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'character':character, 'mustAlwaysSucceedLocking':True }
        
            process = Executor(name="%s %d"%(target.__name__, i), target=target, kwargs=kwargs)
            
            self.processList.append(process)
        
        self._start_and_check_subprocesses()
    
    
    def test_whole_file_mixed_locking_multiprocessing(self):
        self._test_whole_file_mixed_locking(multiprocessing.Process, self.multiprocessing_lock)
        
    def test_whole_file_mixed_locking_multithreading(self):
        self._test_whole_file_mixed_locking(ThreadWithExitCode, self.multithreading_lock)        
        
        
        
        
    def _test_whole_file_readonly_locking(self, Executor, lock):
        """Checks that lots of reader processes can lock the whole file concurrently, without problem.
        """        
        
        character = get_character()
        payLoad = 10000
        
        with open(self.dummyFileName,"wb") as targetFile:
            targetFile.write(character*payLoad)
                    
        for i in range(self.SUBPROCESS_COUNT):

            target = _workerProcess.chunk_reader
            
            lockingKwargs = {'timeout': 0}            
            kwargs = {'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'character':character, 'payLoad':payLoad, 
                      'mustAlwaysSucceedLocking':True, 'lockingKwargs':lockingKwargs}
            
            process = Executor(name="%s %d"%(target.__name__, i), target=target, kwargs=kwargs)

            self.processList.append(process)
        
        self._start_and_check_subprocesses()  


    def test_whole_file_readonly_locking_multiprocessing(self):
        self._test_whole_file_readonly_locking(multiprocessing.Process, self.multiprocessing_lock)
        
    def test_whole_file_readonly_locking_multithreading(self):
        self._test_whole_file_readonly_locking(ThreadWithExitCode, self.multithreading_lock)         
        
        
        
        
        
    def _test_file_chunks_locking(self, Executor, lock):
        """Several process lock and write/read different chunks"""
        
        character = get_character()
        chunkSize = 40
        chunkNumber = 20
        totalPayLoad = chunkNumber * chunkSize
        
        
        with open(self.dummyFileName,"wb") as targetFile:
            targetFile.write(character*totalPayLoad)
            print ("====== ALL INITIALIZED TO %s =====" % character.decode("ascii"))
        
        """ # TO REMOVE
        # we add a reader process first  
        lockingKwargs = {'offset':0, 'length':0, 'timeout':None}
        kwargs = {'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'character':None, 'ioOffset':0, 'payLoad':totalPayLoad, 
                    'mustAlwaysSucceedLocking':True, 'lockingKwargs':lockingKwargs }
        process = multiprocessing.Process(name="READER", target=_workerProcess.chunk_reader, kwargs=kwargs) 
        self.processList.append(process)"""
        
        for i in range(self.SUBPROCESS_COUNT):
            
            target = _workerProcess.chunk_writer_reader 
            character = get_character()  
            ioOffset =  random.randint(0, chunkNumber-2) * chunkSize + random.randint(0, chunkSize)
        
            lockingKwargs = {'offset':ioOffset, 'length':chunkSize, 'timeout':None}
        
            kwargs = {'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'character':character, 'ioOffset':ioOffset, 
                      'payLoad':chunkSize, 'mustAlwaysSucceedLocking':True, 'lockingKwargs':lockingKwargs }
            
            process = Executor(name="%s %d (%s)"%('ID', i, character.decode("ascii")), target=target, kwargs=kwargs) ##target.__name__

            self.processList.append(process)
 
        self._start_and_check_subprocesses()   
               
               
    def test_file_chunks_locking_multiprocessing(self):
        self._test_file_chunks_locking(multiprocessing.Process, self.multiprocessing_lock)
        
    def test_file_chunks_locking_multithreading(self):
        self._test_file_chunks_locking(ThreadWithExitCode, self.multithreading_lock) 
        
        
              
    
    def _test_whence_and_timeout(self, Executor, lock, QueueClass, multiprocess):
        """Checks that the different whence values, and the timeout argument, work OK.
        Also ensures that locks are not inherited by subprocesses !
        """        
        
        character = get_character()
        payLoad = 1000
        lockedByteAbsoluteOffset = random.randint(1,payLoad-2) # we let room on each side to check for the proper delimitation of the locking 
        
        try:
            results = QueueClass() # will receive "(process_name, locking_is_successful, time_spent)" tuples from subprocesses
        except ImportError:
            results = RESULT_FILE
            with io.open(results, "wb", 0):
                pass # we just create/truncate the file
    
    
    
        with io.open(self.dummyFileName,"wb", 0) as targetFile:
            targetFile.write(character*payLoad)
        
            with targetFile.lock_file(offset=lockedByteAbsoluteOffset, length=1, timeout=0) :          
            
            
                target = _workerProcess.lock_tester
                
                fileOffset = 0 
                gap = lockedByteAbsoluteOffset - fileOffset
                lockingKwargs = {'shared': False, 'timeout': 0, 'length':1, 'offset':gap, 'whence':os.SEEK_SET}            
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs, 'multiprocess':multiprocess}
                process1 = Executor(name="%s %s"%(target.__name__, "SEEK_SET"), target=target, kwargs=kwargs)                    
                self.processList.append(process1)               
                
                fileOffset = random.randint(0,payLoad-1)
                gap = lockedByteAbsoluteOffset - fileOffset
                lockingKwargs = {'shared': False, 'timeout': 5, 'length':1, 'offset':gap, 'whence':os.SEEK_CUR}            
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs, 'multiprocess':multiprocess}
                process2 = Executor(name="%s %s"%(target.__name__, "SEEK_CUR"), target=target, kwargs=kwargs)
                self.processList.append(process2)
                
                fileOffset = payLoad # that's the position of file ending
                gap = lockedByteAbsoluteOffset - fileOffset # should be negative
                lockingKwargs = {'shared': False, 'timeout': 15, 'length':1, 'offset':gap, 'whence':os.SEEK_END} # This one should succeed after waiting sufficiently !!           
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs, 'multiprocess':multiprocess}
                process3 = Executor(name="%s %s"%(target.__name__, "SEEK_END"), target=target, kwargs=kwargs)                    
                self.processList.append(process3)
    
                
                # These two processes just check that the bits before and after the "crucial" one are well free for locking !
                fileOffset = 0 
                gap = lockedByteAbsoluteOffset - fileOffset - 1
                lockingKwargs = {'shared': False, 'timeout': 0, 'length':1, 'offset':gap, 'whence':os.SEEK_SET}            
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs, 'multiprocess':multiprocess}
                process4 = Executor(name="%s %s"%(target.__name__, "CHECK_BIT_BEFORE"), target=target, kwargs=kwargs)                    
                self.processList.append(process4)                   
                fileOffset = 0 
                # ---
                gap = lockedByteAbsoluteOffset - fileOffset + 1
                lockingKwargs = {'shared': False, 'timeout': 0, 'length':1, 'offset':gap, 'whence':os.SEEK_SET}            
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs, 'multiprocess':multiprocess}
                process5 = Executor(name="%s %s"%(target.__name__, "CHECK_BIT_AFTER"), target=target, kwargs=kwargs)                    
                self.processList.append(process5)          
                
                
                for process in self.processList:
                    print ("Process '%s' starting..."%process.name)
                    process.daemon = True
                    process.start()
            
                
                time.sleep(11) # we wait until all subprocess timeout except the last one
                
        # we release the bit lock and the file handle  
        for process in self.processList:
            process.join()
            self.assertEqual(process.exitcode, 0, "Process '%s' encountered some trouble during execution"%process.name)
        
        
        real_results = []
        if isinstance(results, basestring):
            for line in io.open(results, "rb"):
                (process_name, locking_is_successful, time_spent) = line.split("|")
                locking_is_successful = int(locking_is_successful)
                time_spent = float(time_spent)
                real_results.append((process_name, locking_is_successful, time_spent))
        else:
            while not results.empty(): 
                real_results.append(results.get())
            if hasattr(results, "close"):
                results.close()
                
                
        for real_res in real_results:
       
            (process_name, locking_is_successful, time_spent) = real_res
            
            if process_name == process1.name :
                self.assertEqual(locking_is_successful, False)
                self.assertTrue(time_spent < 3, "Timespent is %f"%time_spent)
            elif process_name == process2.name :
                self.assertEqual(locking_is_successful, False)
                self.assertTrue(2 < time_spent < 8, "Timespent is %f"%time_spent)
            elif process_name == process3.name :
                self.assertEqual(locking_is_successful, True)
                self.assertTrue( 4 < time_spent < 13, "Timespent is %f"%time_spent)   
            elif process_name == process4.name :
                self.assertEqual(locking_is_successful, True)
                self.assertTrue(time_spent < 2, "Timespent is %f"%time_spent)
            elif process_name == process5.name :
                self.assertEqual(locking_is_successful, True)
                self.assertTrue(time_spent < 2, "Timespent is %f"%time_spent)                       
            else:
                self.fail("Unknown subprocess %s" % process_name)
    
    def test_whence_and_timeout_multiprocessing(self):
        self._test_whence_and_timeout(multiprocessing.Process, self.multiprocessing_lock, multiprocessing.Queue, multiprocess=True)
        
    def test_whence_and_timeout_multithreading(self):
        self._test_whence_and_timeout(ThreadWithExitCode, self.multithreading_lock, Queue.Queue, multiprocess=False)       
                    

if __name__ == '__main__':
    
    from rstest import _utilities 
    backends = _utilities.launch_rsfile_tests_on_backends(unittest.main)

    print ("** RSFILE_LOCKING Test Suite has been run on backends %s **" % backends)
    
    #suite = unittest.defaultTestLoader.loadTestsFromName("__main__.TestSafeFile.test_intra_process_locking")
    #unittest.TextTestRunner(verbosity=2).run(suite)
    
