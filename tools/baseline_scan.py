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

import os
import sys
import glob
import argparse
from time import sleep
import json
import math

from pasttrec import *

def_time = 1

def_broadcast_addr = 0x6500 #0xfe4c
def_max_bl_register_steps = 32
def_pastrec_thresh_range = [0x00, 0x7f]
def_pastrec_bl_base = 0x00000
def_pastrec_bl_range = [0x00, def_max_bl_register_steps]


def scan_baseline_single(address):
    bbb = Baselines()

    print("  address   channel   bl 0" + " " * 32 + "31")
    print("                         |" + "-" * 32 + "|")
    # loop over channels
    for c in list(range(PasttrecDefaults.channels_num)):
        print("  {:s}    {:d}            "
              .format(hex(def_broadcast_addr), c), end='', flush=True)

        # loop over bl register value
        for blv in range(def_pastrec_bl_range[0], def_pastrec_bl_range[1]):
            print("#", end='', flush=True)

            # get addressess
            for addr, cable, asic in address:
                communication.write_reg(addr, cable, asic, 4+c, blv)

            v1 = read_rm_scalers(def_broadcast_addr)
            sleep(def_time)
            v2 = read_rm_scalers(def_broadcast_addr)
            a1 = parse_rm_scalers(v1)
            a2 = parse_rm_scalers(v2)
            bb = a2.diff(a1)
            
            #print("scalers: ",v1," "," ",v2)

            # get addressess
            for addr, cable, asic in address:
                chan = calc_tdc_channel(cable, asic, c)
                #print("\ncheck0 :", addr," ",chan," ", cable," ", asic," ", c)

                vv = bb.scalers[addr][chan]
                #print("\ncheck1")
                if vv < 0:
                    vv += 0x80000000

                bbb.add_trb(addr)
                bbb.baselines[addr][cable][asic][c][blv] = vv

                # See comment in scan_baseline_multi()
                # communication.write_reg(addr, cable, asic, 4+c, 0x00)

        print("  done")

    return bbb


def scan_baseline_multi(address):
    bbb = Baselines()

    print("  address   channel   bl 0" + " " * 32 + "31")
    print("                         |" + "-" * 32 + "|")
    print("  {:s}    {:s}            "
          .format(hex(def_broadcast_addr), 'all'), end='', flush=True)

    # loop over bl register value
    for blv in range(def_pastrec_bl_range[0], def_pastrec_bl_range[1]):
        print("#", end='', flush=True)

        # get addressess
        for addr, cable, asic in address:
            blv_data = []
            # loop over channels
            for c in list(range(PasttrecDefaults.channels_num)):
                blv_data.append(PasttrecDefaults.c_bl_reg[c] | blv)

            communication.write_chunk(addr, cable, asic, blv_data)

        v1 = read_rm_scalers(def_broadcast_addr)
        sleep(def_time)
        v2 = read_rm_scalers(def_broadcast_addr)
        a1 = parse_rm_scalers(v1)
        a2 = parse_rm_scalers(v2)
        bb = a2.diff(a1)

        # reset base line
        # loop over channels
        for addr, cable, asic in address:
            blv_data = []
            for c in list(range(PasttrecDefaults.channels_num)):
                blv_data.append(PasttrecDefaults.c_bl_reg[c])

                chan = calc_tdc_channel(cable, asic, c)
                #print(chan, cable, asic, c)

                vv = bb.scalers[addr][chan]
                if vv < 0:
                    vv += 0x80000000

                bbb.add_trb(addr)
                bbb.baselines[addr][cable][asic][c][blv] = vv

            # This line kills baseline scan for the reg #16 (last of 2nd asic
            # but dunno why. Why writing zero kills it?
            # communication.write_chunk(addr, cable, asic, blv_data)

    print("  done")

    return bbb


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Scan baseline of the PASTTREC chips',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('trbids', help='list of TRBids to scan in form'
                        ' addres[:card-0-1-2[:asic-0-1]]', type=str, nargs="+")

    parser.add_argument('-t', '--time', help='sleep time',
                        type=float, default=def_time)
    parser.add_argument('-o', '--output', help='output file',
                        type=str, default='result.json')
    parser.add_argument('-s', '--scan', help='scan type: singel-low/high:'
                        ' one channel at a time, baseline set to low/high,'
                        ' multi: all channels parallel',
                        choices=['single-low', 'single-high', 'multi'],
                        default='multi')
    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3',
                        type=int, choices=[0, 1, 2, 3], default=0)

    parser.add_argument('--defaults', dest='defaults', action='store_true',
                        help='Override settings with defaults from cmd line')

    parser.add_argument('-Bg', '--source',
                        help='baseline set: internally or externally',
                        type=int, choices=[1, 0], default=1)
    parser.add_argument('-K', '--gain',
                        help='amplification: 4, 2, 1 or 0.67 [mV/fC]',
                        type=int, choices=[0, 1, 2, 3], default=0)
    parser.add_argument('-Tp', '--peaking',
                        help='peaking time: 35, 20, 15 or 10 [ns]',
                        type=int, choices=[3, 2, 1, 0], default=3)

    parser.add_argument('-TC1C', '--timecancelationC1',
                        help='TC1 C: 35, 20, 15 or 10 [ns]',
                        type=lambda x: int(x, 0), choices=range(8), default=3)
    parser.add_argument('-TC1R', '--timecancelationR1',
                        help='TC1 R: 35, 20, 15 or 10 [ns]',
                        type=lambda x: int(x, 0), choices=range(8), default=2)
    parser.add_argument('-TC2C', '--timecancelationC2',
                        help='TC2 C: 35, 20, 15 or 10 [ns]',
                        type=lambda x: int(x, 0), choices=range(8), default=6)
    parser.add_argument('-TC2R', '--timecancelationR2',
                        help='TC2 R: 35, 20, 15 or 10 [ns]',
                        type=lambda x: int(x, 0), choices=range(8), default=5)

    parser.add_argument('-Vth', '--threshold', help='threshold: 0-127',
                        type=lambda x: int(x, 0), default=0)

    args = parser.parse_args()

    communication.g_verbose = args.verbose
    def_time = args.time

    if communication.g_verbose > 0:
        print(args)

    if args.threshold > def_pastrec_thresh_range[1] or \
       args.threshold < def_pastrec_thresh_range[0]:
        print("\nOption error: Threshold value {:d} is to high,"
              " allowed value is 0-127".format(args.threshold))
        sys.exit(1)

    # scan type
    def_scan_type = args.scan
    if def_scan_type == 'single-low':
        def_pastrec_bl_base = def_pastrec_bl_range[0]
    elif def_scan_type == 'single-high':
        def_pastrec_bl_base = def_pastrec_bl_range[1]-1
    elif def_scan_type == 'multi':
        def_pastrec_bl_base = def_pastrec_bl_range[0]

    p = PasttrecRegs(bg_int=args.source, gain=args.gain, peaking=args.peaking,
                     tc1c=args.timecancelationC1, tc1r=args.timecancelationR1,
                     tc2c=args.timecancelationC2, tc2r=args.timecancelationR2,
                     vth=args.threshold, bl=[def_pastrec_bl_base]*8)

    tup = communication.decode_address(args.trbids)

    if (args.defaults):
        communication.asics_to_defaults(tup, p)

    if def_scan_type == 'multi':
        r = scan_baseline_multi(tup)
    else:
        r = scan_baseline_single(tup)

    r.config = p.__dict__

    if (args.defaults):
        communication.asics_to_defaults(tup, p)

    with open(args.output, 'w') as fp:
        json.dump(r.__dict__, fp, indent=2)
