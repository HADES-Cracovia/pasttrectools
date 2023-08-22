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

from pasttrec import hardware

# Custom settings

# Baselines
pasttrec_bl_reg_num = 32


class Baselines:
    """Holds baseline info for given card"""

    baselines = None
    config = None

    def __init__(self):
        self.baselines = {}

    def add_trb(self, trbid, trbfetype):
        if trbid not in self.baselines:
            w = hardware.TrbRegistersOffsets.bl_register_size
            h = trbfetype.n_channels
            a = trbfetype.n_asics
            c = trbfetype.n_cables
            self.baselines[trbid] = [[[[0 for x in range(w)] for y in range(h)] for _a in range(a)] for _c in range(c)]


class Thresholds:
    thresholds = None
    config = None

    def __init__(self):
        self.thresholds = {}

    def add_trb(self, trbid, trbfetype):
        if trbid not in self.thresholds:
            w = 128
            h = trbfetype.n_channels
            a = trbfetype.n_asics
            c = trbfetype.n_cables
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


def parse_rm_scalers(trbfetype, res):
    s = Scalers(trbfetype.n_scalers)

    for addr, values in res.items():
        if len(values) > trbfetype.n_scalers:
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


def calc_tdc_channel(trbfetype, cable, asic, channel, with_ref_time=False):
    """Calculate address of cable and asic channel in tdc (0,48) or with
    reference channel offset (1, 49).
    """
    return (
        channel
        + trbfetype.n_channels * asic
        + trbfetype.n_channels * trbfetype.n_asics * cable
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
