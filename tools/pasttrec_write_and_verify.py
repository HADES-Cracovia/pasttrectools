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
import subprocess

from pasttrec import communication

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Write and verify data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("file", help="file to send")

    parser.add_argument(
        "-v",
        "--verbose",
        help="verbose level: 0, 1, 2, 3",
        type=int,
        choices=[0, 1, 2, 3],
        default=1,
    )

    args = parser.parse_args()

    with open(args.file) as f:
        data = f.readlines()
        for line in data:
            words = line.split()

            # write word
            rc = subprocess.run(words, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # preapre readback
            rb = words
            data = int(rb[4], 16) | 0x1000
            rb[4] = hex(data)
            # write word-read request
            if args.verbose:
                print(" ".join(words))
            rc = subprocess.run(words, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            read_cmd = words[0:4]
            read_cmd[1] = "r"
            # read data
            rc = subprocess.run(read_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ret_data = int(rc.stdout.split()[1], 16)

            orig_data = int(rb[4][-2:], 16)

            if ret_data != orig_data:
                print("Write error at line: ", " ".join(words))
                print("  written: ", hex(orig_data), "  received: ", hex(ret_data))
