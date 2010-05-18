#-*- coding: utf-8 -*-
from __future__ import with_statement
from __future__ import print_function
from __future__ import unicode_literals

import os, threading


# ######### DEFAULT PARAMETERS ######## #

_default_rsfile_options = {
    "enforced_locking_timeout_value": None, # all locking attempts which have no timeout set will actually fail after this time in seconds (prevents denial of service)
    "default_spinlock_delay": 0.1, # how many seconds the program must sleep between attempts at locking a file
    
    # "max_input_load_bytes": None  # Problem - hard to implement, we'd need to hack into every readall() and read() method from io...
    # makes readall() and other greedy operations fail when the data gotten exceeds this size (prevents memory overflow)
    }


def set_rsfile_options(**options):
    """
    Sets process-global options for rsfile, according to keyword arguments provided.
    
    .. warning::
        These options shall not be set from program libraries, only from main scripts, 
        as they affect the behaviour of rsfile in the whole program.
    
    The following keyword arguments are currently available:
    
    - *enforced_locking_timeout_value* (None or positive float, defaults to None): if set, this value is enforced 
      as a timeout value (in seconds) for all *blocking* :meth:`rsfile.lock_file()` calls (i.e those having a timeout argument 
      set to None).
      If that timeout is reached, a RuntimeError is raised. This exception is not meant to be caught, as it's
      normally the sign that a deadlock is occurring around the locking of that file. This feature is for 
      debugging purpose only.
    - *default_spinlock_delay* (positive float, default to 0.1): this value represents the sleeping time between two attempts 
      at locking a file, when using :meth:`rsfile.lock_file()` with a non-zero timeout argument. Modify this 
      value with care, as some libraries might expect a sufficient reactivity for file locking operations.
      """
    
    new_options = set(options.keys())
    all_options = set(_default_rsfile_options.keys())
    if not new_options <= all_options:
        raise ValueError("Unknown safety option : "+", ".join(list(new_options - all_options)))
    _default_rsfile_options.update(options)

    """ UNUSED OPTION
    - *max_input_load_bytes* (None or positive integer, defaults to None): if set, this value (in bytes) will be used as a limit 
      in greedy methods like :meth:`IOBase.readall` or :meth:`rsfile.read_from_file`. If the number of bytes read
      exceeds it, a RuntimeError is raised. This exception is not meant to be caught, as it's
      normally the sign that an abnormal, dangerous amount of data has been loaded into RAM. 
      This feature is for debugging purpose only.
    """


def get_rsfile_options():
    """
    Returns a dictionary with all rsfile options as key/value entries.
    """
    return _default_rsfile_options.copy()




############################################








class IntraProcessLockRegistryClass(object):
    
    
    def __init__(self):
        
        self._original_pid = os.getpid()
        
        # keys : file uid
        # values : event + (list of locked ranges [handle, shared, start, end] where end=None means 'infinity') + attached data
        self._lock_registry = {} 
        
        self.mutex = threading.RLock()
    
        #self.datacount = 0 # TODO REMOVE
        
        

    def _check_forking(self):
        # unprotected method - beware
        
        # reset is required only when the current thread has just forked !
        # we've then lost all locks in the forking, so just flush the registry
        
        if os.getpid() != self._original_pid:
            self._lock_registry = {}
            self._original_pid = os.getpid()
    
    
    
    def _ensure_entry_exists(self, uid, create=False):
        """
        Returns True iff the entry existed before the call.
        """
        if self._lock_registry.has_key(uid):
            return True
        else:
            if create:
                self._lock_registry[uid] = [threading.Condition(self.mutex), [], [], 0]  # [condition, locks, data, number of threads waiting]       
            return False
            
            
    
    def _try_locking_range(self, uid, new_handle, new_length, new_start, new_shared):
        # unprotected method - beware
        
        new_end = (new_start+new_length) if new_length else None # None -> infinity

        #print (">Thread %s handle %s TRYING TO TAKE lock with %s" % (threading.current_thread().name, new_handle, (new_shared, new_start, new_end)))        

        
        
        if self._ensure_entry_exists(uid, create=True):
            
            for (handle, shared, start, end) in self._lock_registry[uid][1]:
                
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

        #print (">Thread %s handle %s takes lock with %s" % (threading.current_thread().name, new_handle, (new_shared, new_start, new_end)))
        self._lock_registry[uid][1].append((new_handle, new_shared, new_start, new_end)) # we register as owner of this lock inside this process
        return True # no badly overlapping range was found
    
 
    
    def _try_unlocking_range(self, uid, new_handle, new_length, new_start):    
        """
        Returns True if there are not locks left for that uid
        """
        
        # unprotected method - beware
        if not self._ensure_entry_exists(uid, create=False):
            return True
        
        new_end = (new_start+new_length) if new_length else None # None -> infinity

        #print ("<Thread %s handle %s wants to remove lock with %s" % (threading.current_thread().name, new_handle, (new_start, new_end)))

        locks = self._lock_registry[uid][1]
        for index, (handle, shared, start, end) in enumerate(locks):
            if (handle == new_handle and start == new_start and end == new_end):
                del locks[index]
                #print ("THREAD %s NOTIFYING %s" % ( threading.current_thread().name, uid))
                self._lock_registry[uid][0].notify_all() # we awake potential waiters - ALL of them
                if not locks:
                    return True
                else:
                    return False
      
        # no matching lock was found
        raise RuntimeError("Trying to unlock a file area not owned by this handle")
            
    
    
    def register_file_lock(self, uid, handle, length, offset, blocking, shared, timeout):
        with self.mutex:
            
            self._check_forking()
            
            # we handle both blocking and non-blocking locks there
            res = False
            while not res:
                res = self._try_locking_range(uid, handle, length, offset, shared)
                if res or not blocking:
                    break
                else:
                    #print ("THREAD %s WAITING REGISTRY %s" % (threading.current_thread().name, uid))
                    self._lock_registry[uid][3] += 1
                    self._lock_registry[uid][0].wait(timeout) # we wait on the condition until locks get removed
                    self._lock_registry[uid][3] -= 1
                    #print ("THREAD %s LEAVING REGISTRY %s" % (threading.current_thread().name, uid))
            
            #print (">Thread %s handle %s RETURNING %s from register_file_lock" % (threading.current_thread().name, handle, res))
            return res
              
              
    
    def unregister_file_lock(self, uid, handle, length, offset):  
        with self.mutex:  
            
            self._check_forking()
            
            return self._try_unlocking_range(uid, handle, length, offset)


    
    def remove_file_locks(self, uid, new_handle):
        with self.mutex:  
            
            self._check_forking()
            
            if not self._ensure_entry_exists(uid, create=False):
                return []
            
            removed_locks = []
            remaining_locks = []
            for record in self._lock_registry[uid][1]:
                if record[0] == new_handle:
                    removed_locks.append(record)
                else:
                    remaining_locks.append(record)
                    
            self._lock_registry[uid][1] = remaining_locks
            
            return removed_locks


    
    def try_deleting_uid_entry(self, uid):
        """
        Returns True iff an entry existed and could be deleted.
        """
        with self.mutex:  
            
            self._check_forking()
            
            if not self._ensure_entry_exists(uid, create=False):
                return False
            elif self._lock_registry[uid][1] or self._lock_registry[uid][2] or self._lock_registry[uid][3]: # locks, data, or waiting threads
                return False
            else:
                del self._lock_registry[uid]
                return True
        
        
    
    def add_uid_data(self, uid, data):
        with self.mutex:  
            
            self._check_forking()
            
            self._ensure_entry_exists(uid, create=True)
            self._lock_registry[uid][2].append(data)
            
            #self.datacount += 1 # TO REMOVE
            # Todo -> put debugging limits, configurable !
            #print (">DATACOUNT : ", self.datacount)
            #if self.datacount > 50: # TODO - make it configurable
            #    raise RuntimeError("Lock Registry size exceeded")
            
            
    
    def remove_uid_data(self, uid):
        with self.mutex:  
            
            self._check_forking()
            
            if self._ensure_entry_exists(uid, create=False):
                data = self._lock_registry[uid][2]
                self._lock_registry[uid][2] = []
                #self.datacount -= len(data) # TO REMOVE
                #print("<DATACOUNT : ", self.datacount)
                return data
            else:
                #print("<DATACOUNT : ", self.datacount)
                return []
                
                
    
    def uid_has_locks(self, uid):
        with self.mutex:  
            
            self._check_forking()        
            
            if self._lock_registry.has_key(uid) and self._lock_registry[uid][1]:
                return True
            else:
                return False
            

# single global instance
IntraProcessLockRegistry = IntraProcessLockRegistryClass()

    
