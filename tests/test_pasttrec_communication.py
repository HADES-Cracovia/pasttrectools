#!/bin/env python3

from context import *

from pasttrec import communication


def test_decode_address():
    pass


def test_filter_raw_trbids():
    assert communication.filter_raw_trbids(["0x1"]) == (0x1,)
    assert communication.filter_raw_trbids(("0x1",)) == (0x1,)
    assert communication.filter_raw_trbids(("0x1:1",)) == (0x1,)
    assert communication.filter_raw_trbids(("0x1:1:2",)) == (0x1,)
    assert communication.filter_raw_trbids(("0x1::2",)) == (0x1,)

    assert communication.filter_raw_trbids(("0x1", "0x2", "0x1", "0x3")) == (
        0x1,
        0x2,
        0x3,
    )
    assert communication.filter_raw_trbids(("0x1:1", "0x2:2", "0x1", "0x3")) == (
        0x1,
        0x2,
        0x3,
    )


def test_filter_decoded_trbids():
    assert communication.filter_decoded_cables(((0x01, 1, 0),)) == ((0x01, 1),)
    assert communication.filter_decoded_cables(((0x01, 1, 0), (0x02, 2, 1),)) == (
        (0x01, 1),
        (0x02, 2),
    )


def test_filter_decoded_cables():
    assert communication.filter_decoded_cables(((0x01, 1, 0),)) == ((0x01, 1),)
    assert communication.filter_decoded_cables(((0x01, 1, 0), (0x02, 2, 1),)) == (
        (0x01, 1),
        (0x02, 2),
    )
