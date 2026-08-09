"""
multi_factor_neutralizer.py — Multi-Factor Risk & Style Neutralizer Engine (Strategy 21)

Neutralizes unwanted Fama-French 5-Factor exposures (SMB, HML, RMW, CMA, MOM)
from raw momentum and return signals via cross-sectional OLS regression,
extracting pure idiosyncratic alpha scores.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


from src.core.base_strategy import BaseStrategyEngine
from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="factor_neutralized",
        display_name="Multi-Factor Neutralized Alpha",
        score_column="factor_neutralized_score",
        category="factor",
        output_file="factor_neutralized_predictions.txt",
        default_regime_weights={
            "BEAR": 0.04, "BEAR_HIGH_VOL": 0.05, "SIDEWAYS_LOW_VOL": 0.03, "BULL_HIGH_VOL": 0.03, "BULL_LOW_VOL": 0.03
        },
    )
)
class MultiFactorNeutralizerEngine(BaseStrategyEngine):
    """Strategy 21: Multi-Factor Style Neutralization Engine.

    Extracts pure idiosyncratic alpha by neutralizing Size (SMB), Value (HML),
    Profitability (RMW), Investment (CMA), and Momentum (MOM) style exposures.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config

    def compute_scores(self, universe: pd.DataFrame, raw_scores: pd.DataFrame = None) -> pd.DataFrame:
        """Compute factor-neutralized pure alpha scores for all universe symbols.

        Args:
            universe: Universe DataFrame containing 'symbol', 'name', 'market', and fundamental/price metrics.
            raw_scores: Optional DataFrame of raw strategy scores to neutralize.

        Returns:
            DataFrame with columns ['symbol', 'name', 'market', 'neutralized_score'].
        """
        results: List[Dict[str, Any]] = []
        if universe is None or universe.empty:
            return pd.DataFrame(columns=["symbol", "name", "market", "neutralized_score"])

        df = universe.copy()

        # Check for required style factor columns; deactivate (return NaN) if missing
        req_cols = ["market_cap", "per", "roe"]
        if not all(col in df.columns for col in req_cols) or (raw_scores is None or raw_scores.empty or "score" not in raw_scores.columns):
            logger.info("MultiFactorNeutralizerEngine: missing required factor columns or raw_scores. Deactivating strategy (returning NaNs).")
            for _, row in df.iterrows():
                sym = str(row["symbol"]).strip()
                name = str(row.get("name", sym))
                mkt = str(row.get("market", "KRX"))
                results.append({
                    "symbol": sym,
                    "name": name,
                    "market": mkt,
                    "neutralized_score": np.nan,
                })
            res_df = pd.DataFrame(results)
            return res_df

        # Explicitly align universe df and raw_scores by symbol
        df_merged = pd.merge(df, raw_scores[['symbol', 'score']], on='symbol', how='inner')
        if df_merged.empty or len(df_merged) < 2:
            results = []
            for _, row in df.iterrows():
                results.append({
                    "symbol": str(row["symbol"]).strip(),
                    "name": str(row.get("name", row["symbol"])),
                    "market": str(row.get("market", "KRX")),
                    "neutralized_score": np.nan,
                })
            return pd.DataFrame(results)

        # Factor definitions: Size (log Cap), Value (1/abs(PER)), Profitability (ROE), Investment (CMA), Momentum (UMD)
        size_factor = np.log(df_merged["market_cap"].clip(lower=1e8))
        value_factor = (1.0 / df_merged["per"].abs().clip(lower=0.1)).fillna(0.0)
        prof_factor = df_merged["roe"].fillna(0.0)
        cma_factor = df_merged.get("asset_growth_yoy", pd.Series(0.0, index=df_merged.index)).fillna(0.0)
        umd_factor = df_merged.get("momentum_12m", pd.Series(0.0, index=df_merged.index)).fillna(0.0)

        s_std = float(size_factor.std(ddof=0))
        v_std = float(value_factor.std(ddof=0))
        p_std = float(prof_factor.std(ddof=0))
        c_std = float(cma_factor.std(ddof=0))
        u_std = float(umd_factor.std(ddof=0))

        # Standardize factor matrix X (5-Factor)
        X = np.column_stack([
            np.ones(len(df_merged)),
            (size_factor - size_factor.mean()) / (s_std if s_std > 1e-6 else 1.0),
            (value_factor - value_factor.mean()) / (v_std if v_std > 1e-6 else 1.0),
            (prof_factor - prof_factor.mean()) / (p_std if p_std > 1e-6 else 1.0),
            (cma_factor - cma_factor.mean()) / (c_std if c_std > 1e-6 else 1.0),
            (umd_factor - umd_factor.mean()) / (u_std if u_std > 1e-6 else 1.0),
        ])

        df_merged = df_merged.dropna(subset=["score"]).copy()
        if df_merged.empty:
            return pd.DataFrame(columns=["symbol", "factor_neutralized_score"])

        y = pd.to_numeric(df_merged["score"], errors="coerce").fillna(0.0).values

        # Perform Cross-Sectional OLS Regression: y = X * beta + residual
        try:
            beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            residuals = y - X.dot(beta)
        except Exception as e:
            logger.warning(f"OLS regression failed in MultiFactorNeutralizerEngine: {e}")
            residuals = y - (np.mean(y) if len(y) > 0 else 0.0)

        # Scale residuals to 0.0 ~ 1.0 score
        res_min, res_max = np.min(residuals), np.max(residuals)
        denom = (res_max - res_min) if (res_max - res_min) > 1e-6 else 1.0
        norm_scores = (residuals - res_min) / denom

        for idx, (_, row) in enumerate(df_merged.iterrows()):
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym))
            mkt = str(row.get("market", "KRX"))
            score = float(np.clip(norm_scores[idx], 0.0, 1.0))

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "neutralized_score": round(score, 4),
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="neutralized_score", ascending=False).reset_index(drop=True)
        return res_df
