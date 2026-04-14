# Plan: Keep test_original_io Working on Python 3.13 and 3.14

## Design Principle

**Always import tests live from CPython's installed test suite** — `from test import test_io, ...`.
The `src/rsfile/rstest/stdlib/` snapshot files remain reference backups only, never imported.

The goal is to inject rsfile's IO primitives into CPython's own test classes so those tests
validate rsfile instead of `_io`/`_pyio`.

---

## What Actually Changed in 3.13 / 3.14

All six test module imports still work unchanged on Python 3.13 and 3.14:

```python
from test import test_io, test_memoryio, test_file, test_bufio, test_fileio, test_largefile
```

The structural changes that do matter:

| Change | Python version | Impact on rsfile |
|--------|---------------|-----------------|
| `load_tests()` sets `is_C = True/False` on every test class | 3.13 | Safe: C* classes are already `dummyklass`; Py* correctly get `is_C = False` |
| `MockCharPseudoDevFileIO` injected into Py* namespaces | 3.13 | Safe: enables `test_tell_character_device_file` / `test_seek_character_device_file` on `PyBufferedReaderTest`, which test `_pyio.BufferedReader` internals, not rsfile's FileIO |
| `ProtocolsTest` added to `load_tests()` test list | 3.14 | Tests `io.Reader`/`io.Writer` structural ABCs — no rsfile-specific code, let it run |
| `CAutoFileTests` / `PyAutoFileTests` explicit split | ≥ 3.9 (stable) | Addressed below — see Bug 1 |

---

## Bug 1 — FileIO Is Never Injected into test_fileio (all versions)

**File:** `src/rsfile/rstest/test_rsfile_stdlib.py` line 131

```python
# Current — no-op: _FileIO is not an attribute referenced by any test class
test_fileio._FileIO = rsfile.io_module.FileIO
```

`test_fileio` has two concrete test classes (present since Python 3.9):

```python
class CAutoFileTests(AutoFileTests, unittest.TestCase):
    FileIO = _io.FileIO      # ← C extension

class PyAutoFileTests(AutoFileTests, unittest.TestCase):
    FileIO = _pyio.FileIO    # ← pure-Python; THIS is what needs replacing
```

Tests call `self.FileIO(TESTFN, 'w')` — so `test_fileio._FileIO = ...` never has any effect.
rsfile's `FileIO` is never exercised by this sub-suite.

Same problem for `OtherFileTests`:

```python
class COtherFileTests(OtherFileTests, unittest.TestCase):
    FileIO = _io.FileIO

class PyOtherFileTests(OtherFileTests, unittest.TestCase):
    FileIO = _pyio.FileIO    # ← also needs replacing
```

---

## Bug 2 — Python 2.7 Dead Code

Lines 141–148 of `test_rsfile_stdlib.py`:

```python
# bugfix of testErrnoOnClosedWrite() test in python2.7
deco = test_fileio.AutoFileTests.__dict__["ClosedFDRaises"]
@deco
def bugfixed(self, f):
    f.write(b"a")  # in py27 trunk, "binary" modifier was lacking...
test_fileio.AutoFileTests.testErrnoOnClosedWrite = bugfixed
```

Minimum supported Python is 3.7. Remove entirely.

---

## Implementation

### Change A — Fix try/except import block (lines 37–50)

No structural change to the imports. Keep the try/except as a safety net for minimal
Python installations (Debian/Ubuntu packages often omit the `test` package). Only improve
the error message to name the failing module:

```python
try:
    from test import (
        test_io,
        test_memoryio,
        test_file,
        test_bufio,
        test_fileio,
        test_largefile,
    )
except ImportError as e:
    print(f"Warning: Could not import stdlib test module — {e} "
          f"(Python {sys.version_info.major}.{sys.version_info.minor})")
    print("Install the Python test package (e.g. python3-lib2to3 or libpython3-dev) "
          "to enable stdlib IO tests.")
    print("Skipping stdlib IO tests.")
    return
```

### Change B — Fix test_fileio injection (lines 131–148)

Replace the entire broken block with:

```python
# Skip C-backed concrete test classes (they test _io.FileIO directly).
test_fileio.CAutoFileTests = dummyklass
test_fileio.COtherFileTests = dummyklass

# Inject rsfile's FileIO into the Python-backed concrete test classes.
test_fileio.PyAutoFileTests.FileIO = rsfile.io_module.FileIO
test_fileio.PyOtherFileTests.FileIO = rsfile.io_module.FileIO

# These patches apply to the AutoFileTests / OtherFileTests mixins so that
# PyAutoFileTests / PyOtherFileTests inherit the skips.
# (CAutoFileTests/COtherFileTests are already dummied out above.)
test_fileio.AutoFileTests.testMethods = dummyfunc      # C-specific method signatures
test_fileio.AutoFileTests.testErrors  = dummyfunc      # errno differs between C and Py
test_fileio.AutoFileTests.testBlksize = dummyfunc      # rsfile has no _blksize
test_fileio.AutoFileTests.testRepr    = dummyfunc      # repr() differs
test_fileio.AutoFileTests.testReprNoCloseFD = dummyfunc
test_fileio.OtherFileTests.testInvalidFd = dummyfunc   # exception types differ
```

The Python 2.7 `ClosedFDRaises` workaround (lines 141–148) is removed here.

### Change C — No new patches needed for 3.13 / 3.14

- **`is_C` attribute**: C* classes are already `dummyklass`; Py* classes correctly receive
  `is_C = False` from `load_tests()`. The `self.is_C` branches in `TextIOWrapperTest`
  (lines 2756, 3831, 3840, 3851, 3855 of test_io.py) take the right (Py) path.
  No additional patches required.

- **`MockCharPseudoDevFileIO`**: Injected into `PyBufferedReaderTest` etc. as
  `PyMockCharPseudoDevFileIO`. The two new tests (`test_tell_character_device_file`,
  `test_seek_character_device_file`) test `_pyio.BufferedReader` with a mock raw IO —
  not rsfile's FileIO. They should pass without patches.

- **`ProtocolsTest` (3.14)**: Tests `io.Reader`/`io.Writer` structural ABCs against
  plain Python classes. No rsfile-specific behaviour. Let it run; dummy it out only if
  it fails:
  ```python
  # Uncomment if ProtocolsTest fails on 3.14:
  # if sys.version_info >= (3, 14):
  #     if hasattr(test_io, 'ProtocolsTest'):
  #         test_io.ProtocolsTest = dummyklass
  ```

---

## Summary of Lines Touched in test_rsfile_stdlib.py

| Lines | Change |
|-------|--------|
| 47–49 | Improve ImportError message |
| 131   | Remove `test_fileio._FileIO = rsfile.io_module.FileIO` |
| 132–139 | Replace method patches on mixin with explicit class patches (Change B) |
| 141–148 | Remove Python 2.7 `ClosedFDRaises` dead code |

Net effect: ~10 lines removed, ~8 lines added.

---

## Verification

```bash
# Smoke-test each Python version directly
py -3.11 -m rsfile.rstest.test_rsfile_stdlib
py -3.12 -m rsfile.rstest.test_rsfile_stdlib
py -3.13 -m rsfile.rstest.test_rsfile_stdlib
py -3.14 -m rsfile.rstest.test_rsfile_stdlib

# Full tox run
tox run -e py311,py312,py313,py314
```

What to check:
- `PyAutoFileTests` tests now **run and use rsfile's FileIO** (they will show failures
  if rsfile's FileIO is missing a method, rather than silently passing with `_pyio.FileIO`)
- `CAutoFileTests` produces **zero test results** (it is `dummyklass`)
- No `AttributeError` on `PyAutoFileTests.FileIO` or `PyOtherFileTests.FileIO`
- Py* tests in test_io with `self.is_C` checks pass (they take the `is_C = False` branch)
