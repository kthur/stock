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
        
        # If fund_map is missing or empty, compute price-volume cashflow proxy
        if not fund_map:
            scores = {}
            if prices_dict:
                for sym_str in sym_strs:
                    p_df = prices_dict.get(sym_str, prices_dict.get(sym_str.zfill(6)))
                    if isinstance(p_df, pd.DataFrame) and len(p_df) >= 10:
                        c_col = 'Close' if 'Close' in p_df.columns else ('close' if 'close' in p_df.columns else None)
                        v_col = 'Volume' if 'Volume' in p_df.columns else ('volume' if 'volume' in p_df.columns else None)
                        if c_col and v_col:
                            ret = p_df[c_col].pct_change().tail(20).fillna(0.0)
                            vol = p_df[v_col].tail(20).fillna(0.0)
                            pos_flow = float(np.where(ret > 0, ret * vol, 0.0).sum())
                            tot_flow = float((np.abs(ret) * vol).sum())
                            scores[sym_str] = float(pos_flow / tot_flow) if tot_flow > 0 else 0.50
                        else:
                            scores[sym_str] = 0.50
                    else:
                        scores[sym_str] = 0.50
            else:
                for sym_str in sym_strs:
                    scores[sym_str] = 0.50
            
            df_acc = pd.DataFrame(list(scores.items()), columns=['symbol', 'raw_score'])
            if len(df_acc) > 1:
                df_acc['accruals_quality_score'] = df_acc['raw_score'].rank(pct=True).clip(0.05, 0.95)
            else:
                df_acc['accruals_quality_score'] = 0.50
            return df_acc[['symbol', 'accruals_quality_score']]

        rows = []
        for sym_str in sym_strs:
            row = fund_map.get(sym_str, fund_map.get(sym_str.zfill(6), {}))
            rows.append(row)

        df_rows = pd.DataFrame(rows, index=sym_strs)

        net_inc = pd.to_numeric(
            df_rows.get('net_income', df_rows.get('net_profit', pd.Series(np.nan, index=sym_strs))),
            errors='coerce'
        )
        ocf = pd.to_numeric(
            df_rows.get('operating_cash_flow', df_rows.get('ocf', df_rows.get('cash_flow_operating', pd.Series(np.nan, index=sym_strs)))),
            errors='coerce'
        )

        # Balance Sheet Accruals fallback if real OCF is missing but operating items are present
        missing_ocf_mask = ocf.isna()
        if np.any(missing_ocf_mask):
            ca_change = pd.to_numeric(df_rows.get('current_assets_change', pd.Series(0.0, index=sym_strs)), errors='coerce').fillna(0.0)
            cl_change = pd.to_numeric(df_rows.get('current_liabilities_change', pd.Series(0.0, index=sym_strs)), errors='coerce').fillna(0.0)
            deprec = pd.to_numeric(df_rows.get('depreciation', pd.Series(0.0, index=sym_strs)), errors='coerce').fillna(0.0)
            op_inc = pd.to_numeric(df_rows.get('operating_income', df_rows.get('ebit', pd.Series(np.nan, index=sym_strs))), errors='coerce')

            # Traditional Balance Sheet Accruals OCF proxy: OCF ≈ Operating Income + Depreciation - ΔWorking Capital
            wc_change = ca_change - cl_change
            bs_ocf_est = op_inc + deprec - wc_change
            ocf = pd.Series(np.where(missing_ocf_mask & op_inc.notna(), bs_ocf_est, ocf), index=sym_strs)

        assets = pd.to_numeric(
            df_rows.get('total_assets', df_rows.get('assets', df_rows.get('book_value', pd.Series(np.nan, index=sym_strs)))),
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
            ranks = df_acc.loc[valid_mask, 'accrual_ratio'].rank(pct=True, ascending=True).clip(0.02, 0.98)
            base_score = (1.0 - ranks + df_acc.loc[valid_mask, 'conversion_bonus']).clip(0.05, 0.95)
            # Accruals Quality Alpha Boost for top 15% high-cashflow sustainable earnings stocks
            high_quality_mask = base_score >= 0.85
            enhanced_score = np.where(high_quality_mask, (0.05 + 0.93 * (base_score ** 0.90)).clip(0.05, 0.98), base_score)
            # Distress check: Cash-burning loss-making firms cannot receive high accruals quality alpha
            is_distressed = ((net_inc < 0) & (ocf < 0)).reindex(df_acc.index).fillna(False).loc[valid_mask]
            enhanced_score = np.where(is_distressed, np.minimum(0.30, enhanced_score), enhanced_score)
            df_acc.loc[valid_mask, 'accruals_quality_score'] = enhanced_score
        elif valid_mask.sum() == 1:
            bonus = float(df_acc.loc[valid_mask, 'conversion_bonus'].iloc[0])
            df_acc.loc[valid_mask, 'accruals_quality_score'] = min(0.50 + bonus, 0.95)
        
        # Fill any remaining NaNs with cross-sectional median or default
        if df_acc['accruals_quality_score'].isna().any():
            med_val = df_acc['accruals_quality_score'].dropna().median() if df_acc['accruals_quality_score'].notna().any() else 0.50
            df_acc['accruals_quality_score'] = df_acc['accruals_quality_score'].fillna(med_val).clip(0.05, 0.95)

        df_acc['accruals_quality_score'] = df_acc['accruals_quality_score'].astype(float)
        return df_acc[['symbol', 'accruals_quality_score']]
