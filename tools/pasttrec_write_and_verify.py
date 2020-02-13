#!/bin/env python3

import argparse
import subprocess

if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Write and verify data',
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

#    parser.add_argument('file', help='file to send', type=lambda x: str(x,0), nargs='+')
    parser.add_argument('file', help='file to send')

    parser.add_argument('-v', '--verbose', help='verbose level: 0, 1, 2, 3', type=int, choices=[ 0, 1, 2, 3 ], default=1)

    args=parser.parse_args()

    print(args)

    with open(args.file) as f:
        data = f.readlines()
#        print(data)
        for line in data:
            words = line.split()

            # write word
            rc = subprocess.run(words, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # preapre readback
            rb = words
            data = int(rb[4], 16) | 0x1000
            rb[4] = hex(data)
            # write word-read request
            if args.verbose:
                print(' '.join(words))
            rc = subprocess.run(words, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            read_cmd = words[0:4]
            read_cmd[1] = 'r'
            # read data
            rc = subprocess.run(read_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ret_data = int(rc.stdout.split()[1], 16)

            orig_data = int(rb[4][-2:], 16)

            if ret_data != orig_data:
                print("Write error at line: ", ' '.join(words))
                print("  written: ", hex(orig_data), "  Received: ", hex(ret_data))
#            print(orig_data, ret_data)
