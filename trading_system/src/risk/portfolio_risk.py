"""Portfolio Risk Module - Portfolio Risk Parity & Risk Evaluation"""

import numpy as np
from typing import Optional
from .risk_manager import RiskManager
from ..analysis.portfolio_optimizer import calculate_risk_parity_weights, calculate_hrp_weights


class PortfolioRiskEvaluator:
    """Evaluates portfolio-level risk parity, concentration, and drawdown risk."""

    def __init__(self, risk_manager: Optional[RiskManager] = None):
        self.risk_manager = risk_manager or RiskManager()

    def optimize_risk_parity(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Compute Risk Parity weights for portfolio assets."""
        return calculate_risk_parity_weights(cov_matrix)

    def optimize_hrp(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Compute Hierarchical Risk Parity weights for portfolio assets."""
        res = calculate_hrp_weights(cov_matrix)
        return np.asarray(res['realized_weights'] if isinstance(res, dict) else res, dtype=np.float64)

    def evaluate_risk_off(self, vix: Optional[float] = None) -> bool:
        """Check VIX-linked risk-off signal (VIX >= 25.0)."""
        return self.risk_manager.check_risk_off_signal(vix)
