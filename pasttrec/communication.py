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
from colorama import Fore, Style

from pasttrec import hardware, g_verbose
from pasttrec.misc import trbaddr
from pasttrec.trb_spi import TrbTdcSpi

try:
    from trbnet import TrbNet
except ImportError:
    trbnet_available = False
    print("ERROR: Trbnet library not found.")
else:
    trbnet_available = True
    lib = os.getenv("LIBTRBNET")
    host = os.getenv("DAQOPSERVER")
    if g_verbose:
        print("INFO: Trbnet library found in {:s} at host {:s}".format(lib, host))

cmd_to_file = None  # if set to file, redirect output to this file
trbnet_interface_env = os.getenv("TRBNET_INTERFACE")

trbnet_interface = None

if trbnet_interface_env is not None:
    if trbnet_interface_env == "trbnet":
        from pasttrec.trbnet_com import TrbNetComLib
        trbnet_interface = TrbNetComLib()
    elif trbnet_interface_env == "shell":
        from pasttrec.trbnet_com import TrbNetComShell
        trbnet_interface = TrbNetComShell()
    elif trbnet_interface_env == "file":
        pass
        # import pasttrec.trb_comm.file as comm
    else:
        raise "TRBNET_INTERFACE is incorrect"
else:
    if trbnet_available:
        from pasttrec.trbnet_com import TrbNetComLib
        trbnet = TrbNet(libtrbnet=lib, daqopserver=host)
        trbnet_interface = TrbNetComLib(trbnet)
    elif cmd_to_file:
        from pasttrec.trbnet_com import TrbNetComShell
        trbnet_interface = TrbNetComShell()
    else:
        pass
        # import pasttrec.trb_comm.file as comm

# chip communication

trb_spi = TrbTdcSpi(trbnet_interface)


def detect_frontend(address):
    if type(address) == str:
        address = int(address, 16)

    rc = trbnet_interface.read(address, 0x42)

    try:
        return hardware.TrbFrontendTypeMapping[rc & 0xFFFF0000]
    except KeyError:
        print("FrontendTypeMapping not known for hardware type {:s} in {:s}".format(hex(rc), trbaddr(address)))
        return None


def decode_address_entry(string, sort=False):
    """
    Converts address into [ trbnet, cable, cable, asic ] tuples input string:
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
        return ()

    # check address
    address = sections[0]
    if len(address) == 6:
        if address[0:2] != "0x":
            print("Incorrect address in string: ", string)
            return ()
    elif len(address) == 4:
        address = "0x" + address
    else:
        print("Incorrect address in string: ", string)
        return ()

    try:
        trbfetype = detect_frontend(address)
    except ValueError:
        print(Fore.RED + f"Incorrect address {address}" + Style.RESET_ALL)
        return ()

    # do everything backwards
    # asics
    if sec_len == 3 and len(sections[2]) > 0:
        _asics = sections[2].split(",")
        asics = (int(a) - 1 for a in _asics if int(a) in range(1, trbfetype.asics))
    else:
        asics = tuple(range(trbfetype.asics))

    # asics
    if sec_len >= 2 and len(sections[1]) > 0:
        _cables = sections[1].split(",")
        cables = (int(c) - 1 for c in _cables if int(c) in range(1, trbfetype.cables))
    else:
        cables = tuple(range(trbfetype.cables))

    tup = ([int(address, 16)] + [y] + [z] for y in cables for z in asics)

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
        trbfetype = detect_frontend(addr)
        if trbfetype is None:
            continue

        if addr == _addr and cable == _cable:
            continue

        _addr = addr
        _cable = cable

        print(Fore.YELLOW + "Reseting {:s} cable {:d}".format(trbaddr(addr), cable) + Style.RESET_ALL)
        trb_spi.spi_reset(addr, cable)


def asics_to_defaults(address, def_pasttrec):
    """Set asics to defaults from config."""
    d = def_pasttrec.dump_config()
    for addr, cable, asic in address:
        write_data(addr, cable, asic, d)


def asic_to_defaults(address, cable, asic, def_pasttrec):
    """Set asics to defaults from config."""
    write_data(address, cable, asic, def_pasttrec.dump_config())


def read_rm_scalers(trbid, n_scalers):
    return trbnet_interface.read_mem(trbid, hardware.TrbRegisters.SCALERS.value, n_scalers)


def read_r_scalers(trbid, channel):
    return trbnet_interface.read(trbid, hardware.TrbRegisters.SCALERS.value + channel)


""" These functions write, read or rad memory for given cable and asic.
    They all call safe_command_ functions. """


def write_reg(trbfetype, trbid, cable, asic, reg, val):
    trbfetype.spi(trb_spi).reg_write(trbid, cable, asic, reg, val)


def read_reg(trbfetype, trbid, cable, asic, reg):
    return trbfetype.spi(trb_spi).reg_read(trbid, cable, asic, reg)


def write_data(trbfetype, trbid, cable, asic, data):
    trbfetype.spi(trb_spi).reg_write_data(trbid, cable, asic, data)


def write_chunk(trbfetype, trbid, cable, asic, data):
    trbfetype.spi(trb_spi).reg_write_chunk(trbid, cable, asic, data)


""" SPI protocol function. """

spi_queue = 0
spi_mem = {}

# use these to check whether the short break is need

last_trb = None
last_asic = None
same_cable_delay = 0.0
