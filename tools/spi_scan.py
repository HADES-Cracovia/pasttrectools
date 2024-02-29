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

from pasttrec import communication, g_verbose
from pasttrec.misc import trbaddr, write_asic, format_etrbid

def_time = 0.0


def scan_spi_communication(address, def_time=1.0, def_no_skip=False):

    reg_target = 0x0C
    reg_test_vals = (0x00, 0xFF, 0x0F, 0xF0, 0x55, 0x99, 0x95, 0x59)

    tests_failed = 0
    tests_ok = 0

    with alive_bar(
        len(address) * len(reg_test_vals),
        title=Fore.YELLOW + "Scanning SPI connection  " + Style.RESET_ALL,
        file=sys.stderr,
    ) as bar:
        sorted_results = write_asic(address, reg=(reg_target,), val=reg_test_vals, verify=True, bar=bar, sort=True)

    last_trbid = 0
    print("Scan results:", end="")
    for key, res in sorted_results.items():

        if key[0] != last_trbid:
            last_trbid = key[0]
            print(f"\n- {trbaddr(last_trbid)}:", end="")

        passed = all(val[0] == True for key, val in res.items())

        if passed:
            print("  " + Fore.GREEN + format_etrbid(key) + Style.RESET_ALL, end="")
            tests_ok += 1
        else:
            print("  " + Fore.RED + format_etrbid(key) + Style.RESET_ALL, end="")
            tests_failed += 1

    print(Style.RESET_ALL + "\n Summary:  ", end="")

    print(Fore.YELLOW + f"Tests passed: {tests_ok}   ", end="")
    if tests_failed:
        print(f"Tests failed: {tests_failed}" + Style.RESET_ALL)
    else:
        print(Style.RESET_ALL + f"Tests failed: {tests_failed}")

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
