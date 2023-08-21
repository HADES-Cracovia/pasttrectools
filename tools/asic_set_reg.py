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

from pasttrec import communication

def_pastrec_thresh_range = [0x00, 0x7f]


def set_register(address, register, value):
    # loop over channels
    for addr, cable, asic in address:
        communication.write_reg(addr, cable, asic, register, value & 0xff)

    print("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Set PASTTREC threshold',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('trbids', help='trb address'
                        ' addres[:card-0-1-2[:asic-0-1]]', type=str)
    parser.add_argument('reg', help='register 0-12', type=int)
    parser.add_argument('val', help='value to write', type=int)

    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3',
                        type=int, choices=[0, 1, 2, 3], default=0)

    parser.add_argument('-Vth', '--threshold', help='threshold: 0-127',
                        type=lambda x: int(x, 0), default=127)

    args = parser.parse_args()

    communication.g_verbose = args.verbose

    if communication.g_verbose > 0:
        print(args)

    if args.threshold > def_pastrec_thresh_range[1] \
       or args.threshold < def_pastrec_thresh_range[0]:
        print("\nOption error: Threshold value {:d} is to high, "
              " allowed value is 0-127".format(args.threshold))
        sys.exit(1)

    ex = True

    tup = communication.decode_address(args.trbids)
    set_register(tup, args.reg, args.val)
