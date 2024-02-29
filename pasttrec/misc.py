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

from colorama import Fore, Style
import itertools
import time
import types

from pasttrec import communication, hardware

# Custom settings

# Baselines
pasttrec_bl_reg_num = 32


class Baselines:
    """Holds baseline info for given card"""

    baselines = None
    config = None

    def __init__(self):
        self.baselines = {}

    def add_trb(self, trbid, trb_design_type):
        if trbid not in self.baselines:
            w = hardware.TrbRegistersOffsets.bl_register_size
            h = trb_design_type.n_channels
            a = trb_design_type.n_asics
            c = trb_design_type.n_cables
            self.baselines[trbid] = [[[[0 for x in range(w)] for y in range(h)] for _a in range(a)] for _c in range(c)]


class Thresholds:
    thresholds = None
    config = None

    def __init__(self):
        self.thresholds = {}

    def add_trb(self, trbid, trb_design_type):
        if trbid not in self.thresholds:
            w = 128
            h = trb_design_type.n_channels
            a = trb_design_type.n_asics
            c = trb_design_type.n_cables
            self.thresholds[trbid] = [[[[0 for x in range(w)] for y in range(h)] for _a in range(a)] for _c in range(c)]


class Scalers:
    scalers = None
    n_scalers = 0

    def __init__(self, n_scalers):
        self.scalers = {}
        self.n_scalers = n_scalers

    def add_trb(self, trb):
        if trb not in self.scalers:
            self.scalers[trb] = [0] * self.n_scalers

    def diff(self, scalers):
        s = Scalers(self.n_scalers)
        for k, v in self.scalers.items():
            if k in scalers.scalers:
                s.add_trb(k)
                for i in list(range(self.n_scalers)):
                    vv = self.scalers[k][i] - scalers.scalers[k][i]
                    if vv < 0:
                        vv += 0x80000000
                    s.scalers[k][i] = vv
        return s


def parse_rm_scalers(n_scalers, res):
    s = Scalers(n_scalers)

    for addr, values in res.items():
        if len(values) > n_scalers:
            continue

        s.add_trb(addr)

        for channel in range(len(values)):
            val = values[channel]
            if val >= 0x80000000:
                val -= 0x80000000
            s.scalers[addr][channel] = val

    return s


def parse_r_scalers(res):
    r = {}
    lines = res.splitlines()
    for line in lines:
        parts = line.split()
        n = len(parts)

        if n == 2:
            a = int(parts[0], 16)
            n = int(parts[1], 16)
            if n >= 0x80000000:
                n -= 0x80000000
            r[hex(a)] = n

    return r


def calc_tdc_channel(trb_design_type, cable, asic, channel, with_ref_time=False):
    """Calculate address of cable and asic channel in tdc (0,48) or with
    reference channel offset (1, 49).
    """
    return (
        channel
        + trb_design_type.n_channels * asic
        + trb_design_type.n_channels * trb_design_type.n_asics * cable
        + (1 if with_ref_time is True else 0)
    )


# def calc_address_from_tdc(channel, with_ref_time=False):
#     """Do reverse address calculation."""
#     if with_ref_time:
#         channel = channel-1
#     cable = math.floor(
#         channel / (RegistersCodes.channels_num*len(def_pastrec_asic)))
#     asic = math.floor(
#         (channel - cable*RegistersCodes.channels_num*len(def_pastrec_asic))
#         / RegistersCodes.channels_num)
#     c = channel % RegistersCodes.channels_num
#     return cable, asic, c


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def convertToInt(num_string):
    """
    From https://python-forum.io/Thread-decimal-or-hexadecimal-digits-to-int
    """
    determine_base = {"0x": 16, "0b": 2, "0o": 8}  # dict to detrmine base

    # returns base from dict defaults to None(for base 10)
    base = determine_base.get(num_string[:2].lower(), None)

    if base is not None:
        return int(num_string[2:], base)
    else:
        return int(num_string)


def padded_hex(value, length):
    """
    based on https://stackoverflow.com/questions/12638408/decorating-hex-function-to-pad-zeros
    """

    hex_result = hex(value)[2:]  # remove '0x' from beginning of str
    num_hex_chars = len(hex_result)
    extra_zeros = "0" * (length - num_hex_chars)  # may not get used..

    return (
        "0x" + hex_result
        if num_hex_chars == length
        else "?" * length
        if num_hex_chars > length
        else "0x" + extra_zeros + hex_result
        if num_hex_chars < length
        else None
    )


def trbaddr(addr):
    return padded_hex(addr, 4)


def bl_list_with_marker(bl_list, pos):
    s = ""
    for i in range(len(bl_list)):
        if i == pos:
            s += Fore.YELLOW + "{:d}".format(bl_list[i]) + Style.RESET_ALL + ", "
        else:
            s += "{:d}, ".format(bl_list[i])
    return s


def is_iterable(object):
    try:
        iter(object)
        return True
    except TypeError:
        return False


def format_etrbid(etrbid):
    return f"{trbaddr(etrbid[0])}:{etrbid[1]}:{etrbid[2]}"


def format_ctrbid(ctrbid):
    return f"{trbaddr(ctrbid[0])}:{ctrbid[1]}"


def read_tempid(address, uid_mode, temp_mode, bar=None, sort=False):
    """Read temperature and/or id of given cables."""
    full_mode = not uid_mode and not temp_mode

    address_ct_sorted = communication.sort_by_ct(address)

    results = {}

    for cg in communication.group_cables(address_ct_sorted):
        cable_cons = communication.make_cable_connections(cg)

        for con in cable_cons:
            rc1 = con.activate_1wire()

        if uid_mode:
            time.sleep(con.spi.delay_1wire_id)
        else:
            time.sleep(con.spi.delay_1wire_temp)

        for con in cable_cons:
            rc1 = con.get_1wire_temp() if temp_mode or full_mode else ()
            rc2 = con.get_1wire_id() if uid_mode or full_mode else ()

            if len(rc1) == 0 and len(rc2) != 0:
                rc1 = ((0, 0),) * len(rc2)
            elif len(rc2) == 0 and len(rc1) != 0:
                rc2 = ((0, 0),) * len(rc1)

            group = ((x[0][0], x[0][1], x[1][1]) for x in zip(rc1, rc2))
            for entry in group:
                results[entry[0], con.cable] = entry[1], entry[2]
            if bar:
                bar()

    if sort:
        return dict(sorted(results.items()))
    else:
        return results


def reset_asic(address, bar=None):
    """Reset ASICs on given cables."""

    address_ct_sorted = communication.sort_by_ct(address)

    results = {}

    for cg in communication.group_cables(address_ct_sorted):
        cable_cons = communication.make_cable_connections(cg)

        for con in cable_cons:
            rc = con.reset_spi()
            if bar:
                bar()


def read_asic(address, reg=None, bar=None, sort=False):
    address_ct_sorted = communication.sort_by_ct(address)

    results = {}

    for cg in communication.group_cables(address_ct_sorted):
        cable_cons = communication.make_asic_connections(cg)

        for con in cable_cons:
            if not is_iterable(reg):
                reg = tuple(reg)

            for r in reg:
                rc = con.read_reg(r)
                for irc in rc:
                    addr = irc[0]
                    faddr = (addr, con.cable, con.asic)
                    if not faddr in results:
                        results[faddr] = [0] * len(reg)
                    results[faddr][r] = (r, irc[1] & 0xFF)
                if bar:
                    bar()

    if sort:
        return dict(sorted(results.items()))
    else:
        return results


def write_asic(address, data=None, reg=None, val=None, verify=False, bar=None, sort=False):
    is_data = data is not None
    is_reg_val = reg is not None and val is not None

    if not ((is_data and not is_reg_val) or (not is_data and is_reg_val)):
        raise "Either data or reg,val can be used"

    if is_data:
        if not is_iterable(data):
            raise "'data' must be of 'iterable' type"
        _data = data

    elif is_reg_val:
        if not (is_iterable(reg) and is_iterable(val)):
            raise "'reg' and 'val' must be of 'iterable' type"
        _data = tuple(itertools.product(reg, val))

    address_ct_sorted = communication.sort_by_ct(address)

    results = {}

    for cg in communication.group_cables(address_ct_sorted):
        cable_cons = communication.make_asic_connections(cg)

        for con in cable_cons:

            for r, d in _data:
                con.write_reg(r, d)

                if verify:
                    rc = con.read_reg(r)

                    for irc in rc:
                        addr = irc[0]
                        faddr = (addr, con.cable, con.asic)

                        if not faddr in results:
                            results[faddr] = {}

                        _d = irc[1] & 0xFF
                        results[faddr][r, d] = _d == d, _d

                if bar:
                    bar()

    if verify:
        if sort:
            return dict(sorted(results.items()))
        else:
            return results
    else:
        return None
