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
from time import sleep
from colorama import Fore, Style
import sys

from alive_progress import alive_bar

from pasttrec import communication
from pasttrec.misc import trbaddr

def_time = 0.0


def read_asic(address):
    results = {}
    n_regs = 12

    stup_ct = communication.sort_by_ct(address)

    with alive_bar(len(stup_ct) * n_regs, title="Reading out registers", file=sys.stderr) as bar:

        for cg in communication.group_cables(stup_ct):
            cable_cons = communication.make_asic_connections(cg)

            for con in cable_cons:
                for reg in range(n_regs):

                    rc = con.read_reg(reg)
                    for irc in rc:
                        addr = irc[0]
                        faddr = (addr, con.cable, con.asic)
                        if not faddr in results:
                            results[faddr] = [0] * n_regs
                        results[faddr][reg] = irc[1] & 0xFF
                    bar()

    print("   TDC  Cable  Asic   Reg# " + Fore.YELLOW, end="")

    if communication.g_verbose == 0:
        for reg in range(n_regs):
            print("    {:2d}".format(reg), end="")
    print(Style.RESET_ALL)

    sresults = dict(sorted(results.items()))
    for key, res in sresults.items():
        print(Fore.YELLOW + "{:s}  {:5d}  {:4d}        ".format(trbaddr(key[0]), key[1], key[2]), end="")

        for reg in range(n_regs):
            if reg < 3:
                print(Fore.MAGENTA, end="")
            elif reg == 3:
                print(Fore.CYAN, end="")
            else:
                print(Fore.GREEN, end="")

            if communication.g_verbose > 0:
                print("Register: {0:#0{1}x}    Value: {2:#0{3}x}".format(reg, 2, _t, 4))
            else:
                print("  {:#0{}x}".format(res[reg], 4), end="")

        print(Style.RESET_ALL)

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
    r = read_asic(tup)
