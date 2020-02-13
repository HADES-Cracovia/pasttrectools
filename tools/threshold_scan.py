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
def_threshold_max = 0

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


class Thresholds:
    thresholds = None
    config = None

    def __init__(self):
        self.thresholds = {}

    def add_trb(self, trb):
        if trb not in self.thresholds:
            w, h, a, c = 128, def_pastrec_channel_range, len(PasttrecDefaults.c_asic), len(PasttrecDefaults.c_cable)
            self.thresholds[trb] = [[[[0 for x in range(w)] for y in range(h)] for _a in range(a)] for _c in range(c)]


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
                    send_command_w(a, PasttrecDefaults.c_trbnet_reg,_d)


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


def scan_threshold(address):
    ttt = Thresholds()

    print("  address   channel   th 0                                                                                                                                127")
    print("                         |--------------------------------------------------------------------------------------------------------------------------------|")
    print("  {:s}    {:s}           ".format(hex(0xfe4f), 'all'), end='', flush=True)

    # loop over bl register value
    for vth in range(def_pastrec_thresh_range[0], def_threshold_max):
        print("#", end='', flush=True)

        # looop over Cable
        for cable in list(range(len(PasttrecDefaults.c_cable))):
            _c = PasttrecDefaults.c_cable[cable]

            # loop over ASIC
            for asic in list(range(len(PasttrecDefaults.c_asic))):
                _a = PasttrecDefaults.c_asic[asic]

                b = PasttrecDefaults.c_base_w | _c | _a
                v = b | PasttrecDefaults.c_config_reg[3] | vth

                # loop over TDC
                for addr in address:
                    send_command_w(addr, PasttrecDefaults.c_trbnet_reg, v)

        sleep(0.1)
        v1 = read_rm_scalers(def_broadcast_addr)
        sleep(def_time)
        v2 = read_rm_scalers(def_broadcast_addr)
        a1 = parse_rm_scalers(v1)
        a2 = parse_rm_scalers(v2)
        bb = a2.diff(a1)

        for cable in list(range(len(PasttrecDefaults.c_cable))):
            _c = PasttrecDefaults.c_cable[cable]
            for asic in list(range(len(PasttrecDefaults.c_asic))):
                _a = PasttrecDefaults.c_asic[asic]
                for c in list(range(def_pastrec_channel_range)):
                    chan = calc_channel(cable, asic, c)

                    for addr in address:
                        haddr = hex(addr)
                        ttt.add_trb(haddr)

                        vv = bb.scalers[haddr][chan]
                        if vv < 0:
                            vv += 0x80000000
                        ttt.thresholds[haddr][cable][asic][c][vth] = vv

    print("  done")

    return ttt


if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Scan baseline of PASTTREC chips',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('trbids', help='list of TRBids to scan', type=lambda x: int(x,0), nargs='+')

    parser.add_argument('-t', '--time', help='sleep time', type=int, default=def_time)
    parser.add_argument('-o', '--output', help='output file', type=str, default='result.json')
    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3', type=int, choices=[ 0, 1, 2, 3 ], default=0)
    parser.add_argument('-l', '--limit', help='threshold scan limit', type=int, choices=range(128), default=127)

    parser.add_argument('-Bg', '--source', help='baseline set: internally or externally', type=int, choices=[1,0], default=1)
    parser.add_argument('-K', '--gain', help='amplification: 4, 2, 1 or 0.67 [mV/fC]', type=int, choices=[0, 1, 2, 3], default=0)
    parser.add_argument('-Tp', '--peaking', help='peaking time: 35, 20, 15 or 10 [ns]', type=int, choices=[3,2,1,0], default=3)

    parser.add_argument('-TC1C', '--timecancelationC1', help='TC1 C: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=3)
    parser.add_argument('-TC1R', '--timecancelationR1', help='TC1 R: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=2)
    parser.add_argument('-TC2C', '--timecancelationC2', help='TC2 C: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=6)
    parser.add_argument('-TC2R', '--timecancelationR2', help='TC2 R: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=5)

    args=parser.parse_args()

    def_verbose = args.verbose
    def_time = args.time
    def_threshold_max = args.limit

    if def_verbose > 0:
        print(args)

    p = PasttrecRegs(bg_int = args.source, gain = args.gain, peaking = args.peaking,
                     tc1c = args.timecancelationC1, tc1r = args.timecancelationR1,
                     tc2c = args.timecancelationC2, tc2r = args.timecancelationR2,
                     vth = 0, bl = [ 0 ] * 8)

    # loop here
    ex = True
    #ex = False
    if ex:
        a = args.trbids

        #reset_asic(a, p)

        r = scan_threshold(a)

        r.config = p.__dict__

        #reset_asic(a, p)

        with open(args.output, 'w') as fp:
            json.dump(r.__dict__, fp, indent=2)

    else:
        p = PasttrecRegs(bg_int = args.source, gain = args.gain, peaking = args.peaking,
                         tc1c = args.timecancelationC1, tc1r = args.timecancelationR1,
                         tc2c = args.timecancelationC2, tc2r = args.timecancelationR2,
                         vth = 0)
        print(p.__dict__, p.dump_config_hex(0, 0))