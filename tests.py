#!/bin/env python3

import json
import os
import unittest

import baseline
from pasttrec import *

import tempfile

class TestPasstreRegs(unittest.TestCase):
    pass

class TestTdc(unittest.TestCase):

    p01 = PasttrecRegs(vth=1)
    p02 = PasttrecRegs(vth=2)
    p03 = PasttrecRegs(vth=3)
    p04 = PasttrecRegs(vth=3)

    p11 = PasttrecRegs(vth=11)
    p12 = PasttrecRegs(vth=12)
    p13 = PasttrecRegs(vth=13)
    p14 = PasttrecRegs(vth=14)

    c0 = PasttrecCard('C001', p01, p02)
    c1 = PasttrecCard('C002', p03, p11)
    c2 = PasttrecCard('C003', p12, p13)

    t0 = TdcConnection(0x6400, c0, None, c1)
    t1 = TdcConnection(0x6401, None, c2, None )

    def test_creation(self):
        self.assertEqual("0x6400", self.t0.id)

        self.assertNotEqual(None, self.t0.cable1)
        self.assertEqual(None, self.t0.cable2)
        self.assertNotEqual(None, self.t0.cable3)

        self.assertEqual(None, self.t1.cable1)
        self.assertNotEqual(None, self.t1.cable2)
        self.assertEqual(None, self.t1.cable3)

    def test_dump_and_load(self):
        res = dump(self.t0)
        self.assertEqual(LIBVERSION, res['version'])
        self.assertEqual(len(res), 2)

        res = dump([self.t0, self.t1])
        self.assertEqual(len(res), 3)

        tf = tempfile.NamedTemporaryFile(mode='w+', delete=False)

        json.dump(res, tf, indent=2)
        tf.close()

        with open(tf.name) as fp:
            dl = json.load(fp)

        r, con = load(dl)

        self.assertNotEqual(None, con[0].cable1)
        self.assertEqual(None, con[0].cable2)
        self.assertNotEqual(None, con[0].cable3)

        self.assertEqual(None, con[1].cable1)
        self.assertNotEqual(None, con[1].cable2)
        self.assertEqual(None, con[1].cable3)

        dc = dump(con)
        self.assertEqual(res, dc)

        os.remove(tf.name)

if __name__ == '__main__':
    unittest.main()
