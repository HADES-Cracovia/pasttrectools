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


"""Env TRBNET_INTERFACE controls which backend to use for communication.
   Default one is libtrbnet."""
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


def detect_frontend(address):
    """Detect the Trb board type"""
    if type(address) == str:
        address = int(address, 16)

    rc = trbnet_interface.read(address, 0x42)

    try:
        return hardware.TrbBoardTypeMapping[rc & 0xFFFF0000]
    except KeyError:
        print(
            "FrontendTypeMapping not known for hardware type {:s} in {:s}".format(
                hex(rc), trbaddr(address)
            )
        )
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
        trb_fe_type = detect_frontend(address)
        if trb_fe_type is None:
            return ()
    except ValueError:
        print(Fore.RED + f"Incorrect address {address}" + Style.RESET_ALL)
        return ()

    # do everything backwards
    # asics
    if sec_len == 3 and len(sections[2]) > 0:
        _asics = sections[2].split(",")
        asics = (int(a) - 1 for a in _asics if int(a) in range(1, trb_fe_type.asics))
    else:
        asics = tuple(range(trb_fe_type.asics))

    # asics
    if sec_len >= 2 and len(sections[1]) > 0:
        _cables = sections[1].split(",")
        cables = (int(c) - 1 for c in _cables if int(c) in range(1, trb_fe_type.cables))
    else:
        cables = tuple(range(trb_fe_type.cables))

    return tuple((int(address, 16), y, z) for y in cables for z in asics)


def decode_address(string, sort=False):
    """Use this for a single string or list of strings."""
    if type(string) is str:
        return decode_address_entry(string, sort)
    else:
        return sum((decode_address_entry(s, sort) for s in string), ())


def filter_raw_trbids(addresses, sort=False):
    """Return list of unique trbnet addresses."""
    return tuple(set((int(x.split(":")[0], 16) for x in addresses)))


def filter_decoded_trbids(addresses, sort=False):
    """Return list of unique trbnet addresses."""
    return tuple(set(trbid for trbid, cable, asic in addresses))


def filter_decoded_cables(addresses, sort=False):
    """Return list of unique trbnet addresses."""
    return tuple(set((trbid, cable) for trbid, cable, asic in addresses))


def get_trbfetype(trbnetids):
    trbfetype = {}
    for trbid in trbnetids:
        trbfetype[trbid] = detect_frontend(trbid)
    return trbfetype


def print_verbose(rc):
    cmd = " ".join(rc.args)
    rtc = rc.returncode

    if g_verbose >= 1:
        print("[{:d}]  {:s}".format(rtc, cmd))


class CardConnection:
    """These functions write, read memory for given cable and asic."""

    trb_fe_type = None
    trbid = None
    cable = None

    spi = SpiTrbTdc(trbnet_interface)  # chip communication
    encoder = hardware.PasttrecDataWordEncoder()

    def __init__(self, trb_frontend, trbid, cable):
        if not isinstance(trb_frontend, hardware.TrbBoardType):
            raise TypeError("Must be of TrbBoardType type")

        self.trb_fe_type = trb_frontend
        self.trbid = trbid
        self.cable = cable

    @property
    def fetype(self):
        return self.trb_fe_type

    def read_wire_temp(self):
        return self.trb_fe_type.spi(trbnet_interface).read_wire_temp(
            self.trbid, self.cable
        )

    def read_wire_id(self):
        return self.trb_fe_type.spi(trbnet_interface).read_wire_id(
            self.trbid, self.cable
        )

    def __str__(self):
        return f"Frontend connection to {trbaddr(self.trbid)} for cable={self.cable}"


def make_cable_connections(address):
    """Make instances of CardConenction based on the decoded addresses."""

    filtered_trbids = filter_decoded_trbids(address)
    filtered_cables = filter_decoded_cables(address)
    fee_types = get_trbfetype(filter_decoded_trbids(address))

    return tuple(
        CardConnection(fee_types[addr], addr, cable)
        for addr, cable in filtered_cables
        if fee_types[addr] is not None
    )


class PasttrecConnection(CardConnection):
    """These functions write, read memory for given cable and asic."""

    trb_fe_type = None
    trbid = None
    cable = None
    asic = None

    spi = SpiTrbTdc(trbnet_interface)  # chip communication
    encoder = hardware.PasttrecDataWordEncoder()

    def __init__(self, trb_frontend, trbid, cable, asic):
        CardConnection.__init__(self, trb_frontend, trbid, cable)

        self.asic = asic

    def write_reg(self, reg, val):
        word = self.encoder.write(self.asic, reg, val)
        self.trb_fe_type.spi(trbnet_interface).write(self.trbid, self.cable, word)

    def read_reg(self, reg):
        word = self.encoder.read(self.asic, reg)
        self.trb_fe_type.spi(trbnet_interface).write(self.trbid, self.cable, word << 1)
        return self.trb_fe_type.spi(trbnet_interface).read(self.trbid)

    def write_data(self, data):
        word = self.encoder.write_data(self.asic, data)
        self.trb_fe_type.spi(trbnet_interface).write_data(self.trbid, self.cable, word)

    def write_chunk(self, data):
        word = self.encoder.write_chunk(self.asic, data)
        self.trb_fe_type.spi(trbnet_interface).write_chunk(self.trbid, self.cable, word)

    def __str__(self):
        return f"Pasttrec connection to {trbaddr(self.trbid)} for cable={self.cable} asic={self.asic}"


def make_asic_connections(address):
    """Make instances of PasttercConenction based on the decoded addresses."""

    fee_types = get_trbfetype(filter_decoded_trbids(address))
    return tuple(
        PasttrecConnection(fee_types[addr], addr, cable, asic)
        for addr, cable, asic in address
        if fee_types[addr] is not None
    )


def reset_asic(address, verbose=False):
    """Send reset signal to asic, resets all registers to defaults."""
    if type(address) is not tuple:
        a = decode_address(address, True)
    else:
        a = address

    _addr = None
    _cable = None

    spi = SpiTrbTdc(trbnet_interface)

    for con in make_asic_connections(a):

        if con.trbid == _addr and con.cable == _cable:
            continue

        _addr = con.trbid
        _cable = con.cable

        print(
            Fore.YELLOW
            + "Reseting {:s} cable {:d}".format(trbaddr(con.trbid), con.cable)
            + Style.RESET_ALL
        )
        spi.reset(con.trbid, con.cable)


def asics_to_defaults(address, def_pasttrec):
    """Set asics to defaults from config."""
    d = def_pasttrec.dump_config()
    for addr, cable, asic in address:
        write_data(addr, cable, asic, d)


def asic_to_defaults(address, cable, asic, def_pasttrec):
    """Set asics to defaults from config."""
    write_data(address, cable, asic, def_pasttrec.dump_config())


def read_rm_scalers(trbid, n_scalers):
    return trbnet_interface.read_mem(
        trbid, hardware.TrbRegisters.SCALERS.value, n_scalers
    )


def read_r_scalers(trbid, channel):
    return trbnet_interface.read(trbid, hardware.TrbRegisters.SCALERS.value + channel)
