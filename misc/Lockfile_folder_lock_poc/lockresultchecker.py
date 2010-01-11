
import os, sys, glob


if(__name__=="__main__"):
    
    expectedValue=60
    expectedLineNumber=50
    
    resDir = "c:\\\\windows\\temp\\locking\\results"
    
    results= glob.glob(resDir+"\\*.txt")
    
    errors = []
    for res in results:
        
        f = open(res,"r")
        
        lineCount=0
        for line in f:
            lineCount+=1
            value = int(line.strip())
            if (value!=expectedValue) :
                txt = "--->BIG ERROR IN FILE "+res+" !"
                errors.append(txt)
                print txt
                break
        else:
            if(lineCount == expectedLineNumber):
                txt = "Ok for file "+res
                print txt
            else:
                txt = "--->BIG ERROR IN FILE "+res+" - bad line count : "+lineCount+" !"
                errors.append(txt)
                print txt
                
        f.close()
    
    if(errors):
        print "\nERRORS OCCURED : "
        print errors
    else:
        print "\nAll is fine !"