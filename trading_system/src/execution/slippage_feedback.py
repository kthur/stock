"""
Closed-Loop Realized Slippage Execution Feedback Engine
Calculates real vs theoretical slippage from trade_logs.db and dynamically updates
microstructure cost parameters in the ensemble scoring engine.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SlippageMetrics:
    avg_slippage_bps: float = 5.0
    market_impact_alpha: float = 0.50
    sample_count: int = 0
    cost_scaling_factor: float = 1.0
    market_slippage_map: Dict[str, float] = field(
        default_factory=lambda: {
            "KOSPI": 5.0,
            "KOSDAQ": 8.0,
            "SP500": 3.0,
            "NASDAQ": 4.0,
            "RUSSELL2000": 7.0,
        }
    )
    total_trades: int = 0
    mean_slippage_bps: float = 5.0
    max_slippage_bps: float = 15.0
    recommended_market_impact_multiplier: float = 1.0


class SlippageFeedbackEngine:
    """
    Queries execution trade logs and computes real vs theoretical slippage metrics,
    returning cost adjustments to tune microstructure cost modeling.
    """

    def __init__(self, db_path: Optional[str] = None, default_slippage_bps: float = 5.0):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "trade_logs.db")
        self.db_path = db_path
        self.default_slippage_bps = default_slippage_bps

    def calculate_realized_slippage(self) -> SlippageMetrics:
        """Reads trade_logs.db and returns realized slippage metrics in basis points (bps)."""
        if not Path(self.db_path).exists():
            return SlippageMetrics(
                avg_slippage_bps=self.default_slippage_bps,
                market_impact_alpha=0.50,
                sample_count=0,
                cost_scaling_factor=1.0,
                total_trades=0,
                mean_slippage_bps=self.default_slippage_bps,
                max_slippage_bps=15.0,
                recommended_market_impact_multiplier=1.0,
            )

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if order_plans / execution_logs or trade_logs exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]

            slippages = []
            mkt_slippage = {
                "KOSPI": [],
                "KOSDAQ": [],
                "SP500": [],
                "NASDAQ": [],
                "RUSSELL2000": [],
            }

            if "execution_logs" in tables and "order_plans" in tables:
                cursor.execute("""
                    SELECT p.market, p.action, p.target_price, e.executed_price
                    FROM execution_logs e
                    JOIN order_plans p ON e.order_id = p.order_id
                    WHERE e.executed_price IS NOT NULL AND p.target_price > 0
                """)
                rows = cursor.fetchall()
                for mkt, act, p_target, p_exec in rows:
                    if p_target > 0 and p_exec > 0:
                        sign = 1.0 if str(act).upper() in ["BUY", "LONG"] else -1.0
                        slip_bps = sign * ((p_exec - p_target) / p_target) * 10000.0
                        slippages.append(slip_bps)
                        if mkt in mkt_slippage:
                            mkt_slippage[mkt].append(slip_bps)

            elif "trade_logs" in tables:
                cursor.execute(
                    "SELECT market, side, expected_price, fill_price FROM trade_logs WHERE fill_price IS NOT NULL AND expected_price > 0"
                )
                rows = cursor.fetchall()
                for mkt, side, p_exp, p_fill in rows:
                    if p_exp > 0 and p_fill > 0:
                        sign = 1.0 if str(side).upper() in ["BUY", "LONG"] else -1.0
                        slip_bps = sign * ((p_fill - p_exp) / p_exp) * 10000.0
                        slippages.append(slip_bps)
                        if mkt in mkt_slippage:
                            mkt_slippage[mkt].append(slip_bps)

            conn.close()

            if not slippages:
                return SlippageMetrics(
                    avg_slippage_bps=self.default_slippage_bps,
                    market_impact_alpha=0.50,
                    sample_count=0,
                    cost_scaling_factor=1.0,
                    total_trades=0,
                    mean_slippage_bps=self.default_slippage_bps,
                    max_slippage_bps=15.0,
                    recommended_market_impact_multiplier=1.0,
                )

            avg_slip = float(np.mean(slippages))
            max_slip = float(np.max(slippages))
            scaling = float(np.clip(avg_slip / self.default_slippage_bps, 0.5, 3.0)) if self.default_slippage_bps > 0 else 1.0
            alpha = float(np.clip(0.50 * scaling, 0.1, 1.00))

            final_mkt_map = {}
            for mkt, val_list in mkt_slippage.items():
                if val_list:
                    final_mkt_map[mkt] = float(np.mean(val_list))
                else:
                    baseline_defaults = {"KOSPI": 5.0, "KOSDAQ": 8.0, "SP500": 3.0, "NASDAQ": 4.0, "RUSSELL2000": 7.0}
                    final_mkt_map[mkt] = baseline_defaults.get(mkt, self.default_slippage_bps)

            return SlippageMetrics(
                avg_slippage_bps=avg_slip,
                market_impact_alpha=alpha,
                sample_count=len(slippages),
                cost_scaling_factor=scaling,
                market_slippage_map=final_mkt_map,
                total_trades=len(slippages),
                mean_slippage_bps=avg_slip,
                max_slippage_bps=max_slip,
                recommended_market_impact_multiplier=scaling,
            )

        except Exception as e:
            logger.error(f"Error calculating realized slippage: {e}")
            return SlippageMetrics(
                avg_slippage_bps=self.default_slippage_bps,
                market_impact_alpha=0.50,
                sample_count=0,
                cost_scaling_factor=1.0,
            )

    def analyze_realized_slippage(self) -> SlippageMetrics:
        return self.calculate_realized_slippage()


RealizedSlippageFeedback = SlippageFeedbackEngine
