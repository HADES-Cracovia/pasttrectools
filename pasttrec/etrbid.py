"""
This module works on pattern trbids and provides different views of the address pattern.

The pattern trbid (ptrbid) is any string of formats:
* 0xXXXX
* 0xXXXX:Y
* 0xXXXX:Y:
* 0xXXXX:Y:Z
* 0xXXXX::Z
* 0xXXXX::
The 0xXXXX address is mandatory, Y or Z may be omitted.

The sections trbid (strbid) is a variable-length tuple of (0xXXXX, Y, Z) strings expanded from ptrbid, with empty
strings if a component is omitted.

"""


def padded_hex(value: int, length: int):
    """
    Pad the hex address with zeros to given length

    Based on https://stackoverflow.com/questions/12638408/decorating-hex-function-to-pad-zeros

    Parameters
    ----------
    value : int
        The value
    length : int
        Hex number digits length

    Returns
    -------
    hexed_value : str
        The hex version of the value padded with 0 to given length
    """

    hex_result = hex(value)[2:]  # remove '0x' from beginning of str
    num_hex_chars = len(hex_result)
    extra_zeros = "0" * (length - num_hex_chars)  # may not get used..

    return (
        "0x" + hex_result
        if num_hex_chars == length
        else (
            "?" * length
            if num_hex_chars > length
            else "0x" + extra_zeros + hex_result if num_hex_chars < length else None
        )
    )


def trbaddr(addr: int):
    """
    Convert trb address from int to hex-string.

    Pamateres
    ---------
    addr : int
        Addres value

    Returns
    -------
    hex_addr : str
        Address as hex
    """

    return padded_hex(addr, 4)


def extract_strbid(ptrbid: str):
    """
    Extract strbid from 'ptrbid' string and check whether the trbid is a valid address.

    Parameters
    ----------
    ptrbid : str
        The strbid string

    Returns
    -------
    etrbid : tuple
        The expanded trbid (etrbid)

    Yields
    ------
    ValueError
        If incorrect strbid format
    """

    sections = ptrbid.split(":")

    if len(sections) > 3:
        print("Error in ptrbid ", ptrbid)
        raise ValueError

    # check address
    address = sections[0]
    if len(address) == 6:
        if address[0:2] != "0x":
            raise ValueError(f"Incorrect address in ptrbid: {ptrbid}")
    elif len(address) == 4:
        address = "0x" + address
    else:
        raise ValueError(f"Incorrect address in ptrbid: {ptrbid}")

    return tuple(sections)


def expand_strbid(strbid: tuple, n_cables: int, n_asics: int):
    """
    Convert strbid into etrbids.

    It uses n_cables and n-asics to generate tuple of tuples, where each tuple is triplet of trbid,cable,asic.

    Parameters
    ----------
    strbid : tuple
        The strbid tuple if (int, str, str)
    n_cables : int
        Number of cables on given TRB design
    n_asics : int
        Number of asics on given TRB design

    Returns
    -------
    etrbids : tuple
        Tuple of etrbid tuples
    """

    sec_len = len(strbid)

    # do everything backwards
    # asics
    if sec_len == 3 and strbid[2]:
        _asics = strbid[2].split(",")
        asics = tuple(int(a) for a in _asics if int(a) in range(n_asics))  # TODO add 1-2 mode
    else:
        asics = tuple(range(n_asics))

    # asics
    if sec_len >= 2 and strbid[1]:
        _cables = strbid[1].split(",")
        cables = tuple(int(c) for c in _cables if int(c) in range(n_cables))  # TODO add 1-4 mode
    else:
        cables = tuple(range(n_cables))

    return tuple(
        (strbid[0] if isinstance(strbid[0], (int,)) else int(strbid[0], 16), y, z) for y in cables for z in asics
    )


def trbids_from_ptrbids(ptrbid: tuple):
    """
    Return list of unique trbnet addresses.

    Parameters
    ----------
    ptrbid : tuple
        Pattern trbids

    Returns
    -------
    trbids : tuple
        Tuple of trbids
    """

    return tuple(set((x if isinstance(x, (int,)) else int(x.split(":")[0], 16) for x in ptrbid)))


def trbids_from_etrbids(etrbid):
    """
    Return list of unique trbnet addresses.

    Parameters
    ----------
    etrbid : tuple
        Tuple of etrbids

    Returns
    -------
    trbids : tuple
        Tuple of trbids
    """

    return tuple(set(trbid for trbid, *_ in etrbid))


def ctrbids_from_etrbids(etrbid):
    """
    Return list of unique trbnet ctrbids.


    Parameters
    ----------
    etrbid : tuple
        Tuple of etrbids

    Returns
    -------
    ctrbids : tuple
        Tuple of unqiue ctrbids
    """

    return tuple(set((trbid, cable) for trbid, cable, *_ in etrbid))


def group_cables(ctrbids_tuple: tuple):
    try:
        min_c = min(ctrbids_tuple, key=lambda tup: tup[1])[1]
        max_c = max(ctrbids_tuple, key=lambda tup: tup[1])[1]
    except ValueError:
        return ()

    def tup_group(c, ct):
        return tuple(tup for tup in ct if tup[1] == c)

    return tuple(sort_by_trbid(tup_group(x, ctrbids_tuple)) for x in range(min_c, max_c + 1))


def sort_by_cable(xtrbids_tuple: tuple):
    return tuple(sorted(xtrbids_tuple, key=lambda tup: (tup[1], tup[0])))


def sort_by_ct(xtrbids_tuple: tuple):
    return tuple(sorted(xtrbids_tuple, key=lambda tup: (tup[1], tup[0])))


def sort_by_tc(xtrbids_tuple: tuple):
    return tuple(sorted(xtrbids_tuple, key=lambda tup: (tup[0], tup[1])))


def sort_by_trbid(xtrbids_tuple: tuple):
    return tuple(sorted(xtrbids_tuple, key=lambda tup: tup[0]))
