Analysis of GPU usage in SIGGRAPH papers
========================================

This repository contains the datasets and source code of the SIGGRAPH 2025 Talk **"Towards a sustainable use of GPUs in Graphics Research"**.

We surveyed *888* SIGGRAPH papers from 2018-2024 and gathered author-reported GPU models. By contextualizing the hardware reported in papers with available data of consumers' hardware, we demonstrate that graphics research is consistently developed and tested on new high-end devices that do not reflect the state of the consumer-level market.

[🌐 Project Page](https://eliemichel.github.io/sustainable-gpu-usage/)

[📕 ACM Link](https://dl.acm.org/doi/full/10.1145/3721239.3734084)

We collected data on GPU devices from four sources:
* SIGGRAPH Research papers from 2018-2024
* GPU device names from [TechPowerUp](https://www.techpowerup.com/gpu-specs/)
* Performance data from [Blender Open data benchmark](https://opendata.blender.org/)
* Consumer-level GPU usage from [Steam Hardware Survey](https://store.steampowered.com/hwsurvey/Steam-Hardware-Software-Survey-Welcome-to-Steam)

Below we explain our data collection process, how to access it, and how to use it to generate the result figure. Code was written as a set of python scripts with various dependencies that we describe below.

## Dataset

All data that we collected with detailed description are available in [`data`](data).

## Data collection process

This repository already provides the result of the data collection process, but you may follow these instructions if you want to reproduce our results, adapt our process to other use cases, or update to newest papers.

### Requirements

The scripts in this repository have a few dependencies, that are listed using the standard `requirements.txt` file. Install them as follows:

```bash
# (optional: run this in a Python virtualenv)
pip install -r requirements.txt
```

> [!NOTE]  
> The file `requirements.txt` is slightly commented, in case you are only interested in the dependencies of one of the scripts. The process was tested with **Python 3.11**.

### Collecting papers

> [!TIP]  
> For quick experimentation, we provide PDFs in `data/raw/papers_sample`.

In the context of our research project, we had academic access to the ACM Digital Library, which we used as a convenient way to collect all papers. If you have ACM DL access, or any other way to download papers in batch, you can directly put them in the directory `data/raw/papers`.

For convenience, we provide a script to help scrape papers from various public available sources in the following script:

```bash
# This is a scraping script, which takes a while to run (maybe 1h)!
# And it downloads ~21GB of data.
python download_papers.py

# Alternatively, use the sample papers
cp -r data/raw/papers_sample data/raw/papers
```

> [!TIP]  
> Most script support calling them with the `--help` argument to get some extra options.

When using the download script:

1. The list of paper's titles are retrieved from [Ke-Sen Huang's amazing website](https://kesen.realtimerendering.com/) (thank you Ke-Sen).
2. For each title, we try to find an openly available PDF. For now, this only relies on [Semantic Scholar](https://www.semanticscholar.org/), but we are planning on also querying Google Scholar because many papers are missing from semantic scholar's title search (especially the ones containing a colon (:) character).
3. Papers are stored in `data/raw/papers`, with each PDF named after the Semantic Scholar paper id.
4. There is also a `data/raw/papers/metadata.json` file that summarizes the list of papers and how the retrieval went.

> [!NOTE]  
> All scraping scripts use the [requests-cache](https://requests-cache.readthedocs.io/en/stable/) module so that once ran a first time, we can reproduce their result without querying again any server. Cached websites are stored in `data/cache/*.sqlite` files.

### Collecting GPU device names

We scraped the device database from [TechPowerUp](https://www.techpowerup.com). You **do not need** to run `download_cpu_database.py` and `download_cpu_database.py` yourself as their result is available in `data/raw/devices`.

> [!WARNING]  
> If you do run these anyways, note that you'll probably need to restart the script multiple time because of 429 errors, and/or go to techpowerup.com to solve captchas manually from time to time.


### Automatic GPU names extraction

We run a script to parse papers text and extract all occurrences of a GPU/CPU device name.

```bash
python extract_device_names_from_papers.py --fuzz-score-cutoff 70
```

This script does the following things:

* We read each PDF's text with PDFmium
* From our list of GPU names (`data/raw/device/all-gpus.csv`) we split each device names into tokens.
* We use [acora](https://pypi.org/project/acora/) to match any of these tokens in PDFs.
* We use [rapidfuzz](https://pypi.org/project/RapidFuzz/) to fuzzily recognize the device name from the extracted window. Fuzzy macthing does not because it really expects the extracted window to only include the device name and nothing else. We lowered with the fuzzy score cutoff parameter to make sure we don't miss any matches.
* We use [fuzzysearch](https://pypi.org/project/fuzzysearch/) to estimate the offset at which the match starts in the text window.

> [!NOTE]  
> The script `test_DeviceNameMatcher.py` can be used to gain an idea of how the `DeviceNameMatcher` works.

### Manual GPU names correction

The previous step detected potential matches using a conservative automatic string matching algorithm, in this step we then manually process this to filter out false positives, correct erroneous assignments, and validate each match.

This is done in two steps:

First, we run `validate_search_results_manually.py` to label matches from `data/processed/automatic/device-search-results.json` as either correct (true positive) / erroneous (there is a GPU name in the window but the match is wrong) / missing (no GPU name in the window)

```bash
# You may use default values instead of providing explicit command line arguments
python validate_search_results_manually.py --input [matches json file] --start [start paper idx] --end [end paper idx]
```

Example of interactive session:

```
INFO:__main__:Loading json data from '/Users/emichel/src/GraphicsPapersStats/data/processed/automatic/device-search-results.json'...
===========================================
Overall Progress: 0/888
Current Progress: 0/887
Paper 0: b'2018/Aberman et al. - 2018 - Neural best-buddies sparse cross-domain correspondence'
Match 1/1
Score:                      73.684211
Matched device name:        Matrox QID
Text window matched:        'max\r\nq ∈Q\r\nd(p,q, P,Q). (2)\r\nNext, w'
Correct? ([Y]es, [E]rror, [N]one, empty defaults to None)> N
--------------------------------
INFO:__main__:Saving json data to '/Users/emichel/src/GraphicsPapersStats/data/processed/manual/device-search-results_annotated.json'...
===========================================
Overall Progress: 1/888
Current Progress: 1/887
Paper 1: b'2018/Akbay et al. - 2018 - An extended partitioned method for conservative solid-fluid coupling'
Match 1/13
Score:                      100.000000
Matched device name:        AMD Opteron 6272
Text window matched:        '\n16 nodes, each comprised of 2 AMD Opteron 6272 CPUs totaling\r\n32 cores, 64GB '
Correct? ([Y]es, [E]rror, [N]one, empty defaults to None)> Y
--------------------------------
Match 2/13
Score:                      80.701754
Matched device name:        ATI VGA Improved Performance
Text window matched:        'n\r\nshown to improve performance of'
Correct? ([Y]es, [E]rror, [N]one, empty defaults to None)> N
```

The script runs through all GPU device name matches from the previous step (`data/processed/automatic/device-search-results.json`) and for each match, it asks the user to check the match and assign a label to it (Y: true positive, E: erroneous, N: no device in window). This writes the labels to `data/processed/manual/device-search-results_annotated.json`.

Second, we run `correct_device_names_manually.py`, to correct all `E` erroneous matches found in the previous step.

```bash
python correct_device_names_manually.py
```

Example of interactive session:

```
INFO:__main__:Loading json data from '/Users/emichel/src/GraphicsPapersStats/data/processed/manual/device-search-results_annotated.json'...
===========================================
Current Progress: 0/396
Paper 0: 2018/Alderighi et al. - 2018 - Metamolds computational design of silicone molds
Match 1/6
Score:                      83.333333
Matched device name:        Intel i740
Text window matched:        ' between 2 and 4 minutes on an Intel I7-6700K 4GHz machine;\r\ncomputing mo'
Nb of devices to input (defaults to 0) >1
1
Device 1/1
[1] for GPU, [2] for CPU>2
Search string for model name (return empty to pass) >Intel I7-6700K
Found 0 matches for cpus.
No matches. Entry status? [1] AMBIGUOUS, [2] NOT IN DB>2
--------------------------------
INFO:__main__:Saving json data to '/Users/emichel/src/GraphicsPapersStats/data/processed/manual/device-search-results_manual_labels.json'...
===========================================
```

For each of the matches marked as erroneous, the script shows the text window to the user and gives them the option to search in the whole GPU database to find the correct device. This writes the final device labels to `data/processed/manual/device-search-results_manual_labels.json`.

Finally, we harmonize GPU names across the whole labelled dataset, in order to resolve small discrepancies between names: for instance, for these two GPUs: `NVIDIA GeForce RTX 2080 Ti 12 GB` and `NVIDIA GeForce RTX 2080 Ti` we decided to consider them equivalent for the purpose of our analysis.
We did that matching process manually by building a table of all GPUs that had at least one occurrence in papers (using the script `aggregate_similar_device_names.py`), and mapping them to an arbitrary "base" model (e.g., assigning `NVIDIA GeForce RTX 2080 Ti` as a common final label for both models mentioned earlier). The resulting table was written to `data/aggregated/paper_gpus_name_aggregation.csv`.

## Steam usage data collection

We use [Scrapy](https://docs.scrapy.org/en/latest/index.html) to scrape the steam GPU stats through the Wayback Machine.
Original code for the Scrapy middleware (`steam_stats_scraper/wayback_machine_middleware.py`) is from https://github.com/sangaline/wayback-machine-scraper with a fix from this PR https://github.com/sangaline/scrapy-wayback-machine/pull/9 . The scraper code is in `steam_stats_scraper/spiders/spider.py`.

```
scrapy crawl steam_stats -o snapshots-test.jl
```

### Blender benchmark collection

We downloaded the latest available data at the time from [Blender Open data benchmark](https://opendata.blender.org/), with this specific [query](https://opendata.blender.org/benchmarks/query/?group_by=device_name). Is it available directly in `raw/benchmark/blender-benchmark-2025.csv`.

## Building correspondences between data sources

Our different data sources (papers, benchmark, users) all talk about GPUs: the goal of our analysis is to aggregate these data sources by putting them into correspondence with one another, in order to establish comparisons.

The main challenge in doing so is that GPU names are pretty ambiguous keys to merge datasets on, so we need to gracefully resolve near-matches. For instance the GPU named `NVIDIA TITAN X Pascal` in the Tech Power Up list and the one named `NVIDIA TITAN X (Pascal)` in the Blender Benchmark are ostensibly the same device. We do that matching process manually using the CLI script `match_papers_to_users.py`. The result of that mapping/merging of keys is written to `data/aggregated/papers_gpu_to_benchmark_gpus.csv`, and is used throughout the analysis and data visualization process.



## Example scripts for analysis

Scripts that analyze the result of the extractions are available in the `analysis` directory.

For instance, here is how one can generate the main result figure:

```bash
python analysis/papers_with_users_bar_chart.py
```

The script `analysis/print_stats.py` displays statistics that we used in the abstract and presentation, eg:

```
==================== DATA COLLECTION STATS ====================
Detected GPU in 383 papers out of 888: 43.13%
GPUs per paper:
1 GPU:        312 paper(s) 81.46%
2 GPU:         60 paper(s) 15.67%
3 GPU:          7 paper(s) 1.83%
4 GPU:          3 paper(s) 0.78%
5 GPU:          1 paper(s) 0.26%
...
```

Some other scripts are available in the `analysis` directory.

