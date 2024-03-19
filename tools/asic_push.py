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

from alive_progress import alive_bar  # type: ignore
from colorama import Fore, Style  # type: ignore

from pasttrec import communication, etrbid, hardware, misc
from pasttrec.actions import write_register

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push or dump registers to asic/file")
    parser.add_argument("dat_file", help="list of arguments", type=str, nargs="+")

    group = parser.add_mutually_exclusive_group()

    parser.add_argument("-m", "--ignore-invalid", help="ignore invalid entries", action="store_true")

    parser.add_argument(
        "-v",
        "--verbose",
        help="verbose level: 0, 1, 2, 3",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
    )

    args = parser.parse_args()

    # Get the DB of all the TRB boards, then select only those which are known to ass a TDC boards.
    # Then, decode the addresses and create cable addresses.
    db = communication.make_trbids_db((0xFFFF,), True)
    trbdb = hardware.filter_known_designs(db)
    etrbids = communication.decode_address(trbdb, False)
    ctrbids = etrbid.ctrbids_from_etrbids(etrbids)

    # Read all IDs from known TDCs boards, and create map of "uid -> ctrbid"
    with alive_bar(
        len(ctrbids),
        title=f"{Fore.BLUE}Reading IDs{Style.RESET_ALL}    ",
        file=sys.stderr,
        receipt_text=True,
    ) as bar:
        results_tempid = misc.read_tempid(communication.make_cable_connections(ctrbids), True, False, bar=bar)
        bar.text("Done")

    map_id_to_ctrbid = {hwinfo[1]: ctrbid for (ctrbid, hwinfo) in results_tempid.items() if hwinfo[1] != 0}

    for f in args.dat_file:
        with open(f) as data:
            lines = data.readlines()
            data.close()

            with alive_bar(
                len(lines),
                title=f"{Fore.BLUE}Pushing data{Style.RESET_ALL}   ",
                file=sys.stderr,
                receipt_text=True,
            ) as bar:
                for line in lines:
                    parts = line.split()

                    # do only baselines
                    if parts[0] == "b" and len(parts) == 11:
                        do_baselines = True
                        regs = range(4, 12)
                    # do full registers
                    elif parts[0] == "f" and len(parts) == 15:
                        do_full_asic = True
                        regs = range(12)
                    else:
                        if args.ignore_invalid:
                            print(f"{Fore.RED}Incorrect line:{Style.RESET_ALL} {line.strip()}", file=sys.stderr)
                            continue
                        else:
                            raise ValueError(f"Incorrect line: {line}")

                    nl = tuple((misc.convertToInt(x) for x in parts[1:]))
                    data = zip(regs, nl[2:], strict=True)

                    current_ctrbid = map_id_to_ctrbid[nl[0]]
                    dst = current_ctrbid + (nl[1],)
                    con = communication.make_asic_connections((dst,))[0][1]

                    for d in data:
                        write_register(con[0], None, d)

                    bar()
                bar.text("Done")
