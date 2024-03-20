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

from pasttrec import communication, misc
from pasttrec.misc import trbaddr, format_etrbid
from pasttrec.requests import write_asic


def scan_spi_communication(address, def_no_skip=False):

    reg_target = 0x0C
    reg_test_vals = (0x00, 0xFF, 0x0F, 0xF0, 0x55, 0x99, 0x95, 0x59)

    tests_failed = 0
    tests_ok = 0

    with alive_bar(
        len(address) * len(reg_test_vals),
        title=f"{Fore.BLUE}Scanning SPI{Style.RESET_ALL}   ",
        file=sys.stderr,
    ) as bar:
        sorted_results = write_asic(
            communication.make_asic_connections(address),
            reg=(reg_target,),
            val=reg_test_vals,
            verify=True,
            bar=bar,
            sort=True,
        )

    last_trbid = 0
    print("Scan results:", end="")
    for key, res in sorted_results.items():

        if key[0] != last_trbid:
            last_trbid = key[0]
            print(f"\n- {trbaddr(last_trbid)}:", end="")

        passed = all(val[0] is True for key, val in res.items())

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

    misc.parser_common_options(parser)

    parser.add_argument("-n", "--no-skip", help="do not skip missing FEEs", action="store_true")

    args = parser.parse_args()

    communication.make_trbids_db(args.trbids, args.ignore_missing)

    etrbids = communication.decode_address(args.trbids, args.ignore_missing)
    r = scan_spi_communication(etrbids, args.no_skip)
    sys.exit(r)
