# Path: data_analysis/Plotting.py
# Plotting module: Contains functions to visualize the logfile dataframe (RunLogStatsDF)
# This module generates scatter plots for VariParam vs. key statistics (mean/median/ConnectionPercent/IterationTime)

import pandas as pd
import numpy as np
import time
from plotnine import *
import re
import os


ALGO_COLORS = [
    '#1E88E5',
    '#E07A1F',
    '#2E7D32',
    '#8E24AA',
    '#D81B60',
    '#00897B',
]


def _safe_file_token(value):
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value)).strip("_")


def _extract_numeric(value):
    m = re.search(r"[-+]?\d*\.?\d+", str(value))
    return float(m.group(0)) if m else np.nan


def _safe_limits(min_val, max_val):
    if pd.isna(min_val) or pd.isna(max_val):
        return (0, 1)
    if min_val == max_val:
        pad = 1 if min_val == 0 else abs(min_val) * 0.1
        return (min_val - pad, max_val + pad)
    return (min_val, max_val)


def _format_param_value(value):
    if pd.isna(value):
        return ''
    try:
        numeric = float(value)
    except Exception:  # noqa: BLE001
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f'{numeric:.3f}'.rstrip('0').rstrip('.')


def _short_group_label(value):
    text = str(value or '').strip()
    if '__' in text:
        return text.split('__', 1)[0]
    return text


def _build_case_label(row, x_col):
    case = str(row.get('ScenarioCase', '') or '').strip()
    parts = []
    if case:
        parts.append(case)
    else:
        parts.append(_format_param_value(row.get(x_col, '')))

    param_bits = []
    for param_col in ['delay', 'loss', 'rate']:
        if param_col in row.index and pd.notna(row.get(param_col)):
            val = row.get(param_col)
            try:
                numeric_val = float(val)
                if numeric_val > 0:
                    param_bits.append(f"{param_col}={_format_param_value(val)}")
            except (ValueError, TypeError):
                param_bits.append(f"{param_col}={str(val)}")
    if param_bits:
        parts.append(' / '.join(param_bits))
    return '\n'.join(parts)


def _build_plot_context(df, x_col):
    groups = [x for x in df.get('ScenarioGroup', pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]
    cases = [x for x in df.get('ScenarioCase', pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if x]

    title_context = ', '.join(sorted({_short_group_label(g) for g in groups if g}))
    subtitle_bits = []
    if cases and 'ScenarioCase' in df.columns:
        for case in sorted(cases):
            case_rows = df[df['ScenarioCase'].astype(str) == case]
            if not case_rows.empty:
                subtitle_bits.append(_build_case_label(case_rows.iloc[0], x_col))

    label_map = {}
    if 'ScenarioCase' in df.columns:
        for x_value, group_df in df.groupby(x_col, dropna=False):
            if not group_df.empty:
                label_map[x_value] = str(group_df.iloc[0].get('ScenarioCase', '') or '').strip() or _format_param_value(x_value)

    return title_context, '\n'.join(subtitle_bits), label_map


def _build_case_axis_label(row, x_col):
    case = str(row.get('ScenarioCase', '') or '').strip()
    if case:
        return case
    return _format_param_value(row.get(x_col, ''))


def PlotVariParam(RunLogStatsDF, plot_dir, plvl):
    os.makedirs(plot_dir, exist_ok=True)
    report_rows = []

    algos = [x for x in RunLogStatsDF.get('Algorithm', pd.Series(dtype=str)).dropna().astype(str).unique().tolist()]
    color_map = {algo: ALGO_COLORS[i % len(ALGO_COLORS)] for i, algo in enumerate(sorted(algos))}

    # Iterate through all unique VariParam values (filter out null values)
    for varp in RunLogStatsDF['VariParam'].dropna().unique().tolist():
        print(varp)
        if plvl > 2:
            # Print detailed values for current VariParam when debug level > 2
            print(RunLogStatsDF[varp][(RunLogStatsDF['VariParam'] == varp)])

        # Filter data for current VariParam (use copy() to avoid SettingWithCopyWarning)
        tmpdf = RunLogStatsDF[(RunLogStatsDF['VariParam'] == varp)].copy()

        # Assign legend labels based on Baseline flag (safe assignment with .loc)
        tmpdf.loc[tmpdf['Baseline'] == True, 'Legend'] = 'Diffie-Helman'
        tmpdf.loc[tmpdf['Baseline'] == False, 'Legend'] = 'Post-Quantum'

        # Extract numerical values from VariParam column (supports ints/floats in strings)
        newcol = varp + 'val'  # Convert to string (no need for list)
        tmpdf[newcol] = tmpdf[varp].apply(_extract_numeric).astype(float)

        # Sort dataframe by numerical values and remove rows with null values in newcol
        tmpdf = tmpdf.sort_values(newcol).dropna(subset=[newcol])

        # Skip plotting if no valid data for current VariParam
        if tmpdf.empty:
            print(f"Warning: No valid data for VariParam={varp}, skipping plot generation")
            continue

        # Calculate x-axis range (no need for astype() - scalar float value)
        minval = tmpdf[newcol].min()
        maxval = tmpdf[newcol].max()
        minval, maxval = _safe_limits(minval, maxval)

        plot_context, plot_subtitle, label_map = _build_plot_context(tmpdf, newcol)

        # Prefer exact sweep values when the sweep is small so labels can show concrete cases.
        unique_x = sorted(tmpdf[newcol].dropna().unique().tolist())
        if len(unique_x) <= 8:
            xbreaks = unique_x
        else:
            xbreaks = np.unique(np.linspace(minval, maxval, 5)).tolist()

        xlabels = [label_map.get(x, _format_param_value(x)) for x in xbreaks]



        plot_df = tmpdf.dropna(subset=[newcol]).copy()
        if plot_df.empty:
            continue

        # Keep configurations together in one axis instead of splitting into multiple images.
        plot_df['CaseLabel'] = plot_df.apply(lambda r: _build_case_axis_label(r, newcol), axis=1)

        # Chart 1: only percentile metrics (p50/p95/p99) in one image.
        pct_metrics = [c for c in ['p50', 'p95', 'p99'] if c in plot_df.columns]
        if pct_metrics:
            pct_long = plot_df.melt(
                id_vars=['CaseLabel', 'Algorithm'],
                value_vars=pct_metrics,
                var_name='Metric',
                value_name='Value',
            ).dropna(subset=['Value'])

            if not pct_long.empty:
                pct_agg = (
                    pct_long.groupby(['CaseLabel', 'Algorithm', 'Metric'], as_index=False)
                    .agg(Value=('Value', 'mean'))
                )
                pct_agg['CaseMetric'] = pct_agg['CaseLabel'].astype(str) + ' | ' + pct_agg['Metric'].str.upper()
                pct_agg['CaseMetric'] = pd.Categorical(
                    pct_agg['CaseMetric'],
                    categories=[
                        f"{case} | {metric.upper()}"
                        for case in plot_df['CaseLabel'].dropna().astype(str).unique().tolist()
                        for metric in pct_metrics
                    ],
                    ordered=True,
                )

                pct_plot = (
                    ggplot(pct_agg)
                    + aes(x='CaseMetric', y='Value', fill='Algorithm')
                    + geom_col(position=position_dodge(width=0.8), width=0.72, alpha=0.9)
                    + labs(
                        title=f"{plot_context + ' | ' if plot_context else ''}{varp} P50/P95/P99",
                        subtitle=plot_subtitle,
                        x='Configuration | Percentile',
                        y='Latency (s)',
                    )
                    + scale_fill_manual(values=color_map)
                    + theme_bw()
                    + theme(
                        figure_size=(13, 5.5),
                        legend_position='top',
                        panel_grid_minor=element_blank(),
                        axis_text_x=element_text(rotation=35, ha='right'),
                    )
                )

                date_time = time.strftime("%Y%m%d_%H%M")
                pct_file = f"{date_time}_{_safe_file_token(varp)}_percentiles_summary.png"
                ggsave(pct_plot, filename=pct_file, path=plot_dir, dpi=300)

                report_rows.append(
                    {
                        'VariParam': varp,
                        'Stat': 'percentiles',
                        'Points': int(len(pct_agg)),
                        'XMin': 0.0,
                        'XMax': 0.0,
                        'YMin': float(pct_agg['Value'].min()),
                        'YMax': float(pct_agg['Value'].max()),
                        'Note': 'p50_p95_p99_only',
                        'Image': pct_file,
                    }
                )

        # Chart 2: other key metrics, excluding mean.
        other_metrics = [c for c in ['median', 'ConnectionPercent', 'IterationTime'] if c in plot_df.columns]
        if other_metrics:
            other_df = plot_df.copy()
            if 'ConnectionPercent' in other_df.columns:
                other_df['ConnectionPercent'] = other_df['ConnectionPercent'] * 100

            other_long = other_df.melt(
                id_vars=['CaseLabel', 'Algorithm'],
                value_vars=other_metrics,
                var_name='Metric',
                value_name='Value',
            ).dropna(subset=['Value'])

            if not other_long.empty:
                other_agg = (
                    other_long.groupby(['CaseLabel', 'Algorithm', 'Metric'], as_index=False)
                    .agg(Value=('Value', 'mean'))
                )
                other_agg['CaseMetric'] = other_agg['CaseLabel'].astype(str) + ' | ' + other_agg['Metric']
                other_agg['CaseMetric'] = pd.Categorical(
                    other_agg['CaseMetric'],
                    categories=[
                        f"{case} | {metric}"
                        for case in other_df['CaseLabel'].dropna().astype(str).unique().tolist()
                        for metric in other_metrics
                    ],
                    ordered=True,
                )

                other_plot = (
                    ggplot(other_agg)
                    + aes(x='CaseMetric', y='Value', fill='Algorithm')
                    + geom_col(position=position_dodge(width=0.8), width=0.72, alpha=0.9)
                    + labs(
                        title=f"{plot_context + ' | ' if plot_context else ''}{varp} Other Metrics",
                        subtitle=plot_subtitle,
                        x='Configuration | Metric',
                        y='Value',
                    )
                    + scale_fill_manual(values=color_map)
                    + theme_bw()
                    + theme(
                        figure_size=(13, 5.5),
                        legend_position='top',
                        panel_grid_minor=element_blank(),
                        axis_text_x=element_text(rotation=35, ha='right'),
                    )
                )

                date_time = time.strftime("%Y%m%d_%H%M")
                other_file = f"{date_time}_{_safe_file_token(varp)}_other_metrics_summary.png"
                ggsave(other_plot, filename=other_file, path=plot_dir, dpi=300)

                report_rows.append(
                    {
                        'VariParam': varp,
                        'Stat': 'other_metrics',
                        'Points': int(len(other_agg)),
                        'XMin': 0.0,
                        'XMax': 0.0,
                        'YMin': float(other_agg['Value'].min()),
                        'YMax': float(other_agg['Value'].max()),
                        'Note': 'median_connection_iteration',
                        'Image': other_file,
                    }
                )

    return pd.DataFrame(report_rows)
