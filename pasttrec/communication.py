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

# convert address into [ trbnet, cable, card, asic ] tuples
# input string:
# AAAAAA[:B[:C]]
#   AAAAAA - trbnet address, can be in form 0xAAAA or AAAA
#   B - card: 1, 2, 3, or empty ("", all cables), or two or three cards comma separated
#   C - asic: 1 or 2 or empty ("", all asics)
#  any higher section of the address can be skipped
# examples:
#  0x6400 - all cables, cards and asics
#  0x6400::1:2 - all cables, card 1, asic 2

def decode_address_entry(string):
    sections = string.split(":")
    sec_len = len(sections)

    if sec_len > 3:
        print("Error in string ", string)
        return []

    # do everything backwards
    # asics
    asics = []
    if sec_len == 3 and len(sections[2]) > 0:
        _asics = sections[2].split(",")
        asics = [ int(a)-1 for a in _asics if int(a) in range(1,3) ]
    else:
        asics = [ 0, 1 ]

    # asics
    cards = []
    if sec_len >= 2 and len(sections[1]) > 0:
        _cards = sections[1].split(",")
        cards = [ int(c)-1 for c in _cards if int(c) in range(1,4) ]
    else:
        cards = [ 0, 1, 2 ]

    # check address
    address = sections[0]
    if len(address) == 6:
        if address[0:2] != "0x":
            print("Incorrect address in string: ", string)
            return []
    elif len(address) == 4:
        address = "0x" + address
    else:
        print("Incorrect address in string: ", string)
        return []

    tup = [ [x] + [y] + [z] for x in [address,] for y in cards for z in asics ]
    return tup

# use this for a single string or list of strings
def decode_address(string):
    if type(string) is str:
        return decode_address_entry(string)
    else:
        tup = []
        for s in string:
            tup += decode_address_entry(s)
        return tup


# calculate address of cable and asic channel in tdc (0,48) or with reference channel offset (1, 49)
def calc_tdc_channel(cable, asic, channel, with_ref_time=False):
    return channel + def_pastrec_channel_range * asic + \
        def_pastrec_channel_range * len(PasttrecDefaults.c_asic)*cable + (1 if with_ref_time is True else 0)

# do reverse calculation
def calc_address_from_tdc(channel, with_ref_time=False):
    if with_ref_time:
        channel = channel-1
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
