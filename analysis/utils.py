import pandas as pd
import numpy as np



def prepare_usage_and_performance_data(
        df_steam,
        df_benchmark,
        year_start,
        year_end
    ):

    # Merge the steam (usage) table and the benchmark performance table
    # We keep a union of the devices
    df_usage_and_perf = pd.merge(df_benchmark, df_steam, how='outer', left_on='Device Name', right_on='GPU')
    df_usage_and_perf.fillna({ "Device Name": df_usage_and_perf["GPU"] }, inplace=True)
    # Select columns corresponding to the years we want
    years = np.arange(year_start, year_end + 1).astype(str).tolist()

    columns = ["Device Name", "Median Score"] + years
    df_usage_and_perf = df_usage_and_perf[columns]

    # Assume that devices that have no value for steam usage have 0% of users
    df_usage_and_perf[years] = df_usage_and_perf[years].fillna(0)


    mystery_gpus_filter = np.logical_or(
        df_usage_and_perf["Device Name"].isin(["Other"]),
        df_usage_and_perf["Median Score"].isna()
    )

    # Compute the aggregate of users corresponding to that
    aggregate_users_mystery_gpus = df_usage_and_perf[mystery_gpus_filter][years].sum(axis=0)

    # Remove these lines
    df_usage_and_perf = df_usage_and_perf[~mystery_gpus_filter]

    # Add a line for the mystery GPUs
    # Define columns to add with an array of values for the new row(s)    
    data = {
        "Device Name": ["Unknown"], 
        "Median Score":   [0], 
    }

    for year in years:
        data[year] = [aggregate_users_mystery_gpus[year]]
        
    # We need a new DataFrame with the new contents
    df_new_rows = pd.DataFrame(data)

    # Call Pandas.concat to create a new DataFrame that includes the mystery gpus
    df_usage_and_perf = pd.concat([df_usage_and_perf, df_new_rows])

    df_usage_and_perf = df_usage_and_perf.sort_values("Median Score", ascending=True, na_position='first')

    return  df_usage_and_perf
