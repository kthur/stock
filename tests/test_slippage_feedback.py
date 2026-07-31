"""
Root Test Forwarder / Suite for Slippage Feedback Engine
"""

from trading_system.tests.test_slippage_feedback import (
    test_slippage_metrics_defaults,
    test_empty_or_missing_db_graceful_fallback,
    test_realized_slippage_calculation_single_and_multi_orders,
    test_market_grouping_and_alpha_tiering,
    test_empirical_impact_alpha_calculation,
    test_ensemble_scorer_cost_update_integration,
    test_forwarder_imports,
)

__all__ = [
    "test_slippage_metrics_defaults",
    "test_empty_or_missing_db_graceful_fallback",
    "test_realized_slippage_calculation_single_and_multi_orders",
    "test_market_grouping_and_alpha_tiering",
    "test_empirical_impact_alpha_calculation",
    "test_ensemble_scorer_cost_update_integration",
    "test_forwarder_imports",
]
