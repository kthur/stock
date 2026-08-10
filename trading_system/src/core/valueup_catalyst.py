"""
trading_system/src/core/valueup_catalyst.py
Strategy #26: Value-Up & Shareholder Yield Catalyst Engine.
Scores stocks based on Corporate Value-Up policy catalysts: low PBR (<1.0), high net cash reserves,
and total shareholder yield (dividend yield + buyback/treasury share cancellation yield).
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="valueup_catalyst",
        display_name="Value-Up & Shareholder Yield",
        score_column="valueup_catalyst_score",
        category="valuation",
        output_file="valueup_catalyst_predictions.txt",
        default_regime_weights={
            "BEAR": 0.05, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.05, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.04
        },
    )
)
class ValueUpCatalystEngine(BaseStrategyEngine):
    """
    Computes Value-Up & Shareholder Yield Score [0.0, 1.0] for stocks.
    High Score = PBR < 1.0 + High Net Cash / Market Cap + Strong Dividend & Buyback Yield (Value-Up re-rating prime target).
    Low Score = High PBR valuation with low shareholder returns and high debt.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        symbols = list(prices_dict.keys()) if prices_dict else []
        return self.calculate_scores(symbols=symbols, prices_dict=prices_dict, **kwargs)

    def calculate_scores(
        self,
        symbols: list,
        features_df: Optional[Any] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None
    ) -> pd.DataFrame:
        """
        Computes Value-Up Catalyst Score per symbol.
        Returns DataFrame with ['symbol', 'valueup_catalyst_score'].
        """
        if not symbols:
            return pd.DataFrame(columns=['symbol', 'valueup_catalyst_score'])

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

        scores = {}
        for sym in symbols:
            sym_str = str(sym)
            row = fund_map.get(sym_str, fund_map.get(sym_str.zfill(6), {}))

            pbr = row.get('pbr', row.get('price_to_book', np.nan))
            bps = row.get('bps', np.nan)
            cash = row.get('cash', row.get('cash_and_equivalents', np.nan))
            mcap = row.get('market_cap', row.get('marcap', np.nan))
            div_yield = row.get('dividend_yield', row.get('div_yield', 0.0))

            # If PBR is missing, estimate from price / BPS if price is available
            if pd.isna(pbr) and pd.notna(bps) and float(bps) > 0 and prices_dict:
                p_df = prices_dict.get(sym_str, prices_dict.get(sym))
                if isinstance(p_df, pd.DataFrame) and not p_df.empty:
                    close_col = 'close' if 'close' in p_df.columns else 'Close'
                    if close_col in p_df.columns:
                        last_price = float(p_df[close_col].dropna().iloc[-1])
                        pbr = last_price / float(bps)

            if pd.notna(pbr):
                pbr_val = float(pbr)
                # Low PBR bonus factor: highest for PBR between 0.3 and 1.0
                if pbr_val <= 0:
                    pbr_factor = 0.1
                elif pbr_val < 1.0:
                    pbr_factor = 1.5 - (pbr_val * 0.5)  # PBR 0.4 -> 1.3, PBR 0.8 -> 1.1
                else:
                    pbr_factor = max(0.1, 1.0 / (pbr_val ** 0.5))

                # Net cash ratio
                cash_ratio = 0.0
                if pd.notna(cash) and pd.notna(mcap) and float(mcap) > 0:
                    cash_ratio = float(cash) / float(mcap)

                div_val = float(div_yield) if pd.notna(div_yield) else 0.0
                if div_val > 1.0:  # Percentage format e.g. 3.5 -> 0.035
                    div_val /= 100.0

                # Composite score
                raw_score = pbr_factor * (1.0 + np.clip(cash_ratio, 0.0, 1.0) * 1.5 + np.clip(div_val, 0.0, 0.10) * 5.0)
                scores[sym_str] = float(raw_score)
            else:
                scores[sym_str] = np.nan

        df_out = pd.DataFrame(list(scores.items()), columns=['symbol', 'raw_score'])
        valid_mask = df_out['raw_score'].notna() & np.isfinite(df_out['raw_score'])

        if valid_mask.sum() > 0:
            ranks = df_out.loc[valid_mask, 'raw_score'].rank(pct=True, ascending=True)
            df_out.loc[valid_mask, 'valueup_catalyst_score'] = ranks.clip(0.05, 0.95)
        else:
            df_out['valueup_catalyst_score'] = 0.50

        df_out['valueup_catalyst_score'] = df_out['valueup_catalyst_score'].fillna(0.50).astype(float)

        return df_out[['symbol', 'valueup_catalyst_score']]
