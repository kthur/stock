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

        col_map = {str(c).lower(): c for c in df.columns}
        sec_col = col_map.get("sector")
        ens_col = col_map.get("ensemble_score")

        if ens_col:
            df[ens_col] = pd.to_numeric(df[ens_col], errors="coerce").fillna(0.0)

        # 1. Sector Concentration Budget Check
        if sec_col and ens_col:
            sector_sums = df.groupby(sec_col)[ens_col].sum()
            total_score_sum = float(sector_sums.sum())
            if total_score_sum > 1e-12:
                sector_weights = sector_sums / total_score_sum
                overconcentrated = sector_weights[sector_weights > self.max_sector_weight]
                for sec, w in overconcentrated.items():
                    w_float = float(w)
                    warnings.append(f"Sector '{sec}' weight {w_float*100:.1f}% exceeds max {self.max_sector_weight*100:.0f}% threshold!")
                    # Dampen scores in overconcentrated sector
                    sec_mask = df[sec_col] == sec
                    scale_factor = self.max_sector_weight / max(w_float, 1e-6)
                    df.loc[sec_mask, ens_col] = df.loc[sec_mask, ens_col] * scale_factor

        # 2. Multi-Strategy Consensus Crowding Penalty
        strat_cols = [c for c in df.columns if str(c).endswith("_score") and c != ens_col]
        num_crowded = 0
        if strat_cols and ens_col:
            numeric_strat_df = df[strat_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
            # Count how many strategies assign a score >= 0.70 to a symbol
            high_score_counts = (numeric_strat_df >= 0.70).sum(axis=1)
            crowded_mask = high_score_counts >= self.consensus_crowding_threshold

            if crowded_mask.any():
                num_crowded = int(crowded_mask.sum())
                logger.info("[CrowdingRiskMonitor] %d symbols exhibit high strategy consensus crowding (>=%d strats). Applying 15%% anti-crowding penalty.", num_crowded, self.consensus_crowding_threshold)
                df.loc[crowded_mask, ens_col] = df.loc[crowded_mask, ens_col] * 0.85

        status = {
            "status": "SUCCESS",
            "warnings": warnings,
            "crowded_symbols_count": num_crowded,
        }

        return df, status
