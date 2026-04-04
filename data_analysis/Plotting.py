"""Chart orchestration entrypoint.

This module now delegates rendering to fixed-layout SVG summarizers:
1) matrix latency small-multiples and overhead trend charts
2) optional packet byte dual-panel benchmark chart
"""

from pathlib import Path

import pandas as pd

from summarize_matrix_results import generate_matrix_svgs
from summarize_results import generate_packet_bytes_from_dataframe


def PlotVariParam(RunLogStatsDF, plot_dir, plvl, include_warmup=False):
    """Generate plot SVGs from run statistics.
    
    Args:
        RunLogStatsDF: DataFrame with run statistics
        plot_dir: Output directory for generated plots
        plvl: Print level (deprecated, kept for backward compatibility)
        include_warmup: If False (default), filter out warmup data. If True, include warmup data.
    
    Returns:
        DataFrame with plot audit information
    """
    del plvl  # The new renderers are deterministic and do not branch by print level.

    # Filter out warmup data unless explicitly requested
    data_to_plot = RunLogStatsDF
    if not include_warmup:
        data_to_plot = _filter_warmup_data(RunLogStatsDF)

    out_dir = Path(plot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    matrix_audit = generate_matrix_svgs(data_to_plot, out_dir)
    if matrix_audit is not None and len(matrix_audit) > 0:
        rows.extend(matrix_audit.to_dict(orient="records"))

    packet_audit = generate_packet_bytes_from_dataframe(data_to_plot, out_dir)
    if packet_audit is not None:
        rows.append(packet_audit)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def _filter_warmup_data(df):
    """Filter out warmup data from DataFrame.
    
    Returns a copy of the DataFrame with warmup rows removed.
    Warmup data is identified by either:
    - IsWarmup column set to True/1/yes
    - ScenarioCase containing 'warmup'
    """
    if df is None or df.empty:
        return df.copy()
    
    result = df.copy()
    
    # Filter by IsWarmup column if it exists
    if 'IsWarmup' in result.columns:
        warmup_mask = result['IsWarmup'].fillna('0').astype(str).str.strip().str.lower().isin({'1', 'true', 'yes'})
        result = result.loc[~warmup_mask].copy()
    
    # Also filter by ScenarioCase if it contains 'warmup'
    if 'ScenarioCase' in result.columns:
        scenario_mask = result['ScenarioCase'].fillna('').astype(str).str.lower().str.contains('warmup', regex=False)
        result = result.loc[~scenario_mask].copy()
    
    return result
