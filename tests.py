#!/bin/env python3

import json
import os
import unittest

from pasttrec import hardware, LIBVERSION

import tempfile


class TestPasstreRegs(unittest.TestCase):
    pass


class TestTdc(unittest.TestCase):

    p01 = hardware.AsicRegistersValue(vth=1)
    p02 = hardware.AsicRegistersValue(vth=2)
    p03 = hardware.AsicRegistersValue(vth=3)
    p04 = hardware.AsicRegistersValue(vth=3)

    p11 = hardware.AsicRegistersValue(vth=11)
    p12 = hardware.AsicRegistersValue(vth=12)
    p13 = hardware.AsicRegistersValue(vth=13)
    p14 = hardware.AsicRegistersValue(vth=14)

    c0 = hardware.PasttrecCard('C001', p01, p02)
    c1 = hardware.PasttrecCard('C002', p03, p11)
    c2 = hardware.PasttrecCard('C003', p12, p13)

    t0 = hardware.TdcConnection(0x6400, c0, None, c1)
    t1 = hardware.TdcConnection(0x6401, None, c2, None)

    def test_creation(self):
        self.assertEqual("0x6400", self.t0.id)

        self.assertNotEqual(None, self.t0.cable1)
        self.assertEqual(None, self.t0.cable2)
        self.assertNotEqual(None, self.t0.cable3)

        self.assertEqual(None, self.t1.cable1)
        self.assertNotEqual(None, self.t1.cable2)
        self.assertEqual(None, self.t1.cable3)

    def test_dump_and_load(self):
        res = hardware.dump(self.t0)
        self.assertEqual(LIBVERSION, res['version'])
        self.assertEqual(len(res), 2)

        res = hardware.dump([self.t0, self.t1])
        self.assertEqual(len(res), 3)

        tf = tempfile.NamedTemporaryFile(mode='w+', delete=False)

        json.dump(res, tf, indent=2)
        tf.close()

        with open(tf.name) as fp:
            dl = json.load(fp)

        r, con = hardware.load(dl)

        self.assertNotEqual(None, con[0].cable1)
        self.assertEqual(None, con[0].cable2)
        self.assertNotEqual(None, con[0].cable3)

        self.assertEqual(None, con[1].cable1)
        self.assertNotEqual(None, con[1].cable2)
        self.assertEqual(None, con[1].cable3)

        dc = hardware.dump(con)
        self.assertEqual(res, dc)

        os.remove(tf.name)


if __name__ == '__main__':
    unittest.main()
