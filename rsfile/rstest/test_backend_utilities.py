# -*- coding: utf-8 -*-


import random
import unittest

from rsfile.rsbackend._utilities import *


class TestBackendUtilities(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_timestamps(self):
        """Test python and win32 timestamp conversions.

        Warning - floating point arithmetics make errors.
        We could use the decimal module...
        """

        num1 = random.randint(0, MAX_DWORD)
        num2 = random.randint(0, MAX_DWORD)

        res = win32_filetime_to_python_timestamp(num1, num2)
        (num3, num4) = python_timestamp_to_win32_filetime(res)
        self.assertTrue(abs(num1 - num3) <= 10000)  # low order numbers must be less than 1 ms far (1 unit = 100 ns)
        self.assertTrue(abs(num2 - num4) <= 1)  # high order numbers

        num1 = random.randint(0, MAX_DWORD)
        num2 = win32_filetime_to_python_timestamp(*python_timestamp_to_win32_filetime(num1))
        self.assertTrue(abs(num1 - num2) <= 1)

        self.assertEqual(python_timestamp_to_win32_filetime(0), pyint_to_double_dwords(116444736000000000))
        self.assertEqual(win32_filetime_to_python_timestamp(0, 0), -11644473600)

    def testNumberConversions(self):

        num1 = random.randint(0, 2 ** 64 - 1)
        num2 = double_dwords_to_pyint(*pyint_to_double_dwords(num1))
        self.assertEqual(num1, num2)

        num1 = random.randint(0, MAX_DWORD)
        num2 = random.randint(0, MAX_DWORD)
        num3, num4 = pyint_to_double_dwords(double_dwords_to_pyint(num1, num2))
        self.assertEqual(num1, num3)
        self.assertEqual(num2, num4)

    def testConversionErrors(self):
        self.assertRaises(ValueError, pyint_to_double_dwords, random.randint(-2 ** 64, -1))
        self.assertRaises(ValueError, pyint_to_double_dwords, random.randint(-2 ** 32, -1), 0)

    def testSignSwitches(self):
        num1 = random.randint(0, 2 ** 32 - 1)
        self.assertEqual(num1, signed_to_unsigned(unsigned_to_signed(num1)))

        num2 = random.randint(-2 ** 31, 2 ** 31 - 1)
        self.assertEqual(num2, unsigned_to_signed(signed_to_unsigned(num2)))

        self.assertEqual(-1, unsigned_to_signed(2 ** 32 - 1))

    def testErrnoConverter(self):
        self.assertEqual(winerror_to_errno(6), 9)
        self.assertEqual(winerror_to_errno(9999999), 22)

if __name__ == '__main__':
    print("Launching tests for low-level backend utilities")
    unittest.main()
