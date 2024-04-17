#!/bin/env python3

from pasttrec.hardware import AsicRegistersValue


def test_load_asic_from_dict():
    data = {
        "bg_int": 1,
        "gain": 0,
        "peaking": 2,
        "tc1c": 3,
        "tc1r": 6,
        "tc2c": 2,
        "tc2r": 5,
        "vth": 0,
        "bl": [1, 2, 3, 4, 5, 6, 7, 8],
    }

    asic = AsicRegistersValue().load_asic_from_dict(data)

    assert asic.dump_registers() == (18, 30, 21, 0, 1, 2, 3, 4, 5, 6, 7, 8)
    assert asic.dump_values() == (1, 0, 2, 3, 6, 2, 5, 0, 1, 2, 3, 4, 5, 6, 7, 8)


def test_AsicRegistersValue():
    data = tuple(range(12))

    asic = AsicRegistersValue()

    asic.load_config(data)

    print(asic.dump_spi_config_hex())

    data2 = asic.dump_registers()

    assert data2 == data
