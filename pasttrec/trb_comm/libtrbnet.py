#!/usr/bin/env python3
#
# Copyright 2023 Rafal Lalik <rafal.lalik@uj.edu.pl>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

""" These functions are trbnetlibrary functions. """

from pasttrec import g_verbose


def print_verbose(rc):
    """ Print verbose return info from trbnet communication """

    if rc is None:
        return

    if g_verbose >= 1:
        print("[{:s}]  {:d}".format(hex(rc[0]), rc[1]))


def command_w(trbnet, trbid, reg, data):
    rc = trbnet.trb_register_write(trbid, reg, data)
    print_verbose(rc)
    return 0


def command_wm(trbnet, trbid, reg, data, option=1):
    rc = trbnet.trb_register_write_mem(trbid, reg, option, data)
    print_verbose(rc)
    return 0


def command_r(trbnet, trbid, reg):
    rc = trbnet.trb_register_read(trbid, reg)
    print_verbose(rc)
    return rc[1]


def command_rm(trbnet, trbid, reg, length, option=1):
    """
    Read memory block.
    Function return of map where the key is the trb address and value is tuple of memory block
    """
    rc = trbnet.trb_register_read_mem(trbid, reg, option, length)
    print_verbose(rc)
    i = 0
    res = {}
    while i < len(rc):
        data = rc[i]
        partial_len = (data & 0xffff0000) >> 16
        res[data & 0xffff] = tuple(rc[i+1:i+1+partial_len])
        i = i + 1 + partial_len
    return res
