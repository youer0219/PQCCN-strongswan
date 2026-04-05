"""Utilities for identifying and excluding warmup rows."""

from __future__ import annotations

import pandas as pd

_TRUE_TOKENS = {"1", "true", "yes", "y", "on"}
_WARMUP_COLUMNS = ("ScenarioCase", "ScenarioNote", "VariParam", "FileName", "FullFilePath")


def _normalize_token(value: object) -> str:
    text = str(value).strip()
    text = text.strip("'\"").strip()
    return text.lower()


def build_warmup_mask(df: pd.DataFrame | None) -> pd.Series:
    """Return a boolean mask marking rows that represent warmup samples."""
    if df is None:
        return pd.Series(dtype=bool)
    if df.empty:
        return pd.Series(False, index=df.index, dtype=bool)

    mask = pd.Series(False, index=df.index, dtype=bool)

    if "IsWarmup" in df.columns:
        normalized = df["IsWarmup"].map(_normalize_token)
        mask |= normalized.isin(_TRUE_TOKENS)

    for column in _WARMUP_COLUMNS:
        if column not in df.columns:
            continue
        normalized = df[column].map(_normalize_token)
        mask |= normalized.str.contains("warmup", regex=False, na=False)

    return mask


def exclude_warmup_rows(df: pd.DataFrame | None) -> pd.DataFrame:
    """Return a copy of ``df`` with warmup-tagged rows removed."""
    if df is None:
        return pd.DataFrame()
    if df.empty:
        return df.copy()

    return df.loc[~build_warmup_mask(df)].copy()
