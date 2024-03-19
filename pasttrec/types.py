import json
import re
import types
from _ctypes import PyObj_FromPtr  # see https://stackoverflow.com/a/15012814/355230

from pasttrec import etrbid, hardware


# From https://stackoverflow.com/questions/42710879/write-two-dimensional-list-to-json-file
class NoIndent(object):
    """Value wrapper."""

    def __init__(self, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError("Only lists and tuples can be wrapped")
        self.value = value


class Baselines:
    """Holds baseline info for given card"""

    baselines = None

    def __init__(self):
        self.baselines = {}

    def add_card(self, uid, trb_design_type):
        if uid not in self.baselines:
            w = hardware.TrbRegistersOffsets.bl_register_size
            h = trb_design_type.n_channels
            a = trb_design_type.n_asics
            self.baselines[etrbid.padded_hex(uid, 16)] = {
                "config": None,
                "results": [[NoIndent([0 for x in range(w)]) for y in range(h)] for _a in range(a)],
            }


class Thresholds:
    thresholds = None
    config = None

    def __init__(self):
        self.thresholds = {}

    def add_trb(self, trbid, trb_design_type):
        if trbid not in self.thresholds:
            w = 128
            h = trb_design_type.n_channels
            a = trb_design_type.n_asics
            c = trb_design_type.n_cables
            self.thresholds[trbid] = [[[[0 for x in range(w)] for y in range(h)] for _a in range(a)] for _c in range(c)]


class Scalers:
    def __init__(self, n_scalers):
        self.scalers = {}
        self.n_scalers = n_scalers

    def add_trb(self, trb):
        if trb not in self.scalers:
            self.scalers[trb] = [0] * self.n_scalers

    def diff(self, scalers):
        s = dict(self.scalers)
        for k, v in s.items():
            if k in scalers.scalers:
                for i in list(range(self.n_scalers)):
                    s[k][i] -= scalers.scalers[k][i]
                    if s[k][i] < 0:
                        s[k][i] += 0x80000000
            else:
                del s[k]
        return s


# From https://stackoverflow.com/questions/42710879/write-two-dimensional-list-to-json-file
# and I have no idea how it works, but works!
class MyEncoder(json.JSONEncoder):
    FORMAT_SPEC = "@@{}@@"  # Unique string pattern of NoIndent object ids.
    regex = re.compile(FORMAT_SPEC.format(r"(\d+)"))  # compile(r'@@(\d+)@@')

    def __init__(self, **kwargs):
        # Keyword arguments to ignore when encoding NoIndent wrapped values.
        ignore = {"cls", "indent"}

        # Save copy of any keyword argument values needed for use here.
        self._kwargs = {k: v for k, v in kwargs.items() if k not in ignore}
        super(MyEncoder, self).__init__(**kwargs)

    def default(self, obj):
        return self.FORMAT_SPEC.format(id(obj)) if isinstance(obj, NoIndent) else super(MyEncoder, self).default(obj)

    def iterencode(self, obj, **kwargs):
        format_spec = self.FORMAT_SPEC  # Local var to expedite access.

        # Replace any marked-up NoIndent wrapped values in the JSON repr
        # with the json.dumps() of the corresponding wrapped Python object.
        for encoded in super(MyEncoder, self).iterencode(obj, **kwargs):
            match = self.regex.search(encoded)
            if match:
                id = int(match.group(1))
                no_indent = PyObj_FromPtr(id)
                json_repr = json.dumps(no_indent.value, **self._kwargs)
                # Replace the matched id string with json formatted representation
                # of the corresponding Python object.
                encoded = encoded.replace('"{}"'.format(format_spec.format(id)), json_repr)

            yield encoded
