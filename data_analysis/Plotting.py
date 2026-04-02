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

        # Generate x-axis breaks (5 evenly spaced points to avoid overlapping labels)
        xbreaks = np.unique(np.linspace(minval, maxval, 5)).tolist()
        strbreaks = [round(x, 2) for x in xbreaks]  # Round to 2 decimal places for readability

        # List of statistics to plot
        selected_stats = ['mean', 'median', 'p50', 'p95', 'p99', 'ConnectionPercent', 'IterationTime']

        for stat in selected_stats:
            stat_plot = stat

            # Filter out null values for current statistic to avoid NaN in max/min calculations
            stat_series = tmpdf[stat].dropna()
            if stat_series.empty:
                print(f"Warning: No valid data for VariParam={varp}, Stat={stat}, skipping")
                continue

            # Calculate y-axis minimum value (scalar float - no astype() needed)
            minval_y = stat_series.min()

            # Calculate median values for Baseline=True/False (handle empty subsets)
            bl_false_stat = tmpdf[(tmpdf['Baseline'] == False)][stat].dropna()
            bl_true_stat = tmpdf[(tmpdf['Baseline'] == True)][stat].dropna()
            median_false = bl_false_stat.median() if not bl_false_stat.empty else 0
            median_true = bl_true_stat.median() if not bl_true_stat.empty else 0
            highmed = max(median_false, median_true)

            # Calculate y-axis maximum value (handle empty Baseline=False subset)
            maxval_y = bl_false_stat.max() if not bl_false_stat.empty else highmed

            # Adjust y-axis max if it's smaller than the higher median
            if maxval_y < highmed:
                maxval_y = maxval_y + highmed

            # Special handling for ConnectionPercent (force 0-100 range)
            if stat == 'ConnectionPercent':
                minval_y = 0
                maxval_y = 100
                stat_plot = 'ConnectionPercent_plot'
                tmpdf.loc[:, stat_plot] = tmpdf[stat] * 100  # Convert to percentage (safe assignment)

            # Extend y-axis range by 15% to add padding around data points
            if stat != 'ConnectionPercent':
                pad = (maxval_y - minval_y) * 0.15 if maxval_y != minval_y else max(1, abs(maxval_y) * 0.15)
                minval_y = minval_y - pad
                maxval_y = maxval_y + pad

            minval_y, maxval_y = _safe_limits(minval_y, maxval_y)

            plot_df = tmpdf.dropna(subset=[newcol, stat_plot]).copy()
            if plot_df.empty:
                continue

            # Prepare aggregated trends for cleaner readability (mean ± std)
            trend_df = (
                plot_df.groupby([newcol, 'Algorithm'], as_index=False)
                .agg(stat_mean=(stat_plot, 'mean'), stat_std=(stat_plot, 'std'))
            )
            trend_df['stat_std'] = trend_df['stat_std'].fillna(0)
            trend_df['ymin'] = trend_df['stat_mean'] - trend_df['stat_std']
            trend_df['ymax'] = trend_df['stat_mean'] + trend_df['stat_std']

            # Create scatter plot with plotnine
            meanplot = (
                ggplot(plot_df)  # Remove rows with null values for plotting
                + aes(x=newcol, y=stat_plot, color='Algorithm')
                + geom_point(alpha=0.55, size=1.8)  # Scatter plot points
                + geom_line(data=trend_df, mapping=aes(x=newcol, y='stat_mean', color='Algorithm'), size=1.0)
                + geom_ribbon(
                    data=trend_df,
                    mapping=aes(x=newcol, ymin='ymin', ymax='ymax', fill='Algorithm'),
                    alpha=0.15,
                    inherit_aes=False,
                )
                + labs(title=f"{varp} vs. {stat}", x=varp, y=stat)  # Plot titles/labels
                + scale_x_continuous(breaks=strbreaks, limits=[minval, maxval])  # X-axis scale
                + scale_y_continuous(limits=[minval_y, maxval_y])  # Y-axis scale
                + scale_color_manual(values=color_map)
                + scale_fill_manual(values=color_map)
                + theme_bw()
                + theme(
                    figure_size=(9, 5),
                    legend_position='top',
                    panel_grid_minor=element_blank(),
                )
            )

            # Generate unique filename with timestamp
            date_time = time.strftime("%Y%m%d_%H%M")
            file_name = f"{date_time}_{_safe_file_token(varp)}_vs_{_safe_file_token(stat)}.png"
            
            # Save plot to specified directory (300 DPI balances quality and file size)
            ggsave(meanplot, filename=file_name, path=plot_dir, dpi=300)

            # Print confirmation when debug level > 1
            if plvl > 1:
                print(f"Plot saved: {file_name}")

            note = "ok"
            if len(plot_df) < 6:
                note = "few_points"
            elif stat == 'ConnectionPercent' and (plot_df[stat_plot].max() > 100 or plot_df[stat_plot].min() < 0):
                note = "out_of_range_connection_percent"

            report_rows.append(
                {
                    'VariParam': varp,
                    'Stat': stat,
                    'Points': int(len(plot_df)),
                    'XMin': float(minval),
                    'XMax': float(maxval),
                    'YMin': float(minval_y),
                    'YMax': float(maxval_y),
                    'Note': note,
                    'Image': file_name,
                }
            )

        # Additional summary chart: compare p50/p95/p99 in a single figure.
        pct_cols = [c for c in ['p50', 'p95', 'p99'] if c in tmpdf.columns]
        if pct_cols:
            pct_df = tmpdf.dropna(subset=[newcol] + pct_cols).copy()
            if not pct_df.empty:
                long_df = pct_df.melt(
                    id_vars=[newcol, 'Algorithm'],
                    value_vars=pct_cols,
                    var_name='Percentile',
                    value_name='Latency',
                )
                long_df = long_df.dropna(subset=['Latency'])

                if not long_df.empty:
                    y_min = long_df['Latency'].min()
                    y_max = long_df['Latency'].max()
                    y_min, y_max = _safe_limits(y_min, y_max)

                    summary_plot = (
                        ggplot(long_df)
                        + aes(x=newcol, y='Latency', color='Algorithm', linetype='Percentile')
                        + geom_line(size=1.0)
                        + geom_point(alpha=0.7, size=1.8)
                        + labs(
                            title=f"{varp} vs. Percentile Latency (P50/P95/P99)",
                            x=varp,
                            y='Latency (s)',
                        )
                        + scale_x_continuous(breaks=strbreaks, limits=[minval, maxval])
                        + scale_y_continuous(limits=[y_min, y_max])
                        + scale_color_manual(values=color_map)
                        + theme_bw()
                        + theme(
                            figure_size=(10, 5.5),
                            legend_position='top',
                            panel_grid_minor=element_blank(),
                        )
                    )

                    date_time = time.strftime("%Y%m%d_%H%M")
                    summary_file = f"{date_time}_{_safe_file_token(varp)}_percentile_summary.png"
                    ggsave(summary_plot, filename=summary_file, path=plot_dir, dpi=300)

                    report_rows.append(
                        {
                            'VariParam': varp,
                            'Stat': 'percentile_summary',
                            'Points': int(len(long_df)),
                            'XMin': float(minval),
                            'XMax': float(maxval),
                            'YMin': float(y_min),
                            'YMax': float(y_max),
                            'Note': 'p50_p95_p99_combined',
                            'Image': summary_file,
                        }
                    )

    return pd.DataFrame(report_rows)