"""Run the end-to-end PQCCN orchestration pipeline.

Preferred usage:
  python3 -m pqccn_strongswan ./logs ./data_collection/configs/DataCollect_composite_ideal.yaml
  python3 -m pqccn_strongswan ./logs "./data_collection/configs/*.yaml"
  python3 -m pqccn_strongswan ./logs ./data_collection/configs/
"""

import argparse
from pathlib import Path


def main() -> int:
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

    from .analysis import plotting
    from .collection import data_collect_core
    from .config_utils import resolve_config_files
    from .parsing import process_logs
    from .preparation import process_stats
    from .reporting import generate_experiment_report

    log_dir = str(Path(args.log_dir))
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    config_files = resolve_config_files(args.configs)
    if not config_files:
        raise FileNotFoundError(f"No config files found from input: {args.configs}")

    for yml_cfg in config_files:
        print(f"Processing Config File: {yml_cfg}\n")
        data_collect_core.RunConfig(yml_cfg, (log_dir + "/"), args.collect_print_level)

    run_log_stats_df = process_logs.Log_stats(log_dir, args.print_level)
    data_file = str(Path(log_dir) / "RunLogStatsDF.csv")
    run_log_stats_df.to_csv(data_file, index=False)

    run_log_stats_df = process_stats.MarkLogs(run_log_stats_df, args.print_level)
    run_log_stats_df.to_csv(data_file, index=False)

    plot_audit_df = plotting.PlotVariParam(run_log_stats_df, log_dir, args.print_level)
    if plot_audit_df is not None and len(plot_audit_df) > 0:
        plot_audit_df.to_csv(str(Path(log_dir) / "PlotAudit.csv"), index=False)

    # Keep a short summary table for quick checks.
    summary_file = str(Path(log_dir) / "RunLogStatsDF_summary.csv")
    summary_cols = [
        c
        for c in [
            "Algorithm",
            "ScenarioGroup",
            "ScenarioCase",
            "VariParam",
            "SweepKey",
            "NetworkProfile",
            "mean",
            "median",
            "p50",
            "p95",
            "p99",
            "ConnectionPercent",
            "IterationTime",
        ]
        if c in run_log_stats_df.columns
    ]
    if summary_cols:
        summary_df = run_log_stats_df[summary_cols].copy()
        summary_df.to_csv(summary_file, index=False)

    report_path = generate_experiment_report(log_dir, run_log_stats_df, plot_audit_df)

    print(f"Orchestration complete. Output directory: {log_dir}")
    print(f"Experiment report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
