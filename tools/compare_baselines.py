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
import json

from colorama import Fore, Style  # type: ignore

from pasttrec import hardware, communication, misc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculates baselines from scan results")
    parser.add_argument("json_file1", help="first json file", type=str)
    parser.add_argument("json_file2", help="second json file", type=str)

    parser.add_argument("-o", "--output", help="output file", type=str)
    parser.add_argument("-O", "--old", help="old output format", action="store_true")

    group = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "-v",
        "--verbose",
        help="verbose level: 0, 1, 2, 3",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )

    args = parser.parse_args()

    with open(args.json_file1) as json_data:
        d1 = json.load(json_data)
        json_data.close()

    with open(args.json_file2) as json_data:
        d2 = json.load(json_data)
        json_data.close()

    bls1 = d1["baselines"]
    cfg1 = d1["config"]

    bls2 = d2["baselines"]
    cfg2 = d2["config"]

    tlist = []

    print(cfg1, cfg2)

    x = list(range(0, 32))

    idx = 1
    for k, v in bls.items():  # FIXME bls missing - bug?

        t = hardware.TdcConnection(k)

        for c in [0, 1, 2]:
            card = hardware.PasttrecCard("noname")

            for a in [0, 1]:
                print(Fore.YELLOW + "Scanning {:s}  CARD: {:d}  ASIC: {:d}".format(k, c, a) + Style.RESET_ALL)
                bl = [0] * 8

                for ch in list(range(8)):
                    b = v[c][a][ch]
                    s = 0
                    w = 0
                    for i in range(1, 32):
                        s = s + (i + 1) * b[i]
                        w += b[i]
                    if w == 0:
                        b = 0
                    else:
                        b = s / w - 1
                    bl[ch] = int(round(b))
                    print(
                        ch,
                        " bl:",
                        Fore.YELLOW,
                        "{:2d}".format(bl[ch]),
                        Style.RESET_ALL,
                        "(0x{:s})".format(hex(bl[ch])[2:].zfill(2)),
                        Fore.GREEN if w > 0 else Fore.RED,
                        "{:>+3d} mV".format(-31 + 2 * bl[ch]),
                        Style.RESET_ALL,
                        " [ ",
                        misc.bl_list_with_marker(v[c][a][ch], bl[ch]),
                        "]",
                    )

                if args.offset is None:
                    while True:
                        bbb = input("Offset for base lines (default: 0): ")
                        if bbb == "":
                            bl_offset = 0
                            break

                        if not bbb.isdigit():
                            print("Input is not a number, try again")
                            continue

                        bl_offset = int(bbb)
                        break
                else:
                    bl_offset = args.offset

                for ch in list(range(8)):

                    _r = bl[ch] + bl_offset
                    _r = max(_r, 0)
                    _r = min(_r, 127)

                    p.bl[ch] = _r  # FIXME seems to be bug

        tlist.append(t)
