import os
from os.path import dirname, join, isfile
import json
from urllib.parse import urlencode
import shutil
import logging
logger = logging.getLogger(__name__)

import pypdfium2 as pdfium

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
        prog='analyze_papers.py',
        description='Extract info from papers that were downloaded using download_papers.py.',
    )

    parser.add_argument(
        '-d', '--data',
        type = str,
        default = join(dirname(__file__), "data", "papers"),
        help = "Data directory (output of download_papers.py).",
    )

    parser.add_argument(
        '-o', '--output',
        type = str,
        default = join(dirname(__file__), "data", "analysis"),
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

    parser.add_argument(
        '-k', '--keyword',
        type = str,
        nargs='*',
        default = None,
        help = "Add a keyword to look for in PDFs",
    )

    parser.add_argument(
        '-s', '--search-radius',
        type = int,
        default = 150,
        help = "Number of character to add before and after a match in search reports",
    )

    return parser

#######################################

def main(args):
    setup(args)

    #meta = load_json(join(args.data, "metadata.json"))

    status = load_json(join(args.output, "paper-status.json"))
    changed_status = False

    tocs = load_json(join(args.output, "tables-of-content.json"))
    changed_tocs = False

    search_results = load_json(join(args.output, "device-search-results.json"))
    changed_search_results = False

    all_paper_ids = list_paper_ids(args)

    for i, paper_id in enumerate(all_paper_ids):
        logger.info(f"Processing paper {paper_id}...")

        # We skip papers that have known errors
        if paper_id in status:
            if status[paper_id]["type"] == "error":
                continue

        try:

            paper = load_paper(join(args.data, f"{paper_id}.pdf"))
            
            if paper_id not in tocs:
                tocs[paper_id] = extract_toc(paper)
                changed_tocs = True

            if paper_id not in search_results:
                search_results[paper_id] = search_experimentation_device(paper, args.all_keywords, args.search_radius)
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
                save_json(join(args.output, "paper-status.json"), status)
                changed_status = False

            if changed_tocs:
                save_json(join(args.output, "tables-of-content.json"), tocs)
                changed_tocs = False

            if changed_search_results:
                save_json(join(args.output, "device-search-results.json"), search_results)
                changed_search_results = False

#######################################

def list_paper_ids(args):
    if args.paper is not None:
        return [ args.paper ]
    
    o = args.paper_offset
    m = args.max_paper_count
    all_files = os.listdir(args.data)
    if m is None:
        target_files = all_files[o:]
    else:
        target_files = all_files[o:o+m]

    return [
        item[:-4]
        for item in target_files
        if item.endswith(".pdf")
    ]

#######################################

def setup(args):
    os.makedirs(args.output, exist_ok=True)
    logging.basicConfig(level=logging.INFO)
    args.all_keywords = DEFAULT_KEYWORDS if args.keyword is None else args.keyword

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

def load_paper(path):
    pdf = pdfium.PdfDocument(path)
    return pdf

#######################################

def show_toc(pdf):
    for item in pdf.get_toc():
        state = "*" if item.n_kids == 0 else "-" if item.is_closed else "+"
        target = "?" if item.page_index is None else item.page_index+1
        print(
            "    " * item.level +
            "[%s] %s -> %s  # %s %s" % (
                state, item.title, target, item.view_mode, item.view_pos,
            )
        )

def extract_toc(pdf):
    result = []
    stack = [ (result, 1<<24) ] # (list, expected_children)
    for item in pdf.get_toc():
        entry = {
            "title": item.title,
            "children": [],
        }

        # Sanity check
        if not stack:
            logger.error(f"Inconsistency in toc children count, got more children than announced")
            break

        # Add to parent children
        parent_children, expected_children = stack[-1]
        parent_children.append(entry)
        expected_children -= 1
        stack[-1] = (parent_children, expected_children)

        # If all expected children have been found, move back to parent
        if expected_children == 0:
            stack = stack[:-1]

        # If the current item has children, recurse
        if item.n_kids > 0:
            stack.append((entry["children"], item.n_kids))

    return result

#######################################

def search_experimentation_device(pdf, all_keywords, window_radius):
    matches = []

    for page_idx in range(len(pdf)):
        #logger.info(f"Inspecting page {page_idx}...")
        page = pdf[page_idx]

        textpage = page.get_textpage()
        for keyword in all_keywords:
            searcher = textpage.search(keyword, match_case=False, match_whole_word=False)
            while occurrence := searcher.get_next():
                if occurrence is None:
                    break
                char_index, char_count = occurrence
                content = textpage.get_text_range(char_index - window_radius, char_count + 2 * window_radius)
                matches.append({
                    "keyword": keyword,
                    "location": {
                        "page": page_idx,
                        "char_index": char_index,
                        "char_count": char_count,
                    },
                    "content": content,
                })

    return matches

#######################################

if __name__ == "__main__":
    parser = make_parser()
    main(parser.parse_args())
