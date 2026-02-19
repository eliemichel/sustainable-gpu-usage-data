import json
import sqlite3
from pprint import pprint
from collections import Counter, defaultdict as ddict
import os
import pickle
import numpy as np
import matplotlib.pyplot as plt
import urllib.request
from pathlib import Path
import glob
import csv

BLENDER_OPENDATA_URL = 'https://opendata.blender.org/snapshots/opendata-latest.zip'
print(BLENDER_OPENDATA_URL)

def find_or_download_blender_opendata():
    paths = glob.glob('../data/blender-opendata/*.jsonl')
    if len(paths) == 0:
        # zip_path = Path('../data/blender-opendata/opendata-latest.zip')
        # zip_path.parent.mkdir(parents=True, exist_ok=True)
        # with urllib.request.urlopen(BLENDER_OPENDATA_URL) as f, open(zip_path, 'wb') as output:
            # output.write(f.read())
        raise Exception('TODO: Download file, unzip it')
    elif len(paths) == 1:
        return paths[0]
    elif len(paths) > 1:
        print('Error: found multiple blender opendata files: ' + ','.join(str(p) for p in paths))
        return paths[0]

BLENDER_OPENDATA_JSON_PATH = find_or_download_blender_opendata()
print(BLENDER_OPENDATA_JSON_PATH)

def get_all_benchmarks():
    schema_versions = Counter()
    benchmarks = []
    with open(BLENDER_OPENDATA_JSON_PATH) as f:
        for line_idx, line in enumerate(f):
            doc = json.loads(line)
            schema_version = [None, 'v1', 'v2', 'v3', 'v4'].index(doc['schema_version'])
            assert(schema_version >= 1 and schema_version <= 4)

            schema_versions[schema_version] += 1
            data = [doc['data']] if (schema_version <= 2) else doc['data']

            if schema_version == 4:
                benchmarks.extend(data)
    pprint(schema_versions)

    return benchmarks

benchmarks_filename = 'benchmarks.pickle'
try:
    print(f'Loading {benchmarks_filename}...')
    with open(benchmarks_filename, 'rb') as f:
        benchmarks = pickle.load(f)
    print(f'Loaded {benchmarks_filename}')
except:
    print(f'Writing {benchmarks_filename}...')
    benchmarks = get_all_benchmarks()
    with open(benchmarks_filename, 'wb') as f:
        pickle.dump(benchmarks, f)
    print(f'Wrote {benchmarks_filename}')

blender_versions = Counter()
device_types = Counter()
gpus = Counter()
device_counts = Counter()
scenes = Counter()

for b in benchmarks:
    blender_versions[b['blender_version']['version']] += 1

    compute_devices = b['device_info']['compute_devices']
    device_counts[len(compute_devices)] += 1
    scenes[(b['scene']['checksum'], b['scene']['label'])] += 1
    if len(compute_devices) == 1:
        device = compute_devices[0]
        device_types[device['type']] += 1
        if device['type'] != 'CPU':
            gpus[device['name']] += 1

device_scores = ddict(lambda: ddict(list))
for b in benchmarks:
    device = b['device_info']['compute_devices'][0]['name'] # , b['device_info']['compute_devices'][0]['type'])
    date = np.datetime64(b['blender_version']['build_commit_date'])
    blender_version = b['blender_version']['version']
    scene = b['scene']['label']
    device_scores[device][(date, blender_version, scene)].append(b['stats']['samples_per_minute'])

pprint(blender_versions)
pprint(device_types)
pprint(gpus)
pprint(device_counts)
pprint(scenes)
pprint(benchmarks[0])

def plot_top_n_performance_vs_date(n):
    for (_, scene_label) in scenes:
        fig, ax = plt.subplots()
        fig.suptitle(scene_label)
        for gpu, _ in gpus.most_common(n):
            data = np.array([(date, np.median(scores)) for ((date, version, scene), scores) in device_scores[gpu].items() if scene == scene_label])
            data = np.sort(data, axis=0)
            ax.plot(*data.T, label=str(gpu))
        ax.legend()
        ax.grid()

# returns a list of (device, normalized_score, normalized_score_std_dev) tuples
def compute_normalized_scores():
    devices_and_scores = []
    reference_device = 'NVIDIA GeForce GTX 1080 Ti' # 'OPTIX'
    for device in device_scores:
        normalized_scores = []
        for (date, blender_version, scene) in device_scores[device]:
            scores = device_scores[device][(date, blender_version, scene)]
            reference_scores = device_scores[reference_device][(date, blender_version, scene)]
            normalized_score = np.mean(scores) / np.mean(reference_scores)
            normalized_scores.append(normalized_score)
        devices_and_scores.append((device, np.mean(normalized_scores), np.std(normalized_scores)))
    devices_and_scores.sort(key=lambda x: x[1])

    return devices_and_scores

normalized_scores = compute_normalized_scores()
with open('../versionned-data/device-database/normalized-blender-scores.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=',')
    writer.writerow(['DeviceName', 'ScoreMean', 'ScoreStdVar'])
    for device, score_mean, score_std in normalized_scores:
        writer.writerow([device, str(score_mean), str(score_std)])
