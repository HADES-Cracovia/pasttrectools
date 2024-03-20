"""
This module provides generic structures describing various hardware components.

This includes:
* the TrbNet registers to communicate with Pasttrec
* the Pasttrec card with peripherals
* the Pasttrec ASIC with internal registers
The functions provide also export/import of the components settings.
"""

from enum import Enum

from pasttrec import LIBVERSION
from pasttrec.types import NoIndent
from pasttrec.trb_spi import SpiTrbTdc
from pasttrec.etrbid import padded_hex


class MissingFeatures(Exception):
    def __init__(self, features):
        super().__init__(f"Features type {hex(features)} not supported")
        self.features = features


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
    n_regs = 12

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
        self.bl = NoIndent([i for i in bl])

    @staticmethod
    def load_asic_from_dict(d, test_version=None):
        if (test_version is not None) and (test_version != LIBVERSION):
            return False
        p = AsicRegistersValue()
        for k, v in d.items():
            if k == "bl":
                p.bl = NoIndent([x for x in v])
            else:
                setattr(p, k, v)
        return p

    def load_config(self, data: tuple):
        if len(data) != self.n_regs:
            raise TypeError(f"The config data tuple has size {len(data)}, must be {self.n_regs}")

        self.bg_int = (data[0] >> 4) & 0x01
        self.gain = (data[0] >> 2) & 0x03
        self.peaking = (data[0] >> 0) & 0x03
        self.tc1c = (data[1] >> 3) & 0x07
        self.tc1r = (data[1] >> 0) & 0x07
        self.tc2c = (data[2] >> 3) & 0x07
        self.tc2r = (data[2] >> 0) & 0x07
        self.vth = (data[3] >> 0) & 0x3F
        self.bl.value = [x for x in data[4:]]

    def dump_config(self):
        return tuple(
            (
                (self.bg_int << 4) | (self.gain << 2) | self.peaking,
                (self.tc1c << 3) | self.tc1r,
                (self.tc2c << 3) | self.tc2r,
                self.vth,
            )
            + tuple(self.bl.value)
        )

    def dump_spi_config(self):
        cfg = self.dump_config()
        return tuple(((TrbRegistersOffsets.c_reg_offsets[i] | cfg[i]) for i in range(self.n_regs)))

    def dump_spi_config_hex(self):
        return tuple((hex(i) for i in self.dump_spi_config()))

    def dump_spi_bl_hex(self):
        return tuple((hex(i) for i in self.dump_spi_config()[4:]))


class TrbDesignInfo:
    """Stores pairs of Trb hwtype nad features."""

    def __init__(self, hwtype: int, features: int, responders: tuple):
        self.hwtype = hwtype
        self.features = features
        self.responders = responders

    def __eq__(self, other):
        return self.hwtype == other.hwtype and self.features == other.features and self.responders == other.responders

    def __hash__(self):
        return hash(self.features << 32 | self.hwtype << len(self.responders))

    def __str__(self):
        return f"TrbDesignInfo({padded_hex(self.hwtype, 8)}, {padded_hex(self.features, 16)}, {self.responders})"

    def __repr__(self):
        return self.__str__()


class TrbDesignSpecs(Enum):
    """Use it to discriminate between different frontend types."""

    TRB3 = (3, 2, 0xFE4C, SpiTrbTdc)
    TRB5SC_16CH = (2, 2, 0xFE81, SpiTrbTdc)

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
    # 0x91000000: TrbDesignSpecs.TRB3,
    0x02010C000000F301: TrbDesignSpecs.TRB5SC_16CH,
}


def get_design_specs(features):
    if features in TrbBoardTypeMapping:
        return TrbBoardTypeMapping[features]
    else:
        return None
        raise MissingFeatures(features)


"""Stores the quered trb design data."""
trb_designs_map = {}


def detect_design(address):
    """Detect the Trb board type"""

    if address in trb_designs_map:
        features = trb_designs_map[address].features
        return (
            address,
            tuple((responder, get_design_specs(features)) for responder in trb_designs_map[address].responders),
        )


def check_broadcats_address(trbid: int):
    """
    Check if the address is of broadcast type, and if yes return the boards properties.

    Parameters
    ----------
    trbid : int or str
        The trb address

    Returns
    -------
    board_type : TrbBoardType or None
        The board type based on broadcast address or None
    """
    pass


def filter_known_designs(db: dict):
    return tuple(
        (
            trbid
            for trbid, design_info in db.items()
            if (design_info is not None and get_design_specs(design_info.features))
        )
    )


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
    c_asic = (0x2000, 0x4000)

    # reg desc.: g_int,K,Tp      TC1      TC2      Vth
    c_config_reg = (0x00000, 0x00100, 0x00200, 0x00300)
    c_bl_reg = (0x00400, 0x00500, 0x00600, 0x00700, 0x00800, 0x00900, 0x00A00, 0x00B00)

    c_reg_offsets = c_config_reg + c_bl_reg

    c_base_w = 0x0050000
    c_base_r = 0x0051000

    bl_register_size = 32
