import os
from os.path import dirname, join, isfile
import csv
import shutil
import logging
logger = logging.getLogger(__name__)

#######################################

def makeParser():
    import argparse

    parser = argparse.ArgumentParser(
        prog='fix_cpu_database.py',
        description="Add the missing 'vendor' columnn in CPU database (if missing).",
    )

    parser.add_argument(
        '-i', '--input',
        type = str,
        default = join(dirname(__file__), "versionned-data", "device-database", "all-cpus.csv"),
        help = "Path to the input CPU database.",
    )

    parser.add_argument(
        '-o', '--output',
        type = str,
        default = None,
        help = "Path to the output CPU database (same as input if not provided).",
    )

    return parser

#######################################
# Fix the CPU database by guessing the device's vendor (not included in the original database, sadly)

cpu_prefix_to_brand = {
    '1.1GigaPro': "VIA",
    '4800S': 'AMD',
    'A10 ': 'AMD',
    'A10-': 'AMD',
    'A100': 'Intel',
    'A110': 'Intel',
    'A12-9800': 'AMD',
    'A4': 'AMD',
    'A6': 'AMD',
    'A8': 'AMD',
    'A9': 'AMD',
    'Athlon': 'AMD',
    'Atom': 'Intel',
    'Aubrey': 'Intel',
    'C-': 'AMD',
    'C3': 'VIA',
    'Celeron': 'Intel',
    'Centaur': 'VIA',
    'Core': 'Intel',
    'E-': 'AMD',
    'E1-': 'AMD',
    'E2-': 'AMD',
    'EPYC': 'AMD',
    'FirePro': 'AMD',
    'FX': 'AMD',
    'GX': 'AMD',
    'K6-': 'AMD',
    'Mobile Athlon': 'AMD',
    'Mobile Pentium': 'Intel',
    'Nano': 'VIA',
    'Opteron': 'AMD',
    'Pentium': 'Intel',
    'Phenom': 'AMD',
    'Processor': 'Intel',
    'PRO': 'AMD',
    'Ryzen': 'AMD',
    'Sempron': 'AMD',
    'Steam': 'AMD',
    'Threadripper': 'AMD',
    'Turion': 'AMD',
    'Xeon': 'Intel',
    'Z-': 'AMD',
}

#######################################

def main(args):
    setup(args)
    fixDatabase(args)

#######################################

def setup(args):
    if args.output is None:
        args.output = args.input
    os.makedirs(dirname(args.output), exist_ok=True)
    logging.basicConfig(level=logging.INFO)

#######################################

def fixDatabase(args):
    with (
        open(args.input, newline='', encoding="utf-8") as fin,
        open(args.output + ".tmp", 'w', newline='', encoding="utf-8") as fout
    ):
        csv_reader = csv.reader(fin, delimiter=';', quotechar='"')
        csv_writer = csv.writer(fout, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        nothing_to_do = False
        for i, row in enumerate(csv_reader):
            if i == 0:
                name_col_idx = row.index("Name")
                if "Vendor" in row:
                    nothing_to_do = True
                else:
                    row.append("Vendor")
                csv_writer.writerow(row)
            elif nothing_to_do:
                csv_writer.writerow(row)
            else:
                csv_writer.writerow(processRow(row, name_col_idx))

    shutil.move(args.output + ".tmp", args.output)

#######################################

def processRow(row, name_col_idx):
    name = row[name_col_idx]
    vendor = None
    for name_prefix, vendor in cpu_prefix_to_brand.items():
        if name.startswith(name_prefix):
            break
    if vendor is None:
        logger.error(f"Could not find vendor for device '{name}'")
        exit(1)
    row.append(vendor)
    return row

#######################################

if __name__ == "__main__":
    parser = makeParser()
    main(parser.parse_args())
