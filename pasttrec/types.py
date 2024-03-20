import json
import re
from _ctypes import PyObj_FromPtr  # see https://stackoverflow.com/a/15012814/355230

from pasttrec import etrbid


# From https://stackoverflow.com/questions/42710879/write-two-dimensional-list-to-json-file
class NoIndent(object):
    """Value wrapper."""

    def __init__(self, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError("Only lists and tuples can be wrapped")
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "NoIndent(" + self.__str__() + ")"


class ScanData:
    """Holds scan data for given card."""

    def __init__(self, depth):
        self.data = {}
        self.depth = depth

    def add_card(self, uid, trb_design_type):
        if uid not in self.data:
            w = self.depth
            h = trb_design_type.n_channels
            a = trb_design_type.n_asics
            self.data[etrbid.padded_hex(uid, 16)] = {
                "config": None,
                "results": [[NoIndent([0 for x in range(w)]) for y in range(h)] for _a in range(a)],
            }


class Baselines(ScanData):
    """Holds baseline info for given card"""

    def __init__(self):
        super().__init__(32)


class Thresholds(ScanData):

    def __init__(self):
        super().__init__(128)


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
