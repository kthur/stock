"""
stealth_accumulation.py — Institutional Stealth Accumulation Strategy Engine (SM-01).

Implements Barclay & Warner (1993) stealth trading hypothesis: informed institutional
participants slice orders into medium-sized execution tickets to avoid alerting HFT
front-running algorithms and minimize market impact. Evaluates medium-tier flow imbalance
and Cumulative Exponential Stealth Drift (CESD) over a 10-day decay kernel.
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


def _norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@register_strategy(
    StrategyMeta(
        strategy_id="stealth_accumulation",
        display_name="Institutional Stealth Accumulation",
        score_column="stealth_accumulation_score",
        category="smart_money",
        output_file="stealth_accumulation_predictions.txt",
        default_regime_weights={
            "BEAR_LOW_VOL": 0.020,
            "BEAR_HIGH_VOL": 0.015,
            "SIDEWAYS_LOW_VOL": 0.025,
            "SIDEWAYS_HIGH_VOL": 0.020,
            "BULL_LOW_VOL": 0.025,
            "BULL_HIGH_VOL": 0.025,
            "CRISIS": 0.010,
        },
    )
)
class StealthAccumulationEngine(BaseStrategyEngine):
    """
    Institutional Stealth Accumulation Engine (SM-01).
    Evaluates Barclay-Warner medium-tier trade clustering and Cumulative Exponential Stealth Drift (CESD).
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(name="StealthAccumulationEngine", config=config)
        self.window: int = 10
        self.gamma: float = 0.85
        self.z_window: int = 60

    def _compute_symbol_stealth(self, df: pd.DataFrame) -> float:
        """
        Computes stealth accumulation score [0.05, 0.95] for a single symbol OHLCV DataFrame.
        """
        if df is None or df.empty or len(df) < 5:
            return 0.50

        try:
            cols = df.columns
            c_raw = pd.to_numeric(df["Close"], errors="coerce").to_numpy(dtype=float)
            h_raw = pd.to_numeric(df["High"], errors="coerce").to_numpy(dtype=float)
            l_raw = pd.to_numeric(df["Low"], errors="coerce").to_numpy(dtype=float)
            v_raw = pd.to_numeric(df["Volume"], errors="coerce").to_numpy(dtype=float) if "Volume" in cols else np.ones_like(c_raw)

            valid = np.isfinite(c_raw) & np.isfinite(h_raw) & np.isfinite(l_raw) & np.isfinite(v_raw)
            if not np.all(valid):
                c_raw = c_raw[valid]
                h_raw = h_raw[valid]
                l_raw = l_raw[valid]
                v_raw = v_raw[valid]

            n = len(c_raw)
            if n < 5:
                return 0.50

            # Check if investor breakdown columns are present
            has_investor = (
                ("InvestmentTrust" in cols and "PensionFund" in cols and "TotalVolume" in cols) or
                ("inst_volume" in cols and "retail_volume" in cols)
            )

            w = min(n, self.window)
            cesd = 0.0
            norm_weight = 0.0

            if has_investor and "InvestmentTrust" in cols:
                it = pd.to_numeric(df["InvestmentTrust"], errors="coerce").to_numpy(dtype=float)[valid]
                pf = pd.to_numeric(df["PensionFund"], errors="coerce").to_numpy(dtype=float)[valid]
                tv = pd.to_numeric(df["TotalVolume"], errors="coerce").to_numpy(dtype=float)[valid]

                for tau in range(w):
                    idx = -(tau + 1)
                    denom = tv[idx] + 1e-6
                    ratio = (it[idx] + pf[idx]) / denom if denom > 0 else 0.0
                    weight = self.gamma ** tau
                    cesd += weight * ratio
                    norm_weight += weight
            else:
                # Causal volume concentration proxy using CLV and relative volume surge
                adv20 = float(np.mean(v_raw[-min(n, 20):])) if n >= 1 else 1.0
                adv20 = max(adv20, 1.0)

                for tau in range(w):
                    idx = -(tau + 1)
                    c_i = c_raw[idx]
                    h_i = h_raw[idx]
                    l_i = l_raw[idx]
                    v_i = v_raw[idx]

                    bar_range = h_i - l_i
                    if bar_range <= 1e-8:
                        clv = 0.0
                    else:
                        clv = ((c_i - l_i) - (h_i - c_i)) / bar_range
                        clv = max(-1.0, min(1.0, clv))

                    vol_surge = math.log(1.0 + max(0.0, v_i) / adv20)
                    proxy = clv * vol_surge
                    weight = self.gamma ** tau
                    cesd += weight * proxy
                    norm_weight += weight

            if norm_weight > 0:
                cesd /= norm_weight

            # Compute historical CESD rolling series over trailing window to compute Z-score
            history_len = min(n, self.z_window)
            if history_len >= 15:
                rolling_proxies = []
                adv_local = max(1.0, float(np.mean(v_raw[-20:])))
                for t in range(history_len):
                    end_idx = n - history_len + t + 1
                    sub_c = c_raw[:end_idx]
                    sub_h = h_raw[:end_idx]
                    sub_l = l_raw[:end_idx]
                    sub_v = v_raw[:end_idx]
                    if len(sub_c) < 2:
                        continue
                    br = sub_h[-1] - sub_l[-1]
                    clv_t = ((sub_c[-1] - sub_l[-1]) - (sub_h[-1] - sub_c[-1])) / max(br, 1e-8)
                    vs_t = math.log(1.0 + max(0.0, sub_v[-1]) / adv_local)
                    rolling_proxies.append(clv_t * vs_t)

                if len(rolling_proxies) >= 10:
                    mean_val = float(np.mean(rolling_proxies))
                    std_val = float(np.std(rolling_proxies))
                    z = (cesd - mean_val) / max(std_val, 1e-4)
                else:
                    z = math.tanh(cesd * 2.0)
            else:
                z = math.tanh(cesd * 2.0)

            score = _norm_cdf(z)
            return float(np.clip(score, 0.05, 0.95))

        except Exception as e:
            logger.debug(f"[StealthAccumulation] Symbol computation error: {e}")
            return 0.50

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Institutional Stealth Accumulation scores for all symbols.
        Returns pd.DataFrame / ScoreDataFrame with ['symbol', 'stealth_accumulation_score'].
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        if prices_source is None or (isinstance(prices_source, (dict, list)) and len(prices_source) == 0) or (isinstance(prices_source, pd.DataFrame) and prices_source.empty):
            return make_score_dataframe({}, score_column="stealth_accumulation_score")

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
            return make_score_dataframe({}, score_column="stealth_accumulation_score")

        scores: Dict[str, float] = {}
        for sym in symbols:
            sym_str = str(sym).strip()
            df_ohlcv = self.extract_ohlcv(sym, p_dict, min_bars=5)
            score = self._compute_symbol_stealth(df_ohlcv)
            scores[sym_str] = round(score, 4)

        res_df = make_score_dataframe(scores, score_column="stealth_accumulation_score")
        if not res_df.empty:
            s_series = pd.to_numeric(res_df["stealth_accumulation_score"], errors="coerce").fillna(0.50).clip(0.05, 0.95)
            if len(res_df) > 1 and s_series.nunique() > 1:
                ranks = s_series.rank(pct=True, ascending=True)
                blended = 0.60 * s_series + 0.40 * (0.05 + 0.90 * ranks)
                res_df["stealth_accumulation_score"] = blended.clip(0.05, 0.95)
            else:
                res_df["stealth_accumulation_score"] = s_series
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


def stealth_accumulation_score(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience function to compute Institutional Stealth Accumulation scores."""
    engine = StealthAccumulationEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)
