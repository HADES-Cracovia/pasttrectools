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

class Scalers:
    scalers = None

    def __init__(self):
        self.scalers = {}

    def add_trb(self, trb):
        if trb not in self.scalers:
            self.scalers[trb] = [0] * def_pastrec_channels_all

    def diff(self, scalers):
        s = Scalers()
        for k,v in self.scalers.items():
            if k in scalers.scalers:
                s.add_trb(k)
                for i in list(range(def_pastrec_channels_all)):
                    vv = self.scalers[k][i] - scalers.scalers[k][i]
                    if vv < 0:
                        vv += 0x80000000
                    s.scalers[k][i] = vv
        return s

class Baselines:
    baselines = None
    config = None

    def __init__(self):
        self.baselines = {}

    def add_trb(self, trb):
        if trb not in self.baselines:
            w, h, a, c = def_max_bl_registers, def_pastrec_channel_range, len(PasttrecDefaults.c_asic), len(PasttrecDefaults.c_cable)
            self.baselines[trb] = [[[[0 for x in range(w)] for y in range(h)] for _a in range(a)] for _c in range(c)]

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

def read_rm_scalers(address):
    l = [ 'trbcmd', 'rm', hex(address), hex(def_scalers_reg), hex(def_pastrec_channels_all), '0' ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()

def parse_rm_scalers(res):
    sm = 0 # state machine: 0 - init, 1 - data
    s = Scalers()
    a = 0   # address
    c = 0   # channel
    lines = res.splitlines()
    for l in lines:
        ll = l.split()
        n = len(ll)

        if n == 2:
            if sm == 1:
                c = int(ll[0], 16) - def_scalers_reg
                if c > def_pastrec_channels_all:
                    continue
                s.scalers[a][c] = int(ll[1], 16)
            else:
                continue
        if n == 3:
            a = hex(int(ll[1], 16))
            s.add_trb(a)
            sm = 1

    return s

def read_r_scalers(address, channel):
    l = [ 'trbcmd', 'r', hex(address), hex(def_scalers_reg + channel) ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()

def parse_r_scalers(res):
    r = {}
    lines = res.splitlines()
    for l in lines:
        ll = l.split()
        n = len(ll)

        if n == 2:
            a = int(ll[0], 16)
            n = int(ll[1], 16)
            r[hex(a)] = n

    return r

def scan_baseline_single(address):
    bbb = Baselines()

    print("  address   channel   bl 0                              31")
    print("                         |------------------------------|")
    # loop over channels
    for c in list(range(def_pastrec_channel_range)):
        print("  {:s}    {:d}            ".format(hex(0xfe4f), c), end='', flush=True)

        # loop over bl register value
        for blv in range(def_pastrec_bl_range[0], def_pastrec_bl_range[1]):
            print("#", end='', flush=True)

            # looop over Cable
            for cable in list(range(len(PasttrecDefaults.c_cable))):
                _c = PasttrecDefaults.c_cable[cable]

                # loop over ASIC
                for asic in list(range(len(PasttrecDefaults.c_asic))):
                    _a = PasttrecDefaults.c_asic[asic]

                    b = PasttrecDefaults.c_base_w | _c | _a
                    v = b | PasttrecDefaults.c_bl_reg[c] | blv

                    # loop over TDC
                    for addr in address:
                        haddr = hex(addr)
                        l = [ 'trbcmd', 'w', haddr, hex(PasttrecDefaults.c_trbnet_reg), hex(v) ]
                        rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        print_verbose(rc)

            chan = calc_channel(cable, asic, c)

            sleep(0.1)
            v1 = read_rm_scalers(def_broadcast_addr)
            sleep(def_time)
            v2 = read_rm_scalers(def_broadcast_addr)
            a1 = parse_rm_scalers(v1)
            a2 = parse_rm_scalers(v2)
            bb = a2.diff(a1)

            # reset base line
            for cable in list(range(len(PasttrecDefaults.c_cable))):
                _c = PasttrecDefaults.c_cable[cable]
                for asic in list(range(len(PasttrecDefaults.c_asic))):
                    _a = PasttrecDefaults.c_asic[asic]

                    chan = calc_channel(cable, asic, c)

                    for addr in address:
                        haddr = hex(addr)
                        bbb.add_trb(haddr)

                        vv = bb.scalers[haddr][chan]
                        #print(vv)
                        if vv < 0:
                            vv += 0x80000000

                        bbb.baselines[haddr][cable][asic][c][blv] = vv

                    b = PasttrecDefaults.c_base_w | _c | _a
                    v = b | def_pastrec_bl_base | PasttrecDefaults.c_bl_reg[c]
                    for addr in address:
                        haddr = hex(addr)
                        l = [ 'trbcmd', 'w', haddr, hex(PasttrecDefaults.c_trbnet_reg), hex(v) ]
                        rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        print_verbose(rc)

        print("  done")

    return bbb


def scan_baseline_multi(address):
    bbb = Baselines()

    print("  address   channel   bl 0                                31")
    print("                         |--------------------------------|")
    print("  {:s}    {:s}           ".format(hex(0xfe4f), 'all'), end='', flush=True)

    # loop over bl register value
    for blv in range(def_pastrec_bl_range[0], def_pastrec_bl_range[1]):
        print("#", end='', flush=True)

        # loop over channels
        for c in list(range(def_pastrec_channel_range)):

            # get addressess
            for addr, cable, asic in address:
                _c = PasttrecDefaults.c_cable[cable]
                _a = PasttrecDefaults.c_asic[asic]

                b = PasttrecDefaults.c_base_w | _c | _a
                v = b | PasttrecDefaults.c_bl_reg[c] | blv

                # loop over TDC
                haddr = addr #hex(addr)
                l = [ 'trbcmd', 'w', haddr, hex(PasttrecDefaults.c_trbnet_reg), hex(v) ]
                rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print_verbose(rc)

        #sleep(1)
        v1 = read_rm_scalers(def_broadcast_addr)
        sleep(def_time)
        v2 = read_rm_scalers(def_broadcast_addr)
        a1 = parse_rm_scalers(v1)
        a2 = parse_rm_scalers(v2)
        bb = a2.diff(a1)

        # reset base line
        # loop over channels
        for c in list(range(def_pastrec_channel_range)):
            for addr, cable, asic in address:
                _c = PasttrecDefaults.c_cable[cable]
                _a = PasttrecDefaults.c_asic[asic]

                b = PasttrecDefaults.c_base_w | _c | _a
                v = b | PasttrecDefaults.c_bl_reg[c] | blv

                chan = calc_channel(cable, asic, c)

                haddr = addr#hex(addr)
                bbb.add_trb(haddr)

                vv = bb.scalers[haddr][chan]
                if vv < 0:
                    vv += 0x80000000

                bbb.baselines[haddr][cable][asic][c][blv] = vv

                b = PasttrecDefaults.c_base_w | _c | _a
                v = b | def_pastrec_bl_base | PasttrecDefaults.c_bl_reg[c]

                l = [ 'trbcmd', 'w', haddr, hex(PasttrecDefaults.c_trbnet_reg), hex(v) ]
                rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print_verbose(rc)

    print("  done")

    return bbb


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

    parser.add_argument('-TC1C', '--timecancelationC1', help='TC1 C: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=3)
    parser.add_argument('-TC1R', '--timecancelationR1', help='TC1 R: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=2)
    parser.add_argument('-TC2C', '--timecancelationC2', help='TC2 C: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=6)
    parser.add_argument('-TC2R', '--timecancelationR2', help='TC2 R: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=5)

    parser.add_argument('-Vth', '--threshold', help='threshold: 0-127', type=lambda x: int(x,0), default=0)

    args=parser.parse_args()

    def_verbose = args.verbose
    def_time = args.time

    if def_verbose > 0:
        print(args)

    if args.threshold > def_pastrec_thresh_range[1] or args.threshold < def_pastrec_thresh_range[0]:
        print("\nOption error: Threshold value {:d} is to high, allowed value is 0-127".format(args.threshold))
        sys.exit(1)

    # scan type
    def_scan_type = args.scan
    if def_scan_type == 'single-low':
        def_pastrec_bl_base = def_pastrec_bl_range[0]
    elif def_scan_type == 'single-high':
        def_pastrec_bl_base = def_pastrec_bl_range[1]-1
    elif def_scan_type == 'multi':
        def_pastrec_bl_base = def_pastrec_bl_range[0]

    p = PasttrecRegs(bg_int = args.source, gain = args.gain, peaking = args.peaking,
                     tc1c = args.timecancelationC1, tc1r = args.timecancelationR1,
                     tc2c = args.timecancelationC2, tc2r = args.timecancelationR2,
                     vth = args.threshold, bl = [ def_pastrec_bl_base ] * 8)

    # loop here
    ex = True
    #ex = False

    tup = communication.decode_address(args.trbids)
    print(tup)
    if ex:
        a = args.trbids

#        reset_asic(a, p)

        if def_scan_type == 'multi':
            r = scan_baseline_multi(tup)
        else:
            r = scan_baseline_single(tup)

        r.config = p.__dict__

#        reset_asic(a, p)

        with open(args.output, 'w') as fp:
            json.dump(r.__dict__, fp, indent=2)

    else:
        p = PasttrecRegs(bg_int = args.source, gain = args.gain, peaking = args.peaking,
                         tc1c = args.timecancelationC1, tc1r = args.timecancelationR1,
                         tc2c = args.timecancelationC2, tc2r = args.timecancelationR2,
                         vth = args.threshold)
        print(p.__dict__, p.dump_config_hex(0, 0))

