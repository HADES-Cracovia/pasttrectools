#!/usr/bin/env python3
#
# Copyright 2022 Akshay Malige <akshay.malige@doctoral.uj.edu.pl>
# Copyright 2023 Rafal Lalik <rafal.lalik@uj.edu.pl>
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
import glob
import argparse
from time import sleep
import json
import math
from colorama import Fore, Style

from pasttrec import communication
from pasttrec.misc import trbaddr

def_time = 0


def asic_tempid(address, pretty_mode, show_temp):

    if pretty_mode:
        print("   TDC  Cable   Temp  WireId " + Fore.YELLOW, end="", flush=True)
        print(Style.RESET_ALL)

    for con in communication.make_cable_connections(address):
        if pretty_mode:
            print(
                Fore.YELLOW
                + "{:s}  {:5d} ".format(trbaddr(con.trbid), con.cable)
                + Style.RESET_ALL,
                end="",
                flush=True,
            )

        if pretty_mode or show_temp:
            rc1 = con.read_wire_temp()

            if pretty_mode:
                print(Fore.MAGENTA, end="")
                print(" {:3.2f}".format(rc1), end="")
            elif show_temp:
                print("{:3.2f}".format(rc1))

        if pretty_mode or not show_temp:
            rc2 = con.read_wire_id()

            if pretty_mode:
                print(Fore.CYAN, end="")
                print("  {:#0{}x}".format(rc2, 4), end="")
            elif not show_temp:
                print("{:#0{}x}".format(rc2, 4))

        if pretty_mode:
            print(Style.RESET_ALL)


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

    parser.add_argument("-t", "--time", help="sleep time", type=float, default=def_time)
    parser.add_argument(
        "-v",
        "--verbose",
        help="verbose level: 0, 1, 2, 3",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )

    parser.add_argument(
        "-p",
        "--pretty",
        help="pretty view -- shwo both temp and id",
        action="store_true",
    )
    parser.add_argument("--temp", help="show temperature not id", action="store_true")

    args = parser.parse_args()

    communication.g_verbose = args.verbose
    def_time = args.time

    if communication.g_verbose > 0:
        print(args)

    tup = communication.decode_address(args.trbids)
    r = asic_tempid(tup, args.pretty, args.temp)
