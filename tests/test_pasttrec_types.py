#!/bin/env python3

import pytest

from pasttrec import types
from pasttrec import hardware


def test_pasttrec_noindent():
    n = types.NoIndent(())
    assert str(n) == "()"

    d = (0, 3, 7)
    n = types.NoIndent(d)
    assert str(n) == str(d)
    assert repr(n) == "NoIndent(" + str(d) + ")"

    d = [0, 3, 7]
    n = types.NoIndent(d)
    assert str(n) == str(d)
    assert repr(n) == "NoIndent(" + str(d) + ")"

    with pytest.raises(TypeError):
        n = types.NoIndent(0)


def test_pasttrec_baselines():
    obj = types.Baselines()

    obj.add_card(0x01, hardware.TrbDesignSpecs.TRB5SC_16CH)

    assert obj.data["0x0000000000000001"]["config"] is None
    assert obj.data["0x0000000000000001"]["results"] == [
        [
            types.NoIndent(
                [
                    0,
                ]
                * 32
            )
        ]
        * 8,
        [
            types.NoIndent(
                [
                    0,
                ]
                * 32
            )
        ]
        * 8,
    ]


def test_pasttrec_thresholds():
    obj = types.Thresholds()

    obj.add_card(0x01, hardware.TrbDesignSpecs.TRB5SC_16CH)

    assert obj.data["0x0000000000000001"]["config"] is None
    assert obj.data["0x0000000000000001"]["results"] == [
        [
            types.NoIndent(
                [
                    0,
                ]
                * 128
            )
        ]
        * 8,
        [
            types.NoIndent(
                [
                    0,
                ]
                * 128
            )
        ]
        * 8,
    ]
