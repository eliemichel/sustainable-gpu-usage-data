import os
from os.path import dirname, join, isfile
import csv
import json
import shutil
import logging
import dataclasses
logger = logging.getLogger(__name__)

from DeviceNameMatcher import DeviceNameMatcher

#######################################

def makeParser():
    import argparse

    parser = argparse.ArgumentParser(
        prog='test_rapidfuzz.py',
        description="Test device name mathcing.",
    )

    DeviceNameMatcher.addCliArguments(parser)

    return parser

#######################################

def main(args):
    setup(args)
    matcher = DeviceNameMatcher(args)
    matcher.testing = True

    #testMatcher(matcher, "ak memory, Nvidia Geforce GTX 850M the L2\r\nerror, and the L\u221e error.\r\nmachines use hyper-threading). In Table 1 we summarize the tim\ufffeings for the large dataset using a 2.6GHz Intel Xeon E5-2690v4 with\r\n8 threads. In all cases, the total time is dominated by the solving\r\ntime.\r\nConvergence. Figures 17 and 18 show the convergence ")

    #testMatcher(matcher, "ion of the OLAS in Python ran in 58.5 ms when run\r\non a GPU (NVIDIA Quadro RTX 8000). Including the tim")

    #testMatcher(matcher, "n on a desktop computer (CPU:\r\nIntel i7-7770 with 64 GB RAM, GPU: NVidia ")

    testMatcher(matcher, " For the hardware platform, the experiments are run on a desktop computer with Intel(R) Core(TM) i7-6700 CPU with 3.40GHz, 32GB DDR4 RAM.")

#######################################

def setup(args):
    logging.basicConfig(level=logging.INFO)

#######################################

def testMatcher(matcher, text):
    all_matches = matcher.searchAllDeviceNames(text)
    for m in all_matches:
        print(json.dumps(m, indent=2, cls=EnhancedJSONEncoder))

#######################################

class EnhancedJSONEncoder(json.JSONEncoder):
    """https://stackoverflow.com/questions/51286748/make-the-python-json-encoder-support-pythons-new-dataclasses"""
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

#######################################

if __name__ == "__main__":
    parser = makeParser()
    main(parser.parse_args())
