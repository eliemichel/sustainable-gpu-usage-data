import os
from os.path import dirname, join, isfile
import json
import shutil
import logging
import pandas as pd

annotated_file_filepath = join('versionned-data', 'device-search-results-70_annotated.json')

#######################################

df_all = pd.read_csv(join("versionned-data", "device-database", "all-gpus.csv"), sep=';')
df_all["Full Name"] = df_all["Vendor"] + " " + df_all['Product Name']

with open(annotated_file_filepath, "r", encoding="utf-8") as f:
    data = json.load(f)

    cpu_found_count = 0
    cpu_error_count = 0

    gpu_found_count = 0
    gpu_error_count = 0

    false_matches_count = 0

    for paper_key, devices_data in data.items():
        for device in devices_data:

            # Find device type
            device_type = 'cpu'
            if (df_all['Full Name'] == device['device_name']).any():
                device_type = 'gpu'

            if device['status'] == 'CORRECT':
                if device_type == 'gpu':
                    gpu_found_count += 1
                else:
                    cpu_found_count += 1
            elif device['status'] == 'ERROR':
                if device_type == 'gpu':
                    gpu_error_count += 1
                else:
                    cpu_error_count += 1
            else:
                false_matches_count += 1

    print(f"Nb of papers treated: {len(data.items())}")

    print(f"Nb of GPU found correctly = {gpu_found_count}")
    print(f"Nb of GPU with an error = {gpu_error_count}")
    print(f"Nb of CPU found correctly = {cpu_found_count}")
    print(f"Nb of CPU with an error = {cpu_error_count}")
    print(f"Nb of false positive matches = {false_matches_count}")