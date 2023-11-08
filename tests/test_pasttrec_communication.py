#!/bin/env python3

from context import *

from pasttrec import communication

def test_filter_addresses():
    assert communication.filter_address(["0x1"]) == set([0x1])
    assert communication.filter_address(["0x1:1"]) == set([0x1])
    assert communication.filter_address(["0x1:1:2"]) == set([0x1])
    assert communication.filter_address(["0x1::2"]) == set([0x1])

    assert communication.filter_address(["0x1", "0x2", "0x1", "0x3"]) == set([0x1, 0x2, 0x3])
    assert communication.filter_address(["0x1:1", "0x2:2", "0x1", "0x3"]) == set([0x1, 0x2, 0x3])
