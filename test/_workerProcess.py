# -*- coding: utf-8 -*-
from __future__ import with_statement


import sys, os, time, random, string, multiprocessing
import rsfile 
import io



def _init_streams(multiprocessing_lock):
    """Sets a locking system (preferably, with a multiprocessing lock) 
    on standard output streams so that outputs don't get mixed 
    on the console together.
    """
    
    if multiprocessing_lock is None:
        return # we must be on a *bsd without semopen implementation....
    
    class newstdout:
        @classmethod
        def write(cls, str):
            multiprocessing_lock.acquire()
            sys.__stdout__.write(str.upper())
            sys.__stdout__.flush()
            multiprocessing_lock.release()
        
        @classmethod
        def flush():
            pass
            
    sys.stdout = newstdout

    class newstderr:
        @classmethod
        def write(cls, str):
            multiprocessing_lock.acquire()
            sys.__stderr__.write(str.upper())
            sys.__stderr__.flush()
            multiprocessing_lock.release()
        
        @classmethod
        def flush():
            pass
    sys.stdout = newstderr
    

def chunk_writer_reader(targetFileName, multiprocessing_lock, character, ioOffset=0, payLoad=10000, mustAlwaysSucceedLocking=False, lockingKwargs={}):
    _init_streams(multiprocessing_lock)
    
    print "Process %s created with args "%(multiprocessing.current_process().name), locals()

    
    for i in range(random.randint(5,15)):
        
        time.sleep(random.random()/5)
        
        with io.open(targetFileName,"r+b", buffering=0) as targetFile:
            
            try:
                
                # doesn't work with partial functions - kwargs = dict(((key, value) for (key, value) in lockingKwargs.items() if key in targetFile.lock_chunk.func_code.co_varnames[1:]))
                kwargs = lockingKwargs
                kwargs['shared'] = False
                
                print "Process %s wanna lock file with args "%(multiprocessing.current_process().name), kwargs
                
                
                with targetFile.lock_chunk(**kwargs):
                    
                    
                    if(random.randint(0,1)):
                        targetFile.seek(ioOffset)
                        targetFile.write(character*payLoad)
                    else:
                        for k in reversed(range(payLoad)):
                            targetFile.seek(ioOffset+k)
                            targetFile.write(character)
                     
                    time.sleep(random.random()/5)
                    
                    targetFile.seek(ioOffset)

                    print "Process %s reads %s bytes at offset %s ***"%(multiprocessing.current_process().name, payLoad, targetFile.tell())                   
                    
                    data = targetFile.read(payLoad)
                     
                    if(data != character*payLoad):
                        print "PROBLEM IN %s: " % multiprocessing.current_process().name, data, "            ><            ", character*payLoad
                        sys.exit(8)
                       
            except rsfile.LockingException:
                if(mustAlwaysSucceedLocking):
                    raise
                else:
                    #print "couldnt lock file, ok..."
                    pass
    sys.exit(0)
    
        
                
                
def chunk_reader(targetFileName, multiprocessing_lock, character=None, ioOffset=0, payLoad=10000, mustAlwaysSucceedLocking=False, lockingKwargs={}):
    _init_streams(multiprocessing_lock)
    
    for i in range(random.randint(5,15)):
        
        time.sleep(random.random()/5)
        
        with io.open(targetFileName,"rb", buffering=0)  as targetFile:
            
            try:
            
                    # doesn't work with new partial objects : kwargs = dict(((key, value) for (key, value) in lockingKwargs.items() if key in targetFile.lock_chunk.func_code.co_varnames[1:]))
                    kwargs = lockingKwargs
                    kwargs['shared'] = True      
                
                    with targetFile.lock_chunk(**kwargs):
    
                        time.sleep(random.random()/10)
                        
                        targetFile.seek(ioOffset)
                        
                        print "{{{{ %s reads %s bytes at offset %s }}}}"%(multiprocessing.current_process().name, payLoad, targetFile.tell())
                        
                        data = targetFile.read(payLoad)
                        
                        if(character is not None):
                            if(len(data) and data != character*payLoad):
                                sys.exit(3)

                     
            except rsfile.LockingException:
                if(mustAlwaysSucceedLocking):
                    raise
                else:
                    #print "couldnt lock file, ok..."
                    pass

                
def lock_tester(resultQueue, targetFileName, multiprocessing_lock, ioOffset=0, whence=os.SEEK_SET, lockingKwargs={}):
        """Tries to lock the file with the given locking parameters, and returns, in the exit code,
        if it managed to lock the file, and in any case, how much time the operation took (before success or timeout)
        Note that due to return code constraints, the timeout value must be lower than 50 for the test to work
        """
        _init_streams(multiprocessing_lock)
        
        with io.open(targetFileName,"r+b", buffering=0)  as targetFile:
            
            targetFile.seek(ioOffset, whence)
            
            start = time.time()
            
            success = None
            
            
            
            try:
                with targetFile.lock_chunk(**lockingKwargs):
                    success = True
            except rsfile.LockingException:  
                success = False
            except BaseException, e: 
                print "=======> ABNORMAL PROPAGATION OF ERROR : ", repr(e), " of ", type(e)
                raise
                  
            total = time.time() - start  # we let in float
            
            if isinstance(resultQueue, basestring):
                with io.open(resultQueue, "ab", 0) as f:
                    f.write("%s|%d|%f\n" % (multiprocessing.current_process().name, 1 if success else 0, total))
            else:
                resultQueue.put((multiprocessing.current_process().name, success, total))
                resultQueue.close()
            
            sys.exit(0)
        
        
            
            
def inheritance_tester(read, write, append, fileno=None, handle=None):
        assert not (fileno and handle)
        print >>sys.stderr, "Launching Worker Process inheritance_tester with fileno=%s and handle=%s !" % (fileno, handle)
        #sys.exit(99)        
        
        time.sleep(0.2)
        
        try:
            with rsfile.rsFileIO(read=read, write=write, append=append, fileno=fileno, handle=handle) as f:
                
                #print >>sys.stderr, "Just opening and closing the file descriptor !!"
                #sys.exit(88)                
                
                """
                print >>sys.stderr, "Filling the file from workerprocess !"
                f.write("sqsdsdqsdqklkjvlsdfqvudfbqudfhyqsudfbqudjkfhsdsdqb")
                f.flush()
                time.sleep(10)"""
                
                if not f.size() or not f.tell():
                    raise IOError("Expected a non empty file with a moved file pointer, whereas size()=%d and tell()=%d" % (f.size(), f.tell()))
                
                if read:
                    f.seek(0)
                    if not(f.read(1000)):
                        raise IOError("Impossible to read")
                else:
                    try:
                        f.seek(0)
                        f.read(1000)
                    except EnvironmentError:
                        pass
                    else:
                        sys.exit(8) # we shouldn't be able to read from this fd !
                    
                if write or append:
                    initial_size = f.size()
                    f.seek(0)
                    f.write("abcdef")
                    if append and f.size() != (initial_size+6):
                        raise IOError("Error when appending : current size %d != %d + 5" % (f.size(), initial_size))
                else:
                    try:
                        f.seek(0)
                        f.write("abcdef")
                    except EnvironmentError:
                        pass
                    else:
                        sys.exit(9) # we shouldn't be able to write to this fd !
                        
        except EnvironmentError,e:
            #print >>sys.stderr, e
            sys.exit(5)
        else:
            sys.exit(4)
            
        
        
        
