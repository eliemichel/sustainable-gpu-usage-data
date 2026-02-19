import os
from os.path import dirname, join, isfile, relpath
import json
from urllib.parse import urlencode
import shutil
import logging
logger = logging.getLogger(__name__)

import pypdfium2 as pdfium

from DeviceNameMatcher import DeviceNameMatcher

#######################################

DEFAULT_KEYWORDS = [
    "NVIDIA",
    "Intel",
    "AMD",
]

#######################################

def make_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog='extract_device_names_from_papers.py',
        description='Extract device names from papers that were downloaded using download_papers.py.',
        formatter_class = argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '-d', '--data',
        type = str,
        default = join(dirname(__file__), "data", "raw", "papers"),
        help = "Data directory (output of download_papers.py).",
    )

    parser.add_argument(
        '-r', '--recursive',
        action = 'store_true',
        default = False,
        help = "Recurse in input data directory (i.e., look for PDFs in all subdirectories).",
    )

    parser.add_argument(
        '-o', '--output',
        type = str,
        default = join(dirname(__file__), "data", "processed", "automatic"),
        help = "Directory where to output automatic device names extraction results.",
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

    DeviceNameMatcher.addCliArguments(parser)

    return parser

#######################################

def main(args):
    setup(args)

    matcher = DeviceNameMatcher(args)

    status = loadJson(join(args.output, "paper-status.json"))
    changed_status = False

    search_results_filepath = join(args.output, "device-search-results.json")

    search_results = loadJson(search_results_filepath)
    changed_search_results = False

    all_paper_ids = listPaperIds(args)

    for i, paper_id in enumerate(all_paper_ids):
        logger.info(f"Processing paper {paper_id}...")

        # We skip papers that have known errors
        if paper_id in status:
            if status[paper_id]["type"] == "error":
                continue

        try:

            paper = pdfium.PdfDocument(join(args.data, f"{paper_id}.pdf"))
            
            if paper_id not in search_results:
                search_results[paper_id] = searchExperimentationDevices(paper, matcher)
                changed_search_results = True

            paper.close()

        except pdfium.PdfiumError as err:
            status[paper_id] = {
                "type": "error",
                "message": str(err),
            }
            changed_status = True

        if i % 10 == 0 or i == len(all_paper_ids) - 1:
            if changed_status:
                saveJson(join(args.output, "paper-status.json"), status)
                changed_status = False

            if changed_search_results:
                saveJson(search_results_filepath, search_results)
                changed_search_results = False

#######################################

def setup(args):
    os.makedirs(args.output, exist_ok=True)
    logging.basicConfig(level=logging.INFO)

#######################################

def listPaperIds(args):
    if args.paper is not None:
        return [ args.paper ]
    
    o = args.paper_offset
    m = args.max_paper_count

    all_paper_ids = []
    for root, dirs, files in os.walk(args.data):
        
        has_enough_files = False
        for name in files:
            if not name.endswith(".pdf"):
                continue
            filepath = relpath(join(root, name), args.data)
            if o > 0:
                o -= 1
            else:
                paper_id = filepath.replace("\\", "/")[:-4]
                all_paper_ids.append(paper_id)
                has_enough_files = m is not None and len(all_paper_ids) >= m
            if has_enough_files:
                break

        if not args.recursive or has_enough_files:
            break

    return all_paper_ids

#######################################

def loadJson(filepath):
    logger.info(f"Loading json data from '{filepath}'...")
    if isfile(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}

def saveJson(filepath, data):
    logger.info(f"Saving json data to '{filepath}'...")
    with open(filepath + ".part", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    shutil.move(filepath + ".part", filepath)

#######################################

def searchExperimentationDevices(pdf, matcher):
    matches = []

    for page_idx in range(len(pdf)):
        page = pdf[page_idx]
        text = page.get_textpage().get_text_bounded()

        for m in matcher.searchAllDeviceNames(text):
            matches.append({
                "device_name": m.device_name,
                "score": m.score,
                "location": {
                    "page": page_idx,
                    "window_offset": m.window_offset,
                    "window": m.window,
                    "match": m.match,
                    "match_offset": m.match_offset,
                    "token": m.token,
                    "token_offset": m.token_offset,
                },
            })

    return matches

#######################################

if __name__ == "__main__":
    parser = make_parser()
    main(parser.parse_args())
