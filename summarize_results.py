#!/usr/bin/env python3
"""Render fixed-layout single-run packet byte comparison charts."""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

BASELINE_COLOR = "#1e88e5"
PQC_COLOR = "#e07a1f"
GRID_COLOR = "#d7dbe0"
TEXT_COLOR = "#142033"

FRAME_CANDIDATES = (
    "FrameBytes",
    "frame_bytes",
    "frameBytes",
    "Frame Bytes",
    "AvgFrameBytes",
)
PAYLOAD_CANDIDATES = (
    "TCPPayloadBytes",
    "TcpPayloadBytes",
    "tcp_payload_bytes",
    "PayloadBytes",
    "TCP Payload Bytes",
)


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

    def add(self, text: str) -> None:
        self._parts.append(text)

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


def _safe_float(value) -> float:
    try:
        v = float(value)
        return v if math.isfinite(v) else math.nan
    except Exception:  # noqa: BLE001
        return math.nan


def _fmt_value(value: float) -> str:
    if value is None or not math.isfinite(value):
        return "n/a"
    if abs(value - int(value)) < 1e-9:
        return f"{int(value)}"
    return f"{value:.1f}"


def _fmt_tick(value: float) -> str:
    if value is None or not math.isfinite(value):
        return "0"
    return f"{value:.0f}"


def _calc_overhead(base: float, pqc: float) -> str:
    if not (math.isfinite(base) and math.isfinite(pqc) and base > 0):
        return "Overhead: n/a"
    pct = (pqc - base) / base * 100.0
    sign = "+" if pct >= 0 else ""
    return f"Overhead: {sign}{pct:.1f}%"


def _pick_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _baseline_mask(df: pd.DataFrame) -> pd.Series:
    if "Baseline" in df.columns:
        return df["Baseline"].fillna(False).astype(bool)
    if "Algorithm" in df.columns:
        return df["Algorithm"].fillna("").astype(str).str.contains(
            r"classic-kex|classic[_-]?classic|baseline",
            case=False,
            regex=True,
        )
    return pd.Series([False] * len(df), index=df.index)


def generate_packet_bytes_svg(
    output_dir: Path | str,
    *,
    frame_baseline: float,
    frame_pqc: float,
    payload_baseline: float,
    payload_pqc: float,
    title: str = "Packet Size Baseline",
    subtitle: str = "Dual-panel comparison: Frame Bytes and TCP Payload Bytes",
    boundary_note: str = "Boundary frame: IKE_AUTH response accepted as handshake end",
    frames_note: str = "Frames counted: outbound + inbound handshake frames",
    post_newkeys_note: str = "Post-NEWKEYS payload frames: excluded from byte aggregation",
    filename: str = "packet_bytes.svg",
) -> Path:
    """Render a fixed-layout SVG with two bar panels and footer notes."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    width = 1320
    height = 860

    values = [frame_baseline, frame_pqc, payload_baseline, payload_pqc]
    finite_values = [v for v in values if math.isfinite(v)]
    ymax = max(finite_values) if finite_values else 1.0
    ymax *= 1.15
    if ymax <= 0:
        ymax = 1.0

    builder = _SvgBuilder(width, height)
    builder.add(f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#pageBg)"/>')

    builder.add('<rect x="22" y="18" width="1276" height="130" rx="16" fill="#e9f3ff" stroke="#c2d8ef"/>')
    builder.text(46, 66, title, size=30, weight="700")
    builder.text(46, 96, subtitle, size=14, fill="#3d556f")

    legend_y = 124
    builder.add(f'<rect x="46" y="{legend_y}" width="16" height="16" rx="2" fill="{BASELINE_COLOR}"/>')
    builder.text(70, legend_y + 13, "Baseline", size=13)
    builder.add(f'<rect x="170" y="{legend_y}" width="16" height="16" rx="2" fill="{PQC_COLOR}"/>')
    builder.text(194, legend_y + 13, "PQC", size=13)

    panel_top = 182
    panel_height = 500
    panel_gap = 26
    panel_width = (width - 56 * 2 - panel_gap) / 2.0

    panel_specs = [
        ("Frame Bytes", frame_baseline, frame_pqc, _calc_overhead(frame_baseline, frame_pqc)),
        ("TCP Payload Bytes", payload_baseline, payload_pqc, _calc_overhead(payload_baseline, payload_pqc)),
    ]

    for idx, (panel_title, base_val, pqc_val, overhead_text) in enumerate(panel_specs):
        panel_x = 56 + idx * (panel_width + panel_gap)
        panel_y = panel_top

        builder.add(
            (
                f'<rect x="{panel_x:.2f}" y="{panel_y:.2f}" width="{panel_width:.2f}" height="{panel_height:.2f}" '
                'rx="14" fill="#ffffff" stroke="#cad5e2"/>'
            )
        )
        builder.text(panel_x + panel_width / 2, panel_y + 36, panel_title, size=20, weight="700", anchor="middle")

        plot_x0 = panel_x + 72
        plot_y0 = panel_y + 70
        plot_w = panel_width - 104
        plot_h = panel_height - 190
        plot_bottom = plot_y0 + plot_h

        ticks = [ymax * i / 5.0 for i in range(6)]
        for tick in ticks:
            y = plot_bottom - (tick / ymax) * plot_h
            builder.add(
                f'<line x1="{plot_x0:.2f}" y1="{y:.2f}" x2="{plot_x0 + plot_w:.2f}" y2="{y:.2f}" stroke="{GRID_COLOR}" stroke-width="1"/>'
            )
            builder.text(plot_x0 - 8, y + 4, _fmt_tick(tick), size=11, anchor="end", fill="#4a5f78")

        builder.add(f'<line x1="{plot_x0:.2f}" y1="{plot_y0:.2f}" x2="{plot_x0:.2f}" y2="{plot_bottom:.2f}" stroke="#6885a5" stroke-width="2"/>')
        builder.add(
            f'<line x1="{plot_x0:.2f}" y1="{plot_bottom:.2f}" x2="{plot_x0 + plot_w:.2f}" y2="{plot_bottom:.2f}" stroke="#6885a5" stroke-width="2"/>'
        )

        positions = [plot_x0 + plot_w * 0.34, plot_x0 + plot_w * 0.66]
        bar_w = min(84.0, plot_w * 0.18)
        bars = [
            (positions[0], base_val, BASELINE_COLOR, "Baseline"),
            (positions[1], pqc_val, PQC_COLOR, "PQC"),
        ]

        for cx, val, color, label in bars:
            if math.isfinite(val):
                bar_h = (val / ymax) * plot_h
                x = cx - bar_w / 2.0
                y = plot_bottom - bar_h
                builder.add(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" fill="{color}" rx="4"/>'
                )
                builder.text(cx, y - 8, _fmt_value(val), size=12, weight="600", anchor="middle")
            builder.text(cx, plot_bottom + 26, label, size=12, anchor="middle")

        builder.text(panel_x + panel_width / 2, panel_y + panel_height - 18, overhead_text, size=12, anchor="middle", fill="#364d67")

    footer_y = 734
    builder.add('<rect x="22" y="706" width="1276" height="130" rx="14" fill="#ffffff" stroke="#cad5e2"/>')
    builder.text(46, footer_y + 14, boundary_note, size=13)
    builder.text(46, footer_y + 44, frames_note, size=13)
    builder.text(46, footer_y + 74, post_newkeys_note, size=13)

    out_path.write_text(builder.close(), encoding="utf-8")
    return out_path


def generate_packet_bytes_from_dataframe(
    run_log_stats_df: pd.DataFrame,
    output_dir: Path | str,
    *,
    filename: str = "packet_bytes.svg",
) -> Optional[Dict[str, object]]:
    """Create packet_bytes.svg if frame and payload byte columns are present.
    
    Filters out warmup data before processing.
    """
    if run_log_stats_df is None or run_log_stats_df.empty:
        return None

    # Filter out warmup data
    df = run_log_stats_df.copy()
    if 'IsWarmup' in df.columns:
        warmup_mask = df['IsWarmup'].fillna('0').astype(str).str.strip().str.lower().isin({'1', 'true', 'yes'})
        df = df.loc[~warmup_mask].copy()
    
    if 'ScenarioCase' in df.columns:
        scenario_mask = df['ScenarioCase'].fillna('').astype(str).str.lower().str.contains('warmup', regex=False)
        df = df.loc[~scenario_mask].copy()

    if df.empty:
        return None

    frame_col = _pick_column(df, FRAME_CANDIDATES)
    payload_col = _pick_column(df, PAYLOAD_CANDIDATES)
    if not frame_col or not payload_col:
        return None

    baseline_mask = _baseline_mask(df)
    baseline_df = df[baseline_mask]
    pqc_df = df[~baseline_mask]

    if baseline_df.empty or pqc_df.empty:
        return None

    frame_baseline = _safe_float(pd.to_numeric(baseline_df[frame_col], errors="coerce").mean())
    frame_pqc = _safe_float(pd.to_numeric(pqc_df[frame_col], errors="coerce").mean())
    payload_baseline = _safe_float(pd.to_numeric(baseline_df[payload_col], errors="coerce").mean())
    payload_pqc = _safe_float(pd.to_numeric(pqc_df[payload_col], errors="coerce").mean())

    if not any(math.isfinite(v) for v in [frame_baseline, frame_pqc, payload_baseline, payload_pqc]):
        return None

    svg_path = generate_packet_bytes_svg(
        output_dir,
        frame_baseline=frame_baseline,
        frame_pqc=frame_pqc,
        payload_baseline=payload_baseline,
        payload_pqc=payload_pqc,
        filename=filename,
    )

    y_values = [v for v in [frame_baseline, frame_pqc, payload_baseline, payload_pqc] if math.isfinite(v)]
    y_min = float(min(y_values)) if y_values else 0.0
    y_max = float(max(y_values)) if y_values else 0.0

    return {
        "VariParam": "packet",
        "Stat": "packet_bytes",
        "Points": 4,
        "XMin": 0.0,
        "XMax": 3.0,
        "YMin": y_min,
        "YMax": y_max,
        "Note": "dual_panel_frame_vs_payload",
        "Image": svg_path.name,
    }
