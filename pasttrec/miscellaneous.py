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

import os
import sys
import glob
import argparse
from time import sleep
import json
import math

from pasttrec import *

# Custom settings

# Baselines
def_max_bl_registers = 32

# Scalers
def_scalers_reg = 0xc001

def_pastrec_channel_range = 8
def_pastrec_channels_all = def_pastrec_channel_range * \
    len(PasttrecDefaults.c_asic) * len(PasttrecDefaults.c_cable)


class Baselines:
    baselines = None
    config = None

    def __init__(self):
        self.baselines = {}

    def add_trb(self, trb):
        if trb not in self.baselines:
            w, h, a, c = def_max_bl_registers, def_pastrec_channel_range, len(PasttrecDefaults.c_asic), len(PasttrecDefaults.c_cable)
            self.baselines[trb] = [[[[0 for x in range(w)] for y in range(h)] for _a in range(a)] for _c in range(c)]


class Scalers:
    scalers = None

    def __init__(self):
        self.scalers = {}

    def add_trb(self, trb):
        if trb not in self.scalers:
            self.scalers[trb] = [0] * def_pastrec_channels_all

    def diff(self, scalers):
        s = Scalers()
        for k, v in self.scalers.items():
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
            w = 128
            h = def_pastrec_channel_range
            a = len(PasttrecDefaults.c_asic)
            c = len(PasttrecDefaults.c_cable)
            self.thresholds[trb] = [
                [[[0 for x in range(w)] for y in range(h)]
                    for _a in range(a)] for _c in range(c)]


def parse_rm_scalers(res):
    sm = 0  # state machine: 0 - init, 1 - data
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

def calc_channel(cable, asic, channel):
    return channel + def_pastrec_channel_range * asic + \
        def_pastrec_channel_range * len(PasttrecDefaults.c_asic)*cable


def calc_address(channel):
    cable = math.floor(channel
                       / (def_pastrec_channel_range*len(def_pastrec_asic)))
    asic = math.floor((channel
                       - cable*def_pastrec_channel_range*len(def_pastrec_asic))
                       / def_pastrec_channel_range)
    c = channel % def_pastrec_channel_range
    return cable, asic, c
