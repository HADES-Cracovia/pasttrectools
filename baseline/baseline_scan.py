#!/usr/bin/env python3

import os,sys,glob
import argparse
import subprocess
from time import sleep
import json
import math

def_asics = '0x6400'
def_mem = "500mb"
def_script='job_script.sh'
def_dir='./'
def_time = 1
def_verbose = 0

class PasttrecDefaults:
    c_cable = [ 0x00 << 19, 0x01 << 19, 0x02 << 19 ]
    c_asic = [ 0x2000, 0x4000 ]

#                Bg_int,K,Tp      TC1      TC2      Vth
    c_config_reg = [ 0x00000, 0x00100, 0x00200, 0x00300 ]
    c_bl_reg = [ 0x00400, 0x00500, 0x00600, 0x00700,
                0x00800, 0x00900, 0x00a00, 0x00b00 ]

    c_trbnet_reg = 0xa000
    c_base_w = 0x0050000
    c_base_r = 0x0051000

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

class PasttrecRegs(PasttrecDefaults):
    bg_int = 0
    gain = 0
    peaking = 0
    tc1c = 0
    tc1r = 0
    tc2c = 0
    tc2r = 0
    vth = 0
    bl = [0] * 8

    def __init__(self, bg_int = 1, gain = 0, peaking = 0,
                 tc1c = 0, tc1r = 0, tc2c = 0, tc2r = 0,
                 vth = 0, bl = [0] * 8):
        self.bg_int   = bg_int
        self.gain     = gain
        self.peaking  = peaking
        self.tc1c     = tc1c
        self.tc1r     = tc1r
        self.tc2c     = tc2c
        self.tc2r     = tc2r
        self.vth      = vth
        self.bl       = bl

    def dump_config(self, cable, asic):
        r_all = [0] * 12
        offset = self.c_base_w | self.c_cable[cable] | self.c_asic[asic]
        t = (self.bg_int << 4) | (self.gain << 2) | self.peaking
        r_all[0] = offset | self.c_config_reg[0] | t
        t = (self.tc1c << 3) | self.tc1r
        r_all[1] = offset | self.c_config_reg[1] | t
        t = (self.tc2c << 3) | self.tc2r
        r_all[2] = offset | self.c_config_reg[2] | t
        r_all[3] = offset | self.c_config_reg[3] | self.vth

        for i in range(8):
            r_all[4+i] = offset | self.c_bl_reg[i] | self.bl[i]

        return r_all

    def dump_config_hex(self, cable, asic):
        return [ hex(i) for i in p.dump_config(cable, asic) ]

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

    print("  address   channel   bl 0                              31")
    print("                         |------------------------------|")
    print("  {:s}    {:s}          ".format(hex(0xfe4f), 'all'), end='', flush=True)

    # loop over bl register value
    for blv in range(def_pastrec_bl_range[0], def_pastrec_bl_range[1]):
        print("#", end='', flush=True)

        # loop over channels
        for c in list(range(def_pastrec_channel_range)):

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

        sleep(0.1)
        v1 = read_rm_scalers(def_broadcast_addr)
        sleep(def_time)
        v2 = read_rm_scalers(def_broadcast_addr)
        a1 = parse_rm_scalers(v1)
        a2 = parse_rm_scalers(v2)
        bb = a2.diff(a1)

        # reset base line
        for c in list(range(def_pastrec_channel_range)):
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


if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Scan baseline of PASTTREC chips',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('trbids', help='list of TRBids to scan', type=lambda x: int(x,0), nargs='+')

    parser.add_argument('-t', '--time', help='sleep time', type=int, default=def_time)
    parser.add_argument('-o', '--output', help='output file', type=str, default='result.json')
    parser.add_argument('-s', '--scan', help='scan type: singel-low/high: one channel at a time, baseline set to low/high, multi: all channels parallel', choices=[ 'single-low', 'single-high', 'multi'], default='single-low')
    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3', type=int, choices=[ 0, 1, 2, 3 ], default=0)

    parser.add_argument('-Bg', '--source', help='baseline set: internally or externally', type=int, choices=[1,0], default=1)
    parser.add_argument('-K', '--gain', help='amplification: 4, 2, 1 or 0.67 [mV/fC]', type=int, choices=[3,2,1,0], default=3)
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
    if ex:
        a = args.trbids

        reset_asic(a, p)

        if def_scan_type == 'multi':
            r = scan_baseline_multi(a)
        else:
            r = scan_baseline_single(a)

        r.config = p.__dict__

        reset_asic(a, p)

        with open(args.output, 'w') as fp:
            json.dump(r.__dict__, fp, indent=2)

    else:
        p = PasttrecRegs(bg_int = args.source, gain = args.gain, peaking = args.peaking,
                         tc1c = args.timecancelationC1, tc1r = args.timecancelationR1,
                         tc2c = args.timecancelationC2, tc2r = args.timecancelationR2,
                         vth = args.threshold)
        print(p.__dict__, p.dump_config_hex(0, 0))
