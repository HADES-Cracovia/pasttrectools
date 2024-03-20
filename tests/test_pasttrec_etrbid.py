#!/bin/env python3

import pytest

from pasttrec import etrbid


def test_extract_strbid():
    assert etrbid.extract_strbid("0x1000:1:1") == ("0x1000", "1", "1")
    assert etrbid.extract_strbid("0x1000:1:2") == ("0x1000", "1", "2")
    assert etrbid.extract_strbid("0x1000:1") == ("0x1000", "1")
    assert etrbid.extract_strbid("0x1000::1") == ("0x1000", "", "1")
    assert etrbid.extract_strbid("0x1000") == ("0x1000",)
    assert etrbid.extract_strbid("1000") == ("0x1000",)
    with pytest.raises(ValueError):
        etrbid.extract_strbid("0x1000:1:1:1")
    with pytest.raises(ValueError):
        etrbid.extract_strbid("0a1000")
    with pytest.raises(ValueError):
        etrbid.extract_strbid("11000")


def test_expand_strbid():
    assert etrbid.expand_strbid(("0x1000", "1", "1"), 3, 3) == ((0x1000, 1, 1),)
    assert etrbid.expand_strbid(("0x1000", "2", "1"), 3, 3) == ((0x1000, 2, 1),)
    assert etrbid.expand_strbid(("0x1000", "1,2", "1"), 3, 3) == (
        (0x1000, 1, 1),
        (0x1000, 2, 1),
    )
    assert etrbid.expand_strbid(("0x1000", "", "1"), 3, 3) == (
        (0x1000, 0, 1),
        (0x1000, 1, 1),
        (0x1000, 2, 1),
    )
    assert etrbid.expand_strbid(("0x1000", "", ""), 2, 2) == (
        (0x1000, 0, 0),
        (0x1000, 0, 1),
        (0x1000, 1, 0),
        (0x1000, 1, 1),
    )
    assert etrbid.expand_strbid(("0x1000", ""), 2, 2) == (
        (0x1000, 0, 0),
        (0x1000, 0, 1),
        (0x1000, 1, 0),
        (0x1000, 1, 1),
    )


def test_trbids_from_ptrbids():
    assert etrbid.trbids_from_ptrbids(["0x1"]) == (0x1,)
    assert etrbid.trbids_from_ptrbids(("0x1",)) == (0x1,)
    assert etrbid.trbids_from_ptrbids(("0x1:1",)) == (0x1,)
    assert etrbid.trbids_from_ptrbids(("0x1:1:2",)) == (0x1,)
    assert etrbid.trbids_from_ptrbids(("0x1::2",)) == (0x1,)

    assert etrbid.trbids_from_ptrbids(("0x1", "0x2", "0x1", "0x3")) == (
        0x1,
        0x2,
        0x3,
    )
    assert etrbid.trbids_from_ptrbids(("0x1:1", "0x2:2", "0x1", "0x3")) == (
        0x1,
        0x2,
        0x3,
    )


def test_trbids_from_etrbids():
    assert etrbid.trbids_from_etrbids(((0x01, 1, 0),)) == (0x01,)
    assert etrbid.trbids_from_etrbids(
        (
            (0x01, 1, 0),
            (0x02, 2, 1),
        )
    ) == (
        0x01,
        0x02,
    )


def test_ctrbids_from_etrbids():
    assert etrbid.ctrbids_from_etrbids(((0x01, 1, 0),)) == ((0x01, 1),)
    assert etrbid.ctrbids_from_etrbids(
        (
            (0x01, 1, 0),
            (0x02, 2, 1),
        )
    ) == (
        (0x01, 1),
        (0x02, 2),
    )


def test_sort_by_ct():
    assert etrbid.sort_by_ct(((0x01, 1), (0x01, 0))) == ((0x01, 0), (0x01, 1))


def test_sort_by_tc():
    assert etrbid.sort_by_tc(((0x02, 1), (0x01, 0), (0x02, 0))) == ((0x01, 0), (0x02, 0), (0x02, 1))


def test_sort_decoded_cables():
    test_data = (
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

    for inp, outp in test_data:
        res = etrbid.ctrbids_from_etrbids(inp)
        assert res == outp
        assert etrbid.sort_by_ct(res) == tuple(sorted(outp, key=lambda tup: (tup[1], tup[0])))


def test_group_decoded_cables():
    test_data = (
        (
            (
                (8208, 0),
                (8209, 0),
                (8210, 0),
                (8208, 1),
                (8209, 1),
                (8210, 1),
                (8208, 2),
                (8209, 2),
                (8210, 2),
                (8208, 3),
                (8209, 3),
                (8210, 3),
            ),
            (
                ((8208, 0), (8209, 0), (8210, 0)),
                ((8208, 1), (8209, 1), (8210, 1)),
                ((8208, 2), (8209, 2), (8210, 2)),
                ((8208, 3), (8209, 3), (8210, 3)),
            ),
        ),
        ((), ()),
    )

    for inp, outp in test_data:
        assert etrbid.group_cables(inp) == outp


def tests_paddex_hex():
    assert etrbid.padded_hex(0xFF, 1) == "?"
    assert etrbid.padded_hex(0xFF, 2) == "0xff"
    assert etrbid.padded_hex(0xFF, 3) == "0x0ff"
    assert etrbid.padded_hex(0xFF, 4) == "0x00ff"


def tests_trbaddr():
    assert etrbid.trbaddr(0xFF) == "0x00ff"
