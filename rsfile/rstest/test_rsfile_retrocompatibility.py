# -*- coding: utf-8 -*-


"""
BEWARE - in this test, we DO NOT monkey patch the stdlib, so that we can compare the original io and rsfile.
"""

import rsfile.rsfile_definitions as defs

from rsfile.rstest import _utilities

_utilities.patch_test_supports()

import os
import unittest

import tempfile
import itertools
import random

import io
import rsfile

from test import test_support  # NOW ONLY we can import it

TESTFN = "@TESTING"  # we used our own one, since the test_support version is broken

HAS_X_OPEN_FLAG = defs.HAS_X_OPEN_FLAG

# this maps advanced modes to standard open() modes
# we don't list here redundant flags, or binary/text/inheritable/synchronised stuffs
FILE_MODES_CORRELATION = {
    "R": None,
    "RN": "r",
    "RC": None,  # makes little sense, but possible
    "W": None,
    "WE": "w",
    "WN": None,
    "WEN": None,
    "WC": "x" if HAS_X_OPEN_FLAG else None,
    "A": "a",
    "AE": None,
    "AC": None,
    "AN": None,
    "ANE": None,
    "RW": None,
    "RWE": "w+",
    "RA": "a+",
    "RAE": None,
    "RAC": None,
    "RAN": None,
    "RANE": None,
    "RWC": "x+" if HAS_X_OPEN_FLAG else None,
    "RWN": "r+",
    "RWNE": None,
}


def _disown_file_descriptor(stream):
    stream = getattr(stream, "wrapped_stream", stream)
    stream = getattr(stream, "_buffer", stream)
    stream = getattr(stream, "raw", stream)
    assert stream._closefd in (True, False)
    stream._closefd = False


def reopener_via_fileno(name, mode):
    """Ensures that possible emulation of fileno doesn't break the access mode of the stream."""
    f = rsfile.rsopen(name, mode=mode, locking=False, thread_safe=False)
    _disown_file_descriptor(f)
    fileno = f.fileno()
    assert fileno, fileno
    new_f = rsfile.rsopen(mode=mode, fileno=fileno, closefd=True)
    assert new_f.handle() == f.handle()
    assert new_f.fileno() == fileno
    return new_f


def __BROKEN__reopener_via_handle(name, mode):
    """Ensures that possible emulation of handle doesn't break the access mode of the stream."""
    f = rsfile.rsopen(name, mode=mode, locking=False, thread_safe=False)
    _disown_file_descriptor(f)
    handle = f.handle()
    assert handle, handle
    new_f = rsfile.rsopen(mode=mode, handle=handle, closefd=True)
    assert new_f.handle() == handle
    if defs.RSFILE_IMPLEMENTATION == "windows":
        assert f._fileno is None, f._fileno  # we take care of NOT exhausting these emulated resources here
    else:
        assert new_f.fileno() == f.fileno()
    return new_f


def complete_and_normalize_possible_modes(file_modes):
    """
    We add all possible file_modes, except for advanced flags "I" and "S".
    """

    file_modes = file_modes.copy()

    # we add redundant (useless) but accepted forms: "W" when "A", and "E", when "C"
    for k, v in list(file_modes.items()):
        if "A" in k:
            assert "W" not in k, k  # initial data must be DRY
            file_modes[k + "W"] = v
    for k, v in list(file_modes.items()):
        if "C" in k:  # EVEN if file not writable, eg. "RCE" is weird but possible
            assert "E" not in k, k  # initial data must be DRY
            file_modes[k + "E"] = v

    suffixes = {"": "", "B": "b", "T": "t"}
    # we add binary/text suffixes
    file_modes = dict(
        (mode1 + suf1, (mode2 + suf2 if mode2 else mode2))
        for (mode1, mode2) in list(file_modes.items())
        for (suf1, suf2) in list(suffixes.items())
    )

    file_modes = {"".join(sorted(k)): v for (k, v) in list(file_modes.items())}

    return file_modes


class TestStreamsRetrocompatibility(unittest.TestCase):
    @staticmethod
    def determine_stream_capabilities(opener, mode):
        """
        Utility that reverse-engineers the REAL behaviour of a stream during and after its creation.
        """

        os_payload = b"ABCDEF"

        if "b" in mode.lower():
            text = False
            payload = b"ABCDEF"
            extra_data = b"XXX"
        else:
            text = True
            payload = "ABCDEF"
            extra_data = "XXX"

        (fd, name) = tempfile.mkstemp(text=text)
        os.write(fd, os_payload)
        os.close(fd)
        assert os.path.getsize(name) == 6

        truncate = False  # always remains false if exclusive creation is used
        try:
            stream = opener(name, mode)  # open EXISTING file
            stream.close()
            truncate = os.path.getsize(name) == 0
            must_create = False
        except EnvironmentError:
            must_create = True
            must_not_create = False
        else:
            os.unlink(name)
            try:
                stream = opener(name, mode)  # open UNEXISTING file
                stream.close()
                must_not_create = False
            except EnvironmentError:
                must_not_create = True
        assert not (must_create and must_not_create), (must_create, must_not_create)

        (fd, name) = tempfile.mkstemp()
        os.write(fd, os_payload)
        os.close(fd)
        assert os.path.getsize(name) == 6
        if must_create:
            os.unlink(name)

        with opener(name, mode) as stream:  # MUST succeed

            try:
                if must_create or truncate:
                    stream.write(payload)
                    stream.flush()
                    stream.seek(0)  # to check "append" behaviour

                stream.write(extra_data)
                stream.flush()
                write = True

                new_size = os.path.getsize(name)
                if new_size == 9:
                    append = True
                else:
                    assert new_size == 6, new_size
                    append = False
            except EnvironmentError:
                write = False
                append = False

            try:
                stream.read(1)
                read = True
            except EnvironmentError:
                read = False

        assert read or write

        params = dict(
            read=read,
            write=write,
            append=append,
            must_create=must_create,
            must_not_create=must_not_create,
            truncate=truncate,
        )
        return params

    def testModeEquivalences(self):

        std_parser = rsfile.parse_standard_args
        adv_parser = rsfile.parse_advanced_args

        file_modes = complete_and_normalize_possible_modes(FILE_MODES_CORRELATION)

        stdlib_file_modes = set(file_modes.values()) - set([None])
        # pprint(stdlib_file_modes)

        # Combinations: 4 access modes, "+" or not, and ""/"b"/"t"
        assert len(stdlib_file_modes) == (4 if HAS_X_OPEN_FLAG else 3) * 2 * 3, len(stdlib_file_modes)

        def gen_all_combinations(values):
            for L in range(0, len(values) + 1):
                for subset in itertools.combinations(values, L):
                    yield subset

        adv_flags = list("RAWCNEBT")  # remove deprecated and isolated flags
        for idx, subset in enumerate(gen_all_combinations(adv_flags)):

            selected_adv_flags = "".join(subset)  # the sames flags will come in various orders

            # print("-> Testing mode equivalences for", selected_adv_flags)

            _selected_adv_flags_normalized = "".join(sorted(selected_adv_flags))
            is_abnormal_mode = _selected_adv_flags_normalized not in file_modes
            selected_stdlib_flags = file_modes.get(_selected_adv_flags_normalized, None)
            del _selected_adv_flags_normalized

            if False:  # USEFUL LOGGING when debugging open modes
                print("==--> %r, %r" % (selected_adv_flags, selected_stdlib_flags))

            if is_abnormal_mode:
                assert selected_stdlib_flags is None
                self.assertRaises(ValueError, rsfile.rsopen, TESTFN, selected_adv_flags)  # NOT an OSError
                continue

            try:
                with rsfile.rsopen(TESTFN, selected_adv_flags):
                    pass
            except EnvironmentError:  # it's certainly due to file existence constraints
                if selected_stdlib_flags:
                    # ALSO fails
                    self.assertRaises(EnvironmentError, rsfile.rsopen, TESTFN, selected_stdlib_flags)
            else:
                if selected_stdlib_flags:
                    # ALSO succeeds
                    with rsfile.rsopen(TESTFN, selected_stdlib_flags):
                        pass

            adv_res = adv_parser(TESTFN, selected_adv_flags, None, None, True)

            if selected_stdlib_flags:

                # we compare abilities on a THEORETICAL level between stdlib and advanced mode
                stdlib_res = std_parser(TESTFN, selected_stdlib_flags, None, None, True)

                msg = """
                        %s != %s :
                        %s
                        %s""" % (
                    selected_stdlib_flags,
                    selected_adv_flags,
                    stdlib_res,
                    adv_res,
                )
                self.assertEqual(stdlib_res, adv_res, msg)

                chosen_flags = random.choice((selected_stdlib_flags, selected_adv_flags))

            else:

                chosen_flags = selected_adv_flags

            # we compare theoretical abilities with what the stream can ACTUALLY do
            theoretical_abilities = dict(
                read=adv_res[0]["read"],
                write=adv_res[0]["write"],
                append=adv_res[0]["append"],
                must_create=adv_res[0]["must_create"],
                must_not_create=adv_res[0]["must_not_create"],
                truncate=adv_res[1]["truncate"],
            )

            real_abilities = self.determine_stream_capabilities(rsfile.rsopen, chosen_flags)

            msg = """
                THEORETICAL: %s
                REAL:         %s""" % (
                theoretical_abilities,
                real_abilities,
            )
            self.assertEqual(theoretical_abilities, real_abilities, msg)

            if selected_stdlib_flags:
                legacy_abilities = self.determine_stream_capabilities(io.open, selected_stdlib_flags)

                msg = """
                    THEORETICAL: %s
                    LEGACY:      %s""" % (
                    theoretical_abilities,
                    legacy_abilities,
                )
                self.assertEqual(theoretical_abilities, legacy_abilities, msg)

            abilities_via_fileno = self.determine_stream_capabilities(reopener_via_fileno, chosen_flags)
            msg = """
                THEORETICAL:         %s
                REOPENED_VIA_FILENO: %s""" % (
                theoretical_abilities,
                abilities_via_fileno,
            )
            self.assertEqual(theoretical_abilities, abilities_via_fileno, msg)

            '''
            # no need to test "handle" passing because handles are below-or-equal filenos in our current
            implementations,
            # plus it leads to "too many open files" on windows because filenos can't be released without closing the
            handle too (and blcksize forces fileno creation..)
            abilities_via_handle = self.determine_stream_capabilities(reopener_via_handle, chosen_flags)
            msg = """
                THEORETICAL :        %s
                REOPENED_VIA_HANDLE: %s""" % (theoretical_abilities, abilities_via_handle)
            self.assertEqual(theoretical_abilities, abilities_via_handle, msg)
            '''

        assert idx > 200, idx  # we've well browsed lots of combinations

    def testMiscStreamBehavioursRetrocompatibility(self):

        filename = "TESTFILE"

        for opener in (rsfile.rsopen, io.open):

            # BEWARE: wrapped stream must NOT be truncated despite the "w" mode

            # print("Trying with", opener)
            fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            self.assertEqual(os.fstat(fd).st_size, 0)
            os.write(fd, b"abcd")
            self.assertEqual(os.fstat(fd).st_size, 4)

            with opener(fd, "w", closefd=True) as f:
                if hasattr(f, "size"):
                    self.assertEqual(f.size(), 4)
                self.assertEqual(os.fstat(fd).st_size, 4)


def display_open_modes_correlations_table():
    file_modes_correlation = FILE_MODES_CORRELATION

    _ref_stdlib_modes = set(m for m in list(file_modes_correlation.values()) if m)
    sorted_stdlib_modes = ["r", "r+", "w", "w+", "a", "a+"] + (["x", "x+"] if HAS_X_OPEN_FLAG else [])
    assert set(sorted_stdlib_modes) == _ref_stdlib_modes  # sanity check

    correlations = []

    for stdlib_mode in sorted_stdlib_modes:
        # print("Analysing stdlib mode %r" % stdlib_mode)

        advanced_modes = [k for (k, v) in list(file_modes_correlation.items()) if v == stdlib_mode]
        advanced_mode = min(advanced_modes, key=len)

        abilities = TestStreamsRetrocompatibility.determine_stream_capabilities(io.open, stdlib_mode)

        abilities = {k: ("true" if v else " ") for (k, v) in list(abilities.items())}

        abilities["std_mode"] = stdlib_mode
        abilities["adv_mode"] = advanced_mode

        correlations.append(abilities)

    return correlations


def test_main():
    def _launch_test_on_single_backend():
        # Historically, these tests have been sloppy about removing TESTFN.
        # So get rid of it no matter what.
        try:
            test_support.run_unittest(TestStreamsRetrocompatibility)
        finally:
            if os.path.exists(TESTFN):
                try:
                    os.unlink(TESTFN)
                except OSError:
                    pass

    backends = _utilities.launch_rsfile_tests_on_backends(_launch_test_on_single_backend)
    print("** RSFILE_RETROCOMPATIBILITY Test Suite has been run on backends %s **\n" % backends)


if __name__ == "__main__":

    test_main()

    try:
        from tabulate import tabulate  # requires "pip install tabulate"

        data = display_open_modes_correlations_table()
        # pprint(data)
        ordering = "std_mode adv_mode read write append must_create must_not_create truncate".split()
        data = [[d[i] for i in ordering] for d in data]
        print(tabulate(data, headers=ordering, tablefmt="rst", numalign="left", stralign="left"))

        all_advanced_modes = sorted(FILE_MODES_CORRELATION.keys())
        print("\nAuthorized advanced open modes:\n%s" % all_advanced_modes)
    except ImportError:
        print("Python-tabulate not installed, skipping display of file modes tables")
