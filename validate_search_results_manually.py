import os
from os.path import dirname, join, isfile
import json
from urllib.parse import urlencode
import shutil
import logging
logger = logging.getLogger(__name__)


#######################################

def make_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog='validate_search_results_manually.py',
        description='Label as true/false the results extracted by extract_device_names_from_papers.py.',
    )

    parser.add_argument(
        '-i', '--input',
        type = str,
        default = join(dirname(__file__), "data", "processed", "automatic", "device-search-results.json"),
        help = "Search results json file that we want to annotate manually.",
    )

    parser.add_argument(
        '-o', '--output',
        type = str,
        default = join(dirname(__file__), "data", "processed", "manual"),
        help = "Directory where to output analysis.",
    )

    parser.add_argument(
        '--start',
        type = int,
        default = 0,
        help = "Index of the paper to start at.",
    )

    parser.add_argument(
        '--end',
        type = int,
        default = None,
        help = "Index of the paper to start at.",
    )

    # parser.add_argument(
    #     '-c', '--correct',
    #     default = False,
    #     action = 'store_true',
    #     help = "Open prompt to input device name and correct erroneous matches.",
    # )

    return parser

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

def main(args):
    setup(args)

    output_file_name = os.path.splitext(os.path.split(args.input)[1])[0] + "_annotated.json"
    output_file_path = join(args.output, output_file_name)

    analysis_results = load_json(args.input)

    validated_results = {}

    if os.path.exists(output_file_path):
        validated_results = load_json(output_file_path)
        print(f"Loading pre-existing results, already {len(validated_results.keys())} papers done out of {len(analysis_results.keys())}.")

    total_papers_count = len(analysis_results.keys())
    end = total_papers_count - 1
    if args.end is not None:
        end = args.end

    papers_to_do_count = end - args.start

    for idx_in_list, (paper_id, paper_data) in enumerate(analysis_results.items()):
        if idx_in_list < args.start:
            continue
        papers_treated_count = len(validated_results.keys())
        print("===========================================")
        print(f"Overall Progress: {papers_treated_count}/{total_papers_count}")
        print(f"Current Progress: {idx_in_list - args.start}/{papers_to_do_count}")
        print(f"Paper {idx_in_list}: {paper_id.encode('utf8')}")

        if paper_id in validated_results:
            print("Skipping - already labelled")
            continue

        # sort matches by score
        matches_list = sorted(paper_data, key=lambda x: x['score'], reverse=True)

        paper_devices_validated_list = []

        for match_id, match_data in enumerate(matches_list):
            print(f"Match {match_id+1}/{len(matches_list)}")
            print(f"Score:                      {match_data['score']:1f}")
            print(f"Matched device name:        {match_data['device_name']}")
            try:
                print(f"Text window matched:        {repr(match_data['location']['window'])}")
            except:
                print(f"Text window matched:        {match_data['location']['window'].encode()}")

            validation_label_txt = input("Correct? ([Y]es, [E]rror, [N]one, empty defaults to None)> ")
            
            # validated = validation_label_txt == 'Y'

            output_match_data = match_data.copy()


            status = "NO MATCH"

            if validation_label_txt.upper() == 'Y':
                status = "CORRECT"
            elif validation_label_txt.upper() == 'E':
                status = "ERROR"
                # if args.correct:
                #     corrected_model_name = input("Correct model name (return empty to pass correction step) >")
                #     if corrected_model_name != '':
                #         output_match_data['model_name_corrected'] = corrected_model_name
                #         output_match_data['correction_notes'] = input("Notes (optional)>")
            
            # populate the output data
            output_match_data['status'] = status
            paper_devices_validated_list.append(output_match_data)

            print("--------------------------------")

        validated_results[paper_id] = paper_devices_validated_list

        save_json(output_file_path, validated_results)

#######################################

if __name__ == "__main__":
    parser = make_parser()
    main(parser.parse_args())