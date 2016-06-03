#-*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

"""
BEWARE - in this test, we DO NOT monkey patch the stdlib, so that we can compare the original io and rsfile.
"""


import rsfile.rsfile_definitions as defs


import sys
import os
import unittest
from pprint import pprint

import tempfile
import time
import itertools
import random

from test import test_support

import io
import rsfile
from rsfile.rstest import _utilities


TESTFN = "@TESTING" # we used our own one, since the test_support version is broken


HAS_X_OPEN_FLAG = (sys.version_info >= (3, 3))


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

def complete_and_normalize_possible_modes(file_modes):
    """
    We add all possible file_modes, except for advanced flags "I" and "S".
    """

    file_modes = file_modes.copy()

    # we add redundant (useless) but accepted forms: "W" when "A", and "E", when "C"
    for k, v in file_modes.items():
        if "A" in k:
            assert "W" not in k, k  # initial data must be DRY
            file_modes[k + "W"] = v
    for k, v in file_modes.items():
        if "C" in k:  # EVEN if file not writable, eg. "RCE" is weird but possible
            assert "E" not in k, k  # initial data must be DRY
            file_modes[k + "E"] = v

    suffixes = {
        "": "",
        "B": "b",
        "T": "t"
    }
    # we add binary/text suffixes
    file_modes = dict((mode1 + suf1, (mode2 + suf2 if mode2 else mode2))
                      for (mode1, mode2) in file_modes.items()
                      for (suf1, suf2) in suffixes.items())

    file_modes = {"".join(sorted(k)): v
                  for (k, v) in file_modes.items()}

    return file_modes



class TestStreamsRetrocompatibility(unittest.TestCase):

    @staticmethod
    def determine_stream_capabilities(opener, mode):
        """
        Utility that reverse-engineers the REAL behaviour of a stream during and after its creation.
        """

        if "b" in mode.lower():
            payload = b"ABCDEF"
            extra_data = b"XXX"
        else:
            payload = "ABCDEF"
            extra_data = "XXX"

        (fd, name) = tempfile.mkstemp()
        os.write(fd, payload)
        os.close(fd)
        assert os.path.getsize(name) == 6

        truncate = False  # always remains false if exclusive creation is used
        try:
            stream = opener(name, mode)  # open EXISTING file
            stream.close()
            truncate = (os.path.getsize(name) == 0)
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
        os.write(fd, payload)
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

        params = dict(read=read,
                      write=write,
                      append=append,
                      must_create=must_create,
                      must_not_create=must_not_create,
                      truncate=truncate)
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
                for subset in itertools.permutations(values, L):
                    yield subset

        adv_flags = list("RAWCNEBT")  # remove deprecated and isolated flags
        for idx, subset in enumerate(gen_all_combinations(adv_flags)):

            selected_adv_flags = "".join(subset)  # the sames flags will come in various orders

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
                        %s""" % (selected_stdlib_flags, selected_adv_flags, stdlib_res, adv_res)
                self.assertEqual(stdlib_res, adv_res, msg)

                chosen_flags = random.choice((selected_stdlib_flags, selected_adv_flags))

            else:

                chosen_flags = selected_adv_flags


            # we compare theoretical abilities with what the stream can ACTUALLY do
            theoretical_abilities = dict(
                read = adv_res[0]["read"],
                write = adv_res[0]["write"],
                append = adv_res[0]["append"],
                must_create = adv_res[0]["must_create"],
                must_not_create = adv_res[0]["must_not_create"],
                truncate = adv_res[1]["truncate"]
            )

            real_abilities = self.determine_stream_capabilities(rsfile.rsopen, chosen_flags)

            msg = """
                THEORETICAL : %s
                REAL:         %s""" % (theoretical_abilities, real_abilities)
            self.assertEqual(theoretical_abilities, real_abilities, msg)


            if selected_stdlib_flags:

                legacy_abilities = self.determine_stream_capabilities(io.open, selected_stdlib_flags)

                msg = """
                    THEORETICAL : %s
                    LEGACY:       %s""" % (theoretical_abilities, legacy_abilities)
                self.assertEqual(theoretical_abilities, legacy_abilities, msg)


        assert idx > 1000, idx  # we've well browsed lots of combinations



def display_open_modes_correlations_table():

    file_modes_correlation = FILE_MODES_CORRELATION

    stdlib_modes = sorted(m for m in file_modes_correlation.values() if m)

    correlations = []

    for stdlib_mode in stdlib_modes:

        print("Analysing stdlib mode %r" % stdlib_mode)

        advanced_modes = [k for (k, v) in file_modes_correlation.items() if v == stdlib_mode]
        advanced_mode = min(advanced_modes, key=len)

        abilities = TestStreamsRetrocompatibility.determine_stream_capabilities(io.open, stdlib_mode)

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
    print("** RSFILE_STREAMS Test Suite has been run on backends %s **" % backends)


if __name__ == '__main__':
    """
    from tabulate import tabulate
    data = display_open_modes_correlations_table()
    print (tabulate(data, headers="keys"))
    """
    #pprint(data)
    test_main()

