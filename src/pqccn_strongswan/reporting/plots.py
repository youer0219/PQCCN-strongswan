"""Chart orchestration entrypoint.

This module now delegates rendering to fixed-layout SVG summarizers:
1) matrix latency small-multiples and overhead trend charts
2) optional packet byte dual-panel benchmark chart
"""

from pathlib import Path

import pandas as pd

from ..processing.warmup import exclude_warmup_rows
from .matrix_svg import generate_matrix_svgs
from .packet_svg import generate_packet_bytes_from_dataframe


def PlotVariParam(RunLogStatsDF, plot_dir, plvl):
    """Generate plot SVGs from run statistics.
    
    Args:
        RunLogStatsDF: DataFrame with run statistics
        plot_dir: Output directory for generated plots
        plvl: Print level (deprecated, kept for backward compatibility)

    Returns:
        DataFrame with plot audit information
    """
    del plvl  # The new renderers are deterministic and do not branch by print level.

    filtered_df = exclude_warmup_rows(RunLogStatsDF)
    if filtered_df.empty:
        return pd.DataFrame()

    out_dir = Path(plot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    matrix_audit = generate_matrix_svgs(filtered_df, out_dir)
    if matrix_audit is not None and len(matrix_audit) > 0:
        rows.extend(matrix_audit.to_dict(orient="records"))

    packet_audit = generate_packet_bytes_from_dataframe(filtered_df, out_dir)
    if packet_audit is not None:
        rows.append(packet_audit)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
