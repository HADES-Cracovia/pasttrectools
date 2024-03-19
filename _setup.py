#!/usr/bin/env python3

from setuptools import setup
import re


def vercmp(version1, version2):
    def normalize(v):
        return [int(x) for x in re.sub(r"(\.0+)*$", "", v).split(".")]

    a = normalize(version1)
    b = normalize(version2)
    return (a > b) - (a < b)


try:
    import pkg_resources
except ImportError:
    print("No setuptools installed for this Python version")
else:
    dist = pkg_resources.get_distribution("setuptools")

if vercmp(dist.version, "40.0.0") >= 0:
    setup()
else:
    setup(
        name="pasttrectools",
        version="0.11.0",
        description="Tools for scanning and configuring pasttrec ASICs",
        url="https://github.com/HADES-Cracovia/pasttrectools",
        author="Rafal Lalik",
        author_email="rafal.lalik@uj.edu.pl",
        license="MIT",
        packages=["pasttrec"],
        scripts=[
            "tools/asic_scan.py",
            "tools/asic_push.py",
            "tools/asic_read.py",
            "tools/asic_reset.py",
            "tools/asic_set.py",
            "tools/asic_tempid.py",
            "tools/asic_threshold.py",
            "tools/baseline_calc.py",
            "tools/baseline_merge.py",
            "tools/baseline_scan.py",
            "tools/compare_baselines.py",
            "tools/draw_baseline_scan.py",
            "tools/dump_threshold_scan.py",
            "tools/pasttrec_write_and_verify.py",
            "tools/scalers_scan.py",
            "tools/spi_scan.py",
            "tools/threshold_scan.py",
            "tools/trb_scan.py",
        ],
        install_requires=[
            "colorama",
        ],
        zip_safe=False,
    )
