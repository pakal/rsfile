



import os, sys

def launch_rsfile_tests_on_backends(test_main):
    backends = []
    
    if sys.platform == 'win32':
        import rsfile.rsfileio_win32 as rsfileio_win32
               
        try:
            import rsbackends.pywin32_extensions as win32
            rsfileio_win32.win3 = win32
            test_main()
            backends.append("pywin32_extensions")
        except ImportError:
            pass
        
        try:
            import rsbackends.pywin32_ctypes as win32
            rsfileio_win32.win3 = win32
            test_main()
            backends.append("pywin32_ctypes")
        except ImportError:
            pass
                  
    else:
        test_main() # only one backend in unix at the moment
        backends.append("unix")
    
    return backends