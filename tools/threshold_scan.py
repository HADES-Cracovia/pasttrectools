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
from time import sleep

from pasttrec import hardware, communication, misc
from pasttrec.misc import parse_rm_scalers, calc_tdc_channel

def_time = 1

def_pastrec_thresh_range = [0x00, 0x7F]


def scan_threshold(address):
    ttt = misc.Thresholds()

    connections = communication.make_asic_connections(address)

    # Store here pairs of bc address and number of channels in an endpoint
    broadcasts_list = set()
    for con in connections:
        broadcasts_list.add((con.trbid, con.fetype.n_scalers))

    print(" trbid   channel   th 0{:s}{:d}".format(" " * def_threshold_max, def_threshold_max))
    print("                      |{:s}|".format("-" * def_threshold_max))
    print("{:s}    {:s}          ".format(hex(0xFFFF), "all"), end="", flush=True)

    # loop over bl register value
    for vth in range(def_pastrec_thresh_range[0], def_threshold_max):
        print(".", end="", flush=True)

        for con in connections:
            con.write_reg(3, vth)

        sleep(0.1)
        for bc_addr, n_scalers in broadcasts_list:
            v1 = communication.read_rm_scalers(bc_addr, n_scalers)
            sleep(def_time)
            v2 = communication.read_rm_scalers(bc_addr, n_scalers)
            a1 = parse_rm_scalers(n_scalers, v1)
            a2 = parse_rm_scalers(n_scalers, v2)
            bb = a2.diff(a1)

            for con in connections:
                hex_addr = misc.trbaddr(con.trbid)

                for c in list(range(con.fetype.n_channels)):
                    chan = misc.calc_tdc_channel(con.fetype, con.cable, con.asic, c)

                    vv = bb.scalers[con.trbid][chan]
                    if vv < 0:
                        vv += 0x80000000

                    ttt.add_trb(hex_addr, con.fetype)
                    ttt.thresholds[hex_addr][con.cable][con.asic][c][vth] = vv

    print("  done")

    return ttt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan threshold of the PASTTREC chips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "trbids",
        help="list of TRBids to scan in form" " addres[:card-0-1-2[:asic-0-1]]",
        type=str,
        nargs="+",
    )

    parser.add_argument("-t", "--time", help="sleep time", type=float, default=def_time)
    parser.add_argument("-o", "--output", help="output file", type=str, default="results_th.json")
    parser.add_argument(
        "-v",
        "--verbose",
        help="verbose level: 0, 1, 2, 3",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )
    parser.add_argument(
        "-l",
        "--limit",
        help="threshold scan limit",
        type=int,
        choices=range(128),
        default=127,
    )

    parser.add_argument(
        "--defaults",
        dest="defaults",
        action="store_true",
        help="Override settings with defaults from cmd line",
    )

    parser.add_argument(
        "-Bg",
        "--source",
        help="baseline set: internally or externally",
        type=int,
        choices=[1, 0],
        default=1,
    )
    parser.add_argument(
        "-K",
        "--gain",
        help="amplification: 4, 2, 1 or 0.67 [mV/fC]",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )
    parser.add_argument(
        "-Tp",
        "--peaking",
        help="peaking time: 35, 20, 15 or 10 [ns]",
        type=int,
        choices=[3, 2, 1, 0],
        default=3,
    )

    parser.add_argument(
        "-TC1C",
        "--timecancelationC1",
        help="TC1 C: 35, 20, 15 or 10 [ns]",
        type=lambda x: int(x, 0),
        choices=range(8),
        default=3,
    )
    parser.add_argument(
        "-TC1R",
        "--timecancelationR1",
        help="TC1 R: 35, 20, 15 or 10 [ns]",
        type=lambda x: int(x, 0),
        choices=range(8),
        default=2,
    )
    parser.add_argument(
        "-TC2C",
        "--timecancelationC2",
        help="TC2 C: 35, 20, 15 or 10 [ns]",
        type=lambda x: int(x, 0),
        choices=range(8),
        default=6,
    )
    parser.add_argument(
        "-TC2R",
        "--timecancelationR2",
        help="TC2 R: 35, 20, 15 or 10 [ns]",
        type=lambda x: int(x, 0),
        choices=range(8),
        default=5,
    )

    args = parser.parse_args()

    def_time = args.time
    def_threshold_max = args.limit

    p = hardware.AsicRegistersValue(
        bg_int=args.source,
        gain=args.gain,
        peaking=args.peaking,
        tc1c=args.timecancelationC1,
        tc1r=args.timecancelationR1,
        tc2c=args.timecancelationC2,
        tc2r=args.timecancelationR2,
        vth=0,
        bl=[0] * 8,
    )

    tup = communication.decode_address(args.trbids, args.ignore_missing)

    if args.defaults:
        communication.asics_to_defaults(tup, p)

    r = scan_threshold(tup)
    r.config = p.__dict__

    if args.defaults:
        communication.asics_to_defaults(tup, p)

    with open(args.output, "w") as fp:
        json.dump(r.__dict__, fp, indent=2)
