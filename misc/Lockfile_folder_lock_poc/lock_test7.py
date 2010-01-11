
import os, sys, threading, random, time, glob, shutil
os.umask(0)

## Process-limited locks for debugging purpose only ! ##

# lock that is equal to the lockDir
globalLock = threading.RLock()

# lock that is equal to the result of the "rat race"
# for becomiong the cleaner process
cleanerLock = threading.RLock()

#modified file
myfile = r"c:\\windows\temp\locking\tester.txt"
mylog = r"c:\\windows\temp\locking\testerlog.txt"
lockDir = r"C:\Windows\Temp\locking\TESTS\megalock.lock"






class locker(threading.Thread):

    # delay in seconds to be sure all the cleaning challengers have well finished their attempt
    
    
    def __init__(self, _name,  _lockDir, _lockValidityTimeSeconds):
        threading.Thread.__init__(self)

        self._name = str(_name)
        self._lockDir = _lockDir
        self._lockValidityDelaySeconds = _lockValidityTimeSeconds
        self._cleaningSecurityDelaySeconds = 3 # seconds


    def run(self):
        
        time.sleep(random.random())
        while(not self._acquireMainLock()):
            self._ensureLockIsValid()   
            time.sleep(random.random()/2)
            

        
        ###
        global globalLock
        res = globalLock.acquire(blocking=False)

        if(not res):
            print "MADNESS ! Lock taken twice !!!"
            exit()
            
            
            
        print "Thread "+self._name+" on action !"
        self._performCriticalOperations()
        
        

        globalLock.release()
        ###
        

            
        if(False):#random.randint(0,2)==0):
            print "     Thread "+self._name+" dies unexpectedly !"
        else:
            self._releaseMainLock()
        
        

        

    def _performCriticalOperations(self):
        
        global myfile
        
        lines=[]
        
        f = open(myfile,"r",0)        
        for line in f:
            lines.append(int(line.strip("\n ")))
        f.close()
        
        time.sleep(random.random())
        
        f = open(myfile,"w",0)        
        for integer in reversed(lines):
            f.write(str(integer+1)+"\n")
        f.close()       
        
        
        
        
        
    def _acquireMainLock(self):

        try:
            os.mkdir(self._lockDir)
            return True
        except Exception :
            return False


    def _releaseMainLock(self):
        try:
            os.rmdir(self._lockDir)
        except:
            pass

    
    def _mainLockExists(self):
        return os.path.exists(self._lockDir)


    # Can throw IOError
    def _isNodeObsolete(self, node):
        
        stat = os.stat(node)

        if(stat.st_atime + self._lockValidityDelaySeconds < time.time()):
            return True

        return False




             
    def _cleanSecurelyEverything(self, startTime):

        
        global cleanerLock
        res = cleanerLock.acquire(blocking=False)
        if(not res):
            print "MADNESS ! Cleaning Lock taken twice !!!"
            exit()
            
        # Important : we ensure all that file acquisition didn't take too long ! 
        # Else race cases could occur with an other cleaning process...
        if(time.time() > startTime+int(self._cleaningSecurityDelaySeconds/2)):
            return
        
        
        # we delete the main lock file
        for j in range(10): #we try several times, in case windows makes access errors on the lock file since other threads are reading it...
            try:
                if(self._mainLockExists()): #the lock dir is obsolete, so no one will remove it between those 2 operations
                    self._releaseMainLock() #The lock dir must be EMPTY                
                break
                #shutil.rmtree(self._lockDir);
                #os.utime(self._lockDir, None)
            except:
                time.sleep(random.random()/4)
                #weird problem, unable to delete/utime the file, why ? Deleted by someone else ? ARgh...
        else:     
            print "MADNESS - Impossible to delete the obsolete lock in spite of 10 attempts !"
            raise


        # VERY IMPORTANT - we ensure there that there are no more processed in the cleaning-lock-obtention-race !
        time.sleep(self._cleaningSecurityDelaySeconds) 

        

        cleanerLock.release()
        
        # we clean the cleaning lock files
        challengeFilePattern = self._lockDir+".cleanerAttempt*"
        cleaningLockFiles = glob.glob(challengeFilePattern)
        for cleaningLockFile in cleaningLockFiles:
            try:
                os.remove(cleaningLockFile)
            except:
                print "Thread "+self._name+" IMPOSSIBLE TO REMOVE CLEANING LOCK "+cleaningLockFile
                # we can't delete this cleaning lock file ? Weird, but who cares - it'll become obsolete anyhow
                raise

            
            

    def _acquire_cleaning_lock(self):
        
        challengeFilePattern = self._lockDir+".cleanerAttempt%03d"

        for i in xrange(1000): # it's kind of impossible to have 1000 processes crashing just after taking the lock...

            currentChallengeLock = challengeFilePattern%(i)

            res = os.path.exists(currentChallengeLock);

            if(not res): # we try to acquire this available lock !
                try:
                    os.mkdir(currentChallengeLock)
                    return True
                except:
                    return False
                
            else:
                # the lock file already exists - is it obsolete ?
                try :
                    res = self._isNodeObsolete(currentChallengeLock)

                    if(not res):
                        # this is well a lock held by another process so we abort our attempt
                        return False
                    else:
                        # we continue the loop since to the next lock file, since it's an obsolete cleaning lock...
                        pass 
                except:
                    # Big trouble - the lock file has been deleted inbetween !
                    # By whom ? How comes ? It shouldn't be so if the cleaner had waited properly
                    raise # Fatal error

        else:
            # Problem - we went until 1000 without solving the pb !!!
            raise Exception, "Too many cleaning locks in folder !!!"
            
        

                                
    def _tryToCleanEverythingAndBecomeTheMaster(self, startTime):
            print " Inside _tryToCleanEverythingAndBecomeTheMaster"
            res = self._acquire_cleaning_lock()
            
            
            if(not res):
                print " WE LOST"
                #we have not won the race, so we wait until the cleaner has finished his job and let a security delay
                time.sleep(self._cleaningSecurityDelaySeconds)
                return False
            else:
                print " WE WON"
                self._cleanSecurelyEverything(startTime)
                return True
            
       
            
    def _ensureLockIsValid(self):

        startTime = time.time()
        
        try:
            res = self._isNodeObsolete(self._lockDir)
        except :
            return #file has disappeared inbetween, so we just let go...
        
        if(res):
            print "Thread "+self._name+" thinks lock is obselete !"
            newRes = self._tryToCleanEverythingAndBecomeTheMaster(startTime)
            if(newRes):
                # we've obtained the lock by cleaning
                print "Thread "+self._name+" has cleaned everything !!!"
                pass#break
            else:
                print "Thread "+self._name+" lost the race..."
                # an other process has cleaned everything in theory, so we loop again...
                pass

        
        
        




if(__name__=="__main__"):

    

    for tests in range(25):
        
        l = open(mylog,"w",0)
        sys.stdout = l
        
        if(os.path.exists(lockDir)):
            shutil.rmtree(lockDir)
        
            
        if(os.path.exists(myfile)):
            os.remove(myfile)
        f = open(myfile,"w",0)
        f.write("0\n"*50)
        f.close()
        
    

        threads = []
        for i in range(60):
            myThread = locker(i,lockDir, 4)
            threads.append(myThread)
            myThread.start()
    
        for thread in threads:
            thread.join()
        
        print "JOB FINISHED !\n\n"
         
             
        l.close()    
        os.rename(mylog,"c:\\\\windows\\temp\\locking\\results\\"+str(int(time.time()))+".log")
        os.rename(myfile,"c:\\\\windows\\temp\\locking\\results\\"+str(int(time.time()))+".txt")
