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
        feat_df = kwargs.get("features_df", fundamentals_dict)
        symbols = kwargs.get("symbols") or (list(prices_dict.keys()) if prices_dict else [])
        return self.calculate_scores(symbols=symbols, features_df=feat_df, prices_dict=prices_dict)

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
                    elif isinstance(df_item, dict):
                        fund_map[str(sym)] = df_item
            elif isinstance(features_df, pd.DataFrame) and not features_df.empty:
                if 'symbol' in features_df.columns:
                    deduped = features_df.drop_duplicates(subset=['symbol'], keep='last')
                    fund_map = deduped.set_index('symbol').to_dict(orient='index')

        scores = {}
        for sym in symbols:
            sym_str = str(sym)
            row = fund_map.get(sym_str, fund_map.get(sym_str.zfill(6), {}))

            pbr = row.get('pbr', row.get('price_to_book', np.nan))
            bps = row.get('bps', np.nan)
            cash = row.get('cash', row.get('cash_equivalents', row.get('cash_and_equivalents', np.nan)))
            mcap = row.get('market_cap', row.get('marcap', np.nan))
            div_yield = row.get('dividend_yield', row.get('div_yield', 0.0))

            # If PBR is missing, estimate from price / BPS if price is available
            if pd.isna(pbr) and pd.notna(bps) and float(bps) > 0 and prices_dict:
                p_df = prices_dict.get(sym_str, prices_dict.get(sym))
                if isinstance(p_df, pd.DataFrame) and not p_df.empty:
                    close_col = 'close' if 'close' in p_df.columns else ('Close' if 'Close' in p_df.columns else None)
                    if close_col and close_col in p_df.columns:
                        c_series = p_df[close_col].dropna()
                        if not c_series.empty:
                            last_price = float(c_series.iloc[-1])
                            bps_f = float(bps)
                            if bps_f > 0 and np.isfinite(bps_f) and np.isfinite(last_price):
                                pbr = last_price / max(bps_f, 1.0)

            if pd.notna(pbr):
                pbr_val = float(pbr)
                # Check fundamental profitability to prevent distress value traps
                op_margin = row.get('operating_margin', row.get('op_margin', np.nan))
                roe_val = row.get('roe', np.nan)
                is_distress = (pd.notna(op_margin) and float(op_margin) < 0) or (pd.notna(roe_val) and float(roe_val) < 0)

                # Low PBR bonus factor: highest for PBR between 0.3 and 1.0 (profitable firms only)
                if pbr_val <= 0 or not np.isfinite(pbr_val):
                    pbr_factor = 0.10  # Negative equity / capital impairment
                elif is_distress or pbr_val <= 0.20:
                    pbr_factor = 0.20  # Invalidate low PBR bonus for loss-making distress value traps / zombie shells
                elif pbr_val < 1.0:
                    pbr_factor = 1.5 - (pbr_val * 0.5)  # PBR 0.4 -> 1.3, PBR 0.8 -> 1.1
                else:
                    pbr_factor = max(0.1, 1.0 / (pbr_val ** 0.5))

                # Net cash ratio (cash minus total debt)
                debt = row.get('total_debt', row.get('debt', row.get('interest_bearing_debt', 0.0)))
                debt_val = float(debt) if (pd.notna(debt) and float(debt) > 0 and np.isfinite(float(debt))) else 0.0
                cash_val = float(cash) if (pd.notna(cash) and float(cash) > 0 and np.isfinite(float(cash))) else 0.0
                net_cash = cash_val - debt_val

                cash_ratio = 0.0
                mcap_val = float(mcap) if (pd.notna(mcap) and np.isfinite(float(mcap))) else 0.0
                is_krx = str(sym).isdigit() or str(sym).endswith(('.KS', '.KQ'))
                if is_krx and 0 < mcap_val < 1e7:
                    if 0 < max(cash_val, debt_val) < 1e7:
                        mcap_norm = mcap_val
                    else:
                        mcap_norm = mcap_val * 1e8
                else:
                    mcap_norm = mcap_val
                if mcap_norm > 1e4:
                    cash_ratio = max(0.0, net_cash) / mcap_norm

                div_val = float(div_yield) if (pd.notna(div_yield) and np.isfinite(float(div_yield))) else 0.0
                if div_val > 1.0:  # Percentage format e.g. 3.5 -> 0.035
                    div_val /= 100.0

                # Profitability Booster (ROE > 8% accelerates Value-Up re-rating potential)
                roe_boost = 1.0
                if pd.notna(roe_val) and np.isfinite(float(roe_val)) and float(roe_val) > 0.08:
                    roe_boost = np.clip(1.0 + float(roe_val) * 0.5, 1.0, 1.25)

                # Composite score
                raw_score = pbr_factor * roe_boost * (1.0 + np.clip(cash_ratio, 0.0, 1.0) * 1.5 + np.clip(div_val, 0.0, 0.10) * 5.0)
                scores[sym_str] = float(np.clip(raw_score, 0.0, 50.0)) if np.isfinite(raw_score) else np.nan
            else:
                scores[sym_str] = np.nan

        df_out = pd.DataFrame(list(scores.items()), columns=['symbol', 'raw_score'])
        valid_mask = df_out['raw_score'].notna() & np.isfinite(df_out['raw_score'])

        if valid_mask.sum() > 1:
            ranks = df_out.loc[valid_mask, 'raw_score'].rank(pct=True, ascending=True).clip(0.02, 0.98)
            base_score = ranks.clip(0.05, 0.95)
            # Value-Up Super Premium Booster for top 15% high-conviction shareholder yield champions
            super_valueup_mask = base_score >= 0.85
            enhanced_score = np.where(super_valueup_mask, (base_score * 1.10).clip(0.05, 0.98), base_score)
            enhanced_score = np.where(np.isfinite(enhanced_score), enhanced_score, 0.50)
            df_out.loc[valid_mask, 'valueup_catalyst_score'] = enhanced_score
        elif valid_mask.sum() == 1:
            df_out.loc[valid_mask, 'valueup_catalyst_score'] = 0.50
        else:
            default_val = 0.50 if len(df_out) == 1 else np.nan
            df_out['valueup_catalyst_score'] = default_val

        df_out['valueup_catalyst_score'] = pd.to_numeric(df_out['valueup_catalyst_score'], errors='coerce')

        return df_out[['symbol', 'valueup_catalyst_score']]
