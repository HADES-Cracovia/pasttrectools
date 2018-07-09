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


def_max_bl_registers = 32

### registers and values
# trbnet
def_broadcast_addr = 0xfe4f
def_pastrec_comm = 0xa000
def_scalers_reg = 0xc001
def_scalers_len = 0x21

# pastrec
def_pastrec_base_w = 0x0050000
def_pastrec_base_r = 0x0051000

def_pastrec_cable = [ 0x00 << 19, 0x01 << 19, 0x02 << 19 ]
def_pastrec_asic = [ 0x2000, 0x4000 ]

#                          K, Tp    TC1      TC2      Vth
def_pastrec_config_reg = [ 0x00000, 0x00100, 0x00200, 0x00300 ]
def_pastrec_config_val = [ 0x00012, 0x0001e, 0x00015, 0x00000 ]
def_pastrec_thresh_range = [ 0x00, 0x7f ]
def_pastrec_channel_range = 8
def_pastrec_channels_all = def_pastrec_channel_range * len(def_pastrec_asic) * len(def_pastrec_cable)
def_pastrec_bl_base = 0x00000

def_pastrec_bl_coff = [
        0x00400,    # cha 1
        0x00500,
        0x00600,
        0x00700,
        0x00800,
        0x00900,
        0x00a00,
        0x00b00,    # cha 8
    ]
def_pastrec_bl_range = [ 0x00, def_max_bl_registers ]

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

    def __init__(self):
        self.baselines = {}

    def add_trb(self, trb):
        if trb not in self.baselines:
            w, h, a, c = def_max_bl_registers, def_pastrec_channel_range, len(def_pastrec_asic), len(def_pastrec_cable)
            self.baselines[trb] = [[[[0 for x in range(w)] for y in range(h)] for _a in range(a)] for _c in range(c)]

def calc_channel(cable, asic, channel):
    return channel + def_pastrec_channel_range*asic + def_pastrec_channel_range*len(def_pastrec_asic)*cable

def calc_address(channel):
    cable = math.floor(channel / (def_pastrec_channel_range*len(def_pastrec_asic)))
    asic = math.floor((channel - cable*def_pastrec_channel_range*len(def_pastrec_asic)) / def_pastrec_channel_range)
    c = channel % def_pastrec_channel_range
    return cable, asic, c

def reset_asic(address):
    for a in address:
        for cable in list(range(len(def_pastrec_cable))):
            _c = def_pastrec_cable[cable]

            for asic in list(range(len(def_pastrec_asic))):
                _a = def_pastrec_asic[asic]

                # reset all registers to def
                for r in list(range(len(def_pastrec_config_reg))):
                    l = [ 'trbcmd', 'w', hex(a), hex(def_pastrec_comm), hex(def_pastrec_base_w | _c | _a | def_pastrec_config_reg[r] | def_pastrec_config_val[r]) ]
                    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    #print(rc)

                # set all baselines to min
                for coff in def_pastrec_bl_coff:
                    l = [ 'trbcmd', 'w', hex(a), hex(def_pastrec_comm), hex(def_pastrec_base_w | _c | _a | def_pastrec_bl_base | coff + def_pastrec_bl_range[0]) ]
                    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    #print(rc)

def read_rm_scalers(address):
    l = [ 'trbcmd', 'rm', hex(address), hex(def_scalers_reg), hex(def_pastrec_channels_all), '0' ]
    rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #print(rc)
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
    #print(rc)
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

def scan_baseline(address):
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
            for cable in list(range(len(def_pastrec_cable))):
                _c = def_pastrec_cable[cable]

                # loop over ASIC
                for asic in list(range(len(def_pastrec_asic))):
                    _a = def_pastrec_asic[asic]

                    v = def_pastrec_base_w | _a | _c | def_pastrec_bl_base | def_pastrec_bl_coff[c] | blv

                    # loop over TDC
                    for addr in address:
                        haddr = hex(addr)
                        l = [ 'trbcmd', 'w', haddr, hex(def_pastrec_comm), hex(v) ]
                        rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        #print(rc)

            chan = calc_channel(cable, asic, c)
            #print(cable, asic, c, chan)

            #v1 = read_r_scalers(def_broadcast_addr, chan)
            #a1 = parse_r_scalers(v1)
            #sleep(def_time)
            #v2 = read_r_scalers(def_broadcast_addr, chan)
            #a2 = parse_r_scalers(v2)

            v1 = read_rm_scalers(def_broadcast_addr)
            a1 = parse_rm_scalers(v1)
            sleep(def_time)
            v2 = read_rm_scalers(def_broadcast_addr)
            a2 = parse_rm_scalers(v2)
            bb = a2.diff(a1)

            #print(v1, v2)
            #for addr in address:
                #haddr = hex(addr)
                #bbb.add_trb(haddr)

                #vv = a2[haddr] - a1[haddr]
                #print(vv)
                #if vv < 0:
                    #vv += 0x80000000

                #bbb.baselines[haddr][cable][asic][c][blv] = vv

            # reset base line
            for cable in list(range(len(def_pastrec_cable))):
                _c = def_pastrec_cable[cable]
                for asic in list(range(len(def_pastrec_asic))):
                    _a = def_pastrec_asic[asic]

                    chan = calc_channel(cable, asic, c)

                    for addr in address:
                        haddr = hex(addr)
                        bbb.add_trb(haddr)

                        vv = bb.scalers[haddr][chan]
                        #print(vv)
                        if vv < 0:
                            vv += 0x80000000

                        bbb.baselines[haddr][cable][asic][c][blv] = vv

                    v = def_pastrec_base_w | _c | _a | def_pastrec_bl_base | def_pastrec_bl_coff[c] + 0x00
                    for addr in address:
                        haddr = hex(addr)
                        l = [ 'trbcmd', 'w', haddr, hex(def_pastrec_comm), hex(v) ]
                        rc = subprocess.run(l, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        #print(rc)

        print("  done")

    return bbb

if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Scan baseline of PASTTREC chips',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('trbids', help='list of TRBids to scan', type=lambda x: int(x,0), nargs='+')

    parser.add_argument('-t', '--time', help='sleep time', type=int, default=def_time)
    parser.add_argument('-o', '--output', help='output file', type=str, default='result.json')

    parser.add_argument('-Bg', '--source', help='baseline set: internally or externally', type=int, choices=[1,0], default=1)
    parser.add_argument('-K', '--gain', help='amplification: 4, 2, 1 or 0.67 [mV/fC]', type=int, choices=[3,2,1,0], default=3)
    parser.add_argument('-Tp', '--peaking', help='peaking time: 35, 20, 15 or 10 [ns]', type=int, choices=[3,2,1,0], default=3)

    parser.add_argument('-TC1C', '--timecancelationC1', help='TC1 C: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=(def_pastrec_config_val[1] >> 3))
    parser.add_argument('-TC1R', '--timecancelationR1', help='TC1 R: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=(def_pastrec_config_val[1] & 0x7))
    parser.add_argument('-TC2C', '--timecancelationC2', help='TC2 C: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=(def_pastrec_config_val[2] >> 3))
    parser.add_argument('-TC2R', '--timecancelationR2', help='TC2 R: 35, 20, 15 or 10 [ns]', type=lambda x: int(x,0), choices=range(8), default=(def_pastrec_config_val[2] & 0x7))

    parser.add_argument('-Vth', '--threshold', help='threshold: 0-127', type=lambda x: int(x,0), default=def_pastrec_config_val[3])

    args=parser.parse_args()
    print(args)

    def_time = args.time

    def_pastrec_config_val[0] = (args.gain << 2) | args.peaking
    def_pastrec_config_val[1] = (args.timecancelationC1 << 3) | args.timecancelationR1
    def_pastrec_config_val[2] = (args.timecancelationC2 << 3) | args.timecancelationR2

    if args.threshold > def_pastrec_thresh_range[1] or args.threshold < def_pastrec_thresh_range[0]:
        print("\nOption error: Threshold value {:d} is to high, allowed value is 0-127".format(args.threshold))
        sys.exit(1)

    def_pastrec_config_val[3] = args.threshold

    # loop here
    ex = True
    #ex = False
    if ex:
        a = args.trbids

        reset_asic(a)
        r = scan_baseline(a)

        with open(args.output, 'w') as fp:
            json.dump(r.baselines, fp, indent=2)
