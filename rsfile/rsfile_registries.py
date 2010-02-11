
import os, threading


# ######### DEFAULT PARAMETERS ######## #
"""
_default_safety_options = {
    "unified_locking_behaviour": True, # TODO ???
    "default_locking_timeout": None, # all locking attempts which have no timeout set will actually fail after this time (prevents denial of service)
    "default_locking_exception": IOError, # exception raised when an enforced timeout occurs (helps detecting deadlocks)
    "max_input_load_bytes": None,  # makes readall() and other greedy operations to fail when the data gotten exceeds this size (prevents memory overflow)
    "default_spinlock_delay": 0.1 # how many seconds the program must sleep between attempts at locking a file
    }

_locked_chunks_registry = {} # for unified_locking_behaviour ?? # keys are absolute file paths, values are lists of inodes identified by their uuid, and each inode has a list of (slice_start, slice_end or None) tuples - "None" meaning "until infinity"


def get_default_safety_options():
    return _default_safety_options.copy()

def set_default_safety_options(**options):
    new_options = set(options.keys())
    all_options = set(_default_safety_options.keys())
    if not new_options <= all_options:
        raise ValueError("Unknown safety option : "+", ".join(list(new_options - all_options)))
    _default_safety_options.update(options)
"""
############################################










class IntraProcessLockRegistry(object):
    
    _original_pid = os.getpid()
    
    # keys : file uid
    # values : event + (list of locked ranges [handle, shared, start, end] where end=None means 'infinity') + attached data
    _lock_registry = {} 
    
    mutex = threading.RLock()
    
    datacount = 0 # TODO REMOVE
    
    
    @classmethod
    def _check_forking(cls):
        # unprotected method - beware
        
        # reset is required only when the current thread has just forked !
        # we've then lost all locks in the forking, so just flush the registry
        
        if os.getpid() != cls._original_pid:
            cls._lock_registry = {}
            cls._original_pid = os.getpid()
    
    
    @classmethod
    def _ensure_entry_exists(cls, uid, create=False):
        """
        Returns True iff the entry existed before the call.
        """
        if cls._lock_registry.has_key(uid):
            return True
        else:
            if create:
                cls._lock_registry[uid] = [threading.Condition(cls.mutex), [], [], 0]  # [condition, locks, data, number of threads waiting]       
            return False
            
            
    @classmethod
    def _try_locking_range(cls, uid, new_handle, new_length, new_start, new_shared):
        # unprotected method - beware
        
        new_end = (new_start+new_length) if new_length else None # None -> infinity

        #print ">Thread %s handle %s TRYING TO TAKE lock with %s" % (threading.current_thread().name, new_handle, (new_shared, new_start, new_end))        

        
        
        if cls._ensure_entry_exists(uid, create=True):
            
            for (handle, shared, start, end) in cls._lock_registry[uid][1]:
                
                if handle != new_handle and shared == new_shared== True:
                    continue # there won't be problems with shared locks from different file handles 
                
                max_start = max(start, new_start)
                
                min_end = end
                if min_end is None or (new_end is not None and new_end < min_end):
                    min_end = new_end
                
                if min_end is None or max_start < min_end: # areas are overlapping
                    if handle == new_handle:
                        raise RuntimeError("Same area of file locked twice by the same file descriptor")
                    else:
                        return False

        #print ">Thread %s handle %s takes lock with %s" % (threading.current_thread().name, new_handle, (new_shared, new_start, new_end))
        cls._lock_registry[uid][1].append((new_handle, new_shared, new_start, new_end)) # we register as owner of this lock inside this process
        return True # no badly overlapping range was found
    
 
    @classmethod
    def _try_unlocking_range(cls, uid, new_handle, new_length, new_start):    
        """
        Returns True if there are not locks left for that uid
        """
        
        # unprotected method - beware
        if not cls._ensure_entry_exists(uid, create=False):
            return True
        
        new_end = (new_start+new_length) if new_length else None # None -> infinity

        #print "<Thread %s handle %s wants to remove lock with %s" % (threading.current_thread().name, new_handle, (new_start, new_end))

        locks = cls._lock_registry[uid][1]
        for index, (handle, shared, start, end) in enumerate(locks):
            if (handle == new_handle and start == new_start and end == new_end):
                del locks[index]
                #print "THREAD %s NOTIFYING %s" % ( threading.current_thread().name, uid)
                cls._lock_registry[uid][0].notify_all() # we awake potential waiters - ALL of them
                if not locks:
                    return True
                else:
                    return False
      
        # no matching lock was found
        raise RuntimeError("Trying to unlock a file area not owned by this handle")
            
    
    @classmethod
    def register_file_lock(cls, uid, handle, length, offset, blocking, shared):
        with cls.mutex:
            
            cls._check_forking()
            
            # we handle both blocking and non-blocking locks there
            res = False
            while not res:
                res = cls._try_locking_range(uid, handle, length, offset, shared)
                if res or not blocking:
                    break
                else:
                    #print "THREAD %s WAITING REGISTRY %s" % (threading.current_thread().name, uid)
                    cls._lock_registry[uid][3] += 1
                    cls._lock_registry[uid][0].wait() # we wait on the condition until locks get removed
                    cls._lock_registry[uid][3] -= 1
                    #print "THREAD %s LEAVING REGISTRY %s" % (threading.current_thread().name, uid)
            
            #print ">Thread %s handle %s RETURNING %s from register_file_lock" % (threading.current_thread().name, handle, res)
            return res
              
              
    @classmethod
    def unregister_file_lock(cls, uid, handle, length, offset):  
        with cls.mutex:  
            
            cls._check_forking()
            
            return cls._try_unlocking_range(uid, handle, length, offset)


    @classmethod
    def remove_file_locks(cls, uid, new_handle):
        with cls.mutex:  
            
            cls._check_forking()
            
            if not cls._ensure_entry_exists(uid, create=False):
                return []
            
            removed_locks = []
            remaining_locks = []
            for record in cls._lock_registry[uid][1]:
                if record[0] == new_handle:
                    removed_locks.append(record)
                else:
                    remaining_locks.append(record)
                    
            cls._lock_registry[uid][1] = remaining_locks
            
            return removed_locks


    @classmethod
    def try_deleting_uid_entry(cls, uid):
        """
        Returns True iff an entry existed and could be deleted.
        """
        with cls.mutex:  
            
            cls._check_forking()
            
            if not cls._ensure_entry_exists(uid, create=False):
                return False
            elif cls._lock_registry[uid][1] or cls._lock_registry[uid][2] or cls._lock_registry[uid][3]: # locks, data, or waiting threads
                return False
            else:
                del cls._lock_registry[uid]
                return True
        
        
    @classmethod
    def add_uid_data(cls, uid, data):
        with cls.mutex:  
            
            cls._check_forking()
            
            cls._ensure_entry_exists(uid, create=True)
            cls._lock_registry[uid][2].append(data)
            
            cls.datacount += 1 # TO REMOVE
            # Todo -> put debugging limits, configurable !
            #print ">DATACOUNT : ", cls.datacount
            #if cls.datacount > 50: # TODO - make it configurable
            #    raise RuntimeError("Lock Registry size exceeded")
            
            
    @classmethod
    def remove_uid_data(cls, uid):
        with cls.mutex:  
            
            cls._check_forking()
            
            if cls._ensure_entry_exists(uid, create=False):
                data = cls._lock_registry[uid][2]
                cls._lock_registry[uid][2] = []
                cls.datacount -= len(data) # TO REMOVE
                #print "<DATACOUNT : ", cls.datacount
                return data
            else:
                #print "<DATACOUNT : ", cls.datacount
                return []
                
                
    @classmethod
    def uid_has_locks(cls, uid):
        with cls.mutex:  
            
            cls._check_forking()        
            
            if cls._lock_registry.has_key(uid) and cls._lock_registry[uid][1]:
                return True
            else:
                return False
            
        
