
#!/usr/bin/env python
import sys


"""
In case we also need to regenerate the xml file :
>h2xml.py windows.c -k -I "D:\!!Projets en cours\pyrstools\backends\trunk\generators" -o win32_defines.xml -c
>xml2py.py windows.c.xml -w -k d -k t -o outfile.py
"""






symbol_list = """
SECURITY_ATTRIBUTES
OVERLAPPED
BY_HANDLE_FILE_INFORMATION
GetLastError 
CreateFileA
CreateFileW
_open_osfhandle
_get_osfhandle  
CloseHandle
SetEndOfFile
GetFileInformationByHandle
GetFileSize
GetFileSizeEx
SetFilePointer
SetFilePointerEx
ReadFile
ReadFileEx
WriteFile
WriteFileEx
FlushFileBuffers
LockFileEx
UnlockFileEx
""".split()



expr_list = []









print "Generating CTYPES wrappers"
# Model : xml2ctypes.py windows.xml -w -o output3.py -s "CreateFileW" -s "CloseHandle" -r ".*File.*"...


sys.argv = [sys.argv[0]] # reset
sys.argv.append("windows.c.xml")
sys.argv.append("-w") # adding default win32 DLLs
sys.argv += ["-o", "../raw_win32_ctypes.py"] # output

for symbol in symbol_list:
    sys.argv += ["-s", symbol]

for expr in expr_list:
    sys.argv += ["-r", expr]

print "-> CTypesGenerator Command line used : ", sys.argv

from xml2ctypes import main
res = main()

if not res:
    print "Job OK"
else:
    print "Job failed"

    
    
    
print "---------"




print "Generating CYTHON wrappers"

#Model : xml2cython.py -s CreateFileA -s CreateFileW -o outputfile windows.h windows.c.xml    
    
sys.argv = [sys.argv[0]] # reset
 
for symbol in symbol_list:
    sys.argv += ["-s", symbol]
    
sys.argv += ["-o", "../raw_win32_cython.c"] # output
sys.argv.append("windows.h")
sys.argv.append("windows.c.xml")

print "-> CythonGenerator Command line used : ", sys.argv


from xml2cython import main
res = main()

if not res:
    print "Job OK"
else:
    print "Job failed"

sys.exit()

