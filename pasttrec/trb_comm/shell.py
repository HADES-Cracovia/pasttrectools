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

#import os
#import sys
#import glob
#import argparse
#import subprocess
#from time import sleep
#import json
#import math
#import time
#from colorama import Fore, Style

#from pasttrec import *

#if isinstance(trbid, int):
        #_trbid = hex(trbid)
    #else:
        #_trbid = trbid

def command_w(trbid, reg, data):
    cmd = ['trbcmd', 'w', trbid, hex(reg), hex(data)]

    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True

    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def command_wm(trbid, reg, data, mode):
    if cmd_to_file is not None:
        cmd = ['trbcmd', 'wm', trbid, hex(reg), str(mode), '- << EOF']
        cmd_to_file.write(' '.join(cmd) + '\n')
        for d in data:
            cmd_to_file.write(hex(d) + '\n')
        cmd_to_file.write('EOF\n')
        return True

    cmd = ['trbcmd', 'wm', trbid, hex(reg), str(mode), '-']
    _data = "\n".join([hex(x) for x in data])
    rc = subprocess.run(cmd, input=_data.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def command_r(trbid, reg):
    cmd = ['trbcmd', 'r', trbid, hex(reg)]

    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True

    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def command_rm(trbid, reg, length):
    cmd = ['trbcmd', 'rm', trbid, hex(reg), str(length), '0']

    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True

    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()
