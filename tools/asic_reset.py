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
import sys

from alive_progress import alive_bar

from pasttrec import communication
from pasttrec.misc import trbaddr

def_spi_time = 0.0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset PASTTREC chips",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "trbids",
        help="list of TRBids to scan in form" " addres[:card-0-1-2[:asic-0-1]]",
        type=str,
        nargs="+",
    )

    parser.add_argument("-t", "--time", help="SPI sleep time", type=float, default=def_spi_time)
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
    def_spi_time = args.time

    if communication.g_verbose > 0:
        print(args)

    tup = communication.decode_address(args.trbids)
    tup = communication.filter_decoded_cables(tup)

    conns = communication.make_cable_connections(tup)

    with alive_bar(
        len(tup), title=Fore.YELLOW + "Resetting" + Style.RESET_ALL, file=sys.stderr, receipt_text=True
    ) as bar:

        for con in conns:
            con.spi.delay_asic_spi = def_spi_time

            bar.text(" {:s}:{:d}".format(trbaddr(con.trbid), con.cable))
            rc = con.reset_spi()
            bar()
        bar.text("Done")
