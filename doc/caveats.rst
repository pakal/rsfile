
.. _interoperability_caveats:

Caveats regarding interoperability
==========================================


Due to the strange semantic of fcntl() calls, native handles can't be released
as long as locks exist on the target file. So if your process constantly opens
and closes the same files while keeping locks on them, you might eventually
run out of process resources.
To avoid this, simply plan lock-less moments for this flushing of pending handles,
or reuse the same file objects as much as possible.

Note that rsfile protections can't do anything if a third-party functions or C extensions
used by the process open the same file without using rsfile's interface  - in this case,
file locks might be silently lost...

Also, nothing is done to detect inter-process or intra-process
deadlocks - that's left to the programmer's responsibility.
