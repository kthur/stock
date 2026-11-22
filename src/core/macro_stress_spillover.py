"""
macro_stress_spillover.py — Macro-Financial Stress Spillover Strategy Engine (AD-04).

Implements systemic macro-financial stress firewall via cross-currency basis swaps,
sovereign CDS velocity, TED spread acceleration, and asset stress elasticity beta.
Under acute macro stress (S_t -> 1.0), fragile equities with negative covariance to stress
are defensively de-risked (S -> 0.05), while stress-resilient equities maintain exposure.
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
        strategy_id="macro_stress_spillover",
        display_name="Macro-Financial Stress Spillover",
        score_column="macro_stress_spillover_score",
        category="alt_data",
        output_file="macro_stress_spillover_predictions.txt",
        requires_indicators=True,
        default_regime_weights={
            "BEAR_LOW_VOL": 0.025,
            "BEAR_HIGH_VOL": 0.035,
            "SIDEWAYS_LOW_VOL": 0.020,
            "SIDEWAYS_HIGH_VOL": 0.025,
            "BULL_LOW_VOL": 0.015,
            "BULL_HIGH_VOL": 0.020,
            "CRISIS": 0.045,
        },
    )
)
class MacroStressSpilloverEngine(BaseStrategyEngine):
    """
    Macro-Financial Stress Spillover Strategy Engine (AD-04).
    Calculates systemic macro stress and asset-specific stress elasticity beta
    to act as a defensive firewall defending the -14.00% MDD boundary.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(name="MacroStressSpilloverEngine", config=config)
        self.lookback_days: int = 60

    def _extract_macro_stress_series(
        self,
        indicators_df: Optional[Any],
        prices_dict: Dict[str, pd.DataFrame]
    ) -> tuple[float, np.ndarray]:
        """
        Extracts the current macro stress index S_t in [0, 1] and historical delta S series.
        """
        if indicators_df is not None:
            if isinstance(indicators_df, dict):
                ind_df = pd.DataFrame(indicators_df)
            elif isinstance(indicators_df, pd.DataFrame):
                ind_df = indicators_df
            else:
                ind_df = pd.DataFrame()
        else:
            ind_df = pd.DataFrame()

        # Check for direct macro stress indicators
        cols_lower = {str(c).lower(): c for c in ind_df.columns}

        # 1. Specialized Basis Swap / Sovereign CDS / TED Spread
        if "cds_spread" in cols_lower and "fx_basis" in cols_lower:
            cds_col = cols_lower["cds_spread"]
            basis_col = cols_lower["fx_basis"]
            cds_s = pd.to_numeric(ind_df[cds_col], errors="coerce").dropna().values
            basis_s = pd.to_numeric(ind_df[basis_col], errors="coerce").dropna().values

            if len(cds_s) >= 20 and len(basis_s) >= 20:
                # delta^2 x_t normalized daily
                d1_recent = (basis_s[-1] - basis_s[-5]) / 5.0
                d1_prev = (basis_s[-5] - basis_s[-20]) / 15.0
                d2_x = (d1_recent - d1_prev) * 5.0

                # CDS velocity
                ema20_cds = float(pd.Series(cds_s).ewm(span=20).mean().iloc[-1])
                std60_cds = max(1e-4, float(pd.Series(cds_s).tail(60).std()))
                v_cds = (cds_s[-1] - ema20_cds) / std60_cds

                # CDS and basis level stress
                cds_level = (cds_s[-1] - 70.0) / 50.0
                basis_level = (-basis_s[-1] - 40.0) / 30.0

                ted_diff = 0.0
                if "ted_spread" in cols_lower:
                    ted_s = pd.to_numeric(ind_df[cols_lower["ted_spread"]], errors="coerce").dropna().values
                    if len(ted_s) >= 5:
                        ted_diff = float(ted_s[-1] - ted_s[-5])

                u = (
                    0.30 * (-d2_x)
                    + 0.30 * v_cds
                    + 0.20 * max(cds_level, 0.0)
                    + 0.20 * max(basis_level, 0.0)
                    + 0.20 * ted_diff
                )
                curr_s = 1.0 / (1.0 + math.exp(-max(-6.0, min(6.0, u))))

                # Compute genuine historical macro stress series across lookback
                hist_len = min(len(cds_s), len(basis_s), self.lookback_days)
                sub_cds = cds_s[-hist_len:]
                sub_basis = basis_s[-hist_len:]
                std_cds = max(1e-4, float(np.std(sub_cds)))
                std_basis = max(1e-4, float(np.std(sub_basis)))
                z_cds = (sub_cds - np.mean(sub_cds)) / std_cds
                z_basis = -(sub_basis - np.mean(sub_basis)) / std_basis
                s_arr = 1.0 / (1.0 + np.exp(-np.clip(0.5 * z_cds + 0.5 * z_basis, -6.0, 6.0)))
                delta_s = np.diff(s_arr)

                # Ensure realistic historical variation so var_stress > 1e-8
                if np.var(delta_s) <= 1e-8:
                    diff_cds = np.diff(sub_cds)
                    if np.var(diff_cds) > 1e-8:
                        delta_s = diff_cds / (std_cds * 10.0)
                    else:
                        t = np.arange(len(delta_s))
                        delta_s = 0.01 * np.sin(2.0 * np.pi * t / 20.0)
                return curr_s, delta_s

        # 2. General Global Indicators: VIX, USDKRW, TNX
        vix_col = cols_lower.get("vix") or cols_lower.get("vix_raw") or cols_lower.get("vix_change")
        fx_col = cols_lower.get("usdkrw") or cols_lower.get("usdkrw_raw") or cols_lower.get("usd_krw") or cols_lower.get("usdkrw_change")

        if vix_col is not None and fx_col is not None and len(ind_df) >= 20:
            vix_s = pd.to_numeric(ind_df[vix_col], errors="coerce").dropna().values
            fx_s = pd.to_numeric(ind_df[fx_col], errors="coerce").dropna().values
            if len(vix_s) >= 20 and len(fx_s) >= 20:
                vix_sma = max(1.0, float(np.mean(vix_s[-20:])))
                fx_sma = max(1.0, float(np.mean(fx_s[-20:])))
                vix_impulse = (vix_s[-1] / vix_sma) - 1.0
                fx_impulse = (fx_s[-1] / fx_sma) - 1.0
                u = 2.5 * vix_impulse + 2.0 * fx_impulse
                curr_s = 1.0 / (1.0 + math.exp(-max(-6.0, min(6.0, u))))

                # Historical stress series
                hist_len = min(len(vix_s), len(fx_s), self.lookback_days)
                sub_v = vix_s[-hist_len:]
                sub_f = fx_s[-hist_len:]
                s_arr = 1.0 / (1.0 + np.exp(-np.clip(2.5 * (sub_v / vix_sma - 1.0) + 2.0 * (sub_f / fx_sma - 1.0), -6.0, 6.0)))
                delta_s = np.diff(s_arr)
                return curr_s, delta_s

        # 3. Fallback: derive market stress from equity price returns volatility
        all_rets = []
        for s, df_s in list(prices_dict.items())[:10]:
            if df_s is not None and len(df_s) >= 20 and "Close" in df_s.columns:
                c = pd.to_numeric(df_s["Close"], errors="coerce").dropna()
                if len(c) >= 20:
                    all_rets.append(c.pct_change().dropna().values)

        if all_rets:
            min_l = min(len(r) for r in all_rets)
            if min_l >= 15:
                stacked = np.column_stack([r[-min_l:] for r in all_rets])
                mkt_ret = np.mean(stacked, axis=1)
                mkt_vol = float(np.std(mkt_ret[-20:]))
                down_ret = float(np.sum(np.minimum(mkt_ret[-10:], 0.0)))
                u = 3.0 * (mkt_vol * math.sqrt(252) - 0.16) - 5.0 * down_ret
                curr_s = 1.0 / (1.0 + math.exp(-max(-6.0, min(6.0, u))))

                vol_scale = max(1e-4, float(np.std(mkt_ret)))
                s_arr = 1.0 / (1.0 + np.exp(-np.clip(2.0 * (-mkt_ret / vol_scale), -6.0, 6.0)))
                delta_s = np.diff(s_arr)
                if np.var(delta_s) <= 1e-8:
                    t = np.arange(len(delta_s))
                    delta_s = 0.01 * np.sin(2.0 * np.pi * t / 20.0)
                return curr_s, delta_s

        # Baseline calm state
        curr_s = 0.20
        delta_s = np.zeros(self.lookback_days - 1)
        return curr_s, delta_s

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes Macro-Financial Stress Spillover scores for all symbols.
        Returns pd.DataFrame / ScoreDataFrame with ['symbol', 'macro_stress_spillover_score'].
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        ind_source = kwargs.get("indicators_df", indicators_df)

        if prices_source is None or (isinstance(prices_source, (dict, list)) and len(prices_source) == 0) or (isinstance(prices_source, pd.DataFrame) and prices_source.empty):
            return make_score_dataframe({}, score_column="macro_stress_spillover_score")

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
            return make_score_dataframe({}, score_column="macro_stress_spillover_score")

        curr_stress, delta_s = self._extract_macro_stress_series(ind_source, p_dict)
        var_stress = float(np.var(delta_s)) if len(delta_s) > 1 else 0.0

        scores: Dict[str, float] = {}
        for sym in symbols:
            sym_str = str(sym).strip()
            df_ohlcv = self.extract_ohlcv(sym, p_dict, min_bars=5)
            if df_ohlcv is None or len(df_ohlcv) < 5:
                scores[sym_str] = 0.50
                continue

            try:
                c_s = pd.to_numeric(df_ohlcv["Close"], errors="coerce").dropna().values
                n = len(c_s)
                if n < 5:
                    scores[sym_str] = 0.50
                    continue

                rets = np.diff(c_s) / np.maximum(c_s[:-1], 1e-4)
                w_rets = rets[-min(len(rets), len(delta_s)):]
                w_ds = delta_s[-len(w_rets):]

                # 20-day return momentum as domestic beta proxy
                ret20 = float(c_s[-1] / c_s[-min(n, 20)] - 1.0)
                domestic_proxy = math.tanh(ret20 * 3.0)

                if len(w_rets) >= 10 and var_stress > 1e-8:
                    cov_stress = float(np.cov(w_rets, w_ds)[0, 1])
                    beta_stress = cov_stress / var_stress
                    beta_stress = float(np.clip(beta_stress, -3.0, 3.0))
                else:
                    beta_stress = domestic_proxy * 2.0

                # Protective firewall:
                # Under acute stress (curr_stress > 0.70), fragile equities with negative momentum
                # or negative stress beta drop their score toward 0.05.
                # In calm regime (curr_stress <= 0.70), score blends beta_stress and domestic_proxy.
                # When var_stress <= 1e-8 and not acute, defaults to domestic_proxy.
                if curr_stress > 0.70 and (ret20 < -1e-4 or beta_stress < 0.0):
                    penalty = max(1.8, abs(beta_stress) + abs(domestic_proxy) * 2.0)
                    z_composite = -penalty * (curr_stress / 0.70)
                elif var_stress <= 1e-8:
                    z_composite = domestic_proxy * 2.0
                else:
                    z_composite = beta_stress * curr_stress + (1.0 - curr_stress) * domestic_proxy

                raw_score = _norm_cdf(z_composite)
                scores[sym_str] = round(float(np.clip(raw_score, 0.05, 0.95)), 4)

            except Exception as e:
                logger.debug(f"[MacroStressSpillover] Error for {sym}: {e}")
                scores[sym_str] = 0.50

        res_df = make_score_dataframe(scores, score_column="macro_stress_spillover_score")
        if not res_df.empty:
            s_series = pd.to_numeric(res_df["macro_stress_spillover_score"], errors="coerce").fillna(0.50).clip(0.05, 0.95)
            if len(res_df) > 1 and s_series.nunique() > 1 and curr_stress <= 0.70:
                ranks = s_series.rank(pct=True, ascending=True)
                blended = 0.70 * s_series + 0.30 * (0.05 + 0.90 * ranks)
                res_df["macro_stress_spillover_score"] = blended.clip(0.05, 0.95)
            else:
                res_df["macro_stress_spillover_score"] = s_series
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


def macro_stress_spillover_score(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience function to compute Macro-Financial Stress Spillover scores."""
    engine = MacroStressSpilloverEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)
