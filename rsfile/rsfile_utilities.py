
from rsfile_factories import rsOpen


    
# TODO - TEST THESE UTILITY METHODS !!!!
    
def write_to_file(filename, data, sync=False, must_exist=False, must_not_exist=False, **open_kwargs):    

    assert "mode" not in open_kwargs # mode is automatically determined by this function

    mode = "WE" # we erase the file
    if sync: 
        mode += "S"
    if must_exist:
        mode += "+"
    if must_not_exist:
        mode += "-"
    if not isinstance(data, unicode):
        mode += "B"
    
    with rsOpen(filename, mode=mode, **open_kwargs) as myfile:
        myfile.write(data)
        myfile.flush()
        if sync:
            myfile.sync()
   
    
def append_to_file(filename, data, sync=False, must_exist=False, **open_kwargs):

    assert "mode" not in open_kwargs # mode is automatically determiend by this function

    mode = "WA"
    if sync: 
        mode += "S"
    if must_exist:
        mode += "+"
    if not isinstance(data, unicode):
        mode += "B"
    
    with rsOpen(filename, mode=mode, **open_kwargs) as myfile:
        myfile.write(data)
        myfile.flush()
        if sync:
            myfile.sync()
    
   
def read_from_file(filename, binary=False, **open_kwargs): 
    assert "mode" not in open_kwargs # mode is automatically determined by this function
    # TODO - To be added - "limit" argument, to retrieve only part of a file ????????
    
    mode = "R+"
    if binary: 
        mode += "B"
    
    with rsOpen(filename, mode=mode, **open_kwargs) as myfile:

        data_blocks = []
        while True:
            temp = myfile.read()
            if not temp:
                break
            data_blocks.append(temp)
            
        if binary: joiner = ""
        else: joiner = u""   
            
        return joiner.join(data_blocks)
    
    
    