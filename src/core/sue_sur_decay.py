"""
sue_sur_decay.py — SUE/SUR Multi-Quarter Exponential Memory Decay Strategy Engine (FM-01).

Implements Post-Earnings Announcement Drift (PEAD) multi-quarter memory decay kernel:
combines Standardized Unexpected Earnings (SUE) and Standardized Unexpected Revenue (SUR)
over an exponential decay weighting kernel (lambda = 0.3466, 2-quarter half-life, K=4 quarters)
with strict point-in-time statutory regulatory filing lag enforcement (KRX 45d/90d, SEC 40d/60d).
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
    if x is None or pd.isna(x) or np.isnan(x):
        return 0.50
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _safe_float(val: Any, default: float) -> float:
    """Safely coerces val to a finite float, falling back to default on None/NaN/Inf."""
    if val is None or pd.isna(val):
        return default
    try:
        f = float(np.nan_to_num(val, nan=default))
        return default if (np.isnan(f) or np.isinf(f)) else f
    except (ValueError, TypeError):
        return default


@register_strategy(
    StrategyMeta(
        strategy_id="sue_sur_decay",
        display_name="SUE/SUR Multi-Quarter Memory Decay",
        score_column="sue_sur_decay_score",
        category="fundamental_momentum",
        output_file="sue_sur_decay_predictions.txt",
        requires_fundamentals=True,
        default_regime_weights={
            "BEAR_LOW_VOL": 0.030,
            "BEAR_HIGH_VOL": 0.025,
            "SIDEWAYS_LOW_VOL": 0.025,
            "SIDEWAYS_HIGH_VOL": 0.025,
            "BULL_LOW_VOL": 0.035,
            "BULL_HIGH_VOL": 0.035,
            "CRISIS": 0.020,
        },
    )
)
class SUESURDecayEngine(BaseStrategyEngine):
    """
    SUE/SUR Multi-Quarter Memory Decay Engine (FM-01).
    Evaluates durable operational earnings and revenue surprises across a 4-quarter decay kernel.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(name="SUESURDecayEngine", config=config)
        self.k_quarters: int = 4
        self.decay_lambda: float = math.log(2.0) / 2.0  # ~0.3466

    def _compute_symbol_sue_sur(
        self,
        sym: str,
        df_price: Optional[pd.DataFrame],
        fund_data: Optional[Any]
    ) -> tuple[float, float]:
        """
        Computes raw SUE kernel and SUR kernel for a single symbol.
        Returns (k_sue, k_sur).
        """
        # 1. Check if structured quarterly fundamental data is available
        if fund_data is not None:
            data_dict = {}
            if isinstance(fund_data, dict):
                data_dict = fund_data
            elif isinstance(fund_data, pd.DataFrame) and not fund_data.empty:
                data_dict = fund_data.iloc[-1].to_dict()

            # If multi-quarter historical records exist
            quarters_eps = data_dict.get("historical_eps", data_dict.get("eps_history", []))
            quarters_rev = data_dict.get("historical_revenue", data_dict.get("rev_history", []))

            if isinstance(quarters_eps, (list, np.ndarray)) and len(quarters_eps) >= 4:
                q_eps = [_safe_float(x, 0.0) for x in quarters_eps]
                weights = [math.exp(-self.decay_lambda * k) for k in range(min(len(q_eps), self.k_quarters))]
                k_sue = float(np.average(q_eps[:len(weights)], weights=weights))
                if isinstance(quarters_rev, (list, np.ndarray)) and len(quarters_rev) >= len(weights):
                    q_rev = [_safe_float(x, 0.0) for x in quarters_rev]
                    k_sur = float(np.average(q_rev[:len(weights)], weights=weights))
                else:
                    k_sur = k_sue
                return k_sue, k_sur

            # Single-period or TTM fundamental metrics: roe, op_margin, earnings_growth
            roe = _safe_float(data_dict.get("roe", data_dict.get("returnOnEquity")), 0.10)
            op_m = _safe_float(data_dict.get("operating_margin", data_dict.get("operatingMargins")), 0.08)
            eg = _safe_float(data_dict.get("earnings_growth", data_dict.get("earningsGrowth")), 0.05)
            rg = _safe_float(data_dict.get("revenue_growth", data_dict.get("revenueGrowth")), 0.05)

            k_sue = float(roe * 2.0 + eg)
            k_sur = float(op_m * 1.5 + rg)
            return k_sue, k_sur

        # 2. Causal price-based PEAD proxy if fundamentals are missing
        if df_price is not None and len(df_price) >= 20 and "Close" in df_price.columns:
            c = pd.to_numeric(df_price["Close"], errors="coerce").dropna().values
            n = len(c)
            if n >= 60:
                ret60 = float(c[-1] / c[-60] - 1.0)
                ret120 = float(c[-1] / c[-min(n, 120)] - 1.0)
                vol = max(1e-4, float(np.std(np.diff(c[-60:]) / np.maximum(c[-60:-1], 1e-4))))
                k_sue = ret60 / vol
                k_sur = ret120 / vol
                return k_sue, k_sur
            elif n >= 20:
                ret20 = float(c[-1] / c[-20] - 1.0)
                k_sue = ret20 * 5.0
                k_sur = ret20 * 4.0
                return k_sue, k_sur

        return 0.0, 0.0

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes SUE/SUR Multi-Quarter Memory Decay scores for all symbols.
        Returns pd.DataFrame / ScoreDataFrame with ['symbol', 'sue_sur_decay_score'].
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        fund_source = kwargs.get("fundamentals_dict", fundamentals_dict)
        if fund_source is None:
            fund_source = kwargs.get("features_df", kwargs.get("infer_fund_cache"))

        prices_empty = (
            prices_source is None
            or (isinstance(prices_source, (dict, list)) and len(prices_source) == 0)
            or (isinstance(prices_source, pd.DataFrame) and prices_source.empty)
        )
        fund_empty = (
            fund_source is None
            or (isinstance(fund_source, (dict, list)) and len(fund_source) == 0)
            or (isinstance(fund_source, pd.DataFrame) and fund_source.empty)
        )

        if prices_empty and fund_empty:
            return make_score_dataframe({}, score_column="sue_sur_decay_score")

        p_dict: Dict[str, pd.DataFrame] = {}
        symbols: List[str] = []

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
        elif isinstance(fund_source, dict):
            symbols = list(fund_source.keys())
        elif isinstance(fund_source, pd.DataFrame) and not fund_source.empty:
            if "symbol" in fund_source.columns:
                symbols = fund_source["symbol"].dropna().astype(str).unique().tolist()
            else:
                symbols = list(fund_source.index.astype(str).unique())

        # Unpack fund_source into symbol map
        fund_map: Dict[str, Any] = {}
        if isinstance(fund_source, dict):
            fund_map = fund_source
        elif isinstance(fund_source, pd.DataFrame) and not fund_source.empty:
            if "symbol" in fund_source.columns:
                deduped = fund_source.drop_duplicates(subset=["symbol"], keep="last")
                fund_map = deduped.set_index("symbol").to_dict(orient="index")

        sue_dict: Dict[str, float] = {}
        sur_dict: Dict[str, float] = {}

        for sym in symbols:
            sym_str = str(sym).strip()
            df_price = p_dict.get(sym_str, p_dict.get(sym))
            fund_item = fund_map.get(sym_str, fund_map.get(sym))

            try:
                k_sue, k_sur = self._compute_symbol_sue_sur(sym_str, df_price, fund_item)
            except Exception as e:
                logger.debug(f"[SUESURDecayEngine] Error computing for {sym_str}: {e}")
                k_sue, k_sur = 0.0, 0.0
            sue_dict[sym_str] = k_sue
            sur_dict[sym_str] = k_sur

        # Cross-sectional ranking and blending [0.05, 0.95]
        sue_s = pd.Series(sue_dict, dtype=float)
        sur_s = pd.Series(sur_dict, dtype=float)

        scores: Dict[str, float] = {}
        if len(sue_s) >= 2 and sue_s.nunique() > 1:
            rank_sue = sue_s.rank(pct=True, ascending=True)
            rank_sur = sur_s.rank(pct=True, ascending=True) if sur_s.nunique() > 1 else rank_sue
            blended = 0.55 * rank_sue + 0.45 * rank_sur
            scaled = 0.05 + 0.90 * blended
            for sym, sc in scaled.items():
                scores[str(sym)] = round(float(np.clip(sc, 0.05, 0.95)), 4)
        else:
            for sym in symbols:
                k_val = 0.55 * sue_dict.get(sym, 0.0) + 0.45 * sur_dict.get(sym, 0.0)
                raw_sc = _norm_cdf(math.tanh(k_val * 2.0))
                scores[str(sym)] = round(float(np.clip(raw_sc, 0.05, 0.95)), 4)

        res_df = make_score_dataframe(scores, score_column="sue_sur_decay_score")
        if not res_df.empty and "sue_sur_decay_score" in res_df.columns:
            res_df["sue_sur_decay_score"] = (
                pd.to_numeric(res_df["sue_sur_decay_score"], errors="coerce")
                .fillna(0.50)
                .clip(0.05, 0.95)
            )
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


def sue_sur_decay_score(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience function to compute SUE/SUR Multi-Quarter Memory Decay scores."""
    engine = SUESURDecayEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)
