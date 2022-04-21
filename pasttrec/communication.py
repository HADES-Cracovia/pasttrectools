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
    #trbnet_available = True
    trbnet = None
    print("INFO: Trbnet library not found.")
else:
    trbnet_available = True
    #lib = '/trbnettools/trbnetd/libtrbnet.so'
    lib = '/home/panda/trb/trbnettools/libtrbnet/libtrbnet.so'
    host = os.getenv("DAQOPSERVER")
    trbnet = TrbNet(libtrbnet=lib, daqopserver=host)
    print("INFO: Trbnet library found at {:s}", host)

# chip communication

def_scalers_reg = 0xc001
def_pastrec_channels_all = PasttrecDefaults.channels_num * \
    len(PasttrecDefaults.c_asic) * len(PasttrecDefaults.c_cable)

cmd_to_file = None  # if set to file, redirect output to this file


def decode_address_entry(string):
    """Converts address into [ trbnet, cable, cable, asic ] tuples
    input string:
    AAAAAA[:B[:C]]
      AAAAAA - trbnet address, can be in form 0xAAAA or AAAA
      B - cable: 1, 2, 3, or empty ("", all cables), or two or three cables
          comma separated
      C - asic: 1 or 2 or empty ("", all asics)
     any higher section of the address can be skipped
    examples:
     0x6400 - all cables and asics
     0x6400::2 - all cables, asic 2
     """

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
        asics = [int(a)-1 for a in _asics if int(a) in range(1, 3)]
    else:
        asics = [0, 1]

    # asics
    cables = []
    if sec_len >= 2 and len(sections[1]) > 0:
        _cables = sections[1].split(",")
        cables = [int(c)-1 for c in _cables if int(c) in range(1, 5)]
    else:
        cables = [0, 1, 2, 3]

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

    tup = [[x] + [y] + [z] for x in [address, ] for y in cables for z in asics]
    #print(tup)
    return tup


def decode_address(string):
    """Use this for a single string or list of strings."""
    if type(string) is str:
        return decode_address_entry(string)
    else:
        tup = []
        for s in string:
            tup += decode_address_entry(s)
        return tup


def print_verbose(rc):
    cmd = ' '.join(rc.args)
    rtc = rc.returncode

    if g_verbose >= 1:
        print("[{:d}]  {:s}".format(rtc, cmd))


def reset_asic(address, verbose=False):
    """Send reset signal to asic, resets all registers to defaults."""
    if type(address) is not list:
        a = decode_address(address)
    else:
        a = address

    _addr = None
    _cable = None
    for addr, cable, asic in a:
        if addr == _addr and cable == _cable:
            continue

        _addr = addr
        _cable = cable

        print(
            Fore.YELLOW + "Reseting {:s} cable {:d}"
                .format(addr, cable) + Style.RESET_ALL)
        spi_reset(addr, cable)
        
def read_temp(address, verbose=False):
    if type(address) is not list:
        a = decode_address(address)
    else:
        a = address

    _addr = None
    _cable = None
    for addr, cable, asic in a:
        if addr == _addr and cable == _cable:
            continue

        _addr = addr
        _cable = cable
        out = wire_temp(addr, cable)
        print(Fore.YELLOW + "Temperature in {:s} cable {:d} is\t:\t".format(addr, cable) + Style.RESET_ALL+ Fore.GREEN + "{:s}".format(out) + Style.RESET_ALL)
        
        #print(out)
        
def read_id(address, verbose=False):
    if type(address) is not list:
        a = decode_address(address)
    else:
        a = address

    _addr = None
    _cable = None
    for addr, cable, asic in a:
        if addr == _addr and cable == _cable:
            continue

        _addr = addr
        _cable = cable
        
        out= wire_id(addr, cable)
        print(Fore.YELLOW + "Chip ID in {:s} cable {:d} is\t\t:\t".format(addr, cable) + Style.RESET_ALL + Fore.GREEN + "{:s}".format(out) + Style.RESET_ALL)
        
        #print(out)


def asics_to_defaults(address, def_pasttrec):
    """Set asics to defaults from config."""
    d = def_pasttrec.dump_config()
    for addr, cable, asic in address:
        write_data(addr, cable, asic, d)


def asic_to_defaults(address, cable, asic, def_pasttrec):
    """Set asics to defaults from config."""
    write_data(address, cable, asic, d)


def read_rm_scalers(address):
    return safe_command_rm(address, def_scalers_reg, def_pastrec_channels_all)


def read_r_scalers(address, channel):
    return safe_command_r(address, def_scalers_reg + channel)


""" These functions write, read or rad memory for given cable and asic.
    They all call safe_command_ functions. """


def write_reg(trbid, cable, asic, reg, val):
    _c = PasttrecDefaults.c_cable[cable]
    _a = PasttrecDefaults.c_asic[asic]
    _b = PasttrecDefaults.c_base_w | _c | _a
    v = _b | (reg << 8) | val
    spi_write(trbid, cable, asic, v)


def read_reg(trbid, cable, asic, reg):
    _c = PasttrecDefaults.c_cable[cable]
    _a = PasttrecDefaults.c_asic[asic]
    _b = PasttrecDefaults.c_base_r | _c | _a
    v = _b | (reg << 8)
    spi_write(trbid, cable, asic, v << 1)
    return spi_read(trbid, cable, asic, v)


def write_data(trbid, cable, asic, data):
    _c = PasttrecDefaults.c_cable[cable]
    _a = PasttrecDefaults.c_asic[asic]
    _b = PasttrecDefaults.c_base_w | _c | _a

    if isinstance(data, list):
        v = [_b | x for x in data]
    else:
        v = _b | data
    spi_write(trbid, cable, asic, v)


def write_chunk(trbid, cable, asic, data):
    _c = PasttrecDefaults.c_cable[cable]
    _a = PasttrecDefaults.c_asic[asic]
    _b = PasttrecDefaults.c_base_w | _c | _a

    if isinstance(data, list):
        v = [_b | x for x in data]
    else:
        v = _b | data
    spi_write_chunk(trbid, cable, asic, v)


""" Safe commands are etsting for trbnet librray and choose between
    the librray or the shell. """


def safe_command_w(trbid, reg, data):
    if isinstance(trbid, int):
        _trbid = hex(trbid)
    else:
        _trbid = trbid

    if trbnet_available and cmd_to_file is not None:
        return trbnet_command_w(_trbid, reg, data)
    else:
        return shell_command_w(_trbid, reg, data)


def safe_command_wm(trbid, reg, data, mode):
    if isinstance(trbid, int):
        _trbid = hex(trbid)
    else:
        _trbid = trbid

    if trbnet_available and cmd_to_file is not None:
        return trbnet_command_wm(_trbid, reg, data, mode)
    else:
        return shell_command_wm(_trbid, reg, data, mode)


def safe_command_r(trbid, reg):
    if isinstance(trbid, int):
        _trbid = hex(trbid)
    else:
        _trbid = trbid

    if trbnet_available and cmd_to_file is not None:
        return trbnet_command_r(_trbid, reg)
    else:
        return shell_command_r(_trbid, reg)


def safe_command_rm(trbid, reg, length):
    if isinstance(trbid, int):
        _trbid = hex(trbid)
    else:
        _trbid = trbid

    if trbnet_available and cmd_to_file is not None:
        return trbnet_command_rm(_trbid, reg, length)
    else:
        return shell_command_rm(_trbid, reg, length)


""" These functions are shell functions. """


def shell_command_w(trbid, reg, data):
    cmd = ['trbcmd', 'w', trbid, hex(reg), hex(data)]

    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True

    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def shell_command_wm(trbid, reg, data, mode):
    if cmd_to_file is not None:
        cmd = ['trbcmd', 'wm', trbid, hex(reg), str(mode), '- << EOF']
        cmd_to_file.write(' '.join(cmd) + '\n')
        for d in data:
            cmd_to_file.write(hex(d) + '\n')
        cmd_to_file.write('EOF\n')
        return True

    cmd = ['trbcmd', 'wm', trbid, hex(reg), str(mode), '-']
    _data = "\n".join([hex(x) for x in data])
    rc = subprocess.run(cmd, input=_data.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def shell_command_r(trbid, reg):
    cmd = ['trbcmd', 'r', trbid, hex(reg)]

    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True

    rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print_verbose(rc)
    return rc.stdout.decode()


def shell_command_rm(trbid, reg, length):
    cmd = ['trbcmd', 'rm', trbid, hex(reg), str(length), '0']

    if cmd_to_file is not None:
        cmd_to_file.write(' '.join(cmd) + '\n')
        return True

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


def spi_fill_buffer(trbid, cable, asic, data):
    if trbid not in spi_mem:
        spi_mem[trbid] = {}
    if cable not in spi_mem[trbid]:
        spi_mem[trbid][cable] = {}
    if asic not in spi_mem[trbid][cable]:
        spi_mem[trbid][cable][asic] = []

    if isinstance(data, list):
        spi_mem[trbid][cable][asic] += data
    else:
        spi_mem[trbid][cable][asic] += [data]


def spi_write(trbid, cable, asic, data):
    spi_fill_buffer(trbid, cable, asic, data)

    if not spi_queue:
        my_data_list = spi_mem[trbid][cable][asic].copy()
        spi_mem[trbid][cable][asic].clear()  # empty queue

        spi_prepare(trbid, cable, asic)

        for data in my_data_list:
            # writing one data word, append zero to the data word, the chip
            # will get some more SCK clock cycles
            safe_command_w(trbid, 0xd400, data)
            # write 1 to length register to trigger sending
            safe_command_w(trbid, 0xd411, 0x0001)


def spi_write_chunk(trbid, cable, asic, data):
    spi_fill_buffer(trbid, cable, asic, data)

    if not spi_queue:
        my_data_list = spi_mem[trbid][cable][asic].copy()
        spi_mem[trbid][cable][asic].clear()  # empty queue

        spi_prepare(trbid, cable, asic)

        for d in miscellaneous.chunks(my_data_list, 16):
            i = 0
            safe_command_wm(trbid, 0xd400, my_data_list, 0)
            #for val in d:
                # writing one data word, append zero to the data word, the chip
                # will get some more SCK clock cycles
                #safe_command_w(trbid, 0xd400 + i, val)
                #i = i + 1

            # write  length register to trigger sending
            safe_command_w(trbid, 0xd411, len(d))


def spi_read(trbid, cable, asic, data):
    return safe_command_r(trbid, 0xd412)


def spi_prepare(trbid, cable, asic):
    # bring all CS (reset lines) in the default state (1) - upper four nibbles:
    # invert CS, lower four nibbles: disable CS
    safe_command_w(trbid, 0xd417, 0x0000FFFF)

    # (chip-)select output $CONN for i/o multiplexer reasons, remember CS lines
    # are disabled
    safe_command_w(trbid, 0xd410, 0xFFFF & (1 << cable))

    # override: (chip-) select all ports!!
    # trbcmd w $trbid 0xd410 0xFFFF

    # override: (chip-) select nothing !!
    # trbcmd w $trbid 0xd410 0x0000

    # disable all SDO outputs but output $CONN
    safe_command_w(trbid, 0xd415, 0xFFFF & ~(1 << cable))

    # disable all SCK outputs but output $CONN
    safe_command_w(trbid, 0xd416, 0xFFFF & ~(1 << cable))

    # override: disable all SDO and SCK lines
    # trbcmd w $trbid 0xd415 0xFFFF
    # trbcmd w $trbid 0xd416 0xFFFF


def spi_reset(trbid, cable):
    # bring all CS (reset lines) in the default state (1) - upper four nibbles:
    # invert CS, lower four nibbles: disable CS
    safe_command_w(trbid, 0xd417, 0x0000FFFF)
    # and bring down selected bit
    safe_command_w(trbid, 0xd417, 0xFFFFFFFF & (0x10000 << cable))

    # generate 25 clock cycles
    for c in range(25):
        #safe_command_w(trbid, 0xd416, 0xFFFF0000 & (0x10000 << cable))
        safe_command_w(trbid, 0xd416, 0xFFFF0000 & (0xF0000))
        safe_command_w(trbid, 0xd416, 0x00000000)

    # restore default CS
    safe_command_w(trbid, 0xd417, 0x0000FFFF)
     

def wire_temp(trbid, cable): #non mux| dedicated 1wire component for each connector/cable
    for c in range(4):
        safe_command_w(trbid, 0xd416, 0xFFFF0000 & (0xF0000))
        safe_command_w(trbid, 0xd416, 0x00000000)
    
    safe_command_w(trbid, 0x23, (0x0001 << cable+1 | 0x0001))
    sleep(2)
    rc = safe_command_r(trbid, 0x8)     
    res = int(rc.split()[1], 16)
    out = hex(res & 0xffff0000)[0:5]
    safe_command_w(trbid, 0x23, 0x0)

    #safe_command_w(trbid, 0x23, (0x1 << cable+1)) #muxed 1wire component for connectors/cables
    #sleep(2)
    #rc = safe_command_r(trbid, 0x8)
    #res = int(rc.split()[1], 16)
    #out = hex(res & 0xffff0000)[0:5]
    #safe_command_w(trbid, 0x23, 0x0)
    return out
    
    
def wire_id(trbid, cable): #non mux| dedicated 1wire component for each connector/cable
    for c in range(4):
        safe_command_w(trbid, 0xd416, 0xFFFF0000 & (0xF0000))
        safe_command_w(trbid, 0xd416, 0x00000000)
    
    safe_command_w(trbid, 0x23, (0x0001 << cable+1 | 0x0001))
    sleep(2)
    rc0 = safe_command_r(trbid, 0xa)
    rc1 = safe_command_r(trbid, 0xb)
    res0 = int(rc0.split()[1], 16)
    res1 = int(rc1.split()[1], 16)
    out = hex( (res1<<32) | res0 )
    safe_command_w(trbid, 0x23, 0x0)
    
    #safe_command_w(trbid, 0x23, (0x1 << cable+1)) #muxed 1wire component for connectors/cables
    #sleep(2)
    #rc0 = safe_command_r(trbid, 0xa)
    #rc1 = safe_command_r(trbid, 0xb)
    #res0 = int(rc0.split()[1], 16)
    #res1 = int(rc1.split()[1], 16)
    #out = hex( (res1<<32) | res0 )
    #safe_command_w(trbid, 0x23, 0x0)
    
    
    return out
