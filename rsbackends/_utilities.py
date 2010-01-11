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

"""
 decimal — Decimal fixed point and floating point arithmetic¶

New in version 2.4.

The decimal module provides support for decimal floating point arithmetic. It offers several advantages over the float datatype:
    *
      Decimal “is based on a floating-point model which was designed with people in mind, and necessarily has a paramount guiding principle – computers must provide an arithmetic that works in the same way as the arithmetic that people learn at school.” – excerpt from the decimal arithmetic specification.
    *
      Decimal numbers can be represented exactly. In contrast, numbers like 1.1 do not have an exact representation in binary floating point. End users typically would not expect 1.1 to display as 1.1000000000000001 as it does with binary floating point.
    *
      The exactness carries over into arithmetic. In decimal floating point, 0.1 + 0.1 + 0.1 - 0.3 is exactly equal to zero. In binary floating point, the result is 5.5511151231257827e-017. While near to zero, the differences prevent reliable equality testing and differences can accumulate. For this reason, decimal is preferred in accounting applications which have strict equality invariants.
    *
      The decimal module incorporates a notion of significant places so that 1.30 + 1.20 is 2.50. The trailing zero is kept to indicate significance. This is the customary presentation for monetary applications. For multiplication, the “schoolbook” approach uses all the figures in the multiplicands. For instance, 1.3 * 1.2 gives 1.56 while 1.30 * 1.20 gives 1.5600.
    *
      Unlike hardware based binary floating point, the decimal module has a user alterable precision (defaulting to 28 places) which can be as large as needed for a given problem:

"""
def python_timestamp_to_win32_filetime(pytimestamp):
    
    win32_timestamp = int((10000000 * pytimestamp) + 116444736000000000)
    
    (loworder, highorder) = pyint_to_double_dwords(win32_timestamp)
    
    return (loworder, highorder)


"""
>>> int((10000000 * float(98527427572 - 116444736000000000) / 10000000) + 116444736000000000)
98527427568L
>>> 10000000 * float(98527427572 - 116444736000000000) / 10000000
-1.1644463747257243e+17
>>> 98527427572 - 116444736000000000
-116444637472572428L
>>> from __future__ import division

>>> 10000000 * float(98527427572 - 116444736000000000) / 10000000
-1.1644463747257243e+17
>>> 8527427572 - 116444736000000000
-116444727472572428L
>>> 10000000 * int(98527427572 - 116444736000000000) / 10000000
-1.1644463747257242e+17
>>> 98527427572 - 116444736000000000
-116444637472572428L
>>> 

"""

class TestUtilities(unittest.TestCase):

        def setUp(self):
                pass
                def tearDown(self):
                        pass
        
        def test_timestamps(self):
                num1 = random.randint(0, MAX_DWORD)
                num2 = random.randint(0, MAX_DWORD)
                
                res = win32_filetime_to_python_timestamp(num1, num2)
                print locals()
                (num3, num4) = python_timestamp_to_win32_filetime(res)
                self.assertEqual((num1, num2), (num3, num4))        

                num1 = random.randint(0, MAX_DWORD)
                num2 = win32_filetime_to_python_timestamp(*python_timestamp_to_win32_filetime(num1))
                self.assertEqual(num1, num2)           


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

