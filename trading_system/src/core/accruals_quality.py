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
            elif isinstance(features_df, pd.DataFrame) and not features_df.empty:
                if 'symbol' in features_df.columns:
                    for sym, group in features_df.groupby('symbol'):
                        fund_map[str(sym)] = group.iloc[-1].to_dict()

        accrual_ratios = {}
        for sym in symbols:
            sym_str = str(sym)
            row = fund_map.get(sym_str, fund_map.get(sym_str.zfill(6), {}))

            net_income = row.get('net_income', row.get('net_profit', np.nan))
            ocf = row.get('operating_cash_flow', row.get('ocf', row.get('cash_flow_operating', np.nan)))
            assets = row.get('total_assets', row.get('assets', row.get('book_value', np.nan)))

            # If OCF is missing, fallback using operating income or revenue proxy
            if pd.isna(ocf) and not pd.isna(row.get('operating_income')):
                ocf = row.get('operating_income') * 0.9  # Proxy estimate

            if pd.notna(net_income) and pd.notna(ocf):
                net_inc_val = float(net_income)
                ocf_val = float(ocf)

                # Assets scale denominator
                denom = float(assets) if (pd.notna(assets) and float(assets) > 0) else abs(net_inc_val) * 10.0 + 1e-5

                # Accrual ratio = (Net Income - OCF) / Total Assets
                # Higher positive = worse accruals (inflated earnings)
                # Lower / negative = better accruals (high cash conversion)
                accrual_ratio = (net_inc_val - ocf_val) / denom
                accrual_ratios[sym_str] = accrual_ratio
            else:
                accrual_ratios[sym_str] = np.nan

        # Convert to DataFrame
        df_acc = pd.DataFrame(list(accrual_ratios.items()), columns=['symbol', 'accrual_ratio'])
        valid_mask = df_acc['accrual_ratio'].notna() & np.isfinite(df_acc['accrual_ratio'])

        if valid_mask.sum() > 0:
            # Rank score: inverted because lower accrual_ratio -> higher earnings quality
            # Percentile rank: 1 - percentile_rank(accrual_ratio)
            ranks = df_acc.loc[valid_mask, 'accrual_ratio'].rank(pct=True, ascending=True)
            df_acc.loc[valid_mask, 'accruals_quality_score'] = (1.0 - ranks).clip(0.05, 0.95)
        else:
            df_acc['accruals_quality_score'] = 0.50

        df_acc['accruals_quality_score'] = df_acc['accruals_quality_score'].fillna(0.50).astype(float)

        return df_acc[['symbol', 'accruals_quality_score']]
