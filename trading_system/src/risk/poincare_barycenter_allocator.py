r"""
src/risk/poincare_barycenter_allocator.py
==========================================
Poincaré-Lorentz Hyperbolic Optimal Transport Barycenter Allocator (Feature F890).
Institutional Production Master Release R180 (Phase 182).

Features Covered:
- Feature F890: Entropic Regularized Sinkhorn-Knopp Wasserstein Barycenter on the Poincaré-Lorentz Hyperbolic Cone
                Preserving Capital Mass sum(w) == L.
- Möbius Gyrovector Space Barycenter Calculus and Geodesic Displacement Interpolation.
- Seamless polymorphic compatibility with Phase 178 / Release R179.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from src.risk.hyperbolic_optimal_transport_allocator import (
    VERSION,
    RELEASE,
    FEATURE,
    VERSION_PHASE186,
    VERSION_PHASE182,
    RELEASE_PHASE186,
    RELEASE_PHASE182,
    FEATURE_PHASE186,
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
    HyperbolicRegime,
    HyperbolicAllocatorConfig,
    HyperbolicAllocationOutput,
    HyperbolicOptimalTransportAllocator,
    HyperbolicWassersteinAllocator,
    PoincareOptimalTransportAllocator,
    Phase165HyperbolicAllocator,
    PoincareHyperbolicTransportAllocator,
    LorentzPoincareWassersteinAllocator,
    HyperbolicOptimalTransportAllocatorPhase178,
    Phase178HyperbolicAllocator,
    F870HyperbolicWassersteinAllocator,
    PoincareFrechetWassersteinAllocator,
    PoincareFréchetWassersteinAllocator,
    PoincareBarycenterAllocator,
    PoincareLorentzWassersteinAllocator,
    HyperbolicOptimalTransportAllocatorPhase182,
    Phase182HyperbolicAllocator,
    F890HyperbolicWassersteinAllocator,
    PoincareWassersteinBarycenterAllocator,
    mobius_addition,
    poincare_exponential_map,
    poincare_logarithmic_map,
    compute_hyperbolic_wasserstein_barycenter,
    compute_lorentz_hyperbolic_ot,
    compute_poincare_wasserstein_barycenter,
    allocate_hyperbolic_barycenter_phase182,
    allocate_hyperbolic_ot_phase186,
    compute_poincare_lorentz_ot_barycenter,
    PoincareLorentzBarycenterAllocator,
    REGIME_HYPERBOLIC_PARAMS,
    REGIME_HYPERBOLIC_PARAMS_PHASE178,
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
    "HyperbolicRegime",
    "HyperbolicAllocatorConfig",
    "HyperbolicAllocationOutput",
    "HyperbolicOptimalTransportAllocator",
    "HyperbolicWassersteinAllocator",
    "PoincareOptimalTransportAllocator",
    "Phase165HyperbolicAllocator",
    "PoincareHyperbolicTransportAllocator",
    "LorentzPoincareWassersteinAllocator",
    "HyperbolicOptimalTransportAllocatorPhase178",
    "Phase178HyperbolicAllocator",
    "F870HyperbolicWassersteinAllocator",
    "PoincareFrechetWassersteinAllocator",
    "PoincareFréchetWassersteinAllocator",
    "PoincareBarycenterAllocator",
    "PoincareLorentzWassersteinAllocator",
    "HyperbolicOptimalTransportAllocatorPhase182",
    "Phase182HyperbolicAllocator",
    "F890HyperbolicWassersteinAllocator",
    "PoincareWassersteinBarycenterAllocator",
    "mobius_addition",
    "poincare_exponential_map",
    "poincare_logarithmic_map",
    "compute_hyperbolic_wasserstein_barycenter",
    "compute_lorentz_hyperbolic_ot",
    "compute_poincare_wasserstein_barycenter",
    "allocate_hyperbolic_barycenter_phase182",
    "REGIME_HYPERBOLIC_PARAMS",
    "REGIME_HYPERBOLIC_PARAMS_PHASE178",
]
