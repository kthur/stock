"""
Portfolio Optimizer Module:
- Risk Parity (Equal Risk Contribution) Allocation
- Mean-Variance / Sharpe Optimization with Covariance Matrix & EVT-CVaR Loss Budget Constraints
- Dynamic Factor & Sector Exposure Control (Neutralization & Constraint)
- Dynamic Band Rebalancing Signal Trigger Evaluation
"""

from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer

__all__ = ["PortfolioOptimizer"]
