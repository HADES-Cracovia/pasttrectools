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


def command_w(cmd_to_file, trbid, reg, data):
    cmd = ['trbcmd', 'w', trbid, hex(reg), hex(data)]
    cmd_to_file.write(' '.join(cmd) + '\n')
    return True

def command_wm(cmd_to_file, trbid, reg, data, mode):
    cmd = ['trbcmd', 'wm', trbid, hex(reg), str(mode), '-']
    cmd_to_file.write(' '.join(cmd) + '\n')
    return True


def command_r(cmd_to_file, trbid, reg):
    cmd = ['trbcmd', 'r', trbid, hex(reg)]
    cmd_to_file.write(' '.join(cmd) + '\n')
    return True

def command_rm(cmd_to_file, trbid, reg, length):
    cmd = ['trbcmd', 'rm', trbid, hex(reg), str(length), '0']
    cmd_to_file.write(' '.join(cmd) + '\n')
    return True
