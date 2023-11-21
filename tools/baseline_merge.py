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

import os
import argparse
import json

from pasttrec import communication, misc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge baseline scans of PASTTREC chips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("files", help="files to merge", type=str, nargs="+")

    parser.add_argument(
        "-o", "--output", help="output file", type=str, default="merged.json"
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

    communication.g_verbose = args.verbose

    if communication.g_verbose > 0:
        print(args)

    if args.output:
        out_file = open(args.output, "w")

    b = misc.Baselines()

    d = None
    for filename in args.files:
        print(filename)
        with open(filename) as json_data:
            d = json.load(json_data)
            json_data.close()

        out_file = None

        bls = d["baselines"]
        cfg = d["config"]

        if b.config is None:
            b.config = d["config"]

        barename = os.path.splitext(filename)[0]
        trbid = barename.split("_")[-1]

        tup = communication.decode_address(trbid)

        for addr, card, asic in tup:
            b.add_trb(addr)
            b.baselines[addr][card][asic] = bls[addr][card][asic]

    with open(args.output, "w") as fp:
        json.dump(b.__dict__, fp, indent=2)
