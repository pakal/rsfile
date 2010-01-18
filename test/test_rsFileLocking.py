# -*- coding: utf-8 -*-
from __future__ import with_statement


import sys, os, unittest, tempfile, multiprocessing, random, string, time

import _workerProcess


""" WARNING - HEAVY monkey-patching """

import io
import rsfile

rsfile.monkey_patch_original_io_module()

RESULT_FILE = "@RESULTFILE"

class TestSafeFile(unittest.TestCase):

    SUBPROCESS_COUNT = 10

    def setUp(self):
        tmpFile = tempfile.NamedTemporaryFile(delete=False)
        tmpFile.close()
        
        self.dummyFileName = tmpFile.name
        
        self.processList = []
        
        try:
            self.multiprocessing_lock = multiprocessing.Lock()
        except ImportError:
            self.multiprocessing_lock = None # *bsd platforms without proper synchronization primitives

    def tearDown(self):
        
        for process in self.processList:
            process.terminate()
        
        if os.path.exists(RESULT_FILE):
            os.remove(RESULT_FILE)
            
        #try:
        if os.path.exists(self.dummyFileName):
            os.remove(self.dummyFileName)
        #except EnvironmentError:
        #    pass # surely the OS still hasn't released the internal locks on the file
        
        
    def _start_and_check_subprocesses(self):
        
        print "----Subprocesses Launch type 1----"  
        
        for process in self.processList:
            print "Process '%s' starting..."%process.name
            process.daemon = True # we don't want them to wander aroudn after the tests are over...
            process.start()

            
        for process in self.processList:
            process.join()

            self.assertEqual(process.exitcode, 0, "Process '%s' detected some synchronization inconsistency : retcode %d" % (process.name, process.exitcode))
            
            print "Process '%s' exited successfully"%process.name
    
    
    
    
    def test_intra_process_locking(self):
        """We check the behaviour of locks when opening several times the same file from within a process.
        """
        
        # Warning - on linux this might succeed - how to prevent that ?????????????????
        with rsfile.rsOpen(self.dummyFileName, "WB", buffering=0, timeout=0) as f:
            try:
                with rsfile.rsOpen(self.dummyFileName, "WB", buffering=0, timeout=0) as g:
                    pass
            except rsfile.LockingException:
                if sys.platform != 'win32':
                    self.fail("Exclusively locking the same disk file twice from different open file objects shouldn't fail on unix")
    
            else:
                if sys.platform == 'win32':
                    self.fail("Exclusively locking the same disk file twice from different open file objects didn't fail on win32")
    
                
        with rsfile.rsOpen(self.dummyFileName, "RB", buffering=0, timeout=0) as f:
            with rsfile.rsOpen(self.dummyFileName, "RB", buffering=0, timeout=0) as g:
                pass # since it's a shared locking, this shoudl succeed !

                                
                
                
                
            
    def test_whole_file_mixed_locking(self):
        """Mixed writer-readers and readers try to work on the whole file.
        
        """
        
        for i in range(self.SUBPROCESS_COUNT):
            
            if (random.randint(0,1)%2 == 0):
                target = _workerProcess.chunk_writer_reader 
                character = random.choice(string.ascii_lowercase)                
            else:
                target = _workerProcess.chunk_reader
                character = None
            
            lockingKwargs = {'timeout': None} # blocking lock attempts on the whole file
            kwargs = {'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'character':character, 'mustAlwaysSucceedLocking':True }
        
            process = multiprocessing.Process(name="%s %d"%(target.__name__, i), target=target, kwargs=kwargs)
            
            self.processList.append(process)
        
        self._start_and_check_subprocesses()
        
        
        
    def test_whole_file_readonly_locking(self):
        """Checks that lots of reader processes can lock the whole file concurrently, without problem.
        """        
        
        character = random.choice(string.ascii_lowercase)
        payLoad = 10000
        
        with open(self.dummyFileName,"wb") as targetFile:
            targetFile.write(character*payLoad)
                    
        for i in range(self.SUBPROCESS_COUNT):

            target = _workerProcess.chunk_reader
            
            lockingKwargs = {'timeout': 0}            
            kwargs = {'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'character':character, 'payLoad':payLoad, 
                      'mustAlwaysSucceedLocking':True, 'lockingKwargs':lockingKwargs}
            
            process = multiprocessing.Process(name="%s %d"%(target.__name__, i), target=target, kwargs=kwargs)

            self.processList.append(process)
        
        self._start_and_check_subprocesses()  

        
        
        
    def test_file_chunks_locking(self):
        """Several process lock and write/read different chunks"""
        
        character = random.choice(string.ascii_lowercase)
        chunkSize = 40
        chunkNumber = 20
        totalPayLoad = chunkNumber * chunkSize
        
        
        with open(self.dummyFileName,"wb") as targetFile:
            targetFile.write(character*totalPayLoad)
            print "====== ALL INITIALIZED TO %c =====" % character
        
        """ # TO REMOVE
        # we add a reader process first  
        lockingKwargs = {'offset':0, 'length':0, 'timeout':None}
        kwargs = {'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'character':None, 'ioOffset':0, 'payLoad':totalPayLoad, 
                    'mustAlwaysSucceedLocking':True, 'lockingKwargs':lockingKwargs }
        process = multiprocessing.Process(name="READER", target=_workerProcess.chunk_reader, kwargs=kwargs) 
        self.processList.append(process)"""
        
        for i in range(self.SUBPROCESS_COUNT):
            
            target = _workerProcess.chunk_writer_reader 
            character = random.choice(string.ascii_lowercase)   
            ioOffset =  random.randint(0, chunkNumber-2) * chunkSize + random.randint(0, chunkSize)
        
            lockingKwargs = {'offset':ioOffset, 'length':chunkSize, 'timeout':None}
        
            kwargs = {'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'character':character, 'ioOffset':ioOffset, 
                      'payLoad':chunkSize, 'mustAlwaysSucceedLocking':True, 'lockingKwargs':lockingKwargs }
            
            process = multiprocessing.Process(name="%s %d (%c)"%('ID', i, character), target=target, kwargs=kwargs) ##target.__name__

            self.processList.append(process)
 
        self._start_and_check_subprocesses()          
    
    
    def test_whence_and_timeout(self):
        """Checks that the different whence values, and the timeout argument, work OK.
        Also ensures that locks are not inherited by subprocesses !
        """        
        
        character = random.choice(string.ascii_lowercase)
        payLoad = 1000
        lockedByteAbsoluteOffset = random.randint(1,payLoad-2) # we let room on each side to check for the proper delimitation of the locking 
        
        try:
            results = multiprocessing.Queue() # will receive "(process_name, locking_is_successful, time_spent)" tuples from subprocesses
        except ImportError:
            results = RESULT_FILE
            with io.open(results, "wb", 0):
                pass # we just create/truncate the file
    
    
    
        with io.open(self.dummyFileName,"wb", 0) as targetFile:
            targetFile.write(character*payLoad)
        
            with targetFile.lock_chunk(offset=lockedByteAbsoluteOffset, length=1, timeout=0) :          
            

            
            
                target = _workerProcess.lock_tester
                
                fileOffset = 0 
                gap = lockedByteAbsoluteOffset - fileOffset
                lockingKwargs = {'shared': False, 'timeout': 0, 'length':1, 'offset':gap, 'whence':os.SEEK_SET}            
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs}
                process1 = multiprocessing.Process(name="%s %s"%(target.__name__, "SEEK_SET"), target=target, kwargs=kwargs)                    
                self.processList.append(process1)               
                
                fileOffset = random.randint(0,payLoad-1)
                gap = lockedByteAbsoluteOffset - fileOffset
                lockingKwargs = {'shared': False, 'timeout': 5, 'length':1, 'offset':gap, 'whence':os.SEEK_CUR}            
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs}
                process2 = multiprocessing.Process(name="%s %s"%(target.__name__, "SEEK_CUR"), target=target, kwargs=kwargs)
                self.processList.append(process2)
                
                fileOffset = payLoad # that's the position of file ending
                gap = lockedByteAbsoluteOffset - fileOffset # should be negative
                lockingKwargs = {'shared': False, 'timeout': 15, 'length':1, 'offset':gap, 'whence':os.SEEK_END} # This one should succeed after waiting sufficiently !!           
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs}
                process3 = multiprocessing.Process(name="%s %s"%(target.__name__, "SEEK_END"), target=target, kwargs=kwargs)                    
                self.processList.append(process3)
    
                
                # These two processes just check that the bits before and after the "crucial" one are well free for locking !
                fileOffset = 0 
                gap = lockedByteAbsoluteOffset - fileOffset - 1
                lockingKwargs = {'shared': False, 'timeout': 0, 'length':1, 'offset':gap, 'whence':os.SEEK_SET}            
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs}
                process4 = multiprocessing.Process(name="%s %s"%(target.__name__, "CHECK_BIT_BEFORE"), target=target, kwargs=kwargs)                    
                self.processList.append(process4)                   
                fileOffset = 0 
                # ---
                gap = lockedByteAbsoluteOffset - fileOffset + 1
                lockingKwargs = {'shared': False, 'timeout': 0, 'length':1, 'offset':gap, 'whence':os.SEEK_SET}            
                kwargs = {'resultQueue':results, 'targetFileName':self.dummyFileName, 'multiprocessing_lock':self.multiprocessing_lock, 'ioOffset':fileOffset, 
                          'lockingKwargs':lockingKwargs}
                process5 = multiprocessing.Process(name="%s %s"%(target.__name__, "CHECK_BIT_AFTER"), target=target, kwargs=kwargs)                    
                self.processList.append(process5)          
                
                
                for process in self.processList:
                    print "Process '%s' starting..."%process.name
                    process.daemon = True # we don't want them to wander around after the tests are over...
                    process.start()
            
                time.sleep(10) # we wait until all subprocess timeout except the last one
                
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
            results.close()
                
                
        for real_res in real_results:
       
            (process_name, locking_is_successful, time_spent) = real_res
            
            if process_name == process1.name :
                self.assertEqual(locking_is_successful, False)
                self.assertTrue(time_spent < 3)
            elif process_name == process2.name :
                self.assertEqual(locking_is_successful, False)
                self.assertTrue(2 < time_spent < 8)
            elif process_name == process3.name :
                self.assertEqual(locking_is_successful, True)
                self.assertTrue( 7 < time_spent < 13)   
            elif process_name == process4.name :
                self.assertEqual(locking_is_successful, True)
                self.assertTrue(time_spent < 2)
            elif process_name == process5.name :
                self.assertEqual(locking_is_successful, True)
                self.assertTrue(time_spent < 2)                       
            else:
                self.fail("Unknown subprocess %s", process_name)
    
           
                    

if __name__ == '__main__':
    unittest.main()
    
    #suite = unittest.defaultTestLoader.loadTestsFromName("__main__.TestSafeFile.test_whence_and_timeout")
    #unittest.TextTestRunner(verbosity=2).run(suite)

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    