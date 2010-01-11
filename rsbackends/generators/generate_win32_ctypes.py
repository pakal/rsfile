
#!/usr/bin/env python
import sys


"""
In case we also need to regenerate the xml file :
>h2xml.py windows.c -k -I "D:\!!Projets en cours\pyrstools\backends\trunk\generators" -o win32_defines.xml -c
>xml2py.py windows.c.xml -w -k d -k t -o outfile.py
"""




# we build our own command line
# Model : xml2py.py windows.xml -w -o output3.py -s "CreateFileW" -s "CloseHandle" -r ".*File.*"...

sys.argv = [sys.argv[0]] # reset
sys.argv.append("windows.c.xml")
sys.argv.append("-w") # adding default win32 DLLs
sys.argv += ["-o", "../raw_win32_ctypes.py"] # output


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
for symbol in symbol_list:
    sys.argv += ["-s", symbol]


expr_list = []
for expr in expr_list:
    sys.argv += ["-r", expr]

print "-> Command line used : ", sys.argv

from ctypeslib.xml2py import main

res = main()

if not res:
    print "Job finished successfuly"
else:
    print "Job failed"
sys.exit(res)

