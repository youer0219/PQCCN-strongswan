#!/usr/bin/env python3
"""Generate matrix heatmaps for percentile and overhead metrics."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import pandas as pd

METRICS = ("p50", "p95", "p99")
SCENARIO_ORDER = ("ideal", "metro", "wan", "lossy")


def _safe_float(value) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else math.nan
    except Exception:  # noqa: BLE001
        return math.nan


def _scenario_key(name: str) -> Tuple[int, str]:
    label = str(name or "").strip().lower()
    if label in SCENARIO_ORDER:
        return (SCENARIO_ORDER.index(label), label)
    return (999, label)


def _algo_key(name: str) -> Tuple[int, str]:
    label = str(name or "").strip().lower()
    if "classic" in label:
        return (0, label)
    if "hybrid(1pq)" in label or "hybrid1pq" in label:
        return (1, label)
    if "hybrid(2pq)" in label or "hybrid2pq" in label:
        return (2, label)
    return (999, label)


def _find_col(df: pd.DataFrame, preferred: str, fallback: str) -> str:
    if preferred in df.columns:
        return preferred
    if fallback in df.columns:
        return fallback
    raise ValueError(f"Missing required columns: {preferred} or {fallback}")


def _prepare_base_table(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    algo_col = _find_col(df, "Algorithm", "Algorithm")
    scen_col = _find_col(df, "ScenarioCase", "VariParam")

    required = [algo_col, scen_col, *METRICS]
    work = df[[c for c in required if c in df.columns]].copy()
    work = work.rename(columns={algo_col: "Algorithm", scen_col: "ScenarioCase"})
    work["Algorithm"] = work["Algorithm"].fillna("").astype(str).str.strip()
    work["ScenarioCase"] = work["ScenarioCase"].fillna("").astype(str).str.strip().str.lower()

    work = work[(work["Algorithm"] != "") & (work["ScenarioCase"] != "")].copy()
    for metric in METRICS:
        work[metric] = pd.to_numeric(work[metric], errors="coerce")

    grouped = (
        work.groupby(["Algorithm", "ScenarioCase"], dropna=False)[list(METRICS)]
        .mean(numeric_only=True)
        .reset_index()
    )

    if grouped.empty:
        return grouped

    algo_order = sorted(grouped["Algorithm"].unique().tolist(), key=_algo_key)
    scen_order_raw = grouped["ScenarioCase"].unique().tolist()
    scen_order = sorted(scen_order_raw, key=_scenario_key)

    grouped["Algorithm"] = pd.Categorical(grouped["Algorithm"], categories=algo_order, ordered=True)
    grouped["ScenarioCase"] = pd.Categorical(grouped["ScenarioCase"], categories=scen_order, ordered=True)
    grouped = grouped.sort_values(["Algorithm", "ScenarioCase"]).reset_index(drop=True)
    return grouped


def _build_pivot(grouped: pd.DataFrame, metric: str) -> pd.DataFrame:
    pivot = grouped.pivot(index="Algorithm", columns="ScenarioCase", values=metric)
    ordered_cols = [c for c in SCENARIO_ORDER if c in pivot.columns] + [c for c in pivot.columns if c not in SCENARIO_ORDER]
    return pivot.reindex(columns=ordered_cols)


def _render_metric_heatmap(metric: str, pivot: pd.DataFrame, out_path: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:  # noqa: BLE001
        return False

    data = pivot.to_numpy(dtype=float)
    if data.size == 0:
        return False

    fig, ax = plt.subplots(figsize=(8.8, 3.8 + 0.5 * max(0, len(pivot.index) - 3)))
    fig.patch.set_facecolor("#f6fbff")
    ax.set_facecolor("#ffffff")

    cmap = plt.cm.YlGnBu
    im = ax.imshow(data, cmap=cmap, aspect="auto")

    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_xticklabels([str(c) for c in pivot.columns], fontsize=10)
    ax.set_yticklabels([str(i) for i in pivot.index], fontsize=10)
    ax.set_title(f"{metric.upper()} Latency Matrix (Algorithm x Network)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Network Scenario")
    ax.set_ylabel("Algorithm")

    # Draw value labels with contrast-aware color.
    finite = [v for v in data.flatten().tolist() if math.isfinite(v)]
    midpoint = sum(finite) / len(finite) if finite else 0.0
    for r in range(data.shape[0]):
        for c in range(data.shape[1]):
            v = data[r, c]
            txt = "n/a" if not math.isfinite(v) else f"{v:.3f}"
            color = "#0f172a" if (not math.isfinite(v) or v <= midpoint) else "#ffffff"
            ax.text(c, r, txt, ha="center", va="center", fontsize=9, color=color)

    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("Latency (s)")

    fig.tight_layout()
    fig.savefig(out_path, format="svg")
    plt.close(fig)
    return True


def _render_latency_panel(pivots: Dict[str, pd.DataFrame], out_path: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:  # noqa: BLE001
        return False

    if not pivots:
        return False

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.2))
    fig.patch.set_facecolor("#f6fbff")

    for ax, metric in zip(axes, METRICS):
        pivot = pivots.get(metric)
        if pivot is None or pivot.empty:
            ax.axis("off")
            continue

        data = pivot.to_numpy(dtype=float)
        im = ax.imshow(data, cmap=plt.cm.YlGnBu, aspect="auto")
        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_xticklabels([str(c) for c in pivot.columns], fontsize=9)
        ax.set_yticklabels([str(i) for i in pivot.index], fontsize=9)
        ax.set_title(metric.upper(), fontsize=12, fontweight="bold")

        finite = [v for v in data.flatten().tolist() if math.isfinite(v)]
        midpoint = sum(finite) / len(finite) if finite else 0.0
        for r in range(data.shape[0]):
            for c in range(data.shape[1]):
                v = data[r, c]
                txt = "n/a" if not math.isfinite(v) else f"{v:.3f}"
                color = "#0f172a" if (not math.isfinite(v) or v <= midpoint) else "#ffffff"
                ax.text(c, r, txt, ha="center", va="center", fontsize=8, color=color)

        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)

    fig.suptitle("Latency Percentiles Matrix (Algorithm x Network)", fontsize=16, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, format="svg")
    plt.close(fig)
    return True


def _build_overhead_pivot(pivots: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    out: Dict[str, pd.DataFrame] = {}
    for metric, pivot in pivots.items():
        if pivot is None or pivot.empty:
            continue
        baseline_rows = [idx for idx in pivot.index if "classic" in str(idx).lower()]
        if not baseline_rows:
            continue
        baseline = pivot.loc[baseline_rows[0]]

        rows = []
        for algo in pivot.index:
            if algo == baseline_rows[0]:
                continue
            row = []
            for col in pivot.columns:
                b = _safe_float(baseline.get(col, math.nan))
                v = _safe_float(pivot.loc[algo, col])
                if math.isfinite(b) and b > 0 and math.isfinite(v):
                    row.append(((v - b) / b) * 100.0)
                else:
                    row.append(math.nan)
            rows.append((algo, row))

        if not rows:
            continue

        frame = pd.DataFrame([row for _, row in rows], index=[algo for algo, _ in rows], columns=list(pivot.columns))
        out[metric] = frame
    return out


def _render_overhead_panel(overheads: Dict[str, pd.DataFrame], out_path: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception:  # noqa: BLE001
        return False

    if not overheads:
        return False

    fig, axes = plt.subplots(1, 3, figsize=(18, 4.8))
    fig.patch.set_facecolor("#f6fbff")

    for ax, metric in zip(axes, METRICS):
        pivot = overheads.get(metric)
        if pivot is None or pivot.empty:
            ax.axis("off")
            continue

        data = pivot.to_numpy(dtype=float)
        abs_max = max([abs(v) for v in data.flatten().tolist() if math.isfinite(v)] or [1.0])
        im = ax.imshow(data, cmap=plt.cm.RdYlGn_r, vmin=-abs_max, vmax=abs_max, aspect="auto")

        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_xticklabels([str(c) for c in pivot.columns], fontsize=9)
        ax.set_yticklabels([str(i) for i in pivot.index], fontsize=9)
        ax.set_title(f"{metric.upper()} Overhead %", fontsize=12, fontweight="bold")

        for r in range(data.shape[0]):
            for c in range(data.shape[1]):
                v = data[r, c]
                txt = "n/a" if not math.isfinite(v) else f"{v:+.1f}%"
                color = "#0f172a" if (not math.isfinite(v) or abs(v) < abs_max * 0.55) else "#ffffff"
                ax.text(c, r, txt, ha="center", va="center", fontsize=8, color=color)

        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)

    fig.suptitle("PQC Overhead vs Classic Baseline (Algorithm x Network)", fontsize=16, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, format="svg")
    plt.close(fig)
    return True


def _build_audit_row(stat: str, image: str, values: Sequence[float], note: str) -> Dict[str, object]:
    finite = [float(v) for v in values if math.isfinite(v)]
    y_min = min(finite) if finite else 0.0
    y_max = max(finite) if finite else 0.0
    return {
        "VariParam": "matrix",
        "Stat": stat,
        "Points": len(finite),
        "XMin": 0.0,
        "XMax": float(max(0, len(finite) - 1)),
        "YMin": float(y_min),
        "YMax": float(y_max),
        "Note": note,
        "Image": image,
    }


def generate_matrix_svgs(run_log_stats_df: pd.DataFrame, output_dir: Path | str) -> pd.DataFrame:
    """Generate algorithm x scenario matrix SVGs and return audit rows."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = _prepare_base_table(run_log_stats_df)
    if base.empty:
        return pd.DataFrame()

    pivots: Dict[str, pd.DataFrame] = {metric: _build_pivot(base, metric) for metric in METRICS}
    audit_rows: List[Dict[str, object]] = []

    for metric in METRICS:
        pivot = pivots[metric]
        out_file = out_dir / f"matrix_algo_scenario_{metric}.svg"
        if _render_metric_heatmap(metric, pivot, out_file):
            note = "algo_scenario_heatmap"
        else:
            note = "render_failed"
        values = pivot.to_numpy(dtype=float).flatten().tolist()
        audit_rows.append(_build_audit_row(f"{metric}_matrix", out_file.name, values, note))

    latency_panel = out_dir / "matrix_latency_percentiles.svg"
    if _render_latency_panel(pivots, latency_panel):
        all_values: List[float] = []
        for metric in METRICS:
            all_values.extend(pivots[metric].to_numpy(dtype=float).flatten().tolist())
        audit_rows.append(_build_audit_row("latency_percentiles", latency_panel.name, all_values, "panel_heatmap"))

    overheads = _build_overhead_pivot(pivots)
    if overheads:
        overhead_file = out_dir / "matrix_overhead_percentiles.svg"
        if _render_overhead_panel(overheads, overhead_file):
            over_vals: List[float] = []
            for metric in METRICS:
                ov = overheads.get(metric)
                if ov is not None:
                    over_vals.extend(ov.to_numpy(dtype=float).flatten().tolist())
            audit_rows.append(_build_audit_row("overhead_percent", overhead_file.name, over_vals, "panel_heatmap"))

    return pd.DataFrame(audit_rows)
