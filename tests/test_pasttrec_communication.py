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


def test_sort_by_cable():
    assert communication.sort_by_cable(((0x01, 1), (0x01, 0))) == ((0x01, 0), (0x01, 1))


def test_sort_decoded_cables():
    data1 = (
        (
            (
                (8208, 0, 0),
                (8208, 0, 1),
                (8208, 1, 0),
                (8208, 1, 1),
                (8208, 2, 0),
                (8208, 2, 1),
                (8208, 3, 0),
                (8208, 3, 1),
                (8209, 0, 0),
                (8209, 0, 1),
                (8209, 1, 0),
                (8209, 1, 1),
                (8209, 2, 0),
                (8209, 2, 1),
                (8209, 3, 0),
                (8209, 3, 1),
                (8210, 0, 0),
                (8210, 0, 1),
                (8210, 1, 0),
                (8210, 1, 1),
                (8210, 2, 0),
                (8210, 2, 1),
                (8210, 3, 0),
                (8210, 3, 1),
            ),
            (
                (8210, 0),
                (8209, 3),
                (8208, 1),
                (8210, 3),
                (8208, 0),
                (8210, 2),
                (8208, 3),
                (8209, 2),
                (8208, 2),
                (8209, 1),
                (8210, 1),
                (8209, 0),
            ),
        ),
    )

    for inp, outp in data1:
        res = communication.filter_decoded_cables(inp)
        assert res == outp
        assert communication.sort_by_cable(res) == tuple(sorted(outp, key=lambda tup: (tup[1], tup[0])))


def test_group_decoded_cables():
    data1 = (
        (
            (
                (8208, 0, 0),
                (8208, 0, 1),
                (8208, 1, 0),
                (8208, 1, 1),
                (8208, 2, 0),
                (8208, 2, 1),
                (8208, 3, 0),
                (8208, 3, 1),
                (8209, 0, 0),
                (8209, 0, 1),
                (8209, 1, 0),
                (8209, 1, 1),
                (8209, 2, 0),
                (8209, 2, 1),
                (8209, 3, 0),
                (8209, 3, 1),
                (8210, 0, 0),
                (8210, 0, 1),
                (8210, 1, 0),
                (8210, 1, 1),
                (8210, 2, 0),
                (8210, 2, 1),
                (8210, 3, 0),
                (8210, 3, 1),
            ),
            (
                ((8208, 0), (8209, 0), (8210, 0)),
                ((8208, 1), (8209, 1), (8210, 1)),
                ((8208, 2), (8209, 2), (8210, 2)),
                ((8208, 3), (8209, 3), (8210, 3)),
            ),
        ),
    )

    for inp, outp in data1:
        filtered_inp = communication.filter_decoded_cables(inp)
        sorted_inp = communication.sort_by_cable(filtered_inp)
        assert communication.group_cables(sorted_inp) == outp
