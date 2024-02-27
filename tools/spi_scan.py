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

import sys
import argparse
from time import sleep
from colorama import Fore, Style

from alive_progress import alive_bar

from pasttrec import communication, g_verbose
from pasttrec.misc import trbaddr

def_time = 0.0


def scan_spi_communication(address, def_time=1.0, def_no_skip=False):

    print("   TDC  Cable  Asic")

    reg_target = 0x0C
    reg_test_vals = [0x00, 0xFF, 0x0F, 0xF0, 0x55, 0x99, 0x95, 0x59]

    tests_failed = 0
    tests_ok = 0

    for con in communication.make_asic_connections(address):

        with alive_bar(
            len(reg_test_vals),
            title=Fore.YELLOW + "{:s}  {:5d} {:5d}  ".format(trbaddr(con.trbid), con.cable, con.asic) + Style.RESET_ALL,
            file=sys.stderr,
            receipt_text=True,
            spinner=None,
            monitor=False,
            elapsed=False,
            stats=False,
        ) as bar:
            reg_test_ok = True

            for t in reg_test_vals:
                con.write_reg(reg_target, t)
                sleep(def_time)
                rc = con.read_reg(reg_target)
                try:
                    _t = rc & 0xFF
                except ValueError as ve:
                    bar.text(f"Wrong result: {rc.split()[1]} {ve}")
                    _t = None

                if _t != t or _t is None:
                    if not def_no_skip:
                        bar.text(
                            Fore.RED
                            + " Test failed for register {:d}".format(reg_target)
                            + Style.RESET_ALL
                            + "  Sent {:d}, received {:d}".format(t, _t),
                        )
                        reg_test_ok = False
                        break
                else:
                    bar()

            if reg_test_ok:
                bar.text(Fore.GREEN + " OK" + Style.RESET_ALL)
                tests_ok += 1
            else:
                bar.text(Fore.RED + " FAILED" + Style.RESET_ALL)
                tests_failed += 1

    print(Fore.GREEN + f"OK tests: {tests_ok}  ", end="")
    if tests_failed:
        print(Fore.RED + f"Failed tests: {tests_failed}" + Style.RESET_ALL)
    else:
        print(Style.RESET_ALL + f"Failed tests: {tests_failed}")

    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan SPI communication of PASTTREC chips",
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
    r = scan_spi_communication(tup, args.time, args.no_skip)
    sys.exit(r)
