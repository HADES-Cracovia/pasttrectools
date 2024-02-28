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

    default_word_length = 20
    owire_mode = False

    def __init__(self, trb_com, trbid: int):
        """
        The constructor

        Paramaters
        ----------
        trb_com : TrbNet
            The TrbNet object
        trbid: int
            The TRB board address
        """

        self.delay_asic_spi = 0.0
        self.delay_1wire_temp = 0.5
        self.delay_1wire_id = 0.15

        self.trb_com = trb_com
        self.trbid = trbid

        self.flag_rb = False  # Enable blocking state when the response is expected

        self.restore = self.trb_com.read(self.trbid, 0xD419) != self.default_word_length  # restore to some defaults
        self.owire_mode = self.trb_com.read(self.trbid, 0x23) != 0x0  # restore to some defaults

    def __prepare(self, cable: int):
        """
        Prepare the SPI interface

        Paramaters
        ----------
        trbid : int
            The trbid address
        cable : int
            The cable number 0..max (typically 3 or 4 cables on a single TDC)
        """

        if self.owire_mode:
            self.__enable_spi(cable)

        # bring all CS (reset lines) in the default state (1) - upper four nibbles:
        # invert CS, lower four nibbles: disable CS
        self.trb_com.write(self.trbid, 0xD417, 0x0000FFFF)

        # (chip-)select output $CONN for i/o multiplexer reasons, remember CS lines are disabled
        self.trb_com.write(self.trbid, 0xD410, 1 << cable)

        # disable all SDO outputs but output $CONN
        self.trb_com.write(self.trbid, 0xD415, 0xFFFF & ~(1 << cable))

        # disable all SCK outputs but output $CONN
        self.trb_com.write(self.trbid, 0xD416, 0xFFFF & ~(1 << cable))

    def __transmit(self, length: int, data_word_length=20):
        """
        Transmit the data

        Paramaters
        ----------
        length: int
            Number of words to transmit
        data_word_length: int
            How many bits to transmit
        """

        # Change the data word length either when:
        #  1. The current data word is different than default
        #  2. The restore flag was used
        if data_word_length != self.default_word_length or self.restore:
            self.trb_com.write(self.trbid, 0xD419, data_word_length)
            self.restore = True

        rb_flag = 1 << 16 if self.flag_rb else 0
        self.trb_com.write(self.trbid, 0xD411, length & 0xFFFF | rb_flag)

    def write(self, cable: int, data: int):
        """
        Write data to spi interface

        Paramaters
        ----------
        cable : int
            The cable number 0..max (typically 3 or 4 cables on a single TDC)
        data : int
            data to write
        """

        self.__prepare(cable)

        # writing one data word, append zero to the data word, the chip will get some more SCK clock cycles
        self.trb_com.write(self.trbid, 0xD400, data)
        # write 1 to length register to trigger sending
        self.__transmit(1)

    def read(self, cable: int, data: int):
        """
        Write data to spi interface and expect result.

        Paramaters
        ----------
        cable : int
            The cable number 0..max (typically 3 or 4 cables on a single TDC)
        data : int
            data to write
        """

        self.__prepare(cable)

        # writing one data word, append zero to the data word, the chip will get some more SCK clock cycles
        self.trb_com.write(self.trbid, 0xD400, data)
        # write 1 to length register to trigger sending
        self.rb_flag = True
        self.__transmit(1)

        if self.restore:
            rc = self.trb_com.read(self.trbid, 0xD412)
            self.trb_com.write(self.trbid, 0xD419, self.default_word_length)
            self.restore = False
            return rc

        self.rb_flag = False

        return self.trb_com.read(self.trbid, 0xD412)

    def write_chunk(self, cable: int, data: int):
        """ """

        if isinstance(data, list):
            my_data_list = data
        else:
            my_data_list = [data]

        self.__prepare(cable)

        self.rb_flag = False

        for d in misc.chunks(my_data_list, 16):
            # i = 0
            self.trb_com.write_mem(self.trbid, 0xD400, my_data_list, 0)
            # for val in d:
            #    # writing one data word, append zero to the data word, the chip will get some more SCK clock cycles
            #    self.trb_com.write(self.trbid, 0xd400 + i, val)
            #    i = i + 1

            # write length register to trigger sending
            self.__transmit(len(d))

    def spi_reset(self, cable: int):
        """Reset sequence for the ASIC."""

        self.__enable_spi(cable)

        # bring all CS (reset lines) in the default state (1) - upper four nibbles:
        # invert CS, lower four nibbles: disable CS
        self.trb_com.write(self.trbid, 0xD417, 0x10000 << cable | 0x0000FFFF)

        # To reset the ASIC one needs to send 25 clocks with CS=0
        # Just send empty word instead of 25 cycles
        self.__transmit(1, 25)

        # restore default CS
        self.trb_com.write(self.trbid, 0xD417, 0x0000FFFF)

    def read_1wire_temp(self, cable: int):
        """non mux| dedicated 1wire component for each connector/cable"""

        self.__enable_1wire(cable)

        # delay is mandatory due to how the 1wire device works
        sleep(self.delay_1wire_temp)

        rc = self.trb_com.read(self.trbid, 0x8)

        return (rc >> 16) * 0.0625

    def read_1wire_id(self, cable: int):
        """non mux| dedicated 1wire component for each connector/cable"""

        self.__enable_1wire(cable)

        # delay is mandatory due to how the 1wire device works
        sleep(self.delay_1wire_id)

        rc0 = self.trb_com.read(self.trbid, 0xA)
        rc1 = self.trb_com.read(self.trbid, 0xB)

        return (rc1 << 32) | rc0

    def activate_1wire(self, cable: int):
        """Activate 1wire component for given connector/cable"""

        self.__enable_1wire(cable)

    def get_1wire_temp(self, cable: int):
        """
        Read the 1wire temp.
        User is responsible for proper delay between
        1wire activation and temp readout.
        """

        rc = self.trb_com.read(self.trbid, 0x8)
        return tuple((rc0[0], (rc0[1] >> 16) * 0.0625) for rc0 in rc)

    def get_1wire_id(self, cable: int):
        """
        Read the 1wire id.
        User is responsible for proper delay between
        1wire activation and id readout.
        """

        rc0 = self.trb_com.read(self.trbid, 0xA)
        rc1 = self.trb_com.read(self.trbid, 0xB)

        merged = zip(rc0, rc1)
        return tuple(tuple((rc1[0], (rc1[1] << 32) | rc0[1])) for rc0, rc1 in merged)

    def __enable_spi(self, cable: int):
        """The sequence is required to change from 1-wire to SPI."""

        self.owire_mode = False
        self.trb_com.write(self.trbid, 0x23, 0x0)

    def __enable_1wire(self, cable: int):
        """The sequence is required to change from SPI to 1-wire."""

        self.owire_mode = True
        self.trb_com.write(self.trbid, 0x23, 0x0002 << cable)

        # send clocks to charge and run 1-wire devices
        self.__transmit(1, 4)

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
