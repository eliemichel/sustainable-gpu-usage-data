import os
from os.path import dirname, join, isfile
import json
from urllib.parse import urlencode
import shutil
import logging
import pandas as pd

logger = logging.getLogger(__name__)


#######################################

def make_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog='correct_device_names_manually.py',
        description='CLI to inspect erroneous cases and assign the correct device(s).',
    )

    parser.add_argument(
        '-i', '--input',
        type = str,
        default = join(dirname(__file__), "data", "processed", "manual", "device-search-results_annotated.json"),
        help = "Annotation file that we want to make corrections to.",
    )

    parser.add_argument(
        '-u', '--user',
        type = str,
        default = "Emilie",
        help = "user name to put in notes",
    )

    parser.add_argument(
        '-o', '--output',
        type = str,
        default = join(dirname(__file__), "data", "processed", "manual", "device-search-results_manual_labels.json"),
        help = "Manual corrections file.",
    )

    parser.add_argument(
        '--cpu-database',
        type = str,
        default = join(dirname(__file__), "data", "raw", "devices", "all-cpus.csv"),
        help = "Path to the CPU database.",
    )

    parser.add_argument(
        '--gpu-database',
        type = str,
        default = join(dirname(__file__), "data", "raw", "devices", "all-gpus.csv"),
        help = "Path to the GPU database.",
    )

    return parser

#######################################

def setup(args):
    # os.makedirs(args.output, exist_ok=True)
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

    input_data = load_json(args.input)

    df_gpus = pd.read_csv(args.gpu_database, sep=';')
    df_gpus["Full Name"] = df_gpus["Vendor"] + " " + df_gpus['Product Name']

    df_cpus = pd.read_csv(args.cpu_database, sep=';')
    df_cpus["Full Name"] = df_cpus["Vendor"] + " " + df_cpus['Name']

    output_data = {}

    if os.path.exists(args.output):
        output_data = load_json(args.output)
        print(f"Loading pre-existing results, already {len(output_data.keys())} papers done")

    # filter to keep the items that need correction
    papers_to_correct = {}
    for paper_id, devices_data in input_data.items():
        for device in devices_data:
            if device['status'] == 'ERROR':
                papers_to_correct[paper_id] = devices_data
                break

    total_papers_count = len(papers_to_correct.keys())

    for idx_in_list, (paper_id, paper_data) in enumerate(papers_to_correct.items()):
        print("===========================================")
        print(f"Current Progress: {idx_in_list}/{total_papers_count}")
        print(f"Paper {idx_in_list}: {paper_id}")

        if paper_id in output_data:
            print("Skipping - already corrected")
            continue

        manual_paper_devices_list = []

        for match_id, match_data in enumerate(paper_data):
            if match_data['status'] == 'ERROR':
                print(f"Match {match_id+1}/{len(paper_data)}")
                print(f"Score:                      {match_data['score']:1f}")
                print(f"Matched device name:        {match_data['device_name']}")
                print(f"Text window matched:        {repr(match_data['location']['window'])}")

                nb_of_devices_to_input = input("Nb of devices to input (defaults to 0) >")
                print(nb_of_devices_to_input)

                if nb_of_devices_to_input == '' or nb_of_devices_to_input == '0':
                    output_corrected_device = {}
                    output_corrected_device['location'] = match_data['location']
                    output_corrected_device['device_type'] = 'None'
                    output_corrected_device['status'] = "ERROR"

                    # populate the output data (empty entry)
                    manual_paper_devices_list.append(output_corrected_device)
                    continue

                for device_input_idx in range(int(nb_of_devices_to_input)):
                    print(f"Device {device_input_idx+1}/{nb_of_devices_to_input}")
                    output_corrected_device = {}
                    output_corrected_device['location'] = match_data['location']

                    device_type = int(input("[1] for GPU, [2] for CPU>"))

                    search_str = input("Search string for model name (return empty to pass) >")
                    if search_str != '':
                        # Return matches from gpu and cpu tables
                        matches = []
                        if device_type == 1:
                            matches = df_gpus[df_gpus['Product Name'].str.contains(search_str.lower(), case=False)]
                            print(f"Found {len(matches)} matches for gpus.")
                        elif device_type == 2:
                            matches = df_cpus[df_cpus['Name'].str.contains(search_str.lower(), case=False)]
                            print(f"Found {len(matches)} matches for cpus.")
                        if len(matches) > 0:
                            print("Device matches:")
                            for match_idx, match in enumerate(matches['Full Name']):
                                print(f"[{match_idx + 1}] - {match}")
                            match_id = input("Correct model (empty if none match) >")
                            if match_id != '':
                                device_match = matches.iloc[int(match_id) - 1]['Full Name']
                                output_corrected_device['device_name'] = device_match
                                output_corrected_device['annotator_notes'] = f"{args.user}, ad-hoc search."
                                output_corrected_device['status'] = 'CORRECT'
                            else:
                                output_corrected_device['device_type'] = 'GPU' if device_type == 1 else 'CPU'
                                output_corrected_device['status'] = "NOT IN DB"
                        # output_corrected_device['annotator_notes'] = input("Notes (optional)>")
                        else:
                            output_corrected_device['device_type'] = 'GPU' if device_type == 1 else 'CPU'
                            status_int = int(input("No matches. Entry status? [1] AMBIGUOUS, [2] NOT IN DB>"))
                            if status_int == 1:
                                output_corrected_device['status'] = "AMBIGUOUS"
                            elif status_int == 2: 
                                output_corrected_device['status'] = "NOT IN DB"
                            else:
                                output_corrected_device['status'] = "OTHER"
                    else:
                        output_corrected_device['device_type'] = 'GPU' if device_type == 1 else 'CPU'
                        status_int = int(input("Skipping correction. Entry status? [1] AMBIGUOUS, [2] NOT IN DB>"))
                        if status_int == 1:
                            output_corrected_device['status'] = "AMBIGUOUS"
                        elif status_int == 2: 
                            output_corrected_device['status'] = "NOT IN DB"
                        else:
                            output_corrected_device['status'] = "OTHER"

                    manual_paper_devices_list.append(output_corrected_device)
                    
                
        
               

                print("--------------------------------")

        output_data[paper_id] = manual_paper_devices_list

        save_json(args.output, output_data)

#######################################

if __name__ == "__main__":
    parser = make_parser()
    main(parser.parse_args())