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

import argparse
from colorama import Fore, Style
import json
import time
import sys

from alive_progress import alive_bar

from pasttrec import communication
from pasttrec.misc import trbaddr

def_time = 0


def asic_tempid(address, uid_mode, temp_mode, no_color, trbnet_map):

    full_mode = not uid_mode and not temp_mode

    results_map = {}

    stup_ct = communication.sort_by_ct(address)
    stup_t = communication.sort_by_tc(address)

    with alive_bar(len(stup_ct), title="Reading out 1-wires", file=sys.stderr) as bar:

        for cg in communication.group_cables(stup_ct):
            cable_cons = communication.make_cable_connections(cg)

            for con in cable_cons:
                bar()
                rc1 = con.activate_1wire()

            if uid_mode:
                time.sleep(con.spi.delay_1wire_id)
            else:
                time.sleep(con.spi.delay_1wire_temp)

            for con in cable_cons:
                rc1 = con.get_1wire_temp() if temp_mode or full_mode else 0
                rc2 = con.get_1wire_id() if uid_mode or full_mode else 0

                results_map[con.address] = rc1, rc2

    if full_mode:
        print("   TDC  Cable   Temp   WireId")
    elif temp_mode:
        print("   TDC  Cable   Temp")
    else:
        print("   TDC  Cable   WireId")

    print(stup_t)
    print(results_map)
    for addr in stup_t:
        res = results_map[addr]
        if not no_color:
            print(Fore.YELLOW, end="")

        print("{:s}  {:5d} ".format(trbaddr(addr[0]), addr[1]) + Style.RESET_ALL, end="")

        if not no_color:
            print(Style.RESET_ALL, end="")

        if full_mode or temp_mode:
            rc1 = res[0]

            if not no_color:
                print(Fore.MAGENTA, end="")

            print("  {:05.2f}".format(rc1), end="")

        if full_mode or uid_mode:
            rc2 = res[1]

            if not no_color:
                print(Fore.CYAN, end="")

            print("  {:#0{}x}".format(rc2, 18), end="")

        print(Style.RESET_ALL)

    if trbnet_map is not None:
        the_map = {hex(k[0]): {} for k, v in results_map.items() if v[1] != 0}
        for k, v in results_map.items():
            if v[1] != 0:
                the_map[hex(k[0])][k[1]] = "{:#0{}x}".format(v[1], 18)

        with open(trbnet_map, "w") as fp:
            json.dump(the_map, fp, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read 1-wire devices of PASTTREC board",
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

    group = parser.add_mutually_exclusive_group()

    group.add_argument("--uid", help="show uid", action="store_true")
    group.add_argument("--temp", help="show temperature", action="store_true")

    parser.add_argument("--no-color", help="don't use colors", action="store_true")
    parser.add_argument("-m", "--trbnet-map", help="export trbnet map", type=str)

    args = parser.parse_args()

    communication.g_verbose = args.verbose
    def_time = args.time

    if communication.g_verbose > 0:
        print(args)

    etrbids = communication.decode_address(args.trbids)
    tup = communication.filter_decoded_cables(etrbids)

    r = asic_tempid(tup, args.uid, args.temp, args.no_color, args.trbnet_map)
