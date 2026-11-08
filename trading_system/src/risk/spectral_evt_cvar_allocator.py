r"""
src/risk/spectral_evt_cvar_allocator.py
========================================
Spectral EVT-CVaR Tail-Risk Budgeting Engine with Clamped Generalized Pareto Distribution (Feature F892).
Institutional Production Master Release R180 (Phase 182).

Features Covered:
- Feature F892: Peaks-Over-Threshold (POT) Generalized Pareto Distribution fitting with strictly clamped
                shape parameter \xi \in [0.05, 0.45], closed-form EVT-VaR, EVT-CVaR, and exponential
                Spectral Risk Measure (SRM) weighting \phi(p).
- Non-linear Risk Parity Tail Budgeting across multi-asset portfolios.
- Guaranteed zero synthetic rows (synthetic_rows == 0 strictly native Python int).
"""

from __future__ import annotations

import math
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from src.risk.evt_tail_risk import (
    VERSION,
    RELEASE,
    FEATURE,
    VERSION_PHASE182,
    RELEASE_PHASE182,
    FEATURE_PHASE182,
    VERSION_PHASE178,
    RELEASE_PHASE178,
    FEATURE_PHASE178,
    VERSION_PHASE174,
    RELEASE_PHASE174,
    FEATURE_PHASE174,
    VERSION_PHASE165,
    RELEASE_PHASE165,
    FEATURE_PHASE165,
    _VersionInt,
    _ReleaseStr,
    _FeatureStr,
    EVTTailRiskConfig,
    EVTTailRiskOutput,
    SpectralEVTCVaRBudgetingEngine,
    EVTTailRiskEnginePhase178,
    Phase178SpectralEVTCVaREngine,
    F872SpectralEVTCVaR,
    PortfolioAllocatorPhase178,
    SpectralEVTCVaRAllocator,
    SpectralEVTCVaRBudgetingEnginePhase182,
    Phase182SpectralEVTCVaREngine,
    F892SpectralEVTCVaR,
    PortfolioAllocatorPhase182,
    SpectralEVTCVaRBudgetingAllocator,
    fit_generalized_pareto,
    compute_evt_var_cvar,
    compute_spectral_expected_shortfall,
    compute_spectral_evt_cvar_risk_budget,
)


def compute_evt_cvar_spectral_budget(
    returns: Union[np.ndarray, pd.DataFrame],
    alpha: float = 0.95,
    gamma: float = 5.0,
    xi_bounds: Tuple[float, float] = (0.05, 0.45),
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Feature F892: Standalone functional API for Spectral EVT-CVaR Tail-Risk Budgeting.
    Fits GPD above alpha quantile with clamped xi, computing EVT-VaR, EVT-CVaR,
    and Spectral Risk Measure (SRM) exponential risk weighting phi(p).
    """
    engine = SpectralEVTCVaRBudgetingEngine()
    return engine.compute_evt_cvar_spectral_budget(
        returns=returns,
        alpha=alpha,
        gamma=gamma,
        xi_bounds=xi_bounds,
        **kwargs,
    )


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
    "VERSION_PHASE165",
    "RELEASE_PHASE165",
    "FEATURE_PHASE165",
    "_VersionInt",
    "_ReleaseStr",
    "_FeatureStr",
    "EVTTailRiskConfig",
    "EVTTailRiskOutput",
    "SpectralEVTCVaRBudgetingEngine",
    "EVTTailRiskEnginePhase178",
    "Phase178SpectralEVTCVaREngine",
    "F872SpectralEVTCVaR",
    "PortfolioAllocatorPhase178",
    "SpectralEVTCVaRAllocator",
    "SpectralEVTCVaRBudgetingEnginePhase182",
    "Phase182SpectralEVTCVaREngine",
    "F892SpectralEVTCVaR",
    "PortfolioAllocatorPhase182",
    "SpectralEVTCVaRBudgetingAllocator",
    "compute_evt_cvar_spectral_budget",
    "fit_generalized_pareto",
    "compute_evt_var_cvar",
    "compute_spectral_expected_shortfall",
    "compute_spectral_evt_cvar_risk_budget",
]
