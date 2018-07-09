# pasttrectools
Tools for PASTTREC ASIC

## baseline scan

### Make scan

Use ```baseline_scan.py``` script, see ```--help``` for usage and options details.

Basic usage requires passage of TRBnet ids to scan:

    baseline_scan.py 0x6400 0x6401 0x6402 0x6403 ...

Default execution will generate ```result.json``` file (JSON format file) which can be chanegd using ```-o``` option.

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

### Drawing

Use ```draw_baseline_scan.py``` for drawing plots. Script requires one argument which is json input file, e.g.:

    ./draw_baseline_scan.py result.json