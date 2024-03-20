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

from pasttrec import communication, misc

def_pastrec_thresh_range = (0x00, 0x7F)


def fill_register(address, value):
    for x in range(12):
        set_register(address, x, value)

    return 0


def set_register(address, register, value):
    for con in communication.asic_connections(address):
        con.write_reg(register, value & 0xFF)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Set PASTTREC registers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    misc.parser_common_options(parser)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-f",
        "--fill",
        help="Fill all registers with value",
        type=lambda x: int(x, 0),
        nargs=1,
        metavar="VALUE",
    )
    group.add_argument(
        "-r",
        "--reg",
        help="Set single register with value",
        type=lambda x: int(x, 0),
        nargs=2,
        metavar=("REGISTER", "VALUE"),
    )
    group.add_argument(
        "-t",
        "--threshold",
        help="Set threshold (range: 0-127)",
        type=lambda x: int(x, 0),
        nargs=1,
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="verbose level: 0, 1, 2, 3",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )

    args = parser.parse_args()

    communication.make_trbids_db(args.trbids, args.ignore_missing)
    etrbids = communication.decode_address(args.trbids, args.ignore_missing)

    if args.fill:
        sys.exit(fill_register(etrbids, args.fill[0]))
    elif args.reg:
        sys.exit(set_register(etrbids, args.reg[0], args.reg[1]))
    elif args.threshold:
        if args.threshold[0] > def_pastrec_thresh_range[1] or args.threshold[0] < def_pastrec_thresh_range[0]:
            print("\nOption error: Threshold value {:d} is to high, " " allowed value is 0-127".format(args.threshold))
            sys.exit(1)

        sys.exit(set_register(etrbids, 3, args.threshold[0]))
    else:
        sys.exit(1)
