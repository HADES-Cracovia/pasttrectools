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
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os,sys,glob
import argparse
import subprocess
from time import sleep
import json
import math
from colorama import Fore, Style

from pasttrec import *

def_asics = '0x6400'
def_time = 0.01
def_verbose = 0

def_max_bl_registers = 32

### registers and values
# trbnet
def_broadcast_addr = 0xfe4f
def_scalers_reg = 0xc001
def_scalers_len = 0x21

def_pastrec_thresh_range = [ 0x00, 0x7f ]

def_pastrec_channel_range = 8
def_pastrec_channels_all = def_pastrec_channel_range * \
    len(PasttrecDefaults.c_asic) * len(PasttrecDefaults.c_cable)

def_pastrec_bl_base = 0x00000
def_pastrec_bl_range = [ 0x00, def_max_bl_registers ]

def_scan_type = None

def calc_channel(cable, asic, channel):
    return channel + def_pastrec_channel_range * asic + \
        def_pastrec_channel_range * len(PasttrecDefaults.c_asic)*cable

def calc_address(channel):
    cable = math.floor(channel / (def_pastrec_channel_range*len(def_pastrec_asic)))
    asic = math.floor((channel - cable*def_pastrec_channel_range*len(def_pastrec_asic)) / def_pastrec_channel_range)
    c = channel % def_pastrec_channel_range
    return cable, asic, c

def write_reg(address, card, asic, reg, val):
    _c = PasttrecDefaults.c_cable[card]
    _a = PasttrecDefaults.c_asic[asic]
    _b = PasttrecDefaults.c_base_w | _c | _a
    v = _b | (reg << 8) | val

    l = [ 'trbcmd', 'w', address, hex(PasttrecDefaults.c_trbnet_reg), hex(v) ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)

def read_reg(address, card, asic, reg):
    _c = PasttrecDefaults.c_cable[card]
    _a = PasttrecDefaults.c_asic[asic]
    _b = PasttrecDefaults.c_base_r | _c | _a
    v = _b | (reg << 8)

    l = [ 'trbcmd', 'w', address, hex(PasttrecDefaults.c_trbnet_reg), hex(v) ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)

    l = [ 'trbcmd', 'r', address, hex(PasttrecDefaults.c_trbnet_reg) ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()

def scan_communication(address):

    print("   TDC  Cable  Asic  >----------------------------------------------------------<")

    reg_test_vals = [ 1, 4, 7, 10, 13 ]
    test_ok = True
    for addr, cable, asic in address:
        print(Fore.YELLOW + "{:s}  {:5d} {:5d}  ".format(addr, cable, asic) + Style.RESET_ALL, end='', flush=True)

        asic_test_ok = True

        for reg in range(12):
            reg_test_ok = True

            for t in reg_test_vals:
                print(".", end='', flush=True)
                write_reg(addr, cable, asic, reg, t)
                sleep(def_time)
                _t = int(read_reg(addr, cable, asic, reg).split()[1], 16)

                if _t != t:
                    print(Fore.RED + " Test failed for register {:d}".format(reg) + Style.RESET_ALL, end='')
                    print("  Sent {:d}, received {:d}".format(t, _t))
                    reg_test_ok = False
                    break

            if reg_test_ok == False:
                asic_test_ok = False
                test_ok = False
                break

        if asic_test_ok:
            print(Fore.GREEN + " OK " + Style.RESET_ALL)

    if test_ok:
        print("All test done and OK")

    return None


if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Scan communication of PASTTREC chips',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('trbids', help='list of TRBids to scan in form addres[:card-0-1-2[:asic-0-1]]', type=str, nargs="+")

    parser.add_argument('-t', '--time', help='sleep time', type=float, default=def_time)
    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3', type=int, choices=[ 0, 1, 2, 3 ], default=0)

    args=parser.parse_args()

    def_verbose = args.verbose
    def_time = args.time

    if def_verbose > 0:
        print(args)

    tup = communication.decode_address(args.trbids)
    # loop here
    ex = True
    #ex = False
    if ex:
        a = args.trbids
        r = scan_communication(tup)

    else:
        p = PasttrecRegs(bg_int = args.source, gain = args.gain, peaking = args.peaking,
                         tc1c = args.timecancelationC1, tc1r = args.timecancelationR1,
                         tc2c = args.timecancelationC2, tc2r = args.timecancelationR2,
                         vth = 0)
        print(p.__dict__, p.dump_config_hex(0, 0))
