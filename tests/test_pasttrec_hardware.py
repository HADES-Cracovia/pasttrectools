#!/bin/env python3

from pasttrec.hardware import AsicRegistersValue


def test_AsicRegistersValue():
    data = tuple(range(12))

    asic = AsicRegistersValue()

    asic.load_config(data)

    print(asic.dump_spi_config_hex())

    data2 = asic.dump_config()

    assert data2 == data
