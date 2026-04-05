from datetime import datetime
from pathlib import Path

import pandas as pd

from ..processing.warmup import exclude_warmup_rows


def _fmt_num(value):
    try:
        return f"{float(value):.3f}"
    except Exception:  # noqa: BLE001
        return str(value)


def generate_experiment_report(log_dir, run_log_stats_df, plot_audit_df):
    """Generate a one-page markdown experiment report in the result directory.
    
    Args:
        log_dir: Output directory for the report
        run_log_stats_df: DataFrame with run statistics  
        plot_audit_df: DataFrame with plot audit information

    Returns:
        Path to the generated report
    """
    out_dir = Path(log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    data_for_report = exclude_warmup_rows(run_log_stats_df)

    report_path = out_dir / "ExperimentReport.md"
    image_files = sorted([p.name for p in out_dir.iterdir() if p.suffix.lower() in {".png", ".svg"}])

    lines = []
    lines.append("# Experiment Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Result Directory: {out_dir}")
    lines.append("")

    lines.append("## Dataset Overview")
    lines.append("")
    lines.append(f"- Total rows: {len(data_for_report)}")
    if "Algorithm" in data_for_report.columns:
        lines.append(f"- Algorithms: {', '.join(sorted(data_for_report['Algorithm'].dropna().astype(str).unique().tolist()))}")
    if "VariParam" in data_for_report.columns:
        lines.append(f"- VariParams: {', '.join(sorted(data_for_report['VariParam'].dropna().astype(str).unique().tolist()))}")
    if "ScenarioCase" in data_for_report.columns:
        cases = sorted([x for x in data_for_report['ScenarioCase'].dropna().astype(str).unique().tolist() if x])
        if cases:
            lines.append(f"- ScenarioCases: {', '.join(cases)}")
    lines.append("")

    lines.append("## Key Metrics (mean by Algorithm x VariParam)")
    lines.append("")
    cols = [
        c
        for c in [
            "Algorithm",
            "VariParam",
            "mean",
            "median",
            "p50",
            "p75",
            "p90",
            "p95",
            "ConnectionPercent",
            "IterationTime",
        ]
        if c in data_for_report.columns
    ]
    if len(cols) >= 3:
        grouped = (
            data_for_report[cols]
            .groupby([c for c in ["Algorithm", "VariParam"] if c in cols], dropna=False)
            .mean(numeric_only=True)
            .reset_index()
        )
        lines.append("| Algorithm | VariParam | mean | median | p50 | p75 | p90 | p95 | ConnectionPercent | IterationTime |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for _, r in grouped.iterrows():
            cp = _fmt_num(r.get("ConnectionPercent", ""))
            if cp != "":
                try:
                    cp = f"{float(cp) * 100:.2f}%"
                except Exception:  # noqa: BLE001
                    pass
            lines.append(
                f"| {r.get('Algorithm', '')} | {r.get('VariParam', '')} | {_fmt_num(r.get('mean', ''))} | {_fmt_num(r.get('median', ''))} | {_fmt_num(r.get('p50', ''))} | {_fmt_num(r.get('p75', ''))} | {_fmt_num(r.get('p90', ''))} | {_fmt_num(r.get('p95', ''))} | {cp} | {_fmt_num(r.get('IterationTime', ''))} |"
            )
    else:
        lines.append("Insufficient columns to generate grouped metric table.")
    lines.append("")

    if "ScenarioCase" in data_for_report.columns:
        case_cols = [
            c
            for c in [
                "ScenarioCase",
                "Algorithm",
                "mean",
                "median",
                "p50",
                "p75",
                "p90",
                "p95",
                "ConnectionPercent",
                "IterationTime",
            ]
            if c in data_for_report.columns
        ]
        if len(case_cols) >= 3:
            lines.append("## Key Metrics (mean by ScenarioCase x Algorithm)")
            lines.append("")
            grouped_case = (
                data_for_report[case_cols]
                .groupby([c for c in ["ScenarioCase", "Algorithm"] if c in case_cols], dropna=False)
                .mean(numeric_only=True)
                .reset_index()
            )
            lines.append("| ScenarioCase | Algorithm | mean | median | p50 | p75 | p90 | p95 | ConnectionPercent | IterationTime |")
            lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
            for _, r in grouped_case.iterrows():
                cp = _fmt_num(r.get("ConnectionPercent", ""))
                if cp != "":
                    try:
                        cp = f"{float(cp) * 100:.2f}%"
                    except Exception:  # noqa: BLE001
                        pass
                lines.append(
                    f"| {r.get('ScenarioCase', '')} | {r.get('Algorithm', '')} | {_fmt_num(r.get('mean', ''))} | {_fmt_num(r.get('median', ''))} | {_fmt_num(r.get('p50', ''))} | {_fmt_num(r.get('p75', ''))} | {_fmt_num(r.get('p90', ''))} | {_fmt_num(r.get('p95', ''))} | {cp} | {_fmt_num(r.get('IterationTime', ''))} |"
                )
            lines.append("")

    lines.append("## Plot Audit")
    lines.append("")
    if plot_audit_df is not None and len(plot_audit_df) > 0:
        lines.append("| VariParam | Stat | Points | XRange | YRange | Note | Image |")
        lines.append("| --- | --- | ---: | --- | --- | --- | --- |")
        for _, row in plot_audit_df.iterrows():
            x_range = f"[{_fmt_num(row.get('XMin'))}, {_fmt_num(row.get('XMax'))}]"
            y_range = f"[{_fmt_num(row.get('YMin'))}, {_fmt_num(row.get('YMax'))}]"
            img = row.get("Image", "")
            lines.append(
                f"| {row.get('VariParam', '')} | {row.get('Stat', '')} | {int(row.get('Points', 0))} | {x_range} | {y_range} | {row.get('Note', '')} | [{img}]({img}) |"
            )
    else:
        lines.append("No plot audit data generated.")
    lines.append("")

    lines.append("## Image Index")
    lines.append("")
    if image_files:
        for image in image_files:
            lines.append(f"- [{image}]({image})")
    else:
        lines.append("No images found in result directory.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(report_path)
