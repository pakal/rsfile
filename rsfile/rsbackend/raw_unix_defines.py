# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from os import O_WRONLY, O_RDONLY, O_RDWR, O_SYNC, O_CREAT, O_EXCL, O_APPEND

from fcntl import F_GETFD, F_SETFD, FD_CLOEXEC
from fcntl import LOCK_EX, LOCK_SH, LOCK_UN, LOCK_NB

F_FULLFSYNC = 51
