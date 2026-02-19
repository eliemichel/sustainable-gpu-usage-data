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

# Build a table:
# Paper ID  | GPU(s)       | CPU(s)
# (string)  | List[string] | List[string]

paper_ids = []
gpu_rows = []
cpu_rows = []

paper_ids_list_gpus = []
paper_ids_list_cpus = []
gpus_list = []
cpus_list = []

# Establish a list of devices found in papers
# gpus_dict = {}
# cpus_dict = {}

df_gpus = pd.read_csv(join("versionned-data", "device-database", "all-gpus.csv"), sep=';')
df_gpus["Full Name"] = df_gpus["Vendor"] + " " + df_gpus['Product Name']

df_cpus = pd.read_csv(join("versionned-data", "device-database", "all-cpus.csv"), sep=';')
df_cpus["Full Name"] = df_cpus["Vendor"] + " " + df_cpus['Name']

# aggregation table
df_paper_names_aggregation = pd.read_csv(join("versionned-data", "aggregate-data", "paper_gpus_name_aggregation.csv"))

# only put in the table the devices that are validated as "correct"
# or that are manually corrected (looking at the manual labels file)

for paper_id, device_annotations in annotation_data.items():
    gpus = []
    cpus = []

    for device_data in itertools.chain(device_annotations, [] if paper_id not in manual_data else manual_data[paper_id]):
        device_name = None
        if device_data['status'] == 'CORRECT':
            device_name = device_data['device_name']

        if device_name is not None:
            # Find device type
            if (df_gpus['Full Name'] == device_name).any():
                # Map the name to its aggregated name
                if (df_paper_names_aggregation['labeled gpu'] == device_name).any():
                    device_name = df_paper_names_aggregation['aggregate gpu'][df_paper_names_aggregation['labeled gpu'] == device_name].iloc[0]
                if device_name not in gpus:
                    gpus.append(device_name)

                    gpus_list.append(device_name)
                    paper_ids_list_gpus.append(paper_id)
                    # if device_name not in gpus_dict:
                    #     gpus_dict[device_name] = []
                    # gpus_dict[device_name].append(paper_id)
            elif (df_cpus['Full Name'] == device_name).any():
                if device_name not in cpus:
                    cpus.append(device_name)

                    cpus_list.append(device_name)
                    paper_ids_list_cpus.append(paper_id)
                    # if device_name not in cpus_dict:
                    #     cpus_dict[device_name] = []
                    # cpus_dict[device_name].append(paper_id)
            else:
                print(f"Warning: paper {paper_id}. {device_name} was not found as a GPU or CPU")

    # df.append({'paper_ID': [], 'GPUs': [], 'CPUs': []})
    paper_ids.append(paper_id)
    gpu_rows.append(gpus)
    cpu_rows.append(cpus)



df_devices_per_paper = pd.DataFrame({'paper_ID': paper_ids, 'GPUs': gpu_rows, 'CPUs': cpu_rows})


df_paper_gpus = pd.DataFrame({'paper_ID': paper_ids_list_gpus, 'device': gpus_list})
df_paper_cpus = pd.DataFrame({'paper_ID': paper_ids_list_cpus, 'device': cpus_list})

# Print some stats:
gpu_model_counts = df_devices_per_paper['GPUs'].apply(lambda x: len(x))
cpu_model_counts = df_devices_per_paper['CPUs'].apply(lambda x: len(x))

print(f"Papers with GPU info: {np.count_nonzero(gpu_model_counts > 0)} / {len(gpu_model_counts)}")
print(f"Papers with CPU info: {np.count_nonzero(cpu_model_counts > 0)} / {len(gpu_model_counts)}")


fig, (ax_1, ax_2) = plt.subplots(1, 2)

ax_1.set_title("# of GPU models detected")

ax_2.set_title("# of CPU models detected")

gpu_model_counts.value_counts().plot.pie(ax=ax_1, autopct='%1.1f%%')
cpu_model_counts.value_counts().plot.pie(ax=ax_2, autopct='%1.1f%%')


plt.show()


print(f"Nb of unique GPUs used: {len(df_paper_gpus['device'].unique())}")
print(f"Nb of unique CPUs used: {len(df_paper_cpus['device'].unique())}")

gpus_paper_counts = df_paper_gpus.groupby("device").count()
cpus_paper_counts = df_paper_cpus.groupby("device").count()

gpus_paper_counts = gpus_paper_counts.sort_values("paper_ID", ascending=False)
cpus_paper_counts = cpus_paper_counts.sort_values("paper_ID", ascending=False)
# df_paper_per_cpus = df_paper_per_cpus.sort_values("Papers count", ascending=False)


# only show top 10 for each

fig, (ax_1, ax_2) = plt.subplots(1, 2)
gpus_paper_counts.iloc[:10].plot.barh()
# df_paper_per_cpus.iloc[:10].plot.barh(x="Device")
# plt.subplots_adjust(left=0.5)
plt.show()


# save as a csv
df_devices_per_paper.to_csv(join("versionned-data", "aggregate-data", "devices_per_paper.csv"), index=False)
df_paper_gpus.to_csv(join("versionned-data", "aggregate-data", "gpus_papers.csv"), index=False)
df_paper_cpus.to_csv(join("versionned-data", "aggregate-data", "cpus_papers.csv"), index=False)