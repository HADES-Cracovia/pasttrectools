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

import argparse
import sys
from time import sleep

from alive_progress import alive_bar
from colorama import Fore, Style
from tabulate import tabulate

from pasttrec import communication, g_verbose
from pasttrec.misc import trbaddr, write_asic, format_etrbid

def_time = 0.0


def scan_asic_communication(address, def_time=1.0, def_no_skip=False):

    reg_range = range(12)
    reg_test_vals = (0x00, 0xFF, 0x0F, 0xF0, 0x55, 0x99, 0x95, 0x59)

    with alive_bar(
        len(address) * len(reg_test_vals) * len(reg_range),
        title=Fore.YELLOW + "Scanning ASIC registers:" + Style.RESET_ALL,
        file=sys.stderr,
    ) as bar:
        sorted_results = write_asic(address, reg=reg_range, val=reg_test_vals, verify=True, bar=bar, sort=True)

    colalign = ("right",) * (len(reg_range) + 3)
    header = ("TDC", "Cable", "Asic") + tuple(str(x) for x in reg_range)
    rows = []
    last_trbid = 0

    for key, res in sorted_results.items():
        passed = all(val[0] == True for key, val in res.items())
        line = (trbaddr(key[0]), key[1], key[2]) + tuple(
            Fore.GREEN + "Passed" + Style.RESET_ALL
            if all(val[0] == True for key, val in res.items() if key[0] == ref_reg)
            else Fore.RED + "Failed" + Style.RESET_ALL
            for ref_reg in reg_range
        )

        rows.append(line)

    if len(rows):
        print(tabulate(rows, headers=header, colalign=colalign))

    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan communication of PASTTREC chips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "trbids",
        help="list of TRBids to scan in form" " addres[:card-0-1-2[:asic-0-1]]",
        type=str,
        nargs="+",
    )

    parser.add_argument("-n", "--no-skip", help="do not skip missing FEEs", action="store_true")
    parser.add_argument("-t", "--time", help="sleep time", type=float, default=def_time)
    parser.add_argument(
        "-v",
        "--verbose",
        help="verbose level: 0, 1, 2, 3",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )

    args = parser.parse_args()

    g_verbose = args.verbose
    if g_verbose > 0:
        print(args)

    tup = communication.decode_address(args.trbids)
    r = scan_asic_communication(tup, args.time, args.no_skip)
    sys.exit(r)
