# pasttrectools

This is a set of various tools for PASTTREC ASIC. The tools are designed to be use with TRBnet network used in HADES and FAIR experiments.

The repository contains two parts:
* set of general libraries to be included in the user code,
* set of various tools to read, write and control the ASIC chips.

## Requirements

The library requires `python-3.5` or later, additional dependencies are:
 * colorama
 * setuptools

## Installation

    python3 setup.py build
    sudo python3 setup.py install

or

    pip install .

# Usage

## List of tools

The `tools` directory provides list of various tools:
* `asic_scan.py` - test communication with ASIC
* `asic_push.py` - read data file and dump to script file or push to ASIC
* `asic_read.py` - read data from ASIC
* `asic_reset.py` - reset ASIC
* `asic_set.py` - set a single register in ASIC
* `asic_threshold.py` - set threshold in ASIC
* `baseline_calc.py` - calculate baselines using scan results
* `baseline_compare.py` - compare two baseline sets
* `baseline_merge.py` - merge differences in two base line sets
* `baseline_scan.py` - scan ASIC for baselines settings
* `draw_baseline_scan.py` - draw baseline scan histograms
* `dump_threshold_scan.py` - dump threshold scan results to file
* `pasttrec_write_and_verify.py` - write data to ASIC and verify correctness
* `scalers_scan.py` - scan scalers of ASICs
* `threshold_scan.py` - scan ASIC threshold settings
* `trb_scan.py` - test communication with TRB

Each tool provides basic help of its usage with command line option `-h` or `--help`.

### Addressing

Each tools uses common addressing scheme, allowing to indicate exact TRB address, the connection cable and one of two ASICs on a single cable.
The address `ADDRESS` has form of `0xADDR:CABLE:ASIC` where:
* `ADDR` can by any valid TRB address
* `CABLE` can take values 0-2 or be empty
* `ASIC` can take value 0-1 or be empty

`CABLE` and `ASIC` parts are optional, if none of them are provided one can also skip `::`. if `ASIC` is missing, one `:` can be omitted.

Example usage:
* `0xbeef` will address all ASICs under this trb net address, it will be expanded into `0xbeef:0:0 0xbeef:0:1 0xbeef:1:0 0xbeef:1:1 0xbeef:2:0 0xbeef:2:1`
* `0xbeef::` will also be expanded into `0xbeef:0:0 0xbeef:0:1 0xbeef:1:0 0xbeef:1:1 0xbeef:2:0 0xbeef:2:1`
* `0xbeef::0` will be expanded into `0xbeef:0:0 0xbeef:1:0`
* `0xbeef:0:` will be expanded into `0xbeef:0:0 0xbeef:0:1`
* `0xbeef:0` will also be expanded into `0xbeef:0:0 0xbeef:0:1`
* `0xbeef:1:2` will be expanded into `0xbeef:1:2`

### Dat files

ASIC settings are stored in human readable text files with following format (applicable to each line):

`ADDRESS r1 r2 r3 r4 r5 th b1 b2 b3 b4 b5 b6 b7 b8`

where:
* `r1`..`r4` are configuration registers values
* `th` is threshold register value
* `b1`..`b8` are baseline register values

Values can be given in decimal format or hexagonal format `0x____`.

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

Use `baseline_calc.py`, see `-h` for details. It allows to

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

    ./baseline_calc.py input.json -D output.dat -blo 0 -o output.json
