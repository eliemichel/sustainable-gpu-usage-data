import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Rectangle
from datetime import datetime as dt
import os
import random
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from matplotlib_bar_link import make_bar_link_patch

def prepare_usage_and_performance_data(
        df_steam,
        df_benchmark,
        year_start,
        year_end,
        keep_mystery_gpus=True
    ):

    # Merge the steam (usage) table and the benchmark performance table
    # We keep a union of the devices
    df_usage_and_perf = pd.merge(df_benchmark, df_steam, how='outer', left_on='DeviceName', right_on='GPU')
    df_usage_and_perf["DeviceName"].fillna(df_usage_and_perf["GPU"], inplace=True)
    # Select columns corresponding to the years we want
    years = np.arange(year_start, year_end + 1).astype(str).tolist()

    columns = ["DeviceName", "ScoreMean"] + years
    df_usage_and_perf = df_usage_and_perf[columns]

    # Assume that devices that have no value for steam usage have 0% of users
    df_usage_and_perf[years] = df_usage_and_perf[years].fillna(0)

    mystery_gpus_filter = np.logical_or(
        df_usage_and_perf["DeviceName"].isin(["Other"]),
        df_usage_and_perf["ScoreMean"].isna()
    )

    # Compute the aggregate of users corresponding to that
    aggregate_users_mystery_gpus = df_usage_and_perf[mystery_gpus_filter][years].sum(axis=0)

    # Remove these lines
    df_usage_and_perf = df_usage_and_perf[~mystery_gpus_filter]

    if keep_mystery_gpus:
        # Add a line for the mystery GPUs
        # Define columns to add with an array of values for the new row(s)
        data = {
            "DeviceName": ["Unknown"],
            "ScoreMean":   [-1000],
        }

        for year in years:
            data[year] = [aggregate_users_mystery_gpus[year]]

        # We need a new DataFrame with the new contents
        df_new_rows = pd.DataFrame(data)

        # Call Pandas.concat to create a new DataFrame that includes the mystery gpus
        df_usage_and_perf = pd.concat([df_usage_and_perf, df_new_rows])

    df_usage_and_perf = df_usage_and_perf.sort_values("ScoreMean", ascending=True, na_position='first')

    return  df_usage_and_perf


df_steam = pd.read_csv(os.path.join("..", "versionned-data", "device-database", "steam-gpu-users-per-year.csv"), sep=";")
df_benchmark = pd.read_csv(os.path.join("..", "versionned-data", "device-database", "blender-benchmark-2025.csv"))
df_normalized_scores = pd.read_csv(os.path.join("..", "versionned-data", "device-database", "normalized-blender-scores.csv"))

df_papers = pd.read_csv(os.path.join("..", "versionned-data", "aggregate-data", "gpus_papers.csv"))
df_papers_to_benchmark = pd.read_csv(os.path.join("..", "versionned-data", "aggregate-data", "papers_gpu_to_benchmark_gpus.csv"))

df_devices_per_paper = pd.read_csv(os.path.join("..", "versionned-data", "aggregate-data", "devices_per_paper.csv"))

# year_start = 2018
# year_end = 2024

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
df_papers_scores = df_papers.merge(df_normalized_scores, left_on="Benchmark Device Name", right_on="DeviceName", how='left')

df_papers_scores = df_papers_scores.set_index("paper_ID")
df_papers_scores = df_papers_scores.sort_values("ScoreMean", ascending=True, na_position='first')
# df_papers_scores = df_papers_scores.drop(columns="Number of Benchmarks")
print(df_papers_scores[:10])
print(df_papers_scores["year"])
# TODO: export this table as csv to let others inspect it (pretty interesting)
df_papers_scores.to_csv(os.path.join("..", "versionned-data", "aggregate-data", "papers_gpu_benchmarked.csv"))

# df_papers_scores.hist(column="ScoreMean", bins=50)

def weighted_bxpstats(values, weights, whis=1.5):
    i = np.argsort(values)
    c = np.cumsum(weights[i])

    q1, med, q3 = values[i[np.searchsorted(c, np.array([.25, .5, .75]) * c[-1])]]
    iqr = q3 - q1
    whislo_val = q1 - whis * iqr
    whishi_val = q3 + whis * iqr

    values_sorted = values[i]
    # From https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.boxplot.html:
    # the lower whisker is at the lowest datum above Q1 - whis*(Q3-Q1), and the upper whisker at the highest datum below Q3 + whis*(Q3-Q1)
    whislo = values_sorted[np.searchsorted(values_sorted, whislo_val)]
    whishi = values_sorted[np.searchsorted(values_sorted, whishi_val)]

    return {
        'med': med,
        'q1': q1,
        'q3': q3,
        'whislo': whislo,
        'whishi': whishi,
    }

def plot_steam_vs_papers_box(ax, year_start, year_end, offset=.1, width=.15):
    for i, year_focus in enumerate(range(year_start, year_end + 1)):
        df_papers_scores_year = df_papers_scores[df_papers_scores["year"] == year_focus]
        paper_scores = np.array(df_papers_scores_year['ScoreMean'])
        paper_scores = paper_scores[~np.isnan(paper_scores)]
        paper_bplot = ax.boxplot(paper_scores, positions=[year_focus - offset], widths=[width], patch_artist=True)
        for paper_patch in paper_bplot['boxes']:
            paper_patch.set_facecolor('blue')
            paper_patch.set_alpha(.3)

        df_steam_and_perf = prepare_usage_and_performance_data(df_steam, df_normalized_scores, year_start=year_focus, year_end=year_focus, keep_mystery_gpus=False)
        # Normalize usage fraction (expressed in %)
        df_steam_and_perf[str(year_focus)] /= df_steam_and_perf[str(year_focus)].sum()
        steam_bxpstats = weighted_bxpstats(np.array(df_steam_and_perf['ScoreMean']), np.array(df_steam_and_perf[str(year_focus)]))
        steam_bplot = ax.bxp([steam_bxpstats], showfliers=False, positions=[year_focus + offset], widths=[width], patch_artist=True)
        for steam_patch in steam_bplot['boxes']:
            steam_patch.set_facecolor('orange')
            steam_patch.set_alpha(.3)

    ax.legend(handles=[paper_patch, steam_patch], labels=['papers', 'steam users'])

def plot_steam_vs_papers_histogram(year_focus):
    fig, ax = plt.subplots()

    bin_count = 20
    hist_range = (0., 14.)

    df_papers_scores_year = df_papers_scores[df_papers_scores["year"] == year_focus]
    df_papers_scores_year = df_papers_scores_year.sort_values("ScoreMean", ascending=True, na_position='first')
    papers_counts, papers_bins = np.histogram(df_papers_scores_year['ScoreMean'], bins=bin_count, range=hist_range)
    ax.stairs(papers_counts, papers_bins, fill=True, color='blue', alpha=.5, label=f'papers ({year_focus})')
    ax.legend()

    ax = ax.twinx()
    df_steam_and_perf = prepare_usage_and_performance_data(df_steam, df_normalized_scores, year_start=year_focus, year_end=year_focus)

    # Normalize usage fraction (expressed in %)
    df_steam_and_perf[str(year_focus)] /= df_steam_and_perf[str(year_focus)].sum()

    steam_counts, steam_bins = np.histogram(df_steam_and_perf['ScoreMean'], bins=bin_count, range=hist_range, weights=df_steam_and_perf[str(year_focus)])
    ax.stairs(steam_counts, steam_bins, fill=True, color='orange', alpha=.5, label=f'steam user base ({year_focus})')
    ax.legend()

    return fig, ax

fig, ax = plt.subplots()
year_start = 2018
year_end = 2024
plot_steam_vs_papers_box(ax, year_start, year_end)
ax.set_xticks(list(range(year_start, year_end + 1)), [str(year) for year in range(year_start, year_end + 1)])
ax.set_ylabel('Normalized score')
ax.set_xlabel('Year')
ax.grid(axis='y')
ax.set_title("Performance score of GPUs\nin SIGGRAPH papers vs. Steam users' machines")

fig.set_size_inches((16, 9))
fig.tight_layout()
fig.savefig('papers_vs_steam.svg')
fig.savefig('papers_vs_steam.png')

# legend_elements = [Line2D([0], [0], color='b', lw=4, label='Line'),
#                    Line2D([0], [0], marker='o', color='w', label='Scatter',
#                           markerfacecolor='g', markersize=15),
#                    Patch(facecolor='orange', edgecolor='r',
#                          label='Color Patch')]

plt.show()
