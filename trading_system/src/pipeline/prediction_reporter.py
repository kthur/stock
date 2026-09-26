"""
prediction_reporter.py — Standardized Strategy & Ensemble Report Writer

Decouples file persistence, multi-market partitioning, and formatted prediction summaries
from pipeline execution logic.
"""

import os
import math
import logging
from typing import Optional, Union, List
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def get_target_markets_to_save(
    df: Optional[pd.DataFrame] = None,
    universe: Optional[pd.DataFrame] = None
) -> List[str]:
    """Return all unique market identifiers to save individual partitioned reports for."""
    markets = set()
    if df is not None and not df.empty and 'market' in df.columns:
        markets.update(df['market'].dropna().unique())
    if universe is not None and not universe.empty and 'market' in universe.columns:
        markets.update(universe['market'].dropna().unique())
    target_env = os.environ.get("INFERENCE_TARGET", "").strip().upper()
    if target_env:
        for t in target_env.split(','):
            t_clean = t.strip()
            if t_clean and t_clean not in ['ALL', 'CORE_5', 'ASIA_DEV', 'ASIA_EMG', 'COMMODITY']:
                markets.add(t_clean)
    if not markets:
        markets = {'KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000'}
    return sorted(str(m) for m in markets)


def slice_top_dataframe(
    df: Optional[pd.DataFrame],
    limit: Union[int, str, None]
) -> pd.DataFrame:
    """Slice DataFrame to top limit rows, or return all rows if limit is 'all' / None / <=0."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df
    if limit is None:
        return df
    if isinstance(limit, str) and limit.strip().lower() in ("all", "0", "-1", "none"):
        return df
    try:
        n = int(limit)
        return df.head(n) if n > 0 else df
    except (ValueError, TypeError):
        return df.head(100)


def save_strategy_predictions_report(
    df_strat: Optional[pd.DataFrame],
    score_col: str,
    title: str,
    output_filename: str,
    result_dir: str,
    universe: Optional[pd.DataFrame] = None,
    pred_limit: Union[int, str, None] = 100,
    score_header: str = "Score",
    header_width: int = 14,
    kst_now_str: Optional[str] = None
) -> Optional[str]:
    """
    Standardized report generation for individual alpha strategies.
    Writes both consolidated and per-market partitioned report files.
    """
    if df_strat is None or df_strat.empty or score_col not in df_strat.columns:
        return None

    if kst_now_str is None:
        kst_now_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')

    # Merge universe metadata for display
    if universe is not None and not universe.empty:
        if 'market' not in df_strat.columns and 'market' in universe.columns:
            merged = df_strat.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
        else:
            merged = df_strat.copy()
        if 'name' not in merged.columns and 'name' in universe.columns:
            merged = merged.merge(universe[['symbol', 'name']], on='symbol', how='left')
    else:
        merged = df_strat.copy()

    merged['symbol'] = merged['symbol'].astype(str)
    merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce')

    if merged[score_col].isna().all():
        logger.warning(f"[REPORT FALLBACK] Strategy '{title}' has all-NaN scores. Imputing baseline neutral score 0.50.")
        merged[score_col] = 0.50
    else:
        col_median = merged[score_col].median()
        fallback_val = col_median if (pd.notna(col_median) and np.isfinite(col_median)) else 0.50
        merged[score_col] = merged[score_col].fillna(fallback_val)

    merged = merged.sort_values(by=score_col, ascending=False)

    def _write_content(f_out, df_sub, market_label=None):
        f_out.write(f"=== {title} ===\n")
        f_out.write(f"Date: {kst_now_str}\n")
        f_out.write(f"Total symbols evaluated: {len(df_sub)}\n\n")
        f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{score_header:<{header_width}}\n")
        f_out.write("-" * (43 + header_width) + "\n")
        for rank, (_, row) in enumerate(slice_top_dataframe(df_sub, pred_limit).iterrows(), 1):
            name_str = str(row.get('name', 'Unknown'))[:16] if pd.notna(row.get('name')) else "Unknown"
            mkt_str = str(row.get('market', 'KRX'))
            sc_raw = float(row[score_col])
            sc_val = sc_raw * 100.0 if sc_raw <= 1.0 else sc_raw
            f_out.write(f"{rank:<5}{str(row['symbol']):<10}{name_str:<18}{mkt_str:<10}{sc_val:>{header_width-2}.1f}%\n")

    effective_dir = result_dir if result_dir else "."
    os.makedirs(effective_dir, exist_ok=True)
    main_path = os.path.join(effective_dir, output_filename)
    tmp_path = main_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        _write_content(f, merged)
    if os.path.exists(main_path):
        os.remove(main_path)
    os.rename(tmp_path, main_path)
    logger.info(f"Saved {title} ({len(merged)} symbols) to {main_path}")

    # Per-market partitioned files
    base_name = output_filename.replace(".txt", "")
    for _m in get_target_markets_to_save(df=merged, universe=universe):
        _m_df = merged[merged['market'] == _m]
        if _m_df.empty:
            continue
        m_path = os.path.join(effective_dir, f"{base_name}_{_m}.txt")
        m_tmp = m_path + ".tmp"
        with open(m_tmp, "w", encoding="utf-8") as _mf:
            _write_content(_mf, _m_df, market_label=_m)
        if os.path.exists(m_path):
            os.remove(m_path)
        os.rename(m_tmp, m_path)

    return main_path
