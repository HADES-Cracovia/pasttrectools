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

try:
    from trbnet import TrbNet
except ImportError:
    trbnet_available = False
    trbnet = None
    print("INFO: Trbnet library not found.")
else:
    trbnet_available = True
    lib = '/trbnettools/trbnetd/libtrbnet.so'
    host = os.getenv("DAQOPSERVER")
    trbnet = TrbNet(libtrbnet=lib, daqopserver=host)
    print("INFO: Trbnet library found at {:s}", host)

# chip communication

def_asics = '0x6400'
def_time = 1
def_verbose = 0

def_max_bl_registers = 32

""" registers and values """
# trbnet
def_broadcast_addr = 0xfe4f
def_scalers_reg = 0xc001
def_scalers_len = 0x21

def_pastrec_thresh_range = [0x00, 0x7f]

def_pastrec_channel_range = 8
def_pastrec_channels_all = def_pastrec_channel_range * \
    len(PasttrecDefaults.c_asic) * len(PasttrecDefaults.c_cable)

def_pastrec_bl_base = 0x00000
def_pastrec_bl_range = [0x00, def_max_bl_registers]

""" Converts address into [ trbnet, cable, card, asic ] tuples
    input string:
    AAAAAA[:B[:C]]
      AAAAAA - trbnet address, can be in form 0xAAAA or AAAA
      B - card: 1, 2, 3, or empty ("", all cables), or two or three cards comma separated
      C - asic: 1 or 2 or empty ("", all asics)
     any higher section of the address can be skipped
    examples:
     0x6400 - all cables and asics
     0x6400::2 - all cables, asic 2"""
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
        asics = [int(a)-1 for a in _asics if int(a) in range(1,3)]
    else:
        asics = [0, 1]

    # asics
    cards = []
    if sec_len >= 2 and len(sections[1]) > 0:
        _cards = sections[1].split(",")
        cards = [int(c)-1 for c in _cards if int(c) in range(1,4)]
    else:
        cards = [0, 1, 2]

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

    tup = [[x] + [y] + [z] for x in [address, ] for y in cards for z in asics]
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


def print_verbose(rc):
    cmd = ' '.join(rc.args)
    rtc = rc.returncode

    if def_verbose == 1:
        print("[{:d}]  {:s}".format(rtc, cmd))


def reset_asic(address, verbose = False):
    if type(address) is not list:
        a = decode_address(address)
    else:
        a = address

    for addr, cable, asic in a:
        d = PasttrecRegs.reset_config(cable, asic)

        print(Fore.YELLOW + "Reseting {:s} cable {:d} asic {:d} with data {:s}".format(addr, cable, asic, hex(d)) + Style.RESET_ALL)
        safe_command_w(addr, PasttrecDefaults.c_trbnet_reg, d)


def asic_to_defaults(address, def_pasttrec):
    for a in address:
        for cable in list(range(len(PasttrecDefaults.c_cable))):
            _c = PasttrecDefaults.c_cable[cable]

            for asic in list(range(len(PasttrecDefaults.c_asic))):
                _a = PasttrecDefaults.c_asic[asic]

                d = def_pasttrec.dump_config_hex(cable, asic)

                for _d in d:
                    safe_command_w(a, PasttrecDefaults.c_trbnet_reg, _d)


def read_rm_scalers(address):
    return safe_command_rm(address, def_scalers_reg, def_pastrec_channels_all)


def read_r_scalers(address, channel):
    return safe_command_r(address, def_scalers_reg + channel)


""" These functions write, read or rad memory for given cable and asic.
    They all call safe_command_ functions. """


def write_reg(address, card, asic, reg, val):
    if trbnet_available:
        pass
    else:
        _c = PasttrecDefaults.c_cable[card]
        _a = PasttrecDefaults.c_asic[asic]
        _b = PasttrecDefaults.c_base_w | _c | _a
        v = _b | (reg << 8) | val
        safe_command_w(address, PasttrecDefaults.c_trbnet_reg, v)


def read_reg(address, card, asic, reg):
    if trbnet_available:
        pass
    else:
        _c = PasttrecDefaults.c_cable[card]
        _a = PasttrecDefaults.c_asic[asic]
        _b = PasttrecDefaults.c_base_r | _c | _a
        v = _b | (reg << 8)
        safe_command_w(address, PasttrecDefaults.c_trbnet_reg, v)
        return safe_command_r(address, PasttrecDefaults.c_trbnet_reg)


def write_data(trbid, cable, asic, data):
    if trbnet_available:
        pass
    else:
        _c = PasttrecDefaults.c_cable[cable]
        _a = PasttrecDefaults.c_asic[asic]
        _b = PasttrecDefaults.c_base_w | _c | _a
        v = _b | data
        safe_command_w(trbid, PasttrecDefaults.c_trbnet_reg, v)


""" Safe commands are etsting for trbnet librray and choose between
    the librray or the shell. """


def safe_command_w(trbid, reg, data):
    if isinstance(trbid, int):
        _trbid = hex(trbid)
    else:
        _trbid = trbid

    if trbnet_available:
        return trbnet_command_w(_trbid, reg, data)
    else:
        return shell_command_w(_trbid, reg, data)


def safe_command_r(trbid, reg):
    if isinstance(trbid, int):
        _trbid = hex(trbid)
    else:
        _trbid = trbid

    if trbnet_available:
        return trbnet_command_r(_trbid, reg)
    else:
        return shell_command_r(_trbid, reg)


def safe_command_rm(trbid, reg, length):
    if isinstance(trbid, int):
        _trbid = hex(trbid)
    else:
        _trbid = trbid

    if trbnet_available:
        return trbnet_command_rm(_trbid, reg, length)
    else:
        return shell_command_rm(_trbid, reg, length)


""" These functions are shell functions. """


def shell_command_w(trbid, reg, data):
    cmd = ['trbcmd', 'w', trbid, hex(reg), hex(data)]
    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def shell_command_r(trbid, reg):
    cmd = ['trbcmd', 'r', trbid, hex(reg)]
    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def shell_command_rm(trbid, reg, length):
    cmd = ['trbcmd', 'rm', trbid, hex(reg), length, '0']
    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


""" These functions are trbnetlibrary functions. """


def trbnet_command_w(trbid, reg, data):
    rc = trbnet.trb_register_write(trbid, reg, data)
    print_verbose(rc)
    return rc.stdout.decode()


def trbnet_command_r(trbid, reg):
    rc = trbnet.trb_register_read(trbid, reg)
    print_verbose(rc)
    return rc.stdout.decode()


def trbnet_command_rm(trbid, reg, length):
    rc = trbnet.trb_register_read_mem(trbid, reg, length)
    print_verbose(rc)
    return rc.stdout.decode()


""" SPI protocol function. """


spi_queue = 0
spi_mem = {}


""" Based on GSI code from M. Wiebusch """


def spi_write(trbid, cable, asic, data):
    #TDC = int(TDC_str, 16) FIXME test if string or int
    _trbid = trbid

    if _trbid not in spi_mem:
        spi_mem[_trbid] = {}
    if cable not in spi_mem[_trbid]:
        spi_mem[_trbid][cable] = {}
    if asic not in spi_mem[_trbid][cable]:
        spi_mem[_trbid][cable][asic] = []

    if spi_queue:
        if isinstance(data, list):
            spi_mem[_trbid][cable][asic] += data
        else:
            spi_mem[_trbid][cable][asic] += [data]

    else:
        if isinstance(data, list):
            my_data_list = spi_mem[_trbid][cable][asic] + data
        else:
            my_data_list = spi_mem[_trbid][cable][asic] + [data]

        spi_mem[_trbid][cable][asic].clear()  # empty queue

        spi_prepare(_trbid, cable, asic)

        for data in my_data_list:
            # writing one data word, append zero to the data word, the chip will get some more SCK clock cycles
            safe_command_w(_trbid, 0xd400, data << 4)

            # write 1 to length register to trigger sending
            safe_command_w(_trbid, 0xd411, 0x0001)


def spi_read(trbid, cable, asic):
    _trbid = trbid

    spi_prepare(_trbid, cable, asic)

    # write 1 to length register to trigger sending
    safe_command_r(_trbid, 0xd412)


def spi_prepare(trbid, cable, asic):
    _trbid = trbid

    # bring all CS (reset lines) in the default state (1) - upper four nibbles: invert CS, lower four nibbles: disable CS
    safe_command_w(_trbid, 0xd417, 0x0000FFFF)

    # (chip-)select output $CONN for i/o multiplexer reasons, remember CS lines are disabled
    safe_command_w(_trbid, 0xd410, 0xFFFF & (1 << (cable-1)))

    # override: (chip-) select all ports!!
    #trbcmd w $_trbid 0xd410 0xFFFF

    # override: (chip-) select nothing !!
    #trbcmd w $_trbid 0xd410 0x0000

    # disable all SDO outputs but output $CONN
    safe_command_w(_trbid, 0xd415, 0xFFFF & ~(1 << (cable-1)))

    # disable all SCK outputs but output $CONN
    safe_command_w(_trbid, 0xd416, 0xFFFF & ~(1 << (cable-1)))

    # override: disable all SDO and SCK lines
    #trbcmd w $_trbid 0xd415 0xFFFF
    #trbcmd w $_trbid 0xd416 0xFFFF