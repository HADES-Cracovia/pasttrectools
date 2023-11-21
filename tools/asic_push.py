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

from pasttrec import communication, misc, g_verbose


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push or dump registers to asic/file")
    parser.add_argument("dat_file", help="list of arguments", type=str, nargs="+")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--dump", help="trbcmd dump file, bl regs only", type=str)
    group.add_argument("-D", "--Dump", help="trbcmd dump file, all regs", type=str)
    parser.add_argument("-e", "--exec", help="execute", action="store_true")

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

    dump_file = None
    if args.dump:
        dump_file = open(args.dump, "w")

    if args.Dump:
        dump_file = open(args.Dump, "w")

    for f in args.dat_file:
        with open(f) as data:
            lines = data.readlines()
            data.close()

        for line in lines:
            # Pawel Kulessa enumerates cables 1..3 and asics 1..2, unlike RL 0..2 and 0..1, so sub 1 for PK files

            if g_verbose > 0:
                print(f"Parsing line: {line}", end="")

            parts = line.split()

            nl = [misc.convertToInt(x) for x in parts[0:15]]

            con = tuple(communication.make_asic_connections((tuple(nl[0:3]),)))[0]

            for i, val in enumerate(nl[3:15]):
                nl[3 + i] = i << 8 | nl[3 + i]

            if args.dump:
                communication.cmd_to_file = dump_file
                con.write_chunk(nl[2], nl[3:15])
                communication.cmd_to_file = None

            if args.Dump:
                communication.cmd_to_file = dump_file
                con.write_chunk(nl[3:15])
                communication.cmd_to_file = None

            if args.exec or args.dump is None and args.Dump is None:
                con.write_chunk(nl[3:15])

    if dump_file:
        dump_file.close()
