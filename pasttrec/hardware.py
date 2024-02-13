"""
This module provides generic structures describing various hardware components.

This includes:
* the TrbNet registers to communicate with Pasttrec
* the Pasttrec card with peripherials
* the Pasttrec ASIC with internal registers
The functions provide also export/import of the components settings.
"""

from enum import Enum

from pasttrec import LIBVERSION
from pasttrec.trb_spi import SpiTrbTdc


class AsicRegisters(Enum):
    CFG = 0
    TC1 = 1
    TC2 = 2
    VTH = 3
    BL0 = 4
    BL1 = 5
    BL2 = 6
    BL3 = 7
    BL4 = 8
    BL5 = 9
    BL6 = 10
    BL7 = 11


class AsicRegistersValue:
    bg_int = 1
    gain = 0
    peaking = 0
    tc1c = 0
    tc1r = 0
    tc2c = 0
    tc2r = 0
    vth = 0
    bl = [0] * 8

    def __init__(
        self,
        bg_int=1,
        gain=0,
        peaking=0,
        tc1c=0,
        tc1r=0,
        tc2c=0,
        tc2r=0,
        vth=0,
        bl=[0] * 8,
    ):
        self.bg_int = bg_int
        self.gain = gain
        self.peaking = peaking
        self.tc1c = tc1c
        self.tc1r = tc1r
        self.tc2c = tc2c
        self.tc2r = tc2r
        self.vth = vth
        self.bl = [i for i in bl]

    @staticmethod
    def load_asic_from_dict(d, test_version=None):
        if (test_version is not None) and (test_version != LIBVERSION):
            return False
        p = AsicRegistersValue()
        for k, v in d.items():
            setattr(p, k, v)
        return p

    def dump_config(self):
        r_all = [0] * 12
        t = (self.bg_int << 4) | (self.gain << 2) | self.peaking
        r_all[0] = TrbRegistersOffsets.c_config_reg[0] | t
        t = (self.tc1c << 3) | self.tc1r
        r_all[1] = TrbRegistersOffsets.c_config_reg[1] | t
        t = (self.tc2c << 3) | self.tc2r
        r_all[2] = TrbRegistersOffsets.c_config_reg[2] | t
        r_all[3] = TrbRegistersOffsets.c_config_reg[3] | self.vth

        for i in range(8):
            r_all[4 + i] = TrbRegistersOffsets.c_bl_reg[i] | self.bl[i]

        return r_all

    def dump_config_hex(self):
        return [hex(i) for i in self.dump_config()]

    def dump_bl_hex(self):
        return [hex(i) for i in self.dump_config()[4:]]


class TrbBoardType(Enum):
    """Use it to discriminate between different frontend types."""

    TRB3 = (3, 2, 0xFE4C, SpiTrbTdc)
    TRB5SC = (4, 2, 0xFE81, SpiTrbTdc)

    def __init__(self, cables, asics, broadcast, spi):
        self.cables = cables
        self.asics = asics
        self.broadcast = broadcast
        self.channels = 8
        self.spi_protocol = spi

    @property
    def n_cables(self):
        return self.cables

    @property
    def n_asics(self):
        return self.asics

    @property
    def n_channels(self):
        return self.channels

    @property
    def n_scalers(self):
        return self.asics * self.cables * self.channels

    @property
    def spi(self):
        return self.spi_protocol


TrbBoardTypeMapping = {
    0x91000000: TrbBoardType.TRB3,
    0xA5000000: TrbBoardType.TRB5SC,
}


class PasttrecDataWordEncoder:
    """This class describes hwo different data frames are created for Pasttrec."""

    c_asic = [0x2000, 0x4000]
    # reg desc.: g_int,K,Tp      TC1      TC2      Vth
    c_config_reg = [0x00000, 0x00100, 0x00200, 0x00300]
    c_bl_reg = [0x00400, 0x00500, 0x00600, 0x00700, 0x00800, 0x00900, 0x00A00, 0x00B00]
    c_base_w = 0x0050000
    c_base_r = 0x0051000
    bl_register_size = 32

    def write(self, asic, reg, val):
        return self.c_base_w | self.c_asic[asic] | (reg << 8) | val

    def read(self, asic, reg):
        return self.c_base_r | self.c_asic[asic] | (reg << 8)

    def write_data(self, asic, data):
        if isinstance(data, list):
            return [self.c_base_w | self.c_asic[asic] | x for x in data]
        else:
            return self.c_base_w | self.c_asic[asic] | data

    def write_chunk(self, asic, data):
        if isinstance(data, list):
            return [self.c_base_w | self.c_asic[asic] | x for x in data]
        else:
            return self.c_base_w | self.c_asic[asic] | data


class TrbRegisters(Enum):
    SCALERS = 0xC001


class TrbRegistersOffsets:
    c_asic = [0x2000, 0x4000]

    # reg desc.: g_int,K,Tp      TC1      TC2      Vth
    c_config_reg = [0x00000, 0x00100, 0x00200, 0x00300]
    c_bl_reg = [0x00400, 0x00500, 0x00600, 0x00700, 0x00800, 0x00900, 0x00A00, 0x00B00]

    c_base_w = 0x0050000
    c_base_r = 0x0051000

    bl_register_size = 32


class PasttrecCard:
    name = None
    asic1 = None
    asic2 = None

    def __init__(self, name, asic1=None, asic2=None):
        self.name = name
        self.asic1 = asic1
        self.asic2 = asic2

    def set_asic(self, pos, asic):
        if pos == 0:
            self.asic1 = asic
        elif pos == 1:
            self.asic2 = asic

    def export(self):
        return {
            "name": self.name,
            "asic1": self.asic1.__dict__ if self.asic1 is not None else None,
            "asic2": self.asic2.__dict__ if self.asic2 is not None else None,
        }

    def export_script(self, cable):
        regs = []
        if self.asic1:
            regs.extend(self.asic1.dump_config(cable, 0))
        if self.asic2:
            regs.extend(self.asic2.dump_config(cable, 1))
        return regs

    @staticmethod
    def load_card_from_dict(d, test_version=None):
        if (test_version is not None) and (test_version != LIBVERSION):
            return False, LIBVERSION

        if d is None:
            return False, None

        pc = PasttrecCard(
            d["name"],
            AsicRegistersValue().load_asic_from_dict(d["asic1"]),
            AsicRegistersValue().load_asic_from_dict(d["asic2"]),
        )

        return True, pc


class TdcConnection:
    id = 0
    cable1 = None
    cable2 = None
    cable3 = None

    def __init__(self, id, cable1=None, cable2=None, cable3=None):
        self.id = hex(id) if isinstance(id, int) else id
        self.cable1 = cable1
        self.cable2 = cable2
        self.cable3 = cable3

    def set_card(self, pos, card):
        if pos == 0:
            self.cable1 = card
        elif pos == 1:
            self.cable2 = card
        elif pos == 2:
            self.cable3 = card

    def export(self):
        c1 = self.cable1.export() if isinstance(self.cable1, PasttrecCard) else None
        c2 = self.cable2.export() if isinstance(self.cable2, PasttrecCard) else None
        c3 = self.cable3.export() if isinstance(self.cable3, PasttrecCard) else None

        return self.id, {"cable1": c1, "cable2": c2, "cable3": c3}

    def export_script(self):
        c1 = self.cable1.export_script(0) if isinstance(self.cable1, PasttrecCard) else None
        c2 = self.cable2.export_script(1) if isinstance(self.cable2, PasttrecCard) else None
        c3 = self.cable3.export_script(2) if isinstance(self.cable3, PasttrecCard) else None

        c = []
        if c1:
            c.extend(c1)
        if c2:
            c.extend(c2)
        if c3:
            c.extend(c3)
        return self.id, c


def dump(tdcs):
    d = {"version": LIBVERSION}
    if isinstance(tdcs, list):
        for t in tdcs:
            k, v = t.export()
            d[k] = v
    elif isinstance(tdcs, TdcConnection):
        k, v = tdcs.export()
        d[k] = v

    return d


def load(d, test_version=True):
    if test_version:
        if "version" in d:
            if d["version"] != LIBVERSION:
                return False, d["version"]
        else:
            return False, "0.0.0"

    connections = []
    for k, v in d.items():
        if k == "version":
            continue

        id = int(k, 16)
        r1, _c1 = PasttrecCard.load_card_from_dict(v["cable1"])
        r2, _c2 = PasttrecCard.load_card_from_dict(v["cable2"])
        r3, _c3 = PasttrecCard.load_card_from_dict(v["cable3"])

        c1 = _c1 if r1 else None
        c2 = _c2 if r2 else None
        c3 = _c3 if r3 else None

        connections.append(TdcConnection(id, cable1=c1, cable2=c2, cable3=c3))

    return True, connections
