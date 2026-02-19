import os
from os.path import dirname, join, isfile
import json
import shutil
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Match the dataframe of devices from papers, to the dataframe of users per devices
df_devices_from_papers = pd.read_csv(join("versionned-data", "aggregate-data", "gpus_papers.csv"))
df_devices_from_benchmark = pd.read_csv(join("versionned-data", "device-database", "blender-benchmark-2025.csv"))

df_matching = pd.read_csv(join("versionned-data", "aggregate-data", "papers_gpu_to_benchmark_gpus.csv"))

devices_names = df_devices_from_papers["device"]
# print(devices_names)

# tpu_to_blender_matching_table = []
tpu_to_blender_matching_table = {}



for device_name in devices_names:
    # skip if already matched
    if df_matching["paper name"].isin([device_name]).any():
        # print(df_matching["paper name"].isin([device_name]))
        print(f"Already dealt with {device_name}")
        tpu_to_blender_matching_table[device_name] = df_matching[df_matching["paper name"].isin([device_name])].iloc[0]["benchmark name"]
        # tpu_to_blender_matching_table.append({"paper name": device_name, "benchmark name": df_matching[df_matching["paper name"].isin([device_name])].iloc[0]["benchmark name"]})
        continue

    if device_name in tpu_to_blender_matching_table:
        print(f"Already dealt with {device_name}")
        continue

    benchmark_name = ""
    # Look for a match in steam data
    matches_in_tpu = df_devices_from_benchmark[df_devices_from_benchmark["Device Name"].isin([device_name])]
    if len(matches_in_tpu) > 0:
        print(f"Found match for {device_name}")
        # print(matches_in_tpu)
        benchmark_name = matches_in_tpu.iloc[0]["Device Name"]

    else:
        print(f"Did not find match for {device_name}")
        search_str = input("Search string for model name (return empty to pass) >")
        if search_str != '':
            # Return matches from gpu and cpu tables
            matches = []
            filter_rows = df_devices_from_benchmark['Device Name'].str.contains(search_str.lower(), case=False)
            matches = df_devices_from_benchmark[df_devices_from_benchmark['Device Name'].str.contains(search_str.lower(), case=False)]
            print(f"Found {len(matches)} matches for gpus.")
            if len(matches) > 0:
                print("Device matches:")
                for match_idx, match in enumerate(matches['Device Name']):
                    print(f"[{match_idx + 1}] - {match}")
                match_id = input("Correct model (empty if none match) >")
                if match_id != '':
                    benchmark_name = matches.iloc[int(match_id) - 1]['Device Name']

    # tpu_to_blender_matching_table.append({"paper name": device_name, "benchmark name": benchmark_name})
    tpu_to_blender_matching_table[device_name] = benchmark_name

    


df_devices_match = pd.DataFrame.from_dict(tpu_to_blender_matching_table, orient='index', columns=["benchmark name"])
# df_devices_match["paper name"] = df_devices_match.index
df_devices_match = df_devices_match.reset_index()
df_devices_match = df_devices_match.rename(columns={'index': 'paper name'})

df_devices_match.to_csv(join("versionned-data", "aggregate-data", "papers_gpu_to_benchmark_gpus.csv"), index=False)