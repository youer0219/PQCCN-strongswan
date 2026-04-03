"""Chart orchestration entrypoint.

This module now delegates rendering to fixed-layout SVG summarizers:
1) matrix latency small-multiples and overhead trend charts
2) optional packet byte dual-panel benchmark chart
"""

from pathlib import Path

import pandas as pd

from summarize_matrix_results import generate_matrix_svgs
from summarize_results import generate_packet_bytes_from_dataframe


def PlotVariParam(RunLogStatsDF, plot_dir, plvl):
    del plvl  # The new renderers are deterministic and do not branch by print level.

    out_dir = Path(plot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    matrix_audit = generate_matrix_svgs(RunLogStatsDF, out_dir)
    if matrix_audit is not None and len(matrix_audit) > 0:
        rows.extend(matrix_audit.to_dict(orient="records"))

    packet_audit = generate_packet_bytes_from_dataframe(RunLogStatsDF, out_dir)
    if packet_audit is not None:
        rows.append(packet_audit)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
