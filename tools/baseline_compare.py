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
import json

try:
    import numpy as np
    import gnuplotlib as gp

    found = True
except ModuleNotFoundError:
    # Error handling
    np = None
    gp = None
    found = False

from pasttrec import communication


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculates baselines from scan results")
    parser.add_argument("json_file1", help="file1", type=str)
    parser.add_argument("json_file2", help="file2", type=str)

    parser.add_argument("-o", "--output", help="output file", type=str)

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

    with open(args.json_file1) as json_data:
        d1 = json.load(json_data)
        json_data.close()

    with open(args.json_file2) as json_data:
        d2 = json.load(json_data)
        json_data.close()

    diffbls = d1.copy()
    stats = {}

    dbl = []

    for k, v in d1.items():

        if k == "version":
            continue

        if k not in d1:
            print("JSON2 has no key {:s}", k)

        for c in [0, 1, 2]:
            card = "cable{:d}".format(c + 1)

            for a in [0, 1]:
                asic = "asic{:d}".format(a + 1)
                print(
                    Fore.YELLOW + "Comparing {:s}  CARD: {:d}  ASIC: {:d}".format(k, c, a) + Style.RESET_ALL,
                    end="",
                )
                bldiff = [0] * 8

                print("    bl:", Style.RESET_ALL, " ", end="")

                for ch in list(range(8)):
                    bldiff[ch] = d2[k][card][asic]["bl"][ch] - d1[k][card][asic]["bl"][ch]

                    x = bldiff[ch]
                    if x == 0:
                        print(Fore.GREEN, x, " ", end="")
                    elif abs(x) == 1:
                        print(Fore.YELLOW, x, " ", end="")
                    else:
                        print(Fore.RED, x, " ", end="")

                    if x in stats:
                        stats[x] += 1
                    else:
                        stats[x] = 1

                    dbl.append(x)

                print(Style.RESET_ALL)

    print("STATS: ", stats)

    if found:
        g1 = gp.gnuplotlib(title="Baseline difference statistics", terminal="dumb 100,40")
        xx = np.arange(-31, 32, 1)
        yy = np.array([stats[x] if x in stats else 0 for x in xx])

        g1.plot((xx, yy, {"with": "impulses"}), _with="lines", unset="grid")

#        z = np.arange(1000)
#        g1.plot((np.array(dbl), dict(histogram = 'freq', binwidth=1)), unset='grid')
