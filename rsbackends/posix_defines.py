#-*- coding: utf-8 -*-

from os import O_WRONLY, O_WRONLY, O_RDWR, O_SYNC, O_CREAT, O_EXCL

from fcntl import F_GETFD, F_SETFD, FD_CLOEXEC

F_FULLSYNC = 51