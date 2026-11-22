"""
vpin_toxicity.py — Volume-Synchronized Probability of Toxicity (VPIN) Strategy Engine (MF-01).

Implements Easley, López de Prado, & O'Hara (2011, 2012) order flow toxicity model:
measures adverse selection risk faced by liquidity providers under a volume clock.
Utilizes Bulk Volume Classification (BVC) and Garman-Klass intraday volatility to detect
informed trading imbalance and trigger defensive de-risking before flash crashes.
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
        strategy_id="vpin_toxicity",
        display_name="Order Flow Toxicity (VPIN)",
        score_column="vpin_toxicity_score",
        category="microstructure",
        output_file="vpin_toxicity_predictions.txt",
        default_regime_weights={
            "BEAR_LOW_VOL": 0.020,
            "BEAR_HIGH_VOL": 0.030,
            "SIDEWAYS_LOW_VOL": 0.025,
            "SIDEWAYS_HIGH_VOL": 0.025,
            "BULL_LOW_VOL": 0.020,
            "BULL_HIGH_VOL": 0.020,
            "CRISIS": 0.040,
        },
    )
)
class VPINToxicityEngine(BaseStrategyEngine):
    """
    Volume-Synchronized Probability of Toxicity (VPIN) Strategy Engine (MF-01).
    Evaluates order flow toxicity, directional buy/sell flow imbalance, and adverse selection risk.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        vpin_threshold_z: float = 2.0,
        toxicity_penalty: float = 0.15,
        **kwargs: Any
    ) -> None:
        super().__init__(name="VPINToxicityEngine", config=config)
        self.window: int = 20
        self.z_window: int = 60
        self.vpin_threshold_z: float = vpin_threshold_z
        self.toxicity_penalty: float = toxicity_penalty

    def _compute_symbol_vpin(self, df: pd.DataFrame) -> float:
        """
        Computes VPIN toxicity score [0.05, 0.95] for a single symbol OHLCV DataFrame.
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
                (c_raw > 0) & (o_raw > 0) & (h_raw > 0) & (l_raw > 0)
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

            # Compute Garman-Klass volatility and BVC volume splits
            ln_hl = np.log(np.maximum(h_raw / l_raw, 1.0))
            ln_co = np.log(c_raw / o_raw)
            const_term = 2.0 * math.log(2.0) - 1.0
            gk_var = 0.5 * (ln_hl ** 2) - const_term * (ln_co ** 2)
            gk_vol = np.sqrt(np.maximum(gk_var, 1e-8))

            # BVC cumulative probability Phi(ln(C/O) / sigma_GK)
            z_ret = np.zeros(n, dtype=float)
            for i in range(n):
                if h_raw[i] <= l_raw[i] or gk_vol[i] <= 1e-6:
                    if c_raw[i] > o_raw[i]:
                        z_ret[i] = 3.0
                    elif c_raw[i] < o_raw[i]:
                        z_ret[i] = -3.0
                    else:
                        z_ret[i] = 0.0
                else:
                    z_ret[i] = ln_co[i] / gk_vol[i]

            phi = np.array([_norm_cdf(float(z)) for z in z_ret])
            v_b = v_raw * phi
            v_s = v_raw * (1.0 - phi)

            # Rolling 20-day VPIN and DirFlow
            w = min(n, self.window)
            imb = np.abs(v_b[-w:] - v_s[-w:])
            tot_v = v_raw[-w:] + 1e-6
            dir_imb = (v_b[-w:] - v_s[-w:])

            vpin_curr = float(np.mean(imb / tot_v))
            dir_flow = float(np.mean(dir_imb / tot_v))

            # Rolling 60-day historical VPIN distribution for Z-score
            history_len = min(n, self.z_window)
            if history_len >= 20:
                vpin_hist = []
                for k in range(history_len - self.window + 1):
                    s_idx = n - history_len + k
                    e_idx = s_idx + self.window
                    sub_imb = np.abs(v_b[s_idx:e_idx] - v_s[s_idx:e_idx])
                    sub_tot = v_raw[s_idx:e_idx] + 1e-6
                    vpin_hist.append(float(np.mean(sub_imb / sub_tot)))

                if len(vpin_hist) >= 5:
                    mu_vpin = float(np.mean(vpin_hist))
                    std_vpin = float(np.std(vpin_hist))
                    z_vpin = (vpin_curr - mu_vpin) / max(std_vpin, 1e-4)
                else:
                    z_vpin = (vpin_curr - 0.20) / 0.10
            else:
                z_vpin = (vpin_curr - 0.20) / 0.10

            # Directional conviction dampened by high toxicity; extreme toxicity penalty (-0.15)
            # Toxicity penalty factor: (1.0 - 1.0 / (1.0 + exp(-z_vpin)))
            # If z_vpin is high (toxic), factor is small; if calm, directional flow is preserved
            logistic_tox = 1.0 / (1.0 + math.exp(-max(-6.0, min(6.0, z_vpin))))
            calm_conviction = 1.0 - logistic_tox
            extreme_penalty = self.toxicity_penalty if z_vpin > self.vpin_threshold_z else 0.0

            raw_score = 0.50 + 0.35 * dir_flow * calm_conviction - extreme_penalty
            return float(np.clip(raw_score, 0.05, 0.95))

        except Exception as e:
            logger.debug(f"[VPINToxicity] Symbol calculation error: {e}")
            return 0.50

    def compute_scores(
        self,
        prices_dict: Any,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Computes VPIN Toxicity scores for all symbols.
        Returns pd.DataFrame / ScoreDataFrame with ['symbol', 'vpin_toxicity_score'].
        """
        prices_source = kwargs.get("df_prices", prices_dict)
        if prices_source is None or (isinstance(prices_source, (dict, list)) and len(prices_source) == 0) or (isinstance(prices_source, pd.DataFrame) and prices_source.empty):
            return make_score_dataframe({}, score_column="vpin_toxicity_score")

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
            return make_score_dataframe({}, score_column="vpin_toxicity_score")

        scores: Dict[str, float] = {}
        for sym in symbols:
            sym_str = str(sym).strip()
            df_ohlcv = self.extract_ohlcv(sym, p_dict, min_bars=5)
            score = self._compute_symbol_vpin(df_ohlcv)
            scores[sym_str] = round(score, 4)

        res_df = make_score_dataframe(scores, score_column="vpin_toxicity_score")
        if not res_df.empty:
            s_series = pd.to_numeric(res_df["vpin_toxicity_score"], errors="coerce").fillna(0.50).clip(0.05, 0.95)
            if len(res_df) > 1 and s_series.nunique() > 1:
                ranks = s_series.rank(pct=True, ascending=True)
                blended = 0.65 * s_series + 0.35 * (0.05 + 0.90 * ranks)
                res_df["vpin_toxicity_score"] = blended.clip(0.05, 0.95)
            else:
                res_df["vpin_toxicity_score"] = s_series
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


def vpin_toxicity_score(prices_dict: Any, **kwargs: Any) -> pd.DataFrame:
    """Convenience function to compute VPIN Toxicity scores."""
    engine = VPINToxicityEngine()
    return engine.compute_scores(prices_dict=prices_dict, **kwargs)
