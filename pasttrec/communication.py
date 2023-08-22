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
import time
from colorama import Fore, Style

from pasttrec import hardware, misc, g_verbose
from pasttrec.misc import trbaddr

try:
    from trbnet import TrbNet
except ImportError:
    trbnet_available = False
    trbnet = None
    print("ERROR: Trbnet library not found.")
else:
    trbnet_available = True
    lib = os.getenv("LIBTRBNET")
    host = os.getenv("DAQOPSERVER")
    trbnet = TrbNet(libtrbnet=lib, daqopserver=host)
    if g_verbose:
        print("INFO: Trbnet library found in {:s} at host {:s}".format(lib, host))

cmd_to_file = None  # if set to file, redirect output to this file
comm_driver = os.getenv("PASTTREC_COMM_DRIVER")

if comm_driver is not None:
    if comm_driver == "trbnet":
        import pasttrec.trb_comm.libtrbnet as comm
    elif comm_driver == "shell":
        import pasttrec.trb_comm.shell as comm
    elif comm_driver == "file":
        import pasttrec.trb_comm.file as comm
    else:
        raise "PASTTREC_COMM_DRIVER is incorrect"
else:
    if trbnet_available:
        import pasttrec.trb_comm.libtrbnet as comm
    elif cmd_to_file:
        import pasttrec.trb_comm.file as comm
    else:
        import pasttrec.trb_comm.shell as comm

# chip communication


def detect_frontend(address):
    if type(address) == str:
        address = int(address, 16)

    rc = safe_command_r(address, 0x42)
    try:
        return hardware.TrbFrontendTypeMapping[rc & 0xFFFF0000]
    except KeyError:
        print("FrontendTypeMapping not known for hardware type {:s} in {:s}".format(hex(rc), trbaddr(address)))
        return None


def decode_address_entry(string, sort=False):
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

    trbfetype = detect_frontend(address)

    # do everything backwards
    # asics
    asics = []
    if sec_len == 3 and len(sections[2]) > 0:
        _asics = sections[2].split(",")
        asics = [int(a) - 1 for a in _asics if int(a) in range(1, trbfetype.asics)]
    else:
        asics = list(range(trbfetype.asics))

    # asics
    cables = []
    if sec_len >= 2 and len(sections[1]) > 0:
        _cables = sections[1].split(",")
        cables = [int(c) - 1 for c in _cables if int(c) in range(1, trbfetype.cables)]
    else:
        cables = list(range(trbfetype.cables))

    tup = [[int(address, 16)] + [y] + [z] for y in cables for z in asics]

    return tup


def decode_address(string, sort=False):
    """Use this for a single string or list of strings."""
    if type(string) is str:
        return decode_address_entry(string, sort)
    else:
        tup = []
        for s in string:
            tup += decode_address_entry(s, sort)
        return tup


def print_verbose(rc):
    cmd = " ".join(rc.args)
    rtc = rc.returncode

    if g_verbose >= 1:
        print("[{:d}]  {:s}".format(rtc, cmd))


def reset_asic(address, verbose=False):
    """Send reset signal to asic, resets all registers to defaults."""
    if type(address) is not list:
        a = decode_address(address, True)
    else:
        a = address

    _addr = None
    _cable = None
    for addr, cable, asic in a:
        if addr == _addr and cable == _cable:
            continue

        _addr = addr
        _cable = cable

        print(Fore.YELLOW + "Reseting {:s} cable {:d}".format(trbaddr(addr), cable) + Style.RESET_ALL)
        spi_reset(addr, cable)


def asics_to_defaults(address, def_pasttrec):
    """Set asics to defaults from config."""
    d = def_pasttrec.dump_config()
    for addr, cable, asic in address:
        write_data(addr, cable, asic, d)


def asic_to_defaults(address, cable, asic, def_pasttrec):
    """Set asics to defaults from config."""
    write_data(address, cable, asic, def_pasttrec.dump_config())


def read_rm_scalers(trbid, n_scalers):
    return safe_command_rm(trbid, hardware.TrbRegisters.SCALERS.value, n_scalers)


def read_r_scalers(trbid, channel):
    return safe_command_r(trbid, hardware.TrbRegisters.SCALERS.value + channel)


""" These functions write, read or rad memory for given cable and asic.
    They all call safe_command_ functions. """


def write_reg(trbid, cable, asic, reg, val):
    _a = hardware.TrbRegistersOffsets.c_asic[asic]
    _b = hardware.TrbRegistersOffsets.c_base_w | _a
    v = _b | (reg << 8) | val
    spi_write(trbid, cable, asic, v)


def read_reg(trbid, cable, asic, reg):
    _a = hardware.TrbRegistersOffsets.c_asic[asic]
    _b = hardware.TrbRegistersOffsets.c_base_r | _a
    v = _b | (reg << 8)
    spi_write(trbid, cable, asic, v << 1)
    return spi_read(trbid, cable, asic, v)


def write_data(trbid, cable, asic, data):
    _a = hardware.TrbRegistersOffsets.c_asic[asic]
    _b = hardware.TrbRegistersOffsets.c_base_w | _a

    if isinstance(data, list):
        v = [_b | x for x in data]
    else:
        v = _b | data
    spi_write(trbid, cable, asic, v)


def write_chunk(trbid, cable, asic, data):
    _a = hardware.TrbRegistersOffsets.c_asic[asic]
    _b = hardware.TrbRegistersOffsets.c_base_w | _a

    if isinstance(data, list):
        v = [_b | x for x in data]
    else:
        v = _b | data
    spi_write_chunk(trbid, cable, asic, v)


""" Safe commands are etsting for trbnet librray and choose between
    the librray or the shell. """


def safe_command_w(trbid: int, reg: int, data: int):
    return comm.command_w(trbnet, trbid, reg, data)


def safe_command_wm(trbid: int, reg: int, data: int, mode: int):
    return comm.command_wm(trbnet, trbid, reg, data, mode)


def safe_command_r(trbid: int, reg: int):
    return comm.command_r(trbnet, trbid, reg)


def safe_command_rm(trbid: int, reg: int, length: int):
    return comm.command_rm(trbnet, trbid, reg, length)


""" SPI protocol function. """

spi_queue = 0
spi_mem = {}

# use these to check whether the short break is need

last_trb = None
last_asic = None
same_cable_delay = 0.0

""" Based on GSI code from M. Wiebusch """


def spi_fill_buffer(trbid, cable, asic, data):
    global spi_mem

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
    global last_trb
    global last_asic
    global same_cable_delay

    if last_asic != asic and last_trb and last_trb == trbid:
        time.sleep(same_cable_delay)

    last_trb = trbid
    last_asic = asic

    spi_fill_buffer(trbid, cable, asic, data)

    if not spi_queue:
        my_data_list = spi_mem[trbid][cable][asic].copy()
        spi_mem[trbid][cable][asic].clear()  # empty queue

        spi_prepare(trbid, cable, asic)

        for data in my_data_list:
            # writing one data word, append zero to the data word, the chip
            # will get some more SCK clock cycles
            safe_command_w(trbid, 0xD400, data)
            # write 1 to length register to trigger sending
            safe_command_w(trbid, 0xD411, 0x0001)


def spi_write_chunk(trbid, cable, asic, data):
    global last_trb
    global last_asic
    global same_cable_delay

    spi_fill_buffer(trbid, cable, asic, data)

    if not spi_queue:
        my_data_list = spi_mem[trbid][cable][asic].copy()
        spi_mem[trbid][cable][asic].clear()  # empty queue

        if last_asic != asic and last_trb and last_trb == trbid:
            time.sleep(same_cable_delay)

        last_trb = trbid
        last_asic = asic

        # print(trbid, cable, asic)
        spi_prepare(trbid, cable, asic)

        for d in misc.chunks(my_data_list, 16):
            # i = 0
            safe_command_wm(trbid, 0xD400, my_data_list, 0)
            # for val in d:
            #    # writing one data word, append zero to the data word, the chip
            #    # will get some more SCK clock cycles
            #    safe_command_w(trbid, 0xd400 + i, val)
            #    i = i + 1

            # write  length register to trigger sending
            safe_command_w(trbid, 0xD411, len(d))


def spi_read(trbid, cable, asic, data):
    return safe_command_r(trbid, 0xD412)


def spi_prepare(trbid, cable, asic):
    # bring all CS (reset lines) in the default state (1) - upper four nibbles:
    # invert CS, lower four nibbles: disable CS
    safe_command_w(trbid, 0xD417, 0x0000FFFF)

    # (chip-)select output $CONN for i/o multiplexer reasons, remember CS lines
    # are disabled
    safe_command_w(trbid, 0xD410, 0xFFFF & (1 << cable))

    # override: (chip-) select all ports!!
    # trbcmd w $trbid 0xd410 0xFFFF

    # override: (chip-) select nothing !!
    # trbcmd w $trbid 0xd410 0x0000

    # disable all SDO outputs but output $CONN
    safe_command_w(trbid, 0xD415, 0xFFFF & ~(1 << cable))

    # disable all SCK outputs but output $CONN
    safe_command_w(trbid, 0xD416, 0xFFFF & ~(1 << cable))

    # override: disable all SDO and SCK lines
    # trbcmd w $trbid 0xd415 0xFFFF
    # trbcmd w $trbid 0xd416 0xFFFF


def spi_reset(trbid, cable):
    # bring all CS (reset lines) in the default state (1) - upper four nibbles:
    # invert CS, lower four nibbles: disable CS
    safe_command_w(trbid, 0xD417, 0x0000FFFF)
    # and bring down selected bit
    safe_command_w(trbid, 0xD417, 0xFFFFFFFF & (0x10000 << cable))

    # generate 25 clock cycles
    for c in range(25):
        safe_command_w(trbid, 0xD416, 0xFFFF0000 & (0x10000 << cable))
        safe_command_w(trbid, 0xD416, 0x00000000)

    # restore default CS
    safe_command_w(trbid, 0xD417, 0x0000FFFF)
