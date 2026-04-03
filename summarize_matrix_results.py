#!/usr/bin/env python3
"""Render matrix percentile and overhead charts with SVG output.

This module prefers Matplotlib for rendering. If Matplotlib is unavailable,
it falls back to handcrafted SVG so the report is still generated.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import pandas as pd

METRICS = ("p50", "p95", "p99")
DEFAULT_PROFILE_ORDER = ("ideal", "metro", "wan", "lossy", "harsh")

BASELINE_COLOR = "#1e88e5"
PQC_COLOR = "#e07a1f"
GRID_COLOR = "#d7dbe0"
TEXT_COLOR = "#142033"
SURFACE_COLOR = "#f8fbff"
PANEL_COLOR = "#ffffff"
OVERHEAD_COLORS = {
    "p50": "#2f6db0",
    "p95": "#c4641a",
    "p99": "#267d4f",
}


@dataclass
class ProfileComparison:
    profile: str
    detail: str
    baseline: Dict[str, float]
    pqc: Dict[str, float]
    overhead: Dict[str, float]


class _SvgBuilder:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            "<defs>",
            '<linearGradient id="pageBg" x1="0" y1="0" x2="1" y2="1">',
            '<stop offset="0%" stop-color="#f2f8ff"/>',
            '<stop offset="100%" stop-color="#edf3fb"/>',
            "</linearGradient>",
            "</defs>",
        ]

    def add(self, payload: str) -> None:
        self._parts.append(payload)

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: int = 14,
        weight: str = "400",
        anchor: str = "start",
        fill: str = TEXT_COLOR,
    ) -> None:
        safe = html.escape(str(value), quote=True)
        self._parts.append(
            (
                f'<text x="{x:.2f}" y="{y:.2f}" font-family="Verdana, DejaVu Sans, sans-serif" '
                f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{safe}</text>'
            )
        )

    def close(self) -> str:
        self._parts.append("</svg>")
        return "\n".join(self._parts)


def _fmt_seconds(value: float) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    return f"{value:.3f}"


def _fmt_tick(value: float) -> str:
    if value is None or not math.isfinite(value):
        return "0.000"
    return f"{value:.3f}"


def _fmt_percent(value: float) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def _safe_float(value) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else math.nan
    except Exception:  # noqa: BLE001
        return math.nan


def _first_non_empty(group: pd.DataFrame, column: str) -> str:
    if column not in group.columns:
        return ""
    series = group[column].dropna().astype(str).str.strip()
    series = series[series != ""]
    if series.empty:
        return ""
    return series.iloc[0]


def _build_detail_label(group: pd.DataFrame) -> str:
    profile = _first_non_empty(group, "NetworkProfile")
    if profile:
        compact = profile.replace("|", " ").replace(",", " ")
        if len(compact) > 78:
            compact = compact[:75].rstrip() + "..."
        return compact

    pieces = []
    for col, label in (
        ("delay_ms", "delay"),
        ("loss_pct", "loss"),
        ("duplicate_pct", "duplicate"),
        ("corrupt_pct", "corrupt"),
        ("reorder_pct", "reorder"),
        ("rate_kbit", "rate"),
        ("delay", "delay"),
        ("loss", "loss"),
    ):
        value = _first_non_empty(group, col)
        if value:
            pieces.append(f"{label} {value}")

    if not pieces:
        return "no network limits"
    return " | ".join(pieces)


def _baseline_mask(df: pd.DataFrame) -> pd.Series:
    if "Baseline" in df.columns:
        try:
            return df["Baseline"].fillna(False).astype(bool)
        except Exception:  # noqa: BLE001
            pass
    if "Algorithm" in df.columns:
        return df["Algorithm"].fillna("").astype(str).str.contains(
            r"classic-kex|classic[_-]?classic|baseline",
            case=False,
            regex=True,
        )
    return pd.Series([False] * len(df), index=df.index)


def _profile_sort_key(profile: str) -> tuple[int, str]:
    mapping = {name: idx for idx, name in enumerate(DEFAULT_PROFILE_ORDER)}
    lower_name = profile.lower().strip()
    return (mapping.get(lower_name, 999), lower_name)


def _build_comparisons(df: pd.DataFrame) -> List[ProfileComparison]:
    if df is None or df.empty:
        return []

    required = ["p50", "p95", "p99"]
    if not all(col in df.columns for col in required):
        return []

    if "ScenarioCase" in df.columns and df["ScenarioCase"].fillna("").astype(str).str.strip().ne("").any():
        profile_col = "ScenarioCase"
    elif "VariParam" in df.columns:
        profile_col = "VariParam"
    else:
        return []

    work_df = df.copy()
    baseline_mask = _baseline_mask(work_df)

    comparisons: List[ProfileComparison] = []
    for profile, group in work_df.groupby(profile_col, dropna=False):
        profile_name = str(profile).strip() if str(profile).strip() else "unknown"
        group_mask = baseline_mask.loc[group.index]
        baseline_group = group[group_mask]
        pqc_group = group[~group_mask]

        if baseline_group.empty or pqc_group.empty:
            continue

        baseline_values: Dict[str, float] = {}
        pqc_values: Dict[str, float] = {}
        overhead_values: Dict[str, float] = {}

        for metric in METRICS:
            base_v = pd.to_numeric(baseline_group[metric], errors="coerce").mean()
            pqc_v = pd.to_numeric(pqc_group[metric], errors="coerce").mean()
            base_val = _safe_float(base_v)
            pqc_val = _safe_float(pqc_v)
            baseline_values[metric] = base_val
            pqc_values[metric] = pqc_val
            if math.isfinite(base_val) and base_val > 0 and math.isfinite(pqc_val):
                overhead_values[metric] = ((pqc_val - base_val) / base_val) * 100.0
            else:
                overhead_values[metric] = math.nan

        if not any(math.isfinite(baseline_values[m]) and math.isfinite(pqc_values[m]) for m in METRICS):
            continue

        comparisons.append(
            ProfileComparison(
                profile=profile_name,
                detail=_build_detail_label(group),
                baseline=baseline_values,
                pqc=pqc_values,
                overhead=overhead_values,
            )
        )

    comparisons.sort(key=lambda item: _profile_sort_key(item.profile))
    return comparisons


def _collect_latency_bounds(records: Sequence[ProfileComparison]) -> tuple[float, float]:
    values: List[float] = []
    for rec in records:
        for metric in METRICS:
            values.append(rec.baseline.get(metric, math.nan))
            values.append(rec.pqc.get(metric, math.nan))
    finite = [v for v in values if math.isfinite(v)]
    if not finite:
        return (0.0, 1.0)
    vmin = min(finite)
    vmax = max(finite)
    if vmin == vmax:
        pad = 0.1 * vmax if vmax else 1.0
        return (max(0.0, vmin - pad), vmax + pad)
    return (max(0.0, vmin * 0.9), vmax * 1.15)


def _collect_overhead_bounds(records: Sequence[ProfileComparison]) -> tuple[float, float]:
    values: List[float] = []
    for rec in records:
        for metric in METRICS:
            values.append(rec.overhead.get(metric, math.nan))
    finite = [v for v in values if math.isfinite(v)]
    if not finite:
        return (-5.0, 5.0)
    lo = min(finite + [0.0])
    hi = max(finite + [0.0])
    if lo == hi:
        return (lo - 5.0, hi + 5.0)
    pad = max(3.0, 0.15 * (hi - lo))
    return (lo - pad, hi + pad)


def _render_latency_matplotlib(records: Sequence[ProfileComparison], out_path: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return False

    profiles = [r.profile for r in records]
    details = [r.detail for r in records]
    x = list(range(len(records)))

    fig, axes = plt.subplots(1, 3, figsize=(17, 6.8))
    fig.patch.set_facecolor("#f2f8ff")
    fig.suptitle("Matrix Latency Percentiles", fontsize=18, fontweight="bold", y=0.98)
    fig.text(
        0.5,
        0.945,
        "Columns: P50 / P95 / P99. Groups: network profile. Bars: Baseline vs PQC(avg).",
        ha="center",
        fontsize=10,
        color="#334e68",
    )

    for idx, metric in enumerate(METRICS):
        ax = axes[idx]
        base_values = [r.baseline.get(metric, math.nan) for r in records]
        pqc_values = [r.pqc.get(metric, math.nan) for r in records]

        width = 0.34
        bars_a = ax.bar([v - width / 2 for v in x], base_values, width=width, color=BASELINE_COLOR, label="Baseline")
        bars_b = ax.bar([v + width / 2 for v in x], pqc_values, width=width, color=PQC_COLOR, label="PQC")

        for bar in list(bars_a) + list(bars_b):
            h = bar.get_height()
            if math.isfinite(h):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    h,
                    f"{h:.3f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

        ax.set_title(metric.upper(), fontsize=13, fontweight="bold")
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8, alpha=0.9)
        ax.set_axisbelow(True)
        ax.set_ylabel("Latency (s)")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{p}\n{d}" for p, d in zip(profiles, details)], fontsize=9)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.90))
    fig.tight_layout(rect=[0.01, 0.03, 0.99, 0.88])
    fig.savefig(out_path, format="svg")
    plt.close(fig)
    return True


def _render_latency_svg(records: Sequence[ProfileComparison], out_path: Path) -> None:
    width = 1500
    height = 860
    margin = 30
    gap = 22
    panel_top = 190
    panel_height = 610
    panel_width = (width - margin * 2 - gap * 2) / 3.0

    builder = _SvgBuilder(width, height)
    builder.add(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#pageBg)"/>')

    builder.add('<rect x="22" y="18" width="1456" height="132" rx="16" fill="#e9f3ff" stroke="#c2d8ef"/>')
    builder.text(46, 66, "Matrix Latency Percentiles", size=30, weight="700")
    builder.text(
        46,
        96,
        "By metric columns (P50/P95/P99), profile groups, and Baseline vs PQC bars.",
        size=14,
        fill="#3d556f",
    )

    legend_y = 138
    builder.add(f'<rect x="46" y="{legend_y}" width="16" height="16" rx="2" fill="{BASELINE_COLOR}"/>')
    builder.text(70, legend_y + 13, "Baseline", size=13)
    builder.add(f'<rect x="170" y="{legend_y}" width="16" height="16" rx="2" fill="{PQC_COLOR}"/>')
    builder.text(194, legend_y + 13, "PQC(avg)", size=13)

    for metric_idx, metric in enumerate(METRICS):
        panel_x = margin + metric_idx * (panel_width + gap)
        panel_y = panel_top

        builder.add(
            (
                f'<rect x="{panel_x:.2f}" y="{panel_y:.2f}" width="{panel_width:.2f}" height="{panel_height:.2f}" '
                f'rx="14" fill="{PANEL_COLOR}" stroke="#cad5e2"/>'
            )
        )
        builder.text(panel_x + panel_width / 2, panel_y + 35, metric.upper(), size=20, weight="700", anchor="middle")

        plot_x0 = panel_x + 64
        plot_y0 = panel_y + 70
        plot_w = panel_width - 84
        plot_h = panel_height - 210
        plot_bottom = plot_y0 + plot_h

        values = [r.baseline.get(metric, math.nan) for r in records] + [r.pqc.get(metric, math.nan) for r in records]
        finite = [v for v in values if math.isfinite(v)]
        max_val = max(finite) if finite else 1.0
        max_val *= 1.15
        if max_val <= 0:
            max_val = 1.0

        ticks = [_safe_float(max_val * i / 5.0) for i in range(6)]
        for tick in ticks:
            y = plot_bottom - (tick / max_val) * plot_h
            builder.add(f'<line x1="{plot_x0:.2f}" y1="{y:.2f}" x2="{plot_x0 + plot_w:.2f}" y2="{y:.2f}" stroke="{GRID_COLOR}" stroke-width="1"/>')
            builder.text(plot_x0 - 8, y + 4, _fmt_tick(tick), size=11, anchor="end", fill="#4a5f78")

        builder.add(f'<line x1="{plot_x0:.2f}" y1="{plot_y0:.2f}" x2="{plot_x0:.2f}" y2="{plot_bottom:.2f}" stroke="#6885a5" stroke-width="2"/>')
        builder.add(f'<line x1="{plot_x0:.2f}" y1="{plot_bottom:.2f}" x2="{plot_x0 + plot_w:.2f}" y2="{plot_bottom:.2f}" stroke="#6885a5" stroke-width="2"/>')

        group_count = max(1, len(records))
        group_step = plot_w / group_count
        bar_w = min(28.0, group_step * 0.25)

        for idx, rec in enumerate(records):
            cx = plot_x0 + group_step * (idx + 0.5)
            baseline_val = rec.baseline.get(metric, math.nan)
            pqc_val = rec.pqc.get(metric, math.nan)

            if math.isfinite(baseline_val):
                h = (baseline_val / max_val) * plot_h
                x = cx - bar_w - 3
                y = plot_bottom - h
                builder.add(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" fill="{BASELINE_COLOR}" rx="3"/>'
                )
                builder.text(x + bar_w / 2, y - 6, _fmt_seconds(baseline_val), size=10, anchor="middle")

            if math.isfinite(pqc_val):
                h = (pqc_val / max_val) * plot_h
                x = cx + 3
                y = plot_bottom - h
                builder.add(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" fill="{PQC_COLOR}" rx="3"/>'
                )
                builder.text(x + bar_w / 2, y - 6, _fmt_seconds(pqc_val), size=10, anchor="middle")

            builder.text(cx, plot_bottom + 30, rec.profile, size=11, anchor="middle", weight="600")
            builder.text(cx, plot_bottom + 48, rec.detail, size=10, anchor="middle", fill="#526b84")

    out_path.write_text(builder.close(), encoding="utf-8")


def _render_overhead_matplotlib(records: Sequence[ProfileComparison], out_path: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return False

    x = list(range(len(records)))
    labels = [f"{r.profile}\n{r.detail}" for r in records]

    fig, ax = plt.subplots(1, 1, figsize=(14, 6.8))
    fig.patch.set_facecolor("#f2f8ff")
    ax.set_facecolor("#ffffff")

    fig.suptitle("Matrix Overhead Trend", fontsize=18, fontweight="bold", y=0.98)
    fig.text(
        0.5,
        0.945,
        "Overhead % = (PQC - Baseline) / Baseline. Mean line intentionally omitted.",
        ha="center",
        fontsize=10,
        color="#334e68",
    )

    for metric in METRICS:
        y_vals = [r.overhead.get(metric, math.nan) for r in records]
        ax.plot(x, y_vals, marker="o", linewidth=2.5, color=OVERHEAD_COLORS[metric], label=metric.upper())
        for x_i, y_i in zip(x, y_vals):
            if math.isfinite(y_i):
                ax.text(x_i, y_i, _fmt_percent(y_i), fontsize=8, ha="center", va="bottom")

    ax.axhline(0.0, color="#6e7f90", linestyle="--", linewidth=1.2)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_ylabel("Overhead %")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)

    fig.legend(loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.90))
    fig.tight_layout(rect=[0.01, 0.03, 0.99, 0.88])
    fig.savefig(out_path, format="svg")
    plt.close(fig)
    return True


def _render_overhead_svg(records: Sequence[ProfileComparison], out_path: Path) -> None:
    width = 1400
    height = 780

    builder = _SvgBuilder(width, height)
    builder.add(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#pageBg)"/>')
    builder.add('<rect x="24" y="20" width="1352" height="132" rx="16" fill="#e9f3ff" stroke="#c2d8ef"/>')

    builder.text(48, 70, "Matrix Overhead Trend", size=30, weight="700")
    builder.text(
        48,
        100,
        "Single-axis trend comparison for P50/P95/P99 overhead percentages.",
        size=14,
        fill="#3d556f",
    )

    legend_y = 138
    x_cursor = 48
    for metric in METRICS:
        color = OVERHEAD_COLORS[metric]
        builder.add(f'<rect x="{x_cursor}" y="{legend_y}" width="16" height="16" rx="2" fill="{color}"/>')
        builder.text(x_cursor + 24, legend_y + 13, metric.upper(), size=13)
        x_cursor += 92

    chart_x = 72
    chart_y = 210
    chart_w = width - 132
    chart_h = 430
    chart_bottom = chart_y + chart_h

    y_min, y_max = _collect_overhead_bounds(records)
    if y_max <= y_min:
        y_min, y_max = -5.0, 5.0

    for tick_idx in range(6):
        tick_val = y_min + (y_max - y_min) * (tick_idx / 5.0)
        y = chart_bottom - (tick_val - y_min) / (y_max - y_min) * chart_h
        builder.add(f'<line x1="{chart_x}" y1="{y:.2f}" x2="{chart_x + chart_w}" y2="{y:.2f}" stroke="{GRID_COLOR}" stroke-width="1"/>')
        builder.text(chart_x - 8, y + 4, _fmt_percent(tick_val), size=11, anchor="end", fill="#4a5f78")

    if y_min <= 0.0 <= y_max:
        zero_y = chart_bottom - (0.0 - y_min) / (y_max - y_min) * chart_h
        builder.add(
            f'<line x1="{chart_x}" y1="{zero_y:.2f}" x2="{chart_x + chart_w}" y2="{zero_y:.2f}" stroke="#5d6f82" stroke-width="1.6" stroke-dasharray="6,5"/>'
        )

    builder.add(f'<line x1="{chart_x}" y1="{chart_y}" x2="{chart_x}" y2="{chart_bottom}" stroke="#6885a5" stroke-width="2"/>')
    builder.add(f'<line x1="{chart_x}" y1="{chart_bottom}" x2="{chart_x + chart_w}" y2="{chart_bottom}" stroke="#6885a5" stroke-width="2"/>')

    count = max(1, len(records))
    step = chart_w / count
    x_points = [chart_x + step * (i + 0.5) for i in range(count)]

    for metric in METRICS:
        color = OVERHEAD_COLORS[metric]
        points = []
        for idx, rec in enumerate(records):
            val = rec.overhead.get(metric, math.nan)
            if math.isfinite(val):
                py = chart_bottom - (val - y_min) / (y_max - y_min) * chart_h
                points.append((x_points[idx], py, val))

        if len(points) >= 2:
            path = " ".join(f"L {x:.2f} {y:.2f}" for x, y, _ in points[1:])
            builder.add(f'<path d="M {points[0][0]:.2f} {points[0][1]:.2f} {path}" fill="none" stroke="{color}" stroke-width="3"/>')

        for x, y, val in points:
            builder.add(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{color}"/>')
            builder.text(x, y - 8, _fmt_percent(val), size=10, anchor="middle")

    for idx, rec in enumerate(records):
        x = x_points[idx]
        builder.text(x, chart_bottom + 28, rec.profile, size=11, anchor="middle", weight="600")
        builder.text(x, chart_bottom + 46, rec.detail, size=10, anchor="middle", fill="#526b84")

    out_path.write_text(builder.close(), encoding="utf-8")


def _build_audit_row(
    *,
    stat: str,
    points: int,
    image: str,
    y_values: Iterable[float],
    note: str,
) -> Dict[str, object]:
    finite = [v for v in y_values if math.isfinite(v)]
    if finite:
        y_min = float(min(finite))
        y_max = float(max(finite))
    else:
        y_min, y_max = 0.0, 0.0

    return {
        "VariParam": "matrix",
        "Stat": stat,
        "Points": int(points),
        "XMin": 0.0,
        "XMax": float(max(0, points - 1)),
        "YMin": y_min,
        "YMax": y_max,
        "Note": note,
        "Image": image,
    }


def generate_matrix_svgs(run_log_stats_df: pd.DataFrame, output_dir: Path | str) -> pd.DataFrame:
    """Generate matrix SVG visuals and return plot-audit rows."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    records = _build_comparisons(run_log_stats_df)
    if not records:
        return pd.DataFrame()

    audit_rows: List[Dict[str, object]] = []

    latency_svg = out_dir / "matrix_latency_percentiles.svg"
    if _render_latency_matplotlib(records, latency_svg):
        latency_note = "small_multiples_p50_p95_p99_matplotlib"
    else:
        _render_latency_svg(records, latency_svg)
        latency_note = "small_multiples_p50_p95_p99_manual_svg"

    latency_values = []
    for rec in records:
        for metric in METRICS:
            latency_values.append(rec.baseline.get(metric, math.nan))
            latency_values.append(rec.pqc.get(metric, math.nan))

    audit_rows.append(
        _build_audit_row(
            stat="latency_percentiles",
            points=len(records) * len(METRICS) * 2,
            image=latency_svg.name,
            y_values=latency_values,
            note=latency_note,
        )
    )

    overhead_svg = out_dir / "matrix_overhead.svg"
    if _render_overhead_matplotlib(records, overhead_svg):
        overhead_note = "overhead_p50_p95_p99_matplotlib"
    else:
        _render_overhead_svg(records, overhead_svg)
        overhead_note = "overhead_p50_p95_p99_manual_svg"

    overhead_values = []
    for rec in records:
        for metric in METRICS:
            overhead_values.append(rec.overhead.get(metric, math.nan))

    audit_rows.append(
        _build_audit_row(
            stat="overhead_percent",
            points=len(records) * len(METRICS),
            image=overhead_svg.name,
            y_values=overhead_values,
            note=overhead_note,
        )
    )

    return pd.DataFrame(audit_rows)
