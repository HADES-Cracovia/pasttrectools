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
from time import sleep
import json

from alive_progress import alive_bar  # type: ignore
from colorama import Fore, Style  # type: ignore

from pasttrec import communication, etrbid, hardware, misc, requests, types
from pasttrec.misc import parser_common_options
from pasttrec.requests import write_asic

def_time = 1

def_max_bl_register_steps = 32
def_pastrec_thresh_range = [0x00, 0x7F]
def_pastrec_bl_base = 0x00000
def_pastrec_bl_range = [0x00, def_max_bl_register_steps]


def update_baselines(bbb, ctrbid_uid_map, broadcasts_list, connections, blv):
    for bc_addr, n_scalers in broadcasts_list:
        scalers_diffs = communication.read_diff_scalers(bc_addr, n_scalers, def_time)

        for con in connections:

            for trbid, data in scalers_diffs.items():
                ctrbid = (trbid, con.cable)
                if ctrbid not in ctrbid_uid_map:
                    continue

                uid = etrbid.padded_hex(ctrbid_uid_map[ctrbid], 16)

                blv_data = []
                for c in list(range(con.fetype.n_channels)):

                    blv_data.append(hardware.TrbRegistersOffsets.c_bl_reg[c])

                    chan = misc.calc_tdc_channel(con.fetype, con.cable, con.asic, c)

                    vv = data[chan]
                    if vv < 0:
                        vv += 0x80000000

                    bbb.baselines[uid]["results"][con.asic][c].value[blv] = vv

                # This line kills baseline scan for the reg #16 (last of 2nd asic
                # but dunno why. Why writing zero kills it?
                # communication.write_chunk(addr, cable, asic, blv_data)


def scan_baseline_single(address, bbb, ctrbid_uid_map):
    connections = communication.asic_connections(address)

    # Store here pairs of bc address and number of channels in an endpoint
    broadcasts_list = set()
    for con in connections:
        broadcasts_list.add((con.trbid, con.fetype.n_scalers))

    bl_range = range(def_pastrec_bl_range[0], def_pastrec_bl_range[1])

    for c in list(range(8)):  # FIXME do not use magic number
        with alive_bar(
            len(bl_range),
            title=f"{Fore.BLUE}Scanning ch={c}{Style.RESET_ALL}  ",
            file=sys.stderr,
            receipt_text=True,
        ) as bar:

            for blv in range(def_pastrec_bl_range[0], def_pastrec_bl_range[1]):
                for con in connections:
                    con.write_reg(4 + c, blv)

                update_baselines(bbb, ctrbid_uid_map, broadcasts_list, connections, blv)
                bar()

            bar.text("Scanning done")

    return bbb


def scan_baseline_multi(address, bbb, ctrbid_uid_map):
    connections = communication.asic_connections(address)

    # Store here pairs of bc address and number of channels in an endpoint
    broadcasts_list = set()
    for con in connections:
        broadcasts_list.add((con.trbid, con.fetype.n_scalers))

    bl_range = range(def_pastrec_bl_range[0], def_pastrec_bl_range[1])
    with alive_bar(
        len(bl_range),
        title=f"{Fore.BLUE}Scanning all{Style.RESET_ALL}   ",
        file=sys.stderr,
        receipt_text=True,
    ) as bar:

        for blv in bl_range:

            for con in connections:
                blv_data = []

                for c in list(range(con.fetype.n_channels)):
                    blv_data.append(hardware.TrbRegistersOffsets.c_bl_reg[c] | blv)

                con.write_chunk(blv_data)

            update_baselines(bbb, ctrbid_uid_map, broadcasts_list, connections, blv)
            bar()

        bar.text("Scanning done")

    return bbb


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan baseline of the PASTTREC chips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    misc.parser_common_options(parser)

    parser.add_argument("-t", "--time", help="sleep time", type=float, default=def_time)
    parser.add_argument("-o", "--output", help="output file", type=str, default="results_bl.json")
    parser.add_argument(
        "-s",
        "--scan",
        help="scan type: singel-low/high:"
        " one channel at a time, baseline set to low/high,"
        " multi: all channels parallel",
        choices=["single-low", "single-high", "multi"],
        default="multi",
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
        choices=(0, 1, 2, 3),
        default=0,
    )
    parser.add_argument(
        "-Tp",
        "--peaking",
        help="peaking time: 35, 20, 15 or 10 [ns]",
        type=int,
        choices=(3, 2, 1, 0),
        default=2,
    )

    parser.add_argument(
        "-TC1C",
        help="TC1 C: 0-7",
        type=lambda x: int(x, 0),
        choices=range(8),
        default=3,
    )
    parser.add_argument(
        "-TC1R",
        help="TC1 R: 0-7",
        type=lambda x: int(x, 0),
        choices=range(8),
        default=6,
    )
    parser.add_argument(
        "-TC2C",
        help="TC2 C: 0-7",
        type=lambda x: int(x, 0),
        choices=range(8),
        default=2,
    )
    parser.add_argument(
        "-TC2R",
        help="TC2 R: 0-7",
        type=lambda x: int(x, 0),
        choices=range(8),
        default=5,
    )

    parser.add_argument(
        "-Vth",
        "--threshold",
        help="threshold: 0-127",
        type=lambda x: int(x, 0),
        choices=range(128),
        default=0,
    )

    args = parser.parse_args()

    def_time = args.time

    if args.threshold > def_pastrec_thresh_range[1] or args.threshold < def_pastrec_thresh_range[0]:
        print("\nOption error: Threshold value {:d} is to high," " allowed value is 0-127".format(args.threshold))
        sys.exit(1)

    # scan type
    def_scan_type = args.scan
    if def_scan_type == "single-low":
        def_pastrec_bl_base = def_pastrec_bl_range[0]
    elif def_scan_type == "single-high":
        def_pastrec_bl_base = def_pastrec_bl_range[1] - 1
    elif def_scan_type == "multi":
        def_pastrec_bl_base = def_pastrec_bl_range[0]

    p = hardware.AsicRegistersValue(
        bg_int=args.source,
        gain=args.gain,
        peaking=args.peaking,
        tc1c=args.TC1C,
        tc1r=args.TC1R,
        tc2c=args.TC2C,
        tc2r=args.TC2R,
        vth=args.threshold,
        bl=[def_pastrec_bl_base] * 8,
    )

    db = communication.make_trbids_db(args.trbids, args.ignore_missing)

    etrbids = communication.decode_address(args.trbids, args.ignore_missing)
    ctrbids = etrbid.ctrbids_from_etrbids(etrbids)

    if args.defaults:
        communication.asics_to_defaults(etrbids, p)

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
    baselines = types.Baselines()

    for k, v in filtered_cards.items():
        design_info = db[k[0]]
        design_specs = hardware.get_design_specs(design_info.features)
        baselines.add_card(v, design_specs)

    if def_scan_type == "multi":
        r = scan_baseline_multi(etrbids, baselines, filtered_cards)
    else:
        r = scan_baseline_single(etrbids, baselines, filtered_cards)

    for k, v in baselines.baselines.items():
        v["config"] = dict(p.__dict__)

    if args.defaults:
        communication.asics_to_defaults(etrbids, p)

    with open(args.output, "w") as fp:
        json.dump(r.baselines, fp, indent=4, cls=types.MyEncoder)
