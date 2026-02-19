import os
from os.path import dirname, join, isfile
import json
import shutil
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import itertools

# starting from an annotation file
annotated_file_filepath = join('versionned-data', 'device-search-results-70_annotated.json')
manual_devices_file_filepath = join('versionned-data', 'device-search-results-70_manual_labels.json')

with open(annotated_file_filepath, "r", encoding="utf-8") as f:
    annotation_data = json.load(f)

with open(manual_devices_file_filepath, "r", encoding="utf-8") as f:
    manual_data = json.load(f)

df_gpus = pd.read_csv(join("versionned-data", "device-database", "all-gpus.csv"), sep=';')
df_gpus["Full Name"] = df_gpus["Vendor"] + " " + df_gpus['Product Name']

df_cpus = pd.read_csv(join("versionned-data", "device-database", "all-cpus.csv"), sep=';')
df_cpus["Full Name"] = df_cpus["Vendor"] + " " + df_cpus['Name']


gpu_names = []
cpu_names = []

for paper_id, device_annotations in annotation_data.items():

    for device_data in itertools.chain(device_annotations, [] if paper_id not in manual_data else manual_data[paper_id]):
        device_name = None
        print(paper_id)
        if device_data['status'] == 'CORRECT':
            device_name = device_data['device_name']

        if device_name is not None:
            # Find device type
            if (df_gpus['Full Name'] == device_name).any():
                if device_name not in gpu_names:
                    gpu_names.append(device_name)
            elif (df_cpus['Full Name'] == device_name).any():
                if device_name not in cpu_names:
                    cpu_names.append(device_name)
            else:
                print(f"Warning: paper {paper_id}. {device_name} was not found as a GPU or CPU")

# aggregation table
df_paper_names = pd.read_csv(join("versionned-data", "aggregate-data", "paper_gpus_name_aggregation.csv"))

# Add new names to the aggregation data table (this table can be manually edited to aggregate as needed)
df_paper_names_new = pd.DataFrame(data={'labeled gpu': gpu_names, 'aggregate gpu': gpu_names})
df_paper_names = df_paper_names.combine_first(df_paper_names_new).sort_values(by="labeled gpu")
df_paper_names.to_csv(join("versionned-data", "aggregate-data", "paper_gpus_name_aggregation.csv"), index=False)

# fig, (ax_1, ax_2) = plt.subplots(1, 2)