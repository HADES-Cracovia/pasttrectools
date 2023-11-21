import abc
from time import sleep

from pasttrec import misc


class TrbSpiDriver(metaclass=abc.ABCMeta):
    """A TrbMetaclass that will be used for trb interface class creation."""

    @classmethod
    def __subclasshook__(self, subclass):
        return (
            hasattr(subclass, "fill_buffer")
            and callable(subclass.fill_buffer)
            and hasattr(subclass, "prepare")
            and callable(subclass.prepare)
            and hasattr(subclass, "read")
            and callable(subclass.read)
            and hasattr(subclass, "write")
            and callable(subclass.write)
            and hasattr(subclass, "write_chunk")
            and callable(subclass.write_chunk)
            and hasattr(subclass, "reset")
            and callable(subclass.reset)
            or NotImplemented
        )

    @abc.abstractmethod
    def prepare(self, trbid, cable, asic):
        raise NotImplementedError

    @abc.abstractmethod
    def read(self, trbid, cable, asic, data):
        raise NotImplementedError

    @abc.abstractmethod
    def write(self, trbid, cable, asic, data):
        raise NotImplementedError

    @abc.abstractmethod
    def write_chunk(self, trbid, cable, asic, data):
        raise NotImplementedError

    @abc.abstractmethod
    def reset(self, trbid, cable):
        raise NotImplementedError


class SpiTrbTdc:
    """Doc"""

    trb_com = None

    spi_mem = {}
    spi_queue = 0
    spi_interface = None

    def __init__(self, trb_com):
        """
        The constructor

        Paramaters
        ----------
        trb_com : TrbNet
            The TrbNet object
        """
        self.trb_com = trb_com

    def prepare(self, trbid: int, cable: int):
        """
        Prepare the SPI interface

        Paramaters
        ----------
        trbid : int
            The trbid address
        cable : int
            The cable number 0..max (typically 3 or 4 cables on a single TDC)
        """
        # print(f"PREPARE {hex(trbid)} {cable}")
        # bring all CS (reset lines) in the default state (1) - upper four nibbles:
        # invert CS, lower four nibbles: disable CS
        self.trb_com.write(trbid, 0xD417, 0x0000FFFF)

        # (chip-)select output $CONN for i/o multiplexer reasons, remember CS lines are disabled
        self.trb_com.write(trbid, 0xD410, 1 << cable)

        # override: (chip-) select all ports!!
        # trbcmd w $trbid 0xd410 0xFFFF

        # override: (chip-) select nothing !!
        # trbcmd w $trbid 0xd410 0x0000

        # disable all SDO outputs but output $CONN
        self.trb_com.write(trbid, 0xD415, 0xFFFF & ~(1 << cable))

        # disable all SCK outputs but output $CONN
        self.trb_com.write(trbid, 0xD416, 0xFFFF & ~(1 << cable))

        # override: disable all SDO and SCK lines
        # trbcmd w $trbid 0xd415 0xFFFF
        # trbcmd w $trbid 0xd416 0xFFFF

    def read(self, trbid):
        return self.trb_com.read(trbid, 0xD412)

    def write(self, trbid: int, cable: int, data: int):
        """
        Write data to spi interface

        Paramaters
        ----------
        trbid : int
            The trbid address
        cable : int
            The cable number 0..max (typically 3 or 4 cables on a single TDC)
        data : int
            data to write
        """

        if isinstance(data, list):
            my_data_list = data
        else:
            my_data_list = [data]

        self.prepare(trbid, cable)

        for data in my_data_list:
            # writing one data word, append zero to the data word, the chip will get some more SCK clock cycles
            self.trb_com.write(trbid, 0xD400, data)
            # write 1 to length register to trigger sending
            self.trb_com.write(trbid, 0xD411, 0x0001)

    def write_chunk(self, trbid, cable, data):
        if isinstance(data, list):
            my_data_list = data
        else:
            my_data_list = [data]

        self.prepare(trbid, cable)

        for d in misc.chunks(my_data_list, 16):
            # i = 0
            self.trb_com.write_mem(trbid, 0xD400, my_data_list, 0)
            # for val in d:
            #    # writing one data word, append zero to the data word, the chip will get some more SCK clock cycles
            #    self.trb_com.write(trbid, 0xd400 + i, val)
            #    i = i + 1

            # write length register to trigger sending
            self.trb_com.write(trbid, 0xD411, len(d))

    def reset(self, trbid, cable):
        # bring all CS (reset lines) in the default state (1) - upper four nibbles:
        # invert CS, lower four nibbles: disable CS
        self.trb_com.write(trbid, 0xD417, 0x0000FFFF)
        # and bring down selected bit
        self.trb_com.write(trbid, 0xD417, 0x10000 << cable)

        # generate 25 clock cycles
        for c in range(25):
            self.trb_com.write(trbid, 0xD416, 0x10000 << cable)
            self.trb_com.write(trbid, 0xD416, 0x00000000)

        # restore default CS
        self.trb_com.write(trbid, 0xD417, 0x0000FFFF)

    def read_wire_temp(
        self, trbid, cable
    ):  # non mux| dedicated 1wire component for each connector/cable
        for c in range(4):
            self.trb_com.write(trbid, 0xD416, 0xFFFF0000 & (0xF0000))
            self.trb_com.write(trbid, 0xD416, 0x00000000)

        self.trb_com.write(trbid, 0x23, (0x0001 << cable + 1 | 0x0001))
        sleep(0.5)
        rc = self.trb_com.read(trbid, 0x8)
        self.trb_com.write(trbid, 0x23, 0x0)
        return (rc >> 16) * 0.0625

    def read_wire_id(
        self, trbid, cable
    ):  # non mux| dedicated 1wire component for each connector/cable
        for c in range(4):
            self.trb_com.write(trbid, 0xD416, 0xFFFF0000 & (0xF0000))
            self.trb_com.write(trbid, 0xD416, 0x00000000)

        self.trb_com.write(trbid, 0x23, (0x0001 << cable + 1 | 0x0001))
        sleep(0.1)
        rc0 = self.trb_com.read(trbid, 0xA)
        rc1 = self.trb_com.read(trbid, 0xB)
        self.trb_com.write(trbid, 0x23, 0x0)
        return (rc1 << 32) | rc0


class TrbSpiEncoder(metaclass=abc.ABCMeta):
    """A TrbMetaclass that will be used for trb interface class creation."""

    @classmethod
    def __subclasshook__(self, subclass):
        return (
            hasattr(subclass, "reg_write")
            and callable(subclass.reg_write)
            and hasattr(subclass, "reg_read")
            and callable(subclass.reg_read)
            and hasattr(subclass, "reg_write_data")
            and callable(subclass.reg_write_data)
            and hasattr(subclass, "reg_write_chunk")
            and callable(subclass.reg_write_chunk)
            or NotImplemented
        )

    @abc.abstractmethod
    def reg_write(trbid, cable, asic, reg, val):
        raise NotImplementedError

    @abc.abstractmethod
    def reg_read(trbid, cable, asic, reg):
        raise NotImplementedError

    @abc.abstractmethod
    def reg_write_data(trbid, cable, asic, data):
        raise NotImplementedError

    @abc.abstractmethod
    def reg_write_chunk(trbid, cable, asic, data):
        raise NotImplementedError
