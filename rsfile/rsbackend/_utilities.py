# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function


MAX_DWORD = 2 ** 32 - 1


def signed_to_unsigned(value, wordsize=32):
    if (value < 0):
        value = value + 2 ** (wordsize)
    return value


def unsigned_to_signed(value, wordsize=32):
    if (value >= 2 ** (wordsize - 1)):
        value = value - 2 ** (wordsize)
    return value


def pyint_to_double_dwords(mylong, dwordsize=32):
    "Convert a positive long integer into a (low-order dword, high-order dword) 2's complement tuple."

    if (mylong < 0):
        raise ValueError("Positive argument required")

    uloworder = mylong & (2 ** dwordsize - 1)
    uhighorder = (mylong >> dwordsize) & (2 ** dwordsize - 1)

    return (uloworder, uhighorder)


def double_dwords_to_pyint(loworder, highorder, dwordsize=32):  # the arguments can be negative or positive integers !
    "Convert a low-order dword, high-order dword) tuple into an unsigned long integer."

    return (highorder << dwordsize) + loworder


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


# Taken from python's errmap.h, generated by generrmap.c thanks to msvcrt's undocumented function "_dosmaperr()"




_error_mapping = {
    2: 2,
    3: 2,
    4: 24,
    5: 13,
    6: 9,
    7: 12,
    8: 12,
    9: 12,
    10: 7,
    11: 8,
    15: 2,
    16: 13,
    17: 18,
    18: 2,
    19: 13,
    20: 13,
    21: 13,
    22: 13,
    23: 13,
    24: 13,
    25: 13,
    26: 13,
    27: 13,
    28: 13,
    29: 13,
    30: 13,
    31: 13,
    32: 13,
    33: 13,
    34: 13,
    35: 13,
    36: 13,
    53: 2,
    65: 13,
    67: 2,
    80: 17,
    82: 13,
    83: 13,
    89: 11,
    108: 13,
    109: 32,
    112: 28,
    114: 9,
    128: 10,
    129: 10,
    130: 9,
    132: 13,
    145: 41,
    158: 13,
    161: 2,
    164: 11,
    167: 13,
    183: 17,
    188: 8,
    189: 8,
    190: 8,
    191: 8,
    192: 8,
    193: 8,
    194: 8,
    195: 8,
    196: 8,
    197: 8,
    198: 8,
    199: 8,
    200: 8,
    201: 8,
    202: 8,
    206: 2,
    215: 11,
    1816: 12
}


def winerror_to_errno(winerror):
    """
    Maps most common win32 error codes to C errno equivalents (by default, returns EINVAL).
    """
    return _error_mapping.get(winerror, 22)  # default : EINVAL


