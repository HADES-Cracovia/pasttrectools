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

from alive_progress import alive_bar  # type: ignore
from colorama import Fore, Style  # type: ignore
from tabulate import tabulate  # type: ignore

from pasttrec import communication, misc
from pasttrec.etrbid import trbaddr, padded_hex


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scan communication of PASTTREC chips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    misc.parser_common_options(parser)

    parser.add_argument("-i", "--infinite", help="quick test", action="store_true")

    args = parser.parse_args()

    db = communication.make_trbids_db(args.trbids, args.ignore_missing)

    rows = tuple(
        (
            f"{Fore.YELLOW}{trbaddr(trbid)}{Style.RESET_ALL}",
            f"{Fore.GREEN}{padded_hex(data.hwtype, 8)}{Style.RESET_ALL}",
            f"{Fore.BLUE}{padded_hex(data.features, 16)}{Style.RESET_ALL}",
            f"{' '.join(tuple(trbaddr(x) for x in data.responders))}",
        )
        for trbid, data in sorted(db.items())
    )

    colalign = ("left",) * 4
    header = ("Address", "HW Type", "Features", "Responders")

    if len(rows):
        print(tabulate(rows, headers=header, colalign=colalign))
