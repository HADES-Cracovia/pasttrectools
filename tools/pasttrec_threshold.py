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
from time import sleep
import json
import math

from pasttrec import *

def_asics = '0x6400'
def_time = 1
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

    if rtc != 0:
        print()
        print(Fore.RED + "Error code: {:d}\n{:s}".format(rtc, rc.stderr.decode()) + Style.RESET_ALL)
        sys.exit(rtc)

    if def_verbose == 1:
        print("[{:d}]  {:s}".format(rtc, cmd))

def send_value(address, value):
    # loop over channels
    for addr, cable, asic in address:
        _c = PasttrecDefaults.c_cable[cable]
        _a = PasttrecDefaults.c_asic[asic]

        b = PasttrecDefaults.c_base_w | _c | _a
        v = b | PasttrecDefaults.c_config_reg[3] | value if value <= 0x7ff else 0x7ff

        haddr = addr #hex(addr)
        send_command_w(haddr, PasttrecDefaults.c_trbnet_reg, v)

    print("Done")

if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Scan baseline of PASTTREC chips',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('trbids', help='list of TRBids to scan in form addres[:card-0-1-2[:asic-0-1]]', type=str, nargs="+")

    parser.add_argument('-t', '--time', help='sleep time', type=int, default=def_time)
    parser.add_argument('-o', '--output', help='output file', type=str, default='result.json')
    parser.add_argument('-s', '--scan', help='scan type: singel-low/high: one channel at a time, baseline set to low/high, multi: all channels parallel', choices=[ 'single-low', 'single-high', 'multi'], default='multi')
    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3', type=int, choices=[ 0, 1, 2, 3 ], default=0)

    parser.add_argument('-Bg', '--source', help='baseline set: internally or externally', type=int, choices=[1,0], default=1)
    parser.add_argument('-K', '--gain', help='amplification: 4, 2, 1 or 0.67 [mV/fC]', type=int, choices=[0, 1, 2, 3], default=0)
    parser.add_argument('-Tp', '--peaking', help='peaking time: 35, 20, 15 or 10 [ns]', type=int, choices=[3,2,1,0], default=3)

    parser.add_argument('-Vth', '--threshold', help='threshold: 0-127', type=lambda x: int(x,0), default=127)

    args=parser.parse_args()

    def_verbose = args.verbose
    def_time = args.time

    if def_verbose > 0:
        print(args)

    if args.threshold > def_pastrec_thresh_range[1] or args.threshold < def_pastrec_thresh_range[0]:
        print("\nOption error: Threshold value {:d} is to high, allowed value is 0-127".format(args.threshold))
        sys.exit(1)

    ex = True
    #ex = False

    tup = communication.decode_address(args.trbids)
    if ex:
        send_value(tup, args.threshold)
