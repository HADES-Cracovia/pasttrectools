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

from alive_progress import alive_bar  # type: ignore
from colorama import Fore, Style  # type: ignore
from tabulate import tabulate  # type: ignore

from pasttrec import communication, misc
from pasttrec.etrbid import trbaddr
from pasttrec.actions import asic_parallel_access, read_register


def read_asics(address):
    n_regs = 12

    reg = range(n_regs)

    with alive_bar(
        len(address) * n_regs,
        title=f"{Fore.BLUE}Reading ASICs{Style.RESET_ALL}  ",
        file=sys.stderr,
    ) as bar:
        sorted_results = asic_parallel_access(
            communication.make_asic_connections(address),
            read_register,
            data=reg,
            post_action=lambda: bar(),
            sort=True,
        )

    color_map = (Fore.MAGENTA,) * 3 + (Fore.CYAN,) + (Fore.GREEN,) * 8
    funcs = (hex,) + (oct,) * 2 + (hex,) + (int,) * 8

    rows = []
    for key, res in sorted_results.items():
        color_res = zip(funcs, res, color_map)
        line = tuple(Fore.YELLOW + str(s) for s in (trbaddr(key[0]), key[1], key[2], "")) + tuple(
            color + f"{func(val)}" + Style.RESET_ALL for (func, (reg, val), color) in color_res
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

    misc.parser_common_options(parser)

    args = parser.parse_args()

    communication.make_trbids_db(args.trbids, args.ignore_missing)

    etrbids = communication.decode_address(args.trbids, args.ignore_missing)
    r = read_asics(etrbids)
