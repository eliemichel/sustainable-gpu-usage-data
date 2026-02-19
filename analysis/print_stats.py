import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Rectangle
from datetime import datetime as dt
import os
import random
from os.path import dirname, join, realpath

from matplotlib_bar_link import make_bar_link_patch
from utils import prepare_usage_and_performance_data

ROOT = dirname(realpath(__file__))

df_steam = pd.read_csv(join(ROOT, "..", "data", "raw", "users", "steam-gpu-users-per-year.csv"), sep=";")
df_benchmark = pd.read_csv(join(ROOT, "..", "data", "raw", "benchmark", "blender-benchmark-2025.csv"))

df_papers = pd.read_csv(join(ROOT, "..", "data", "aggregated", "gpus_papers.csv"))
df_papers_to_benchmark = pd.read_csv(join(ROOT, "..", "data", "aggregated", "papers_gpu_to_benchmark_gpus.csv"))

df_devices_per_paper = pd.read_csv(join(ROOT, "..", "data", "aggregated", "devices_per_paper.csv"))

year_start = 2018
year_end = 2024
users_ratio_threshold = 0.2


df_papers["year"] = df_papers["paper_ID"].map(lambda x :  int(x.split("/")[0]))

df_usage_and_perf = prepare_usage_and_performance_data(
    df_steam,
    df_benchmark,
    year_start,
    year_end
    )


# General paper stats
print("==================== DATA COLLECTION STATS ====================")
# Nb of papers with at least one detected GPU
papers_gpu_count = df_papers.groupby("paper_ID").count()
papers_gpu_count_groups = papers_gpu_count["device"].value_counts()
total_nb_papers = len(df_devices_per_paper)
papers_with_gpu_detected = np.sum(papers_gpu_count_groups)
print(f"Detected GPU in {papers_with_gpu_detected} papers out of {total_nb_papers}: {100 * papers_with_gpu_detected / total_nb_papers:.2f}%")

print("GPUs per paper:")
for idx, count in papers_gpu_count_groups.items():
    print(f"{idx} GPU: {count:>10} paper(s) {100 * count / papers_gpu_count_groups.sum():.2f}%")

print("==================== GPU USED IN PAPERS ====================")
nb_of_gpu_cite = df_papers.groupby("device").count().sort_values(by="paper_ID", ascending=False)
for idx, row in nb_of_gpu_cite[:10].iterrows():
    print(f"{idx:<30}: {row['paper_ID']} papers.")

print("By year:")
for year in range(year_start, year_end + 1):
    print(f" - In {year} the top 5 GPUs are:")
    df_papers_year = df_papers[df_papers["year"] == year]
    nb_of_gpu_cited_that_year = df_papers_year.groupby("device").count().sort_values(by="paper_ID", ascending=False)
    # print(f"Most cited GPU in {year}: {nb_of_gpu_cited_that_year.loc[0, ""]}")
    # print(nb_of_gpu_cited_that_year)
    for idx, row in nb_of_gpu_cited_that_year[:5].iterrows():
        print(f"{idx:<30}: {row['paper_ID']} papers.")


print("==================== PAPERS VS USERS ====================")
# map the device names from TPU name to benchmark name
df_paper_relative_perf = df_papers.copy()
mapping_dict = dict(df_papers_to_benchmark.values)
df_paper_relative_perf["benchmark device name"] = df_paper_relative_perf["device"].map(lambda x : mapping_dict[x])
# df_paper_relative_perf["year"] = df_paper_relative_perf["paper_ID"].map(lambda x :  x.split("/")[0])

cumulative_users_ratio = df_usage_and_perf.copy()
# we assume that the rows are sorted by performance already
years = np.arange(year_start, year_end + 1).astype(str).tolist()
years_cumulative_cols = [f"{year}-cumulative" for year in years]
cumulative_users_ratio[years_cumulative_cols] = df_usage_and_perf[years].cumsum()
df_papers_vs_users = pd.merge(df_paper_relative_perf, cumulative_users_ratio, left_on="benchmark device name", right_on="Device Name", how='left')

# for each paper/device, keep only the device/user/perf value for the corresponding year
years_per_paper = df_paper_relative_perf["year"].to_numpy().astype(int) - year_start
df_per_paper_cumulative = df_papers_vs_users[years_cumulative_cols].values[np.arange(len(years_per_paper)), years_per_paper]
df_paper_relative_perf["relative perf"] = df_per_paper_cumulative
max_perf_grouped_by_paper = df_paper_relative_perf.groupby("paper_ID")["relative perf"].max()
# print(max_perf_grouped_by_paper)
nb_papers_above_80 = np.count_nonzero(max_perf_grouped_by_paper > 80)
print(f"{nb_papers_above_80} papers ({100* nb_papers_above_80 / papers_with_gpu_detected:.2f}% of papers with a known GPU) use a GPU that is more powerful than 80% of the user-base at publication time")

print("==================== SPECIFIC GPU VS USERS ====================")
nvidia_1080_2023_cum_score = cumulative_users_ratio[cumulative_users_ratio["Device Name"] == "NVIDIA GeForce GTX 1080 Ti"]['2024-cumulative']
nvidia_1080_raw_score = df_usage_and_perf[df_usage_and_perf["Device Name"] == "NVIDIA GeForce GTX 1080 Ti"]['2024']
print(f"The proportion of users with a GPU as good or better than the 1080 in 2024 is: {100 - nvidia_1080_2023_cum_score + nvidia_1080_raw_score}")