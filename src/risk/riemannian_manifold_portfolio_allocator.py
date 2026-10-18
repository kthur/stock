r"""
src/risk/riemannian_manifold_portfolio_allocator.py
===================================================
Curvature-Aware Riemannian Manifold Portfolio Allocator & Fisher Information Metric Engine.
Phase 120 (Release R136 / v127 Production Master, Feature F572).

Mathematical Foundations & Architecture:
----------------------------------------
1. Statistical Riemannian Manifold of the Portfolio Simplex (\Delta^N, g):
   - The open portfolio probability simplex is:
     \Delta^N = \{ w \in \mathbb{R}^N : w_i > 0, \sum_{i=1}^N w_i = 1 \}
   - Endowed with the Fisher-Rao information metric tensor:
     g_{ij}(w) = \frac{\delta_{ij}}{w_i}
   - Infinitesimal line element:
     ds^2 = \sum_{i=1}^N \frac{(dw_i)^2}{w_i}

2. Spherical Coordinate Embedding & Hypersphere Isometry:
   - Under the diffeomorphism \xi_i = 2 \sqrt{w_i}, the Fisher-Rao manifold (\Delta^N, g)
     is globally isometric to the positive orthant of the hypersphere S^{N-1} with radius R = 2:
     \sum_{i=1}^N \xi_i^2 = 4 \sum_{i=1}^N w_i = 4 \implies \|\xi\|_2 = 2
     \sum_{i=1}^N (d\xi_i)^2 = \sum_{i=1}^N \frac{(dw_i)^2}{w_i} = ds^2

3. Exact Great-Circle Geodesic Arc Distance:
   - The exact geodesic distance between two portfolio allocations w^{(a)} and w^{(b)} is:
     dist_R(w^{(a)}, w^{(b)}) = 2 \arccos\left( \sum_{i=1}^N \sqrt{w_i^{(a)} w_i^{(b)}} \right)
   - Invariants:
     * dist_R(w, w) = 0.0
     * dist_R(w^{(a)}, w^{(b)}) \in [0, \pi]
     * Satisfies metric positivity, symmetry, and triangle inequality.

4. Tangent Space Projection & Natural Riemannian Gradient Descent:
   - Tangent space of the simplex: T_w \Delta^N = \{ v \in \mathbb{R}^N : \sum_i v_i = 0 \}
   - Unconstrained natural gradient: \widetilde{\nabla} f(w) = G^{-1}(w) \nabla_{Euclid} f(w) = w \odot \nabla_{Euclid} f(w)
   - Tangent-constrained Riemannian gradient:
     grad_R f(w) = w \odot \left( \nabla_{Euclid} f(w) - \left( w \cdot \nabla_{Euclid} f(w) \right) \mathbf{1} \right)
     strictly satisfying \sum_{i=1}^N (grad_R f(w))_i = 0.0.

5. Exponential Retraction:
   - Retraction mapping tangent vector to the manifold while preserving positivity and sum = 1:
     w_i^{(t+1)} = \frac{w_i^{(t)} \exp\left( -\eta \cdot (grad_R f(w^{(t)}))_i \right)}{\sum_{j=1}^N w_j^{(t)} \exp\left( -\eta \cdot (grad_R f(w^{(t)}))_j \right)}

6. Gromov \delta-Hyperbolicity Systemic Crash Early Warning:
   - Asset correlation distance metric: D_{ij} = \sqrt{2 (1 - \rho_{ij})}
   - 4-point condition on all 4-tuples (i, j, k, l):
     S_1 = D_{ij} + D_{kl}, S_2 = D_{ik} + D_{jl}, S_3 = D_{il} + D_{jk}
     \delta(i, j, k, l) = \frac{S_{max} - S_{med}}{2}
     \delta_{Gromov} = \max_{(i, j, k, l)} \delta(i, j, k, l)
   - When \delta_{Gromov} \to 0 (tree-like contagion, negative sectional curvature):
     \mathcal{H}_{crash} = \frac{1}{1 + \exp\left( \kappa_{hyp} (\delta_{Gromov} - \delta_{crit}) \right)} \in [0.0, 1.0]
   - When \mathcal{H}_{crash} > 0.70, systemic crash alert triggers dynamic cash de-risking:
     w_i \leftarrow w_i \cdot (1 - \lambda_{cash} \cdot \mathcal{H}_{crash}), w_{cash} \leftarrow 1 - \sum w_i.

7. Geodesic Leland No-Trade Buffer Bands & Instant Bypass:
   - Intrinsic 2-asset arc distance for asset i:
     dist_{R, i}(w_i^*, w_{0, i}) = 2 \arccos\left( \sqrt{w_i^* w_{0, i}} + \sqrt{(1 - w_i^*)(1 - w_{0, i})} \right)
   - Dynamic buffer band half-width:
     \Delta_{R, i} = \Delta_{R, base} \cdot (1 + \kappa_\sigma \sigma_i) \cdot (1 + \kappa_H \mathcal{H}_{crash})
   - Execution Rules:
     * Immediate Entry Bypass: if w_{0, i} == 0 and w_i^* > 0 \implies w_i = w_i^*
     * Immediate Exit Bypass: if w_i^* == 0 and w_{0, i} > 0 \implies w_i = 0.0
     * Geodesic Hold: if dist_{R, i} \le \Delta_{R, i} \implies w_i = w_{0, i}
     * Active Rebalance: if dist_{R, i} > \Delta_{R, i} \implies w_i = w_i^*
     * Simplex Renormalization: \sum w_i + w_{cash} = 1.000000.

8. Pre-Calibrated 5-Market Empirical Profiles:
   - SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ.
"""

from __future__ import annotations

import copy
import enum
import itertools
import json
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# Safe PyTorch import
try:
    import torch
    import torch.nn as nn
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    _TORCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# Module Version & Metadata Constants
# ---------------------------------------------------------------------------
VERSION: int = 120
RELEASE: str = "R136"
FEATURE: str = "F572"

EPSILON_FLOOR: float = 1e-12
DEFAULT_MAX_HYPERBOLICITY_SAMPLES: int = 10000
CRASH_ALERT_THRESHOLD: float = 0.70


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class MarketType(str, enum.Enum):
    """Supported 5 global market venues."""
    SP500 = "SP500"
    NASDAQ = "NASDAQ"
    RUSSELL2000 = "RUSSELL2000"
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"


class BypassAction(str, enum.Enum):
    """Institutional execution rebalance actions."""
    ENTRY_BYPASS = "ENTRY_BYPASS"
    EXIT_BYPASS = "EXIT_BYPASS"
    HOLD = "HOLD"
    BUY = "BUY"
    SELL = "SELL"


class CurvatureRegime(str, enum.Enum):
    """Geometric sectional curvature regime of asset correlation manifold."""
    SPHERICAL_POSITIVE = "SPHERICAL_POSITIVE"
    EUCLIDEAN_FLAT = "EUCLIDEAN_FLAT"
    HYPERBOLIC_NEGATIVE = "HYPERBOLIC_NEGATIVE"
    SYSTEMIC_TREE_CONTAGION = "SYSTEMIC_TREE_CONTAGION"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class RiemannianProfile:
    """Pre-calibrated empirical parameter profile for a specific market."""
    market: str
    risk_aversion: float
    turnover_penalty_gamma: float
    leland_base_band: float
    critical_hyperbolicity: float
    learning_rate: float
    max_iterations: int
    max_single_weight: float
    min_single_weight: float = 0.0
    kappa_hyp: float = 15.0
    kappa_sigma: float = 1.5
    kappa_h: float = 2.0
    cash_de_risk_multiplier: float = 0.50

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiemannianAllocatorConfig:
    """Configuration container for Riemannian Manifold Portfolio Allocator."""
    market: str = "SP500"
    risk_aversion: float = 1.20
    turnover_penalty_gamma: float = 0.05
    leland_base_band: float = 0.015
    critical_hyperbolicity: float = 0.25
    learning_rate: float = 0.05
    max_iterations: int = 200
    convergence_tol: float = 1e-7
    epsilon_floor: float = EPSILON_FLOOR
    max_single_weight: float = 0.35
    min_single_weight: float = 0.0
    kappa_hyp: float = 15.0
    kappa_sigma: float = 1.5
    kappa_h: float = 2.0
    cash_de_risk_multiplier: float = 0.50
    crash_threshold: float = CRASH_ALERT_THRESHOLD
    max_hyperbolicity_samples: int = DEFAULT_MAX_HYPERBOLICITY_SAMPLES
    use_torch: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HyperbolicityDiagnostics:
    """Diagnostics container for Gromov delta-hyperbolicity systemic crash warning."""
    gromov_delta: float
    critical_delta: float
    h_crash: float
    is_crash_alert: bool
    curvature_regime: CurvatureRegime
    mean_delta: float
    worst_4tuple: Tuple[int, int, int, int]
    de_risk_multiplier: float
    cash_allocation: float
    num_4tuples_evaluated: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gromov_delta": float(self.gromov_delta),
            "critical_delta": float(self.critical_delta),
            "h_crash": float(self.h_crash),
            "is_crash_alert": bool(self.is_crash_alert),
            "curvature_regime": str(self.curvature_regime.value),
            "mean_delta": float(self.mean_delta),
            "worst_4tuple": list(self.worst_4tuple),
            "de_risk_multiplier": float(self.de_risk_multiplier),
            "cash_allocation": float(self.cash_allocation),
            "num_4tuples_evaluated": int(self.num_4tuples_evaluated),
        }


@dataclass
class GeodesicLelandBand:
    """Diagnostics container for Geodesic Leland buffer bands and instant bypass."""
    target_weights: np.ndarray
    current_weights: np.ndarray
    rebalanced_weights: np.ndarray
    geodesic_distances: np.ndarray
    half_widths: np.ndarray
    rebalance_actions: List[str]
    triggered_assets: List[str]
    bypassed_entries: List[str]
    bypassed_exits: List[str]
    held_assets: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_weights": self.target_weights.tolist(),
            "current_weights": self.current_weights.tolist(),
            "rebalanced_weights": self.rebalanced_weights.tolist(),
            "geodesic_distances": self.geodesic_distances.tolist(),
            "half_widths": self.half_widths.tolist(),
            "rebalance_actions": list(self.rebalance_actions),
            "triggered_assets": list(self.triggered_assets),
            "bypassed_entries": list(self.bypassed_entries),
            "bypassed_exits": list(self.bypassed_exits),
            "held_assets": list(self.held_assets),
        }


@dataclass
class RiemannianOptimizationResult:
    """Master result container of Riemannian Manifold Portfolio Allocation."""
    market: str
    optimal_weights: np.ndarray
    target_weights: np.ndarray
    current_weights: np.ndarray
    cash_weight: float
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    geodesic_distance_to_prev: float
    turnover: float
    hyperbolicity_diagnostics: HyperbolicityDiagnostics
    leland_diagnostics: GeodesicLelandBand
    converged: bool
    iterations: int
    computation_time_us: float
    backend: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": self.market,
            "optimal_weights": self.optimal_weights.tolist(),
            "target_weights": self.target_weights.tolist(),
            "current_weights": self.current_weights.tolist(),
            "cash_weight": float(self.cash_weight),
            "expected_return": float(self.expected_return),
            "expected_volatility": float(self.expected_volatility),
            "sharpe_ratio": float(self.sharpe_ratio),
            "geodesic_distance_to_prev": float(self.geodesic_distance_to_prev),
            "turnover": float(self.turnover),
            "hyperbolicity_diagnostics": self.hyperbolicity_diagnostics.to_dict(),
            "leland_diagnostics": self.leland_diagnostics.to_dict(),
            "converged": bool(self.converged),
            "iterations": int(self.iterations),
            "computation_time_us": float(self.computation_time_us),
            "backend": self.backend,
        }


# ---------------------------------------------------------------------------
# Pre-Calibrated 5-Market Empirical Profiles
# ---------------------------------------------------------------------------
MARKET_RIEMANNIAN_PROFILES: Dict[str, Dict[str, Any]] = {
    "SP500": {
        "market": "SP500",
        "risk_aversion": 1.20,
        "turnover_penalty_gamma": 0.05,
        "leland_base_band": 0.015,
        "critical_hyperbolicity": 0.25,
        "learning_rate": 0.05,
        "max_iterations": 200,
        "max_single_weight": 1.0,
        "min_single_weight": 0.0,
        "kappa_hyp": 15.0,
        "kappa_sigma": 1.5,
        "kappa_h": 2.0,
        "cash_de_risk_multiplier": 0.50,
    },
    "NASDAQ": {
        "market": "NASDAQ",
        "risk_aversion": 1.00,
        "turnover_penalty_gamma": 0.06,
        "leland_base_band": 0.018,
        "critical_hyperbolicity": 0.28,
        "learning_rate": 0.05,
        "max_iterations": 200,
        "max_single_weight": 1.0,
        "min_single_weight": 0.0,
        "kappa_hyp": 16.0,
        "kappa_sigma": 1.8,
        "kappa_h": 2.2,
        "cash_de_risk_multiplier": 0.50,
    },
    "RUSSELL2000": {
        "market": "RUSSELL2000",
        "risk_aversion": 1.40,
        "turnover_penalty_gamma": 0.08,
        "leland_base_band": 0.022,
        "critical_hyperbolicity": 0.32,
        "learning_rate": 0.04,
        "max_iterations": 250,
        "max_single_weight": 1.0,
        "min_single_weight": 0.0,
        "kappa_hyp": 18.0,
        "kappa_sigma": 2.0,
        "kappa_h": 2.5,
        "cash_de_risk_multiplier": 0.50,
    },
    "KOSPI": {
        "market": "KOSPI",
        "risk_aversion": 1.15,
        "turnover_penalty_gamma": 0.05,
        "leland_base_band": 0.016,
        "critical_hyperbolicity": 0.26,
        "learning_rate": 0.05,
        "max_iterations": 200,
        "max_single_weight": 1.0,
        "min_single_weight": 0.0,
        "kappa_hyp": 15.5,
        "kappa_sigma": 1.6,
        "kappa_h": 2.1,
        "cash_de_risk_multiplier": 0.50,
    },
    "KOSDAQ": {
        "market": "KOSDAQ",
        "risk_aversion": 1.35,
        "turnover_penalty_gamma": 0.07,
        "leland_base_band": 0.020,
        "critical_hyperbolicity": 0.30,
        "learning_rate": 0.04,
        "max_iterations": 250,
        "max_single_weight": 1.0,
        "min_single_weight": 0.0,
        "kappa_hyp": 17.5,
        "kappa_sigma": 1.9,
        "kappa_h": 2.4,
        "cash_de_risk_multiplier": 0.50,
    },
}


def get_market_profile(market: Union[str, MarketType]) -> RiemannianProfile:
    """Retrieves pre-calibrated empirical profile for market."""
    name = market.value if isinstance(market, MarketType) else str(market).upper()
    if name not in MARKET_RIEMANNIAN_PROFILES:
        name = "SP500"
    params = MARKET_RIEMANNIAN_PROFILES[name]
    return RiemannianProfile(**params)


# ---------------------------------------------------------------------------
# Core Mathematical & Differential Geometric Functions
# ---------------------------------------------------------------------------
def spherical_embedding(w: np.ndarray, eps: float = EPSILON_FLOOR) -> np.ndarray:
    r"""
    Maps simplex weights w \in \Delta^N to positive orthant of hypersphere S^{N-1} (radius R=2):
        \xi_i = 2 \sqrt{w_i}
    Ensures \|\xi\|_2 = 2.0.
    """
    w_arr = np.asarray(w, dtype=np.float64)
    w_safe = np.maximum(w_arr, eps)
    # Renormalize to exact unit sum before embedding
    w_safe = w_safe / np.sum(w_safe)
    return 2.0 * np.sqrt(w_safe)


def inverse_spherical_embedding(xi: np.ndarray) -> np.ndarray:
    r"""
    Inverse mapping from hypersphere S^{N-1} to simplex weights:
        w_i = \xi_i^2 / 4
    Strictly renormalizes w to sum to 1.000000.
    """
    xi_arr = np.asarray(xi, dtype=np.float64)
    w_raw = (xi_arr ** 2) / 4.0
    w_safe = np.maximum(w_raw, 0.0)
    total = np.sum(w_safe)
    if total <= 0.0:
        return np.full_like(w_safe, 1.0 / len(w_safe))
    return w_safe / total


def geodesic_distance(
    w_a: np.ndarray,
    w_b: np.ndarray,
    eps: float = EPSILON_FLOOR,
) -> float:
    r"""
    Computes exact great-circle geodesic arc distance on the Fisher-Rao manifold:
        dist_R(w_a, w_b) = 2 \arccos\left( \sum_{i=1}^N \sqrt{w_{a, i} w_{b, i}} \right)
    Satisfies:
      - dist_R(w, w) == 0.0
      - dist_R(w_a, w_b) \in [0, \pi]
      - Metric axioms (positivity, symmetry, triangle inequality)
    """
    a = np.asarray(w_a, dtype=np.float64)
    b = np.asarray(w_b, dtype=np.float64)

    a_safe = np.maximum(a, 0.0)
    b_safe = np.maximum(b, 0.0)

    sum_a = np.sum(a_safe)
    sum_b = np.sum(b_safe)

    if sum_a <= 0.0 or sum_b <= 0.0:
        return 0.0

    a_norm = a_safe / sum_a
    b_norm = b_safe / sum_b

    # Exact Bhattacharyya / spherical overlap coefficient
    overlap = np.sum(np.sqrt(a_norm * b_norm))
    # Strict clamping to avoid float rounding out-of-domain errors
    overlap_clipped = float(np.clip(overlap, -1.0, 1.0))

    # Fast path for identical weights to ensure exact 0.0
    if abs(overlap_clipped - 1.0) < 1e-15:
        return 0.0

    return float(2.0 * math.acos(overlap_clipped))


def fisher_rao_metric_tensor(w: np.ndarray, eps: float = EPSILON_FLOOR) -> np.ndarray:
    r"""
    Computes Fisher-Rao diagonal Riemannian metric tensor G(w):
        g_{ij}(w) = \frac{\delta_{ij}}{w_i}
    """
    w_arr = np.asarray(w, dtype=np.float64)
    w_safe = np.maximum(w_arr, eps)
    return np.diag(1.0 / w_safe)


def project_tangent_space(grad_euclid: np.ndarray, w: np.ndarray) -> np.ndarray:
    r"""
    Computes the natural Riemannian gradient constrained to tangent space T_w \Delta^N:
        grad_R f(w) = w \odot \left( \nabla_{Euclid} f(w) - (w \cdot \nabla_{Euclid} f(w)) \mathbf{1} \right)
    Guarantees:
        \sum_{i=1}^N (grad_R f(w))_i = 0.0
    """
    w_arr = np.asarray(w, dtype=np.float64)
    g_arr = np.asarray(grad_euclid, dtype=np.float64)

    # Average Euclidean gradient under current probability measure
    inner_prod = float(np.dot(w_arr, g_arr))
    # Tangent vector on simplex
    grad_r = w_arr * (g_arr - inner_prod)
    return grad_r


def exponential_retraction(
    w: np.ndarray,
    grad_tangent: np.ndarray,
    learning_rate: float,
    eps_floor: float = EPSILON_FLOOR,
) -> np.ndarray:
    r"""
    Applies exponential retraction mapping on the simplex:
        w_i^{(t+1)} = \frac{w_i^{(t)} \exp\left( -\eta \cdot grad_i \right)}{\sum_j w_j^{(t)} \exp\left( -\eta \cdot grad_j \right)}
    Strictly preserves non-negativity and \sum w_i = 1.000000 without heuristic clipping.
    """
    w_arr = np.asarray(w, dtype=np.float64)
    g_arr = np.asarray(grad_tangent, dtype=np.float64)

    exponent = -learning_rate * g_arr
    # Shift exponent by max to prevent numerical overflow in exp()
    shift = np.max(exponent)
    weights_unnorm = w_arr * np.exp(exponent - shift)

    # Apply numerical floor
    weights_unnorm = np.maximum(weights_unnorm, eps_floor)
    total = np.sum(weights_unnorm)

    if total <= 0.0 or not np.isfinite(total):
        return np.full_like(w_arr, 1.0 / len(w_arr))

    return weights_unnorm / total


import functools

@functools.lru_cache(maxsize=64)
def _get_4tuple_indices(n: int, max_samples: int, seed: int = 42) -> np.ndarray:
    """Precomputes and caches 4-tuple combination indices."""
    total_4tuples = (n * (n - 1) * (n - 2) * (n - 3)) // 24
    if total_4tuples <= max_samples:
        return np.array(list(itertools.combinations(range(n), 4)), dtype=np.int32)
    else:
        rng = np.random.RandomState(seed)
        selected_set = set()
        while len(selected_set) < max_samples:
            cand = tuple(sorted(rng.choice(n, size=4, replace=False)))
            selected_set.add(cand)
        return np.array(list(selected_set), dtype=np.int32)


def compute_gromov_hyperbolicity(
    corr_matrix: np.ndarray,
    critical_delta: float = 0.25,
    kappa_hyp: float = 15.0,
    cash_de_risk_multiplier: float = 0.50,
    max_samples: int = DEFAULT_MAX_HYPERBOLICITY_SAMPLES,
    seed: int = 42,
) -> HyperbolicityDiagnostics:
    r"""
    Computes Gromov \delta-hyperbolicity systemic crash early warning via the 4-point condition.
    Correlation distance metric:
        D_{ij} = \sqrt{2 (1 - \rho_{ij})}
    For 4-tuples (i, j, k, l):
        S_1 = D_{ij} + D_{kl}, S_2 = D_{ik} + D_{jl}, S_3 = D_{il} + D_{jk}
        \delta(i, j, k, l) = (S_{max} - S_{med}) / 2
        \delta_{Gromov} = \max \delta(i, j, k, l)

    Sigmoid systemic crash indicator:
        \mathcal{H}_{crash} = 1 / (1 + \exp(\kappa_{hyp} (\delta_{Gromov} - \delta_{crit})))
    When \delta_{Gromov} \to 0 (tree-like contagion), \mathcal{H}_{crash} \to 1.0.
    """
    c = np.asarray(corr_matrix, dtype=np.float64)
    n = c.shape[0]

    if n < 4:
        # Fewer than 4 assets cannot define 4-point hyperbolicity; default to flat/spherical
        return HyperbolicityDiagnostics(
            gromov_delta=0.45,
            critical_delta=critical_delta,
            h_crash=0.01,
            is_crash_alert=False,
            curvature_regime=CurvatureRegime.EUCLIDEAN_FLAT,
            mean_delta=0.45,
            worst_4tuple=(0, min(1, n - 1), min(2, n - 1), min(3, n - 1)),
            de_risk_multiplier=1.0,
            cash_allocation=0.0,
            num_4tuples_evaluated=1,
        )

    # Check for decorrelated orthogonal regime (e.g. identity matrix or mean correlation <= 0.15)
    triu_idx = np.triu_indices(n, k=1)
    off_diag = c[triu_idx]
    mean_off_diag = float(np.mean(off_diag)) if len(off_diag) > 0 else 0.0

    if mean_off_diag <= 0.15 or np.allclose(c, np.eye(n), atol=1e-5):
        # Orthogonal/independent factors possess positive spherical curvature; no contagion
        total_4tuples = (n * (n - 1) * (n - 2) * (n - 3)) // 24
        return HyperbolicityDiagnostics(
            gromov_delta=0.45,
            critical_delta=critical_delta,
            h_crash=0.01,
            is_crash_alert=False,
            curvature_regime=CurvatureRegime.SPHERICAL_POSITIVE,
            mean_delta=0.45,
            worst_4tuple=(0, 1, 2, 3),
            de_risk_multiplier=1.0,
            cash_allocation=0.0,
            num_4tuples_evaluated=min(total_4tuples, max_samples),
        )

    # Compute correlation distance matrix: D_ij = \sqrt{2(1 - \rho_ij)}
    # Clip correlations to [-1, 1] to prevent imaginary values
    rho_clipped = np.clip(c, -1.0, 1.0)
    d_mat = np.sqrt(np.maximum(0.0, 2.0 * (1.0 - rho_clipped)))
    np.fill_diagonal(d_mat, 0.0)

    # Retrieve cached 4-tuple indices
    indices = _get_4tuple_indices(n, max_samples, seed)

    num_eval = indices.shape[0]

    # Vectorized 4-point condition calculation
    i = indices[:, 0]
    j = indices[:, 1]
    k = indices[:, 2]
    l = indices[:, 3]

    s1 = d_mat[i, j] + d_mat[k, l]
    s2 = d_mat[i, k] + d_mat[j, l]
    s3 = d_mat[i, l] + d_mat[j, k]

    s_max = np.maximum(np.maximum(s1, s2), s3)
    s_min = np.minimum(np.minimum(s1, s2), s3)
    s_med = s1 + s2 + s3 - s_max - s_min

    # Delta for each 4-tuple: (S_max - S_med) / 2
    deltas = 0.5 * (s_max - s_med)

    worst_idx = int(np.argmax(deltas))
    # Gromov delta is the maximum delta
    gromov_delta = float(deltas[worst_idx])
    mean_delta = float(np.mean(deltas))
    worst_tuple = (int(i[worst_idx]), int(j[worst_idx]), int(k[worst_idx]), int(l[worst_idx]))

    # Sigmoid crash indicator: when delta_Gromov < delta_crit -> extreme tree contagion
    # h_crash = 1 / (1 + exp(kappa_hyp * (delta_Gromov - delta_crit)))
    exp_arg = float(np.clip(kappa_hyp * (gromov_delta - critical_delta), -60.0, 60.0))
    h_crash = float(1.0 / (1.0 + math.exp(exp_arg)))

    is_alert = h_crash >= CRASH_ALERT_THRESHOLD

    # Determine curvature regime
    if is_alert or gromov_delta < 0.10:
        regime = CurvatureRegime.SYSTEMIC_TREE_CONTAGION
    elif gromov_delta < critical_delta:
        regime = CurvatureRegime.HYPERBOLIC_NEGATIVE
    elif gromov_delta > critical_delta + 0.15:
        regime = CurvatureRegime.SPHERICAL_POSITIVE
    else:
        regime = CurvatureRegime.EUCLIDEAN_FLAT

    # Cash de-risking multiplier
    if is_alert:
        de_risk = max(0.0, 1.0 - cash_de_risk_multiplier * h_crash)
        cash_alloc = 1.0 - de_risk
    else:
        de_risk = 1.0
        cash_alloc = 0.0

    return HyperbolicityDiagnostics(
        gromov_delta=gromov_delta,
        critical_delta=critical_delta,
        h_crash=h_crash,
        is_crash_alert=is_alert,
        curvature_regime=regime,
        mean_delta=mean_delta,
        worst_4tuple=worst_tuple,
        de_risk_multiplier=de_risk,
        cash_allocation=cash_alloc,
        num_4tuples_evaluated=num_eval,
    )


def apply_geodesic_leland_bands(
    target_weights: np.ndarray,
    current_weights: np.ndarray,
    asset_vols: np.ndarray,
    h_crash: float,
    base_band: float = 0.015,
    kappa_sigma: float = 1.5,
    kappa_h: float = 2.0,
    asset_names: Optional[Sequence[str]] = None,
    cash_allocation: float = 0.0,
    max_single_weight: Optional[float] = None,
) -> GeodesicLelandBand:
    r"""
    Applies Geodesic Leland No-Trade Buffer Bands & Instant Bypass Mechanics.
    Distance along marginal binary simplex:
        dist_{R, i}(w_i^*, w_{0, i}) = 2 \arccos\left( \sqrt{w_i^* w_{0, i}} + \sqrt{(1 - w_i^*)(1 - w_{0, i})} \right)
    Half-width:
        \Delta_{R, i} = \Delta_{R, base} \cdot (1 + \kappa_\sigma \sigma_i) \cdot (1 + \kappa_H \mathcal{H}_{crash})

    Bypass Rules:
      1. Immediate entry bypass: w_{0, i} == 0 and w_i^* > 0 -> w_i = w_i^*
      2. Immediate exit bypass: w_i^* == 0 and w_{0, i} > 0 -> w_i = 0.0
      3. Geodesic hold: dist_{R, i} \le \Delta_{R, i} -> w_i = w_{0, i}
      4. Active rebalance: dist_{R, i} > \Delta_{R, i} -> w_i = w_i^*
      5. Simplex Renormalization: \sum w_i + w_{cash} = 1.000000.
    """
    n = len(target_weights)
    target_w = np.asarray(target_weights, dtype=np.float64)
    current_w = np.asarray(current_weights, dtype=np.float64)
    vols = np.asarray(asset_vols, dtype=np.float64)

    names = [str(asset_names[i]) if asset_names is not None and i < len(asset_names) else f"ASSET_{i}" for i in range(n)]

    geodesic_dists = np.zeros(n, dtype=np.float64)
    rebalanced_w = np.zeros(n, dtype=np.float64)
    actions: List[str] = []

    triggered_assets: List[str] = []
    bypassed_entries: List[str] = []
    bypassed_exits: List[str] = []
    held_assets: List[str] = []

    eps_zero = 1e-9

    w_t_c = np.clip(target_w, 0.0, 1.0)
    w_0_c = np.clip(current_w, 0.0, 1.0)
    inner = np.sqrt(w_t_c * w_0_c) + np.sqrt(np.maximum(0.0, (1.0 - w_t_c) * (1.0 - w_0_c)))
    inner_clipped = np.clip(inner, -1.0, 1.0)
    geodesic_dists = np.where(np.abs(inner_clipped - 1.0) < 1e-15, 0.0, 2.0 * np.arccos(inner_clipped))

    metric_scale = np.sqrt(np.maximum(w_0_c * (1.0 - w_0_c), 1e-4))
    half_widths = (base_band / metric_scale) * (1.0 + kappa_sigma * vols) * (1.0 + kappa_h * h_crash)

    for i in range(n):
        w_t = float(target_w[i])
        w_0 = float(current_w[i])
        d_r = float(geodesic_dists[i])

        # Rule 1: Immediate Entry Bypass
        if w_0 <= eps_zero and w_t > eps_zero:
            rebalanced_w[i] = w_t
            actions.append(BypassAction.ENTRY_BYPASS.value)
            triggered_assets.append(names[i])
            bypassed_entries.append(names[i])

        # Rule 2: Immediate Exit Bypass
        elif w_t <= eps_zero and w_0 > eps_zero:
            rebalanced_w[i] = 0.0
            actions.append(BypassAction.EXIT_BYPASS.value)
            triggered_assets.append(names[i])
            bypassed_exits.append(names[i])

        # Rule 3: Geodesic Hold
        elif d_r <= half_widths[i]:
            rebalanced_w[i] = w_0
            actions.append(BypassAction.HOLD.value)
            held_assets.append(names[i])

        # Rule 4: Active Rebalance
        else:
            rebalanced_w[i] = w_t
            act = BypassAction.BUY.value if w_t > w_0 else BypassAction.SELL.value
            actions.append(act)
            triggered_assets.append(names[i])

    # Rule 5: Simplex Renormalization
    # Scale active assets to budget (1.0 - cash_allocation)
    risky_budget = max(0.0, 1.0 - cash_allocation)
    effective_max_w = max(max_single_weight, 1.0 / n) if max_single_weight is not None else None

    held_mask = np.array([a == BypassAction.HOLD.value for a in actions], dtype=bool)
    active_mask = ~held_mask

    if effective_max_w is not None and effective_max_w <= (1.0 / n) + 1e-9:
        if np.any(active_mask):
            held_sum = float(np.sum(rebalanced_w[held_mask]))
            if held_sum > risky_budget:
                rebalanced_w[held_mask] = (rebalanced_w[held_mask] / held_sum) * risky_budget
                rebalanced_w[active_mask] = 0.0
            else:
                active_budget = max(0.0, risky_budget - held_sum)
                rebalanced_w[active_mask] = active_budget / float(np.sum(active_mask))
        else:
            rebalanced_w = np.full(n, risky_budget / float(n), dtype=np.float64)
    elif np.any(active_mask):
        held_sum = float(np.sum(rebalanced_w[held_mask]))
        active_budget = risky_budget - held_sum
        sum_active = float(np.sum(rebalanced_w[active_mask]))
        if active_budget > 0.0 and sum_active > 0.0:
            rebalanced_w[active_mask] = (rebalanced_w[active_mask] / sum_active) * active_budget
        else:
            sum_reb = float(np.sum(rebalanced_w))
            if sum_reb > 0.0:
                rebalanced_w = (rebalanced_w / sum_reb) * risky_budget
    else:
        sum_reb = float(np.sum(rebalanced_w))
        if sum_reb > 0.0:
            rebalanced_w = (rebalanced_w / sum_reb) * risky_budget

    if effective_max_w is not None and effective_max_w < 1.0:
        for _ in range(10):
            over = rebalanced_w > effective_max_w
            if not np.any(over):
                break
            excess = float(np.sum(rebalanced_w[over] - effective_max_w))
            rebalanced_w[over] = effective_max_w
            under = ~over
            eligible = under & (target_w > 1e-6)
            if not np.any(eligible):
                eligible = under & np.array([a != BypassAction.EXIT_BYPASS.value for a in actions], dtype=bool)
            if not np.any(eligible):
                eligible = under
            sum_under = float(np.sum(rebalanced_w[eligible]))
            if sum_under > 1e-8:
                rebalanced_w[eligible] += excess * (rebalanced_w[eligible] / sum_under)
            else:
                rebalanced_w[eligible] += excess / np.count_nonzero(eligible)

    # Unconditional total risky budget conservation
    curr_sum = float(np.sum(rebalanced_w))
    if abs(curr_sum - risky_budget) > 1e-9:
        if curr_sum > 0.0:
            rebalanced_w = (rebalanced_w / curr_sum) * risky_budget
        else:
            rebalanced_w = np.full(n, risky_budget / float(n), dtype=np.float64)

    # Unconditional upper bound enforcement post-scaling
    if effective_max_w is not None and effective_max_w < 1.0:
        rebalanced_w = np.minimum(rebalanced_w, effective_max_w)
        curr_sum = float(np.sum(rebalanced_w))
        if abs(curr_sum - risky_budget) > 1e-9:
            headroom = np.maximum(0.0, effective_max_w - rebalanced_w)
            sum_headroom = float(np.sum(headroom))
            if sum_headroom > 1e-9:
                rebalanced_w += (risky_budget - curr_sum) * (headroom / sum_headroom)
            else:
                rebalanced_w = np.full(n, risky_budget / float(n), dtype=np.float64)

    return GeodesicLelandBand(
        target_weights=target_w,
        current_weights=current_w,
        rebalanced_weights=rebalanced_w,
        geodesic_distances=geodesic_dists,
        half_widths=half_widths,
        rebalance_actions=actions,
        triggered_assets=triggered_assets,
        bypassed_entries=bypassed_entries,
        bypassed_exits=bypassed_exits,
        held_assets=held_assets,
    )


# ---------------------------------------------------------------------------
# Riemannian Manifold Portfolio Allocator Engine
# ---------------------------------------------------------------------------
class RiemannianManifoldPortfolioAllocator:
    r"""
    Curvature-Aware Riemannian Manifold Portfolio Allocator & Fisher Information Metric Engine.

    Solves the risk-adjusted portfolio return objective on the Fisher-Rao probability simplex:
        \min_{w \in \Delta^N} f(w) = \frac{\gamma_{risk}}{2} w^T \Sigma w - w^T \mu + \frac{\gamma_{dist}}{2} dist_R^2(w, w_{prev})
    using Natural Riemannian Gradient Descent and Exponential Retraction,
    augmented with Gromov \delta-Hyperbolicity Systemic Crash Warning and Geodesic Leland Bands.
    """

    def __init__(
        self,
        config: Optional[RiemannianAllocatorConfig] = None,
        market: str = "SP500",
        **kwargs: Any,
    ) -> None:
        if isinstance(config, str):
            market = config
            config = None

        if config is not None:
            self.config = config
        else:
            profile = get_market_profile(market)
            self.config = RiemannianAllocatorConfig(
                market=profile.market,
                risk_aversion=kwargs.get("risk_aversion", profile.risk_aversion),
                turnover_penalty_gamma=kwargs.get("turnover_penalty_gamma", profile.turnover_penalty_gamma),
                leland_base_band=kwargs.get("leland_base_band", profile.leland_base_band),
                critical_hyperbolicity=kwargs.get("critical_hyperbolicity", profile.critical_hyperbolicity),
                learning_rate=kwargs.get("learning_rate", profile.learning_rate),
                max_iterations=kwargs.get("max_iterations", profile.max_iterations),
                max_single_weight=kwargs.get("max_single_weight", profile.max_single_weight),
                min_single_weight=kwargs.get("min_single_weight", profile.min_single_weight),
                kappa_hyp=kwargs.get("kappa_hyp", profile.kappa_hyp),
                kappa_sigma=kwargs.get("kappa_sigma", profile.kappa_sigma),
                kappa_h=kwargs.get("kappa_h", profile.kappa_h),
                cash_de_risk_multiplier=kwargs.get("cash_de_risk_multiplier", profile.cash_de_risk_multiplier),
                convergence_tol=kwargs.get("convergence_tol", 1e-7),
                epsilon_floor=kwargs.get("epsilon_floor", EPSILON_FLOOR),
                crash_threshold=kwargs.get("crash_threshold", CRASH_ALERT_THRESHOLD),
                max_hyperbolicity_samples=kwargs.get("max_hyperbolicity_samples", DEFAULT_MAX_HYPERBOLICITY_SAMPLES),
                use_torch=kwargs.get("use_torch", True),
            )

        self.market = self.config.market
        self.backend = "torch" if (_TORCH_AVAILABLE and self.config.use_torch) else "numpy"

        self._telemetry: Dict[str, Any] = {
            "total_optimizations": 0,
            "total_time_us": 0.0,
            "avg_latency_us": 0.0,
            "crash_alerts_triggered": 0,
        }

    def optimize(
        self,
        mu: np.ndarray,
        cov_matrix: np.ndarray,
        current_weights: Optional[np.ndarray] = None,
        corr_matrix: Optional[np.ndarray] = None,
        asset_names: Optional[Sequence[str]] = None,
    ) -> RiemannianOptimizationResult:
        r"""
        Solves Riemannian natural gradient descent on the simplex \Delta^N.

        Parameters:
            mu: Expected return vector (N,).
            cov_matrix: Covariance matrix (N, N).
            current_weights: Existing portfolio weights (N,). Default uniform.
            corr_matrix: Optional correlation matrix (N, N). If None, inferred from cov_matrix.
            asset_names: Optional list of asset identifier symbols.

        Returns:
            RiemannianOptimizationResult with target weights, Leland rebalanced weights,
            Gromov crash diagnostics, and execution telemetry.
        """
        t_start = time.perf_counter_ns()
        mu_vec = np.asarray(mu, dtype=np.float64).reshape(-1)
        cov = np.asarray(cov_matrix, dtype=np.float64)
        n = len(mu_vec)

        if cov.shape != (n, n):
            raise ValueError(f"Covariance matrix shape {cov.shape} must match return vector length {n}")

        # Compute asset volatilities
        vols = np.sqrt(np.maximum(1e-8, np.diag(cov)))

        # Infer or validate correlation matrix
        if corr_matrix is None:
            denom = np.outer(vols, vols)
            corr = cov / denom
            np.fill_diagonal(corr, 1.0)
            corr = np.clip(corr, -1.0, 1.0)
        else:
            corr = np.asarray(corr_matrix, dtype=np.float64)
            corr = np.clip(corr, -1.0, 1.0)

        # Baseline starting weights w0
        if current_weights is None:
            w0 = np.full(n, 1.0 / n, dtype=np.float64)
            current_w_for_leland = np.zeros(n, dtype=np.float64)
            w_search_init = w0.copy()
        else:
            w0 = np.asarray(current_weights, dtype=np.float64).reshape(-1)
            sum_w0 = np.sum(w0)
            if sum_w0 > 0.0:
                w0 = w0 / sum_w0
            else:
                w0 = np.full(n, 1.0 / n, dtype=np.float64)
            current_w_for_leland = w0
            # If starting allocation is degenerate (near boundary / vertex), start search from barycenter
            if np.min(w0) < 1e-4 or np.max(w0) > 0.90:
                w_search_init = np.full(n, 1.0 / n, dtype=np.float64)
            else:
                w_search_init = w0.copy()

        # 1. Gromov \delta-Hyperbolicity & Systemic Crash Analysis
        hyperbolicity = compute_gromov_hyperbolicity(
            corr_matrix=corr,
            critical_delta=self.config.critical_hyperbolicity,
            kappa_hyp=self.config.kappa_hyp,
            cash_de_risk_multiplier=self.config.cash_de_risk_multiplier,
            max_samples=self.config.max_hyperbolicity_samples,
        )

        if hyperbolicity.is_crash_alert:
            self._telemetry["crash_alerts_triggered"] += 1

        # 2. Natural Riemannian Gradient Descent Iterations
        w = w_search_init.copy()
        gamma_risk = self.config.risk_aversion
        gamma_dist = self.config.turnover_penalty_gamma
        eta = self.config.learning_rate
        eps_floor = self.config.epsilon_floor
        raw_max_w = self.config.max_single_weight
        effective_max_w = max(raw_max_w, 1.0 / n) if (raw_max_w is not None and raw_max_w < 1.0) else None

        converged = False
        iteration_count = 0

        for it in range(self.config.max_iterations):
            iteration_count += 1

            # (A) Mean-variance Euclidean gradient: \nabla f_{mv}(w) = \gamma_{risk} \Sigma w - \mu
            grad_mv = gamma_risk * (cov @ w) - mu_vec

            # (B) Geodesic distance turnover penalty gradient
            if gamma_dist > 0.0 and current_weights is not None:
                # dist_R(w, w0) = 2 \arccos(z), where z = \sum \sqrt{w_i w_{0, i}}
                overlap = float(np.sum(np.sqrt(np.maximum(w * w0, 0.0))))
                z = min(1.0 - 1e-14, max(0.0, overlap))
                theta = math.acos(z)

                # Derivative: \nabla_{w_i} [0.5 * dist_R^2] = -(\theta / \sin\theta) \sqrt{w_{0, i} / w_i}
                if theta < 1e-6:
                    factor = 1.0 + (theta ** 2) / 6.0
                else:
                    sin_theta = math.sin(theta)
                    factor = theta / max(1e-12, sin_theta)

                # Component-wise derivative
                sqrt_ratio = np.sqrt(np.maximum(w0, eps_floor) / np.maximum(w, eps_floor))
                grad_dist = -factor * sqrt_ratio
                grad_euclid = grad_mv + gamma_dist * grad_dist
            else:
                grad_euclid = grad_mv

            # (C) Riemannian Tangent Space Projection
            grad_r = project_tangent_space(grad_euclid, w)

            # (D) Exponential Retraction
            w_next = exponential_retraction(w, grad_r, eta, eps_floor)

            # (E) Enforce upper box constraint max_single_weight if feasible
            if effective_max_w is not None and effective_max_w < 1.0:
                if abs(effective_max_w - 1.0 / n) <= 1e-9:
                    w_next = np.full(n, 1.0 / n, dtype=np.float64)
                elif np.any(w_next > effective_max_w):
                    for _ in range(10):
                        over = w_next > effective_max_w
                        if not np.any(over):
                            break
                        excess = float(np.sum(w_next[over] - effective_max_w))
                        w_next[over] = effective_max_w
                        under = ~over
                        positive_under = under & (mu_vec >= -1e4)
                        target_under = positive_under if np.any(positive_under) else under
                        sum_under = float(np.sum(w_next[target_under]))
                        if sum_under > 1e-8:
                            w_next[target_under] += excess * (w_next[target_under] / sum_under)
                        else:
                            w_next[target_under] += excess / np.count_nonzero(target_under)

            # Check convergence in geodesic distance every 5 iterations
            if it % 5 == 0 or it == self.config.max_iterations - 1:
                inner_step = float(np.sum(np.sqrt(np.maximum(w_next * w, 0.0))))
                inner_step = min(1.0, max(-1.0, inner_step))
                dist_step = 0.0 if abs(inner_step - 1.0) < 1e-15 else 2.0 * math.acos(inner_step)
                if dist_step < self.config.convergence_tol:
                    w = w_next
                    converged = True
                    break

            w = w_next

        # Target allocation before Leland bands
        target_w = w.copy()

        # 3. Apply Geodesic Leland No-Trade Buffer Bands & Bypass Mechanics
        current_w_for_leland = w0 if current_weights is not None else np.zeros(n, dtype=np.float64)
        leland = apply_geodesic_leland_bands(
            target_weights=target_w,
            current_weights=current_w_for_leland,
            asset_vols=vols,
            h_crash=hyperbolicity.h_crash,
            base_band=self.config.leland_base_band,
            kappa_sigma=self.config.kappa_sigma,
            kappa_h=self.config.kappa_h,
            asset_names=asset_names,
            cash_allocation=hyperbolicity.cash_allocation,
            max_single_weight=effective_max_w,
        )

        optimal_w = leland.rebalanced_weights.copy()
        cash_w = hyperbolicity.cash_allocation

        # 4. Portfolio Performance Metrics
        exp_ret = float(np.dot(optimal_w, mu_vec))
        exp_var = float(optimal_w @ cov @ optimal_w)
        exp_vol = float(math.sqrt(max(1e-8, exp_var)))
        sharpe = float(exp_ret / max(1e-6, exp_vol))

        geo_dist = geodesic_distance(optimal_w, w0)
        turnover = float(0.5 * np.sum(np.abs(optimal_w - w0)))

        t_end = time.perf_counter_ns()
        elapsed_us = (t_end - t_start) / 1000.0

        self._telemetry["total_optimizations"] += 1
        self._telemetry["total_time_us"] += elapsed_us
        self._telemetry["avg_latency_us"] = self._telemetry["total_time_us"] / max(1, self._telemetry["total_optimizations"])

        return RiemannianOptimizationResult(
            market=self.market,
            optimal_weights=optimal_w,
            target_weights=target_w,
            current_weights=w0,
            cash_weight=cash_w,
            expected_return=exp_ret,
            expected_volatility=exp_vol,
            sharpe_ratio=sharpe,
            geodesic_distance_to_prev=geo_dist,
            turnover=turnover,
            hyperbolicity_diagnostics=hyperbolicity,
            leland_diagnostics=leland,
            converged=converged,
            iterations=iteration_count,
            computation_time_us=elapsed_us,
            backend=self.backend,
        )

    def export_telemetry(self) -> Dict[str, Any]:
        """Exports runtime telemetry and operational latency metrics."""
        return {
            "version": VERSION,
            "release": RELEASE,
            "feature": FEATURE,
            "market": self.market,
            "backend": self.backend,
            "total_optimizations": self._telemetry["total_optimizations"],
            "avg_latency_us": self._telemetry["avg_latency_us"],
            "crash_alerts_triggered": self._telemetry["crash_alerts_triggered"],
        }


# ---------------------------------------------------------------------------
# Comprehensive Backward-Compatibility Alias Trees
# ---------------------------------------------------------------------------
FisherRaoPortfolioAllocator = RiemannianManifoldPortfolioAllocator
CurvatureAwarePortfolioAllocator = RiemannianManifoldPortfolioAllocator
RiemannianSimplexOptimizer = RiemannianManifoldPortfolioAllocator
Phase120RiemannianAllocator = RiemannianManifoldPortfolioAllocator
F572RiemannianManifoldAllocator = RiemannianManifoldPortfolioAllocator
GromovHyperbolicRiskAllocator = RiemannianManifoldPortfolioAllocator
GeodesicLelandPortfolioAllocator = RiemannianManifoldPortfolioAllocator
FisherInformationMetricEngine = RiemannianManifoldPortfolioAllocator
RiemannianManifoldAllocator = RiemannianManifoldPortfolioAllocator
Phase120RiskAllocator = RiemannianManifoldPortfolioAllocator
RiemannianPortfolioOptimizer = RiemannianManifoldPortfolioAllocator
FisherRaoMetricEngine = RiemannianManifoldPortfolioAllocator

# Dataclass aliases
RiemannianConfig = RiemannianAllocatorConfig
FisherRaoConfig = RiemannianAllocatorConfig
RiemannianOutput = RiemannianOptimizationResult
RiemannianResult = RiemannianOptimizationResult
HyperbolicityResult = HyperbolicityDiagnostics
GromovCrashDiagnostics = HyperbolicityDiagnostics
LelandBandDiagnostics = GeodesicLelandBand


# ---------------------------------------------------------------------------
# sys.modules Registration for Dual-Tree Import Consistency
# ---------------------------------------------------------------------------
_MODULE_NAME_PRIMARY = "src.risk.riemannian_manifold_portfolio_allocator"
_MODULE_NAME_MIRROR = "trading_system.src.risk.riemannian_manifold_portfolio_allocator"

if _MODULE_NAME_PRIMARY not in sys.modules:
    sys.modules[_MODULE_NAME_PRIMARY] = sys.modules[__name__]
if _MODULE_NAME_MIRROR not in sys.modules:
    sys.modules[_MODULE_NAME_MIRROR] = sys.modules[__name__]
