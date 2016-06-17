# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys, os, time, random, string, multiprocessing, threading
import rsfile
import io

VERBOSE_MODE = False


def logger(*args):
    if VERBOSE_MODE:
        print(" ".join(str(a) for a in args) + os.linesep, end="")


_streams_already_initialized = False


def _init_output_streams(multiprocessing_lock):
    """Sets a locking system (preferably, with a multiprocessing lock) 
    on standard output streams so that outputs don't get mixed 
    on the console together.
    """

    if multiprocessing_lock is None:
        return  # we must be on a *bsd without semopen implementation....

    global _streams_already_initialized
    if _streams_already_initialized:
        return

    class newstdout:
        @classmethod
        def write(cls, string):
            multiprocessing_lock.acquire()
            sys.__stdout__.write(string)
            sys.__stdout__.flush()
            multiprocessing_lock.release()

        @classmethod
        def flush(cls):
            pass

    sys.stdout = newstdout

    class newstderr:
        @classmethod
        def write(cls, string):
            multiprocessing_lock.acquire()
            sys.__stderr__.write(string)
            sys.__stderr__.flush()
            multiprocessing_lock.release()

        @classmethod
        def flush(cls):
            pass

    sys.stdout = newstderr

    _streams_already_initialized = True


def locking_inheritance_tester(rsfile_stream, multiprocessing_lock, offset=100):
    # we expect parent process to have locked the first "offset" bytes

    rsfile_stream.lock_file(length=100, offset=offset, timeout=0)
    rsfile_stream.unlock_file(length=100, offset=offset)

    try:
        rsfile_stream.lock_file(length=100, offset=0, timeout=0)
    except EnvironmentError:
        pass  # should raise something like "[Errno 11] Resource temporarily unavailable" on linux
    else:
        raise RuntimeError("Child abnormally able to lock beginning of rsfile_stream.")


def writer_without_file_locking(rsfile_stream, multiprocessing_lock, character, chunk_length):
    _init_output_streams(multiprocessing_lock)

    divisor = 1000
    assert chunk_length % divisor == 0  # let's make it simple

    logger("Process %s created with args " % (multiprocessing.current_process().name), locals())

    for i in range(10):

        logger("Process %s writing chunk of characters %s" % (multiprocessing.current_process().name, character))
        data_chunk = character * chunk_length
        rsfile_stream.write(data_chunk)  # ATOMIC on unix systems thanks to fork and interprocess lock

        time.sleep(0.1)

        with rsfile_stream.mutex:  # ATOMIC thanks to interprocess lock
            for i in range(chunk_length // divisor):
                rsfile_stream.write(character * divisor)


def chunk_writer_reader(targetFileName, multiprocessing_lock, character, ioOffset=0, payLoad=10000,
                        mustAlwaysSucceedLocking=False, lockingKwargs={}):
    _init_output_streams(multiprocessing_lock)

    logger("Process %s created with args " % (multiprocessing.current_process().name), locals())

    for i in range(random.randint(5, 15)):

        time.sleep(random.random() / 5)

        with io.open(targetFileName, "r+b", buffering=0) as targetFile:

            try:

                # doesn't work with partial functions - kwargs = dict(((key, value) for (key, value) in
                # lockingKwargs.items() if key in targetFile.lock_file.func_code.co_varnames[1:]))
                kwargs = lockingKwargs
                kwargs['shared'] = False

                logger("Process %s (%s) wanna lock file with args " % (
                    multiprocessing.current_process().name, threading.currentThread().name), kwargs)

                with targetFile.lock_file(**kwargs):

                    logger("Process %s (%s) has the lock ! " % (
                        multiprocessing.current_process().name, threading.currentThread().name))

                    if (random.randint(0, 1)):
                        targetFile.seek(ioOffset)
                        targetFile.write(character * payLoad)
                    else:
                        for k in reversed(range(payLoad)):
                            targetFile.seek(ioOffset + k)
                            targetFile.write(character)

                    time.sleep(random.random() / 5)

                    targetFile.seek(ioOffset)

                    logger("Process %s (%s) reads %s bytes at offset %s ***" % (
                        multiprocessing.current_process().name, threading.currentThread().name, payLoad,
                        targetFile.tell()))

                    data = targetFile.read(payLoad)

                    if (data != character * payLoad):
                        logger("PROBLEM IN %s: " % multiprocessing.current_process().name, data,
                               "            ><            ", character * payLoad)
                        sys.exit(8)

                logger("Process %s (%s) unlocks file" % (
                    multiprocessing.current_process().name, threading.currentThread().name))

            except rsfile.LockingException:
                if (mustAlwaysSucceedLocking):
                    raise
                else:
                    # logger"couldnt lock file, ok..."
                    pass
    import rsfile.rsfile_registries as RG

    logger("Process %s (%s) <<<<exiting>>>> - lock is %s" % (
        multiprocessing.current_process().name, threading.currentThread().name, RG.IntraProcessLockRegistry.mutex))
    sys.exit(0)


def chunk_reader(targetFileName, multiprocessing_lock, character=None, ioOffset=0, payLoad=10000,
                 mustAlwaysSucceedLocking=False, lockingKwargs={}):
    _init_output_streams(multiprocessing_lock)

    for i in range(random.randint(5, 15)):

        time.sleep(random.random() / 5)

        with io.open(targetFileName, "rb", buffering=0)  as targetFile:

            try:

                # doesn't work with new partial objects : kwargs = dict(((key, value) for (key, value) in
                # lockingKwargs.items() if key in targetFile.lock_file.func_code.co_varnames[1:]))
                kwargs = lockingKwargs
                kwargs['shared'] = True

                with targetFile.lock_file(**kwargs):

                    time.sleep(random.random() / 10)

                    targetFile.seek(ioOffset)

                    logger("Process (reader) %s (%s) reads %s bytes at offset %s ***" % (
                        multiprocessing.current_process().name, threading.currentThread().name, payLoad,
                        targetFile.tell()))

                    data = targetFile.read(payLoad)

                    if (character is not None):
                        if (len(data) and data != character * payLoad):
                            sys.exit(3)


            except rsfile.LockingException:
                if (mustAlwaysSucceedLocking):
                    raise
                else:
                    # logger"couldnt lock file, ok..."
                    pass


def lock_tester(resultQueue, targetFileName, multiprocessing_lock, multiprocess, ioOffset=0, whence=os.SEEK_SET,
                pause=0, lockingKwargs={}, res_by_exit_code=False):
    """Tries to lock the file with the given locking parameters, and returns whether it succeeded or not,
    and the time it took.
    """
    _init_output_streams(multiprocessing_lock)

    with io.open(targetFileName, "r+b", buffering=0)  as targetFile:

        targetFile.seek(ioOffset, whence)

        start = time.time()

        success = None

        try:
            with targetFile.lock_file(**lockingKwargs):
                success = True
                time.sleep(pause)
        except rsfile.LockingException:
            success = False

        if res_by_exit_code:
            sys.exit(1 if success else 2)  # quick result

        total = time.time() - start  # we let it in float format

        if multiprocess:
            myname = multiprocessing.current_process().name
        else:
            myname = threading.current_thread().name

        if resultQueue is not None:

            if isinstance(resultQueue, basestring):
                with io.open(resultQueue, "ab", 0) as f:
                    f.write(b"%s|%d|%f\n" % (myname.encode("ascii"), 1 if success else 0, total))
            else:
                resultQueue.put((myname, success, total))
                if hasattr(resultQueue, "close"):
                    resultQueue.close()  # multithreading queue.Queue has no close() method...

        sys.exit(0)


def fd_inheritance_tester(read, write, append, fileno=None, handle=None):
    assert not (fileno and handle)
    # logger>>sys.stderr, "Launching Worker Process inheritance_tester with fileno=%s and handle=%s !" % (fileno,
    # handle)
    # sys.exit(99)

    time.sleep(0.2)

    try:
        with rsfile.RSFileIO(read=read, write=write, append=append, fileno=fileno, handle=handle) as f:

            # logger>>sys.stderr, "Just opening and closing the file descriptor !!"
            # sys.exit(88)

            """
            logger(>>sys.stderr, "Filling the file from workerprocess !")
            f.write("sqsdsdqsdqklkjvlsdfqvudfbqudfhyqsudfbqudjkfhsdsdqb")
            f.flush()
            time.sleep(10)"""

            if not f.size() or not f.tell():
                raise IOError("Expected a non empty file with a moved file pointer, whereas size()=%d and tell()=%d" % (
                    f.size(), f.tell()))

            if read:
                f.seek(0)
                if not (f.read(1000)):
                    raise IOError("Impossible to read")
            else:
                try:
                    f.seek(0)
                    f.read(1000)
                except EnvironmentError:
                    pass
                else:
                    sys.exit(8)  # we shouldn't be able to read from this fd !

            if write or append:
                initial_size = f.size()
                f.seek(0)
                f.write(b"abcdef")
                if append and f.size() != (initial_size + 6):
                    raise IOError("Error when appending : current size %d != %d + 5" % (f.size(), initial_size))
            else:
                try:
                    f.seek(0)
                    f.write("abcdef")
                except EnvironmentError:
                    pass
                else:
                    sys.exit(9)  # we shouldn't be able to write to this fd !

    except EnvironmentError as e:
        # logger>>sys.stderr, e
        sys.exit(5)
    else:
        sys.exit(4)
