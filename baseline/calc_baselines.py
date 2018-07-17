#!/usr/bin/env python3

import argparse
import copy
import json
import sys

from baseline_scan import PasttrecRegs

if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Submit dst analysis to GSI batch farm')
    parser.add_argument('json_file', help='list of arguments', type=str)

    parser.add_argument('-o', '--output', help='output file', type=str)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--dump', help='trbcmd dump file, bl regs only', type=str)
    group.add_argument('-D', '--Dump', help='trbcmd dump file, all regs', type=str)

    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3', type=int, choices=[ 0, 1, 2, 3 ], default=0)

    parser.add_argument('-blo', '--offset', help='offset to baselines (ask for each chip if not given)', type=lambda x: int(x,0))

    parser.add_argument('-Vth', '--threshold', help='threshold: 0-127 (overwrites value from input file)', type=lambda x: int(x,0))
    parser.add_argument('-g', '--gain', help='gain: 0-3 (overwrites value from input file)', type=lambda x: int(x,0))


    args=parser.parse_args()

    print(args)

    with open(args.json_file) as json_data:
        d = json.load(json_data)
        json_data.close()

    dump_file = None
    if args.dump:
        dump_file = open(args.dump, 'w')

    if args.Dump:
        dump_file = open(args.Dump, 'w')

    out_file = None
    if args.output:
        out_file = open(args.output, 'w')

    bls = d['baselines']
    cfg = d['config']


    p = PasttrecRegs()

    for k,v in cfg.items():
        setattr(p, k, v)

    if args.threshold is not None:
        p.vth = args.threshold

    if args.gain is not None:
        p.gain = args.gain

    print(cfg)

    x = list(range(0,32))

    outd = {}

    idx = 1
    for k,v in bls.items():

        outd[k] = [[ None for _a in range(2)] for _c in range(3)]

        for c in [0,1,2]:
            for a in [0,1]:
                print("Scanning {:s}  CARD: {:d}  ASIC: {:d}".format(k, c, a))
                bl = [0] * 8

                for ch in list(range(8)):
                    b = v[c][a][ch]
                    s = 0
                    w = 0
                    for i in range(32):
                        s = s + i * b[i]
                        w += b[i]
                    if w == 0:
                        b = 0
                    else:
                        b = s/w
                    bl[ch] = int(round(b))
                    print(ch, v[c][a][ch], "==> bl: ", bl[ch])
                    #print("s={:d}  w={:d}  avg={:f}  bl={:d}".format(s, w, bl, r))

                if args.offset == None:
                    while True:
                        bbb = input("Offset for base lines (default: 0): ")
                        if bbb == "":
                            bl_offset = 0
                            break

                        if not bbb.isdigit():
                            print("Input is not a number, try again")
                            continue

                        bl_offset = int(bbb)
                        break
                else:
                    bl_offset = args.offset

                for ch in list(range(8)):

                    _r = bl[ch] + bl_offset
                    _r = max(_r, 0)
                    _r = min(_r, 127)

                    p.bl[ch] = _r

                outd[k][c][a] = copy.deepcopy(p.__dict__)

                if args.dump:
                    regs = p.dump_bl_hex(c, a)
                    for r in regs:
                        dump_file.write("trbcmd w {:s} {:s} {:s}\n".format(k, hex(PasttrecRegs.c_trbnet_reg), r))

                        if args.verbose >= 1:
                            print("trbcmd w {:s} {:s} {:s}".format(k, hex(PasttrecRegs.c_trbnet_reg), r))

                if args.Dump:
                    regs = p.dump_config_hex(c, a)
                    for r in regs:
                        dump_file.write("trbcmd w {:s} {:s} {:s}\n".format(k, hex(PasttrecRegs.c_trbnet_reg), r))

                        if args.verbose >= 1:
                            print("trbcmd w {:s} {:s} {:s}".format(k, hex(PasttrecRegs.c_trbnet_reg), r))

    if dump_file:
        dump_file.close()

    if out_file:
        out_file.write(json.dumps(outd, indent=2))
        out_file.close()
