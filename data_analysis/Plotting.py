# Path: data_analysis/Plotting.py
# Plotting module: Contains functions to visualize the logfile dataframe (RunLogStatsDF)
# This module generates scatter plots for VariParam vs. key statistics (mean/median/ConnectionPercent/IterationTime)

import pandas as pd
import numpy as np
import time
from plotnine import *
import re
import os


def _safe_file_token(value):
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value)).strip("_")


def _extract_numeric(value):
    m = re.search(r"[-+]?\d*\.?\d+", str(value))
    return float(m.group(0)) if m else np.nan


def PlotVariParam(RunLogStatsDF, plot_dir, plvl):
    os.makedirs(plot_dir, exist_ok=True)

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
        # Handle case where Baseline=False has no data
        baseline_false_df = tmpdf[tmpdf['Baseline'] == False]
        maxval = baseline_false_df[newcol].max() if not baseline_false_df.empty else minval

        # Generate x-axis breaks (5 evenly spaced points to avoid overlapping labels)
        xbreaks = np.linspace(minval, maxval, 5).tolist()
        strbreaks = [round(x, 2) for x in xbreaks]  # Round to 2 decimal places for readability

        # List of statistics to plot
        selected_stats = ['mean', 'median', 'ConnectionPercent', 'IterationTime']

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
            pad = (maxval_y - minval_y) * 0.15 if maxval_y != minval_y else max(1, abs(maxval_y) * 0.15)
            minval_y = minval_y - pad
            maxval_y = maxval_y + pad

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
                + scale_color_manual(values=['#1E88E5', '#E07A1F'])
                + scale_fill_manual(values=['#1E88E5', '#E07A1F'])
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