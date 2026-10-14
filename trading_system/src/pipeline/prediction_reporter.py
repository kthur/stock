"""
prediction_reporter.py — Standardized Strategy & Ensemble Report Writer

Decouples file persistence, multi-market partitioning, and formatted prediction summaries
from pipeline execution logic.
"""

import os
import math
import logging
from typing import Optional, Union, List, Dict, Any, Tuple
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


def format_prediction_line(
    rank: int,
    symbol: str,
    name: str = "Unknown",
    market: str = "KRX",
    score: float = 0.0,
    header_width: int = 14,
    is_percentage: bool = True,
    annual_cagr: Optional[float] = None,
    cagr_header_width: int = 14,
) -> str:
    """Format a single prediction entry with aligned columns, symmetric score scaling, and optional realistic CAGR."""
    name_str = str(name)[:16] if (name is not None and pd.notna(name)) else "Unknown"
    mkt_str = str(market) if (market is not None and pd.notna(market)) else "KRX"
    sc_raw = float(score) if (score is not None and math.isfinite(float(score))) else 0.0
    if is_percentage:
        sc_val = sc_raw * 100.0 if abs(sc_raw) <= 1.0 else sc_raw
        sc_formatted = f"{sc_val:>{header_width-2}.1f}%"
    else:
        sc_formatted = f"{sc_raw:>{header_width-2}.2f}"

    if annual_cagr is not None and math.isfinite(float(annual_cagr)):
        cagr_raw = float(annual_cagr)
        cagr_val = cagr_raw * 100.0 if abs(cagr_raw) <= 1.0 else cagr_raw
        cagr_formatted = f"{cagr_val:>{cagr_header_width-2}.1f}%"
        return f"{rank:<5}{str(symbol):<10}{name_str:<18}{mkt_str:<10}{sc_formatted}{cagr_formatted}\n"

    return f"{rank:<5}{str(symbol):<10}{name_str:<18}{mkt_str:<10}{sc_formatted}\n"


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
    kst_now_str: Optional[str] = None,
    cagr_col: Optional[str] = None,
    cagr_header: str = "Realistic CAGR",
    cagr_header_width: int = 16,
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
        has_cagr = (cagr_col is not None and cagr_col in df_sub.columns)
        if has_cagr:
            f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{score_header:<{header_width}}{cagr_header:<{cagr_header_width}}\n")
            f_out.write("-" * (43 + header_width + cagr_header_width) + "\n")
        else:
            f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<10}{score_header:<{header_width}}\n")
            f_out.write("-" * (43 + header_width) + "\n")

        for rank, (_, row) in enumerate(slice_top_dataframe(df_sub, pred_limit).iterrows(), 1):
            cagr_raw_val = row.get(cagr_col) if has_cagr else None
            cagr_num = float(cagr_raw_val) if (cagr_raw_val is not None and pd.notna(cagr_raw_val) and math.isfinite(float(cagr_raw_val))) else None
            line = format_prediction_line(
                rank=rank,
                symbol=str(row['symbol']),
                name=row.get('name', 'Unknown'),
                market=row.get('market', 'KRX'),
                score=float(row[score_col]),
                header_width=header_width,
                is_percentage=True,
                annual_cagr=cagr_num,
                cagr_header_width=cagr_header_width,
            )
            f_out.write(line)

    effective_dir = result_dir if result_dir else "."
    os.makedirs(effective_dir, exist_ok=True)
    main_path = os.path.join(effective_dir, output_filename)
    tmp_path = main_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        _write_content(f, merged)
    # D4: Atomic file replace on Windows to eliminate WinError 32 file locking race conditions
    os.replace(tmp_path, main_path)
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
        os.replace(m_tmp, m_path)

    return main_path


def save_ensemble_predictions_report(
    df_ensemble: Optional[pd.DataFrame],
    title: str = "Ensemble Predictions",
    output_filename: str = "ensemble_predictions.txt",
    result_dir: str = "trading_system/result",
    universe: Optional[pd.DataFrame] = None,
    pred_limit: Union[int, str, None] = 100,
    score_col: str = "ensemble_score",
    exp_ret_col: str = "ensemble_expected_return",
    cagr_col: Optional[str] = "realistic_annualized_cagr",
    strategy_cols: Optional[List[Tuple[str, str, int]]] = None,
    weights_dict: Optional[Dict[str, float]] = None,
    kst_now_str: Optional[str] = None,
    include_cagr: bool = True,
) -> Optional[str]:
    """
    Feature F494 (Phase 104): Standardized report generation for multi-factor ensemble predictions.
    Writes both consolidated and per-market partitioned report files with
    optional realistic annualized CAGR alongside dimensionless alpha scores and 20D expected returns.
    """
    if df_ensemble is None or df_ensemble.empty or score_col not in df_ensemble.columns:
        return None

    if kst_now_str is None:
        kst_now_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')

    # Merge universe metadata for display
    if universe is not None and not universe.empty:
        if 'market' not in df_ensemble.columns and 'market' in universe.columns:
            merged = df_ensemble.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left')
        else:
            merged = df_ensemble.copy()
        if 'name' not in merged.columns and 'name' in universe.columns:
            merged = merged.merge(universe[['symbol', 'name']], on='symbol', how='left')
    else:
        merged = df_ensemble.copy()

    merged['symbol'] = merged['symbol'].astype(str)
    merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce').fillna(0.50)
    if exp_ret_col in merged.columns:
        merged[exp_ret_col] = pd.to_numeric(merged[exp_ret_col], errors='coerce').fillna(0.0)

    has_cagr = bool(include_cagr and cagr_col is not None and cagr_col in merged.columns)
    if has_cagr:
        merged[cagr_col] = pd.to_numeric(merged[cagr_col], errors='coerce').fillna(8.0)

    merged = merged.sort_values(by=score_col, ascending=False)

    # Strategy factor column definitions: (col_name, header_label, width)
    default_strategy_cols = [
        ('reg_score', 'Reg', 5),
        ('surge_score', 'Srg', 5),
        ('ll_score', 'L-L', 5),
        ('vcp_rule_score', 'VCP-R', 6),
        ('vcp_ml_score', 'VCP-M', 6),
        ('lstm_score', 'LSTM', 5),
        ('stat_arb_score', 'S-Arb', 6),
        ('sector_score', 'Sec-R', 6),
        ('rim_score', 'RIM', 5),
        ('event_score', 'Event', 6),
        ('mq_score', 'MQ', 5),
        ('iv_skew_score', 'IV-Sk', 6),
        ('order_flow_score', 'Flow', 5),
        ('reversal_score', 'Rev', 5),
        ('arm_score', 'ARM', 5),
        ('card_score', 'CARD', 6),
        ('latr_score', 'LATR', 5),
        ('inst_foreign_sector_score', 'IFS', 5),
        ('supply_chain_score', 'Supply', 7),
        ('sentiment_score', 'NLP', 5),
        ('factor_neutralized_score', 'Neutral', 8),
        ('vol_target_score', 'Vol-T', 6),
        ('microstructure_score', 'Micro', 6),
        ('accruals_quality_score', 'Accrual', 8),
        ('short_squeeze_score', 'S-Sq', 5),
        ('valueup_catalyst_score', 'ValueUp', 8),
        ('trend_efficiency_score', 'TrendEff', 9),
        ('gamma_squeeze_score', 'GammaSq', 8),
        ('insider_buying_score', 'Insider', 8),
        ('darkpool_score', 'Darkpool', 9),
        ('earnings_tone_drift_score', 'ToneDrift', 10),
        ('cross_asset_spillover_score', 'Spillover', 10),
        ('supply_chain_gnn_score', 'SC-GNN', 8),
        ('range_expansion_score', 'RangeExp', 9),
        ('dual_correction_score', 'DualCorr', 9),
        ('index_rebalance_score', 'IdxRebal', 9),
        ('overnight_gap_score', 'OverGap', 8),
    ]
    active_strat_cols = strategy_cols if strategy_cols is not None else default_strategy_cols

    def _format_strat_val(val, width):
        if val is None or pd.isna(val):
            return f"{'-':>{width}}"
        v = float(val)
        pct = v * 100.0 if abs(v) <= 1.0 else v
        return f"{pct:>{width}.1f}%"

    def _write_ensemble_content(f_out, df_sub, market_label=None):
        f_out.write(f"=== {title} ===\n")
        f_out.write(f"Date: {kst_now_str}\n")
        if market_label:
            f_out.write(f"Market: {market_label}\n")
        f_out.write(f"Total symbols evaluated: {len(df_sub)}\n\n")

        # Top section weights if provided
        if weights_dict:
            f_out.write("--- Dynamic Strategy Weights ---\n")
            for strat_k, strat_w in weights_dict.items():
                w_pct = float(strat_w) * 100.0 if abs(float(strat_w)) <= 1.0 else float(strat_w)
                f_out.write(f"  {strat_k:<36}: {w_pct:.1f}%\n")
            f_out.write("\n")

        f_out.write("--- Top Recommendations ---\n")
        header = f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Ens Score':<12}{'Exp Ret(20D)':<14}"
        if has_cagr:
            header += f"{'Real CAGR':<12}"
        for _, h_label, w in active_strat_cols:
            header += f"{h_label:<{w}}"
        header += "\n"
        f_out.write(header)
        f_out.write("-" * max(len(header.rstrip()), 80) + "\n")

        for rank, (_, row) in enumerate(slice_top_dataframe(df_sub, pred_limit).iterrows(), 1):
            name_val = row.get('name', 'Unknown')
            name_str = str(name_val)[:16] if (name_val is not None and pd.notna(name_val)) else "Unknown"
            sc_raw = float(row[score_col]) if pd.notna(row[score_col]) else 0.50
            sc_val = sc_raw * 100.0 if abs(sc_raw) <= 1.0 else sc_raw
            ret_raw = float(row.get(exp_ret_col, 0.0)) if pd.notna(row.get(exp_ret_col, 0.0)) else 0.0

            line = f"{rank:<5}{str(row['symbol']):<10}{name_str:<18}{sc_val:>10.1f}%{ret_raw:>12.2f}%"
            if has_cagr:
                cagr_raw = float(row.get(cagr_col, 8.0)) if pd.notna(row.get(cagr_col, 8.0)) else 8.0
                cagr_val = cagr_raw * 100.0 if abs(cagr_raw) <= 1.0 else cagr_raw
                line += f"{cagr_val:>10.1f}%"

            for c_name, _, w in active_strat_cols:
                v = row.get(c_name)
                # Fallback alternative column names if needed
                if v is None and c_name == 'factor_neutralized_score':
                    v = row.get('neutralized_score')
                elif v is None and c_name == 'range_expansion_score':
                    v = row.get('range_expansion_breakout_score')
                elif v is None and c_name == 'overnight_gap_score':
                    v = row.get('overnight_gap_reversal_score')
                line += _format_strat_val(v, w)
            line += "\n"
            f_out.write(line)

    effective_dir = result_dir if result_dir else "."
    os.makedirs(effective_dir, exist_ok=True)
    main_path = os.path.join(effective_dir, output_filename)
    tmp_path = main_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        _write_ensemble_content(f, merged)
    os.replace(tmp_path, main_path)
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
            _write_ensemble_content(_mf, _m_df, market_label=_m)
        os.replace(m_tmp, m_path)

    return main_path

