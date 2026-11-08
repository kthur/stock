"""
Asymmetric Power-Law Leland No-Trade Buffer Bands with Zero-Bypass (Feature F893, Release R180).

Phase 182 risk & execution module providing dynamic asymmetric Leland transaction cost
no-trade bands with instant zero-bypass eligibility for fresh entries and complete exits.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Tuple

from src.execution.leland_buffer_bands import (
    _FeatureStr,
    _ReleaseStr,
    _VersionInt,
    LelandBufferConfig,
    LelandExecutionOutput,
    AsymmetricLelandTurnoverOptimizer,
    AsymmetricLelandTurnoverOptimizerPhase182,
    Phase182AsymmetricLelandOptimizer,
    F893AsymmetricLelandOptimizer,
    TurnoverOptimizerPhase182,
    AsymmetricLelandBandsEngine,
    LelandBufferBandsEnginePhase178,
    Phase178AsymmetricLelandOptimizer,
    F873AsymmetricLelandOptimizer,
    TurnoverOptimizerPhase178,
    compute_asymmetric_leland_bands_r179,
    filter_portfolio_rebalance,
    is_zero_bypass_eligible as _base_is_zero_bypass_eligible,
)

from src.execution.turnover_optimizer import (
    TurnoverOptimizer,
    LelandTurnoverOptimizer,
    compute_asymmetric_leland_bands as _turnover_compute_bands,
)

VERSION: int = _VersionInt(182)
RELEASE: str = _ReleaseStr("R180")
FEATURE: str = _FeatureStr("F893")

VERSION_PHASE182: int = 182
RELEASE_PHASE182: str = "R180"
FEATURE_PHASE182: str = "F893"

VERSION_PHASE178: int = 178
RELEASE_PHASE178: str = "R179"
FEATURE_PHASE178: str = "F873"

VERSION_PHASE174: int = 174
RELEASE_PHASE174: str = "R175"
FEATURE_PHASE174: str = "F853"

VERSION_PHASE166: int = 166
RELEASE_PHASE166: str = "R167"
FEATURE_PHASE166: str = "F813"


def compute_asymmetric_leeland_bands(
    current_weights: Dict[str, float],
    target_weights: Dict[str, float],
    alphas: Optional[Dict[str, float]] = None,
    volatilities: Optional[Dict[str, float]] = None,
    spread_bps: float = 10.0,
    impact_coef: float = 0.05,
    risk_aversion: float = 1.0,
    min_bandwidth: float = 0.005,
    max_bandwidth: float = 0.060,
    catalyst_surge_ratio: float = 3.5,
    **kwargs: Any,
) -> Dict[str, Dict[str, Any]]:
    """
    Computes asymmetric power-law Leland no-trade buffer bands for rebalance turnover optimization.
    """
    return compute_asymmetric_leland_bands_r179(
        current_weights=current_weights,
        target_weights=target_weights,
        alphas=alphas,
        volatilities=volatilities,
        spread_bps=spread_bps,
        impact_coef=impact_coef,
        risk_aversion=risk_aversion,
        min_bandwidth=min_bandwidth,
        max_bandwidth=max_bandwidth,
        catalyst_surge_ratio=catalyst_surge_ratio,
        **kwargs,
    )


compute_asymmetric_leland_bands = compute_asymmetric_leeland_bands


def is_zero_bypass_eligible(
    current_weight: float,
    target_weight: float,
    threshold: float = 1e-4,
) -> bool:
    """
    Evaluates whether an order qualifies for immediate zero-bypass through Leland bands.
    Returns True for fresh entries (current_weight == 0) and full liquidations (target_weight == 0).
    """
    return _base_is_zero_bypass_eligible(current_weight, target_weight, threshold=threshold)


# Aliases
AsymmetricLelandBandsEnginePhase182 = AsymmetricLelandTurnoverOptimizer
LelandNoTradeBandsEngine = AsymmetricLelandTurnoverOptimizer

# sys.modules registration
sys.modules[f"{__name__}.AsymmetricLelandTurnoverOptimizer"] = AsymmetricLelandTurnoverOptimizer
sys.modules[f"{__name__}.AsymmetricLelandTurnoverOptimizerPhase182"] = AsymmetricLelandTurnoverOptimizer
sys.modules[f"{__name__}.Phase182AsymmetricLelandOptimizer"] = AsymmetricLelandTurnoverOptimizer
sys.modules[f"{__name__}.F893AsymmetricLelandOptimizer"] = AsymmetricLelandTurnoverOptimizer
sys.modules[f"{__name__}.TurnoverOptimizerPhase182"] = AsymmetricLelandTurnoverOptimizer
sys.modules[f"{__name__}.AsymmetricLelandBandsEngine"] = AsymmetricLelandTurnoverOptimizer
sys.modules[f"{__name__}.LelandNoTradeBandsEngine"] = AsymmetricLelandTurnoverOptimizer

__all__ = [
    "VERSION",
    "RELEASE",
    "FEATURE",
    "VERSION_PHASE182",
    "RELEASE_PHASE182",
    "FEATURE_PHASE182",
    "VERSION_PHASE178",
    "RELEASE_PHASE178",
    "FEATURE_PHASE178",
    "VERSION_PHASE174",
    "RELEASE_PHASE174",
    "FEATURE_PHASE174",
    "VERSION_PHASE166",
    "RELEASE_PHASE166",
    "FEATURE_PHASE166",
    "LelandBufferConfig",
    "LelandExecutionOutput",
    "AsymmetricLelandTurnoverOptimizer",
    "AsymmetricLelandTurnoverOptimizerPhase182",
    "Phase182AsymmetricLelandOptimizer",
    "F893AsymmetricLelandOptimizer",
    "TurnoverOptimizerPhase182",
    "AsymmetricLelandBandsEngine",
    "AsymmetricLelandBandsEnginePhase182",
    "LelandNoTradeBandsEngine",
    "TurnoverOptimizer",
    "LelandTurnoverOptimizer",
    "compute_asymmetric_leeland_bands",
    "compute_asymmetric_leland_bands",
    "is_zero_bypass_eligible",
    "filter_portfolio_rebalance",
]
