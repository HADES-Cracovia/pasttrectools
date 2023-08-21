#!/usr/bin/env python3
#
# Copyright 2018 Rafal Lalik <rafal.lalik@uj.edu.pl>
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


import subprocess

from pasttrec import g_verbose


def print_verbose(rc):
    """ Print verbose return info from trbnet communication """

    if rc is None:
        return

    if g_verbose >= 1:
        print("[{:s}]  {:d}".format(hex(rc[0]), rc[1]))


def command_w(trbid, reg, data):
    cmd = ['trbcmd', 'w', trbid, hex(reg), hex(data)]
    """
    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True
    """
    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def command_wm(trbid, reg, data, mode):
    """
    if cmd_to_file is not None:
        cmd = ['trbcmd', 'wm', trbid, hex(reg), str(mode), '- << EOF']
        cmd_to_file.write(' '.join(cmd) + '\n')
        for d in data:
            cmd_to_file.write(hex(d) + '\n')
        cmd_to_file.write('EOF\n')
        return True
    """
    cmd = ['trbcmd', 'wm', trbid, hex(reg), str(mode), '-']
    _data = "\n".join([hex(x) for x in data])
    rc = subprocess.run(cmd, input=_data.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def command_r(trbid, reg):
    cmd = ['trbcmd', 'r', trbid, hex(reg)]
    """
    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True
    """
    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def command_rm(trbid, reg, length):
    cmd = ['trbcmd', 'rm', trbid, hex(reg), str(length), '0']
    """
    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True
    """
    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


"""
def parse_rm_scalers(res):
    s = Scalers()
    a = None   # address
    c = 0   # channel
    for line in lines:
        parts = line.split()
        n = len(parts)

        if n == 3:
            a = hex(int(parts[1], 16))
            s.add_trb(a)
            sm = 1

        if n == 2:
            if a is not None:
                c = int(parts[0], 16) - def_scalers_reg
                if c > def_pastrec_channels_all:
                    continue
                val = int(parts[1], 16)
                if val >= 0x80000000:
                    val -= 0x80000000
                s.scalers[a][c] = val
            else:
                continue

    return s


def parse_r_scalers(res):
    r = {}
    lines = res.splitlines()
    for line in lines:
        parts = line.split()
        n = len(parts)

        if n == 2:
            a = int(parts[0], 16)
            n = int(parts[1], 16)
            if n >= 0x80000000:
                n -= 0x80000000
            r[hex(a)] = n

    return r
"""
