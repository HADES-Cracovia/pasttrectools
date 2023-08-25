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

from pasttrec import communication, g_verbose
from pasttrec.misc import trbaddr

def_time = 0.0
def_quick = False


def scan_communication(address):

    print("   TDC  Cable  Asic  >{:s}<".format("-" * 58))

    if def_quick is True:
        reg_range = [3]
        reg_test_vals = [0x5A]
    else:
        reg_range = range(12)
        reg_test_vals = [1, 4, 7, 10, 13]

    test_ok = True
    for addr, cable, asic in address:
        trbfetype = communication.detect_frontend(addr)
        if trbfetype is None:
            continue

        print(
            Fore.YELLOW + "{:s}  {:5d} {:5d}  ".format(trbaddr(addr), cable, asic) + Style.RESET_ALL,
            end="",
            flush=True,
        )

        asic_test_ok = True

        for reg in reg_range:
            reg_test_ok = True

            for t in reg_test_vals:
                print(".", end="", flush=True)
                communication.write_reg(trbfetype, addr, cable, asic, reg, t)
                sleep(def_time)
                rc = communication.read_reg(trbfetype, addr, cable, asic, reg)
                try:
                    _t = rc & 0xFF
                except ValueError as ve:
                    print("Wrong result: ", rc.split()[1])
                    print(ve)
                    _t = 0xDEADBEEF

                if _t != t or _t == 0xDEADBEEF:
                    print(
                        Fore.RED + " Test failed for register {:d}".format(reg) + Style.RESET_ALL,
                        end="",
                    )
                    print("  Sent {:d}, received {:d}".format(t, _t))
                    reg_test_ok = False
                    break

            if reg_test_ok is False:
                asic_test_ok = False
                test_ok = False
                break

        if asic_test_ok:
            print(Fore.GREEN + " OK " + Style.RESET_ALL)

    if test_ok:
        print("All test done and OK")
        return True

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

    parser.add_argument("-q", "--quick", help="quick test", action="store_true")
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

    def_time = args.time
    def_quick = args.quick

    tup = communication.decode_address(args.trbids)
    a = args.trbids
    r = scan_communication(tup)
    sys.exit(r)
