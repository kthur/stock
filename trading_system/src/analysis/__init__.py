"""
Analysis & Portfolio Optimization Module
Provides backtesting engines, statistical metrics, covariance shrinkage,
portfolio optimizers (HRP, Black-Litterman, Risk Parity), market regime detectors, and strategy coverage analyzers.
"""

from __future__ import annotations

try:
    from src.analysis.backtest import BacktestEngine, BacktestResult, BacktestTrade, PriceBar
    from src.analysis.relative_strength import RelativeStrengthAnalyzer
    from src.analysis.statistics import AdvancedStatistics, PerformanceMetrics
    from src.analysis.style_rotator import StyleRotator
    from src.analysis.portfolio_optimizer import (
        shrink_covariance_matrix,
        calculate_hrp_weights,
        calculate_risk_parity_weights,
        calculate_black_litterman_weights,
        calculate_herc_weights,
        apply_portfolio_constraints,
    )
    from src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
    from src.analysis.regime_detector import MarketRegimeDetector
    from src.risk.portfolio_optimizer import PortfolioOptimizer
    from src.analysis.walk_forward_validation_framework import (
        WalkForwardValidationFramework,
        WalkForwardMode,
        WalkForwardWindow,
        WalkForwardAuditReport,
    )
    from src.analysis.survivorship_bias_auditor import (
        SurvivorshipBiasAuditor,
        SurvivorshipAuditResult,
    )
except ImportError:
    from trading_system.src.analysis.backtest import BacktestEngine, BacktestResult, BacktestTrade, PriceBar
    from trading_system.src.analysis.relative_strength import RelativeStrengthAnalyzer
    from trading_system.src.analysis.statistics import AdvancedStatistics, PerformanceMetrics
    from trading_system.src.analysis.style_rotator import StyleRotator
    from trading_system.src.analysis.portfolio_optimizer import (
        shrink_covariance_matrix,
        calculate_hrp_weights,
        calculate_risk_parity_weights,
        calculate_black_litterman_weights,
        calculate_herc_weights,
        apply_portfolio_constraints,
    )
    from trading_system.src.analysis.coverage_analyzer import StrategyCoverageAnalyzer
    from trading_system.src.analysis.regime_detector import MarketRegimeDetector
    from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer
    from trading_system.src.analysis.walk_forward_validation_framework import (
        WalkForwardValidationFramework,
        WalkForwardMode,
        WalkForwardWindow,
        WalkForwardAuditReport,
    )
    from trading_system.src.analysis.survivorship_bias_auditor import (
        SurvivorshipBiasAuditor,
        SurvivorshipAuditResult,
    )

__all__ = [
    "AdvancedStatistics",
    "BacktestEngine",
    "BacktestResult",
    "BacktestTrade",
    "PerformanceMetrics",
    "PriceBar",
    "RelativeStrengthAnalyzer",
    "StyleRotator",
    "PortfolioOptimizer",
    "shrink_covariance_matrix",
    "calculate_hrp_weights",
    "calculate_risk_parity_weights",
    "calculate_black_litterman_weights",
    "calculate_herc_weights",
    "apply_portfolio_constraints",
    "StrategyCoverageAnalyzer",
    "MarketRegimeDetector",
    "WalkForwardValidationFramework",
    "WalkForwardMode",
    "WalkForwardWindow",
    "WalkForwardAuditReport",
    "SurvivorshipBiasAuditor",
    "SurvivorshipAuditResult",
]
