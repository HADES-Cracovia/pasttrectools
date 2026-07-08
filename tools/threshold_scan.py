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

import sys
import argparse
import json
from time import sleep

from alive_progress import alive_bar  # type: ignore
from colorama import Fore, Style  # type: ignore

from pasttrec import communication, etrbid, hardware, misc, types

def_time = 1

def_pastrec_thresh_range = [0x00, 0x7F]


def scan_threshold(address, ttt, ctrbid_uid_map):
    connections = communication.asic_connections(address)

    # Store here pairs of bc address and number of channels in an endpoint
    broadcasts_list = set()
    for con in connections:
        broadcasts_list.add((con.trbid, con.fetype.n_scalers))

    thr_range = range(def_pastrec_thresh_range[0], def_pastrec_thresh_range[1])
    with alive_bar(
        len(thr_range),
        title=f"{Fore.BLUE}Scanning all{Style.RESET_ALL}   ",
        file=sys.stderr,
        receipt_text=True,
    ) as bar:

        for thrv in thr_range:

            for con in connections:
                thrv_data = []

                thrv_data.append(hardware.TrbRegistersOffsets.c_config_reg[3] | thrv)

                con.write_chunk(thrv_data)

            update_thresholds(ttt, ctrbid_uid_map, broadcasts_list, connections, thrv)
            bar()

        bar.text("Scanning done")

    return ttt


def update_thresholds(ttt, ctrbid_uid_map, broadcasts_list, connections, thrv):
    for bc_addr, n_scalers in broadcasts_list:
        scalers_diffs = communication.read_diff_scalers(bc_addr, n_scalers, def_time)

        for con in connections:

            for trbid, data in scalers_diffs.items():
                ctrbid = (trbid, con.cable)
                if ctrbid not in ctrbid_uid_map:
                    continue

                uid = etrbid.padded_hex(ctrbid_uid_map[ctrbid], 16)

                thrv_data = []
                for c in list(range(con.fetype.n_channels)):

                    thrv_data.append(hardware.TrbRegistersOffsets.c_baselines_reg[c])

                    chan = misc.calc_tdc_channel(con.fetype, con.cable, con.asic, c)

                    vv = data[chan]
                    if vv < 0:
                        vv += 0x80000000

                    ttt.data[uid]["results"][con.asic][c].value[thrv] = vv

                # This line kills baseline scan for the reg #16 (last of 2nd asic
                # but don't know why. Why writing zero kills it?
                # communication.write_chunk(addr, cable, asic, blv_data)


def nooop():
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

    misc.parser_common_options(parser)

    parser.add_argument("-p", "--period", help="measurement period", type=float, default=def_time)
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
        "--configure",
        dest="configure",
        action="store_true",
        help=(
            "Configure ASICs with values from command line (either given or defaults). "
            "This option is required for cmd values to take effect."
        ),
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

    def_time = args.period
    def_threshold_max = args.limit

    pasttrec_config = hardware.AsicRegistersValue(
        bg_int=args.source,
        gain=args.gain,
        peaking=args.peaking,
        tc1c=args.timecancelationC1,
        tc1r=args.timecancelationR1,
        tc2c=args.timecancelationC2,
        tc2r=args.timecancelationR2,
        threshold=0,
        baselines=[0] * 8,
    )

    db = communication.make_trbids_db(args.trbids, args.ignore_missing)

    etrbids = communication.decode_address(args.trbids, args.ignore_missing)
    ctrbids = etrbid.ctrbids_from_etrbids(etrbids)

    # FIXME we should have some restore/configure mode
    # if args.configure:
    communication.asics_configure(etrbids, pasttrec_config)

    with alive_bar(
        len(ctrbids),
        title=f"{Fore.BLUE}Reading IDs{Style.RESET_ALL}    ",
        file=sys.stderr,
        receipt_text=True,
    ) as bar:
        results_tempid = misc.read_tempid(communication.make_cable_connections(ctrbids), True, False, bar=bar)
        bar.text("Done")

    filtered_cards = {k: v[1] for k, v in results_tempid.items() if v[1] != 0}
    tempid_map = {v: k for k, v in filtered_cards.items()}
    thresholds = types.Thresholds()

    for k, v in filtered_cards.items():
        design_info = db[k[0]]
        design_specs = hardware.get_design_specs(design_info.features)
        thresholds.add_card(v, design_specs)

    r = scan_threshold(etrbids, thresholds, filtered_cards)
    # r.config = pasttrec_config.__dict__
    for k, v in thresholds.data.items():
        v["config"] = dict(pasttrec_config.__dict__)

    # FIXME we should have some restore/configure mode
    # if args.configure:
    communication.asics_configure(etrbids, pasttrec_config)

    with open(args.output, "w") as fp:
        json.dump(r.data, fp, indent=4, cls=types.MyEncoder)
