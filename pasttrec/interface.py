#!/usr/bin/env python3
#
# Copyright 2023 Rafal Lalik <rafal.lalik@uj.edu.pl>
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

"""
This module provides implementation for various interfaces, like libtrbnet and shell.
"""

import abc

from pasttrec.etrbid import trbaddr
import subprocess


def group_output(trb_response):
    return tuple(tuple(trb_response[i : i + 2]) for i in range(0, len(trb_response), 2))


class TrbNetComInterface(metaclass=abc.ABCMeta):
    """A TrbMetaclass that will be used for trb interface class creation."""

    @classmethod
    def __subclasshook__(self, subclass):
        return (
            hasattr(subclass, "print_verbose")
            and callable(subclass.print_verbose)
            and hasattr(subclass, "write")
            and callable(subclass.write)
            and hasattr(subclass, "write_mem")
            and callable(subclass.write_mem)
            and hasattr(subclass, "read")
            and callable(subclass.read)
            and hasattr(subclass, "read_mem")
            and callable(subclass.read_mem)
            or NotImplemented
        )

    @abc.abstractmethod
    def print_verbose(self, rc):
        """Print verbose return info from trbnet communication"""
        raise NotImplementedError

    @abc.abstractmethod
    def write(self, trbid, reg, data):
        raise NotImplementedError

    @abc.abstractmethod
    def write_mem(self, trbid, reg, data, option=1):
        raise NotImplementedError

    @abc.abstractmethod
    def read(self, trbid, reg):
        raise NotImplementedError

    @abc.abstractmethod
    def read_mem(self, trbid, reg, length, option=1):
        """
        Read memory block.
        Function return of map where the key is the trb address and value is tuple of memory block
        """
        raise NotImplementedError


class TrbNetComLib:
    trbnet = None

    def __init__(self, trbnet):
        self.trbnet = trbnet

    def print_verbose(self, rc):
        """Print verbose return info from trbnet communication"""

        if rc is None:
            return

        print("[{:s}]  {:d}".format(hex(rc[0]), rc[1]))

    def write(self, trbid, reg, data):
        self.trbnet.trb_register_write(trbid, reg, data)
        # self.print_verbose(rc)

    def write_mem(self, trbid, reg, data, option=1):
        self.trbnet.trb_register_write_mem(trbid, reg, option, data)

    def read(self, trbid, reg):
        rc = self.trbnet.trb_register_read(trbid, reg)
        # self.print_verbose(rc)
        if len(rc):
            return group_output(rc)
        else:
            raise ValueError("Trbid {:s} not available".format(trbaddr(trbid)))

    def read_mem(self, trbid, reg, length, option=1):
        """
        Read memory block.
        Function return of map where the key is the trb address and value is tuple of memory block
        """
        rc = self.trbnet.trb_register_read_mem(trbid, reg, option, length)
        # self.print_verbose(rc)
        i = 0
        res = {}
        while i < len(rc):
            data = rc[i]
            partial_len = (data & 0xFFFF0000) >> 16
            res[data & 0xFFFF] = tuple(rc[i + 1 : i + 1 + partial_len])
            i = i + 1 + partial_len
        return res


class TrbNetComShell:
    def print_verbose(self, rc):
        """Print verbose return info from trbnet communication"""

        if rc is None:
            return

        print("[{:s}]  {:d}".format(hex(rc[0]), rc[1]))

    def write(self, trbid, reg, data):
        cmd = ["trbcmd", "w", hex(trbid), hex(reg), hex(data)]
        """
        if cmd_to_file is not None:
            cmd_to_file.write(' '.join(cmd) + '\n')
            return True
        """
        rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # self.print_verbose(rc)
        return rc.stdout.decode()

    def write_mem(self, trbid, reg, data, option=1):
        """
        if cmd_to_file is not None:
            cmd = ['trbcmd', 'wm', hex(trbid), hex(reg), str(mode), '- << EOF']
            cmd_to_file.write(' '.join(cmd) + '\n')
            for d in data:
                cmd_to_file.write(hex(d) + '\n')
            cmd_to_file.write('EOF\n')
            return True
        """
        cmd = ["trbcmd", "wm", hex(trbid), hex(reg), str(option), "-"]
        _data = "\n".join([hex(x) for x in data])
        rc = subprocess.run(
            cmd,
            input=_data.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # self.print_verbose(rc)
        return rc.stdout.decode()

    def read(self, trbid, reg):
        cmd = ["trbcmd", "r", hex(trbid), hex(reg)]
        """
        if cmd_to_file is not None:
            cmd_to_file.write(' '.join(cmd) + '\n')
            return True
        """

        rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            return group_output(tuple((int(x, 16) for x in rc.stdout.decode().split())))
        except IndexError:
            return 0xDEADBEEF  # TODO Add exceptions

    def read_mem(self, trbid, reg, length, option=1):
        cmd = ["trbcmd", "rm", hex(trbid), hex(reg), str(length), "0"]
        """
        if cmd_to_file is not None:
            cmd_to_file.write(' '.join(cmd) + '\n')
            return True
        """
        rc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # self.print_verbose(rc)
        return rc.stdout.decode()
