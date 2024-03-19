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
import time
from colorama import Fore, Style

from pasttrec import etrbid, hardware, misc
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
    # print("INFO: Trbnet library found in {:s} at host {:s}".format(lib, host))

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


def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func

    return decorate


def read_trb_features(trbid, ignore_missing):
    """
    Get TRB features Info.

    Parameters
    ----------
    trbid : int
        Valid trbid address
    ignore_missing : bool
        Do not throw exception when trbid is not responding

    Returns
    -------
    features : tuple(trbid, responders) or None
        List of the trbid responders with hw and features.
        The 'responders' is a tuple of (responding_trbid, (hwtype, features)).
    """

    try:
        rc_hw = trbnet_interface.read(trbid, 0x42)
        rc_fh = trbnet_interface.read(trbid, 0x43)
        rc_fl = trbnet_interface.read(trbid, 0x41)
    except ValueError as e:
        if ignore_missing:
            return None
        else:
            raise e

    responders = tuple(
        (responder_trbid, (hw, fh << 32 | fl)) for (responder_trbid, hw), (_, fh), (_, fl) in zip(rc_hw, rc_fh, rc_fl)
    )

    return (trbid, responders)


def make_trbids_db(ptrbids: tuple, ignore_missing):
    """
    Make database of trbids and design types.

    The trbids are checket for the address type. The broadcasts addresses are takend from design types db, and regular
    addresses are queried from the trbnet. For the broadcast adddress having responders, each responder is also add
    with itself being its own responder.

    Parameters
    ----------
    ptrbids : tuple
        Tuple of ptrbids strings
    ignore_missing : bool
        Ignore missing trbids. If trbid is missing, the exception is raised.
    """
    trbids = etrbid.trbids_from_ptrbids(ptrbids)

    for trbid in trbids:
        if trbid in hardware.trb_designs_map:
            continue

        res = read_trb_features(trbid, ignore_missing)

        if res is None:
            continue

        # Loop over all responders. If this was single trbid one expect also single responder.
        # In case of broadcast address, responders would have different trbids.
        # If this was broadcast, cehck whetehr are responders are of the same hwtype and features.
        # If they are not, the address cannot be used for commin actions.

        is_broadcast = False
        responders_features = set()
        responders_hwtypes = set()
        responders_trbids = set()

        if res[1] is not None:
            for responder_trbid, (hwtype, features) in res[1]:

                responders_trbids.add(responder_trbid)
                responders_hwtypes.add(hwtype)
                responders_features.add(features)

                hardware.trb_designs_map[responder_trbid] = hardware.TrbDesignInfo(hwtype, features, (responder_trbid,))

                if responder_trbid != trbid:
                    is_broadcast = True

        # If the 'responders_features' set has length larger than 1, then we had different features set.
        if is_broadcast:
            hardware.trb_designs_map[trbid] = hardware.TrbDesignInfo(
                0 if len(responders_hwtypes) != 1 else tuple(responders_hwtypes)[0],
                0 if len(responders_features) != 1 else tuple(responders_features)[0],
                tuple(responders_trbids),
            )

    return hardware.trb_designs_map


@static_vars(designs_map={})
def get_trb_design_type(trbid):
    """Caches the design types."""

    if type(trbid) == str:
        trbid = int(trbid, 16)

    if trbid not in get_trb_design_type.designs_map:
        design = hardware.detect_design(trbid)
        get_trb_design_type.designs_map[trbid] = design[1][0][1] if design else None

    return get_trb_design_type.designs_map[trbid]


def decode_address_entry(strbid, ignore_missing, sort=False):
    """
    Converts strbid into ( trbnet, cable, cable, asic ) tuples from input string.

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

    if isinstance(strbid, (int,)):
        address_t = (strbid,)
    else:
        address_t = etrbid.extract_strbid(strbid)

    try:
        trb_fe_type_t = get_trb_design_type(address_t[0])
        if trb_fe_type_t == ():
            return ()

    except hardware.MissingFeatures as e:
        if ignore_missing:
            return ()
        else:
            raise e

    except ValueError:
        print(Fore.RED + f"Incorrect address {address}" + Style.RESET_ALL, file=sys.stderr)
        return ()

    trb_fe_type = trb_fe_type_t
    return etrbid.expand_strbid(address_t, trb_fe_type.cables, trb_fe_type.asics) if trb_fe_type else ()


def decode_address(strbid, ignore_missing):
    """Use this for a single string or list of strings."""

    if len(hardware.trb_designs_map) == 0:
        print(Fore.RED + f"TRB database is empty. Did you call 'make_trbids_db()'?" + Style.RESET_ALL, file=sys.stderr)

    if isinstance(strbid, (tuple, list)):
        return sum((decode_address_entry(s, ignore_missing) for s in strbid), ())
    else:
        return decode_address_entry(strbid, ignore_missing)


class CardConnection:
    """These functions write, read memory for given cable and asic."""

    shared_trb_spi = {}
    encoder = hardware.PasttrecDataWordEncoder()

    def __init__(self, trb_frontend, trbid, cable):
        if not isinstance(trb_frontend, hardware.TrbDesignSpecs):
            raise TypeError("Must be of TrbDesignSpecs type")

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
    def cable_address(self):
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


def cable_connections(address):
    """Make instances of CardConenction based on the decoded addresses."""

    filtered_cables = etrbid.ctrbids_from_etrbids(address)
    sorted_cables = etrbid.sort_by_cable(filtered_cables)

    return tuple(
        CardConnection(get_trb_design_type(addr), addr, cable)
        for addr, cable in sorted_cables
        if get_trb_design_type(addr) is not None
    )


def make_cable_connections(address):
    """Make groups of CardConenction based on the decoded addresses."""

    return tuple((cg, cable_connections(cg)) for cg in etrbid.group_cables(address))


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
        return f"Pasttrec connection to {etrbid.trbaddr(self.trbid)} for cable={self.cable} asic={self.asic}"


def asic_connections(address):
    """Make instances of PasttercConenction based on the decoded addresses."""

    address_ct_sorted = etrbid.sort_by_ct(address)

    return tuple(
        PasttrecConnection(get_trb_design_type(addr), addr, cable, asic)
        for addr, cable, asic in address_ct_sorted
        if get_trb_design_type(addr) is not None
    )


def make_asic_connections(address):
    """Make instances of PasttercConenction based on the decoded addresses."""

    return tuple((cg, asic_connections(cg)) for cg in etrbid.group_cables(address))


def asics_to_defaults(address, def_pasttrec):
    """Set asics to defaults from config."""
    d = def_pasttrec.dump_config()
    for addr, cable, asic in address:
        write_data(addr, cable, asic, d)


def asic_to_defaults(address, cable, asic, def_pasttrec):
    """Set asics to defaults from config."""
    write_data(address, cable, asic, def_pasttrec.dump_config())


def read_rm_scalers(trbid, n_scalers):
    return trbnet_interface.read_mem(trbid, hardware.TrbRegisters.SCALERS.value, n_scalers, option=0)


def read_r_scalers(trbid, channel):
    return trbnet_interface.read(trbid, hardware.TrbRegisters.SCALERS.value + channel)


def read_diff_scalers(trbid, n_scalers, sleep_time):
    """Read scalers from 'trbid' twice with 'sleep_time'
    pause and calculate the counts difference."""

    v1 = read_rm_scalers(trbid, n_scalers)
    time.sleep(sleep_time)
    v2 = read_rm_scalers(trbid, n_scalers)
    a1 = misc.parse_rm_scalers(n_scalers, v1)
    a2 = misc.parse_rm_scalers(n_scalers, v2)
    bb = a2.diff(a1)
    return bb
