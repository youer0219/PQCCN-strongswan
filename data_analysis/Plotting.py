# Path: data_analysis/Plotting.py
# Plotting module: Contains functions to visualize the logfile dataframe (RunLogStatsDF)
# This module generates scatter plots for VariParam vs. key statistics (mean/median/ConnectionPercent/IterationTime)

import pandas as pd
import numpy as np
import time
from plotnine import *
import re


def PlotVariParam(RunLogStatsDF, plot_dir, plvl):
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

        # Extract numerical values from VariParam column (handle nulls and non-numeric strings)
        newcol = varp + 'val'  # Convert to string (no need for list)
        tmpdf[newcol] = tmpdf[varp].apply(
            lambda x: re.search(r'\d+', str(x)).group(0) if pd.notnull(x) and re.search(r'\d+', str(x)) else np.nan
        ).astype(float)

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

        # Generate x-axis breaks (10 evenly spaced points)
        xbreaks = np.linspace(minval, maxval, 10).tolist()
        strbreaks = [round(x, 2) for x in xbreaks]  # Round to 2 decimal places for readability

        # List of statistics to plot
        selected_stats = ['mean', 'median', 'ConnectionPercent', 'IterationTime']

        for stat in selected_stats:
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
                tmpdf.loc[:, stat] = tmpdf[stat] * 100  # Convert to percentage (safe assignment)

            # Extend y-axis range by 20% to add padding around data points
            minval_y = minval_y - (minval_y * 0.2)
            maxval_y = maxval_y + (maxval_y * 0.2)

            # Create scatter plot with plotnine
            meanplot = (
                ggplot(tmpdf.dropna(subset=[newcol, stat]))  # Remove rows with null values for plotting
                + aes(x=newcol, y=stat, color='Algorithm')
                + geom_point()  # Scatter plot points
                + labs(title=f"{varp} vs. {stat}", x=varp, y=stat)  # Plot titles/labels
                + scale_x_continuous(breaks=strbreaks, limits=[minval, maxval])  # X-axis scale
                + scale_y_continuous(limits=[minval_y, maxval_y])  # Y-axis scale
                + scale_color_manual(values=['#0077C8', '#E69F00'])  # Custom color palette
            )

            # Generate unique filename with timestamp
            date_time = time.strftime("%Y%m%d_%H%M")
            file_name = f"{date_time}_{varp}_vs_{stat}.png"
            
            # Save plot to specified directory (600 DPI for high resolution)
            ggsave(meanplot, filename=file_name, path=plot_dir, dpi=600)

            # Print confirmation when debug level > 1
            if plvl > 1:
                print(f"Plot saved: {file_name}")