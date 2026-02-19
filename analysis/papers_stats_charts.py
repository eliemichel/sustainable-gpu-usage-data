import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Rectangle
from datetime import datetime as dt
import os
import random

from matplotlib_bar_link import make_bar_link_patch
from utils import prepare_usage_and_performance_data


df_steam = pd.read_csv(os.path.join("..", "versionned-data", "device-database", "steam-gpu-users-per-year.csv"), sep=";")
df_benchmark = pd.read_csv(os.path.join("..", "versionned-data", "device-database", "blender-benchmark-2025.csv"))

df_papers = pd.read_csv(os.path.join("..", "versionned-data", "aggregate-data", "gpus_papers.csv"))
df_papers_to_benchmark = pd.read_csv(os.path.join("..", "versionned-data", "aggregate-data", "papers_gpu_to_benchmark_gpus.csv"))

df_devices_per_paper = pd.read_csv(os.path.join("..", "versionned-data", "aggregate-data", "devices_per_paper.csv"))

year_start = 2018
year_end = 2024
# users_ratio_threshold = 0.2



# Nb of papers per GPU (total over the years)
gpu_citations_count = df_papers.groupby("device").count().sort_values(by="paper_ID", ascending=False)

gpu_citations_count = gpu_citations_count.rename(columns = {'paper_ID': '# papers'})
gpu_citations_count[:10].plot.barh(y="# papers")

# plt.savefig("papers_per_gpu.svg")
# plt.show()

# Nb of papers per GPU and per year (for top 10 GPUs)
df_papers["year"] = df_papers["paper_ID"].map(lambda x :  int(x.split("/")[0]))

top_10_gpus_df = gpu_citations_count[:10]

# Sort those 10 gpus by performance
mapping_dict = dict(df_papers_to_benchmark.values)
top_10_gpus_df["TPU Device Name"] = top_10_gpus_df.index
top_10_gpus_df["Benchmark Device Name"] = top_10_gpus_df.index.map(lambda x : mapping_dict[x])
top_10_gpus_df = top_10_gpus_df.merge(df_benchmark, left_on="Benchmark Device Name", right_on="Device Name", how='left')
top_10_gpus_df = top_10_gpus_df.sort_values("Median Score", ascending=True, na_position='first')
# print(top_10_gpus_df)
top_10_gpus = top_10_gpus_df['TPU Device Name']
print(top_10_gpus)

# For each of the top 10 GPU, collect its count of papers per year
df_gpu_count_per_year = pd.DataFrame(index=np.arange(2018, 2025))
for gpu in top_10_gpus:
    print(gpu)
    # Select rows of the df that correspond to that gpu
    papers_with_that_gpu = df_papers[df_papers["device"] == gpu]
    # group by year
    papers_count_per_year = papers_with_that_gpu.groupby("year").count()
    papers_count_per_year = papers_count_per_year.rename(columns = {'device': gpu})[gpu]
    print(papers_count_per_year)
    df_gpu_count_per_year = df_gpu_count_per_year.merge(papers_count_per_year, left_index=True, right_index=True, how='left')


df_gpu_count_per_year = df_gpu_count_per_year.fillna(0)
print(df_gpu_count_per_year)

df_gpu_count_per_year.plot.bar(stacked=True)

# plt.show()
plt.savefig("gpus_in_papers_per_year.svg")

# # Nb of GPUs reported per paper
# papers_gpu_count = df_papers.groupby("paper_ID").count()
# papers_gpu_count["year"] = papers_gpu_count.index.map(lambda x :  int(x.split("/")[0]))
# print(papers_gpu_count)

# df_devices_per_paper["year"] = df_devices_per_paper["paper_ID"].map(lambda x :  int(x.split("/")[0]))

# rows = []
# for year in range(year_start, year_end+1):
#     total_papers_count_year = len(df_devices_per_paper[df_devices_per_paper["year"] == year])
#     print(f"Total nb of papers {total_papers_count_year} in {year}")
#     row = {'year': year}
#     papers_gpu_count_year = papers_gpu_count[papers_gpu_count["year"] == year].value_counts()

#     # print(papers_gpu_count_year)

#     row['No GPU'] = total_papers_count_year - papers_gpu_count_year.to_numpy().sum()

#     gpu_counts = papers_gpu_count_year.index.get_level_values('device').values
#     paper_counts = papers_gpu_count_year.values
#     for gpu_count, paper_count in zip(gpu_counts, paper_counts):
#         row[f"{gpu_count} GPU"] = paper_count

#     rows.append(row)


# df_bar_chart = pd.DataFrame(rows)
# df_bar_chart.fillna(0)

# print(df_bar_chart)

# cmap = matplotlib.cm.get_cmap('plasma')
# colors = []
# for i in range(6):
#     colors.append(cmap(i/5))
# df_bar_chart.plot.bar(x="year", stacked=True, color=colors)
# plt.savefig("gpus_reported_per_paper.svg")
