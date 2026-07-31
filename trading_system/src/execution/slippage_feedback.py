"""
Closed-Loop Realized Slippage Execution Feedback Engine
Calculates real vs theoretical slippage from trade_logs.db and dynamically updates
microstructure cost parameters in the ensemble scoring engine.
"""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SlippageMetrics:
    total_trades: int
    mean_slippage_bps: float
    max_slippage_bps: float
    recommended_market_impact_multiplier: float


class RealizedSlippageFeedback:
    """
    Queries execution trade logs and computes real vs theoretical slippage metrics,
    returning cost adjustments to tune microstructure cost modeling.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "trade_logs.db")
        self.db_path = db_path

    def analyze_realized_slippage(self) -> SlippageMetrics:
        """Reads trade_logs.db and returns realized slippage metrics in basis points (bps)."""
        if not Path(self.db_path).exists():
            logger.info("trade_logs.db does not exist yet. Returning baseline cost multiplier.")
            return SlippageMetrics(
                total_trades=0,
                mean_slippage_bps=5.0,
                max_slippage_bps=15.0,
                recommended_market_impact_multiplier=1.0,
            )

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Fetch fill_price vs order_price if columns exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trade_logs'")
            if not cursor.fetchone():
                conn.close()
                return SlippageMetrics(0, 5.0, 15.0, 1.0)

            cursor.execute(
                "SELECT symbol, expected_price, fill_price, side FROM trade_logs WHERE fill_price IS NOT NULL AND expected_price IS NOT NULL"
            )
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return SlippageMetrics(0, 5.0, 15.0, 1.0)

            slippages = []
            for sym, exp_p, fill_p, side in rows:
                if exp_p <= 0 or fill_p <= 0:
                    continue
                # For Buy: (fill_p - exp_p) / exp_p; For Sell: (exp_p - fill_p) / exp_p
                if str(side).upper() == "BUY":
                    slip_bps = ((fill_p - exp_p) / exp_p) * 10000.0
                else:
                    slip_bps = ((exp_p - fill_p) / exp_p) * 10000.0
                slippages.append(slip_bps)

            if not slippages:
                return SlippageMetrics(0, 5.0, 15.0, 1.0)

            mean_slip = float(np.mean(slippages))
            max_slip = float(np.max(slippages))

            # Base multiplier is 1.0 for 5 bps; scale proportionally if mean slippage is higher
            multiplier = float(np.clip(max(1.0, mean_slip / 5.0), 1.0, 3.0))

            return SlippageMetrics(
                total_trades=len(slippages),
                mean_slippage_bps=mean_slip,
                max_slippage_bps=max_slip,
                recommended_market_impact_multiplier=multiplier,
            )

        except Exception as e:
            logger.error(f"Error querying trade_logs.db for slippage: {e}")
            return SlippageMetrics(0, 5.0, 15.0, 1.0)


# Alias for backwards compatibility
SlippageFeedbackEngine = RealizedSlippageFeedback
