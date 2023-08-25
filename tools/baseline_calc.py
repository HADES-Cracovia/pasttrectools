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
from colorama import Fore, Style
import copy
import json

from pasttrec import hardware, communication, misc, output_formats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculates baselines from scan results")
    parser.add_argument("json_file", help="list of arguments", type=str)

    parser.add_argument("-o", "--output", help="output file", type=str)
    parser.add_argument("-O", "--old", help="old output format", action="store_true")
    parser.add_argument("--range", help="range based blo finder", action="store_true")

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

    parser.add_argument(
        "-blo",
        "--offset",
        help="offset to baselines (ask for" " each chip if not given)",
        type=lambda x: int(x, 0),
    )

    parser.add_argument(
        "-Vth",
        "--threshold",
        help="threshold: 0-127" " (overwrites value from input file)",
        type=lambda x: int(x, 0),
    )
    parser.add_argument(
        "-g",
        "--gain",
        help="gain: 0-3 (overwrites value" " from input file)",
        type=lambda x: int(x, 0),
    )

    args = parser.parse_args()

    communication.g_verbose = args.verbose
    if communication.g_verbose > 0:
        print(args)

    with open(args.json_file) as json_data:
        d = json.load(json_data)
        json_data.close()

    dump_file = None
    if args.dump:
        dump_file = open(args.dump, "w")

    if args.Dump:
        dump_file = open(args.Dump, "w")

    out_file = None
    if args.output:
        out_file = open(args.output, "w")

    bls = d["baselines"]
    cfg = d["config"]

    tlist = []
    p = hardware.AsicRegistersValue()

    for k, v in cfg.items():
        setattr(p, k, v)

    if args.threshold is not None:
        p.vth = args.threshold

    if args.gain is not None:
        p.gain = args.gain

    print(cfg)

    x = list(range(0, 32))

    idx = 1
    for k, v in bls.items():

        t = hardware.TdcConnection(k)

        for c in range(len(v)):  # deduce number of cards from file
            card = hardware.PasttrecCard("noname")

            for a in range(2):  # two asics
                print(Fore.YELLOW + "Processing  {:s}  CARD: {:d}  ASIC: {:d}".format(k, c, a) + Style.RESET_ALL)
                bl = [0] * 8

                for ch in list(range(8)):
                    b = v[c][a][ch]
                    s = 0
                    w = 0
                    if args.range:  # old way
                        for i in range(1, 32):
                            s = s + (i + 1) * b[i]
                            w += b[i]
                    else:
                        cnt_max = max(b)
                        # find duplicates
                        indices = [index for index, item in enumerate(b) if item == cnt_max]
                        if len(indices) == 1:
                            s = indices[0] + 1
                            w = 1
                        else:
                            w = 0
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
                #                    if w == 0:
                #                        print(Fore.RED, "All Zero - check it", Style.RESET_ALL)
                #                    else:
                #                        print(Fore.GREEN, " * OK *", Style.RESET_ALL)

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

                    p.bl[ch] = _r

                card.set_asic(a, copy.deepcopy(p))

                if args.dump:
                    regs = p.dump_config()[4:]
                    if args.old:
                        communication.cmd_to_file = dump_file
                        communication.write_chunk(k, c, a, regs)
                        communication.cmd_to_file = None
                    else:
                        output_formats.cmd_to_file = dump_file
                        output_formats.export_chunk(k, c, a, regs,
                                                    "  %s  %d  %d    %2d  %2d  %2d  %2d  %2d  %2d  %2d  %2d")

                if args.Dump:
                    regs = p.dump_config()
                    if args.old:
                        communication.cmd_to_file = dump_file
                        communication.write_chunk(k, c, a, regs)
                        communication.cmd_to_file = None
                    else:
                        output_formats.cmd_to_file = dump_file
                        output_formats.export_chunk(k, c, a, regs)

                if args.exec:
                    communication.write_chunk(k, c, a, regs)

            t.set_card(c, card)

        tlist.append(t)

    if dump_file:
        dump_file.close()

    if out_file:
        out_file.write(json.dumps(dump(tlist), indent=2))
        out_file.close()
