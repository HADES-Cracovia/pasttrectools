import itertools

from pasttrec.misc import is_iterable


def reset_asic(cable_connections, bar=None):
    """Reset ASICs on given cables."""

    for cg, cable_cons in cable_connections:

        for con in cable_cons:
            rc = con.reset_spi()
            if bar:
                bar()


def read_asic(address, reg=None, bar=None, sort=False):
    address_ct_sorted = communication.sort_by_ct(address)

    results = {}

    for cg in communication.group_cables(address_ct_sorted):
        cable_cons = communication.make_asic_connections(cg)

        for con in cable_cons:
            if not is_iterable(reg):
                reg = tuple(reg)

            for r in reg:
                rc = con.read_reg(r)
                for irc in rc:
                    addr = irc[0]
                    faddr = (addr, con.cable, con.asic)
                    if faddr not in results:
                        results[faddr] = [0] * len(reg)
                    results[faddr][r] = (r, irc[1] & 0xFF)
                if bar:
                    bar()

    if sort:
        return dict(sorted(results.items()))
    else:
        return results


def write_asic(asic_connections, data=None, reg=None, val=None, verify=False, bar=None, sort=False):
    is_data = data is not None
    is_reg_val = reg is not None and val is not None

    if not ((is_data and not is_reg_val) or (not is_data and is_reg_val)):
        raise "Either data or reg,val can be used"

    if is_data:
        if not is_iterable(data):
            raise "'data' must be of 'iterable' type"
        _data = data

    elif is_reg_val:
        if not (is_iterable(reg) and is_iterable(val)):
            raise "'reg' and 'val' must be of 'iterable' type"
        _data = tuple(itertools.product(reg, val))

    results = {}
    for cg, asic_cons in asic_connections:
        for con in asic_cons:

            for r, d in _data:
                con.write_reg(r, d)

                if verify:
                    rc = con.read_reg(r)

                    for irc in rc:
                        addr = irc[0]
                        faddr = (addr, con.cable, con.asic)

                        if faddr not in results:
                            results[faddr] = {}

                        _d = irc[1] & 0xFF
                        results[faddr][r, d] = _d == d, _d

                if bar:
                    bar()

    if verify:
        if sort:
            return dict(sorted(results.items()))
        else:
            return results
    else:
        return None
