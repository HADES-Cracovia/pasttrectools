
import abc

from pasttrec import misc


class TrbSpiDriver(metaclass=abc.ABCMeta):
    """A TrbMetaclass that will be used for trb interface class creation."""

    @classmethod
    def __subclasshook__(self, subclass):
        return (hasattr(subclass, 'spi_fill_buffer') and
                callable(subclass.spi_fill_buffer) and
                hasattr(subclass, 'spi_prepare') and
                callable(subclass.spi_prepare) and
                hasattr(subclass, 'spi_read') and
                callable(subclass.spi_read) and
                hasattr(subclass, 'spi_write') and
                callable(subclass.spi_write) and
                hasattr(subclass, 'spi_write_chunk') and
                callable(subclass.spi_write_chunk) and
                hasattr(subclass, 'spi_reset') and
                callable(subclass.spi_reset) or
                NotImplemented)

    @abc.abstractmethod
    def spi_prepare(self, trbid, cable, asic):
        raise NotImplementedError

    @abc.abstractmethod
    def spi_read(self, trbid, cable, asic, data):
        raise NotImplementedError

    @abc.abstractmethod
    def spi_write(self, trbid, cable, asic, data):
        raise NotImplementedError

    @abc.abstractmethod
    def spi_write_chunk(self, trbid, cable, asic, data):
        raise NotImplementedError

    @abc.abstractmethod
    def spi_reset(self, trbid, cable):
        raise NotImplementedError


class TrbTdcSpi:
    """Doc"""
    trb_com = None

    def __init__(self, trb_com):
        """
        The constructor

        Paramaters
        ----------
        trb_com : TrbNet
            The TrbNet object
        """
        self.trb_com = trb_com

    def spi_prepare(self, trbid: int, cable: int):
        """
        Prepare the SPI interface

        Paramaters
        ----------
        trbid : int
            The trbid address
        cable : int
            The cable number 0..max (typically 3 or 4 cables on a single TDC)
        """

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

    def spi_read(self, trbid):
        return self.trb_com.read(trbid, 0xD412)

    def spi_write(self, trbid: int, cable: int, asic: int, data: int):
        """
        Write data to spi interface

        Paramaters
        ----------
        trbid : int
            The trbid address
        cable : int
            The cable number 0..max (typically 3 or 4 cables on a single TDC)
        asic : int
            the asis number, 0..1 (two asics on a single cables)
        data : int
            data to write
        """

        if isinstance(data, list):
            my_data_list = data
        else:
            my_data_list = [data]

        self.spi_prepare(trbid, cable)

        for data in my_data_list:
            # writing one data word, append zero to the data word, the chip will get some more SCK clock cycles
            self.trb_com.write(trbid, 0xD400, data)
            # write 1 to length register to trigger sending
            self.trb_com.write(trbid, 0xD411, 0x0001)

    def spi_write_chunk(self, trbid, cable, asic, data):
        if isinstance(data, list):
            my_data_list = data
        else:
            my_data_list = [data]

        self.spi_prepare(trbid, cable)

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


class TrbSpiEncoder(metaclass=abc.ABCMeta):
    """A TrbMetaclass that will be used for trb interface class creation."""

    @classmethod
    def __subclasshook__(self, subclass):
        return (hasattr(subclass, 'reg_write') and
                callable(subclass.reg_write) and
                hasattr(subclass, 'reg_read') and
                callable(subclass.reg_read) and
                hasattr(subclass, 'reg_write_data') and
                callable(subclass.reg_write_data) and
                hasattr(subclass, 'reg_write_chunk') and
                callable(subclass.reg_write_chunk) or
                NotImplemented)

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


class Trb3Encoder:
    """Doc"""
    c_asic = [0x2000, 0x4000]
    # reg desc.: g_int,K,Tp      TC1      TC2      Vth
    c_config_reg = [0x00000, 0x00100, 0x00200, 0x00300]
    c_bl_reg = [0x00400, 0x00500, 0x00600, 0x00700, 0x00800, 0x00900, 0x00A00, 0x00B00]
    c_base_w = 0x0050000
    c_base_r = 0x0051000
    bl_register_size = 32

    spi_mem = {}
    spi_queue = 0
    spi_interface = None

    def __init__(self, spi_interface):
        self.spi_interface = spi_interface

    def reg_write(self, trbid, cable, asic, reg, val):
        word = self.c_base_w | self.c_asic[asic] | (reg << 8) | val
        self.spi_interface.spi_write(trbid, cable, asic, word)

    def reg_read(self, trbid, cable, asic, reg):
        word = self.c_base_w | self.c_asic[asic] | (reg << 8)
        self.spi_interface.spi_write(trbid, cable, asic, word << 1)
        return self.spi_interface.spi_read(trbid)

    def reg_write_data(self, trbid, cable, asic, data):
        if isinstance(data, list):
            word = [self.c_base_w | self.c_asic[asic] | x for x in data]
        else:
            word = self.c_base_w | self.c_asic[asic] | data
        self.spi_interface.spi_write(trbid, cable, asic, word)

    def reg_write_chunk(self, trbid, cable, asic, data):
        if isinstance(data, list):
            word = [self.c_base_w | self.c_asic[asic] | x for x in data]
        else:
            word = self.c_base_w | self.c_asic[asic] | data
        self.spi_interface.spi_write_chunk(trbid, cable, asic, word)


class Trb5scEncoder(Trb3Encoder):
    """Doc"""
    pass
