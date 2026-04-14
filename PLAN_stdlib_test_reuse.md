# Plan: Reusing CPython's Old Test Files to Test rsfile on Python 3.13+

## Background

`test_original_io()` in `src/rsfile/rstest/test_rsfile_stdlib.py` validates rsfile by
monkey-patching `io`/`_io`/`_pyio` and then running CPython's own IO test suite against them.
It currently imports test modules **live at runtime** from the installed Python's `test` package:

```python
from test import test_io, test_memoryio, test_file, test_bufio, test_fileio, test_largefile
```

The `src/rsfile/rstest/stdlib/` directory already holds version-pinned snapshots of
CPython's `test_io.py` (`test_io_py311.py`, `test_io_py312.py`) and every `_pyio` module
back to Python 2.7 — but **none of these backup files are ever imported**. They are dead
assets.

This plan activates that snapshot strategy for `test_io.py` and fixes two compounding bugs
that mean rsfile's `FileIO` has never actually been exercised by the `test_fileio` sub-suite.

---

## What Changed in CPython's Test Suite at Python 3.13

After cloning / fetching the CPython repo and diffing `Lib/test/test_io.py` across tags:

| Version | Key change in `load_tests()` |
|---------|------------------------------|
| ≤ 3.12  | Mocks: 8 standard mocks. Does **not** set `is_C` on test classes. `io.__all__ + ["IncrementalNewlineDecoder"]` |
| 3.13    | Adds `MockCharPseudoDevFileIO` to injected mocks. **Sets `is_C = True/False`** on every test class. Some test methods branch on `self.is_C`. |
| 3.14    | Adds `ProtocolsTest` (tests new `io.Reader`/`io.Writer` structural ABCs) to the suite. |

The `test_fileio.py` module gained explicit `CAutoFileTests` / `PyAutoFileTests` concrete
classes in Python 3.10 (inheriting from the `AutoFileTests` mixin) and has been structurally
stable since.

---

## Bug 1 — Broken FileIO Injection (all Python versions)

**Location:** `src/rsfile/rstest/test_rsfile_stdlib.py` line 131

```python
# CURRENT — broken, has no effect
test_fileio._FileIO = rsfile.io_module.FileIO
```

`_FileIO` is not referenced by any test class across Python 3.9–3.14.  
The concrete classes `CAutoFileTests` and `PyAutoFileTests` each carry a **class-level**
`FileIO = _io.FileIO` / `FileIO = _pyio.FileIO` attribute; `self.FileIO(...)` is what
instantiates the file object under test.

**Result:** rsfile's `FileIO` is never substituted. The `PyAutoFileTests` suite silently
runs against `_pyio.FileIO` (CPython's pure-Python implementation) instead of rsfile's.

---

## Bug 2 — C Concrete Classes Not Dummied Out in test_fileio

**Location:** same file, same block

The code dummies out `CIOTest`, `CBufferedReaderTest`, etc. from `test_io`, but it never
dummies `CAutoFileTests` or `COtherFileTests` from `test_fileio`. Those classes still run
against `_io.FileIO` (the real C extension), which passes — falsely giving confidence.

---

## Implementation Plan

### Step 1 — Fetch the Missing CPython Snapshot

Fetch `Lib/test/test_io.py` from the CPython repository at the `v3.13.0` tag and save it
into the existing stdlib backup directory:

```bash
# from the project root
python -c "
import urllib.request, pathlib
url = 'https://raw.githubusercontent.com/python/cpython/v3.13.0/Lib/test/test_io.py'
dest = pathlib.Path('src/rsfile/rstest/stdlib/test_io_py313.py')
urllib.request.urlretrieve(url, dest)
print('saved', dest)
"
```

Optionally repeat for 3.14 once a stable tag exists (`v3.14.0`).

> `_pyio_py313_backup.py` already exists — no new `_pyio` backup needed.

---

### Step 2 — Replace the Live Import with Version-Dispatched Snapshot Imports

**File:** `src/rsfile/rstest/test_rsfile_stdlib.py`, lines 37–50

```python
# BEFORE
try:
    from test import (
        test_io,
        test_memoryio,
        ...
    )
except ImportError as e:
    ...
    return

# AFTER
try:
    # Use version-pinned snapshots of test_io for reproducibility.
    # The snapshot matches the test suite of the Python version being tested,
    # so patches stay stable even as the installed Python evolves.
    if sys.version_info >= (3, 14):
        from rsfile.rstest.stdlib import test_io_py314 as test_io  # once available
    elif sys.version_info >= (3, 13):
        from rsfile.rstest.stdlib import test_io_py313 as test_io
    elif sys.version_info >= (3, 12):
        from rsfile.rstest.stdlib import test_io_py312 as test_io
    elif sys.version_info >= (3, 11):
        from rsfile.rstest.stdlib import test_io_py311 as test_io
    else:
        from test import test_io

    # The remaining modules are structurally stable; import live.
    from test import (
        test_memoryio,
        test_file,
        test_bufio,
        test_fileio,
        test_largefile,
    )
except ImportError as e:
    print(f"Warning: Could not import stdlib test modules "
          f"(Python {sys.version_info.major}.{sys.version_info.minor}): {e}")
    print("Skipping stdlib IO tests.")
    return
```

---

### Step 3 — Fix the test_fileio Patching Block

**File:** `src/rsfile/rstest/test_rsfile_stdlib.py`, lines 131–148

Remove the broken block entirely and replace with:

```python
# --- test_fileio: correct substitution ---

# Dummy out C-backed concrete classes (use _io.FileIO, not rsfile).
test_fileio.CAutoFileTests = dummyklass
test_fileio.COtherFileTests = dummyklass

# Inject rsfile's FileIO into the Python-backed concrete test class.
test_fileio.PyAutoFileTests.FileIO = rsfile.io_module.FileIO

# Skip methods that don't apply to rsfile (applied to the mixin so
# PyAutoFileTests inherits the skip; CAutoFileTests is already dummied).
test_fileio.AutoFileTests.testMethods = dummyfunc      # C-specific method signatures
test_fileio.AutoFileTests.testErrors  = dummyfunc      # errno differs between C/Py
test_fileio.AutoFileTests.testBlksize = dummyfunc      # rsfile has no _blksize
test_fileio.AutoFileTests.testRepr    = dummyfunc      # repr() differs
test_fileio.AutoFileTests.testReprNoCloseFD = dummyfunc

# testInvalidFd lives on OtherFileTests; different exception types between C and Py
test_fileio.OtherFileTests.testInvalidFd = dummyfunc
```

The Python 2.7-era `ClosedFDRaises` decorator workaround (lines 141–148 of the current
file) is dead code and is removed along with this block.

---

### Step 4 — Add Python 3.13+ Patches for test_io

After the existing patch block, add a version guard:

```python
if sys.version_info >= (3, 13):
    # load_tests() now sets is_C=True on C* classes and is_C=False on Py* classes.
    # All C* classes are already replaced with dummyklass so this is safe.
    # MockCharPseudoDevFileIO is injected into Py* test namespaces.
    # Guard against any new method that may fail with rsfile:
    if hasattr(test_io.PyIOTest, 'test_char_pseudo_dev'):
        test_io.PyIOTest.test_char_pseudo_dev = dummyfunc

if sys.version_info >= (3, 14):
    # ProtocolsTest checks io.Reader / io.Writer structural ABCs (new in 3.14).
    # These verify stdlib protocol correctness, not rsfile-specific behaviour.
    # Leave enabled; dummy out only if they fail:
    # test_io.ProtocolsTest = dummyklass  # uncomment if needed
    pass
```

---

## Files Changed / Created

| File | Action |
|------|--------|
| `src/rsfile/rstest/stdlib/test_io_py313.py` | **Create** — CPython v3.13.0 snapshot |
| `src/rsfile/rstest/stdlib/test_io_py314.py` | **Create** — CPython 3.14 snapshot (once stable) |
| `src/rsfile/rstest/test_rsfile_stdlib.py`   | **Modify** — Steps 2, 3, 4 above |

---

## Why Snapshot Files Instead of Always Using Live Imports

| Concern | Live import (`from test import test_io`) | Snapshot (`test_io_py313.py`) |
|---------|------------------------------------------|-------------------------------|
| Reproducibility | Test changes invisibly when Python is upgraded | Fixed to a known CPython commit |
| C/Py divergence gating | We patch `CXxx = dummyklass` after import; any import-time side-effects from the C path still run | Full control; can patch before module-level code runs |
| Forward compatibility | A future CPython version could remove the module or rename classes | We choose when to add a new snapshot |
| Version mismatch | Running py3.13 always uses py3.13's test_io (correct) | Same, because dispatch is on `sys.version_info` |

---

## Verification Sequence

```bash
# Direct per-version smoke test
py -3.11 -m rsfile.rstest.test_rsfile_stdlib
py -3.12 -m rsfile.rstest.test_rsfile_stdlib
py -3.13 -m rsfile.rstest.test_rsfile_stdlib
py -3.14 -m rsfile.rstest.test_rsfile_stdlib

# Full tox run
tox run -e py311,py312,py313,py314
```

**Key things to verify:**

- `PyAutoFileTests` tests actually execute and report results (previously they ran against
  `_pyio.FileIO`, not rsfile — check that failures now surface)
- `CAutoFileTests` produces zero test results (it is a `dummyklass`)
- No `AttributeError` on any of the new patch targets (`test_fileio.PyAutoFileTests.FileIO`,
  `test_fileio.CAutoFileTests`, etc.)
- `is_C`-gated code paths in `PyTextIOWrapperTest` take the `is_C = False` branch
  (correct for rsfile's pure-Python implementation)
