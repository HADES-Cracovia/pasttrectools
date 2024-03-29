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

from pasttrec import communication
from pasttrec.misc import trbaddr

def_time = 0.0


def read_asic(address):

    print("   TDC  Cable  Asic   Reg# " + Fore.YELLOW, end="", flush=True)

    if communication.g_verbose == 0:
        for reg in range(12):
            print("    {:2d}".format(reg), end="", flush=True)

    print(Style.RESET_ALL)

    for con in communication.make_asic_connections(address):
        if communication.g_verbose == 0:
            print(
                Fore.YELLOW
                + "{:s}  {:5d}  {:4d}        ".format(trbaddr(con.trbid), con.cable, con.asic)
                + Style.RESET_ALL,
                end="",
                flush=True,
            )

        for reg in range(12):

            rc = con.read_reg(reg)
            try:
                _t = rc & 0xFF
            except ValueError as ve:
                print("Wrong result: ", rc.split()[1])
                print(ve)
                _t = 0xDEADBEEF

            if _t == 0xDEADBEEF:
                print(
                    Fore.RED + " Read failed for register {:s}".format(hex(reg)) + Style.RESET_ALL,
                    end="",
                )
                print("  Received {:s}".format(hex(_t)))
            else:
                if communication.g_verbose > 0:
                    print(
                        Fore.YELLOW
                        + "{:s}  {:5d}  {:4d}        ".format(trbaddr(con.trbid), con.cable, con.asic)
                        + Style.RESET_ALL,
                        end="",
                        flush=True,
                    )

                if reg < 3:
                    print(Fore.MAGENTA, end="", flush=True)
                elif reg == 3:
                    print(Fore.CYAN, end="", flush=True)
                else:
                    print(Fore.GREEN, end="", flush=True)

                if communication.g_verbose > 0:
                    print("Register: {0:#0{1}x}    Value: {2:#0{3}x}".format(reg, 2, _t, 4))
                else:
                    print("  {:#0{}x}".format(_t, 4), end="", flush=True)

            print(Style.RESET_ALL, end="", flush=True)
            sleep(def_time)

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
