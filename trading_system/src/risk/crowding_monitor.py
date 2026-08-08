"""
crowding_monitor.py — Anti-Crowding & Sector Risk Monitor

Monitors strategy consensus crowding (>80% strategy alignment) and sector concentration
budgets (>40%) to protect against liquidity squeezes and systemic factor crowding.
"""

from __future__ import annotations

import logging
import pandas as pd
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class CrowdingRiskMonitor:
    """Anti-Crowding & Sector Concentration Monitor."""

    def __init__(self, max_sector_weight: float = 0.40, consensus_crowding_threshold: int = 15) -> None:
        self.max_sector_weight = max_sector_weight
        self.consensus_crowding_threshold = consensus_crowding_threshold

    def evaluate_crowding_risk(self, ensemble_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Apply anti-crowding penalty dampening to strategy scores.

        Args:
            ensemble_df: DataFrame containing symbol, market, sector, ensemble_score, and strategy score columns.

        Returns:
            Tuple of (dampened ensemble_df, crowding status summary dict).
        """
        if ensemble_df is None or ensemble_df.empty:
            return ensemble_df, {"status": "EMPTY"}

        df = ensemble_df.copy()
        warnings: List[str] = []

        # 1. Sector Concentration Budget Check
        if "sector" in df.columns and "ensemble_score" in df.columns:
            sector_sums = df.groupby("sector")["ensemble_score"].sum()
            total_score_sum = sector_sums.sum()
            if total_score_sum > 0:
                sector_weights = sector_sums / total_score_sum
                overconcentrated = sector_weights[sector_weights > self.max_sector_weight]
                for sec, w in overconcentrated.items():
                    warnings.append(f"Sector '{sec}' weight {w*100:.1f}% exceeds max {self.max_sector_weight*100:.0f}% threshold!")
                    # Dampen scores in overconcentrated sector
                    sec_mask = df["sector"] == sec
                    df.loc[sec_mask, "ensemble_score"] = df.loc[sec_mask, "ensemble_score"] * (self.max_sector_weight / w)

        # 2. Multi-Strategy Consensus Crowding Penalty
        strat_cols = [c for c in df.columns if c.endswith("_score") and c != "ensemble_score"]
        if strat_cols and "ensemble_score" in df.columns:
            # Count how many strategies assign a score >= 0.70 to a symbol
            high_score_counts = (df[strat_cols] >= 0.70).sum(axis=1)
            crowded_mask = high_score_counts >= self.consensus_crowding_threshold

            if crowded_mask.any():
                num_crowded = int(crowded_mask.sum())
                logger.info("[CrowdingRiskMonitor] %d symbols exhibit high strategy consensus crowding (>=%d strats). Applying 15%% anti-crowding penalty.", num_crowded, self.consensus_crowding_threshold)
                df.loc[crowded_mask, "ensemble_score"] = df.loc[crowded_mask, "ensemble_score"] * 0.85

        status = {
            "status": "SUCCESS",
            "warnings": warnings,
            "crowded_symbols_count": int(crowded_mask.sum()) if "strat_cols" in locals() and strat_cols else 0,
        }

        return df, status
