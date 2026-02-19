import os
from os.path import dirname, join, isfile
import json
from urllib.parse import urlencode
import shutil
import logging
logger = logging.getLogger(__name__)

import pypdfium2 as pdfium

#######################################

def make_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog='analyze_search_results_manually.py',
        description='Classify results extracted by analyze_papers.py.',
    )

    parser.add_argument(
        '-d', '--data',
        type = str,
        default = join(dirname(__file__), "data", "analysis"),
        help = "Data directory (output of analyze_papers.py), also used for output.",
    )

    parser.add_argument(
        '-o', '--output',
        type = str,
        default = join(dirname(__file__), "versionned-data"),
        help = "Directory where to output analysis.",
    )

    parser.add_argument(
        '-p', '--paper',
        type = str,
        help = "Paper id to focus on. If not provided, all papers are inspected",
    )

    parser.add_argument(
        '-m', '--max-paper-count',
        type = int,
        default = None,
        help = "Maximum number of papers to inspect. Actual number may differ if non-pdf files are found in the target range.",
    )

    parser.add_argument(
        '-f', '--paper-offset',
        type = int,
        default = 0,
        help = "Offset of the first paper to inspect, in the global list of papers",
    )

    return parser

#######################################

def main(args):
    setup(args)

    search_results = load_json(join(args.data, "device-search-results.json"))

    analysis_results = load_json(join(args.data, "device-search-analysis-manual.json"))
    changed_analysis_results = False

    all_paper_ids = list_paper_ids(args, search_results)

    for i, paper_id in enumerate(all_paper_ids):
        logger.info(f"Processing paper {paper_id}...")

        if paper_id not in analysis_results:
            analysis_results[paper_id] = analyze_results_manually(search_results[paper_id])
            changed_analysis_results = True

        if i % 10 == 0 or i == len(all_paper_ids) - 1:
            if changed_analysis_results:
                save_json(join(args.data, "device-search-analysis.json"), analysis_results)
                changed_analysis_results = False

#######################################

def list_paper_ids(args, search_results):
    if args.paper is not None:
        return [ args.paper ]
    
    o = args.paper_offset
    m = args.max_paper_count
    all_paper_ids = list(search_results.keys())
    if m is None:
        return all_paper_ids[o:]
    else:
        return all_paper_ids[o:o+m]

#######################################

def setup(args):
    os.makedirs(args.output, exist_ok=True)
    logging.basicConfig(level=logging.INFO)

#######################################

def load_json(filepath):
    logger.info(f"Loading json data from '{filepath}'...")
    if isfile(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}

def save_json(filepath, data):
    logger.info(f"Saving json data to '{filepath}'...")
    with open(filepath + ".part", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    shutil.move(filepath + ".part", filepath)

#######################################

def analyze_results_manually(matches):
    results = []
    for m in matches:
        print("--------------------------------")
        #print(f"Title: " + m["paper_title"])
        print(f"Keyword: " + m["keyword"])
        print(f"Content:\n" + m["content"])
        gpu_name = input("GPU Name> ")
        gpu_vram = input("GPU VRAM> ")
        cpu_name = input("CPU Name> ")
        cpu_ram = input("CPU RAM> ")
        results.append({
            "match": m,
            "annotation": {
                "gpu_name": gpu_name,
                "gpu_vram": gpu_vram,
                "cpu_name": cpu_name,
                "cpu_ram": cpu_ram,
            }
        })
    return results

#######################################

if __name__ == "__main__":
    parser = make_parser()
    main(parser.parse_args())
