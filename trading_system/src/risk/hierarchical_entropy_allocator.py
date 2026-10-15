"""
Hierarchical Equal Risk Contribution (HERC) with Black-Litterman Entropy Pooling.
Release R126 / Phase 110 Production Master / v117 (Feature F521).

Combines Meucci's Fully Flexible Views (Entropy Pooling) with Hierarchical Tree
Clustering, multi-regime dynamic capital shifting away from high-entropy nodes,
strict simplex and capacity constraints, 12% annual target volatility scaling,
and asymmetric Leland dynamic no-trade buffer bands.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.optimize import minimize
from scipy.spatial.distance import squareform

logger = logging.getLogger(__name__)


@dataclass
class EntropyView:
    """
    Represents an equality or inequality view on scenario distributions.
    Linear view: A_k * p == b_k (equality) or A_k * p <= b_k (inequality).
    """
    view_type: str = "asset_mean"  # 'asset_mean', 'relative_mean', 'cluster_mean', 'volatility', 'ranking', 'custom'
    constraint_type: str = "eq"   # 'eq' or 'ineq' (ineq represents A p <= b)
    coefficients: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=float))  # (S,) or (N,)
    target_value: float = 0.0     # RHS scalar b
    confidence: float = 1.0       # [0.05, 1.0] view confidence weight
    description: str = ""


@dataclass
class EntropyPoolingResult:
    """Result of Meucci's Entropy Pooling optimization."""
    posterior_probabilities: np.ndarray    # p* in Delta^(S-1)
    kl_divergence: float                  # D_KL(p* || p_0)
    prior_probabilities: np.ndarray        # p_0
    posterior_expected_returns: np.ndarray # mu_tilde (N,)
    posterior_covariance: np.ndarray      # Sigma_tilde (N, N)
    posterior_downside_semicov: np.ndarray # Sigma^-_tilde (N, N)
    success: bool
    iterations: int
    message: str


@dataclass
class HERCClusterNode:
    """Cluster representation in the hierarchical dendrogram tree."""
    cluster_id: int
    member_indices: List[int]
    member_symbols: List[str]
    intra_weights: np.ndarray
    cluster_volatility: float
    cluster_entropy: float
    shift_multiplier: float
    allocated_capital: float


@dataclass
class HERCAllocationResult:
    """Comprehensive output of the Hierarchical Entropy Allocator."""
    weights: Dict[str, float]                # Symbol to final weight (sum = 1.000000)
    weights_vector: np.ndarray               # Weight vector (N,)
    symbols: List[str]
    entropy_result: EntropyPoolingResult
    clusters: List[HERCClusterNode]
    portfolio_annual_volatility: float
    target_volatility: float                 # 0.12 (12%)
    volatility_scale_factor: float          # gamma_vol
    cash_buffer_ratio: float
    leland_bands: Dict[str, Tuple[float, float, float]] # sym -> (lower_band, target, upper_band)
    rebalance_actions: Dict[str, Dict[str, Any]]        # sym -> {action, trade_w, is_bypass, band}
    regime: str
    stress_factor: float
    version: int = 110


class HierarchicalEntropyAllocator:
    """
    Multi-Regime Hierarchical Equal Risk Contribution (HERC) with Black-Litterman Entropy Pooling.
    Release R126 / Phase 110 Production Master / v117.
    """
    VERSION: int = 110

    # 2D / Dual Market Regime Stress Index Mappings
    REGIME_STRESS_FACTORS: Dict[str, float] = {
        "BULL_LOW_VOL": 0.00,
        "BULL_HIGH_VOL": 0.20,
        "SIDEWAYS_LOW_VOL": 0.30,
        "SIDEWAYS_HIGH_VOL": 0.50,
        "BEAR_LOW_VOL": 0.70,
        "BEAR_HIGH_VOL": 0.85,
        "CRISIS": 1.00,
    }

    def __init__(
        self,
        target_volatility: float = 0.12,
        max_single_weight: float = 0.20,
        max_sector_weight: float = 0.35,
        linkage_method: str = "ward",
        max_clusters: int = 5,
        risk_measure: str = "volatility",
        stress_shift_intensity: float = 1.5,
        risk_aversion: float = 1.0,
        delta_floor: float = 0.005,
        delta_cap: float = 0.050,
        rebalance_mode: str = "boundary",
        regularization: float = 1e-7,
        version: int = 110,
        **kwargs: Any,
    ) -> None:
        self.target_volatility = float(target_volatility) if (target_volatility is not None and math.isfinite(float(target_volatility)) and float(target_volatility) > 0) else 0.12
        self.max_single_weight = float(max_single_weight) if (max_single_weight is not None and math.isfinite(float(max_single_weight)) and float(max_single_weight) > 0) else 0.20
        self.max_sector_weight = float(max_sector_weight) if (max_sector_weight is not None and math.isfinite(float(max_sector_weight)) and float(max_sector_weight) > 0) else 0.35
        self.linkage_method = str(linkage_method) if linkage_method else "ward"
        self.max_clusters = max(2, int(max_clusters)) if max_clusters is not None else 5
        self.risk_measure = str(risk_measure).lower() if risk_measure else "volatility"
        self.stress_shift_intensity = float(stress_shift_intensity) if stress_shift_intensity is not None else 1.5
        self.risk_aversion = max(0.1, float(risk_aversion)) if risk_aversion is not None else 1.0
        self.delta_floor = max(0.0001, float(delta_floor)) if delta_floor is not None else 0.005
        self.delta_cap = min(0.20, max(self.delta_floor, float(delta_cap))) if delta_cap is not None else 0.050
        self.rebalance_mode = str(rebalance_mode).lower() if rebalance_mode is not None else "boundary"
        self.regularization = max(1e-12, float(regularization)) if regularization is not None else 1e-7
        self.version = int(version) if version is not None else 110

    # -------------------------------------------------------------------------
    # 1. Meucci's Black-Litterman Entropy Pooling Solver
    # -------------------------------------------------------------------------
    def solve_entropy_pooling(
        self,
        returns_matrix: np.ndarray,
        views: Optional[List[EntropyView]] = None,
        prior_probabilities: Optional[np.ndarray] = None,
        use_dual_solver: bool = True,
        regularization: Optional[float] = None,
    ) -> EntropyPoolingResult:
        """
        Solves Meucci's Entropy Pooling (minimum relative entropy / KL divergence):
            min_p  sum_{s=1}^S p_s * ln(p_s / p_{0, s})
            s.t.   A_{eq} p = b_{eq}
                   A_{ineq} p <= b_{ineq}
                   sum p_s = 1.0,  p_s >= 0
        """
        X = np.asarray(returns_matrix, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"returns_matrix must be 2D of shape (S, N), got {X.shape}")

        S, N = X.shape
        if S == 0 or N == 0:
            raise ValueError(f"Empty returns_matrix of shape ({S}, {N})")

        # Setup prior probabilities p_0 (uniform 1/S default)
        if prior_probabilities is not None:
            p0 = np.asarray(prior_probabilities, dtype=float).flatten()
            if len(p0) != S or np.any(p0 <= 0.0):
                p0 = np.full(S, 1.0 / S, dtype=float)
            else:
                p0 = p0 / np.sum(p0)
        else:
            p0 = np.full(S, 1.0 / S, dtype=float)

        eps_reg = regularization if regularization is not None else self.regularization

        # Parse views into equality and inequality matrices
        eq_rows: List[np.ndarray] = []
        eq_rhs: List[float] = []
        ineq_rows: List[np.ndarray] = []
        ineq_rhs: List[float] = []

        if views:
            for v in views:
                if v is None:
                    continue
                coeffs = np.asarray(v.coefficients, dtype=float).flatten()
                # If coefficients are of length N (asset weights): project to scenarios row: (N,) @ X^T = (S,)
                if len(coeffs) == N:
                    row_s = X @ coeffs
                elif len(coeffs) == S:
                    row_s = coeffs
                else:
                    logger.debug(f"[EntropyPooling] Skipping view with invalid coeff len {len(coeffs)} != {N} or {S}")
                    continue

                # Scale with confidence if specified
                conf = min(1.0, max(0.05, float(v.confidence)))
                prior_target = float(row_s @ p0)
                eff_target = conf * float(v.target_value) + (1.0 - conf) * prior_target

                if v.constraint_type == "eq":
                    eq_rows.append(row_s)
                    eq_rhs.append(eff_target)
                elif v.constraint_type == "ineq":
                    ineq_rows.append(row_s)
                    ineq_rhs.append(eff_target)

        num_eq = len(eq_rows)
        num_ineq = len(ineq_rows)

        # Base case: no views provided
        if num_eq == 0 and num_ineq == 0:
            p_star = p0.copy()
            kl_div = 0.0
            mu_tilde = X.T @ p_star
            dev = X - mu_tilde
            sigma_tilde = (dev.T * p_star) @ dev + 1e-8 * np.eye(N)
            dev_neg = np.minimum(dev, 0.0)
            semi_tilde = (dev_neg.T * p_star) @ dev_neg + 1e-8 * np.eye(N)
            return EntropyPoolingResult(
                posterior_probabilities=p_star,
                kl_divergence=kl_div,
                prior_probabilities=p0,
                posterior_expected_returns=mu_tilde,
                posterior_covariance=sigma_tilde,
                posterior_downside_semicov=semi_tilde,
                success=True,
                iterations=0,
                message="Zero views; uniform prior preserved.",
            )

        A_eq = np.array(eq_rows, dtype=float) if num_eq > 0 else np.zeros((0, S), dtype=float)
        b_eq = np.array(eq_rhs, dtype=float) if num_eq > 0 else np.zeros(0, dtype=float)
        A_ineq = np.array(ineq_rows, dtype=float) if num_ineq > 0 else np.zeros((0, S), dtype=float)
        b_ineq = np.array(ineq_rhs, dtype=float) if num_ineq > 0 else np.zeros(0, dtype=float)

        opt_success = False
        opt_message = ""
        n_iters = 0
        p_star = p0.copy()

        # ---------------------------------------------------------------------
        # Dual Convex Optimization Solver (L-BFGS-B)
        # ---------------------------------------------------------------------
        if use_dual_solver:
            def dual_objective(theta: np.ndarray) -> Tuple[float, np.ndarray]:
                lam = theta[:num_eq] if num_eq > 0 else np.zeros(0, dtype=float)
                nu = theta[num_eq:] if num_ineq > 0 else np.zeros(0, dtype=float)

                z = np.zeros(S, dtype=float)
                if num_eq > 0:
                    z -= A_eq.T @ lam
                if num_ineq > 0:
                    z -= A_ineq.T @ nu

                # Log-sum-exp stabilization trick
                z_max = np.max(z)
                w = p0 * np.exp(z - z_max)
                sum_w = np.sum(w)
                if sum_w <= 0.0 or not np.isfinite(sum_w):
                    return 1e12, np.zeros_like(theta)

                p = w / sum_w
                obj = (z_max + math.log(sum_w))
                if num_eq > 0:
                    obj += float(lam @ b_eq)
                if num_ineq > 0:
                    obj += float(nu @ b_ineq)
                obj += 0.5 * eps_reg * float(np.sum(theta ** 2))

                # Gradient
                grad = np.zeros_like(theta)
                if num_eq > 0:
                    grad[:num_eq] = b_eq - A_eq @ p + eps_reg * lam
                if num_ineq > 0:
                    grad[num_eq:] = b_ineq - A_ineq @ p + eps_reg * nu

                return float(obj), grad

            theta0 = np.zeros(num_eq + num_ineq, dtype=float)
            bounds = [(None, None)] * num_eq + [(0.0, None)] * num_ineq

            try:
                res = minimize(
                    dual_objective,
                    theta0,
                    jac=True,
                    method="L-BFGS-B",
                    bounds=bounds,
                    options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-8},
                )
                if res.success or res.fun < 1e10:
                    lam = res.x[:num_eq] if num_eq > 0 else np.zeros(0, dtype=float)
                    nu = res.x[num_eq:] if num_ineq > 0 else np.zeros(0, dtype=float)
                    z = np.zeros(S, dtype=float)
                    if num_eq > 0:
                        z -= A_eq.T @ lam
                    if num_ineq > 0:
                        z -= A_ineq.T @ nu
                    z_max = np.max(z)
                    w = p0 * np.exp(z - z_max)
                    w_sum = np.sum(w)
                    if w_sum > 0.0 and np.isfinite(w_sum):
                        p_star = w / w_sum
                        opt_success = True
                        opt_message = res.message
                        n_iters = res.nit
            except Exception as e_dual:
                logger.debug(f"[EntropyPooling Dual] Failed: {e_dual}, falling back to Primal SLSQP")

        # ---------------------------------------------------------------------
        # Fallback: Primal SLSQP Convex Optimization Solver
        # ---------------------------------------------------------------------
        if not opt_success:
            def primal_objective(p: np.ndarray) -> float:
                p_safe = np.maximum(p, 1e-16)
                return float(np.sum(p_safe * np.log(p_safe / p0)))

            def primal_gradient(p: np.ndarray) -> np.ndarray:
                p_safe = np.maximum(p, 1e-16)
                return np.log(p_safe / p0) + 1.0

            constraints: List[Dict[str, Any]] = [
                {"type": "eq", "fun": lambda p: np.sum(p) - 1.0, "jac": lambda p: np.ones(S)}
            ]
            if num_eq > 0:
                constraints.append({
                    "type": "eq",
                    "fun": lambda p: A_eq @ p - b_eq,
                    "jac": lambda p: A_eq,
                })
            if num_ineq > 0:
                constraints.append({
                    "type": "ineq",
                    "fun": lambda p: b_ineq - A_ineq @ p,
                    "jac": lambda p: -A_ineq,
                })

            bounds_p = [(1e-12, 1.0)] * S
            try:
                res_primal = minimize(
                    primal_objective,
                    p0.copy(),
                    jac=primal_gradient,
                    method="SLSQP",
                    bounds=bounds_p,
                    constraints=constraints,
                    options={"maxiter": 1000, "ftol": 1e-9},
                )
                p_star = np.maximum(res_primal.x, 0.0)
                sum_p = np.sum(p_star)
                if sum_p > 0.0:
                    p_star /= sum_p
                opt_success = res_primal.success
                opt_message = f"Primal SLSQP: {res_primal.message}"
                n_iters = res_primal.nit
            except Exception as e_primal:
                logger.warning(f"[EntropyPooling Primal] Failed: {e_primal}; using bounded prior projection")
                p_star = p0.copy()
                opt_success = False
                opt_message = f"Solver failure: {e_primal}"

        # Clean, project to strict simplex
        p_star = np.maximum(p_star, 1e-16)
        p_star /= np.sum(p_star)

        # Compute Kullback-Leibler divergence D_KL(p* || p_0)
        kl_div = float(np.sum(p_star * np.log(p_star / p0)))

        # Posterior moments
        mu_tilde = X.T @ p_star
        dev = X - mu_tilde
        sigma_tilde = (dev.T * p_star) @ dev + 1e-8 * np.eye(N)
        dev_neg = np.minimum(dev, 0.0)
        semi_tilde = (dev_neg.T * p_star) @ dev_neg + 1e-8 * np.eye(N)

        return EntropyPoolingResult(
            posterior_probabilities=p_star,
            kl_divergence=max(0.0, kl_div),
            prior_probabilities=p0,
            posterior_expected_returns=mu_tilde,
            posterior_covariance=sigma_tilde,
            posterior_downside_semicov=semi_tilde,
            success=opt_success,
            iterations=n_iters,
            message=opt_message,
        )

    # -------------------------------------------------------------------------
    # 2. View Construction from Strategy Predictions
    # -------------------------------------------------------------------------
    def build_views_from_predictions(
        self,
        predicted_returns: Union[np.ndarray, pd.Series, Dict[str, float]],
        symbols: List[str],
        view_confidence: float = 0.75,
        ranking_spread_threshold: float = 0.02,
        max_views: int = 10,
    ) -> List[EntropyView]:
        """
        Builds Meucci EntropyView objects from multi-factor strategy predicted returns:
        1. Asset expected return equality views (shrunk by view_confidence).
        2. Pairwise ranking inequality views between top-ranked and bottom-ranked assets.
        """
        N = len(symbols)
        if N == 0:
            return []

        # Parse predicted_returns into (N,) array
        if isinstance(predicted_returns, dict):
            p_arr = np.array([float(predicted_returns.get(s, 0.0)) for s in symbols], dtype=float)
        elif isinstance(predicted_returns, pd.Series):
            p_arr = np.array([float(predicted_returns.get(s, 0.0)) for s in symbols], dtype=float)
        else:
            p_arr = np.asarray(predicted_returns, dtype=float).flatten()
            if len(p_arr) < N:
                p_pad = np.zeros(N, dtype=float)
                p_pad[:len(p_arr)] = p_arr
                p_arr = p_pad
            elif len(p_arr) > N:
                p_arr = p_arr[:N]

        views: List[EntropyView] = []

        # 1. Individual Asset Expected Return Views
        finite_mask = np.isfinite(p_arr)
        if np.any(finite_mask):
            sorted_indices = np.argsort(p_arr)
            # Pick top and bottom conviction candidates
            n_select = min(max_views // 2, N // 2) if N >= 4 else min(max_views, N)
            selected_idx = list(sorted_indices[-n_select:]) + list(sorted_indices[:n_select])
            selected_idx = list(dict.fromkeys(selected_idx))

            for idx in selected_idx:
                if not finite_mask[idx]:
                    continue
                c_vec = np.zeros(N, dtype=float)
                c_vec[idx] = 1.0
                views.append(
                    EntropyView(
                        view_type="asset_mean",
                        constraint_type="eq",
                        coefficients=c_vec,
                        target_value=float(p_arr[idx]),
                        confidence=view_confidence,
                        description=f"Expected return view on {symbols[idx]} = {p_arr[idx]:.4f}",
                    )
                )

            # 2. Pairwise Ranking Inequality Views: E[X_top - X_bot] >= spread
            # Expressed as: E[X_bot - X_top] <= -spread
            if len(sorted_indices) >= 2:
                top_idx = sorted_indices[-1]
                bot_idx = sorted_indices[0]
                spread = float(p_arr[top_idx] - p_arr[bot_idx])
                if spread >= ranking_spread_threshold:
                    c_pair = np.zeros(N, dtype=float)
                    c_pair[bot_idx] = 1.0
                    c_pair[top_idx] = -1.0
                    views.append(
                        EntropyView(
                            view_type="ranking",
                            constraint_type="ineq",
                            coefficients=c_pair,
                            target_value=-ranking_spread_threshold,
                            confidence=view_confidence,
                            description=f"Ranking view: {symbols[top_idx]} >= {symbols[bot_idx]} + {ranking_spread_threshold:.4f}",
                        )
                    )

        return views

    # -------------------------------------------------------------------------
    # 3. HERC Dendrogram Tree Clustering
    # -------------------------------------------------------------------------
    def cluster_hierarchical_tree(
        self,
        posterior_covariance: np.ndarray,
        symbols: List[str],
        max_k: Optional[int] = None,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Builds correlation distance matrix D_{i, j} = sqrt(max(0, 0.5 * (1 - rho_{i, j})))
        and applies Ward hierarchical tree linkage clustering.
        Returns:
            Tuple of (cluster_labels (N,), linkage_matrix)
        """
        cov = np.asarray(posterior_covariance, dtype=float)
        N = cov.shape[0]
        if N <= 1:
            return np.ones(N, dtype=int), None

        # Clean diagonal and compute correlation
        stds = np.sqrt(np.maximum(np.diag(cov), 1e-12))
        outer_stds = np.outer(stds, stds)
        corr = cov / np.maximum(outer_stds, 1e-12)
        corr = np.clip(corr, -1.0, 1.0)
        np.fill_diagonal(corr, 1.0)

        # Distance matrix D_{i, j}
        dist = np.sqrt(np.maximum(0.0, 0.5 * (1.0 - corr)))
        np.fill_diagonal(dist, 0.0)

        # Convert to condensed upper triangular distance vector
        dist_condensed = squareform(dist, checks=False)

        # Hierarchical Linkage with fallback
        try:
            link = linkage(dist_condensed, method=self.linkage_method)
        except Exception as e_link:
            logger.debug(f"[HERC Linkage] {self.linkage_method} failed: {e_link}, fallback to average")
            link = linkage(dist_condensed, method="average")

        # Determine macro cluster count K
        k_bound = max_k if max_k is not None else self.max_clusters
        k = min(N, max(2, min(k_bound, max(2, N // 2))))
        cluster_labels = fcluster(link, t=k, criterion="maxclust")

        return cluster_labels, link

    # -------------------------------------------------------------------------
    # 4. Multi-Regime Dynamic Capital Shift Away from High-Entropy Nodes
    # -------------------------------------------------------------------------
    def compute_cluster_entropies(
        self,
        cluster_labels: np.ndarray,
        intra_weights: Dict[int, np.ndarray],
        uncertainty_scores: Optional[np.ndarray] = None,
        cluster_vols: Optional[Dict[int, float]] = None,
    ) -> Dict[int, float]:
        """
        Computes composite information and predictive uncertainty entropy for each cluster:
            H_k = 0.5 * H_k^{norm_weight} + 0.5 * H_k^{uncertainty}
        """
        unique_clusters = np.unique(cluster_labels)
        cluster_entropies: Dict[int, float] = {}

        for cid in unique_clusters:
            cid_int = int(cid)
            members = np.where(cluster_labels == cid)[0]
            n_m = len(members)
            w_intra = intra_weights.get(cid_int, np.full(n_m, 1.0 / max(1, n_m)))

            # Normalized weight dispersion Shannon entropy
            if n_m > 1:
                w_safe = np.maximum(w_intra, 1e-15)
                h_weight = -float(np.sum(w_safe * np.log(w_safe))) / math.log(n_m)
            else:
                h_weight = 0.5

            # Predictive uncertainty / volatility dispersion entropy
            if uncertainty_scores is not None and len(uncertainty_scores) >= len(cluster_labels):
                u_m = np.asarray(uncertainty_scores)[members]
                u_clean = u_m[np.isfinite(u_m)]
                h_pred = float(np.mean(u_clean)) if len(u_clean) > 0 else 0.5
            elif cluster_vols and cid_int in cluster_vols:
                h_pred = min(1.0, max(0.0, cluster_vols[cid_int] / 0.30))
            else:
                h_pred = 0.5

            cluster_entropies[cid_int] = float(np.clip(0.5 * h_weight + 0.5 * h_pred, 0.0, 1.0))

        return cluster_entropies

    def shift_cluster_capital_under_stress(
        self,
        cluster_risks: Dict[int, float],
        cluster_entropies: Dict[int, float],
        regime: str = "SIDEWAYS_LOW_VOL",
        stress_intensity: Optional[float] = None,
    ) -> Dict[int, float]:
        """
        Applies exponential stress shift multiplier:
            M_k = exp(-kappa_{stress} * S_{regime} * z_{H, k})
        during stress/crisis regimes (S_{regime} > 0.25) to dynamically reallocate
        capital away from high-entropy cluster nodes.
        When S_{regime} <= 0.25 (tranquil bull), preserves pure Equal Risk Contribution (M_k = 1.0).
        """
        stress_factor = self.REGIME_STRESS_FACTORS.get(regime.upper(), 0.30)
        cids = sorted(cluster_risks.keys())
        k_count = len(cids)
        if k_count == 0:
            return {}

        kappa = stress_intensity if stress_intensity is not None else self.stress_shift_intensity

        # Compute standardized cluster entropy z_{H, k}
        h_vals = np.array([cluster_entropies.get(cid, 0.5) for cid in cids], dtype=float)
        h_mean = float(np.mean(h_vals))
        h_std = float(np.std(h_vals))

        if h_std > 1e-6:
            z_h = (h_vals - h_mean) / h_std
        else:
            z_h = np.zeros(k_count, dtype=float)

        shift_multipliers: Dict[int, float] = {}
        weighted_inv_risks: Dict[int, float] = {}

        for i, cid in enumerate(cids):
            sigma_k = max(1e-6, cluster_risks[cid])
            inv_risk = 1.0 / sigma_k

            if stress_factor > 0.25:
                # Exponential de-weighting of high-entropy clusters
                m_k = math.exp(-kappa * stress_factor * z_h[i])
                m_k = max(0.10, min(10.0, m_k))
            else:
                m_k = 1.0

            shift_multipliers[cid] = m_k
            weighted_inv_risks[cid] = inv_risk * m_k

        total_alloc = sum(weighted_inv_risks.values())
        cluster_capital: Dict[int, float] = {}
        for cid in cids:
            cluster_capital[cid] = weighted_inv_risks[cid] / total_alloc if total_alloc > 0 else 1.0 / k_count

        return cluster_capital

    # -------------------------------------------------------------------------
    # 5. Strict Simplex & Capacity Constraints (Single Stock & Sector Caps)
    # -------------------------------------------------------------------------
    def apply_capacity_constraints(
        self,
        raw_weights: np.ndarray,
        symbols: List[str],
        sectors: Optional[List[str]] = None,
        max_single_weight: Optional[float] = None,
        max_sector_weight: Optional[float] = None,
        max_iter: int = 100,
    ) -> np.ndarray:
        """
        Enforces:
            1. Strict non-negativity: w_i >= 0
            2. Single-stock cap: w_i <= max_single_weight (default 0.20)
            3. Sector cap: sum_{i in Sector} w_i <= max_sector_weight (default 0.35)
            4. Strict simplex equality: sum w_i = 1.000000
        Iterative excess redistribution ensures exact convergence.
        """
        w = np.asarray(raw_weights, dtype=float).copy()
        N = len(w)
        if N <= 1:
            return np.ones(N, dtype=float)

        cap_single = max_single_weight if max_single_weight is not None else self.max_single_weight
        cap_sector = max_sector_weight if max_sector_weight is not None else self.max_sector_weight

        # Adjust single stock cap when N * cap_single <= 1.0 to guarantee feasibility
        if N * cap_single > 1.0:
            eff_cap_single = cap_single
        else:
            eff_cap_single = min(0.85, max(cap_single, 1.0 / max(N - 1, 1))) if N > 1 else 1.0

        # Ensure non-negativity and initial simplex
        w = np.maximum(w, 0.0)
        total = np.sum(w)
        if total > 0:
            w /= total
        else:
            w = np.full(N, 1.0 / N)

        # Build sector membership mappings
        sector_map: Dict[str, List[int]] = {}
        if sectors and len(sectors) == N:
            for i, sec in enumerate(sectors):
                s_name = str(sec) if sec is not None else "UNKNOWN"
                sector_map.setdefault(s_name, []).append(i)

        for _ in range(max_iter):
            prev_w = w.copy()

            # 1. Single stock cap projection
            w = np.minimum(w, eff_cap_single)

            # 2. Sector cap projection
            if sector_map:
                for s_name, indices in sector_map.items():
                    sec_sum = float(np.sum(w[indices]))
                    if sec_sum > cap_sector and sec_sum > 0:
                        w[indices] *= (cap_sector / sec_sum)

            # 3. Simplex re-normalization on unpinned assets
            current_sum = float(np.sum(w))
            deficit = 1.0 - current_sum

            if abs(deficit) < 1e-9:
                break

            free_mask = (w < (eff_cap_single - 1e-6)) & (w > 0.0)
            if np.any(free_mask):
                free_sum = float(np.sum(w[free_mask]))
                if free_sum > 0:
                    w[free_mask] += deficit * (w[free_mask] / free_sum)
                    w = np.maximum(w, 0.0)
                else:
                    w /= np.sum(w)
            else:
                # If all free assets pinned, scale proportionally
                w = np.maximum(w, 0.0)
                w /= np.sum(w)

            if np.max(np.abs(w - prev_w)) < 1e-8:
                break

        # Final guarantee of strict non-negativity and exact simplex sum = 1.000000
        w = np.maximum(w, 0.0)
        w /= np.sum(w)
        return w

    # -------------------------------------------------------------------------
    # 6. Target Volatility Scaling (12% Target Volatility)
    # -------------------------------------------------------------------------
    def scale_target_volatility(
        self,
        weights: np.ndarray,
        covariance: np.ndarray,
        target_annual_vol: Optional[float] = None,
        regime: str = "SIDEWAYS_LOW_VOL",
    ) -> Tuple[float, float, float]:
        """
        Calculates annualized portfolio volatility and volatility scale factor:
            sigma_ann = sqrt(252 * w^T Sigma w)
            gamma_vol = sigma_{target} / sigma_ann
        In stress regimes, allocates cash buffer ratio = max(0, 1 - gamma_vol) when sigma_ann > 0.12.
        In tranquil bull markets, bull market cash drag eliminator keeps cash_ratio = 0.0.
        Returns:
            Tuple of (portfolio_annual_volatility, volatility_scale_factor, cash_buffer_ratio)
        """
        w = np.asarray(weights, dtype=float).flatten()
        cov = np.asarray(covariance, dtype=float)
        port_var = float(w @ cov @ w)
        port_ann_vol = math.sqrt(max(1e-8, 252.0 * port_var))

        target_vol = target_annual_vol if target_annual_vol is not None else self.target_volatility
        gamma_vol = target_vol / max(0.01, port_ann_vol)

        stress_factor = self.REGIME_STRESS_FACTORS.get(regime.upper(), 0.30)
        if stress_factor >= 0.50 and port_ann_vol > target_vol:
            cash_buffer_ratio = max(0.0, 1.0 - gamma_vol)
        else:
            # Bull market cash drag eliminator
            cash_buffer_ratio = 0.0

        return port_ann_vol, gamma_vol, cash_buffer_ratio

    # -------------------------------------------------------------------------
    # 7. Asymmetric Leland Dynamic No-Trade Buffer Bands
    # -------------------------------------------------------------------------
    def evaluate_leland_no_trade_bands(
        self,
        target_weights: Dict[str, float],
        current_weights: Optional[Dict[str, float]] = None,
        volatilities: Optional[Dict[str, float]] = None,
        cost_rates: Optional[Dict[str, float]] = None,
        unrealized_returns: Optional[Dict[str, float]] = None,
    ) -> Tuple[Dict[str, Tuple[float, float, float]], Dict[str, Dict[str, Any]]]:
        """
        Computes dynamic asymmetric Leland buffer bands:
            delta_i = [ (3 * c_i * w_i * (1 - w_i) * sigma_{ann, i}^2) / (4 * gamma) ]^(1/3)
        Asymmetric modulation:
            - Winner (z > 0): expands upper band (up to 1.8x) to let winners run.
            - Laggard (z < 0): tightens lower band (down to 0.6x) for swift de-risking.
        Immediate bypass:
            - New entry (w_{cur} == 0) or full liquidation (w_{target} == 0) bypasses buffer.
        Returns:
            Tuple of:
            - leland_bands: sym -> (lower_band, target_weight, upper_band)
            - rebalance_actions: sym -> {action: 'BUY'|'SELL'|'HOLD', trade_w, is_bypass, band}
        """
        bands: Dict[str, Tuple[float, float, float]] = {}
        actions: Dict[str, Dict[str, Any]] = {}

        all_syms = set(target_weights.keys())
        if current_weights:
            all_syms.update(current_weights.keys())

        for sym in sorted(all_syms):
            w_tgt = float(target_weights.get(sym, 0.0))
            w_cur = float(current_weights.get(sym, 0.0)) if current_weights else 0.0
            sigma_ann = float(volatilities.get(sym, 0.25)) if volatilities else 0.25
            c_rate = float(cost_rates.get(sym, 0.0020)) if cost_rates else 0.0020

            # Base Leland buffer half-width
            base_delta = (
                (3.0 * c_rate * max(1e-4, w_tgt) * max(1e-4, 1.0 - w_tgt) * (sigma_ann ** 2))
                / (4.0 * self.risk_aversion)
            ) ** (1.0 / 3.0)
            base_delta = max(self.delta_floor, min(self.delta_cap, base_delta))

            # Asymmetric multiplier from unrealized return
            u_ret = float(unrealized_returns.get(sym, 0.0)) if unrealized_returns else 0.0
            vol_5d = max(0.005, sigma_ann / math.sqrt(252.0)) * math.sqrt(5.0)
            z_unrealized = u_ret / vol_5d if vol_5d > 0 else 0.0

            if z_unrealized > 0.0:
                z_clamped = min(max((z_unrealized - 1.0) / 2.0, 0.0), 1.0)
                upper_mult = 1.0 + 0.8 * z_clamped
                lower_mult = 1.0
            elif z_unrealized < 0.0:
                z_clamped = min(max((-1.0 - z_unrealized) / 2.0, 0.0), 1.0)
                upper_mult = 1.0
                lower_mult = 1.0 - 0.4 * z_clamped
            else:
                upper_mult = 1.0
                lower_mult = 1.0

            delta_lower = base_delta * lower_mult
            delta_upper = base_delta * upper_mult
            band_lower = max(0.0, w_tgt - delta_lower)
            band_upper = min(1.0, w_tgt + delta_upper)
            bands[sym] = (band_lower, w_tgt, band_upper)

            # Immediate Bypass for new positions or full liquidations
            is_bypass = False
            if w_cur == 0.0 or w_tgt == 0.0:
                is_bypass = True
                diff = w_tgt - w_cur
                action = "BUY" if diff > 0 else ("SELL" if diff < 0 else "HOLD")
                trade_w = diff
            elif w_cur < band_lower:
                action = "BUY"
                trade_w = (band_lower - w_cur) if self.rebalance_mode == "boundary" else (w_tgt - w_cur)
            elif w_cur > band_upper:
                action = "SELL"
                trade_w = (band_upper - w_cur) if self.rebalance_mode == "boundary" else (w_tgt - w_cur)
            else:
                action = "HOLD"
                trade_w = 0.0

            actions[sym] = {
                "action": action,
                "trade_weight": float(trade_w),
                "is_bypass": is_bypass,
                "band_lower": band_lower,
                "target": w_tgt,
                "band_upper": band_upper,
                "current_weight": w_cur,
            }

        return bands, actions

    # -------------------------------------------------------------------------
    # 8. Master Allocation Orchestrator
    # -------------------------------------------------------------------------
    def allocate(
        self,
        returns_data: Union[pd.DataFrame, np.ndarray],
        cov_matrix: Optional[np.ndarray] = None,
        predicted_returns: Optional[Union[np.ndarray, pd.Series, Dict[str, float]]] = None,
        symbols: Optional[List[str]] = None,
        sectors: Optional[List[str]] = None,
        regime: Optional[str] = "SIDEWAYS_LOW_VOL",
        current_weights: Optional[Dict[str, float]] = None,
        uncertainty_scores: Optional[np.ndarray] = None,
        custom_views: Optional[List[EntropyView]] = None,
        cost_rates: Optional[Dict[str, float]] = None,
        unrealized_returns: Optional[Dict[str, float]] = None,
        **kwargs: Any,
    ) -> HERCAllocationResult:
        """
        Executes the full Multi-Regime Entropy-Pooled HERC Allocation pipeline:
        1. Parse and validate scenario return matrix / covariance.
        2. Solve Meucci's Black-Litterman Entropy Pooling for posterior moments.
        3. Cluster dendrogram tree using Ward linkage on correlation distance.
        4. Reallocate capital away from high-entropy cluster nodes under stress.
        5. Apply strict simplex sum = 1.000000, non-negativity, and capacity caps.
        6. Scale to 12% annual target volatility with bull cash drag elimination.
        7. Evaluate asymmetric Leland dynamic no-trade buffer bands.
        """
        active_regime = regime if regime else "SIDEWAYS_LOW_VOL"

        # 1. Parse returns_data and symbols
        if isinstance(returns_data, pd.DataFrame):
            inferred_symbols = list(returns_data.columns)
            X = returns_data.values.astype(float)
        else:
            X = np.asarray(returns_data, dtype=float)
            inferred_symbols = [f"A_{i}" for i in range(X.shape[1] if X.ndim == 2 else len(X))]

        sym_list = symbols if symbols is not None else inferred_symbols
        N = len(sym_list)

        # Edge case: N == 0
        if N == 0:
            empty_res = EntropyPoolingResult(
                posterior_probabilities=np.zeros(0),
                kl_divergence=0.0,
                prior_probabilities=np.zeros(0),
                posterior_expected_returns=np.zeros(0),
                posterior_covariance=np.zeros((0, 0)),
                posterior_downside_semicov=np.zeros((0, 0)),
                success=True,
                iterations=0,
                message="Empty asset universe",
            )
            return HERCAllocationResult(
                weights={},
                weights_vector=np.zeros(0),
                symbols=[],
                entropy_result=empty_res,
                clusters=[],
                portfolio_annual_volatility=0.0,
                target_volatility=self.target_volatility,
                volatility_scale_factor=1.0,
                cash_buffer_ratio=0.0,
                leland_bands={},
                rebalance_actions={},
                regime=active_regime,
                stress_factor=self.REGIME_STRESS_FACTORS.get(active_regime.upper(), 0.30),
                version=self.version,
            )

        # Edge case: N == 1
        if N == 1:
            single_sym = sym_list[0]
            w_dict = {single_sym: 1.0}
            w_vec = np.array([1.0], dtype=float)
            sigma_val = float(cov_matrix[0, 0]) if (cov_matrix is not None and cov_matrix.shape == (1, 1)) else 0.04
            single_cov = np.array([[sigma_val]], dtype=float)
            single_res = EntropyPoolingResult(
                posterior_probabilities=np.array([1.0]),
                kl_divergence=0.0,
                prior_probabilities=np.array([1.0]),
                posterior_expected_returns=np.zeros(1),
                posterior_covariance=single_cov,
                posterior_downside_semicov=single_cov,
                success=True,
                iterations=0,
                message="Single asset universe",
            )
            cluster_node = HERCClusterNode(
                cluster_id=1,
                member_indices=[0],
                member_symbols=[single_sym],
                intra_weights=np.array([1.0]),
                cluster_volatility=math.sqrt(max(1e-8, sigma_val)),
                cluster_entropy=0.5,
                shift_multiplier=1.0,
                allocated_capital=1.0,
            )
            p_vol, g_vol, c_ratio = self.scale_target_volatility(w_vec, single_cov, regime=active_regime)
            bands, acts = self.evaluate_leland_no_trade_bands(w_dict, current_weights, {single_sym: p_vol})
            return HERCAllocationResult(
                weights=w_dict,
                weights_vector=w_vec,
                symbols=sym_list,
                entropy_result=single_res,
                clusters=[cluster_node],
                portfolio_annual_volatility=p_vol,
                target_volatility=self.target_volatility,
                volatility_scale_factor=g_vol,
                cash_buffer_ratio=c_ratio,
                leland_bands=bands,
                rebalance_actions=acts,
                regime=active_regime,
                stress_factor=self.REGIME_STRESS_FACTORS.get(active_regime.upper(), 0.30),
                version=self.version,
            )

        # Check if X is square covariance or rectangular scenario returns
        if X.ndim == 2 and X.shape[0] == X.shape[1] == N and cov_matrix is None:
            # X is covariance matrix: generate synthetic scenarios via Cholesky decomposition
            cov_base = X
            S_sim = 252
            rng = np.random.RandomState(42)
            try:
                L = np.linalg.cholesky(cov_base + 1e-6 * np.eye(N))
                Z = rng.randn(S_sim, N)
                X_scenarios = Z @ L.T
            except Exception:
                eigenvals, eigenvecs = np.linalg.eigh(cov_base + 1e-6 * np.eye(N))
                eigenvals = np.maximum(eigenvals, 1e-6)
                L = eigenvecs @ np.diag(np.sqrt(eigenvals))
                Z = rng.randn(S_sim, N)
                X_scenarios = Z @ L.T
        elif X.ndim == 2 and X.shape[1] == N and X.shape[0] >= 5:
            X_scenarios = X
        else:
            # Fallback scenario generation
            S_sim = 252
            rng = np.random.RandomState(42)
            cov_base = cov_matrix if cov_matrix is not None else np.eye(N) * 0.04
            eigenvals, eigenvecs = np.linalg.eigh(cov_base + 1e-6 * np.eye(N))
            eigenvals = np.maximum(eigenvals, 1e-6)
            L = eigenvecs @ np.diag(np.sqrt(eigenvals))
            Z = rng.randn(S_sim, N)
            X_scenarios = Z @ L.T

        # 2. Build views from strategy predictions
        all_views: List[EntropyView] = []
        if custom_views:
            all_views.extend(custom_views)
        if predicted_returns is not None:
            pred_views = self.build_views_from_predictions(predicted_returns, sym_list)
            all_views.extend(pred_views)

        # 3. Solve Meucci Entropy Pooling
        entropy_res = self.solve_entropy_pooling(returns_matrix=X_scenarios, views=all_views)
        post_cov = entropy_res.posterior_covariance

        # If external cov_matrix was provided, blend or shrink with posterior covariance
        if cov_matrix is not None and cov_matrix.shape == (N, N):
            eff_cov = 0.5 * post_cov + 0.5 * cov_matrix
        else:
            eff_cov = post_cov

        # 4. Dendrogram Tree Clustering
        cluster_labels, link_matrix = self.cluster_hierarchical_tree(eff_cov, sym_list)

        # 5. Intra-Cluster Weighting & Cluster Risks
        unique_cids = sorted(np.unique(cluster_labels))
        intra_weights_dict: Dict[int, np.ndarray] = {}
        cluster_risks_dict: Dict[int, float] = {}
        cluster_vols_dict: Dict[int, float] = {}

        for cid in unique_cids:
            members = np.where(cluster_labels == cid)[0]
            n_m = len(members)
            sub_cov = eff_cov[np.ix_(members, members)]

            # Inverse variance within cluster
            diag_vars = np.maximum(np.diag(sub_cov), 1e-12)
            inv_vars = 1.0 / diag_vars
            w_intra = inv_vars / np.sum(inv_vars)
            intra_weights_dict[cid] = w_intra

            # Cluster risk
            c_var = float(w_intra @ sub_cov @ w_intra)
            c_vol = math.sqrt(max(1e-12, c_var))
            cluster_risks_dict[cid] = c_vol
            cluster_vols_dict[cid] = c_vol * math.sqrt(252.0)

        # 6. Cluster Entropies & Multi-Regime Stress Shift
        cluster_entropies = self.compute_cluster_entropies(
            cluster_labels=cluster_labels,
            intra_weights=intra_weights_dict,
            uncertainty_scores=uncertainty_scores,
            cluster_vols=cluster_vols_dict,
        )

        cluster_capital = self.shift_cluster_capital_under_stress(
            cluster_risks=cluster_risks_dict,
            cluster_entropies=cluster_entropies,
            regime=active_regime,
        )

        # 7. Unconstrained Raw Weights
        raw_w = np.zeros(N, dtype=float)
        cluster_nodes: List[HERCClusterNode] = []
        for cid in unique_cids:
            members = np.where(cluster_labels == cid)[0]
            cap = cluster_capital.get(cid, 0.0)
            w_intra = intra_weights_dict[cid]
            raw_w[members] = cap * w_intra

            cluster_nodes.append(
                HERCClusterNode(
                    cluster_id=int(cid),
                    member_indices=list(members),
                    member_symbols=[sym_list[m] for m in members],
                    intra_weights=w_intra,
                    cluster_volatility=cluster_vols_dict[cid],
                    cluster_entropy=cluster_entropies[cid],
                    shift_multiplier=cap / max(1e-6, (1.0 / cluster_risks_dict[cid]) / sum(1.0 / cluster_risks_dict[c] for c in unique_cids)),
                    allocated_capital=cap,
                )
            )

        # 8. Capacity Constraints (Simplex, Single-Stock Cap, Sector Cap)
        constrained_w = self.apply_capacity_constraints(
            raw_weights=raw_w,
            symbols=sym_list,
            sectors=sectors,
            max_single_weight=self.max_single_weight,
            max_sector_weight=self.max_sector_weight,
        )

        # 9. Target Volatility Scaling (12% Target Volatility)
        port_ann_vol, gamma_vol, cash_ratio = self.scale_target_volatility(
            weights=constrained_w,
            covariance=eff_cov,
            regime=active_regime,
        )

        weights_dict = {sym_list[i]: float(constrained_w[i]) for i in range(N)}

        # Individual asset annual volatilities for Leland bands
        asset_ann_vols = {
            sym_list[i]: math.sqrt(max(1e-8, 252.0 * float(eff_cov[i, i]))) for i in range(N)
        }

        # 10. Asymmetric Leland Dynamic No-Trade Buffer Bands
        leland_bands, rebalance_actions = self.evaluate_leland_no_trade_bands(
            target_weights=weights_dict,
            current_weights=current_weights,
            volatilities=asset_ann_vols,
            cost_rates=cost_rates,
            unrealized_returns=unrealized_returns,
        )

        return HERCAllocationResult(
            weights=weights_dict,
            weights_vector=constrained_w,
            symbols=sym_list,
            entropy_result=entropy_res,
            clusters=cluster_nodes,
            portfolio_annual_volatility=port_ann_vol,
            target_volatility=self.target_volatility,
            volatility_scale_factor=gamma_vol,
            cash_buffer_ratio=cash_ratio,
            leland_bands=leland_bands,
            rebalance_actions=rebalance_actions,
            regime=active_regime,
            stress_factor=self.REGIME_STRESS_FACTORS.get(active_regime.upper(), 0.30),
            version=self.version,
        )


# =============================================================================
# Backward Compatibility & Alias Trees
# =============================================================================
MultiRegimeEntropyPooledHERC = HierarchicalEntropyAllocator
EntropyPooledHERCAllocator = HierarchicalEntropyAllocator
Phase110HERCAllocator = HierarchicalEntropyAllocator
BlackLittermanEntropyHERC = HierarchicalEntropyAllocator
MultiRegimeHERCEntropyAllocator = HierarchicalEntropyAllocator
BlackLittermanEntropyHERCAllocator = HierarchicalEntropyAllocator
Phase110HERCEntropyAllocator = HierarchicalEntropyAllocator
HierarchicalEqualRiskContributionEntropyAllocator = HierarchicalEntropyAllocator


def calculate_herc_entropy_weights(
    cov_matrix: np.ndarray,
    predicted_returns: Optional[Union[np.ndarray, pd.Series, Dict[str, float]]] = None,
    returns_matrix: Optional[Union[np.ndarray, pd.DataFrame]] = None,
    returns_df: Optional[Union[pd.DataFrame, np.ndarray]] = None,
    symbols: Optional[List[str]] = None,
    sectors: Optional[List[str]] = None,
    regime: Optional[str] = "SIDEWAYS_LOW_VOL",
    current_weights: Optional[Dict[str, float]] = None,
    target_volatility: float = 0.12,
    max_single_stock_weight: float = 0.20,
    max_sector_weight: float = 0.35,
    version: int = 110,
    **kwargs: Any,
) -> np.ndarray:
    """
    Convenience function for calculating HERC entropy-pooled weights.
    Returns weight vector (N,) satisfying sum w_i = 1.000000.
    """
    allocator = HierarchicalEntropyAllocator(
        target_volatility=target_volatility,
        max_single_weight=max_single_stock_weight,
        max_sector_weight=max_sector_weight,
        version=version,
        **kwargs,
    )
    data = returns_df if returns_df is not None else (returns_matrix if returns_matrix is not None else cov_matrix)
    res = allocator.allocate(
        returns_data=data,
        cov_matrix=cov_matrix,
        predicted_returns=predicted_returns,
        symbols=symbols,
        sectors=sectors,
        regime=regime,
        current_weights=current_weights,
        **kwargs,
    )
    return res.weights_vector


def solve_meucci_entropy_pooling(
    returns_matrix: np.ndarray,
    views: Optional[List[EntropyView]] = None,
    prior_probabilities: Optional[np.ndarray] = None,
    regularization: float = 1e-7,
) -> EntropyPoolingResult:
    """Convenience functional interface to Meucci's entropy pooling solver."""
    allocator = HierarchicalEntropyAllocator(regularization=regularization)
    return allocator.solve_entropy_pooling(
        returns_matrix=returns_matrix,
        views=views,
        prior_probabilities=prior_probabilities,
    )
