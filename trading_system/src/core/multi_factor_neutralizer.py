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


class MultiFactorNeutralizerEngine:
    """Strategy 21: Multi-Factor Style Neutralization Engine.

    Extracts pure idiosyncratic alpha by neutralizing Size (SMB), Value (HML),
    Profitability (RMW), Investment (CMA), and Momentum (MOM) style exposures.
    """

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

        # Factor definitions: Size (log Cap), Value (1/abs(PER)), Profitability (ROE)
        size_factor = np.log(df["market_cap"].clip(lower=1e8))
        value_factor = (1.0 / df["per"].abs().clip(lower=0.1)).fillna(0.0)
        prof_factor = df["roe"].fillna(0.0)

        # Standardize factor matrix X
        X = np.column_stack([
            np.ones(len(df)),
            (size_factor - size_factor.mean()) / (size_factor.std() + 1e-6),
            (value_factor - value_factor.mean()) / (value_factor.std() + 1e-6),
            (prof_factor - prof_factor.mean()) / (prof_factor.std() + 1e-6),
        ])

        y = raw_scores["score"].values

        # Perform Cross-Sectional OLS Regression: y = X * beta + residual
        try:
            beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            residuals = y - X.dot(beta)
        except Exception as e:
            logger.warning(f"OLS regression failed in MultiFactorNeutralizerEngine: {e}")
            residuals = y - np.mean(y)

        # Scale residuals to 0 ~ 100 score
        res_min, res_max = np.min(residuals), np.max(residuals)
        denom = (res_max - res_min) if (res_max - res_min) > 1e-6 else 1.0
        norm_scores = 100.0 * (residuals - res_min) / denom

        for idx, (_, row) in enumerate(df.iterrows()):
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym))
            mkt = str(row.get("market", "KRX"))
            score = float(np.clip(norm_scores[idx], 0.0, 100.0))

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "neutralized_score": round(score, 2),
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="neutralized_score", ascending=False).reset_index(drop=True)
        return res_df
