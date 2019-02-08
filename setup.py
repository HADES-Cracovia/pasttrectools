#!/usr/bin/env python3

from setuptools import setup
import re

def vercmp(version1, version2):
    def normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
    a = normalize(version1)
    b = normalize(version2)
    return ((a>b) - (a<b))

try:
    import pkg_resources
except ImportError:
    print("No setuptools installed for this Python version")
else:
    dist = pkg_resources.get_distribution('setuptools')

if vercmp(dist.version, "40.0.0") >= 0:
    setup()
else:
    setup(
        name='pasttrectools',
        version='0.2',
        description='Tools for scanning and configuring pasttrec ASICs',
        url='https://github.com/HADES-Cracovia/pasttrectools',
        author='Rafal Lalik',
        author_email='rafal.lalik@uj.edu.pl',
        license='MIT',
        packages=['pasttrec'],
        scripts = [
            'baseline/baseline_scan.py',
            'baseline/calc_baselines.py',
            'baseline/draw_baseline_scan.py',
            'baseline/threshold_scan.py',
            'baseline/dump_threshold_scan.py',
            'baseline/communication_test.py',
            'baseline/reset_asic.py',
            'baseline/pasttrec_write_and_verify.py',
            ],
        install_requires=[
            'colorama',
            ],
        zip_safe=False
    )
