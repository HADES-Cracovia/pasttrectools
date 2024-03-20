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

from pasttrec import communication, misc
from pasttrec.etrbid import ctrbids_from_etrbids
from pasttrec.requests import reset_asic

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset PASTTREC chips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    misc.parser_common_options(parser)

    args = parser.parse_args()

    communication.make_trbids_db(args.trbids, args.ignore_missing)

    etrbids = communication.decode_address(args.trbids, args.ignore_missing)
    ctrbids = ctrbids_from_etrbids(etrbids)

    with alive_bar(
        len(ctrbids),
        title=f"{Fore.BLUE}Resetting ASICs{Style.RESET_ALL}",
        file=sys.stderr,
        receipt_text=True,
    ) as bar:
        reset_asic(communication.make_cable_connections(ctrbids), bar=bar)
        bar.text("Done")
