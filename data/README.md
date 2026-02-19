# Data
All of our data is available as a set of CSV files. Below we explain the content of each file, separated in three categories: **raw data** that was downloaded or scrapped as is, **processed data** on which we performed some transformation, and **aggregated data** that is the result of using multiple sources to find correlation later on. At the end of the day, processed and aggregated data were not all used for our analysis, but we release it in case it may be useful to someone.

## Raw data (`data/raw`)

### Papers sample (`data/raw/papers_sample`) 
Accessing SIGGRAPH papers is possible if you are an ACM member, or if the paper is available through open access. For reproducibility purposes, we provide sample papers to test our set of python scripts.

### Devices list  (`data/raw/devices`)
We collected GPU and CPU device names by scrapping the TechPowerUp database, resulting in two raw CSV files:
- `devices/all-cpus.csv`
- `devices/all-gpus.csv`

### Performance data  (`data/raw/benchmark`)
Performance data for comparing GPUs against each other comes from the [Blender Open data benchmark](https://opendata.blender.org/), resulting in a ranking file `blender-benchmark-2025.csv`.

### Device usage  (`data/raw/users`)
GPU device usage for consumers was scrapped from historical data from [Steam Hardware Survey](https://store.steampowered.com/hwsurvey/videocard/) through the [Web Archive](https://web.archive.org/), and is stored in `device-database/steam-gpu-users-per-year.csv`.


## Processed data (`data/processed`)

### Devices in papers - automatic labelling  (`data/processed/automatic`)
A starting point for the device labelling in papers was done using an automatic method, available in the script `extract_device_names_from_papers.py`. The result of this with a custom threshold `--fuzz-score-cutoff 70` is available in `device-search-results.json`. This is a first filter over the raw data for SIGGRAPH papers.

### Devices in papers - manual labelling  (`data/processed/manual`)
On top of automatic labelling, we perform a manual correction step to correct false positive or erroneous data. This resulted in two additional data files:
- `device-search-results_annotated.json`: result from running `validate_search_results_manually.py` to label matches from `device-search-results.json` as either correct (true positive) / erroneous (there is a GPU name in the window but the match is wrong) / missing (no GPU name in the window)
- `device-search-results_manual_labels.json`: result from running `correct_device_names_manually.py`, to search the whole device database in order to correct erroneous matches.


## Aggregated data (`data/aggregated`)
These aggregated tables were created by merging the other data tables (with GPU names as keys), and stored in this format for convenience of reuse in data analysis / data vis. Please see the main README and the associated scripts for more details on their construction.
- `gpus_papers.csv`: one row per GPU/paper match
- `devices_per_paper.csv`: one row per paper, with a list of its CPUs and GPUs found in text
- `paper_gpus_name_aggregation.csv`: manually built correspondence table mapping all GPU names found in at least one paper text, to a "base model". This helps resolve minor discrepancies between reporting/naming conventions.
- `papers_gpu_to_benchmark_gpus.csv`: correspondence table mapping GPU names as found in the Tech Power Up dataset, with the GPU names as found in the Blender benchmark dataset. Built manually by running the script `match_papers_to_users.py` and using the CLI program to assign correspondences.