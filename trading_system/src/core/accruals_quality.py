"""
trading_system/src/core/accruals_quality.py
Strategy #24: Accruals Quality Anomaly Engine.
Evaluates earnings quality by contrasting Net Income against Operating Cash Flow (OCF)
relative to Total Assets (Sloan 1996 Accrual Anomaly).
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategyEngine

logger = logging.getLogger(__name__)


from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="accruals_quality",
        display_name="Accruals Quality Anomaly",
        score_column="accruals_quality_score",
        category="factor",
        output_file="accruals_quality_predictions.txt",
        requires_fundamentals=True,
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.06, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.02, "BULL_LOW_VOL": 0.03
        },
    )
)
class AccrualsQualityEngine(BaseStrategyEngine):
    """
    Computes Accruals Quality Score [0.0, 1.0] for stocks.
    High Score = High Operating Cash Flow relative to Net Income (sustainable earnings).
    Low Score = Earnings inflated by non-cash working capital accruals (accounting risk).
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        symbols = list(prices_dict.keys()) if prices_dict else []
        return self.calculate_scores(symbols, features_df=fundamentals_dict, prices_dict=prices_dict)

    def calculate_scores(
        self,
        symbols: list,
        features_df: Optional[Any] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None
    ) -> pd.DataFrame:
        """
        Computes Accruals Quality Score per symbol.
        Returns DataFrame with ['symbol', 'accruals_quality_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'accruals_quality_score'])


        # Build lookup table from features_df
        fund_map = {}
        if features_df is not None:
            if isinstance(features_df, dict):
                for sym, df_item in features_df.items():
                    if isinstance(df_item, pd.DataFrame) and not df_item.empty:
                        fund_map[str(sym)] = df_item.iloc[-1].to_dict()
                    elif isinstance(df_item, dict):
                        fund_map[str(sym)] = df_item
            elif isinstance(features_df, pd.DataFrame) and not features_df.empty:
                if 'symbol' in features_df.columns:
                    deduped = features_df.drop_duplicates(subset=['symbol'], keep='last')
                    fund_map = deduped.set_index('symbol').to_dict(orient='index')

        sym_strs = [str(s) for s in symbols]

        def _get_p_df(p_dict, *keys):
            if not p_dict or not isinstance(p_dict, dict):
                return None
            for k in keys:
                if k is not None and k in p_dict:
                    return p_dict[k]
            return None

        def _compute_price_flow_proxy(sym_str: str) -> float:
            if not prices_dict or not isinstance(prices_dict, dict):
                return np.nan
            p_df = _get_p_df(prices_dict, sym_str, sym_str.zfill(6), sym_str.split('.')[0])
            if p_df is None or not isinstance(p_df, pd.DataFrame) or len(p_df) < 5:
                return np.nan
            c_col = 'Close' if 'Close' in p_df.columns else ('close' if 'close' in p_df.columns else None)
            if not c_col:
                return np.nan
            c_s = p_df[c_col].dropna().astype(float)
            if len(c_s) < 5:
                return np.nan
            n_bars = min(len(c_s), 20)
            tail_df = p_df.iloc[-n_bars:]
            c_tail = tail_df[c_col].astype(float)
            v_col = 'Volume' if 'Volume' in tail_df.columns else ('volume' if 'volume' in tail_df.columns else None)
            v_tail = tail_df[v_col].astype(float) if v_col else pd.Series(1.0, index=tail_df.index)
            h_col = 'High' if 'High' in tail_df.columns else ('high' if 'high' in tail_df.columns else None)
            l_col = 'Low' if 'Low' in tail_df.columns else ('low' if 'low' in tail_df.columns else None)
            h_tail = tail_df[h_col].astype(float) if h_col else c_tail
            l_tail = tail_df[l_col].astype(float) if l_col else c_tail

            hl_diff = h_tail - l_tail
            mfm = np.where(hl_diff > 1e-5, ((c_tail - l_tail) - (h_tail - c_tail)) / hl_diff, np.sign(c_tail.diff().fillna(0.0)))
            mfv = mfm * v_tail
            cmf = float(mfv.sum() / max(v_tail.sum(), 1e-5))
            cmf = float(np.clip(cmf, -1.0, 1.0))

            c_arr = c_tail.to_numpy()
            net_change = abs(c_arr[-1] - c_arr[0])
            total_path = np.sum(np.abs(np.diff(c_arr)))
            ker = float(net_change / max(total_path, 1e-5))
            ker = float(np.clip(ker, 0.0, 1.0))

            rets = np.diff(c_arr) / np.maximum(c_arr[:-1], 1e-5)
            vol20 = float(np.std(rets) * np.sqrt(252)) if len(rets) > 1 else 0.20

            raw_proxy = 0.50 + 0.25 * cmf + 0.20 * ker - 0.20 * min(vol20, 1.0)
            return float(np.clip(raw_proxy, 0.05, 0.95))

        if not fund_map:
            if prices_dict is not None and isinstance(prices_dict, dict) and bool(prices_dict):
                if len(sym_strs) == 1:
                    return pd.DataFrame({'symbol': sym_strs, 'accruals_quality_score': [0.50]})
                proxy_vals = [_compute_price_flow_proxy(s) for s in sym_strs]
                df_acc = pd.DataFrame({'symbol': sym_strs, 'accruals_quality_score': proxy_vals})
                val_mask = df_acc['accruals_quality_score'].notna()
                if val_mask.sum() > 1:
                    df_acc.loc[val_mask, 'accruals_quality_score'] = df_acc.loc[val_mask, 'accruals_quality_score'].rank(pct=True).clip(0.05, 0.95)
                return df_acc[['symbol', 'accruals_quality_score']]
            else:
                df_acc = pd.DataFrame({'symbol': sym_strs, 'accruals_quality_score': np.nan})
                return df_acc[['symbol', 'accruals_quality_score']]

        rows = []
        for sym_str in sym_strs:
            row = fund_map.get(sym_str, fund_map.get(sym_str.zfill(6), {}))
            rows.append(row)

        df_rows = pd.DataFrame(rows, index=sym_strs)

        net_inc = pd.to_numeric(
            df_rows.get('net_income', df_rows.get('net_income_y', df_rows.get('net_income_x', df_rows.get('net_profit', pd.Series(np.nan, index=sym_strs))))),
            errors='coerce'
        )
        ocf = pd.to_numeric(
            df_rows.get('operating_cash_flow', df_rows.get('ocf', df_rows.get('cash_flow_operating', pd.Series(np.nan, index=sym_strs)))),
            errors='coerce'
        )

        # Balance Sheet Accruals fallback if real OCF is missing but operating items are present
        missing_ocf_mask = ocf.isna() & net_inc.notna()
        if np.any(missing_ocf_mask):
            ca_change = pd.to_numeric(df_rows.get('current_assets_change', pd.Series(0.0, index=sym_strs)), errors='coerce').fillna(0.0)
            cl_change = pd.to_numeric(df_rows.get('current_liabilities_change', pd.Series(0.0, index=sym_strs)), errors='coerce').fillna(0.0)
            deprec = pd.to_numeric(df_rows.get('depreciation', pd.Series(0.0, index=sym_strs)), errors='coerce').fillna(0.0)
            op_inc = pd.to_numeric(
                df_rows.get('operating_income', df_rows.get('operating_income_y', df_rows.get('operating_income_x', df_rows.get('ebit', pd.Series(np.nan, index=sym_strs))))),
                errors='coerce'
            )

            # Traditional Balance Sheet Accruals OCF proxy: OCF ≈ Operating Income + Depreciation - ΔWorking Capital
            wc_change = ca_change - cl_change
            bs_ocf_est = op_inc + deprec - wc_change
            ocf = pd.Series(np.where(missing_ocf_mask & op_inc.notna(), bs_ocf_est, ocf), index=sym_strs)

        assets = pd.to_numeric(
            df_rows.get('total_assets', df_rows.get('assets', df_rows.get('book_value', df_rows.get('book_value_y', df_rows.get('book_value_x', pd.Series(np.nan, index=sym_strs)))))),
            errors='coerce'
        )

        valid_mask = net_inc.notna() & ocf.notna()
        proxy_denom = np.maximum(np.abs(net_inc) + np.abs(ocf), 1e-4) * 3.0
        raw_denom = np.where(assets.notna() & (assets > 0), assets, proxy_denom)
        raw_accrual = np.where(valid_mask & pd.notna(raw_denom), (net_inc - ocf) / np.maximum(raw_denom, 1e-5), np.nan)
        accrual_ratio = np.where(np.isfinite(raw_accrual), np.clip(raw_accrual, -5.0, 5.0), np.nan)

        # Cash conversion booster: OCF > Net Income significantly
        raw_conversion = np.where(valid_mask & (net_inc > 0), ocf / np.maximum(net_inc, 1e-5), 1.0)
        cash_conversion = np.where(np.isfinite(raw_conversion), np.clip(raw_conversion, 0.0, 10.0), 1.0)
        conversion_bonus = np.where(cash_conversion > 1.25, 0.05, 0.0)

        df_acc = pd.DataFrame({'symbol': sym_strs, 'accrual_ratio': accrual_ratio, 'conversion_bonus': conversion_bonus})
        valid_mask = df_acc['accrual_ratio'].notna() & np.isfinite(df_acc['accrual_ratio'])

        if valid_mask.sum() > 1:
            # Rank score: inverted because lower accrual_ratio -> higher earnings quality
            # Percentile rank: 1 - percentile_rank(accrual_ratio)
            ranks = df_acc.loc[valid_mask, 'accrual_ratio'].rank(pct=True, ascending=True).clip(0.02, 0.98)
            base_score = (1.0 - ranks + df_acc.loc[valid_mask, 'conversion_bonus']).clip(0.05, 0.95)
            # Accruals Quality Alpha Boost for top 15% high-cashflow sustainable earnings stocks
            high_quality_mask = base_score >= 0.85
            enhanced_score = np.where(high_quality_mask, (base_score * 1.08).clip(0.05, 0.98), base_score)
            # Distress check: Cash-burning loss-making firms cannot receive high accruals quality alpha
            net_arr = net_inc.to_numpy()
            ocf_arr = ocf.to_numpy()
            is_distressed = ((net_arr < 0) & (ocf_arr < 0))[valid_mask.to_numpy()]
            enhanced_score = np.where(is_distressed, np.minimum(0.30, enhanced_score), enhanced_score)
            df_acc.loc[valid_mask, 'accruals_quality_score'] = enhanced_score
        elif valid_mask.sum() == 1:
            bonus = float(df_acc.loc[valid_mask, 'conversion_bonus'].iloc[0])
            df_acc.loc[valid_mask, 'accruals_quality_score'] = min(0.50 + bonus, 0.95)
        else:
            df_acc['accruals_quality_score'] = np.nan

        # For remaining missing rows, compute price flow proxy if prices_dict is provided
        missing_scores = df_acc['accruals_quality_score'].isna()
        if missing_scores.any() and prices_dict is not None and isinstance(prices_dict, dict) and bool(prices_dict):
            for idx in df_acc[missing_scores].index:
                s = str(df_acc.loc[idx, 'symbol'])
                px_val = _compute_price_flow_proxy(s)
                if pd.notna(px_val):
                    df_acc.loc[idx, 'accruals_quality_score'] = px_val

        df_acc['accruals_quality_score'] = df_acc['accruals_quality_score'].astype(float)

        return df_acc[['symbol', 'accruals_quality_score']]
