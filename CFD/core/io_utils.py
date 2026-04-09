"""
core/io_utils.py — File I/O utilities for AquaGuard

Functions:
  standardize_summary_df(df) — validate and normalise a case summary DataFrame
  save_csv(df, path, log)    — write DataFrame to CSV with optional logging
  save_json(data, path, log) — write dict to JSON with optional logging
  ensure_dir(path)           — mkdir -p
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

import pandas as pd


REQUIRED_SUMMARY_COLS = [
    'case_name',
    'direction',
    'net',
    'risk_status',
    'first_arrival_s',
    'total_risk_exposure_mass_seconds',
]


def standardize_summary_df(summary_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return summary_df with normalised column names and validate required fields.

    - Adds 'case_name' from 'direction' (or vice versa) when one is missing.
    - Raises KeyError if required columns are absent after normalisation.
    """
    if summary_df is None:
        raise ValueError("summary_df is None; cannot continue.")
    if not isinstance(summary_df, pd.DataFrame):
        summary_df = pd.DataFrame(summary_df)
    out = summary_df.copy()

    if 'case_name' not in out.columns and 'direction' in out.columns:
        out['case_name'] = out['direction']
    if 'direction' not in out.columns and 'case_name' in out.columns:
        out['direction'] = out['case_name']

    missing = [c for c in REQUIRED_SUMMARY_COLS if c not in out.columns]
    if missing:
        raise KeyError(
            "summary_df mangler nødvendige kolonner: "
            + ", ".join(missing)
            + f". Tilgjengelige kolonner: {list(out.columns)}"
        )
    return out


def save_csv(
    df: pd.DataFrame,
    path: Path,
    log_func: Optional[Callable[[str], None]] = None,
) -> Path:
    df.to_csv(path, index=False)
    if log_func:
        log_func(f"Lagrer CSV: {path}")
    return path


def save_json(
    data: dict,
    path: Path,
    log_func: Optional[Callable[[str], None]] = None,
) -> Path:
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    if log_func:
        log_func(f"Lagrer JSON: {path}")
    return path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
