#!/usr/bin/env python3
#
# Copyright 2018 Rafal Lalik <rafal.lalik@uj.edu.pl>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import json
import matplotlib.pyplot as plt
import sys

if __name__=="__main__":
    parser=argparse.ArgumentParser(description='Draw baseline scan results')
    parser.add_argument('json_file', help='list of arguments', type=str)
    args=parser.parse_args()

    print(args)

    with open(args.json_file) as json_data:
        d = json.load(json_data)
        json_data.close()

    x = list(range(0,32))

    plt.figure(1)

    idx = 1

    bls = d['baselines']

    for k,v in bls.items():
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
                    plt.semilogy(x, d, label='{:d}'.format(ch))

                    plt.xlabel('baseline register')
                    plt.ylabel('pdf')

                plt.legend(loc=6, title='C: {:d}  A: {:d}'.format(c, a))

        idx += 1


    plt.show()
