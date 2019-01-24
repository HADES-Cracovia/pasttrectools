LIBVERSION = "1.0"

class PasttrecDefaults:
    c_cable = [ 0x00 << 19, 0x01 << 19, 0x02 << 19 ]
    c_asic = [ 0x2000, 0x4000 ]

#                Bg_int,K,Tp      TC1      TC2      Vth
    c_config_reg = [ 0x00000, 0x00100, 0x00200, 0x00300 ]
    c_bl_reg = [ 0x00400, 0x00500, 0x00600, 0x00700,
                0x00800, 0x00900, 0x00a00, 0x00b00 ]

    c_trbnet_reg = 0xa000
    c_base_w = 0x0050000
    c_base_r = 0x0051000

class PasttrecRegs(PasttrecDefaults):
    bg_int = 1
    gain = 0
    peaking = 0
    tc1c = 0
    tc1r = 0
    tc2c = 0
    tc2r = 0
    vth = 0
    bl = [0] * 8

    def __init__(self, bg_int = 1, gain = 0, peaking = 0,
                 tc1c = 0, tc1r = 0, tc2c = 0, tc2r = 0,
                 vth = 0, bl = [0] * 8):
        self.bg_int   = bg_int
        self.gain     = gain
        self.peaking  = peaking
        self.tc1c     = tc1c
        self.tc1r     = tc1r
        self.tc2c     = tc2c
        self.tc2r     = tc2r
        self.vth      = vth
        self.bl       = [ i for i in bl]

    @staticmethod
    def load_asic_from_dict(d, test_version=None):
        if (test_version is not None) and (test_version != LIBVERSION):
            return False
        p = PasttrecRegs()
        for k, v in d.items():
            setattr(p, k, v)
        return p

    def dump_config(self, cable, asic):
        r_all = [0] * 12
        offset = self.c_base_w | self.c_cable[cable] | self.c_asic[asic]
        t = (self.bg_int << 4) | (self.gain << 2) | self.peaking
        r_all[0] = offset | self.c_config_reg[0] | t
        t = (self.tc1c << 3) | self.tc1r
        r_all[1] = offset | self.c_config_reg[1] | t
        t = (self.tc2c << 3) | self.tc2r
        r_all[2] = offset | self.c_config_reg[2] | t
        r_all[3] = offset | self.c_config_reg[3] | self.vth

        for i in range(8):
            r_all[4+i] = offset | self.c_bl_reg[i] | self.bl[i]

        return r_all

    def dump_config_hex(self, cable, asic):
        return [ hex(i) for i in self.dump_config(cable, asic) ]

    def dump_bl_hex(self, cable, asic):
        return [ hex(i) for i in self.dump_config(cable, asic)[4:] ]

class PasttrecCard():
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
        return { 'name' : self.name,
                'asic1' : self.asic1.__dict__ if self.asic1 is not None else None,
                'asic2' : self.asic2.__dict__ if self.asic2 is not None else None
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

        pc = PasttrecCard(d['name'],
                          PasttrecRegs().load_asic_from_dict(d['asic1']),
                          PasttrecRegs().load_asic_from_dict(d['asic2']))

        return True, pc

class TdcConnection():
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

        return self.id, {
            'cable1' : c1,
            'cable2' : c2,
            'cable3' : c3
        }

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
    d = { 'version' : LIBVERSION }
    if isinstance(tdcs, list):
        for t in tdcs:
            k, v = t.export()
            d[k] = v
    elif isinstance(tdcs, TdcConnection):
        k, v = tdcs.export()
        d[k] = v

    return d

def dump_script(tdcs):
    d = []
    if isinstance(tdcs, list):
        for t in tdcs:
            k, v = t.export_script()
            for _v in v:
                d.append("trbcmd w {:s} 0xa000 {:s}".format(k, hex(_v)))
    elif isinstance(tdcs, TdcConnection):
        k, v = tdcs.export_script()
        for _v in v:
            d.append("trbcmd w {:s} 0xa000 {:s}".format(k, hex(_v)))

    return d

def load(d, test_version=True):
    if test_version:
        if 'version' in d:
            if d['version'] != LIBVERSION:
                return False, d['version']
        else:
            return False, '0.0.0'

    connections = []
    for k, v in d.items():
        if k == 'version': continue

        id = int(k, 16)
        r1, _c1 = PasttrecCard.load_card_from_dict(v['cable1'])
        r2, _c2 = PasttrecCard.load_card_from_dict(v['cable2'])
        r3, _c3 = PasttrecCard.load_card_from_dict(v['cable3'])

        c1 = _c1 if r1 else None
        c2 = _c2 if r2 else None
        c3 = _c3 if r3 else None

        connections.append(TdcConnection(id, cable1=c1, cable2=c2, cable3=c3))

    return True, connections
