    def lock_chunk(self, shared=False, timeout=None, length=None, offset=0, whence=os.SEEK_SET):
        """Locks the whole file or a portion of it, depending on the arguments provided.
        
        If shared is True, the lock is a "reader", non-exclusive lock, which can be shared by several 
        processes, but prevents "writer" locks from being taken on the locked portion. 
        Else, the lock is a "writer" lock which is fully exclusive, preventing both writer 
        and reader locks from being taken by other processes on the locked portion.
        
        If timeout is None, the process will block on this operation until it manages to get the lock; 
        else, it must be a number indicating how many seconds
        the operation will wait before raising a timeout????? exception 
        (thus, timeout=0 means a non-blocking locking attempt).
        
        Offset and/or length can be used to specify a portion of file to lock. 
        They must both be None or positive integers. If length is 0 or None, this means all the rest of the file will be locked, from the specified offset. Whence is the same as in seek(), and specifies where the offset is calculated from (beginning, current position, or end of file).
        
        The strength of the locking depends on the underlying platform. On windows, all file locks are mandatory, i.e even programs which are not using 
        file locks won't be able to access locked parts of files for reading or writing (depending on the type of lock used).
        On posix platforms, most of the time locking is only advisory, i.e unless they use the same type of lock as rsFile's ones (currently, fcntl calls), programs will be able to freely access your files if they have proper permissions. Note that it is possible to enforce mandatory locking thanks to some
        mount options and file flags (see XXX???urls)
        
        Note that file locking is not reentrant: calling this function several times, on overlapping areas, will raise a Rntime Error; but you can still get different locks at the same time, for different parts of the same file (beware of deadlocks however, in case several process try to get them in different orders).
        ??? TELL EXCEPTIONS HER        

        # TO BE ADDED : MORE ASSERTIONS PYCONTRACT !!! 
        pre:
            offset is None or isistance(offset, int)
            length is None or (isistance(length, int) and length >= 0)
        post:
            isinstance(__return__, bool)

        WARNING : WIN32 - Locking a portion of a file for shared access denies all processes write access to the specified region of the file, including the process that first locks the region. All processes can read the locked region.-> do not enforce that on unix !!!!!! advisory only !!!
        
        """



rsFile aims at providing python with a cross-platform, reliable, and comprehensive file I/O API (that is, file stream manpulation, not filesystem operations like shutil does). Stdlib file stream APIs suffer indeed from their history and their C/unix origins : they are scattered all over lots of modules (os, stat, fnctl???, tempfile...), poorly object-oriented, full of platform-specific behaviours, and worst of all they sometimes rely on castrated implementations, like windows' libc compatibility layer.
That's why rsFile offers more than a simple interfacing/adaptation layer : it also wraps native file objects (like win32 "Handles"), to ensure a maximal flexibility ro the API.
The main idea behind the design of the API, is that "cross-platform" doesn't mean "lowest denominator", and that "high level" doesn't mean "poor". That's why, even though rsFile can transparently replace the current python builtin file object, it also provides lots of additional methods and parameters to finely tweak the streams you need : file chunk locking, timeout handling, disk synchronization, atomic file creation, handle inheritance, thread safety...

Locking Recursivity :
The thread-level lock included in the rsFile is always recursive, i.e as threading.RLock, it allows the same thread to acquire it several times ; as long as this lock is released the same number of time as it's acquired, all will be fine.
But the process-level lock cannot be recursive on all platforms.
FALSE
 That's why, by default, the process holding it (whathever particular thread issued the acquisition call) will raise a RuntimeError if it tries to lock some bytes several times without releasing it inbetween. Also, 
However, it is possible to disabled this "cross-platform uniformity" by setting to "False" the registry option XXXX.
Advantages
- you gain performance by removing the overhead of this checking on posix platforms (windows ones tooo??? what happens exactly if we double lock???)
- you can benefit from posix's advanced locking features ( merging or separation of locked chunks 
This might be interesting in two particular cases
- your application will only run in posix system, and you 
/FALSE

TODO : check behaviour of double lock in win32 and posix - do not allow deadlocks !! 
just test if 2° thread can unlok the file locked by another one !

If the principle of "composed streams" affords a great flexibility, it comes at the cost of losing the notion of "public method". Indeed, depending on the chainning of different IOBase instances, they will be directly accessible, or instead wrapped in other objects. This is particularly embarrassing concerning thread-safety : in prevision of the moment when it might be used as"top-level" object, each stream type currently implements its own mutex system, which is both error-prone (in the IO implementation, some methods like xxx.truncate are not thread-safe ??????), and performance-hindering (there might easily be until 3 levels of redundant locking, eg. in common textIOWrapper streams).
To solve the problem, rsFile uses some kind of "thread-safe interface" pattern : each class inheriting IOBase shall implement its logic in a thread-unsafe way, and it's up to each factory functions (like io.open()) to wrap the top-level object of the IO chain inside a "thread-safe adapter", a transparent wrapper which simply ensures that only one thread at a time may access the methods and properties of the stream ????


Disk file : this is the set of physical disk blocks on which your file (both metadata and data) is eventually stored. This is also the only place where data can really be considered as persistent. Data is saved into the disk file way less often than we might think - on laptops particularly, disks can be left inactive for dozens of minutes in order to preserve energy.

Open file object : this kernel-level object represents an open stream to a file. As such, it contains references to the target disk file, as well as transient state information relative to the open stream (current file pointer, miscellaneous caching and locking information...)

Open file handle (C file descriptor on posix systems, file handle on win32 platforms) : this type  mostly acts as a "pointer" to an open file object. It is typically an integer used as an index in a per-process (posix) or global (win32) open file table. Several open file references can target the same open file objects, via inheritance (case of a fork()) or dedicated duplication functions (dup() on posix, DuplicateHandle() on win32). On some platforms, open file references have specific attributes (like permissions, locks, inheritability options...), but the rest of their "state" is the one of the open file they represent (eg. duplicated ile descriptors share the same file pointer)  

Since, depending on the platform, crucial safety information may be owned by open file references or by open file objects, the only way to unify the behaviour of high level streams seems to prevent file reference duplication inside each process, and to consider "open file reference -> open file object" couples as inseperable entities. Since on the contrary, lots of different python objects can keep references, and write to, such high level streams (in particular, it's trvivialy to replace standard streams in sys module), this shouldn't be too cruel a constraint. However, experienced developers may still retrieve native open file references, and play with lowel level IO routines as they wish - we're all consentent adults, remember ?


fileno()
handle()
These methods give access to low level types underlying the rsFile streams. 
fileno() returns a C/Posix compatible file descriptor (actually, an integer action as index in the process file descriptor table - where 0, 1 and 2 are standard streams).
handle() returns a more platform-specific file handle, if any (on win32, a handle integer or a thin wrapper around it).
Note that if the requested object doesn't exist on the execution platform, an IOError ???? is raised.


PB avec fctl si on ferme differents descripteurs ????


Inheritance of file objects between parent and child processes isn't a simplistic subject, especially if you want to play with different stream types (FILE*, ostream, ...) and process creation methods (spawn(), fork(), CreateProcess) on different platforms.
In the case of rsFile however, in which native file handles are used on each platform, a somehow unified behaviour can be obtained. By default, rsFile streams are NOT inheritable, but they can be made so at opening time. 
Then, to achieve inheritance, two operations must be done.
-Creating a new process thanks to a "certified" call.
On unix, the fork+exec behaviour properly takes file descriptor inheritance into account. Notte that after fork, file descriptors are ALWAYS inherited, since the forking process 

Note : it's a little off-topic, but I "profiter"??? of the occasion to recall that fork() and multithreading HATE each other. Basically, only the thread issuing ythe fork will be duplicated to the new process, and many data structures might be left

the semantic of stream inheritability can be tamed if we only use corresponding process creation methods.
By default, 

On posix platforms, where subprocess creation -> what happens when execing ??? can a fd be closed when forking ???
Due to the number of file types


Buffering and caching
The data we read from or write to a file actually goes through many more levels of buffering than we might think.

Application-level caching : This is the caching we find in C libraries (inside FILE* objects, cf setvbuf()), python file objects (via the "buffering" parameters) and more generally any IO library written in a given language. It usually consists of read-ahead buffering (to improve performance, allow character encoding operations, and allow line ending detection) and write buffering (to diminish the number of write system calls - this buffer can be manually emptied with a flush() operation). A seek() on a stream typically resets this buffering.

Kernel-level caching and buffering : contrary to popular belief, if you open a file, issue read/write operations on it, and close it (with an implicit flush), this doesn't implicate that your modifications have been saved to disk. Most likely, they've just been reflected by a cache located in the kernel, and will be written to oxyde later, with other changes, by a lazy writer (pdfflush on linux, ....????). Since that kernel caching is fully transparent to applications (no desynchronization occurs between what different processes see in files), it usually doesn't matter. But in case of crash, data which hasn't eventually been written to oxyde will be lost - which can be extremly embarrassing for sensitive files management, database applications etc.
That's why operfating system offer ways of flushing that kernel cache, to ensure that data gets properly pushed to the device before starting other operations. Such a flush can be manual (posix??? sync() call, win32 FlushFileBuffers...) or enforced for each write on a given open file (O_SYNC/FILE_WRITE_THROUGH opening flags). Note that variants of that kernel cache flush exist (dsync, rsinc, ...semantics), to also enforce flushes on read operations, but rsFile concentrates on the most critical requirement  - having your data become persistent when you ask it.



Note on Disk internal cache
Although all operating system provide ways of flushing the kernel cache to the device, this is not always sufficient. Indeed, for performance reasons, most hard disk have an internal "disk cache" enabled by default, which doesn't necessarily get flushed by sync calls. Needless to say that your data is not much more likely to survive to a crash, if it's in the disk cache instead of the kernel one (although sophisticated disks are sometimes backed by batteries to deal with this case, and let the device automatically purge itself before falling out of energy).
So here is an overview of the "disk cache" affair:
- Disks and operating system easily lie about their real synchronization state. That's why, if you have very important data to protect,your best chance is to disable all disk caching features, through hardware configuration  utilities, (hdparm -W 0, windows hardware condiguration panels etc.). But such tweaks can heavily hinder performance, and they heavily depend on your hardware - IDE and SCSI disks, for example, can have very different options and, and more or less "deceiving" behaviours. If your data is stored on remore shares (samba, nfs...) then chances are big that your sync calls won't make it to the oxyde, and only a careful study of involved hardware/OS/applications may give you some certainties in this case (a good old "unplug the cable violently" test might also help - see the perl utility **** for that).
Windows : The win32 FlushFileBuffer call theoretically implicates both kernel cache and disk cache flushing, as well on local as on remote ntfs filesystem????? TO CHECK
*nix-like systems: as well in posix norms as in the Single Unix Specification, nothing ensures???assurer? that fsync() calls will care about disk cache. But more specifically:
	- Mac OS X users : lucky you, Apple has introduced a new fcntl flag (F_FULLSYNC) to enforce full synchronization.
	- Linux users: it seems that the very latest kernel versions (3.6.???? and above) have been patched to ensure full sync. The question is : when will that patch make it to your favorite distribution ?
	- Other *nix-like platforms : Your mileage may vary... read the sweet manuals, as we say.


win32:
LockFile:
This is a mandatory, per-handle, non reentrant lock, allowing byte range locking.
More precisely
	-once a file area is locked through a handle, no other handle, in this process or another one, can access this area in a way incompatible to the lock type (shared or exclusive). Forbidden read/write operations will fail immediately, incompatible locking attempts through other handles/processes will block, and trying to lock the bytes already locked through the same handle will block too ???
	There is no merging/cutting of locked ranges. Unlocking calls must provide as arguments a byte range identical to one of those previously locked.
Locks are removed automatically by the system (but possibly after some delay) when the handle is closed or the process is shut down.

Unix:
-fcntl locks, 
This is an advisory, per-process, rentrant lock, allowing byte range locking
	- Write or read operations which take no account of file locking will not be hindered by these locks, unless mandatory locking has been activated on this particular file (SEE DOCS°
	- Inside a process, it makes no difference whether a file/range has been locked via a specific handle or open file object : the lock belongs to the whole process ; 
	- Byte range locking is very flexible : consecutive areas can be freed in a single unlock() call, it is possible to release only part of a byte range, and locking the same bytes several times simply updates their locking mode (exclusive or shared) on demand. 
Note that you needn't unlock a byte range as many  times as it was locked - only the last lock operation is "active"
Note - Changing the locking method of a byte range is not atomic - bytes are releases and then locked again, which makes that another process might take ownership in the meantime.
rename lock_chunk -lock_range !!!!
	- Locks are NEVER shared with child processes, even those born from a simple fork() without exec(). 
	- fcntl locks are (theoretically) supported by recent enough (>4.???) NFS servers
-flock locks:
These are advisory, per-open-file, non reentrant?? locks, dealing only with the whole file. 
	-All handles pointing to the open file table entry on which the flock() call was issued, "own" this lock. It means that different handles in the same process, 

The "flock" affair.
At first, a very interesting alternative to fcntl:
	- locking per-file-table-entry instead of per-process, allowing more isolation inside a process
	-no loss of locks in case of file desciptor closing
But
	-no NFS support
	-no byte range locking
	-dulicated/inherited file descriptors share their locks with original  ones
	-on several platforms, flock locks are actually emulated by fcntl(), and thus don't respect their theoretical semantic
Conclusion : not worth the hassle


Warning - the danger with this system, is that your process could run out of available file handles, if it continuely opens and locks the same file(s) without ever letting the possibility to release them - i.e by constantly keeping at least some bytes locked.
Blatantly, if your application behaves that way, it creates some kind of denial-of-service against any other process which would want to lock the whole file, so it could be the sign that other means of protection (file permissions, immediate deletion of the filesystem entry...) would be more appropriate for your needs than record locking. 
But if you reaallly need to constantly lock parts of the file (eg. for a shared database file), then you shall
- reuse the same file descriptors whenever possible
- plan "zero lock" moments to allow the garbage collection of an inode's zombie file descriptors
- let the closing operation of a file descriptor atomically release the locks still kept, instead of manually unlocking them just before closing the file. This helps garbage collection, by ensuring that no new lock is taken in the short time between the unlocking operation and the closing of the descriptor itself.


rsfile.umask
Sets the permission mask used when creating a new inode, and returns the previous mask. On unix platforms, the umask is inherited from the parent process, and features all the flags describe in the stat module ; on windows it is zero on startup, and only the "user write" flag is taken into account, to switch between read-only and normal file.

TODO:
HOW TO disable the effects of the umask on *nix???
DEAL WITH THE STICKY BIT !!! 
Or make win32 like unix, by offering folder permissions and changing file deletion with readonly files!!!!!

rsfile.close_handle
Closes the native handle, and performs any cleaning operation required by the rsfile system (currently : nothing).
The handle might not be closed immediately.

rsfile.close_fileno
Closes the C file descriptor according to the mechanisms of the rsfile system. Currently, it prevents the loss of fcntl locks on unix platfotms, by placing the file descriptor in the garbage collection system (note that this file descriptor might not be closed immediately, thus)

HOW TO KNOW THE COUNT OF OPEN FILES FOR CURRENT PROCESS ??

Warning : the sharing of open file table entries by several handles (via handle duplication, inheritance or unix message passing) is a dangerous sport, since in this case they all share the same file pointer, which opens the doors to memorable race conditions (EVEN WHEN LOCKING??). As long as these handles are in the same process, basic mutexes can suffice to sort it out, but in the interprocess case, it is necessary to agree on a shared lock, which is slightly harder

===> enforce no reentrancy even in win32 ! ! else deadlocks may occur !!! Raise rruntime error when locking twice !!

DONNER POSSIBILITE DE RECREER FILE OBJECT A PARTIR D'UN MUTEX ou SEMAPHORE AUSSI !!! IPC 
-> done

VERIFIER : est-ce que les handles sont systemwide ou processwide

DO NOT raise errors when auto unlocking file on close

y A T IL DIFFERENT ENTRE FLOCK5° ET PUIS O_SCLOCK de BSD ????


There is a catastrophic flaw in fcntl lock specifications : when any file descriptor to a disk file is closed, all the locks owned by the process on that file is lost. Beware : we said "any" file descriptor, not the file descriptor which was used to obtain locks, or one of the file descriptors pointing to the same open file table entry. So if, while you're peacefully playing with your locks around some important file (sey, /etc/passwd), one of the numerous libraries used of your project


It's still unclear why Posix people specified it that way. Rumors affirm that they actually let a monkey write the fcntl part, and later on they un***(inadvertance) let the fruits of this funny experiment go with final specs ; others affirm that one of the workgroups was unfortunately close from an oenologia session. Anyway, we have to live with this fact : the only unix locks able to work over NFS and to lock byte ranges, are also the only locks in the world able to discreetly run away as soon as they''re disturbed by third-party libraries. Impressive, isn't it?






