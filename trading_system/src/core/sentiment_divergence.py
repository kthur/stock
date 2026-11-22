"""
sentiment_divergence.py — Retail vs. Institutional Sentiment Divergence Strategy Engine (SM-05).

Implements Barber, Odean, & Zhu (2009) behavioral divergence anomaly:
retail investors systematically chase parabolic rallies and panic-sell at market bottoms,
while institutional capital acts as liquidity providers and contrarian arbitrageurs.
Interacts participant order flow spread (Institutional - Retail) with 14-day RSI overextension
to buy retail panic capitulations and veto euphoric retail tops.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from .base_strategy import BaseStrategyEngine, ScoreDataFrame, make_score_dataframe
from src.core.strategy_registry import register_strategy, StrategyMeta

logger = logging.getLogger(__name__)


@register_strategy(
    StrategyMeta(
        strategy_id="sentiment_divergence",
        display_name="Retail vs Inst Sentiment Divergence",
        score_column="sentiment_divergence_score",
        category="smart_money",
        output_file="sentiment_divergence_predictions.txt",
        default_regime_weights={
            "BEAR_LOW_VOL": 0.025,
            "BEAR_HIGH_VOL": 0.025,
            "SIDEWAYS_LOW_VOL": 0.025,
            "SIDEWAYS_HIGH_VOL": 0.030,
            "BULL_LOW_VOL": 0.025,
            "BULL_HIGH_VOL": 0.020,
            "CRISIS": 0.035,
        },
    )
)
class SentimentDivergenceEngine(BaseStrategyEngine):
    """
    Retail vs. Institutional Sentiment Divergence Engine (SM-05).
    Evaluates order flow spread between institutional and retail participants,
    modulated non-linearly by 14-day RSI distance from neutral (50).
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(name="SentimentDivergenceEngine", config=config)
        self.spread_window: int = 20
        self.rsi_period: int = 14
        self.slope: float = 1.5

    def _compute_rsi14(self, close_arr: np.ndarray) -> float:
        """Computes 14-day Wilder RSI."""
        if len(close_arr) < self.rsi_period + 1:
            return 50.0

        diffs = np.diff(close_arr)
        recent_diffs = diffs[-self.rsi_period:]
        gains = np.maximum(recent_diffs, 0.0)
        losses = np.maximum(-recent_diffs, 0.0)

        avg_gain = float(np.mean(gains))
        avg_loss = float(np.mean(losses))

        if avg_loss <= 1e-8:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _compute_symbol_divergence(
        self,
        df: pd.DataFrame,
        fund_dict: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Computes Sentiment Divergence score [0.05, 0.95] for a single symbol OHLCV DataFrame.
        """
        if df is None or df.empty or len(df) < 5:
            return 0.50

        try:
            cols = df.columns
            c_raw = pd.to_numeric(df["Close"], errors="coerce").to_numpy(dtype=float)
            o_raw = pd.to_numeric(df["Open"], errors="coerce").to_numpy(dtype=float) if "Open" in cols else c_raw
            h_raw = pd.to_numeric(df["High"], errors="coerce").to_numpy(dtype=float) if "High" in cols else c_raw
            l_raw = pd.to_numeric(df["Low"], errors="coerce").to_numpy(dtype=float) if "Low" in cols else c_raw
            v_raw = pd.to_numeric(df["Volume"], errors="coerce").to_numpy(dtype=float) if "Volume" in cols else np.ones_like(c_raw)

            valid = (
                np.isfinite(c_raw) & np.isfinite(o_raw) &
                np.isfinite(h_raw) & np.isfinite(l_raw) & np.isfinite(v_raw) &
                (c_raw > 0)
            )
            if not np.all(valid):
                c_raw = c_raw[valid]
                o_raw = o_raw[valid]
                h_raw = h_raw[valid]
                l_raw = l_raw[valid]
                v_raw = v_raw[valid]

            n = len(c_raw)
            if n < 5:
                return 0.50

            # Direct institutional / retail flow Z-scores from fundamentals / flow data if available
            if (
                fund_dict is not None
                and isinstance(fund_dict, dict)
                and ("inst_flow_z" in fund_dict or "retail_flow_z" in fund_dict)
            ):
                inst_z = float(np.nan_to_num(fund_dict.get("inst_flow_z", 0.0), nan=0.0))
                ret_z = float(np.nan_to_num(fund_dict.get("retail_flow_z", 0.0), nan=0.0))
                z_spread = float(np.clip(inst_z - ret_z, -3.0, 3.0))
            else:
                # 1. Flow Spread calculation
                has_investor = (
                    ("inst_volume" in cols and "retail_volume" in cols) or
                    ("foreign_net_buy" in cols and "retail_net_buy" in cols)
                )

                if has_investor and "inst_volume" in cols:
                    inst_v = pd.to_numeric(df["inst_volume"], errors="coerce").to_numpy(dtype=float)[valid]
                    ret_v = pd.to_numeric(df["retail_volume"], errors="coerce").to_numpy(dtype=float)[valid]
                    spread_series = (inst_v - ret_v) / np.maximum(v_raw, 1.0)
                elif has_investor and "foreign_net_buy" in cols:
                    f_buy = pd.to_numeric(df["foreign_net_buy"], errors="coerce").to_numpy(dtype=float)[valid]
                    r_buy = pd.to_numeric(df["retail_net_buy"], errors="coerce").to_numpy(dtype=float)[valid]
                    spread_series = (f_buy - r_buy) / np.maximum(v_raw, 1.0)
                else:
                    # Causal proxy: CLV volume concentration vs simple price drift
                    adv20 = float(np.mean(v_raw[-min(n, 20):])) if n >= 1 else 1.0
                    adv20 = max(adv20, 1.0)
                    bar_range = np.maximum(h_raw - l_raw, 1e-8)
                    clv = ((c_raw - l_raw) - (h_raw - c_raw)) / bar_range
                    clv = np.clip(clv, -1.0, 1.0)
                    vol_ratio = np.clip(v_raw / adv20, 0.1, 10.0)

                    # Institutional proxy absorbs volume on down/reversal bars; retail chases momentum
                    ret1 = np.zeros(n)
                    ret1[1:] = np.diff(c_raw) / np.maximum(c_raw[:-1], 1e-4)
                    spread_series = clv * np.log(1.0 + vol_ratio) - 0.5 * ret1

                # Rolling 20-day Z-score of flow spread
                w = min(n, self.spread_window)
                sub_spread = spread_series[-w:]
                spread_curr = float(sub_spread[-1])
                mu_spread = float(np.mean(sub_spread))
                std_spread = float(np.std(sub_spread))

                z_spread = (spread_curr - mu_spread) / max(std_spread, 1e-4) if std_spread > 1e-6 else 0.0
                z_spread = float(np.clip(z_spread, -3.0, 3.0))

            # 2. 14-day RSI interaction
            rsi_val = self._compute_rsi14(c_raw)
            rsi_dist = abs(rsi_val - 50.0) / 50.0  # [0.0, 1.0]

            # DivAlpha_t = Z_spread * (1.0 + |RSI - 50| / 50)
            div_alpha = z_spread * (1.0 + rsi_dist)

            # Continuous logistic mapping [0.05, 0.95]
            logistic_val = 1.0 / (1.0 + math.exp(-max(-6.0, min(6.0, self.slope * div_alpha))))
            return float(np.clip(logistic_val, 0.05, 0.95))

        except Exception as e:
            logger.debug(f"[SentimentDivergence] Symbol calculation error: {e}")
            return 0.50

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Retail vs Institutional Sentiment Divergence scores for all symbols.
        Returns pd.DataFrame / ScoreDataFrame with ['symbol', 'sentiment_divergence_score'].
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        fund_source = kwargs.get("fundamentals_dict", fundamentals_dict)

        if prices_source is None or (isinstance(prices_source, (dict, list)) and len(prices_source) == 0) or (isinstance(prices_source, pd.DataFrame) and prices_source.empty):
            return make_score_dataframe({}, score_column="sentiment_divergence_score")

        if isinstance(prices_source, dict):
            p_dict = prices_source
            symbols = list(p_dict.keys())
        elif isinstance(prices_source, pd.DataFrame):
            if "symbol" in prices_source.columns:
                symbols = prices_source["symbol"].dropna().astype(str).unique().tolist()
                p_dict = {s: prices_source[prices_source["symbol"] == s] for s in symbols}
            else:
                symbols = list(prices_source.columns)
                p_dict = {col: pd.DataFrame({"Close": prices_source[col]}) for col in symbols}
        else:
            return make_score_dataframe({}, score_column="sentiment_divergence_score")

        fund_map: Dict[str, Any] = {}
        if isinstance(fund_source, dict):
            fund_map = fund_source
        elif isinstance(fund_source, pd.DataFrame) and not fund_source.empty:
            if "symbol" in fund_source.columns:
                deduped = fund_source.drop_duplicates(subset=["symbol"], keep="last")
                fund_map = deduped.set_index("symbol").to_dict(orient="index")

        scores: Dict[str, float] = {}
        for sym in symbols:
            sym_str = str(sym).strip()
            df_ohlcv = self.extract_ohlcv(sym, p_dict, min_bars=5)
            fund_item = fund_map.get(sym_str, fund_map.get(sym))
            score = self._compute_symbol_divergence(df_ohlcv, fund_item)
            scores[sym_str] = round(score, 4)

        res_df = make_score_dataframe(scores, score_column="sentiment_divergence_score")
        if not res_df.empty:
            s_series = pd.to_numeric(res_df["sentiment_divergence_score"], errors="coerce").fillna(0.50).clip(0.05, 0.95)
            if len(res_df) > 1 and s_series.nunique() > 1:
                ranks = s_series.rank(pct=True, ascending=True)
                blended = 0.65 * s_series + 0.35 * (0.05 + 0.90 * ranks)
                res_df["sentiment_divergence_score"] = blended.clip(0.05, 0.95)
            else:
                res_df["sentiment_divergence_score"] = s_series
        return res_df

    def calculate_scores(
        self,
        symbols: Optional[List[str]] = None,
        prices_dict: Optional[Dict[str, pd.DataFrame]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Universal calculate_scores method compatible with test suites and pipeline runners."""
        if prices_dict is None and isinstance(symbols, dict):
            prices_dict = symbols
            symbols = None
        if symbols is not None and prices_dict is not None:
            prices_dict = {s: prices_dict[s] for s in symbols if s in prices_dict}
        return self.compute_scores(prices_dict=prices_dict, **kwargs)


def sentiment_divergence_score(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience function to compute Retail vs Inst Sentiment Divergence scores."""
    engine = SentimentDivergenceEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)
