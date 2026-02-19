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

year_start = 2018
year_end = 2024
users_ratio_threshold = 0.2



def plot_usage_chart(
        df_usage_and_perf,
        year_start, 
        year_end, 
        ax,
        emphasize_gpus = [],
        users_ratio_threshold=0):
    
    years = np.arange(year_start, year_end + 1).astype(str).tolist()

    
    df_usage_and_perf = df_usage_and_perf.copy()
    
    # Remove the GPU names for rows where the GPU never reaches x% of users (to simplify the legend and colors)
    unpopular_gpus = np.all(df_usage_and_perf[years] < users_ratio_threshold, axis=1)

    df_usage_and_perf.loc[unpopular_gpus, "Device Name"] = "ignore"


    # Transpose to have the year as index
    df_per_year = df_usage_and_perf.set_index("Device Name")[years].T


    # Paint the gpus to emphasize in bright colors
    unique_gpus = list(dict.fromkeys(df_per_year.columns))

    # cmap = matplotlib.cm.get_cmap('tab10')
    # colors_dict = {}
    # for gpu_name in unique_gpus:
    #     colors_dict[gpu_name] = (1, 1, 1, 1)

    # for idx, gpu_name in enumerate(emphasize_gpus):
    #     colors_dict[gpu_name] = cmap(idx / len(emphasize_gpus))

    cmap = plt.get_cmap('plasma')
    colors_dict = {'Unknown': 'dimgrey', 'ignore': 'white'}
    for idx, gpu_name in enumerate(unique_gpus):
        if gpu_name == 'ignore' or gpu_name == 'Unknown':
            continue
        colors_dict[gpu_name] = cmap(idx / len(unique_gpus))


    # Plot stacked bar chart
    df_per_year.plot.bar(stacked=True, edgecolor="white", linewidth=0.5, color=colors_dict, ax=ax)
    
    width = 0.5


    # Plot hatched zone for the mystery GPUs
    for year_idx, year in enumerate(years):
        ax.add_patch(Rectangle(
            (year_idx - 0.5 * width, 0),
            width,
            df_per_year.iloc[year_idx, 0],
            fill=True,
            hatch ='///',
            linewidth=0.5,
            color='dimgrey',
            ec='white'
            ))

    # draw the flux curves
    cumulative_users_per_gpu = df_usage_and_perf[["Device Name"] + years].copy()
    cumulative_users_per_gpu[years] = df_usage_and_perf[years].cumsum()

    gpu_to_legend = []
    for gpu_name in emphasize_gpus:
        if df_usage_and_perf["Device Name"].isin([gpu_name]).any():
            # Check if the gpu has at least 5% of users at any year
            gpu_max_usage = df_usage_and_perf[df_usage_and_perf["Device Name"].isin([gpu_name])][years].max(axis=1).item()
            # Don't plot GPUs with almost no users
            if gpu_max_usage > 0.8:
                gpu_to_legend.append(gpu_name)

    # Add the most popular GPU (biggest slice)
    # most_used_gpu_idx = df_usage_and_perf[years].sum(axis=1)[1:].argmax()
    # most_used_gpu = df_usage_and_perf.iloc[1 + most_used_gpu_idx]["Device Name"]

    for gpu_name in gpu_to_legend:
        color = colors_dict[gpu_name]
        gpu_row_idx = np.flatnonzero(cumulative_users_per_gpu["Device Name"].isin([gpu_name]))[0] # it is guaranteed that there is one and only one match by construction
        for year_idx, year in enumerate(years):
            if year_idx + 1 > len(years) - 1:
                continue
            ax.add_patch(make_bar_link_patch(
                start_bar_x=year_idx + width * 0.5,
                start_bar_y_range=(
                    cumulative_users_per_gpu.iloc[gpu_row_idx - 1][year],
                    cumulative_users_per_gpu.iloc[gpu_row_idx][year]),
                end_bar_x=year_idx + 1 - width * 0.5,
                end_bar_y_range=(
                    cumulative_users_per_gpu.iloc[gpu_row_idx - 1][years[year_idx + 1]],
                    cumulative_users_per_gpu.iloc[gpu_row_idx][years[year_idx + 1]]
                    ),
                color=color,
                # ec='white',
                # linewidth=0.5
            ))

    # Legend
    h, l = ax.get_legend_handles_labels()
    final_h = []
    final_l = []
    # set_labels = set()
    # set_labels.add("ignore") # ignore this label
    for handle, label in zip(h, l):
        if label in gpu_to_legend:
            final_h.append(handle)
            final_l.append(label)
            # set_labels.add(label)

    # unique_h.reverse()
    # unique_l.reverse()

    ax.legend(final_h, final_l, loc='upper center', bbox_to_anchor=(1.1, 1.05))

    # box = ax.get_position()
    # ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

def plot_paper_gpus(
        df_papers,
        df_usage_and_perf,
        year_start,
        year_end,
        ax
    ):

    years = np.arange(year_start, year_end + 1).astype(str).tolist()

    # Plot paper GPU as dots
    df_paper_relative_perf = df_papers.copy()


    # For each gpu and year, compute the y-coordinates
    cumulative_users_ratio = df_usage_and_perf.copy()
    # we assume that the rows are sorted by performance already
    years_cumulative_cols = [f"{year}-cumulative" for year in years]
    cumulative_users_ratio[years_cumulative_cols] = df_usage_and_perf[years].cumsum() - df_usage_and_perf[years] * 0.5

    # map the device names from TPU name to benchmark name
    mapping_dict = dict(df_papers_to_benchmark.values)
    df_paper_relative_perf["benchmark device name"] = df_paper_relative_perf["device"].map(lambda x : mapping_dict[x])
    # the year will serve as the x-axis
    df_paper_relative_perf["year"] = df_paper_relative_perf["paper_ID"].map(lambda x :  x.split("/")[0])
    df_paper_relative_perf["xs"] = df_paper_relative_perf["year"].map(lambda x: int(x) - year_start + random.uniform(-0.25, 0.25))
    # combine the paper/device table with the device/user/perf table
    df_cumulative_ratios_by_papers = pd.merge(df_paper_relative_perf, cumulative_users_ratio, left_on="benchmark device name", right_on="Device Name", how='left')

    # for each paper/device, keep only the device/user/perf value for the corresponding year
    years_per_paper = df_paper_relative_perf["year"].to_numpy().astype(int) - year_start
    df_per_paper_cumulative = df_cumulative_ratios_by_papers[years_cumulative_cols].values[np.arange(len(years_per_paper)), years_per_paper]
    df_paper_relative_perf["relative perf"] = df_per_paper_cumulative

    # find out what's the max user ratio for each device from papers
    # df_usage_ratio_by_papers = pd.merge(df_paper_relative_perf, df_usage_and_perf, left_on="benchmark device name", right_on="Device Name", how='left')
    # df_max_usage_ratio_by_papers = df_paper_relative_perf[years].fillna(0).max(axis=1)
    # max_usage_ratio_by_papers = df_cumulative_ratios_by_papers[years].max(axis=1)
    
    # find out which GPUs are above all users in terms of perf
    # unused_ultra_powerful_flag = np.logical_and(max_usage_ratio_by_papers <= 0, df_paper_relative_perf["relative perf"] >= 99)
    # print(df_paper_relative_perf[unused_ultra_powerful_flag])
    # df_paper_relative_perf.loc[unused_ultra_powerful_flag,"relative perf"] += 1
    # df_paper_relative_perf.loc[unused_ultra_powerful_flag,"relative perf"] += 5 * np.random.rand(len(df_paper_relative_perf.loc[unused_ultra_powerful_flag,"relative perf"]))
    
    # colors = max_usage_ratio_by_papers <= 0
    # print(df_cumulative_ratios_by_papers[colors].groupby("benchmark device name"))

    # Scatter plot
    df_paper_relative_perf.plot.scatter(x="xs", y="relative perf", ax=ax, zorder=10, c='white', ec="dimgrey")


    # ax.set_title("Usage ratio for GPUs, sorted by performance")
    ax.set_xlabel("Year")
    ax.set_ylabel("Ratio of users")
    # ax.get_legend().remove()


def main():
    fig, ax = plt.subplots()

    df_usage_and_perf = prepare_usage_and_performance_data(
        df_steam,
        df_benchmark,
        year_start,
        year_end
        )
    
    # Find the most used GPUs in papers
    gpu_cited_counts = df_papers.groupby("device").count().sort_values("paper_ID", ascending=False)
    selection_nb = 20
    most_cited_gpus = gpu_cited_counts.index[:selection_nb].tolist()
    print(gpu_cited_counts[:selection_nb])

    # Map them to the names used in the benchmark
    mapping_dict = dict(df_papers_to_benchmark.values)
    most_cited_gpus_benchmark_names = [mapping_dict[gpu_name] for gpu_name in most_cited_gpus]

    print(most_cited_gpus_benchmark_names)

    # Find their usage
    print(f"usage data for {selection_nb} most frequently cited gpus in papers:")
    print(df_usage_and_perf[df_usage_and_perf["Device Name"].isin(most_cited_gpus_benchmark_names)])
    
    plot_usage_chart(df_usage_and_perf, year_start, year_end, ax, emphasize_gpus=most_cited_gpus_benchmark_names, users_ratio_threshold=users_ratio_threshold)
    plot_paper_gpus(df_papers, df_usage_and_perf, year_start, year_end, ax)


    # plt.savefig("plot.svg")
    plt.show()


if __name__ == "__main__":
    main()