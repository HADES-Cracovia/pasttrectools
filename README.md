# pasttrectools
Tools for PASTTREC ASIC

Application is system-wide installable, contains of two parts:

 * `pastrec.py` module with the interface
 * user scripts

## Requirements

 * python >= 3.5
 * colorama
 * setuptools

## Installation

    python3 setup.py build
    sudo python3 setup.py install

## Baseline scan

### Make scan

Use `baseline_scan.py` script, see `--help` for usage and options details.

Basic usage requires passage of TRBnet ids to scan:

    baseline_scan.py 0x6400 0x6401 0x6402 0x6403 ...

Default execution will generate `result.json` file (JSON format file) which can be chanegd using `-o` option.

### JSON output format

The output contains a dictionary with a key being a TRBnet ids, e.g. in the example above:

    {
      0x6400 : ...,
      0x6401 : ...,
      0x6402 : ...,
      0x6403 : ...
    }

and values are mutlidimensional arrays of cables (2), asics(3), channels(8) and base line values (32)

    [
      [                     # cable 1
        [                   # asic #1
          [                 # channel #0
            0, 0, 0, ...    # 32 values for a counts for each base line
          ],
          [ ... ],
          ...
          [ ... ],          # channel 7
        ],
        [                   # asic #2
          ...
        ]
      ],
      [                     # cable #2
        [ asic #1 ], [ asic #2 ]
      ],
      [                     # cable 3
        [ asic #1 ], [ asic #2 ]
      ]
    ]

## Drawing

Use `draw_baseline_scan.py` for drawing plots. Script requires one argument which is json input file, e.g.:

    ./draw_baseline_scan.py result.json


## Extract baselines

Use `calc_baselines.py`, see `-h` for details. It allows to

* extract average baseline (weighted mean: `bl = Sum_i(ch_i*cnt)/Sum(ch_i)`),
* add offset for all channels (use `-blo val`, where val is a number), if offset is not given, user will be ask for offset for each chip,
* dump registers to file, if `-D` then all registers, if `-d` then only baseline registers,
* export configuration in json format.

The json output contains a dictionary with a key being a TRBnet ids, e.g. in the example above:

    {
      "version" : 1.0,
      "0x6400" : ...,
      "0x6400" : ...,
      "0x6401" : ...,
      "0x6402" : ...,
      "0x6403" : ...
    }

and values are next-level dictionaries of cables:

    {
      "cable1" : ...,
      "cable2" : ...,
      "cable3" : ...
    }

containing card info and asics:

    {
      "name" : "noname",  # 'nonane' is default
      "asic1" : ...,
      "asic2" : ...
    }

and each asic dictionary list of Pasttrec registers and settings, e.g.:

    {
      "bg_int": 1,
      "gain": 2,
      "peaking": 3,
      "tc1c": 3,
      "tc1r": 2,
      "tc2c": 6,
      "tc2r": 5,
      "vth": 10,
      "bl": [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0
      ]
    }

The version in `pasttrec.LIBVERSION` must be changed each time when structure/format of json data is changed.

Example usage:

    ./calc_baselines.py input.json -D output.dat -blo 0 -o output.json
