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
import sys
import glob
import argparse
from time import sleep
import json
import math
import curses
from colorama import Fore, Style

from pasttrec import *

def_time = 0
def_diffs = False
prev_scalers = None

def_broadcast_addr = 0xfe4c
def_max_bl_register_steps = 32
def_pastrec_thresh_range = [0x00, 0x7f]
def_pastrec_channel_range = 8
def_pastrec_bl_base = 0x00000
def_pastrec_bl_range = [0x00, def_max_bl_register_steps]

par_address = None
par_loop = None


def show_scalers(stdscr):
    global prev_scalers
    global def_diffs

    v1 = read_rm_scalers(def_broadcast_addr)
    a1 = parse_rm_scalers(v1)
    if prev_scalers is not None and def_diffs:
        ss = a1.diff(prev_scalers)
    else:
        ss = a1
    prev_scalers = a1

    ntdsc = len(ss.scalers)

    field_width = 10
    height, width = stdscr.getmaxyx()
    maxnx = min(ntdsc, (width-field_width)/field_width)
    maxny = min(48, height-1)

    stdscr.clear()
    stdscr.addstr(0, 0, "R={:.2f} s".format(def_time), curses.A_DIM)

    for chan in range(int(maxny)):
        stdscr.addstr(chan+1, 0, "Chan {:#3d}  ".format(chan), curses.A_STANDOUT)

    cnt = 0
    for tdc in sorted(ss.scalers):
        if cnt > int(maxnx)-1:
            break
        stdscr.addstr(0, field_width + cnt*field_width,
                      "{:>{}s}".format(tdc[:field_width], field_width),
                      curses.A_STANDOUT)
        for n in range(int(maxny)):
            stdscr.addstr(1+n, field_width + cnt*field_width,
                          "{:>#{}d}".format(ss.scalers[tdc][n], field_width),
                          curses.A_BOLD)
        cnt = cnt + 1


def scan_scalers(stdscr):
    # Clear screen
    global def_diffs

    stdscr.nodelay(True)

    if par_loop is not None:
        while True:
            show_scalers(stdscr)
            stdscr.refresh()
            c = stdscr.getch()
            if c == ord('d'):
                pass
                def_diffs = 1 - def_diffs
            elif c == ord('q'):
                break  # Exit the while loop
            elif c == curses.KEY_HOME:
                x = y = 0
            sleep(def_time)

    else:
        show_scalers(stdscr)
        stdscr.refresh()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Scan baseline of the PASTTREC chips',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    #parser.add_argument('trbids', help='list of TRBids to scan in form'
                        #' addres[:card-0-1-2[:asic-0-1]]', type=str, nargs="+")

    parser.add_argument('-d', '--diffs', help='show differences',
                        action='store_true')

    parser.add_argument('-t', '--time', help='sleep time',
                        type=float, default=def_time)

    args = parser.parse_args()

    def_time = args.time
    def_diffs = args.diffs

    if def_time > 0:
        par_loop = True

    par_address = 0xfe4c  # args.trbids
    curses.wrapper(scan_scalers)
