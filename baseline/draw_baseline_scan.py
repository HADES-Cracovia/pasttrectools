#!/usr/bin/env python3

import argparse
import json
import matplotlib.pyplot as plt
import sys

if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Submit dst analysis to GSI batch farm')
    parser.add_argument('json_file', help='list of arguments', type=str)
    args=parser.parse_args()

    print(args)

    with open(args.json_file) as json_data:
        d = json.load(json_data)
        json_data.close()

    x = list(range(0,32))

    plt.figure(1)

    idx = 1
    for k,v in d.items():
        plt.figure(idx)
        for c in [0,1,2]:
            for a in [0,1]:
                for ch in list(range(8)):

                    plt.subplot(3, 2, c*2 + a + 1)
                    dd = v[c][a][ch]

                    sum_d = sum(dd)
                    if sum_d > 0:
                        n = 1.0/sum_d
                    elif sum_d < 0:
                        n = 0
                    else:
                        n = 1.0
                    d = [i * n for i in dd]
                    plt.plot(x, d, label='{:d}'.format(ch))

                    plt.xlabel('baseline register')
                    plt.ylabel('pdf')

                plt.legend(loc=6, title='C: {:d}  A: {:d}'.format(c, a))

        idx += 1


    plt.show()
