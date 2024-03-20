#!/usr/bin/env python3
#
# Copyright 2024 Rafal Lalik <rafal.lalik@uj.edu.pl>
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


def cable_parallel_access(connections, action, data=None, post_action=None, sort=True):
    """
    Executes 'action()' for each cable parallel action.
    action() should return pair of key, value. The function
    returns distionary of all key,val pais.
    """

    results = {}
    for cable_group, cable_cons in connections:
        for con in cable_cons:
            action(con, results)

            if post_action:
                post_action()

    if sort:
        return dict(sorted(results.items()))
    else:
        return results


def asic_parallel_access(connections, action, data=None, post_action=None, sort=True):
    """
    Executes 'action()' for each cable parallel action.
    action() should return pair of key, value. The function
    returns distionary of all key,val pais.
    """

    results = {}
    for cable_group, asic_cons in connections:
        for con in asic_cons:
            if data is None:
                action(con, results)

                if post_action:
                    post_action()
            else:
                for d in data:
                    action(con, results, d)

                    if post_action:
                        post_action()

    if sort:
        return dict(sorted(results.items()))
    else:
        return results


def read_register(con, results, register):
    rc = con.read_reg(register)
    for irc in rc:
        addr = irc[0]
        faddr = (addr, con.cable, con.asic)
        if faddr not in results:
            results[faddr] = []
        results[faddr].append((register, irc[1] & 0xFF))


def write_register(con, results, register_data):
    con.write_reg(*register_data)


def activate_1wire(con, results):
    """Read temperature and/or id of given cables."""
    con.activate_1wire()


def read_1wire(con, results, uid_mode, temp_mode):
    """Read temperature and/or id of given cables."""
    full_mode = not uid_mode and not temp_mode

    rc1 = con.get_1wire_temp() if temp_mode or full_mode else ()
    rc2 = con.get_1wire_id() if uid_mode or full_mode else ()

    if len(rc1) == 0 and len(rc2) != 0:
        rc1 = ((0, 0),) * len(rc2)
    elif len(rc2) == 0 and len(rc1) != 0:
        rc2 = ((0, 0),) * len(rc1)

    group = ((x[0][0], x[0][1], x[1][1]) for x in zip(rc1, rc2))
    for entry in group:
        results[entry[0], con.cable] = entry[1], entry[2]


def read_diff_scalers(con, results, time_delta):
    print(con)
    for bc_addr, n_scalers in broadcasts_list:
        v1 = communication.read_rm_scalers(bc_addr, n_scalers)
        sleep(def_time)
        v2 = communication.read_rm_scalers(bc_addr, n_scalers)
        a1 = misc.parse_rm_scalers(n_scalers, v1)
        a2 = misc.parse_rm_scalers(n_scalers, v2)
        bb = a2.diff(a1)
        print(bb)

        for con in connections:
            hex_addr = misc.trbaddr(con.trbid)
            blv_data = []
            for c in list(range(con.fetype.n_channels)):
                blv_data.append(hardware.TrbRegistersOffsets.c_bl_reg[c])

                chan = misc.calc_tdc_channel(con.fetype, con.cable, con.asic, c)

                vv = bb.scalers[con.trbid][chan]
                if vv < 0:
                    vv += 0x80000000

                bbb.add_trb(hex_addr, con.fetype)
                bbb.baselines[hex_addr][con.cable][con.asic][c][blv] = vv

            # This line kills baseline scan for the reg #16 (last of 2nd asic
            # but do not know why. Why writing zero kills it?
            # communication.write_chunk(addr, cable, asic, blv_data)
