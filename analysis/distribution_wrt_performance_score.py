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

# year_start = 2018
# year_end = 2024

year_focus = 2024

fig, ax = plt.subplots()

# Plot a histogram
# - x-axis: benchmark score (bins)
# - y-axis: count of paper GPU that fall in that score bin

# Create a table:
# - index: paper_ID
# - column: benchmark score

# Associate a benchmark score to each gpu from paper
mapping_dict = dict(df_papers_to_benchmark.values)
df_papers["Benchmark Device Name"] = df_papers["device"].map(lambda x : mapping_dict[x])
df_papers["year"] = df_papers["paper_ID"].map(lambda x :  int(x.split("/")[0]))
df_papers_scores = df_papers.merge(df_benchmark, left_on="Benchmark Device Name", right_on="Device Name", how='left')

df_papers_scores = df_papers_scores.set_index("paper_ID")
df_papers_scores = df_papers_scores.sort_values("Median Score", ascending=True, na_position='first')
# df_papers_scores = df_papers_scores.drop(columns="Number of Benchmarks")
print(df_papers_scores[:10])
print(df_papers_scores["year"])
# TODO: export this table as csv to let others inspect it (pretty interesting)
df_papers_scores.to_csv(os.path.join("..", "versionned-data", "aggregate-data", "papers_gpu_benchmarked.csv"))

# df_papers_scores.hist(column="Median Score", bins=50)

# Look at a specific year
df_papers_scores_year = df_papers_scores[df_papers_scores["year"] == year_focus]
df_papers_scores_year = df_papers_scores_year.sort_values("Median Score", ascending=True, na_position='first')
df_papers_scores_year.hist(column="Median Score", bins=50, ax=ax)
print(df_papers_scores_year[:10])

# plt.show()


# Create a table:
# - index: benchmark score
# - column: usage ratio for that year
df_steam_and_perf = prepare_usage_and_performance_data(df_steam, df_benchmark, year_start=2024, year_end=2024)
print(df_steam_and_perf)
df_steam_and_perf.plot.line(x="Median Score", y="2024", ax=ax)

plt.show()