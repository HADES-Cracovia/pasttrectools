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

import time

from colorama import Fore, Style

from pasttrec.types import Scalers
from pasttrec.etrbid import trbaddr


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
    determine_base = {"0x": 16, "0b": 2, "0o": 8}  # dict to determine base

    # returns base from dict defaults to None(for base 10)
    base = determine_base.get(num_string[:2].lower(), None)

    if base is not None:
        return int(num_string[2:], base)
    else:
        return int(num_string)


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


def read_tempid(connections, uid_mode, temp_mode, bar=None, sort=False):
    """Read temperature and/or id of given cables."""
    full_mode = not uid_mode and not temp_mode

    results = {}
    for cg, cable_cons in connections:

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

            group = ((max(x[0][0], x[1][0]), x[0][1], x[1][1]) for x in zip(rc1, rc2))
            for entry in group:
                results[entry[0], con.cable] = entry[1], entry[2]
            if bar:
                bar()

    if sort:
        return dict(sorted(results.items()))
    else:
        return results


def print_verbose(rc, verbose=0):
    cmd = " ".join(rc.args)
    rtc = rc.returncode

    if verbose >= 1:
        print("[{:d}]  {:s}".format(rtc, cmd))


def parser_common_options(parser):
    parser.add_argument(
        "trbids",
        help="list of TRBids to scan in form" " address[:card-0-1-2[:asic-0-1]]",
        type=str,
        nargs="+",
    )
    parser.add_argument("-m", "--ignore-missing", help="ignore missing trbids", action="store_true")
