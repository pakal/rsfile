#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys, os
import functools


# must be FIRST - VERY IMPORTANT !
from .rsfile_definitions import * # constants, base types and exceptions


from .rsfileio_abstract import RSFileIOAbstract

from .rsfile_streams import *
from .rsfile_factories import *
from .rsfile_registries import set_rsfile_options, get_rsfile_options
from .rsfile_utilities import *




    
        
#contract.checkmod(module)  # UNCOMMENT THIS TO ACTIVATE PYCONTRACT CHECKING    

