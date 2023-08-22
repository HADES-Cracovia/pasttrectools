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

cmd_to_file = None  # if set to file, redirect output to this file
bgs = "    "
igs = "  "


def export_chunk(trbid, cable, asic, data):
    if isinstance(data, list):
        v = [x & 0xFF for x in data]
    else:
        v = data & 0xFF
    dat_write_chunk(trbid, cable, asic, v)


def dat_write_chunk(trbid, cable, asic, data, hexflags=[1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]):
    zdata = list(zip(data, hexflags))
    fdata = [trbid, str(cable), str(asic)] + [hex(x[0]) if x[1] else str(x[0]).rjust(2) for x in zdata]

    if cmd_to_file is not None:
        cmd_to_file.write(
            "  " + igs.join(fdata[0:3]) + bgs + igs.join(fdata[3:6]) + bgs + fdata[6] + bgs + igs.join(fdata[7:]) + "\n"
        )
    else:
        print("  " + "  ".join(fdata) + "\n")
