"""Orchestrate data collection, parsing, preparation, and plotting.

Usage examples:
  python3 Orchestration.py ./logs ./data_collection/configs/DataCollect.yaml
  python3 Orchestration.py ./logs "./data_collection/configs/*.yaml"
  python3 Orchestration.py ./logs ./data_collection/configs/
"""

import argparse
from pathlib import Path

from data_collection import DataCollectCore
from data_parsing import ProcessLogs
from data_preparation import ProcessStats
from data_analysis import Plotting
from config_utils import resolve_config_files


def main():
    parser = argparse.ArgumentParser(description="Run end-to-end PQCCN test orchestration")
    parser.add_argument("log_dir", help="Directory to store generated logs and outputs")
    parser.add_argument(
        "configs",
        help="A YAML file, YAML directory, wildcard pattern, or comma-separated list",
    )
    parser.add_argument("--print-level", type=int, default=2, help="Pipeline print level")
    parser.add_argument(
        "--collect-print-level",
        type=int,
        default=1,
        help="DataCollectCore print level",
    )
    args = parser.parse_args()

    log_dir = str(Path(args.log_dir))
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    config_files = resolve_config_files(args.configs)
    if not config_files:
        raise FileNotFoundError(f"No config files found from input: {args.configs}")

    for yml_cfg in config_files:
        print(f"Processing Config File: {yml_cfg}\n")
        DataCollectCore.RunConfig(yml_cfg, (log_dir + "/"), args.collect_print_level)

    run_log_stats_df = ProcessLogs.Log_stats(log_dir, args.print_level)
    data_file = str(Path(log_dir) / "RunLogStatsDF.csv")
    run_log_stats_df.to_csv(data_file, index=False)

    run_log_stats_df = ProcessStats.MarkLogs(run_log_stats_df, args.print_level)
    run_log_stats_df.to_csv(data_file, index=False)

    Plotting.PlotVariParam(run_log_stats_df, log_dir, args.print_level)

    # Keep a short summary table for quick checks.
    summary_file = str(Path(log_dir) / "RunLogStatsDF_summary.csv")
    summary_cols = [
        c
        for c in ["Algorithm", "VariParam", "mean", "median", "ConnectionPercent", "IterationTime"]
        if c in run_log_stats_df.columns
    ]
    if summary_cols:
        summary_df = run_log_stats_df[summary_cols].copy()
        summary_df.to_csv(summary_file, index=False)

    print(f"Orchestration complete. Output directory: {log_dir}")


if __name__ == "__main__":
    main()
