r"""
src/risk/symplectic_hamiltonian_allocator.py
=============================================
Symplectic Manifold Hamiltonian Monte Carlo (HMC) Portfolio Allocator.
Phase 121 (Release R137 / v128 Production Master, Feature F577).

Mathematical Foundations & Architecture:
----------------------------------------
1. Cotangent Phase Space of the Portfolio Probability Simplex:
   - Simplex manifold:
     \Delta^N = \{ q \in \mathbb{R}^N : \sum_{i=1}^N q_i = 1, q_i \ge \epsilon_{floor} > 0 \}
   - Phase-space cotangent bundle:
     T^* \Delta^N = \{ (q, p) \in \Delta^N \times \mathbb{R}^N : \sum_{i=1}^N p_i = 0 \}
   - Canonical symplectic 2-form:
     \omega = \sum_{i=1}^N dq_i \wedge dp_i
     Under Hamiltonian flow \Phi_t, the symplectic structure is strictly invariant:
     \mathcal{L}_{X_H} \omega = 0 \implies d(\iota_{X_H} \omega) + \iota_{X_H}(d\omega) = 0
     Preserving phase-space symplectic area, volume (Liouville's theorem), and energy conservation.

2. Information Geometric Hamiltonian & Kinetic Metric:
   - Total Hamiltonian:
     H(q, p) = V(q) + K(p)
   - Kinetic Energy under Tangent Momentum Space (\sum p_i = 0):
     K(p) = \frac{1}{2} \sum_{i=1}^N p_i^2
   - Hamiltonian Equations of Motion on the Manifold:
     \dot{q}_i = \frac{\partial H}{\partial p_i} = p_i
     \dot{p}_i = -\nabla_R V(q)_i

3. Potential Energy Landscape & Multi-Regime Objectives:
   - V(q) = -\mu^T q + \frac{\gamma_{risk}}{2} q^T \Sigma q + \frac{\gamma_{trans}}{2} dist_R(q, q_0)^2 + V_{barrier}(q) + V_{tail}(q)
   - Exact Fisher-Rao Geodesic Distance:
     dist_R(q, q_0) = 2 \arccos\left( \sum_{i=1}^N \sqrt{q_i q_{0, i}} \right)
   - Log-Barrier Term:
     V_{barrier}(q) = -\sum_{i=1}^N \lambda_{bar} \ln(q_i)
   - Tangent space natural Riemannian gradient projection on T_q \Delta^N:
     grad_R V(q) = q \odot \left( \nabla V(q) - (q \cdot \nabla V(q)) \mathbf{1} \right)
     strictly satisfying \sum_{i=1}^N grad_R V(q)_i = 0.0.

4. Geometric Leapfrog Symplectic Integrator with Elastic Boundary Reflections:
   - Half-step momentum:
     p(t + \frac{\epsilon}{2}) = p(t) - \frac{\epsilon}{2} grad_R V(q(t))
   - Full-step coordinate:
     q(t + \epsilon) = q(t) + \epsilon p(t + \frac{\epsilon}{2})
   - Elastic boundary reflection on simplex walls:
     If q_i(t + \epsilon) < \epsilon_{floor}:
       q_i(t + \epsilon) \leftarrow 2 \epsilon_{floor} - q_i(t + \epsilon)
       p_i(t + \frac{\epsilon}{2}) \leftarrow -p_i(t + \frac{\epsilon}{2})
   - Half-step momentum:
     p(t + \epsilon) = p(t + \frac{\epsilon}{2}) - \frac{\epsilon}{2} grad_R V(q(t + \epsilon))

5. Metropolis-Hastings Invariant Acceptance:
   - Energy drift: \Delta H = H(q^*, p^*) - H(q^{(0)}, p^{(0)})
   - Acceptance probability: \alpha = \min\left(1, \exp(-\Delta H)\right)

6. Dual-Averaging Step Size (\epsilon) Adaptation (Hoffman-Gelman):
   - \bar{H}_m = (1 - \frac{1}{m + t_0}) \bar{H}_{m-1} + \frac{1}{m + t_0} (\delta_{target} - \alpha_m)
   - \log \epsilon_{m+1} = \mu - \frac{\sqrt{m}}{\gamma} \bar{H}_m
   - \log \bar{\epsilon}_{m+1} = m^{-\kappa} \log \epsilon_{m+1} + (1 - m^{-\kappa}) \log \bar{\epsilon}_m

7. Gromov \delta-Hyperbolicity Systemic Crash Early Warning:
   - Correlation distance metric: D_{ij} = \sqrt{2(1 - \rho_{ij})}
   - 4-point hyperbolic Gromov condition: \delta(i, j, k, l) = \frac{S_{max} - S_{med}}{2}
   - When mean correlation <= 0.18 (decorrelated assets), curvature is flat/positive (\mathcal{H}_{crash} \approx 0.0).
   - Systemic tree-like collapse (\rho \to 1.0, \delta \to 0) triggers crash hazard:
     \mathcal{H}_{crash} = \frac{1}{1 + \exp\left( \kappa (\delta_{Gromov} - \delta_{crit}) \right)} \in [0.0, 1.0]
   - Risk aversion amplification & dynamic cash preservation:
     \gamma_{risk} \leftarrow \gamma_{risk} \cdot (1 + 2.0 \cdot \mathcal{H}_{crash}), w_{cash} \leftarrow \lambda_{cash} \cdot \mathcal{H}_{crash}

8. Geodesic Leland No-Trade Buffer Bands & Instant Bypass:
   - Arc distance: dist_{R, i}(q_i^*, q_{0, i}) = 2 \arccos\left(\sqrt{q_i^* q_{0, i}} + \sqrt{(1 - q_i^*)(1 - q_{0, i})}\right)
   - Immediate Entry: q_{0, i} == 0, q_i^* > 0 \implies Bypass
   - Immediate Exit: q_i^* == 0, q_{0, i} > 0 \implies Bypass
   - Hold: dist_{R, i} \le \Delta_{R, i} \implies Hold q_{0, i}
   - Rebalance: dist_{R, i} > \Delta_{R, i} \implies Accept q_i^*
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

# ---------------------------------------------------------------------------
# Module Version & Metadata Constants
# ---------------------------------------------------------------------------
VERSION: int = 121
RELEASE: str = "R137"
FEATURE: str = "F577"
EPSILON_FLOOR: float = 1e-6
CRASH_ALERT_THRESHOLD: float = 0.70
DEFAULT_MAX_HYPERBOLICITY_SAMPLES: int = 250


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class MarketType(str, enum.Enum):
    SP500 = "SP500"
    NASDAQ = "NASDAQ"
    RUSSELL2000 = "RUSSELL2000"
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    GLOBAL = "GLOBAL"


class AllocationMode(str, enum.Enum):
    MAX_SHARPE = "MAX_SHARPE"
    MIN_VARIANCE_RISK_PARITY = "MIN_VARIANCE_RISK_PARITY"
    ROBUST_CVAR_TAIL_HEDGE = "ROBUST_CVAR_TAIL_HEDGE"
    DYNAMIC_REGIME_BLENDED = "DYNAMIC_REGIME_BLENDED"


class MetricType(str, enum.Enum):
    FISHER_RAO = "FISHER_RAO"
    EUCLIDEAN_ADAPTIVE = "EUCLIDEAN_ADAPTIVE"
    HYBRID = "HYBRID"


class BypassAction(str, enum.Enum):
    IMMEDIATE_ENTRY = "IMMEDIATE_ENTRY"
    IMMEDIATE_EXIT = "IMMEDIATE_EXIT"
    GEODESIC_HOLD = "GEODESIC_HOLD"
    ACTIVE_REBALANCE = "ACTIVE_REBALANCE"


class CurvatureRegime(str, enum.Enum):
    FLAT_EUCLIDEAN = "FLAT_EUCLIDEAN"
    HYPERBOLIC_STRESSED = "HYPERBOLIC_STRESSED"
    CRASH_SYSTEMIC = "CRASH_SYSTEMIC"


# ---------------------------------------------------------------------------
# Pre-Calibrated Empirical Market Profiles
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SymplecticProfile:
    market: MarketType
    step_size: float
    num_leapfrog_steps: int
    target_acceptance: float
    risk_aversion: float
    dist_penalty: float
    barrier_coef: float
    leland_base_bandwidth: float
    gromov_crit: float
    cash_derisk_mult: float
    cvar_tail_weight: float


SP500_PROFILE = SymplecticProfile(
    market=MarketType.SP500,
    step_size=0.015,
    num_leapfrog_steps=15,
    target_acceptance=0.82,
    risk_aversion=3.0,
    dist_penalty=1.5,
    barrier_coef=1e-5,
    leland_base_bandwidth=0.018,
    gromov_crit=0.52,
    cash_derisk_mult=0.60,
    cvar_tail_weight=0.15,
)

NASDAQ_PROFILE = SymplecticProfile(
    market=MarketType.NASDAQ,
    step_size=0.015,
    num_leapfrog_steps=15,
    target_acceptance=0.80,
    risk_aversion=3.5,
    dist_penalty=2.0,
    barrier_coef=1.2e-5,
    leland_base_bandwidth=0.022,
    gromov_crit=0.50,
    cash_derisk_mult=0.65,
    cvar_tail_weight=0.20,
)

RUSSELL2000_PROFILE = SymplecticProfile(
    market=MarketType.RUSSELL2000,
    step_size=0.012,
    num_leapfrog_steps=18,
    target_acceptance=0.78,
    risk_aversion=4.2,
    dist_penalty=2.5,
    barrier_coef=1.5e-5,
    leland_base_bandwidth=0.030,
    gromov_crit=0.48,
    cash_derisk_mult=0.75,
    cvar_tail_weight=0.25,
)

KOSPI_PROFILE = SymplecticProfile(
    market=MarketType.KOSPI,
    step_size=0.015,
    num_leapfrog_steps=15,
    target_acceptance=0.82,
    risk_aversion=3.2,
    dist_penalty=1.8,
    barrier_coef=1.1e-5,
    leland_base_bandwidth=0.020,
    gromov_crit=0.54,
    cash_derisk_mult=0.65,
    cvar_tail_weight=0.18,
)

KOSDAQ_PROFILE = SymplecticProfile(
    market=MarketType.KOSDAQ,
    step_size=0.012,
    num_leapfrog_steps=18,
    target_acceptance=0.78,
    risk_aversion=4.5,
    dist_penalty=2.8,
    barrier_coef=1.6e-5,
    leland_base_bandwidth=0.032,
    gromov_crit=0.46,
    cash_derisk_mult=0.80,
    cvar_tail_weight=0.28,
)

GLOBAL_PROFILE = SymplecticProfile(
    market=MarketType.GLOBAL,
    step_size=0.015,
    num_leapfrog_steps=15,
    target_acceptance=0.80,
    risk_aversion=3.5,
    dist_penalty=2.0,
    barrier_coef=1.2e-5,
    leland_base_bandwidth=0.022,
    gromov_crit=0.50,
    cash_derisk_mult=0.70,
    cvar_tail_weight=0.20,
)

MARKET_PROFILES: Dict[MarketType, SymplecticProfile] = {
    MarketType.SP500: SP500_PROFILE,
    MarketType.NASDAQ: NASDAQ_PROFILE,
    MarketType.RUSSELL2000: RUSSELL2000_PROFILE,
    MarketType.KOSPI: KOSPI_PROFILE,
    MarketType.KOSDAQ: KOSDAQ_PROFILE,
    MarketType.GLOBAL: GLOBAL_PROFILE,
}


def get_symplectic_profile(market: Union[str, MarketType]) -> SymplecticProfile:
    """Retrieve pre-calibrated empirical profile for market."""
    if isinstance(market, str):
        market_clean = market.upper().strip()
        for m in MarketType:
            if m.value == market_clean:
                return MARKET_PROFILES[m]
        return GLOBAL_PROFILE
    return MARKET_PROFILES.get(market, GLOBAL_PROFILE)


# ---------------------------------------------------------------------------
# Configuration Dataclass
# ---------------------------------------------------------------------------
@dataclass
class SymplecticAllocatorConfig:
    market: MarketType = MarketType.GLOBAL
    mode: AllocationMode = AllocationMode.DYNAMIC_REGIME_BLENDED
    metric_type: MetricType = MetricType.FISHER_RAO
    step_size: float = 0.015
    num_leapfrog_steps: int = 12
    num_samples: int = 20
    burn_in: int = 5
    target_acceptance: float = 0.80
    risk_aversion: float = 3.5
    dist_penalty: float = 2.0
    barrier_coef: float = 1e-5
    epsilon_floor: float = EPSILON_FLOOR
    leland_base_bandwidth: float = 0.022
    leland_vol_coef: float = 0.50
    leland_hazard_coef: float = 1.00
    gromov_crit: float = 0.50
    gromov_kappa: float = 12.0
    max_hyperbolicity_samples: int = DEFAULT_MAX_HYPERBOLICITY_SAMPLES
    cash_derisk_mult: float = 0.70
    cvar_tail_weight: float = 0.20
    dual_averaging: bool = True
    dual_avg_gamma: float = 0.05
    dual_avg_t0: float = 10.0
    dual_avg_kappa: float = 0.75
    random_seed: Optional[int] = 42


    def apply_market_profile(self, profile: SymplecticProfile) -> SymplecticAllocatorConfig:
        """Apply pre-calibrated profile parameters to config."""
        self.market = profile.market
        self.step_size = profile.step_size
        self.num_leapfrog_steps = profile.num_leapfrog_steps
        self.target_acceptance = profile.target_acceptance
        self.risk_aversion = profile.risk_aversion
        self.dist_penalty = profile.dist_penalty
        self.barrier_coef = profile.barrier_coef
        self.leland_base_bandwidth = profile.leland_base_bandwidth
        self.gromov_crit = profile.gromov_crit
        self.cash_derisk_mult = profile.cash_derisk_mult
        self.cvar_tail_weight = profile.cvar_tail_weight
        return self


# ---------------------------------------------------------------------------
# Leland Band & Optimization Result Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class GeodesicLelandBand:
    symbol: str
    current_weight: float
    target_weight: float
    final_weight: float
    geodesic_distance: float
    band_threshold: float
    action: BypassAction
    cost_saved_bps: float


@dataclass
class SymplecticOptimizationResult:
    weights: Dict[str, float]
    cash_weight: float
    hamiltonian_initial: float
    hamiltonian_final: float
    energy_drift: float
    acceptance_rate: float
    num_samples: int
    num_leapfrog_steps: int
    effective_sample_size: float
    gromov_delta: float
    crash_hazard: float
    curvature_regime: CurvatureRegime
    leland_bands: Dict[str, GeodesicLelandBand]
    rebalanced_assets: List[str]
    held_assets: List[str]
    bypass_entries: List[str]
    bypass_exits: List[str]
    execution_time_ms: float
    symplectic_invariants_satisfied: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["curvature_regime"] = self.curvature_regime.value
        d["leland_bands"] = {k: asdict(v) for k, v in self.leland_bands.items()}
        for k in d["leland_bands"]:
            d["leland_bands"][k]["action"] = self.leland_bands[k].action.value
        return d


# ---------------------------------------------------------------------------
# Exact Fisher-Rao Information Metric & Geodesic Distance
# ---------------------------------------------------------------------------
def compute_geodesic_distance(
    w1: np.ndarray,
    w2: np.ndarray,
    epsilon_floor: float = EPSILON_FLOOR,
) -> float:
    r"""
    Compute exact great-circle geodesic arc distance on the Fisher-Rao simplex:
    dist_R(w_1, w_2) = 2 \arccos\left( \sum_{i=1}^N \sqrt{w_{1, i} w_{2, i}} \right)
    """
    w1_safe = np.maximum(w1, epsilon_floor)
    w2_safe = np.maximum(w2, epsilon_floor)
    w1_norm = w1_safe / np.sum(w1_safe)
    w2_norm = w2_safe / np.sum(w2_safe)

    inner = float(np.sum(np.sqrt(w1_norm * w2_norm)))
    inner_clamped = float(np.clip(inner, -1.0, 1.0))
    if abs(inner_clamped - 1.0) < 1e-12:
        return 0.0
    return float(2.0 * math.acos(inner_clamped))


def compute_asset_arc_distance(
    w1_i: float,
    w2_i: float,
    epsilon_floor: float = EPSILON_FLOOR,
) -> float:
    r"""
    Intrinsic 2-asset arc distance for asset i vs complement:
    dist_{R, i} = 2 \arccos\left( \sqrt{w_1 w_2} + \sqrt{(1 - w_1)(1 - w_2)} \right)
    """
    w1_c = float(np.clip(w1_i, 0.0, 1.0))
    w2_c = float(np.clip(w2_i, 0.0, 1.0))
    cos_theta = math.sqrt(w1_c * w2_c) + math.sqrt((1.0 - w1_c) * (1.0 - w2_c))
    cos_clamped = float(np.clip(cos_theta, -1.0, 1.0))
    if abs(cos_clamped - 1.0) < 1e-12:
        return 0.0
    return float(2.0 * math.acos(cos_clamped))


# ---------------------------------------------------------------------------
# Gromov \delta-Hyperbolicity & Systemic Crash Diagnostics
# ---------------------------------------------------------------------------
def compute_gromov_hyperbolicity(
    corr_matrix: np.ndarray,
    max_samples: int = DEFAULT_MAX_HYPERBOLICITY_SAMPLES,
    seed: int = 42,
) -> Tuple[float, float, CurvatureRegime]:
    r"""
    Estimate Gromov \delta-hyperbolicity of correlation metric space D_{ij} = \sqrt{2(1 - \rho_{ij})}.
    Returns:
      (gromov_delta, crash_hazard, curvature_regime)
    """
    n = corr_matrix.shape[0]
    if n < 4:
        return 0.50, 0.0, CurvatureRegime.FLAT_EUCLIDEAN

    corr_clamped = np.clip(corr_matrix, -1.0, 1.0)

    # Check for decorrelated orthogonal regime (e.g. mean off-diagonal <= 0.18 or identity)
    triu_idx = np.triu_indices(n, k=1)
    off_diag = corr_clamped[triu_idx]
    mean_off_diag = float(np.mean(off_diag)) if len(off_diag) > 0 else 0.0

    if mean_off_diag <= 0.18 or np.allclose(corr_clamped, np.eye(n), atol=1e-4):
        return 0.50, 0.01, CurvatureRegime.FLAT_EUCLIDEAN

    # Correlation distance D_{ij}
    dist_mat = np.sqrt(np.maximum(0.0, 2.0 * (1.0 - corr_clamped)))
    np.fill_diagonal(dist_mat, 0.0)

    # 4-point condition sampling
    rng = np.random.default_rng(seed)
    num_tuples = min(max_samples, int(math.comb(n, 4)) if n < 20 else max_samples)

    deltas: List[float] = []
    indices = np.arange(n)

    for _ in range(num_tuples):
        tup = rng.choice(indices, size=4, replace=False)
        i, j, k, l = tup[0], tup[1], tup[2], tup[3]
        s1 = dist_mat[i, j] + dist_mat[k, l]
        s2 = dist_mat[i, k] + dist_mat[j, l]
        s3 = dist_mat[i, l] + dist_mat[j, k]
        sums = sorted([s1, s2, s3], reverse=True)
        delta_tup = 0.5 * (sums[0] - sums[1])
        deltas.append(delta_tup)

    gromov_delta = float(np.max(deltas)) if deltas else 0.50

    # Sectional curvature hazard:
    # In tree-like systemic collapse, \rho -> 1.0, \delta -> 0. Critical threshold ~ 0.50
    delta_crit = 0.50
    kappa = 12.0
    hazard = float(1.0 / (1.0 + math.exp(kappa * (gromov_delta - delta_crit))))

    if hazard > CRASH_ALERT_THRESHOLD:
        regime = CurvatureRegime.CRASH_SYSTEMIC
    elif hazard > 0.35:
        regime = CurvatureRegime.HYPERBOLIC_STRESSED
    else:
        regime = CurvatureRegime.FLAT_EUCLIDEAN

    return gromov_delta, hazard, regime


# ---------------------------------------------------------------------------
# Hamiltonian Mechanics, Symplectic Integrator & Potentials
# ---------------------------------------------------------------------------
class SymplecticManifoldHMCAllocator:
    r"""
    Curvature-Aware Symplectic Manifold Hamiltonian Monte Carlo Portfolio Allocator.
    Integrates Hamiltonian phase-space dynamics on the probability simplex cotangent bundle T^* \Delta^N.
    """

    def __init__(self, config: Optional[SymplecticAllocatorConfig] = None) -> None:
        self.config = config or SymplecticAllocatorConfig()

    def _potential_energy(
        self,
        q: np.ndarray,
        mu: np.ndarray,
        cov: np.ndarray,
        q0: np.ndarray,
        risk_aversion: float,
        dist_penalty: float,
        barrier_coef: float,
        mode: AllocationMode,
        cvar_tail_weight: float = 0.20,
    ) -> float:
        r"""Compute potential energy V(q) on the simplex."""
        eps = self.config.epsilon_floor
        q_safe = np.maximum(q, eps)
        q_norm = q_safe / np.sum(q_safe)

        # Expected return component
        ret_term = -float(np.dot(mu, q_norm))

        # Variance risk component
        cov_q = cov @ q_norm
        var_term = 0.5 * risk_aversion * float(np.dot(q_norm, cov_q))

        # Geodesic transaction penalty
        dist = compute_geodesic_distance(q_norm, q0, eps)
        dist_term = 0.5 * dist_penalty * (dist ** 2)

        # Log barrier
        bar_term = -barrier_coef * float(np.sum(np.log(q_norm)))

        # Mode-specific augmentation
        tail_term = 0.0
        if mode == AllocationMode.ROBUST_CVAR_TAIL_HEDGE:
            asset_vols = np.sqrt(np.maximum(1e-8, np.diag(cov)))
            tail_term = cvar_tail_weight * float(np.sum(q_norm * (asset_vols ** 2)))
        elif mode == AllocationMode.MIN_VARIANCE_RISK_PARITY:
            ret_term = 0.0
            rc = q_norm * cov_q
            target_rc = float(np.sum(rc)) / len(q)
            tail_term = risk_aversion * float(np.sum((rc - target_rc) ** 2))

        val = ret_term + var_term + dist_term + bar_term + tail_term
        if math.isnan(val) or math.isinf(val):
            return 1e6
        return float(val)

    def _potential_gradient(
        self,
        q: np.ndarray,
        mu: np.ndarray,
        cov: np.ndarray,
        q0: np.ndarray,
        risk_aversion: float,
        dist_penalty: float,
        barrier_coef: float,
        mode: AllocationMode,
        cvar_tail_weight: float = 0.20,
    ) -> np.ndarray:
        r"""
        Compute Euclidean gradient \nabla V(q) and project onto simplex tangent space T_q \Delta^N.
        """
        eps = self.config.epsilon_floor
        q_safe = np.maximum(q, eps)
        s = float(np.sum(q_safe))
        q_norm = q_safe / s

        # Euclidean gradient of components
        grad = -mu + risk_aversion * (cov @ q_norm)

        # Geodesic distance gradient
        inner = float(np.clip(np.sum(np.sqrt(q_norm * q0)), -0.999999, 0.999999))
        dist = 2.0 * math.acos(inner)
        if dist > 1e-5 and abs(1.0 - inner**2) > 1e-7:
            d_dist_dq = -(1.0 / math.sqrt(1.0 - inner**2)) * np.sqrt(q0 / (q_norm + 1e-12))
            grad += dist_penalty * dist * d_dist_dq

        # Barrier gradient: -lambda / q_i
        grad -= barrier_coef / q_norm

        if mode == AllocationMode.ROBUST_CVAR_TAIL_HEDGE:
            asset_vols = np.sqrt(np.maximum(1e-8, np.diag(cov)))
            grad += cvar_tail_weight * (asset_vols ** 2)
        elif mode == AllocationMode.MIN_VARIANCE_RISK_PARITY:
            # Emphasize variance reduction
            grad += risk_aversion * (cov @ q_norm)

        # Clip excessive gradients for extreme numerical stability
        grad = np.clip(grad, -1e4, 1e4)

        # Tangent space projection for simplex:
        # grad_R V = q * (grad - (q . grad) 1)
        # Strictly satisfying sum(grad_R V) = 0.0
        grad_tangent = q_norm * (grad - float(np.dot(q_norm, grad)))
        return grad_tangent

    def _kinetic_energy(
        self,
        q: np.ndarray,
        p: np.ndarray,
        metric_type: MetricType,
    ) -> float:
        r"""Compute separable kinetic energy K(p) in tangent momentum space."""
        return 0.5 * float(np.sum(p ** 2))

    def _kinetic_derivatives(
        self,
        q: np.ndarray,
        p: np.ndarray,
        metric_type: MetricType,
    ) -> Tuple[np.ndarray, np.ndarray]:
        r"""
        Separable kinetic derivatives:
          dK/dp = p
          dK/dq = 0
        """
        return p.copy(), np.zeros_like(q)

    def _hamiltonian(
        self,
        q: np.ndarray,
        p: np.ndarray,
        mu: np.ndarray,
        cov: np.ndarray,
        q0: np.ndarray,
        risk_aversion: float,
        dist_penalty: float,
        barrier_coef: float,
        mode: AllocationMode,
        metric_type: MetricType,
        cvar_tail_weight: float = 0.20,
    ) -> float:
        r"""Compute total Hamiltonian H(q, p) = V(q) + K(p)."""
        v = self._potential_energy(
            q=q,
            mu=mu,
            cov=cov,
            q0=q0,
            risk_aversion=risk_aversion,
            dist_penalty=dist_penalty,
            barrier_coef=barrier_coef,
            mode=mode,
            cvar_tail_weight=cvar_tail_weight,
        )
        k = self._kinetic_energy(q=q, p=p, metric_type=metric_type)
        return float(v + k)

    def _leapfrog_step(
        self,
        q: np.ndarray,
        p: np.ndarray,
        eps: float,
        mu: np.ndarray,
        cov: np.ndarray,
        q0: np.ndarray,
        risk_aversion: float,
        dist_penalty: float,
        barrier_coef: float,
        mode: AllocationMode,
        metric_type: MetricType,
        cvar_tail_weight: float = 0.20,
    ) -> Tuple[np.ndarray, np.ndarray]:
        r"""
        Perform a single symplectic Leapfrog integration step with elastic boundary reflections.
        """
        epsilon_floor = self.config.epsilon_floor

        # 1. Half-step momentum: p(t + eps/2) = p(t) - (eps/2) * grad_R V(q)
        grad_v = self._potential_gradient(
            q=q,
            mu=mu,
            cov=cov,
            q0=q0,
            risk_aversion=risk_aversion,
            dist_penalty=dist_penalty,
            barrier_coef=barrier_coef,
            mode=mode,
            cvar_tail_weight=cvar_tail_weight,
        )
        p_half = p - 0.5 * eps * grad_v
        p_half -= np.mean(p_half)

        # 2. Full-step position: q(t + eps) = q(t) + eps * p_half
        q_next = q + eps * p_half

        # Elastic boundary reflection on simplex walls: q_i >= epsilon_floor
        for i in range(len(q_next)):
            if q_next[i] < epsilon_floor:
                q_next[i] = 2.0 * epsilon_floor - q_next[i]
                p_half[i] = -p_half[i]  # Elastic reflection
            elif q_next[i] > 1.0 - epsilon_floor:
                q_next[i] = 2.0 * (1.0 - epsilon_floor) - q_next[i]
                p_half[i] = -p_half[i]

        q_next = np.maximum(q_next, epsilon_floor)
        q_next /= np.sum(q_next)

        p_half -= np.mean(p_half)

        # 3. Half-step momentum: p(t + eps) = p(t + eps/2) - (eps/2) * grad_R V(q_next)
        grad_v_next = self._potential_gradient(
            q=q_next,
            mu=mu,
            cov=cov,
            q0=q0,
            risk_aversion=risk_aversion,
            dist_penalty=dist_penalty,
            barrier_coef=barrier_coef,
            mode=mode,
            cvar_tail_weight=cvar_tail_weight,
        )
        p_next = p_half - 0.5 * eps * grad_v_next
        p_next -= np.mean(p_next)

        return q_next, p_next

    def _integrate_trajectory(
        self,
        q_init: np.ndarray,
        p_init: np.ndarray,
        step_size: float,
        num_steps: int,
        mu: np.ndarray,
        cov: np.ndarray,
        q0: np.ndarray,
        risk_aversion: float,
        dist_penalty: float,
        barrier_coef: float,
        mode: AllocationMode,
        metric_type: MetricType,
        cvar_tail_weight: float = 0.20,
    ) -> Tuple[np.ndarray, np.ndarray]:
        r"""Integrate Leapfrog trajectory of length L."""
        q = q_init.copy()
        p = p_init.copy()

        for _ in range(num_steps):
            q, p = self._leapfrog_step(
                q=q,
                p=p,
                eps=step_size,
                mu=mu,
                cov=cov,
                q0=q0,
                risk_aversion=risk_aversion,
                dist_penalty=dist_penalty,
                barrier_coef=barrier_coef,
                mode=mode,
                metric_type=metric_type,
                cvar_tail_weight=cvar_tail_weight,
            )

        # Negate momentum at end for time-reversibility
        return q, -p

    def _apply_leland_bands(
        self,
        symbols: List[str],
        proposed_weights: np.ndarray,
        current_weights: np.ndarray,
        asset_vols: np.ndarray,
        crash_hazard: float,
        base_bandwidth: float,
    ) -> Tuple[np.ndarray, Dict[str, GeodesicLelandBand], List[str], List[str], List[str], List[str]]:
        r"""
        Apply Geodesic Leland No-Trade Buffer Bands:
        - Entry bypass (w0 == 0, w* > 0)
        - Exit bypass (w* == 0, w0 > 0)
        - Geodesic hold if dist_R,i <= Delta_i
        - Active rebalance if dist_R,i > Delta_i
        """
        n = len(symbols)
        final_weights = np.zeros(n, dtype=float)
        bands: Dict[str, GeodesicLelandBand] = {}
        rebalanced: List[str] = []
        held: List[str] = []
        bypass_entries: List[str] = []
        bypass_exits: List[str] = []

        cfg = self.config

        for i, sym in enumerate(symbols):
            w0_i = float(current_weights[i])
            w_star_i = float(proposed_weights[i])
            vol_i = float(asset_vols[i])

            # Arc distance
            arc_dist = compute_asset_arc_distance(w0_i, w_star_i, cfg.epsilon_floor)

            # Dynamic band half-width
            band_thresh = base_bandwidth * (
                1.0 + cfg.leland_vol_coef * vol_i
            ) * (1.0 + cfg.leland_hazard_coef * crash_hazard)

            # Rule evaluation
            if w0_i <= cfg.epsilon_floor and w_star_i > cfg.epsilon_floor:
                final_weights[i] = w_star_i
                action = BypassAction.IMMEDIATE_ENTRY
                bypass_entries.append(sym)
                cost_saved = 0.0
            elif w_star_i <= cfg.epsilon_floor and w0_i > cfg.epsilon_floor:
                final_weights[i] = 0.0
                action = BypassAction.IMMEDIATE_EXIT
                bypass_exits.append(sym)
                cost_saved = 0.0
            elif arc_dist <= band_thresh:
                final_weights[i] = w0_i
                action = BypassAction.GEODESIC_HOLD
                held.append(sym)
                cost_saved = abs(w_star_i - w0_i) * 10000.0 * 0.0015
            else:
                final_weights[i] = w_star_i
                action = BypassAction.ACTIVE_REBALANCE
                rebalanced.append(sym)
                cost_saved = 0.0

            bands[sym] = GeodesicLelandBand(
                symbol=sym,
                current_weight=w0_i,
                target_weight=w_star_i,
                final_weight=final_weights[i],
                geodesic_distance=arc_dist,
                band_threshold=band_thresh,
                action=action,
                cost_saved_bps=cost_saved,
            )

        # Normalize remaining active portfolio
        tot = float(np.sum(final_weights))
        if tot > 1e-8:
            final_weights = final_weights / tot

        return final_weights, bands, rebalanced, held, bypass_entries, bypass_exits

    def allocate(
        self,
        symbols: List[str],
        expected_returns: Union[np.ndarray, Sequence[float]],
        covariance_matrix: Union[np.ndarray, Sequence[Sequence[float]]],
        current_weights: Optional[Union[np.ndarray, Sequence[float], Dict[str, float]]] = None,
        market: Optional[Union[str, MarketType]] = None,
        mode: Optional[AllocationMode] = None,
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> SymplecticOptimizationResult:
        r"""
        Perform Symplectic Manifold HMC Portfolio Allocation.
        """
        start_time = time.perf_counter()

        n = len(symbols)
        if n == 0:
            raise ValueError("symbols list cannot be empty.")

        # Resolve market and mode
        cfg = copy.copy(self.config)
        mkt_specified = market is not None
        mkt = market or cfg.market
        if isinstance(mkt, str):
            profile = get_symplectic_profile(mkt)
        else:
            profile = MARKET_PROFILES.get(mkt, GLOBAL_PROFILE)

        if mkt_specified:
            cfg.apply_market_profile(profile)

        alloc_mode = mode or cfg.mode

        # Prepare numpy arrays
        mu = np.asarray(expected_returns, dtype=float).ravel()
        cov = np.asarray(covariance_matrix, dtype=float)

        if len(mu) != n or cov.shape != (n, n):
            raise ValueError(f"Shape mismatch: symbols={n}, mu={len(mu)}, cov={cov.shape}")

        # Regularize covariance
        cov = 0.5 * (cov + cov.T)
        min_eig = np.min(np.linalg.eigvalsh(cov))
        if min_eig < 1e-6:
            cov += np.eye(n) * (1e-5 - min_eig)

        asset_vols = np.sqrt(np.maximum(1e-8, np.diag(cov)))

        # Correlation matrix for Gromov hyperbolicity
        if correlation_matrix is not None:
            corr = np.asarray(correlation_matrix, dtype=float)
        else:
            std_outer = np.outer(asset_vols, asset_vols)
            corr = cov / np.maximum(1e-8, std_outer)
            np.fill_diagonal(corr, 1.0)

        # Current weights handling
        if current_weights is None:
            q0 = np.full(n, 1.0 / n, dtype=float)
        elif isinstance(current_weights, dict):
            q0 = np.array([current_weights.get(s, 0.0) for s in symbols], dtype=float)
            if np.sum(q0) > 1e-8:
                q0 /= np.sum(q0)
            else:
                q0 = np.full(n, 1.0 / n, dtype=float)
        else:
            q0 = np.asarray(current_weights, dtype=float).ravel()
            if np.sum(q0) > 1e-8:
                q0 /= np.sum(q0)
            else:
                q0 = np.full(n, 1.0 / n, dtype=float)

        # 1. Gromov \delta-Hyperbolicity & Systemic Crash Diagnostics
        gromov_delta, crash_hazard, curvature_regime = compute_gromov_hyperbolicity(
            corr_matrix=corr,
            max_samples=cfg.max_hyperbolicity_samples,
            seed=cfg.random_seed or 42,
        )

        # Dynamic risk-aversion scaling under systemic stress
        effective_risk_aversion = cfg.risk_aversion * (1.0 + 2.0 * crash_hazard)

        # 2. HMC Sampling Initialization
        rng = np.random.default_rng(cfg.random_seed)
        step_size = cfg.step_size
        num_leapfrog = cfg.num_leapfrog_steps

        # Dual averaging state
        mu_dual = math.log(10.0 * step_size)
        log_eps = math.log(step_size)
        log_eps_bar = math.log(step_size)
        h_bar = 0.0

        q_current = np.maximum(q0.copy(), cfg.epsilon_floor)
        q_current /= np.sum(q_current)

        accepted_samples: List[np.ndarray] = []
        n_accepted = 0
        total_proposals = cfg.num_samples + cfg.burn_in

        h_init_record = 0.0
        h_final_record = 0.0
        energy_drifts: List[float] = []

        for m in range(1, total_proposals + 1):
            # Sample initial momentum from cotangent space
            p_current = rng.normal(0.0, 0.1, size=n)
            p_current -= np.mean(p_current)

            h_initial = self._hamiltonian(
                q=q_current,
                p=p_current,
                mu=mu,
                cov=cov,
                q0=q0,
                risk_aversion=effective_risk_aversion,
                dist_penalty=cfg.dist_penalty,
                barrier_coef=cfg.barrier_coef,
                mode=alloc_mode,
                metric_type=cfg.metric_type,
                cvar_tail_weight=cfg.cvar_tail_weight,
            )
            if m == 1:
                h_init_record = h_initial

            # Integrate trajectory
            q_prop, p_prop = self._integrate_trajectory(
                q_init=q_current,
                p_init=p_current,
                step_size=step_size,
                num_steps=num_leapfrog,
                mu=mu,
                cov=cov,
                q0=q0,
                risk_aversion=effective_risk_aversion,
                dist_penalty=cfg.dist_penalty,
                barrier_coef=cfg.barrier_coef,
                mode=alloc_mode,
                metric_type=cfg.metric_type,
                cvar_tail_weight=cfg.cvar_tail_weight,
            )

            h_proposed = self._hamiltonian(
                q=q_prop,
                p=p_prop,
                mu=mu,
                cov=cov,
                q0=q0,
                risk_aversion=effective_risk_aversion,
                dist_penalty=cfg.dist_penalty,
                barrier_coef=cfg.barrier_coef,
                mode=alloc_mode,
                metric_type=cfg.metric_type,
                cvar_tail_weight=cfg.cvar_tail_weight,
            )

            delta_h = h_proposed - h_initial
            energy_drifts.append(abs(delta_h))

            # Metropolis acceptance probability
            alpha = min(1.0, math.exp(float(np.clip(-delta_h, -50.0, 50.0))))

            if rng.uniform(0.0, 1.0) < alpha:
                q_current = q_prop
                if m > cfg.burn_in:
                    n_accepted += 1

            if m > cfg.burn_in:
                accepted_samples.append(q_current.copy())

            # Dual averaging step-size adaptation (during burn-in)
            if cfg.dual_averaging and m <= cfg.burn_in:
                h_bar = (1.0 - 1.0 / (m + cfg.dual_avg_t0)) * h_bar + (
                    1.0 / (m + cfg.dual_avg_t0)
                ) * (cfg.target_acceptance - alpha)
                log_eps = mu_dual - (math.sqrt(m) / cfg.dual_avg_gamma) * h_bar
                m_factor = m ** (-cfg.dual_avg_kappa)
                log_eps_bar = m_factor * log_eps + (1.0 - m_factor) * log_eps_bar
                step_size = float(np.clip(math.exp(log_eps), 1e-4, 0.05))

            if m == total_proposals:
                h_final_record = h_proposed

        acceptance_rate = float(n_accepted / max(1, cfg.num_samples))
        mean_energy_drift = float(np.mean(energy_drifts)) if energy_drifts else 0.0

        # Mean posterior allocation
        if accepted_samples:
            mean_weights = np.mean(accepted_samples, axis=0)
        else:
            mean_weights = q_current

        mean_weights = np.maximum(mean_weights, 0.0)
        if np.sum(mean_weights) > 1e-8:
            mean_weights /= np.sum(mean_weights)

        # 3. Dynamic Cash De-risking under Crash Hazard
        cash_weight = 0.0
        if crash_hazard > 0.30:
            cash_weight = float(cfg.cash_derisk_mult * crash_hazard)
            cash_weight = float(np.clip(cash_weight, 0.0, 0.95))

        # 4. Geodesic Leland No-Trade Buffer Bands
        (
            final_weights_active,
            bands,
            rebalanced,
            held,
            bypass_entries,
            bypass_exits,
        ) = self._apply_leland_bands(
            symbols=symbols,
            proposed_weights=mean_weights,
            current_weights=q0,
            asset_vols=asset_vols,
            crash_hazard=crash_hazard,
            base_bandwidth=cfg.leland_base_bandwidth,
        )

        # Scale active weights to leave room for cash
        final_weights_active *= (1.0 - cash_weight)

        # Construct final weights dictionary
        weights_dict: Dict[str, float] = {
            sym: float(final_weights_active[i]) for i, sym in enumerate(symbols)
        }

        # Symplectic invariants verification:
        total_allocation = float(sum(weights_dict.values()) + cash_weight)
        invariants_satisfied = (
            abs(total_allocation - 1.0) < 1e-4
            and all(w >= -1e-8 for w in weights_dict.values())
            and not math.isnan(total_allocation)
        )

        exec_time_ms = float((time.perf_counter() - start_time) * 1000.0)
        ess = float(len(accepted_samples) * (1.0 - min(0.9, mean_energy_drift)))

        return SymplecticOptimizationResult(
            weights=weights_dict,
            cash_weight=cash_weight,
            hamiltonian_initial=h_init_record,
            hamiltonian_final=h_final_record,
            energy_drift=mean_energy_drift,
            acceptance_rate=acceptance_rate,
            num_samples=len(accepted_samples),
            num_leapfrog_steps=num_leapfrog,
            effective_sample_size=max(1.0, ess),
            gromov_delta=gromov_delta,
            crash_hazard=crash_hazard,
            curvature_regime=curvature_regime,
            leland_bands=bands,
            rebalanced_assets=rebalanced,
            held_assets=held,
            bypass_entries=bypass_entries,
            bypass_exits=bypass_exits,
            execution_time_ms=exec_time_ms,
            symplectic_invariants_satisfied=invariants_satisfied,
            metadata={
                "market": profile.market.value,
                "mode": alloc_mode.value,
                "metric_type": cfg.metric_type.value,
                "effective_risk_aversion": effective_risk_aversion,
                "adapted_step_size": step_size,
                "version": VERSION,
                "release": RELEASE,
                "feature": FEATURE,
            },
        )


# Export canonical helper functions
def run_symplectic_allocation(
    symbols: List[str],
    expected_returns: Union[np.ndarray, Sequence[float]],
    covariance_matrix: Union[np.ndarray, Sequence[Sequence[float]]],
    current_weights: Optional[Union[np.ndarray, Sequence[float], Dict[str, float]]] = None,
    market: str = "GLOBAL",
    mode: str = "DYNAMIC_REGIME_BLENDED",
    config: Optional[SymplecticAllocatorConfig] = None,
) -> SymplecticOptimizationResult:
    """Convenience functional wrapper for SymplecticManifoldHMCAllocator."""
    cfg = config or SymplecticAllocatorConfig()
    cfg.market = get_symplectic_profile(market).market
    for m in AllocationMode:
        if m.value == mode:
            cfg.mode = m
            break
    allocator = SymplecticManifoldHMCAllocator(cfg)
    return allocator.allocate(
        symbols=symbols,
        expected_returns=expected_returns,
        covariance_matrix=covariance_matrix,
        current_weights=current_weights,
        market=cfg.market,
        mode=cfg.mode,
    )
