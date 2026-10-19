"""
trading_system/src/analysis/strategy_correlation_monitor.py
Strategy Correlation & Effective Strategy Count (ESC) Monitor.
Computes real-time Spearman rank correlation matrix across all active strategies,
measures Effective Number of Independent Bets (Meucci Entropy, 2009),
and identifies redundancy clusters for automated ensemble risk management.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class StrategyCorrelationMonitor:
    """
    Monitors inter-strategy correlations and calculates the Effective Number of Bets (ESC).
    """

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).resolve().parent.parent.parent / "result"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compute_effective_strategy_count(self, corr_matrix: pd.DataFrame) -> float:
        """
        Calculates the Effective Number of Independent Strategies (ESC) using Meucci (2009) PCA Entropy:
        p_i = lambda_i / sum(lambda)
        ESC = exp( - sum(p_i * ln(p_i)) )
        """
        if corr_matrix.empty or len(corr_matrix) < 2:
            return float(len(corr_matrix))

        try:
            # Eigenvalue decomposition of correlation matrix
            vals = np.nan_to_num(corr_matrix.values, nan=0.0, posinf=0.0, neginf=0.0)
            eigenvals = np.linalg.eigvalsh(vals)
            eigenvals = np.maximum(0.0, eigenvals)
            tot = float(np.sum(eigenvals))
            if tot <= 1e-12 or not np.isfinite(tot):
                return 1.0

            p = eigenvals / tot
            # Filter non-zero probabilities for entropy
            p_pos = p[(p > 1e-8) & np.isfinite(p)]
            if len(p_pos) == 0:
                return 1.0
            entropy = -float(np.sum(p_pos * np.log(p_pos)))
            if not np.isfinite(entropy):
                return 1.0
            esc = float(np.exp(entropy))
            return round(min(float(len(corr_matrix)), max(1.0, esc if np.isfinite(esc) else 1.0)), 2)
        except Exception as ex:
            logger.warning(f"Error computing ESC: {ex}")
            return float(len(corr_matrix))

    def analyze_correlations(
        self,
        strategy_scores_df: pd.DataFrame,
        save_json: bool = True
    ) -> Dict[str, Any]:
        """
        Computes Spearman rank correlation matrix and identifies high/low correlation clusters.

        Args:
            strategy_scores_df: DataFrame where each column is a strategy score (symbols as rows).
            save_json: If True, saves output to strategy_correlation_matrix.json.

        Returns:
            Dict containing correlation matrix, ESC, top redundant pairs, and diversification leaders.
        """
        if strategy_scores_df.empty:
            return {"esc": 0.0, "matrix": {}, "redundant_pairs": [], "diversifiers": []}

        # Select numeric columns only
        num_cols = strategy_scores_df.select_dtypes(include=[np.number]).columns
        if len(num_cols) < 2:
            return {"esc": float(len(num_cols)), "matrix": {}, "redundant_pairs": [], "diversifiers": []}

        # Compute Spearman rank correlation matrix
        corr_df = strategy_scores_df[num_cols].corr(method="spearman").fillna(0.0)

        # Calculate Effective Strategy Count
        esc = self.compute_effective_strategy_count(corr_df)

        # Find top redundant pairs (rho > 0.60) and top diversifiers (rho < 0.10)
        redundant_pairs = []
        diversifiers = []

        cols = list(corr_df.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                c1, c2 = cols[i], cols[j]
                rho = float(corr_df.loc[c1, c2])
                pair_info = {"strategy_1": c1, "strategy_2": c2, "spearman_rho": round(rho, 4)}
                if rho >= 0.55:
                    redundant_pairs.append(pair_info)
                elif rho <= 0.15:
                    diversifiers.append(pair_info)

        redundant_pairs.sort(key=lambda x: x["spearman_rho"], reverse=True)
        diversifiers.sort(key=lambda x: x["spearman_rho"])

        # Average correlation per strategy
        avg_corr = {}
        for c in cols:
            other_corrs = [abs(float(corr_df.loc[c, o])) for o in cols if o != c]
            avg_corr[c] = round(float(np.mean(other_corrs)), 4) if other_corrs else 0.0

        summary = {
            "effective_strategy_count": esc,
            "total_strategies": len(cols),
            "diversity_ratio": round(esc / max(1, len(cols)), 4),
            "redundant_pair_count": len(redundant_pairs),
            "top_redundant_pairs": redundant_pairs[:10],
            "top_diversifier_pairs": diversifiers[:10],
            "strategy_average_correlation": avg_corr,
            "correlation_matrix": corr_df.round(4).to_dict()
        }

        if save_json:
            out_file = self.output_dir / "strategy_correlation_matrix.json"
            try:
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved Strategy Correlation Monitor analysis to {out_file} (ESC={esc}/{len(cols)})")
            except Exception as e:
                logger.warning(f"Failed to write correlation matrix to {out_file}: {e}")

        return summary
