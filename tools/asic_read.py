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

from pasttrec import communication
from pasttrec.misc import trbaddr, read_asic

def_time = 0.0


def read_asics(address):
    n_regs = 12

    with alive_bar(len(address) * n_regs, title="Reading out registers", file=sys.stderr) as bar:
        sorted_results = read_asic(address, range(n_regs), bar=bar, sort=True)

    color_map = (Fore.MAGENTA,) * 3 + (Fore.CYAN,) + (Fore.GREEN,) * 8

    rows = []
    for key, res in sorted_results.items():
        color_res = zip(res, color_map)
        line = tuple(Fore.YELLOW + str(s) for s in (trbaddr(key[0]), key[1], key[2], "")) + tuple(
            color + f"{hex(val)}" + Style.RESET_ALL for ((reg, val), color) in color_res
        )
        rows.append(line)

    colalign = ("right",) * (n_regs + 4)
    header = ("TDC", "Cable", "Asic", "Reg#") + tuple(str(x) for x in range(n_regs))

    if len(rows):
        print(tabulate(rows, headers=header, colalign=colalign))

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read registers of the PASTTREC chips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "trbids",
        help="list of TRBids to scan in form" " addres[:card-0-1-2[:asic-0-1]]",
        type=str,
        nargs="+",
    )

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

    communication.g_verbose = args.verbose
    def_time = args.time

    if communication.g_verbose > 0:
        print(args)

    tup = communication.decode_address(args.trbids)
    r = read_asics(tup)
