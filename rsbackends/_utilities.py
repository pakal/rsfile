# -*- coding: utf-8 -*-


from __future__ import with_statement


import random
import unittest




MAX_DWORD = 2**32-1

def signed_to_unsigned(value, wordsize=32):
        if(value < 0):
                value = value + 2**(wordsize)
        return value

def unsigned_to_signed(value, wordsize=32):
        if(value >= 2**(wordsize-1)):
                value = value - 2**(wordsize)
        return value	


def pyint_to_double_dwords(long, dwordsize=32):
        "Convert a positive long integer into a (low-order dword, high-order dword) 2's complement tuple."

        if(long<0):
                raise ValueError("Positive argument required")

        uloworder = long & (2**dwordsize-1)
        uhighorder = (long >> dwordsize) & (2**dwordsize-1)
 
        return (uloworder, uhighorder)

def double_dwords_to_pyint(loworder, highorder , dwordsize=32): # the arguments can be negative or positive integers !
        "Convert a low-order dword, high-order dword) tuple into an unsigned long integer."

        return  (highorder << dwordsize) + loworder



def win32_filetime_to_python_timestamp(loworder, highorder):
    
    win32_timestamp = double_dwords_to_pyint(loworder, highorder)
    """
    FILETIME is a 64-bit unsigned integer representing
    the number of 100-nanosecond intervals since January 1, 1601
    UNIX timestamp is number of seconds since January 1, 1970
    116444736000000000 = 10000000 * 60 * 60 * 24 * 365 * 369 + 89 leap days
    """
    return float(win32_timestamp - 116444736000000000) / 10000000 



def python_timestamp_to_win32_filetime(pytimestamp):
                                                 
    win32_timestamp = int((10000000 * pytimestamp) + 116444736000000000)
    
    (loworder, highorder) = pyint_to_double_dwords(win32_timestamp)
    
    return (loworder, highorder)






class TestUtilities(unittest.TestCase):

        def setUp(self):
                pass
                def tearDown(self):
                        pass
        
        def test_timestamps(self):
                """Test python and win32 timestamp conversions.
                
                Warning - floating point arithmetics makes errors.
                We could use the decimal module...
                """
            
                num1 = random.randint(0, MAX_DWORD)
                num2 = random.randint(0, MAX_DWORD)
                
                res = win32_filetime_to_python_timestamp(num1, num2)
                (num3, num4) = python_timestamp_to_win32_filetime(res)
                self.assertTrue(abs(num1 - num3) <= 10000) # low order numbers must be less than 1 ms far (1 unit = 100 ns)
                self.assertTrue(abs(num2 - num4) <= 1) # high order numbers       

                num1 = random.randint(0, MAX_DWORD)
                num2 = win32_filetime_to_python_timestamp(*python_timestamp_to_win32_filetime(num1))
                self.assertTrue(abs(num1 - num2) <= 1)           

                self.assertEqual(python_timestamp_to_win32_filetime(0), pyint_to_double_dwords(116444736000000000))
                self.assertEqual(win32_filetime_to_python_timestamp(0,0), -11644473600)

        def testConversion1(self):
                num1 = random.randint(0, 2**64-1)
                num2 = double_dwords_to_pyint(*pyint_to_double_dwords(num1))
                self.assertEqual(num1, num2)

        def testConversion2(self):
                num1=random.randint(0, MAX_DWORD)
                num2=random.randint(0, MAX_DWORD)
                num3,num4 = pyint_to_double_dwords(double_dwords_to_pyint(num1,num2))
                self.assertEqual(num1, num3)
                self.assertEqual(num2, num4)

        def testError1(self):
                self.assertRaises(ValueError, pyint_to_double_dwords, random.randint(-2**64,-1))

        def testError2(self):
                self.assertRaises(ValueError, pyint_to_double_dwords, random.randint(-2**32,-1), 0)

        def testSignSwitches(self):
                num1 = random.randint(0, 2**32-1)
                self.assertEqual(num1, signed_to_unsigned(unsigned_to_signed(num1)))

                num2 = random.randint(-2**31, 2**31-1)
                self.assertEqual(num2, unsigned_to_signed(signed_to_unsigned(num2)))

                self.assertEqual(-1, unsigned_to_signed(2**32-1))



if __name__ == '__main__':
        unittest.main()

