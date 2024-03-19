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


def export_chunk(entry_type, uid, asic, data, format_string=None):
    if isinstance(data, (list, tuple)):
        v = tuple((x & 0xFF for x in data))
    else:
        v = data & 0xFF
    dat_write_chunk(entry_type, uid, asic, v, format_string)


def dat_write_chunk(entry_type, uid, asic, data, format_string=None):
    if format_string is None:
        format_string = "%s  %s  %d    %#04x  %#04x  %#04x    %3d    %2d  %2d  %2d  %2d  %2d  %2d  %2d  %2d"

    if cmd_to_file is not None:
        cmd_to_file.write(
            format_string
            % tuple(
                (
                    entry_type,
                    uid,
                    asic,
                )
                + data
            )
            + "\n"
        )
    else:
        print(format_string % tuple(entry_type + uid + asic + data) + "\n")
