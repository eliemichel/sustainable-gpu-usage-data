import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Rectangle
from datetime import datetime as dt
import os
import random
import json
from os.path import dirname, join, isfile

from matplotlib_bar_link import make_bar_link_patch
from utils import prepare_usage_and_performance_data

# starting from an annotation file
annotated_file_filepath = join('..', 'versionned-data', 'device-search-results-70_annotated.json')
manual_devices_file_filepath = join('..', 'versionned-data', 'device-search-results-70_manual_labels.json')

with open(annotated_file_filepath, "r", encoding="utf-8") as f:
    annotation_data = json.load(f)

with open(manual_devices_file_filepath, "r", encoding="utf-8") as f:
    manual_data = json.load(f)

df_gpus = pd.read_csv(join("..", "versionned-data", "device-database", "all-gpus.csv"), sep=';')
df_gpus["Full Name"] = df_gpus["Vendor"] + " " + df_gpus['Product Name']


print(f"Total number of annotated papers = {len(annotation_data.keys())}")

total_annotations_count = 0
correct_auto_annotations_count = 0
false_positive_annotations_count = 0
erroneous_annotations_count = 0
for paper_id, matches in annotation_data.items():
    for device_data in matches:
        device_name = device_data['device_name']

        if device_name is not None:
            # Only count instances of GPU matches
            if (df_gpus['Full Name'] == device_name).any():
                total_annotations_count += 1

                if device_data['status'] == 'CORRECT':
                    correct_auto_annotations_count += 1
                elif device_data['status'] == 'NO MATCH':
                    false_positive_annotations_count += 1
                else:
                    erroneous_annotations_count += 1

manually_added_annotations_count = 0
for paper_id, matches in manual_data.items():
    for device_data in matches:
        if 'device_name' in device_data:
            # print(device_data)
            device_name = device_data['device_name']

            if device_name is not None:
                # Only count instances of GPU matches
                if (df_gpus['Full Name'] == device_name).any():
                    manually_added_annotations_count += 1

print(f"Total number of annotations = {total_annotations_count}")
print(f"Number of correct auto annotations = {correct_auto_annotations_count}")
print(f"Number of false positive annotations = {false_positive_annotations_count}")
print(f"Number of erroneous annotations = {erroneous_annotations_count}")
print(f"Number of manually added annotations = {manually_added_annotations_count}")

print(f"Number of correct annotations total = {manually_added_annotations_count + correct_auto_annotations_count}")

fig, ax = plt.subplots()
bottom = 0
width = 1

for count_name, count_value in zip(["correct", "false positive", "error"], [correct_auto_annotations_count, false_positive_annotations_count, erroneous_annotations_count]):
    p = ax.bar(0, count_value, width, label=count_name, bottom=bottom)
    bottom += count_value

ax.bar(1, manually_added_annotations_count, width, label="manual")

# ax.set_title("Number of penguins with above average body mass")
ax.legend(loc="upper right")

plt.savefig("papers-data-auto-collection-results.svg")