"""
fcf_velocity.py — Free Cash Flow Yield Velocity and Acceleration Strategy Engine (FM-02).

Implements fundamental cash flow momentum and turnaround acceleration:
evaluates the first derivative (Velocity, v = Delta FCF_Yield) and second derivative
(Acceleration, a = Delta v) of TTM Free Cash Flow relative to Floored Enterprise Value (EV).
Enforces an explicit economic floor of EV >= 0.20 * MarketCap to strictly eliminate phantom
positive yield anomalies on cash-burning companies and ensure mathematical continuity.
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
        strategy_id="fcf_velocity",
        display_name="FCF Yield Velocity & Acceleration",
        score_column="fcf_velocity_score",
        category="fundamental_momentum",
        output_file="fcf_velocity_predictions.txt",
        requires_fundamentals=True,
        default_regime_weights={
            "BEAR_LOW_VOL": 0.035,
            "BEAR_HIGH_VOL": 0.035,
            "SIDEWAYS_LOW_VOL": 0.025,
            "SIDEWAYS_HIGH_VOL": 0.025,
            "BULL_LOW_VOL": 0.030,
            "BULL_HIGH_VOL": 0.030,
            "CRISIS": 0.025,
        },
    )
)
class FCFVelocityEngine(BaseStrategyEngine):
    """
    FCF Yield Velocity & Acceleration Strategy Engine (FM-02).
    Evaluates 1st and 2nd derivatives of FCF/EV with strict EV flooring.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(name="FCFVelocityEngine", config=config)
        self.ev_floor_pct: float = 0.20
        self.v_weight: float = 0.65
        self.a_weight: float = 0.35

    def _compute_symbol_fcf_va(
        self,
        sym: str,
        df_price: Optional[pd.DataFrame],
        fund_data: Optional[Any]
    ) -> tuple[float, float]:
        """
        Computes (velocity, acceleration) of FCF yield for a single symbol.
        """
        # 1. Check fundamental records
        if fund_data is not None:
            data_dict = {}
            if isinstance(fund_data, dict):
                data_dict = fund_data
            elif isinstance(fund_data, pd.DataFrame) and not fund_data.empty:
                data_dict = fund_data.iloc[-1].to_dict()

            # Single period fundamental fields and EV computation
            p_close = 1.0
            if df_price is not None and len(df_price) >= 1 and "Close" in df_price.columns:
                p_close = float(df_price["Close"].dropna().iloc[-1])

            shares = _safe_float(data_dict.get("shares_outstanding", data_dict.get("sharesOutstanding")), 1e7)
            mcap = _safe_float(data_dict.get("market_cap", data_dict.get("marketCap")), p_close * shares)
            mcap = max(1e4, mcap)

            total_debt = _safe_float(data_dict.get("total_debt", data_dict.get("totalDebt")), 0.0)
            cash_eq = _safe_float(data_dict.get("cash_and_equivalents", data_dict.get("cashAndCashEquivalents")), 0.0)

            # Strict Floored Enterprise Value: EV >= 0.20 * MarketCap
            raw_ev = mcap + total_debt - cash_eq
            floored_ev = max(raw_ev, self.ev_floor_pct * mcap, 1e-4)

            # Multi-quarter historical FCF yields if available
            fcf_hist = data_dict.get(
                "historical_fcf_yield",
                data_dict.get("fcf_yield_history", data_dict.get("fcf_history", []))
            )
            if isinstance(fcf_hist, (list, np.ndarray)) and len(fcf_hist) >= 3:
                y_vals = [_safe_float(v, 0.0) for v in fcf_hist]
                if any(abs(v) > 1e4 for v in y_vals):
                    y_vals = [v / floored_ev for v in y_vals]
                y0 = y_vals[-1]
                y1 = y_vals[-2]
                y2 = y_vals[-3]
                v0 = y0 - y1
                v1 = y1 - y2
                a0 = v0 - v1
                return v0, a0

            # Free cash flow
            fcf_val = data_dict.get("free_cash_flow", data_dict.get("freeCashflow"))
            if fcf_val is None or pd.isna(fcf_val):
                ocf = _safe_float(data_dict.get("operating_cash_flow", data_dict.get("operatingCashflow")), 0.0)
                capex = _safe_float(data_dict.get("capital_expenditure", data_dict.get("capitalExpenditures")), 0.0)
                fcf = ocf - capex
            else:
                fcf = _safe_float(fcf_val, 0.0)

            fcf_yield = fcf / floored_ev

            # Velocity proxy via cash flow growth or operating margin momentum
            ocf_growth = _safe_float(data_dict.get("ocf_growth", data_dict.get("earnings_growth")), 0.05)
            velocity = fcf_yield * ocf_growth
            accel = velocity * 0.5
            return velocity, accel

        # 2. Causal price-based cash flow acceleration proxy if fundamentals are absent
        if df_price is not None and len(df_price) >= 60 and "Close" in df_price.columns:
            c = pd.to_numeric(df_price["Close"], errors="coerce").dropna().values
            n = len(c)
            if n >= 120:
                ret60 = float(c[-1] / c[-60] - 1.0)
                ret120 = float(c[-60] / c[-120] - 1.0)
                v = ret60 - ret120
                if n >= 180:
                    ret180 = float(c[-120] / c[-180] - 1.0)
                    prev_v = ret120 - ret180
                    a = v - prev_v
                else:
                    a = v * 0.5
                return v, a
            elif n >= 60:
                ret30 = float(c[-1] / c[-30] - 1.0)
                ret60 = float(c[-30] / c[-60] - 1.0)
                v = ret30 - ret60
                return v, v * 0.5

        return 0.0, 0.0

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes FCF Yield Velocity and Acceleration scores for all symbols.
        Returns pd.DataFrame / ScoreDataFrame with ['symbol', 'fcf_velocity_score'].
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
            return make_score_dataframe({}, score_column="fcf_velocity_score")

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

        v_dict: Dict[str, float] = {}
        a_dict: Dict[str, float] = {}

        for sym in symbols:
            sym_str = str(sym).strip()
            df_price = p_dict.get(sym_str, p_dict.get(sym))
            fund_item = fund_map.get(sym_str, fund_map.get(sym))

            try:
                v_val, a_val = self._compute_symbol_fcf_va(sym_str, df_price, fund_item)
            except Exception as e:
                logger.debug(f"[FCFVelocityEngine] Error computing for {sym_str}: {e}")
                v_val, a_val = 0.0, 0.0
            v_dict[sym_str] = v_val
            a_dict[sym_str] = a_val

        v_s = pd.Series(v_dict, dtype=float)
        a_s = pd.Series(a_dict, dtype=float)

        scores: Dict[str, float] = {}
        if len(v_s) >= 2 and v_s.nunique() > 1:
            mu_v = float(v_s.mean())
            std_v = max(1e-4, float(v_s.std()))
            mu_a = float(a_s.mean())
            std_a = max(1e-4, float(a_s.std()))

            z_v = ((v_s - mu_v) / std_v).clip(-3.0, 3.0)
            z_a = ((a_s - mu_a) / std_a).clip(-3.0, 3.0)
            z_comp = self.v_weight * z_v + self.a_weight * z_a

            for sym, z_val in z_comp.items():
                sc = _norm_cdf(float(z_val))
                scores[str(sym)] = round(float(np.clip(sc, 0.05, 0.95)), 4)
        else:
            for sym in symbols:
                v_val = v_dict.get(sym, 0.0)
                a_val = a_dict.get(sym, 0.0)
                z_raw = self.v_weight * math.tanh(v_val * 5.0) + self.a_weight * math.tanh(a_val * 5.0)
                sc = _norm_cdf(z_raw)
                scores[str(sym)] = round(float(np.clip(sc, 0.05, 0.95)), 4)

        res_df = make_score_dataframe(scores, score_column="fcf_velocity_score")
        if not res_df.empty and "fcf_velocity_score" in res_df.columns:
            res_df["fcf_velocity_score"] = (
                pd.to_numeric(res_df["fcf_velocity_score"], errors="coerce")
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


def fcf_velocity_score(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience function to compute Free Cash Flow Yield Velocity and Acceleration scores."""
    engine = FCFVelocityEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)
