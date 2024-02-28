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
from colorama import Fore, Style

from pasttrec import hardware, g_verbose
from pasttrec.misc import trbaddr
from pasttrec.trb_spi import SpiTrbTdc


"""Try to import TrbNet library"""
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


"""
Env TRBNET_INTERFACE controls which backend to use for communication.
Default one is libtrbnet.
"""
if trbnet_interface_env is not None:
    if trbnet_interface_env == "trbnet":
        trbnet = TrbNet(libtrbnet=lib, daqopserver=host)

        from pasttrec.interface import TrbNetComLib

        trbnet_interface = TrbNetComLib(trbnet)

    elif trbnet_interface_env == "shell":
        from pasttrec.interface import TrbNetComShell

        trbnet_interface = TrbNetComShell()

    elif trbnet_interface_env == "file":
        pass
        # import pasttrec.trb_comm.file as comm
    else:
        raise "TRBNET_INTERFACE is incorrect"
else:
    if trbnet_available:
        trbnet = TrbNet(libtrbnet=lib, daqopserver=host)

        from pasttrec.interface import TrbNetComLib

        trbnet_interface = TrbNetComLib(trbnet)

    elif cmd_to_file:
        from pasttrec.interface import TrbNetComShell

        trbnet_interface = TrbNetComShell()

    else:
        pass
        # import pasttrec.trb_comm.file as comm


def detect_design(address):
    """Detect the Trb board type"""

    if type(address) == str:
        address = int(address, 16)

    rc = trbnet_interface.read(address, 0x42)

    try:
        return hardware.TrbBoardTypeMapping[rc & 0xFFFF0000]
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
            print("Incorrect address in string: ", string, file=sys.stderr)
            return ()
    elif len(address) == 4:
        address = "0x" + address
    else:
        print("Incorrect address in string: ", string, file=sys.stderr)
        return ()

    try:
        trb_fe_type = detect_design(address)
        if trb_fe_type is None:
            return ()
    except ValueError:
        print(Fore.RED + f"Incorrect address {address}" + Style.RESET_ALL, file=sys.stderr)
        return ()

    # do everything backwards
    # asics
    if sec_len == 3 and len(sections[2]) > 0:
        _asics = sections[2].split(",")
        asics = (int(a) for a in _asics if int(a) in range(0, trb_fe_type.asics))  # TODO add 1-2 mode
    else:
        asics = tuple(range(trb_fe_type.asics))

    # asics
    if sec_len >= 2 and len(sections[1]) > 0:
        _cables = sections[1].split(",")
        cables = (int(c) for c in _cables if int(c) in range(0, trb_fe_type.cables))  # TODO add 1-4 mode
    else:
        cables = tuple(range(trb_fe_type.cables))

    return tuple((int(address, 16), y, z) for y in cables for z in asics)


def decode_address(string):
    """Use this for a single string or list of strings."""

    if type(string) is str:
        return decode_address_entry(string)
    else:
        return sum((decode_address_entry(s) for s in string), ())


def filter_raw_trbids(addresses):
    """Return list of unique trbnet addresses."""

    return tuple(set((int(x.split(":")[0], 16) for x in addresses)))


def filter_decoded_trbids(addresses):
    """Return list of unique trbnet addresses."""

    return tuple(set(trbid for trbid, *_ in addresses))


def filter_decoded_cables(addresses):
    """Return list of unique trbnet ctrbids."""
    return tuple(set((trbid, cable) for trbid, cable, *_ in addresses))


def group_cables(ctrbids_tuple: tuple):
    min_c = min(ctrbids_tuple, key=lambda tup: tup[1])[1]
    max_c = max(ctrbids_tuple, key=lambda tup: tup[1])[1]

    def tup_group(c, ct):
        return tuple(tup for tup in ct if tup[1] == c)

    return tuple(sort_by_trbid(tup_group(x, ctrbids_tuple)) for x in range(min_c, max_c + 1))


def sort_by_cable(xtrbids_tuple: tuple):
    return tuple(sorted(xtrbids_tuple, key=lambda tup: (tup[1], tup[0])))


def sort_by_ct(xtrbids_tuple: tuple):
    return tuple(sorted(xtrbids_tuple, key=lambda tup: (tup[1], tup[0])))


def sort_by_tc(xtrbids_tuple: tuple):
    return tuple(sorted(xtrbids_tuple, key=lambda tup: (tup[0], tup[1])))


def sort_by_trbid(xtrbids_tuple: tuple):
    return tuple(sorted(xtrbids_tuple, key=lambda tup: tup[0]))


def get_trb_design_type(trbnetids):
    trb_design_type = {}
    for trbid in trbnetids:
        trb_design_type[trbid] = detect_design(trbid)
    return trb_design_type


def print_verbose(rc):
    cmd = " ".join(rc.args)
    rtc = rc.returncode

    if g_verbose >= 1:
        print("[{:d}]  {:s}".format(rtc, cmd))


class CardConnection:
    """These functions write, read memory for given cable and asic."""

    shared_trb_spi = {}
    encoder = hardware.PasttrecDataWordEncoder()

    def __init__(self, trb_frontend, trbid, cable):
        if not isinstance(trb_frontend, hardware.TrbBoardType):
            raise TypeError("Must be of TrbBoardType type")

        self.trb_fe_type = trb_frontend
        self.trbid = trbid
        self.cable = cable

        if trbid not in self.shared_trb_spi:
            self.shared_trb_spi[trbid] = self.trb_fe_type.spi(trbnet_interface, trbid)
        self.trb_spi = self.shared_trb_spi[trbid]

    @property
    def fetype(self):
        return self.trb_fe_type

    @property
    def spi(self):
        return self.trb_spi

    @property
    def address(self):
        return (self.trbid, self.cable)

    def read_1wire_temp(self):
        return self.trb_spi.read_1wire_temp(self.cable)

    def read_1wire_id(self):
        return self.trb_spi.read_1wire_id(self.cable)

    def activate_1wire(self):
        return self.trb_spi.activate_1wire(self.cable)

    def get_1wire_temp(self):
        return self.trb_spi.get_1wire_temp(self.cable)

    def get_1wire_id(self):
        return self.trb_spi.get_1wire_id(self.cable)

    def reset_spi(self):
        self.trb_spi.spi_reset(self.cable)

    def __str__(self):
        return f"Frontend connection to {trbaddr(self.trbid)} for cable={self.cable}"


def make_cable_connections(address):
    """Make instances of CardConenction based on the decoded addresses."""

    filtered_cables = filter_decoded_cables(address)
    sorted_cables = sort_by_cable(filtered_cables)

    fee_types = get_trb_design_type(filter_decoded_trbids(address))

    return tuple(
        CardConnection(fee_types[addr], addr, cable) for addr, cable in sorted_cables if fee_types[addr] is not None
    )


class PasttrecConnection(CardConnection):
    """These functions write, read memory for given cable and asic."""

    trb_fe_type = None
    trbid = None
    cable = None
    asic = None

    encoder = hardware.PasttrecDataWordEncoder()

    def __init__(self, trb_frontend, trbid, cable, asic):
        CardConnection.__init__(self, trb_frontend, trbid, cable)

        self.asic = asic

    def write_reg(self, reg, val):
        word = self.encoder.write(self.asic, reg, val)
        self.trb_spi.write(self.cable, word)

    def read_reg(self, reg):
        word = self.encoder.read(self.asic, reg)
        return self.trb_spi.read(self.cable, word << 1)

    def write_data(self, data):
        word = self.encoder.write_data(self.asic, data)
        self.trb_spi.write_data(self.cable, word)

    def write_chunk(self, data):
        word = self.encoder.write_chunk(self.asic, data)
        self.trb_spi.write_chunk(self.cable, word)

    def reset_asic(self):
        word = self.encoder.reset(self.asic)
        self.trb_spi.write(self.cable, word << 1)

    def __str__(self):
        return f"Pasttrec connection to {trbaddr(self.trbid)} for cable={self.cable} asic={self.asic}"


def make_asic_connections(address):
    """Make instances of PasttercConenction based on the decoded addresses."""

    fee_types = get_trb_design_type(filter_decoded_trbids(address))
    return tuple(
        PasttrecConnection(fee_types[addr], addr, cable, asic)
        for addr, cable, asic in address
        if fee_types[addr] is not None
    )


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
