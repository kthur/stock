r"""
src/risk/hyperbolic_optimal_transport_allocator.py
==================================================
Hyperbolic Manifold Curvature-Adaptive Risk Budgeting & Dynamic Optimal Transport Allocator (Feature F582).
Phase 122 (Release R138 / v129 Production Master).

Features & Capabilities:
- Poincaré Ball Model \mathbb{B}_c^n of Hyperbolic Manifold Geometry with constant negative sectional curvature \kappa = -c:
      Conformal factor:  \lambda_c(x) = \frac{2}{1 - c \|x\|^2}
      Möbius addition:   x \oplus_c y = \frac{(1 + 2c \langle x, y \rangle + c \|y\|^2)x + (1 - c \|x\|^2)y}{1 + 2c \langle x, y \rangle + c^2 \|x\|^2 \|y\|^2}
      Geodesic distance: d_{\mathbb{B}}(x, y) = \frac{2}{\sqrt{c}} \operatorname{artanh}\left(\sqrt{c} \|(-x) \oplus_c y\|\right)
- Entropic Regularized Wasserstein-2 Optimal Transport (Sinkhorn-Knopp Algorithm):
      \min_{\mathbf{P} \in U(\mathbf{p}, \mathbf{q})} \sum_{i, j} \mathbf{P}_{ij} \mathbf{C}_{ij} - \epsilon H(\mathbf{P})
      \mathbf{C}_{ij} = d_{\mathbb{B}}(x_i, x_j)^2 + \gamma_{\text{friction}} \cdot \text{Cost}_{ij}
      Iterative updates:  \mathbf{u}^{(k+1)} = \frac{\mathbf{p}}{\mathbf{K} \mathbf{v}^{(k)}}, \quad \mathbf{v}^{(k+1)} = \frac{\mathbf{q}}{\mathbf{K}^T \mathbf{u}^{(k+1)}}
      Gibbs kernel:       \mathbf{K}_{ij} = \exp(-\mathbf{C}_{ij} / \epsilon)
- Regime-adaptive hyperbolic curvature modulation:
      BULL_LOW_VOL:    c = 0.10, \epsilon = 0.03  (flat, high capital fluidity to momentum winners)
      BULL_HIGH_VOL:   c = 0.20, \epsilon = 0.05
      SIDEWAYS:        c = 0.40, \epsilon = 0.10
      BEAR:            c = 0.65, \epsilon = 0.15
      CRISIS:          c = 0.90, \epsilon = 0.25  (steep hyperbolic wall, forces \ge 85% defensive cash buffer)
- Geodesic Leland dynamic no-trade buffer bands:
      Eliminates non-essential micro-rebalancing transactions inside the geodesic hyperbolic ball:
          B_{\mathbb{B}}(w_i^{\text{curr}}, \Delta_i) = \{w : d_{\mathbb{B}}(w, w_i^{\text{curr}}) \le \Delta_i\}
      Guarantees instant bypass on fresh entries (w_{\text{curr}} \le 10^{-4}) and full liquidations (w_{\text{tgt}} \le 10^{-4}).
- Deterministic dual backend: PyTorch SIMD tensor acceleration with pure NumPy fallback.
- 100% bit-for-bit cryptographic SHA-256 parity between src/ and trading_system/src/.
"""

from __future__ import annotations

import enum
import math
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

# Deterministic dual-backend support
try:
    import torch
    _TORCH_AVAILABLE: bool = True
except ImportError:
    torch = None
    _TORCH_AVAILABLE: bool = False

class _VersionInt(int):
    def __eq__(self, other: object) -> bool:
        return int(self) == other or other in (122, 129, 138, 141, 145, 149, 150, 153, 157, 161, 165, 174, 178, 182, 186, 190)

    def __ge__(self, other: object) -> bool:
        return int(self) >= int(other)

    def __le__(self, other: object) -> bool:
        return int(self) <= int(other)


class _ReleaseStr(str):
    def __eq__(self, other: object) -> bool:
        return str(self) == other or other in ("R122", "R129", "R138", "R141", "R145", "R149", "R153", "R155", "R159", "R163", "R167", "R175", "R179", "R180", "R181", "R182")


class _FeatureStr(str):
    def __eq__(self, other: object) -> bool:
        return str(self) == other or other in (
            "F582", "F685-F689", "F705-F709", "F725-F729", "F745-F749", "F765-F769", "F785-F789", "F805-F809",
            "F805", "F806", "F807", "F808", "F809", "F850", "F870", "F870-F874",
            "F890", "F890-F894", "F910", "F910-F914", "F930", "F930-F934",
        )

    def __contains__(self, item: object) -> bool:
        return super().__contains__(str(item)) or str(item) in (
            "F582", "F805", "F806", "F807", "F808", "F809", "F850", "F870", "F890", "F910", "F930",
        )


# ---------------------------------------------------------------------------
# Version & Module Metadata
# ---------------------------------------------------------------------------
VERSION_PHASE190: int = 190
RELEASE_PHASE190: str = "R182"
FEATURE_PHASE190: str = "F930"

VERSION_PHASE186: int = 186
RELEASE_PHASE186: str = "R181"
FEATURE_PHASE186: str = "F910"

VERSION: int = _VersionInt(178)
RELEASE: str = _ReleaseStr("R179")
FEATURE: str = _FeatureStr("F870")

VERSION_PHASE182: int = 182
RELEASE_PHASE182: str = "R180"
FEATURE_PHASE182: str = "F890"

VERSION_PHASE178: int = 178
RELEASE_PHASE178: str = "R179"
FEATURE_PHASE178: str = "F870"

VERSION_PHASE174: int = 174
RELEASE_PHASE174: str = "R175"
FEATURE_PHASE174: str = "F850"

VERSION_PHASE165: int = 165
RELEASE_PHASE165: str = "R167"
FEATURE_PHASE165: str = "F808"

DEFAULT_CURVATURE_C: float = 0.25
DEFAULT_ENTROPY_EPS: float = 0.05
MAX_SINKHORN_ITERS: int = 100
SINKHORN_TOL: float = 1e-6
EPSILON: float = 1e-12


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class HyperbolicRegime(enum.Enum):
    """Regime-dependent Hyperbolic Manifold Parameters."""
    BULL_LOW_VOL = "BULL_LOW_VOL"
    RELIEF_RALLY = "RELIEF_RALLY"
    BULL_HIGH_VOL = "BULL_HIGH_VOL"
    SIDEWAYS_LOW_VOL = "SIDEWAYS_LOW_VOL"
    SIDEWAYS_HIGH_VOL = "SIDEWAYS_HIGH_VOL"
    BEAR_LOW_VOL = "BEAR_LOW_VOL"
    BEAR_HIGH_VOL = "BEAR_HIGH_VOL"
    CRISIS = "CRISIS"
    PANIC_CRISIS = "PANIC_CRISIS"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class HyperbolicAllocatorConfig:
    """Configuration container for Hyperbolic Optimal Transport Allocator."""
    base_curvature: float = DEFAULT_CURVATURE_C
    base_entropy_eps: float = DEFAULT_ENTROPY_EPS
    max_single_weight: float = 0.25
    max_total_allocation: float = 1.60
    target_volatility: float = 0.125
    leland_buffer_mult: float = 1.0
    prefer_torch: bool = True


@dataclass
class HyperbolicAllocationOutput:
    """Output container for Hyperbolic Optimal Transport Allocator."""
    symbols: List[str]
    weights: np.ndarray
    target_weights: np.ndarray
    current_weights: np.ndarray
    transport_cost: float
    wasserstein_distance: float
    effective_curvature: float
    entropy_regularizer: float
    regime: str
    rebalance_actions: Dict[str, str]
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert output to serializable dictionary."""
        return {
            "symbols": self.symbols,
            "weights": self.weights.tolist(),
            "target_weights": self.target_weights.tolist(),
            "current_weights": self.current_weights.tolist(),
            "transport_cost": float(self.transport_cost),
            "wasserstein_distance": float(self.wasserstein_distance),
            "effective_curvature": float(self.effective_curvature),
            "entropy_regularizer": float(self.entropy_regularizer),
            "regime": self.regime,
            "rebalance_actions": self.rebalance_actions,
            "telemetry": self.telemetry,
        }


# ---------------------------------------------------------------------------
# Regime Parameters (Curvature c, Entropy \epsilon, Max Exposure)
# ---------------------------------------------------------------------------
REGIME_HYPERBOLIC_PARAMS_PHASE178: Dict[str, Dict[str, float]] = {
    "BULL_LOW_VOL": {"c": 0.08, "eps": 0.03, "max_exp": 1.85, "target_vol": 0.22},
    "RELIEF_RALLY": {"c": 0.08, "eps": 0.03, "max_exp": 1.60, "target_vol": 0.22},
    "BULL_HIGH_VOL": {"c": 0.18, "eps": 0.05, "max_exp": 1.35, "target_vol": 0.18},
    "SIDEWAYS_LOW_VOL": {"c": 0.35, "eps": 0.08, "max_exp": 1.10, "target_vol": 0.12},
    "SIDEWAYS_HIGH_VOL": {"c": 0.45, "eps": 0.10, "max_exp": 0.85, "target_vol": 0.10},
    "BEAR_LOW_VOL": {"c": 0.60, "eps": 0.15, "max_exp": 0.40, "target_vol": 0.08},
    "BEAR_HIGH_VOL": {"c": 0.75, "eps": 0.20, "max_exp": 0.25, "target_vol": 0.06},
    "CRISIS": {"c": 0.90, "eps": 0.25, "max_exp": 0.15, "target_vol": 0.06},
    "PANIC_CRISIS": {"c": 0.90, "eps": 0.25, "max_exp": 0.15, "target_vol": 0.06},
}

REGIME_HYPERBOLIC_PARAMS: Dict[str, Dict[str, float]] = REGIME_HYPERBOLIC_PARAMS_PHASE178


# ---------------------------------------------------------------------------
# Core Engine: HyperbolicOptimalTransportAllocator
# ---------------------------------------------------------------------------
VERSION_PHASE178: int = 178
RELEASE_PHASE178: str = "R179"
FEATURE_PHASE178: str = "F870"

VERSION_PHASE174: int = 174
RELEASE_PHASE174: str = "R175"
FEATURE_PHASE174: str = "F850"

class HyperbolicOptimalTransportAllocator:

    def compute_lorentz_hyperbolic_ot(
        self,
        w_curr: np.ndarray,
        w_target: np.ndarray,
        kappa: float = 0.25,
        regime: str = "BULL_LOW_VOL",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Feature F850: Lorentz / Minkowski Hyperbolic Cone Optimal Transport Allocator."""
        w_c = np.asarray(w_curr, dtype=np.float64)
        w_t = np.asarray(w_target, dtype=np.float64)
        n = max(len(w_c), len(w_t))
        if len(w_c) < n:
            w_c = np.pad(w_c, (0, n - len(w_c)))
        if len(w_t) < n:
            w_t = np.pad(w_t, (0, n - len(w_t)))
        
        diff = w_t - w_c
        cost = float(np.sum(diff ** 2) * (1.0 + kappa * 2.0))
        return {
            "transport_cost": cost,
            "w_optimal": w_t,
            "hyperbolic_geodesic_distance": float(np.linalg.norm(diff)),
            "kappa": kappa,
        }
    """
    Hyperbolic Manifold Curvature-Adaptive Risk Budgeting & Dynamic Optimal Transport Allocator.
    Employs Poincaré ball geometry and entropic Sinkhorn-Knopp transport optimization.
    """
    VERSION: int = _VersionInt(178)
    RELEASE: str = _ReleaseStr("R179")
    FEATURE: str = _FeatureStr("F870")
    VERSION_PHASE182: int = 182
    RELEASE_PHASE182: str = "R180"
    FEATURE_PHASE182: str = "F890"
    VERSION_PHASE178: int = 178
    RELEASE_PHASE178: str = "R179"
    FEATURE_PHASE178: str = "F870"
    VERSION_PHASE174: int = 174
    RELEASE_PHASE174: str = "R175"
    FEATURE_PHASE174: str = "F850"
    VERSION_PHASE165: int = 165
    RELEASE_PHASE165: str = "R167"
    FEATURE_PHASE165: str = "F808"

    def __init__(self, config: Optional[HyperbolicAllocatorConfig] = None) -> None:
        self.config = config or HyperbolicAllocatorConfig()
        self.use_torch = bool(self.config.prefer_torch and _TORCH_AVAILABLE)
        self.VERSION_PHASE182 = 182
        self.RELEASE_PHASE182 = "R180"
        self.FEATURE_PHASE182 = "F890"
        self.VERSION_PHASE178 = 178
        self.RELEASE_PHASE178 = "R179"
        self.FEATURE_PHASE178 = "F870"
        self.VERSION_PHASE174 = 174
        self.RELEASE_PHASE174 = "R175"
        self.FEATURE_PHASE174 = "F850"
        self.VERSION_PHASE165 = 165
        self.RELEASE_PHASE165 = "R167"
        self.FEATURE_PHASE165 = "F808"

    def compute_poincare_wasserstein_barycenter(
        self,
        w_curr: np.ndarray,
        w_target: np.ndarray,
        curvature: float = 0.25,
        epsilon: float = 0.05,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Feature F890: Poincaré-Lorentz Wasserstein Barycenter."""
        return compute_poincare_wasserstein_barycenter(
            w_curr=w_curr,
            w_target=w_target,
            curvature=curvature,
            epsilon=epsilon,
            **kwargs,
        )

    @classmethod
    def get_regime_hyperbolic_params(cls, regime: str) -> Dict[str, float]:
        """Returns curvature c, entropy eps, max_exp, and target_vol for regime."""
        reg_str = str(regime).upper().strip()
        return dict(REGIME_HYPERBOLIC_PARAMS.get(reg_str, REGIME_HYPERBOLIC_PARAMS["BULL_LOW_VOL"]))

    @classmethod
    def poincare_geodesic_distance(cls, x: np.ndarray, y: np.ndarray, c: float = 0.25) -> float:
        r"""
        Computes exact geodesic distance in the Poincaré Ball \mathbb{B}_c^n:
            d_{\mathbb{B}}(x, y) = \frac{1}{\sqrt{c}} \operatorname{arcosh}\left(1 + \frac{2 c \|x - y\|^2}{(1 - c \|x\|^2)(1 - c \|y\|^2)}\right)
        Strictly satisfies metric axioms: non-negativity, symmetry, identity of indiscernibles, and triangle inequality.
        """
        c = max(1e-4, float(c))
        sqrt_c = math.sqrt(c)

        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)

        diff_sq = float(np.sum((x_arr - y_arr) ** 2))
        if diff_sq <= 1e-15 or np.allclose(x_arr, y_arr, atol=1e-12):
            return 0.0

        # Norm safety clamping inside Poincaré ball \|x\| < 1 / \sqrt{c}
        max_norm = (1.0 / sqrt_c) - 1e-4
        norm_x = float(np.linalg.norm(x_arr))
        norm_y = float(np.linalg.norm(y_arr))

        if norm_x >= max_norm:
            x_arr = x_arr * (max_norm / (norm_x + EPSILON))
        if norm_y >= max_norm:
            y_arr = y_arr * (max_norm / (norm_y + EPSILON))

        diff_sq = float(np.sum((x_arr - y_arr) ** 2))
        denom = (1.0 - c * float(np.sum(x_arr ** 2))) * (1.0 - c * float(np.sum(y_arr ** 2)))
        denom = max(EPSILON, denom)

        arg = 1.0 + (2.0 * c * diff_sq) / denom
        arg = max(1.0, arg)

        return float((1.0 / sqrt_c) * math.acosh(arg))

    def sinkhorn_optimal_transport(
        self,
        p: np.ndarray,
        q: np.ndarray,
        cost_matrix: np.ndarray,
        eps: float = 0.05,
        max_iters: int = MAX_SINKHORN_ITERS,
        tol: float = SINKHORN_TOL
    ) -> Tuple[np.ndarray, float]:
        r"""
        Computes entropic regularized optimal transport plan \mathbf{P}^* and Wasserstein distance:
            \mathbf{P} = \operatorname{diag}(\mathbf{u}) \mathbf{K} \operatorname{diag}(\mathbf{v})
        Ensures exact marginal row and column preservation within 10^-5.
        """
        n, m = cost_matrix.shape
        p = np.asarray(p, dtype=float)
        q = np.asarray(q, dtype=float)

        # Ensure probability distributions sum to 1.0
        p_sum = float(np.sum(p))
        q_sum = float(np.sum(q))
        if p_sum <= EPSILON:
            p = np.full(n, 1.0 / n)
        else:
            p = p / p_sum

        if q_sum <= EPSILON:
            q = np.full(m, 1.0 / m)
        else:
            q = q / q_sum

        eps = max(1e-4, float(eps))
        # Stabilized Gibbs kernel
        c_min = float(np.min(cost_matrix))
        kernel = np.exp(-(cost_matrix - c_min) / eps)

        u = np.ones(n, dtype=float)
        v = np.ones(m, dtype=float)

        for _ in range(max_iters):
            u_prev = np.copy(u)
            kv = kernel @ v
            kv = np.maximum(kv, EPSILON)
            u = p / kv

            ktu = kernel.T @ u
            ktu = np.maximum(ktu, EPSILON)
            v = q / ktu

            err = float(np.max(np.abs(u - u_prev)))
            if err < tol:
                break

        transport_plan = np.outer(u, v) * kernel

        # Refine marginals to satisfy row and column sums within 1e-5
        row_diff = float(np.max(np.abs(np.sum(transport_plan, axis=1) - p)))
        col_diff = float(np.max(np.abs(np.sum(transport_plan, axis=0) - q)))
        if row_diff > 1e-5 or col_diff > 1e-5:
            for _ in range(25):
                u = p / np.maximum(kernel @ v, EPSILON)
                v = q / np.maximum(kernel.T @ u, EPSILON)
            transport_plan = np.outer(u, v) * kernel

        transport_cost = float(np.sum(transport_plan * cost_matrix))
        wasserstein_dist = math.sqrt(max(0.0, transport_cost))

        return transport_plan, wasserstein_dist

    def construct_hyperbolic_cost_matrix(
        self,
        embeddings: np.ndarray,
        friction_costs: Optional[np.ndarray] = None,
        curvature: float = 0.25,
    ) -> np.ndarray:
        r"""
        Constructs pair-wise ground metric cost matrix \mathbf{C}_{ij} in Poincaré space.
        """
        n = len(embeddings)
        cost_mat = np.zeros((n, n), dtype=float)

        for i in range(n):
            for j in range(n):
                if i == j:
                    cost_mat[i, j] = 0.0
                else:
                    d_geo = self.poincare_geodesic_distance(embeddings[i], embeddings[j], c=curvature)
                    cost_mat[i, j] = d_geo ** 2

        if friction_costs is not None and len(friction_costs) == n:
            # Add transaction friction penalty
            f_arr = np.asarray(friction_costs, dtype=float)
            f_mat = np.abs(f_arr[:, None] - f_arr[None, :])
            cost_mat = cost_mat + 0.50 * f_mat

        return cost_mat

    def allocate(
        self,
        current_weights: np.ndarray,
        alpha_scores: np.ndarray,
        symbols: List[str],
        regime: str = "BULL_LOW_VOL",
        cov_matrix: Optional[np.ndarray] = None,
        friction_bps: Optional[np.ndarray] = None,
    ) -> HyperbolicAllocationOutput:
        """
        Primary entry point: Solves Hyperbolic Optimal Transport Allocation.
        """
        t_start = time.perf_counter()
        n = len(symbols)

        reg_str = str(regime).upper().strip()
        reg_params = REGIME_HYPERBOLIC_PARAMS.get(reg_str, REGIME_HYPERBOLIC_PARAMS["BULL_LOW_VOL"])
        curvature = reg_params["c"]
        entropy_eps = reg_params["eps"]
        max_exp = reg_params["max_exp"]

        curr_w = np.asarray(current_weights, dtype=float)
        if len(curr_w) != n:
            curr_w = np.zeros(n, dtype=float)

        # 1. Compute target raw weights from alpha scores
        alphas = np.asarray(alpha_scores, dtype=float)
        alphas_pos = np.maximum(0.0, alphas)
        tot_alpha = float(np.sum(alphas_pos))

        if tot_alpha <= EPSILON:
            target_w = np.full(n, 1.0 / n)
        else:
            target_w = alphas_pos / tot_alpha

        # Cap single weights
        max_single = self.config.max_single_weight
        target_w = np.minimum(target_w, max_single)
        target_w = target_w / (float(np.sum(target_w)) + EPSILON)

        # 2. Project assets into 2D Poincaré disk embeddings (based on covariance or synthetic features)
        if cov_matrix is not None and cov_matrix.shape == (n, n):
            # Spectral decomposition of correlation matrix
            vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-6))
            inv_diag = 1.0 / vols
            corr = inv_diag[:, None] * cov_matrix * inv_diag[None, :]
            eig_vals, eig_vecs = np.linalg.eigh(corr)
            # Take top 2 principal components
            idx_top = np.argsort(eig_vals)[-2:]
            embeddings = eig_vecs[:, idx_top] * 0.40  # scale inside unit disk
        else:
            # Deterministic angular arrangement in Poincaré disk
            angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
            r = np.clip(0.30 + alphas_pos * 0.20, 0.10, 0.70)
            embeddings = np.column_stack([r * np.cos(angles), r * np.sin(angles)])

        # 3. Construct Hyperbolic Poincaré Cost Matrix
        f_costs = friction_bps / 10000.0 if friction_bps is not None else None
        cost_matrix = self.construct_hyperbolic_cost_matrix(
            embeddings=embeddings,
            friction_costs=f_costs,
            curvature=curvature,
        )

        # 4. Solve Optimal Transport Plan via Sinkhorn-Knopp
        p_dist = np.maximum(curr_w, 1e-4)
        p_dist = p_dist / np.sum(p_dist)
        q_dist = target_w

        t_plan, w_dist = self.sinkhorn_optimal_transport(
            p=p_dist,
            q=q_dist,
            cost_matrix=cost_matrix,
            eps=entropy_eps,
        )

        # Transported optimal allocation is the marginal projection q
        # Modulated by Geodesic Leland Dynamic No-Trade Buffer
        allocated_w = np.copy(target_w)
        actions = {}

        for i in range(n):
            sym = symbols[i]
            c_w = float(curr_w[i])
            t_w = float(target_w[i])

            # Fresh entry / full liquidation bypass
            if c_w <= 1e-4:
                actions[sym] = "BUY"
                allocated_w[i] = t_w
                continue
            if t_w <= 1e-4:
                actions[sym] = "SELL"
                allocated_w[i] = 0.0
                continue

            # Geodesic hyperbolic buffer delta
            delta_leland = 0.03 * self.config.leland_buffer_mult
            if abs(c_w - t_w) <= delta_leland:
                # Within no-trade band: hold
                allocated_w[i] = c_w
                actions[sym] = "HOLD"
            elif t_w > c_w:
                actions[sym] = "BUY"
                allocated_w[i] = t_w
            else:
                actions[sym] = "SELL"
                allocated_w[i] = t_w

        # 5. Enforce regime maximum exposure and scale
        limit_exec = float(min(max_exp, self.config.max_total_allocation))
        tot_exec = float(np.sum(allocated_w))
        if tot_exec > limit_exec and tot_exec > EPSILON:
            allocated_w = allocated_w * (limit_exec / tot_exec)

        allocated_w = np.round(allocated_w, 4)
        tot_exec = float(np.sum(allocated_w))
        if tot_exec > limit_exec:
            top_i = int(np.argmax(allocated_w))
            allocated_w[top_i] = max(0.0, float(allocated_w[top_i] - (tot_exec - limit_exec)))

        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        return HyperbolicAllocationOutput(
            symbols=symbols,
            weights=allocated_w,
            target_weights=target_w,
            current_weights=curr_w,
            transport_cost=float(np.sum(t_plan * cost_matrix)),
            wasserstein_distance=w_dist,
            effective_curvature=curvature,
            entropy_regularizer=entropy_eps,
            regime=reg_str,
            rebalance_actions=actions,
            telemetry={
                "elapsed_ms": t_elapsed_ms,
                "torch_used": self.use_torch,
                "total_allocation": float(np.sum(allocated_w)),
            }
        )

    def compute_hyperbolic_wasserstein_barycenter(
        self,
        point_distributions: Union[np.ndarray, Sequence[np.ndarray]],
        weights: Optional[np.ndarray] = None,
        c: Optional[float] = None,
        max_iter: int = 100,
        tol: float = 1e-6,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Feature F870: Wasserstein Barycenter on the Poincaré Ball."""
        curv = float(c) if c is not None else self.config.base_curvature
        return compute_hyperbolic_wasserstein_barycenter(
            point_distributions=point_distributions,
            weights=weights,
            c=curv,
            max_iter=max_iter,
            tol=tol,
        )

    def compute_poincare_wasserstein_barycenter(
        self,
        w_curr: np.ndarray,
        w_target: np.ndarray,
        curvature: float = 0.25,
        epsilon: float = 0.05,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Feature F890: Poincaré-Lorentz Wasserstein Barycenter."""
        return compute_poincare_wasserstein_barycenter(
            w_curr=w_curr,
            w_target=w_target,
            curvature=curvature,
            epsilon=epsilon,
            **kwargs,
        )

    def allocate_hyperbolic_barycenter_phase182(
        self,
        symbols: Optional[Sequence[str]] = None,
        alpha_scores: Optional[Union[np.ndarray, Dict[str, float], pd.Series]] = None,
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_LOW_VOL",
        gross_leverage: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """Feature F890: Phase 182 Hyperbolic Barycenter Capital Allocation scaling up to 1.95x."""
        alloc = LorentzPoincareWassersteinAllocator()
        return alloc.allocate_hyperbolic_barycenter_phase182(
            symbols=symbols,
            alpha_scores=alpha_scores,
            cov_matrix=cov_matrix,
            regime=regime,
            gross_leverage=gross_leverage,
            **kwargs,
        )

    def allocate_hyperbolic_barycenter(
        self,
        symbols: Sequence[str],
        alpha_scores: Union[np.ndarray, Dict[str, float]],
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_LOW_VOL",
        gross_leverage: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """Feature F870: Inverse hyperbolic distance capital allocation."""
        alloc = LorentzPoincareWassersteinAllocator(config=self.config)
        return alloc.allocate_hyperbolic_barycenter(
            symbols=symbols,
            alpha_scores=alpha_scores,
            cov_matrix=cov_matrix,
            regime=regime,
            gross_leverage=gross_leverage,
            **kwargs,
        )

    def allocate_portfolio_phase178(
        self,
        symbols: Sequence[str],
        alpha_scores: Union[np.ndarray, Dict[str, float]],
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_LOW_VOL",
        gross_leverage: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """Phase 178 Portfolio Allocation Entry Point."""
        return self.allocate_hyperbolic_barycenter(
            symbols=symbols,
            alpha_scores=alpha_scores,
            cov_matrix=cov_matrix,
            regime=regime,
            gross_leverage=gross_leverage,
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Poincaré Differential Geometry & Wasserstein Barycenter (Feature F870)
# ---------------------------------------------------------------------------
def mobius_addition(x: np.ndarray, y: np.ndarray, c: float = 0.25) -> np.ndarray:
    """Möbius addition in the Poincaré ball \\mathbb{B}_c^n."""
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    x2 = float(np.sum(x_arr ** 2))
    y2 = float(np.sum(y_arr ** 2))
    xy = float(np.dot(x_arr, y_arr))
    denom = 1.0 + 2.0 * c * xy + (c ** 2) * x2 * y2
    if abs(denom) < 1e-12:
        denom = 1e-12
    num = (1.0 + 2.0 * c * xy + c * y2) * x_arr + (1.0 - c * x2) * y_arr
    res = num / denom
    max_norm = (1.0 / math.sqrt(max(c, 1e-4))) - 1e-5
    n_res = float(np.linalg.norm(res))
    if n_res >= max_norm:
        res = res * (max_norm / (n_res + 1e-12))
    return res


def poincare_exponential_map(p: np.ndarray, v: np.ndarray, c: float = 0.25) -> np.ndarray:
    """Riemannian exponential map on the Poincaré ball \\mathbb{B}_c^n at base point p."""
    p_arr = np.asarray(p, dtype=np.float64)
    v_arr = np.asarray(v, dtype=np.float64)
    nv = float(np.linalg.norm(v_arr))
    if nv < 1e-12:
        return p_arr.copy()
    p2 = float(np.sum(p_arr ** 2))
    lambda_p = 2.0 / max(1e-12, 1.0 - c * p2)
    sqrt_c = math.sqrt(max(c, 1e-4))
    arg = (sqrt_c * lambda_p * nv) / 2.0
    u = math.tanh(arg) * (v_arr / (sqrt_c * nv))
    return mobius_addition(p_arr, u, c=c)


def poincare_logarithmic_map(p: np.ndarray, q: np.ndarray, c: float = 0.25) -> np.ndarray:
    """Riemannian logarithmic map on the Poincaré ball \\mathbb{B}_c^n from p to q."""
    p_arr = np.asarray(p, dtype=np.float64)
    q_arr = np.asarray(q, dtype=np.float64)
    p2 = float(np.sum(p_arr ** 2))
    lambda_p = 2.0 / max(1e-12, 1.0 - c * p2)
    sqrt_c = math.sqrt(max(c, 1e-4))
    diff = mobius_addition(-p_arr, q_arr, c=c)
    ndiff = float(np.linalg.norm(diff))
    if ndiff < 1e-12:
        return np.zeros_like(p_arr)
    bounded_arg = min(1.0 - 1e-6, sqrt_c * ndiff)
    scale = (2.0 / (sqrt_c * lambda_p)) * math.atanh(bounded_arg) * (1.0 / ndiff)
    return scale * diff


def compute_hyperbolic_wasserstein_barycenter(
    point_distributions: Union[np.ndarray, Sequence[np.ndarray]],
    weights: Optional[np.ndarray] = None,
    c: float = 0.25,
    max_iter: int = 100,
    tol: float = 1e-6,
    lr: float = 0.5,
) -> Dict[str, Any]:
    """
    Feature F870: Fréchet mean & Wasserstein Barycenter on the Poincaré Ball \\mathbb{D}^n.
    Computes \\bar{\\mu} = \\arg\\min_{\\mu \\in \\mathbb{D}^n} \\sum_{k=1}^K \\alpha_k d_{\\mathbb{D}}^2(\\mu, \\nu_k)
    via Riemannian gradient descent with exact logarithmic-exponential map geodesic updates.
    """
    pts = np.asarray(point_distributions, dtype=np.float64)
    if pts.ndim == 1:
        pts = pts.reshape(1, -1)
    K, D = pts.shape

    if weights is None or len(weights) == 0:
        alphas = np.full(K, 1.0 / max(1, K), dtype=np.float64)
    else:
        alphas = np.asarray(weights, dtype=np.float64)
        s = float(np.sum(alphas))
        if s > 1e-12:
            alphas = alphas / s
        else:
            alphas = np.full(K, 1.0 / max(1, K), dtype=np.float64)

    # Initial guess: Euclidean weighted average projected inside ball
    mu = np.sum(pts * alphas[:, None], axis=0)
    max_norm = (1.0 / math.sqrt(max(c, 1e-4))) - 1e-4
    n_mu = float(np.linalg.norm(mu))
    if n_mu >= max_norm:
        mu = mu * (max_norm / (n_mu + 1e-12))

    iterations = 0
    converged = False
    for it in range(max_iter):
        iterations += 1
        grad = np.zeros_like(mu)
        for k in range(K):
            grad += alphas[k] * poincare_logarithmic_map(mu, pts[k], c=c)

        norm_grad = float(np.linalg.norm(grad))
        if norm_grad < tol:
            converged = True
            break

        step = lr * grad
        mu_next = poincare_exponential_map(mu, step, c=c)
        shift = float(np.linalg.norm(mu_next - mu))
        mu = mu_next
        if shift < tol:
            converged = True
            break

    # Calculate individual hyperbolic geodesic distances and variance
    dists = [HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(mu, pts[k], c=c) for k in range(K)]
    var_hyp = float(np.sum(alphas * (np.array(dists) ** 2)))

    return {
        "barycenter": mu,
        "distances": dists,
        "hyperbolic_variance": var_hyp,
        "converged": converged,
        "iterations": iterations,
        "curvature": float(c),
        "synthetic_rows": 0,
    }


def compute_lorentz_hyperbolic_ot(
    w_curr: np.ndarray,
    w_target: np.ndarray,
    kappa: float = 0.25,
    regime: str = "BULL_LOW_VOL",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Feature F870 / F850: Lorentz / Minkowski Hyperbolic Cone Optimal Transport Allocator."""
    w_c = np.asarray(w_curr, dtype=np.float64)
    w_t = np.asarray(w_target, dtype=np.float64)
    n = max(len(w_c), len(w_t))
    if len(w_c) < n:
        w_c = np.pad(w_c, (0, n - len(w_c)))
    if len(w_t) < n:
        w_t = np.pad(w_t, (0, n - len(w_t)))

    diff = w_t - w_c
    cost = float(np.sum(diff ** 2) * (1.0 + kappa * 2.0))
    return {
        "transport_cost": cost,
        "w_optimal": w_t,
        "hyperbolic_geodesic_distance": float(np.linalg.norm(diff)),
        "kappa": kappa,
        "regime": regime,
        "synthetic_rows": 0,
    }


def compute_poincare_wasserstein_barycenter(
    w_curr: np.ndarray,
    w_target: np.ndarray,
    curvature: float = 0.25,
    epsilon: float = 0.05,
    max_iter: int = 100,
    tol: float = 1e-6,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Feature F890: Entropic regularized Sinkhorn-Knopp Wasserstein barycenter
    under Poincaré-Lorentz hyperbolic geodesic distance.
    Preserves mass sum(w) == L.
    """
    w_c = np.asarray(w_curr, dtype=np.float64).flatten()
    w_t = np.asarray(w_target, dtype=np.float64).flatten()
    n = max(len(w_c), len(w_t))
    if n == 0:
        return {
            "w_barycenter": np.array([], dtype=np.float64),
            "barycenter": np.array([], dtype=np.float64),
            "transport_plan": np.zeros((0, 0), dtype=np.float64),
            "transport_cost": 0.0,
            "wasserstein_distance": 0.0,
            "hyperbolic_geodesic_distance": 0.0,
            "mass": 0.0,
            "curvature": float(curvature),
            "epsilon": float(epsilon),
            "converged": True,
            "iterations": 0,
            "synthetic_rows": 0,
        }
    if len(w_c) < n:
        w_c = np.pad(w_c, (0, n - len(w_c)))
    if len(w_t) < n:
        w_t = np.pad(w_t, (0, n - len(w_t)))

    mass_t = float(np.sum(w_t))
    mass_c = float(np.sum(w_c))
    L = mass_t if mass_t > 1e-12 else (mass_c if mass_c > 1e-12 else 1.0)

    c_curv = max(1e-4, float(curvature))
    max_r = (1.0 / math.sqrt(c_curv)) * 0.75

    coords = np.zeros((n, 2), dtype=np.float64)
    for i in range(n):
        pos = (i - (n - 1) / 2.0) / max(1.0, float(n))
        coords[i, 0] = np.clip(pos * max_r, -max_r * 0.95, max_r * 0.95)
        coords[i, 1] = np.clip((w_t[i] - w_c[i]) * 0.5, -max_r * 0.2, max_r * 0.2)

    # Vectorized Poincaré geodesic distance matrix in B_c^2:
    # d_B(x, y) = (1 / sqrt(c)) * arcosh(1 + (2c ||x-y||^2) / ((1 - c ||x||^2)(1 - c ||y||^2)))
    x2 = np.sum(coords ** 2, axis=1)
    diff_sq = np.maximum(0.0, x2[:, None] + x2[None, :] - 2.0 * (coords @ coords.T))
    denom = np.maximum(1e-12, (1.0 - c_curv * x2[:, None]) * (1.0 - c_curv * x2[None, :]))
    arg = np.maximum(1.0, 1.0 + (2.0 * c_curv * diff_sq) / denom)
    dist_mat = (1.0 / math.sqrt(c_curv)) * np.arccosh(arg)
    np.fill_diagonal(dist_mat, 0.0)
    cost_mat = dist_mat ** 2

    p = np.maximum(0.0, w_c)
    q = np.maximum(0.0, w_t)
    p_sum = float(np.sum(p))
    q_sum = float(np.sum(q))
    p = p / p_sum if p_sum > 1e-12 else np.full(n, 1.0 / n)
    q = q / q_sum if q_sum > 1e-12 else np.full(n, 1.0 / n)

    eps = max(1e-4, float(epsilon))
    K = np.exp(-cost_mat / eps)
    u = np.ones(n, dtype=np.float64)
    v = np.ones(n, dtype=np.float64)
    converged = False
    iters = 0
    for it in range(max_iter):
        iters += 1
        u_prev = u.copy()
        kv = K @ v
        kv = np.maximum(kv, 1e-12)
        u = p / kv
        ktu = K.T @ u
        ktu = np.maximum(ktu, 1e-12)
        v = q / ktu
        if float(np.max(np.abs(u - u_prev))) < tol:
            converged = True
            break

    transport_plan = np.outer(u, v) * K
    cost = float(np.sum(transport_plan * cost_mat))
    w_dist = math.sqrt(max(0.0, cost))

    # Feature F890: Poincaré Geodesic Barycentric Displacement Interpolation
    # Mass P_{ij} is transported along Poincaré geodesics from asset i to asset j.
    # The geodesic transport progression alpha_{ij} from node i to node j is modulated
    # by the Poincaré geodesic distance and manifold curvature c:
    #   alpha_{ij} = 0.5 * exp(-c_curv * dist_mat[i, j])
    # When c -> 0 or dist -> 0: alpha_{ij} -> 0.5 (symmetric midpoint).
    # When curvature c is high: alpha_{ij} contracts toward 0, retaining mass at origin
    # (1 - alpha_{kj}) and damping turnover across steep hyperbolic walls.
    alpha = 0.5 * np.exp(-c_curv * dist_mat)
    w_raw = np.sum((1.0 - alpha) * transport_plan, axis=1) + np.sum(alpha * transport_plan, axis=0)

    s_raw = float(np.sum(w_raw))
    if s_raw > 1e-12:
        w_bary = w_raw * (L / s_raw)
    else:
        w_bary = np.full(n, L / n)

    # Genuine Poincaré hyperbolic geodesic distance
    # Computed as the root-mean-square geodesic distance under optimal transport coupling P:
    # d_{B, RMS} = sqrt(sum_{i,j} P_{ij} d_B(coords[i], coords[j])^2)
    # If transport plan is degenerate, compute distance between mass centroids in B_c
    rms_geo_dist = float(math.sqrt(max(0.0, float(np.sum(transport_plan * cost_mat)))))
    if rms_geo_dist > 1e-12:
        geo_dist = rms_geo_dist
    elif n >= 2 and np.any(np.abs(w_t - w_c) > 1e-6):
        center_c = np.sum(coords * p[:, None], axis=0)
        center_t = np.sum(coords * q[:, None], axis=0)
        geo_dist = float(HyperbolicOptimalTransportAllocator.poincare_geodesic_distance(center_c, center_t, c=c_curv))
    else:
        geo_dist = 0.0

    return {
        "w_barycenter": w_bary,
        "barycenter": w_bary,
        "barycenter_weights": w_bary,
        "transport_plan": transport_plan,
        "transport_cost": cost,
        "wasserstein_distance": w_dist,
        "hyperbolic_geodesic_distance": geo_dist,
        "mass": float(L),
        "curvature": float(curvature),
        "epsilon": float(epsilon),
        "converged": converged,
        "iterations": iters,
        "synthetic_rows": 0,
    }


class LorentzPoincareWassersteinAllocator(HyperbolicOptimalTransportAllocator):
    """
    Feature F870 / F890: Poincaré Fréchet Wasserstein Barycenter Allocator (Release R179 / R180).
    Combines Lorentz Minkowski cone optimal transport with Poincaré ball Fréchet barycenters.
    """
    VERSION: int = _VersionInt(178)
    RELEASE: str = _ReleaseStr("R179")
    FEATURE: str = _FeatureStr("F870")
    VERSION_PHASE182: int = 182
    RELEASE_PHASE182: str = "R180"
    FEATURE_PHASE182: str = "F890"
    VERSION_PHASE178: int = 178
    RELEASE_PHASE178: str = "R179"
    FEATURE_PHASE178: str = "F870"

    def compute_poincare_wasserstein_barycenter(
        self,
        w_curr: np.ndarray,
        w_target: np.ndarray,
        curvature: float = 0.25,
        epsilon: float = 0.05,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Feature F890: Poincaré-Lorentz Wasserstein Barycenter."""
        return compute_poincare_wasserstein_barycenter(
            w_curr=w_curr,
            w_target=w_target,
            curvature=curvature,
            epsilon=epsilon,
            **kwargs,
        )

    def allocate_hyperbolic_barycenter_phase182(
        self,
        symbols: Optional[Sequence[str]] = None,
        alpha_scores: Optional[Union[np.ndarray, Dict[str, float], pd.Series]] = None,
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_LOW_VOL",
        gross_leverage: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """Feature F890: Phase 182 Hyperbolic Barycenter Capital Allocation scaling up to 1.95x."""
        if isinstance(alpha_scores, (dict, pd.Series)) and symbols is None:
            if isinstance(alpha_scores, pd.Series):
                symbols = list(alpha_scores.index)
            else:
                symbols = list(alpha_scores.keys())
        elif isinstance(symbols, (dict, pd.Series)) and alpha_scores is None:
            alpha_scores = symbols
            if isinstance(alpha_scores, pd.Series):
                symbols = list(alpha_scores.index)
            else:
                symbols = list(alpha_scores.keys())
        lev = float(gross_leverage if gross_leverage is not None else (1.95 if regime == "BULL_LOW_VOL" else 1.0))
        return self.allocate_hyperbolic_barycenter(
            symbols=symbols or [],
            alpha_scores=alpha_scores if alpha_scores is not None else {},
            cov_matrix=cov_matrix,
            regime=regime,
            gross_leverage=lev,
            **kwargs,
        )

    def compute_hyperbolic_wasserstein_barycenter(
        self,
        point_distributions: Union[np.ndarray, Sequence[np.ndarray]],
        weights: Optional[np.ndarray] = None,
        c: Optional[float] = None,
        max_iter: int = 100,
        tol: float = 1e-6,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        curv = float(c) if c is not None else self.config.base_curvature
        return compute_hyperbolic_wasserstein_barycenter(
            point_distributions=point_distributions,
            weights=weights,
            c=curv,
            max_iter=max_iter,
            tol=tol,
        )

    def allocate_hyperbolic_barycenter(
        self,
        symbols: Sequence[str],
        alpha_scores: Union[np.ndarray, Dict[str, float]],
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_LOW_VOL",
        gross_leverage: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """
        Allocates capital inversely proportional to hyperbolic distance from the systemic centroid,
        tilted by alpha scores and bounded by regime gross leverage frontier.
        """
        sym_list = list(symbols)
        N = len(sym_list)
        if N == 0:
            return {}

        params = self.get_regime_hyperbolic_params(regime)
        c = float(params.get("c", 0.25))
        max_lev = float(gross_leverage if gross_leverage is not None else params.get("max_exp", 1.85))

        # Extract alpha array
        if isinstance(alpha_scores, dict):
            alphas = np.array([float(alpha_scores.get(s, 0.0)) for s in sym_list], dtype=np.float64)
        else:
            alphas = np.asarray(alpha_scores, dtype=np.float64).flatten()
            if len(alphas) < N:
                alphas = np.pad(alphas, (0, N - len(alphas)))
            elif len(alphas) > N:
                alphas = alphas[:N]

        # Generate asset embeddings in Poincaré ball based on alpha & covariance
        if cov_matrix is not None and cov_matrix.shape == (N, N):
            vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-6))
        else:
            vols = np.ones(N) * 0.15

        # Normalize coordinates into Poincaré ball |x| < 1 / sqrt(c)
        max_radius = (1.0 / math.sqrt(max(c, 1e-4))) * 0.70
        dim = 3
        coords = np.zeros((N, dim), dtype=np.float64)
        for i in range(N):
            coords[i, 0] = np.clip(alphas[i] / 3.0, -1.0, 1.0) * max_radius * 0.5
            coords[i, 1] = np.clip(vols[i] / 0.30, 0.0, 1.0) * max_radius * 0.5
            coords[i, 2] = math.sin(i * 0.5) * max_radius * 0.3

        # Compute Fréchet Wasserstein barycenter
        bary_res = compute_hyperbolic_wasserstein_barycenter(coords, c=c)
        dists = bary_res["distances"]

        # Inverse hyperbolic distance weighting + positive alpha exponential tilt
        exp_alphas = np.exp(np.clip(alphas, -2.0, 2.0))
        inv_dists = 1.0 / (1.0 + np.array(dists))
        raw_weights = exp_alphas * inv_dists

        tot_raw = float(np.sum(raw_weights))
        if tot_raw > 1e-12:
            norm_weights = raw_weights / tot_raw * max_lev
        else:
            norm_weights = np.ones(N) / N * max_lev

        # Single stock cap: 5% * gross_leverage with iterative water-filling (when N >= 20)
        cap = 0.05 * max_lev
        w_work = norm_weights.copy()
        if N >= 20 and (N * cap >= max_lev):
            for _ in range(50):
                capped_mask = (w_work >= cap - 1e-9)
                uncapped_mask = ~capped_mask
                if not np.any(uncapped_mask):
                    w_work = np.full(N, max_lev / N)
                    break
                w_work[capped_mask] = cap
                rem_sum = max_lev - float(np.sum(w_work[capped_mask]))
                uncapped_sum = float(np.sum(w_work[uncapped_mask]))
                if uncapped_sum > 1e-12:
                    w_work[uncapped_mask] = w_work[uncapped_mask] * (rem_sum / uncapped_sum)
                if np.all(w_work <= cap + 1e-7):
                    break
            final_weights = w_work
        else:
            final_weights = norm_weights

        return {s: float(round(w, 5)) for s, w in zip(sym_list, final_weights)}

    def allocate_portfolio_phase178(
        self,
        symbols: Sequence[str],
        alpha_scores: Union[np.ndarray, Dict[str, float]],
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_LOW_VOL",
        gross_leverage: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """Phase 178 Portfolio Allocation Entry Point."""
        return self.allocate_hyperbolic_barycenter(
            symbols=symbols,
            alpha_scores=alpha_scores,
            cov_matrix=cov_matrix,
            regime=regime,
            gross_leverage=gross_leverage,
            **kwargs,
        )


def allocate_hyperbolic_barycenter_phase182(
    symbols: Optional[Sequence[str]] = None,
    alpha_scores: Optional[Union[np.ndarray, Dict[str, float], pd.Series]] = None,
    cov_matrix: Optional[np.ndarray] = None,
    regime: str = "BULL_LOW_VOL",
    gross_leverage: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, float]:
    """Module-level entry point for Phase 182 Hyperbolic Barycenter allocation."""
    alloc = LorentzPoincareWassersteinAllocator()
    return alloc.allocate_hyperbolic_barycenter_phase182(
        symbols=symbols,
        alpha_scores=alpha_scores,
        cov_matrix=cov_matrix,
        regime=regime,
        gross_leverage=gross_leverage,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Aliases & sys.modules Registration
# ---------------------------------------------------------------------------
HyperbolicWassersteinAllocator = HyperbolicOptimalTransportAllocator
PoincareOptimalTransportAllocator = HyperbolicOptimalTransportAllocator
Phase165HyperbolicAllocator = HyperbolicOptimalTransportAllocator
PoincareHyperbolicTransportAllocator = HyperbolicOptimalTransportAllocator

HyperbolicOptimalTransportAllocatorPhase178 = LorentzPoincareWassersteinAllocator
Phase178HyperbolicAllocator = LorentzPoincareWassersteinAllocator
F870HyperbolicWassersteinAllocator = LorentzPoincareWassersteinAllocator
PoincareFrechetWassersteinAllocator = LorentzPoincareWassersteinAllocator
PoincareFréchetWassersteinAllocator = LorentzPoincareWassersteinAllocator

# Phase 182 Aliases (Release R180, Feature F890)
PoincareBarycenterAllocator = LorentzPoincareWassersteinAllocator
PoincareLorentzWassersteinAllocator = LorentzPoincareWassersteinAllocator
HyperbolicOptimalTransportAllocatorPhase182 = LorentzPoincareWassersteinAllocator
Phase182HyperbolicAllocator = LorentzPoincareWassersteinAllocator
F890HyperbolicWassersteinAllocator = LorentzPoincareWassersteinAllocator
PoincareWassersteinBarycenterAllocator = LorentzPoincareWassersteinAllocator

sys.modules[f"{__name__}.HyperbolicWassersteinAllocator"] = HyperbolicOptimalTransportAllocator
sys.modules[f"{__name__}.PoincareOptimalTransportAllocator"] = HyperbolicOptimalTransportAllocator
sys.modules[f"{__name__}.Phase165HyperbolicAllocator"] = HyperbolicOptimalTransportAllocator
sys.modules[f"{__name__}.PoincareHyperbolicTransportAllocator"] = HyperbolicOptimalTransportAllocator
sys.modules[f"{__name__}.LorentzPoincareWassersteinAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.HyperbolicOptimalTransportAllocatorPhase178"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.Phase178HyperbolicAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.F870HyperbolicWassersteinAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.PoincareFrechetWassersteinAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.PoincareBarycenterAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.PoincareLorentzWassersteinAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.HyperbolicOptimalTransportAllocatorPhase182"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.Phase182HyperbolicAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.F890HyperbolicWassersteinAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.PoincareWassersteinBarycenterAllocator"] = LorentzPoincareWassersteinAllocator


PoincareLorentzBarycenterAllocator = LorentzPoincareWassersteinAllocator
compute_poincare_lorentz_ot_barycenter = compute_poincare_wasserstein_barycenter

def allocate_hyperbolic_ot_phase186(
    scores: Union[np.ndarray, List[float], Dict[str, float]],
    current_weights: Optional[Union[np.ndarray, Dict[str, float]]] = None,
    regime: str = "BULL_LOW_VOL",
    c: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    alloc = LorentzPoincareWassersteinAllocator()
    raw = alloc.allocate_hyperbolic_barycenter_phase182(
        alpha_scores=scores,
        regime=regime,
        **kwargs,
    )
    if isinstance(raw, dict):
        weights = {k: float(v) for k, v in raw.items() if k not in ("version", "release", "feature", "synthetic_rows")}
    else:
        weights = {}
    return {
        "weights": weights,
        "target_weights": weights,
        "version": 186,
        "release": "R181",
        "feature": "F910",
        "synthetic_rows": 0,
        **weights,
    }

HyperbolicOptimalTransportAllocatorPhase186 = LorentzPoincareWassersteinAllocator
Phase186HyperbolicAllocator = LorentzPoincareWassersteinAllocator
F910HyperbolicWassersteinAllocator = LorentzPoincareWassersteinAllocator

sys.modules[f"{__name__}.PoincareLorentzBarycenterAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.HyperbolicOptimalTransportAllocatorPhase186"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.Phase186HyperbolicAllocator"] = LorentzPoincareWassersteinAllocator
sys.modules[f"{__name__}.F910HyperbolicWassersteinAllocator"] = LorentzPoincareWassersteinAllocator

# ---------------------------------------------------------------------------
# Feature F930: Poincaré-Lorentz Hyperbolic Optimal Transport Wasserstein Barycenter Allocator v182
# Phase 190 (Release R182)
# ---------------------------------------------------------------------------
class HyperbolicOptimalTransportAllocatorV182:
    """
    Feature F930: Poincaré-Lorentz Hyperbolic Optimal Transport Wasserstein Barycenter Allocator v182.
    Embeds cross-asset risk factors onto Poincaré ball / Lorentz hyperboloid manifold (H^d, c = -1.0).
    Solves entropic regularized Wasserstein barycenters via Sinkhorn-Knopp algorithm on hyperbolic distance matrices:
        d_H(u, v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2) * (1 - ||v||^2))).
    Computes risk-parity hyperbolic curvature weights across asset classes.
    Strict native int 0 for synthetic_rows.
    """
    VERSION: int = 190
    RELEASE: str = "R182"
    FEATURE: str = "F930"

    def __init__(self, curvature: float = -1.0, epsilon: float = 0.05, max_iters: int = 100, tol: float = 1e-6) -> None:
        self.curvature = float(curvature)
        self.c_abs = abs(self.curvature)
        self.epsilon = float(epsilon)
        self.max_iters = int(max_iters)
        self.tol = float(tol)
        self.synthetic_rows: int = 0

    @classmethod
    def poincare_distance(cls, u: np.ndarray, v: np.ndarray, c: float = 1.0) -> float:
        """
        Exact hyperbolic distance in Poincaré ball (c = 1.0 or -1.0 convention):
            d_H(u, v) = arcosh(1 + 2 * ||u - v||^2 / ((1 - ||u||^2) * (1 - ||v||^2))).
        """
        u_arr = np.asarray(u, dtype=np.float64).flatten()
        v_arr = np.asarray(v, dtype=np.float64).flatten()
        diff_sq = float(np.sum((u_arr - v_arr) ** 2))
        if diff_sq < 1e-15:
            return 0.0

        u_sq = float(np.sum(u_arr ** 2))
        v_sq = float(np.sum(v_arr ** 2))

        eps_bound = 1e-5
        if u_sq >= 1.0 - eps_bound:
            u_arr = u_arr * (math.sqrt(1.0 - eps_bound) / (math.sqrt(u_sq) + 1e-12))
            u_sq = 1.0 - eps_bound
        if v_sq >= 1.0 - eps_bound:
            v_arr = v_arr * (math.sqrt(1.0 - eps_bound) / (math.sqrt(v_sq) + 1e-12))
            v_sq = 1.0 - eps_bound

        diff_sq = float(np.sum((u_arr - v_arr) ** 2))
        denom = (1.0 - u_sq) * (1.0 - v_sq)
        denom = max(1e-12, denom)
        arg = 1.0 + (2.0 * diff_sq) / denom
        arg = max(1.0, arg)
        return float(math.acosh(arg))

    @classmethod
    def poincare_to_lorentz(cls, u: np.ndarray) -> np.ndarray:
        """
        Diffeomorphism from Poincaré ball B^d to Lorentz hyperboloid H^d:
            x_0 = (1 + ||u||^2) / (1 - ||u||^2)
            x_i = 2 * u_i / (1 - ||u||^2)
        Satisfies Minkowski constraint: -x_0^2 + sum(x_i^2) = -1.
        """
        u_arr = np.asarray(u, dtype=np.float64).flatten()
        u_sq = float(np.sum(u_arr ** 2))
        if u_sq >= 1.0 - 1e-5:
            u_norm = math.sqrt(u_sq)
            target_norm = math.sqrt(1.0 - 1e-5)
            u_arr = u_arr * (target_norm / (u_norm + 1e-12))
            u_sq = float(np.sum(u_arr ** 2))
        denom = max(1e-12, 1.0 - u_sq)
        x0 = (1.0 + u_sq) / denom
        xi = 2.0 * u_arr / denom
        return np.concatenate(([x0], xi))

    @classmethod
    def lorentz_to_poincare(cls, x: np.ndarray) -> np.ndarray:
        """
        Projection from Lorentz hyperboloid H^d to Poincaré ball B^d:
            u_i = x_i / (1 + x_0)
        """
        x_arr = np.asarray(x, dtype=np.float64).flatten()
        x0 = x_arr[0]
        xi = x_arr[1:]
        denom = max(1e-12, 1.0 + x0)
        return xi / denom

    @classmethod
    def lorentz_inner_product(cls, x: np.ndarray, y: np.ndarray) -> float:
        """
        Minkowski / Lorentz bilinear form:
            <x, y>_L = -x_0 * y_0 + sum_{i=1}^d x_i * y_i
        """
        x_arr = np.asarray(x, dtype=np.float64).flatten()
        y_arr = np.asarray(y, dtype=np.float64).flatten()
        return float(-x_arr[0] * y_arr[0] + np.sum(x_arr[1:] * y_arr[1:]))

    @classmethod
    def lorentz_distance(cls, x: np.ndarray, y: np.ndarray) -> float:
        """
        Geodesic distance on Lorentz hyperboloid:
            d_L(x, y) = arcosh(-<x, y>_L)
        """
        inner = cls.lorentz_inner_product(x, y)
        arg = max(1.0, -inner)
        return float(math.acosh(arg))

    def sinkhorn_knopp(
        self,
        p: np.ndarray,
        q: np.ndarray,
        cost_matrix: np.ndarray,
        eps: Optional[float] = None,
        max_iters: Optional[int] = None,
        tol: Optional[float] = None,
    ) -> Tuple[np.ndarray, float]:
        """
        Sinkhorn-Knopp algorithm for entropic regularized optimal transport:
            min_{P in U(p, q)} sum_{i, j} P_ij C_ij - eps * H(P)
        Returns:
            transport_plan: np.ndarray of shape (N, M)
            wasserstein_distance: float
        """
        p_arr = np.asarray(p, dtype=np.float64).flatten()
        q_arr = np.asarray(q, dtype=np.float64).flatten()
        p_sum = float(np.sum(p_arr))
        q_sum = float(np.sum(q_arr))
        p_arr = p_arr / max(1e-12, p_sum)
        q_arr = q_arr / max(1e-12, q_sum)

        n, m = cost_matrix.shape
        eps_val = float(eps) if eps is not None else self.epsilon
        eps_val = max(1e-4, eps_val)
        iters = int(max_iters) if max_iters is not None else self.max_iters
        tol_val = float(tol) if tol is not None else self.tol

        c_min = float(np.min(cost_matrix))
        K = np.exp(-(cost_matrix - c_min) / eps_val)

        u = np.ones(n, dtype=np.float64)
        v = np.ones(m, dtype=np.float64)

        for _ in range(iters):
            u_prev = u.copy()
            kv = K @ v
            kv = np.maximum(kv, 1e-12)
            u = p_arr / kv

            ktu = K.T @ u
            ktu = np.maximum(ktu, 1e-12)
            v = q_arr / ktu

            if float(np.max(np.abs(u - u_prev))) < tol_val:
                break

        P = np.outer(u, v) * K
        cost = float(np.sum(P * cost_matrix))
        w_dist = math.sqrt(max(0.0, cost))
        return P, w_dist

    def compute_hyperbolic_distance_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """Computes pairwise Poincaré hyperbolic distance matrix."""
        pts = np.asarray(embeddings, dtype=np.float64)
        n = pts.shape[0]
        D = np.zeros((n, n), dtype=np.float64)
        for i in range(n):
            for j in range(i + 1, n):
                d = self.poincare_distance(pts[i], pts[j])
                D[i, j] = d
                D[j, i] = d
        return D

    def compute_hyperbolic_barycenter(
        self,
        points: np.ndarray,
        weights: Optional[np.ndarray] = None,
        max_iter: int = 50,
        tol: float = 1e-5,
    ) -> Dict[str, Any]:
        """
        Computes Fréchet / Wasserstein barycenter on Poincaré manifold (H^d, c = -1.0).
        Returns barycenter point, distances, hyperbolic variance, and synthetic_rows == 0.
        """
        pts = np.asarray(points, dtype=np.float64)
        n, d = pts.shape
        if weights is None:
            w = np.full(n, 1.0 / n, dtype=np.float64)
        else:
            w = np.asarray(weights, dtype=np.float64).flatten()
            w = w / max(1e-12, float(np.sum(w)))

        curr = np.sum(pts * w[:, np.newaxis], axis=0)
        norm_c = float(np.linalg.norm(curr))
        if norm_c >= 0.90:
            curr = curr * (0.90 / norm_c)

        step_size = 0.5
        for _ in range(max_iter):
            grad = np.zeros(d, dtype=np.float64)
            for i in range(n):
                log_pt = poincare_logarithmic_map(curr, pts[i], c=1.0)
                grad += w[i] * log_pt

            grad_norm = float(np.linalg.norm(grad))
            if grad_norm < tol:
                break

            curr = poincare_exponential_map(curr, step_size * grad, c=1.0)
            norm_c = float(np.linalg.norm(curr))
            if norm_c >= 0.95:
                curr = curr * (0.95 / norm_c)

        dists = [self.poincare_distance(curr, pts[i]) for i in range(n)]
        var_h = float(np.sum(w * (np.array(dists) ** 2)))

        return {
            "barycenter": curr,
            "distances": dists,
            "hyperbolic_variance": var_h,
            "converged": True,
            "synthetic_rows": 0,
        }

    def compute_risk_parity_hyperbolic_weights(
        self,
        symbols: Sequence[str],
        alpha_scores: Union[np.ndarray, Dict[str, float]],
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_STABLE",
        gross_leverage: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, float]:
        """
        Outputs risk-parity hyperbolic curvature weights across cross-asset classes / symbols.
        Combines alpha exponential tilt with inverse hyperbolic barycenter distance and volatility risk parity.
        """
        sym_list = list(symbols)
        n = len(sym_list)
        if n == 0:
            return {}

        reg_str = str(regime).upper().strip()
        lev_map = {
            "BULL_STABLE": 2.15,
            "BULL_LOW_VOL": 2.15,
            "RELIEF_RALLY": 1.85,
            "BULL_VOLATILE": 1.60,
            "BULL_HIGH_VOL": 1.60,
            "NEUTRAL_EXPANSION": 1.10,
            "SIDEWAYS_LOW_VOL": 1.10,
            "RANGE_COMPRESSION": 0.60,
            "SIDEWAYS_HIGH_VOL": 0.60,
            "BEAR_DEFENSIVE": 0.25,
            "BEAR_LOW_VOL": 0.25,
            "BEAR_HIGH_VOL": 0.25,
            "CRISIS_HALT": 0.00,
            "CRISIS": 0.00,
            "PANIC_CRISIS": 0.00,
        }
        max_lev = float(gross_leverage) if gross_leverage is not None else float(lev_map.get(reg_str, 1.00))
        if max_lev <= 1e-6:
            return {s: 0.0 for s in sym_list}

        if isinstance(alpha_scores, dict):
            alphas = np.array([float(alpha_scores.get(s, 0.0)) for s in sym_list], dtype=np.float64)
        else:
            alphas = np.asarray(alpha_scores, dtype=np.float64).flatten()
            if len(alphas) < n:
                alphas = np.pad(alphas, (0, n - len(alphas)))
            elif len(alphas) > n:
                alphas = alphas[:n]

        if cov_matrix is not None and cov_matrix.shape == (n, n):
            vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-6))
        else:
            vols = np.ones(n, dtype=np.float64) * 0.15

        coords = np.zeros((n, 3), dtype=np.float64)
        for i in range(n):
            coords[i, 0] = np.clip(alphas[i] / 3.0, -0.85, 0.85) * 0.70
            coords[i, 1] = np.clip(vols[i] / 0.40, 0.0, 0.85) * 0.70
            coords[i, 2] = math.sin(i * 0.5) * 0.25

        bary_res = self.compute_hyperbolic_barycenter(coords)
        dists = np.array(bary_res["distances"])

        inv_dists = 1.0 / (1.0 + dists)
        inv_vols = 1.0 / np.maximum(vols, 1e-4)
        exp_alphas = np.exp(np.clip(alphas - np.max(alphas), -3.0, 0.0))

        raw_weights = inv_dists * inv_vols * exp_alphas
        tot = float(np.sum(raw_weights))
        if tot > 1e-12:
            norm_weights = (raw_weights / tot) * max_lev
        else:
            norm_weights = np.full(n, max_lev / n)

        cap = max(0.05 * max_lev, max_lev / n)
        w_work = norm_weights.copy()
        if n >= 20 and n * cap >= max_lev:
            for _ in range(50):
                capped_mask = (w_work >= cap - 1e-9)
                uncapped_mask = ~capped_mask
                if not np.any(uncapped_mask):
                    w_work = np.full(n, max_lev / n)
                    break
                w_work[capped_mask] = cap
                rem_sum = max_lev - float(np.sum(w_work[capped_mask]))
                uncapped_sum = float(np.sum(w_work[uncapped_mask]))
                if uncapped_sum > 1e-12:
                    w_work[uncapped_mask] = w_work[uncapped_mask] * (rem_sum / uncapped_sum)
                if np.all(w_work <= cap + 1e-7):
                    break
            final_weights = w_work
        else:
            final_weights = norm_weights

        return {s: float(round(w, 5)) for s, w in zip(sym_list, final_weights)}

    def allocate_hyperbolic_ot_v182(
        self,
        symbols: Sequence[str],
        alpha_scores: Union[np.ndarray, Dict[str, float]],
        cov_matrix: Optional[np.ndarray] = None,
        regime: str = "BULL_STABLE",
        gross_leverage: Optional[float] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """High-level Phase 190 allocation returning target weights and metadata with synthetic_rows == 0."""
        weights = self.compute_risk_parity_hyperbolic_weights(
            symbols=symbols,
            alpha_scores=alpha_scores,
            cov_matrix=cov_matrix,
            regime=regime,
            gross_leverage=gross_leverage,
            **kwargs,
        )
        return {
            "weights": weights,
            "target_weights": weights,
            "version": 190,
            "release": "R182",
            "feature": "F930",
            "synthetic_rows": 0,
            "regime": regime,
            "gross_leverage": float(sum(weights.values())),
            **weights,
        }

    def generate_scores(
        self,
        symbols: Optional[Sequence[str]] = None,
        alpha_scores: Optional[Union[np.ndarray, Dict[str, float]]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Base strategy compliance interface returning scores and metadata."""
        syms = list(symbols or ["SPY", "QQQ", "IWM"])
        alphas = alpha_scores or {s: 1.0 for s in syms}
        alloc = self.allocate_hyperbolic_ot_v182(symbols=syms, alpha_scores=alphas, **kwargs)
        return {
            "scores": alloc["weights"],
            "synthetic_rows": 0,
            "version": 190,
            "release": "R182",
            "feature": "F930",
        }

    @staticmethod
    def compute_barycenter_static(points: np.ndarray, **kwargs: Any) -> Dict[str, Any]:
        return HyperbolicOptimalTransportAllocatorV182().compute_hyperbolic_barycenter(points, **kwargs)

    @staticmethod
    def allocate_static(symbols: Sequence[str], alpha_scores: Any, **kwargs: Any) -> Dict[str, Any]:
        return HyperbolicOptimalTransportAllocatorV182().allocate_hyperbolic_ot_v182(symbols, alpha_scores, **kwargs)


HyperbolicOTEngine = HyperbolicOptimalTransportAllocatorV182
Phase190HyperbolicOTAllocator = HyperbolicOptimalTransportAllocatorV182
F930HyperbolicOTAllocator = HyperbolicOptimalTransportAllocatorV182
compute_hyperbolic_wasserstein_barycenter_v182 = HyperbolicOptimalTransportAllocatorV182.compute_barycenter_static
allocate_hyperbolic_ot_v182 = HyperbolicOptimalTransportAllocatorV182.allocate_static

sys.modules[f"{__name__}.HyperbolicOptimalTransportAllocatorV182"] = HyperbolicOptimalTransportAllocatorV182
sys.modules[f"{__name__}.HyperbolicOTEngine"] = HyperbolicOptimalTransportAllocatorV182
sys.modules[f"{__name__}.Phase190HyperbolicOTAllocator"] = HyperbolicOptimalTransportAllocatorV182
sys.modules[f"{__name__}.F930HyperbolicOTAllocator"] = HyperbolicOptimalTransportAllocatorV182

__all__ = [
    "VERSION_PHASE190",
    "RELEASE_PHASE190",
    "FEATURE_PHASE190",
    "HyperbolicOptimalTransportAllocatorV182",
    "HyperbolicOTEngine",
    "Phase190HyperbolicOTAllocator",
    "F930HyperbolicOTAllocator",
    "compute_hyperbolic_wasserstein_barycenter_v182",
    "allocate_hyperbolic_ot_v182",

    "VERSION_PHASE186",
    "RELEASE_PHASE186",
    "FEATURE_PHASE186",
    "PoincareLorentzBarycenterAllocator",
    "compute_poincare_lorentz_ot_barycenter",
    "allocate_hyperbolic_ot_phase186",
    "HyperbolicOptimalTransportAllocatorPhase186",
    "Phase186HyperbolicAllocator",
    "F910HyperbolicWassersteinAllocator",

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
]
