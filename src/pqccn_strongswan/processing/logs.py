"""Process collected run statistics and merge them with per-log metrics."""

from __future__ import annotations

import yaml
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from IPython.display import display

from .log_conversion import Get_Ike_State_Stats, RunStats, get_Ike_State


def Log_stats(log_dir, plvl):
    print("Starting Log_stats")

    if log_dir == "":
        root = tk.Tk()
        root.withdraw()

        log_dir = filedialog.askdirectory(title="Select a directory")
        print(log_dir)
        root.destroy()

    logs = Path(log_dir)

    filesinfolder = sum(1 for x in logs.glob("*") if x.is_file())
    totalfiles = sum(1 for x in logs.rglob("*") if x.is_file())

    if plvl >= 1:
        print(("files in slected folder: " + str(filesinfolder)))
        print(("files in slected folder and subfolders: " + str(totalfiles)))

    if plvl >= 2:
        print("\n\nList of log files in selected folder and subfolders:")
        for x in logs.rglob("*.log"):
            print(x.name)

    newlog = RunStats(log_dir, "w")

    data = []
    data3 = []

    with open(newlog, encoding="utf-8") as f:
        for line in f:
            data.append(line)
            line = line.replace(":", ": ")
            line = line.replace(": /", ":/")
            x = line.replace(": \\", ":\\").split(",")
            data2 = {}
            for y in x[:-1]:
                data2.update(yaml.safe_load(y))

            data3.append(data2)

    runstats_df = pd.DataFrame(data3)

    if "IsWarmup" in runstats_df.columns:
        warmup_mask = runstats_df["IsWarmup"].fillna("0").astype(str).str.strip().str.lower().isin({"1", "true", "yes"})
        if plvl >= 1:
            print(f"Warmup rows filtered (IsWarmup): {int(warmup_mask.sum())}")
        runstats_df = runstats_df.loc[~warmup_mask].copy()

    if "ScenarioCase" in runstats_df.columns:
        scenario_warmup_mask = runstats_df["ScenarioCase"].fillna("").astype(str).str.lower().str.contains("warmup", regex=False)
        if plvl >= 1:
            print(f"Warmup rows filtered (ScenarioCase): {int(scenario_warmup_mask.sum())}")
        runstats_df = runstats_df.loc[~scenario_warmup_mask].copy()
    elif "VariParam" in runstats_df.columns:
        variParam_warmup_mask = runstats_df["VariParam"].fillna("").astype(str).str.lower().str.contains("warmup", regex=False)
        if plvl >= 1:
            print(f"Warmup rows filtered (VariParam): {int(variParam_warmup_mask.sum())}")
        runstats_df = runstats_df.loc[~variParam_warmup_mask].copy()

    if plvl >= 2:
        print("\n\nRunStatsDF:\n")
        display(runstats_df[["TotalTime", "IterationTime"]])

    runstats_df["FullFilePath"] = runstats_df[["FilePath", "FileName"]].agg("".join, axis=1)
    if plvl >= 2:
        print("\n\nRunStatsDF 'FulleFilePath':\n")
        display(runstats_df["FullFilePath"])

    ike_state_stats = pd.DataFrame()
    log_stats = {}

    for log in runstats_df["FullFilePath"]:
        ike_state_dict = get_Ike_State(log)
        df = pd.DataFrame(ike_state_dict)

        log_stats["FullFilePath"] = log
        log_stats.update(Get_Ike_State_Stats(df))
        if len(ike_state_stats.columns) == 0:
            ike_state_stats = pd.DataFrame(log_stats, index=[0])
        else:
            ike_state_stats = pd.concat([ike_state_stats, pd.DataFrame(log_stats, index=[0])], axis=0)

    run_log_stats_df = runstats_df.merge(ike_state_stats, how="inner", on="FullFilePath")

    if plvl > 2:
        print("\n\nRunLogStatsDF:\n")
        display(run_log_stats_df)
        print("\n\nSaving RunLogStatsDF to a csv file.")

    return run_log_stats_df
