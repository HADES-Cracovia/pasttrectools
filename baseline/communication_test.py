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
def_time = 0
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

def print_verbose(rc):
    cmd = ' '.join(rc.args)
    rtc = rc.returncode

    if def_verbose == 1:
        print("[{:d}]  {:s}".format(rtc, cmd))

def calc_channel(cable, asic, channel):
    return channel + def_pastrec_channel_range * asic + \
        def_pastrec_channel_range * len(PasttrecDefaults.c_asic)*cable

def calc_address(channel):
    cable = math.floor(channel / (def_pastrec_channel_range*len(def_pastrec_asic)))
    asic = math.floor((channel - cable*def_pastrec_channel_range*len(def_pastrec_asic)) / def_pastrec_channel_range)
    c = channel % def_pastrec_channel_range
    return cable, asic, c

def reset_asic(address, def_pasttrec):
    for a in address:
        for cable in list(range(len(PasttrecDefaults.c_cable))):
            _c = PasttrecDefaults.c_cable[cable]

            for asic in list(range(len(PasttrecDefaults.c_asic))):
                _a = PasttrecDefaults.c_asic[asic]

                d = def_pasttrec.dump_config_hex(cable, asic)

                for _d in d:
                    l = [ 'trbcmd', 'w', hex(a), hex(PasttrecDefaults.c_trbnet_reg), _d ]
                    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print_verbose(rc)

def write_reg(address, card, asic, reg, val):
    _c = PasttrecDefaults.c_cable[card]
    _a = PasttrecDefaults.c_asic[asic]
    _b = PasttrecDefaults.c_base_w | _c | _a
    v = _b | (reg << 8) | val

    l = [ 'trbcmd', 'w', hex(address), hex(PasttrecDefaults.c_trbnet_reg), hex(v) ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)

def read_reg(address, card, asic, reg):
    _c = PasttrecDefaults.c_cable[card]
    _a = PasttrecDefaults.c_asic[asic]
    _b = PasttrecDefaults.c_base_r | _c | _a
    v = _b | (reg << 8)

    l = [ 'trbcmd', 'w', hex(address), hex(PasttrecDefaults.c_trbnet_reg), hex(v) ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)

    l = [ 'trbcmd', 'r', hex(address), hex(PasttrecDefaults.c_trbnet_reg) ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()

def scan_communication(address):

    print("|--- TEST RANGE -------------------------------------------|")

    reg_test_vals = [ 1, 4, 7, 10, 13 ]
    test_ok = True
    for a in address:
        # looop over Cable
        for cable in list(range(len(PasttrecDefaults.c_cable))):
            # loop over ASIC

            for asic in list(range(len(PasttrecDefaults.c_asic))):
                print(Fore.YELLOW + "Testing {:s} cable {:d} asic {:d}".format(hex(a), cable, asic) + Style.RESET_ALL)

                asic_test_ok = True

                for reg in range(12):
                    reg_test_ok = True

                    for t in reg_test_vals:
                        print(".", end='', flush=True)
                        write_reg(a, cable, asic, reg, t)
                        sleep(def_time)
                        _t = int(read_reg(a, cable, asic, reg).split()[1], 16)

                        if _t != t:
                            print(Fore.RED + " Test failed for register {:d}".format(reg) + Style.RESET_ALL)
                            print("  Sent {:d}, received {:d}".format(t, _t))
                            reg_test_ok = False
                            break

                    if reg_test_ok == False:
                        asic_test_ok = False
                        test_ok = False
                        break

                if asic_test_ok:
                    print(Fore.GREEN + " done" + Style.RESET_ALL)
                #print("  done")

    if test_ok:
        print("All test done and OK")

    return None


if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Scan communication of PASTTREC chips',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('trbids', help='list of TRBids to scan', type=lambda x: int(x,0), nargs='+')

    parser.add_argument('-t', '--time', help='sleep time', type=float, default=def_time)
    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3', type=int, choices=[ 0, 1, 2, 3 ], default=0)

    args=parser.parse_args()

    def_verbose = args.verbose
    def_time = args.time

    if def_verbose > 0:
        print(args)

    # loop here
    ex = True
    #ex = False
    if ex:
        a = args.trbids

        #reset_asic(a, p)

        r = scan_communication(a)

        #reset_asic(a, p)

    else:
        p = PasttrecRegs(bg_int = args.source, gain = args.gain, peaking = args.peaking,
                         tc1c = args.timecancelationC1, tc1r = args.timecancelationR1,
                         tc2c = args.timecancelationC2, tc2r = args.timecancelationR2,
                         vth = 0)
        print(p.__dict__, p.dump_config_hex(0, 0))
