


cdef class IntraProcessLockRegistryClass(object):
    
    cdef int _original_pid
    
    cdef object _lock_registry 
    
    cdef object mutex
    
    cdef void _check_forking(self)
    
    
    
    
    
    
# cdef extern IntraProcessLockRegistryClass IntraProcessLockRegistry