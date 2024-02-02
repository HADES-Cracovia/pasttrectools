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

        self.delay_asic_spi = 0.0
        self.delay_1wire_temp = 0.5
        self.delay_1wire_id = 0.15

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

        self.enable_spi(trbid, cable)

        # bring all CS (reset lines) in the default state (1) - upper four nibbles:
        # invert CS, lower four nibbles: disable CS
        self.trb_com.write(trbid, 0xD417, 0x0000FFFF)

        # (chip-)select output $CONN for i/o multiplexer reasons, remember CS lines are disabled
        self.trb_com.write(trbid, 0xD410, 1 << cable)

        # disable all SDO outputs but output $CONN
        self.trb_com.write(trbid, 0xD415, 0xFFFF & ~(1 << cable))

        # disable all SCK outputs but output $CONN
        self.trb_com.write(trbid, 0xD416, 0xFFFF & ~(1 << cable))

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
        """ """

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

    def spi_reset(self, trbid, cable):
        """Reset sequence for the ASIC."""

        self.enable_spi(trbid, cable)

        # bring all CS (reset lines) in the default state (1) - upper four nibbles:
        # invert CS, lower four nibbles: disable CS
        self.trb_com.write(trbid, 0xD417, 0xFFFFFFFF)  # FIXME calble selection
        # and bring down selected bit
        # self.trb_com.write(trbid, 0xD417, 0x10000 << cable)

        # TODO can be be more generic like below?
        # generate 25 clock cycles
        # sleep(self.delay_asic_spi)

        # for c in range(25):
        # self.trb_com.write(trbid, 0xD416, ~(0x1 << cable))
        # sleep(self.delay_asic_spi)

        # self.trb_com.write(trbid, 0xD416, 0x00000000)
        # sleep(self.delay_asic_spi)

        # Alternate
        # Just send empty word instead of 25 cycles
        self.trb_com.write(trbid, 0xD411, 0x0002)

        # restore default CS
        self.trb_com.write(trbid, 0xD417, 0x0000FFFF)

    def read_wire_temp(self, trbid, cable):
        """non mux| dedicated 1wire component for each connector/cable"""

        self.enable_1wire(trbid, cable)

        # delay is mandatory due to how the 1wire device works
        sleep(self.delay_1wire_temp)

        rc = self.trb_com.read(trbid, 0x8)

        return (rc >> 16) * 0.0625

    def read_wire_id(self, trbid, cable):
        """non mux| dedicated 1wire component for each connector/cable"""

        self.enable_1wire(trbid, cable)

        # delay is mandatory due to how the 1wire device works
        sleep(self.delay_1wire_id)

        rc0 = self.trb_com.read(trbid, 0xA)
        rc1 = self.trb_com.read(trbid, 0xB)

        return (rc1 << 32) | rc0

    def enable_spi(self, trbid, cable):
        """The sequence is required to change from 1-wire to SPI."""

        self.trb_com.write(trbid, 0x23, 0x0)

        for c in range(4):
            self.trb_com.write(trbid, 0xD416, 0x10000 << cable)
            sleep(self.delay_asic_spi)

            self.trb_com.write(trbid, 0xD416, 0x00000000)
            sleep(self.delay_asic_spi)

    def enable_1wire(self, trbid, cable):
        """The sequence is required to change from SPI to 1-wire."""

        self.trb_com.write(trbid, 0x23, (0x0001 << cable + 1 | 0x0001))

        for c in range(4):
            self.trb_com.write(trbid, 0xD416, 0x10000 << cable)
            sleep(self.delay_asic_spi)

            self.trb_com.write(trbid, 0xD416, 0x00000000)
            sleep(self.delay_asic_spi)

    def print_info(self):
        print("Communication delays")
        print(f" SPI ASIC delay  : {self.delay_asic_spi}")
        print(f" 1wire temp delay: {self.delay_1wire_temp}")
        print(f" 1wire id delay  : {self.delay_1wire_id}")


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
