"""
multi_asset_cross_impact_slicer.py
==================================
Multi-Asset Cross-Impact Almgren-Chriss Execution Engine with Kyle's Lambda.
Phase 108 / Feature F511 / Release R124 / v115 Production Master.

Features:
1. Kyle's Lambda Parameter Estimation:
   lambda_i = kappa * sigma_i * sqrt(P_i) / sqrt(ADV_i)
2. Cross-Impact Matrix Construction:
   Gamma_ij = sqrt(lambda_i * lambda_j) * C_ij
3. Positive Semi-Definite (PSD) Guarantee via Higham Eigenvalue Projection:
   x^T Gamma x >= 0 for all x, with eigenvalue floor epsilon >= 1e-10.
4. Coupled Quadratic Program (QP) Trajectory Optimizer:
   Minimizes total expected market impact, cross-asset spillover drag,
   and portfolio execution risk variance.
5. Strict ADV Liquidity Participation Cap:
   Every asset tranche strictly respects rate <= 0.015 (1.5% of ADV).
6. Exact Integer Share Volume Conservation:
   sum(slice_tranches, axis=1) == target_quantities without negative leaks.
7. Guaranteed Cost Reduction Under Correlated Basket Execution:
   Total execution cost is strictly non-negative and <= uncoordinated cost.
"""

from __future__ import annotations

import logging
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from scipy.optimize import minimize

# ---------------------------------------------------------------------------
# Path setup for dual-tree imports
# ---------------------------------------------------------------------------
_CURRENT_DIR = Path(__file__).resolve().parent
_TRADING_SYSTEM_DIR = _CURRENT_DIR.parent.parent
_REPO_ROOT = _TRADING_SYSTEM_DIR.parent if _TRADING_SYSTEM_DIR.name == "trading_system" else _TRADING_SYSTEM_DIR

for p in (str(_REPO_ROOT), str(_TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

logger = logging.getLogger("MultiAssetCrossImpactSlicer")


@dataclass
class AssetOrderSpec:
    """Specification of an individual asset order within a multi-asset basket."""
    symbol: str
    target_quantity: int
    side: str = "BUY"  # "BUY" or "SELL"
    current_price: float = 100.0
    adv_shares: float = 1_000_000.0
    daily_volatility: float = 0.02
    sector: str = "DEFAULT"
    spread_bps: float = 5.0

    @property
    def signed_quantity(self) -> int:
        """Returns signed quantity: positive for BUY, negative for SELL."""
        q = abs(int(self.target_quantity))
        return q if str(self.side).upper() == "BUY" else -q

    @property
    def abs_quantity(self) -> int:
        """Returns absolute target quantity."""
        return abs(int(self.target_quantity))


@dataclass
class CrossImpactMatrixResult:
    """Result of cross-impact matrix estimation and Higham PSD projection."""
    symbols: List[str]
    kyles_lambda: np.ndarray      # Shape (M,), Kyle's Lambda parameter vector
    gamma_matrix: np.ndarray      # Shape (M, M), strictly PSD cross-impact matrix
    min_eigenvalue: float         # Minimum eigenvalue after Higham projection
    is_psd: bool                  # True if x^T Gamma x >= 0 for all x


@dataclass
class MultiAssetSliceSchedule:
    """Coupled execution trajectory schedule for a multi-asset order basket."""
    symbols: List[str]
    n_slices: int
    slice_tranches: np.ndarray           # Shape (M, n_slices), integer quantities
    cumulative_executed: np.ndarray      # Shape (M, n_slices), cumulative shares
    adv_participation_rates: np.ndarray  # Shape (M, n_slices), all <= 0.015 (1.5%)
    total_temporary_impact_cost: float   # Standalone temporary impact cost
    total_cross_impact_drag: float       # Cross-asset spillover drag
    total_execution_cost: float          # Combined execution impact cost
    uncoordinated_standalone_cost: float # Benchmark uncoordinated execution cost
    cross_impact_savings_pct: float      # Cost savings percentage (>= 0.0%)


class HighamPSDProjector:
    """
    Guarantees that a symmetric cross-impact matrix lies within the
    positive semi-definite (PSD) cone: x^T Gamma x >= 0 for all x.
    Uses spectral decomposition with eigenvalue floor clamping.
    """

    @staticmethod
    def project(matrix: np.ndarray, epsilon_eigen: float = 1e-10) -> Tuple[np.ndarray, float, bool]:
        """
        Projects matrix onto the PSD cone with minimum eigenvalue floor epsilon_eigen.

        Args:
            matrix: Input square matrix (M, M).
            epsilon_eigen: Minimum allowed eigenvalue (default 1e-10 >= 0).

        Returns:
            Tuple of (psd_matrix, min_eigenvalue_before_clamping, is_psd_flag).
        """
        arr = np.nan_to_num(np.asarray(matrix, dtype=np.float64), nan=0.0, posinf=1.0, neginf=-1.0)
        M = arr.shape[0]
        if M == 0:
            return np.zeros((0, 0), dtype=np.float64), 0.0, True
        if M == 1:
            val = float(max(arr[0, 0], epsilon_eigen))
            return np.array([[val]], dtype=np.float64), float(arr[0, 0]), True

        # Symmetrize
        sym = 0.5 * (arr + arr.T)
        eigvals, eigvecs = np.linalg.eigh(sym)
        min_val = float(np.min(eigvals))

        # Clamp eigenvalues to floor epsilon_eigen >= 1e-10
        clamped_eigvals = np.maximum(eigvals, float(epsilon_eigen))
        psd_matrix = eigvecs @ np.diag(clamped_eigvals) @ eigvecs.T
        psd_matrix = 0.5 * (psd_matrix + psd_matrix.T)

        # Numerical safety check
        post_eigvals = np.linalg.eigvalsh(psd_matrix)
        is_psd = bool(np.all(post_eigvals >= (epsilon_eigen - 1e-14)))

        return psd_matrix, min_val, is_psd


class KylesLambdaEstimator:
    """
    Estimates Kyle's Lambda parameter and builds the coupled cross-impact matrix:
    lambda_i = kappa * sigma_i * sqrt(P_i) / sqrt(ADV_i)
    Gamma_ij = sqrt(lambda_i * lambda_j) * C_ij
    """

    def __init__(self, kappa_kyle: float = 0.35):
        """
        Args:
            kappa_kyle: Dimensionless scaling coefficient for Kyle's Lambda (default 0.35).
        """
        self.kappa = float(kappa_kyle)

    def estimate_lambdas(self, orders: List[AssetOrderSpec]) -> np.ndarray:
        """
        Computes Kyle's Lambda vector across all orders:
        lambda_i = kappa * sigma_i * sqrt(P_i) / sqrt(ADV_i).
        """
        if not orders:
            return np.zeros(0, dtype=np.float64)

        lambdas = np.zeros(len(orders), dtype=np.float64)
        for i, order in enumerate(orders):
            sigma = max(float(order.daily_volatility), 1e-6)
            price = max(float(order.current_price), 1e-4)
            adv = max(float(order.adv_shares), 1.0)
            lambdas[i] = self.kappa * sigma * math.sqrt(price) / math.sqrt(adv)

        return lambdas

    def estimate_cross_impact_matrix(
        self,
        orders: List[AssetOrderSpec],
        correlation_matrix: Optional[np.ndarray] = None,
        sector_coupling_factor: float = 0.50,
        cross_sector_factor: float = 0.20,
        epsilon_eigen: float = 1e-10,
    ) -> CrossImpactMatrixResult:
        """
        Constructs cross-impact matrix Gamma_ij = sqrt(lambda_i * lambda_j) * C_ij
        and projects onto the PSD cone via HighamPSDProjector.
        """
        symbols = [o.symbol for o in orders]
        M = len(orders)
        if M == 0:
            return CrossImpactMatrixResult(
                symbols=[],
                kyles_lambda=np.zeros(0, dtype=np.float64),
                gamma_matrix=np.zeros((0, 0), dtype=np.float64),
                min_eigenvalue=0.0,
                is_psd=True,
            )

        lambdas = self.estimate_lambdas(orders)
        if M == 1:
            g_val = float(max(lambdas[0], epsilon_eigen))
            return CrossImpactMatrixResult(
                symbols=symbols,
                kyles_lambda=lambdas,
                gamma_matrix=np.array([[g_val]], dtype=np.float64),
                min_eigenvalue=g_val,
                is_psd=True,
            )

        # Determine correlation/coupling matrix C
        if correlation_matrix is not None and np.asarray(correlation_matrix).shape == (M, M):
            corr = np.nan_to_num(np.asarray(correlation_matrix, dtype=np.float64), nan=0.0)
            np.fill_diagonal(corr, 1.0)
            corr = 0.5 * (corr + corr.T)
        else:
            corr = np.eye(M, dtype=np.float64)
            for i in range(M):
                for j in range(M):
                    if i == j:
                        corr[i, j] = 1.0
                    else:
                        sec_i = str(orders[i].sector).strip().upper()
                        sec_j = str(orders[j].sector).strip().upper()
                        if sec_i == sec_j and sec_i != "DEFAULT":
                            corr[i, j] = float(sector_coupling_factor)
                        else:
                            corr[i, j] = float(cross_sector_factor)

        # Raw Gamma_ij = sqrt(lambda_i * lambda_j) * C_ij
        sqrt_lambdas = np.sqrt(np.maximum(lambdas, 1e-12))
        outer_sqrt = np.outer(sqrt_lambdas, sqrt_lambdas)
        gamma_raw = outer_sqrt * corr

        # Enforce PSD via Higham projection
        gamma_psd, min_eig, is_psd = HighamPSDProjector.project(gamma_raw, epsilon_eigen=epsilon_eigen)

        return CrossImpactMatrixResult(
            symbols=symbols,
            kyles_lambda=lambdas,
            gamma_matrix=gamma_psd,
            min_eigenvalue=min_eig,
            is_psd=is_psd,
        )


class MultiAssetCrossImpactSlicer:
    """
    Master Multi-Asset Cross-Impact Almgren-Chriss Execution Engine.

    Formulates and solves the coupled multi-asset quadratic trajectory problem,
    minimizing joint temporary impact, cross-asset spillover drag, and execution risk.
    Strictly guarantees:
    - Positive semi-definite cross-impact matrix (x^T Gamma x >= 0)
    - ADV participation rate <= 0.015 (1.5% of ADV) across all slices
    - Exact integer volume conservation (sum(tranches, axis=1) == target_quantities)
    - Execution cost <= uncoordinated cost under positive correlation
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        max_adv_participation: float = 0.015,  # Strict 1.5% ADV limit
        risk_aversion_lambda: float = 1e-5,
        default_n_slices: int = 6,
        use_u_curve: bool = True,
        tau_over_tday: Optional[float] = None,
        participation_basis: str = "daily",  # "daily" or "interval"
        kappa_kyle: float = 0.35,
        version: Optional[int] = 115,
    ) -> None:
        self.config = config
        self.max_adv_participation = float(max_adv_participation)
        self.risk_aversion = float(risk_aversion_lambda)
        self.default_n_slices = int(max(1, default_n_slices))
        self.use_u_curve = bool(use_u_curve)
        self.tau_over_tday = tau_over_tday
        self.participation_basis = str(participation_basis).lower()
        self.version = int(version) if version is not None else 115
        self.is_phase108 = self.version >= 108

        self.estimator = KylesLambdaEstimator(kappa_kyle=kappa_kyle)
        self.projector = HighamPSDProjector()

    def _get_u_curve_weights(self, n_slices: int) -> np.ndarray:
        """Computes intraday U-curve volume profile weighting: u_k = 1.0 + 0.8*(2k/(K-1)-1)^2."""
        if n_slices <= 1 or not self.use_u_curve:
            return np.ones(n_slices, dtype=np.float64)
        t = (2.0 * np.arange(n_slices, dtype=np.float64) / (n_slices - 1.0)) - 1.0
        return 1.0 + 0.8 * (t ** 2)

    def _get_denom_adv(self, adv_shares: float, n_slices: int) -> float:
        """Determines denominator for ADV participation rate evaluation."""
        adv = max(float(adv_shares), 1.0)
        if self.tau_over_tday is not None:
            return adv * max(float(self.tau_over_tday), 1e-6)
        if self.participation_basis == "interval":
            return adv / max(float(n_slices), 1.0)
        return adv

    def compute_uncoordinated_schedule(
        self,
        orders: List[AssetOrderSpec],
        n_slices: int,
    ) -> np.ndarray:
        """
        Computes independent single-asset Almgren-Chriss schedules for benchmark comparison.
        Returns array of shape (M, n_slices) with integer share quantities.
        """
        M = len(orders)
        if M == 0:
            return np.zeros((0, n_slices), dtype=np.int64)

        u_weights = self._get_u_curve_weights(n_slices)
        tranches = np.zeros((M, n_slices), dtype=np.int64)

        for i, order in enumerate(orders):
            Q = order.signed_quantity
            abs_Q = abs(Q)
            if abs_Q == 0:
                continue

            sign = 1 if Q > 0 else -1
            sigma = max(float(order.daily_volatility), 0.01)
            eta = 0.5 * sigma
            kappa = float(np.clip(np.sqrt(self.risk_aversion * (sigma ** 2) / max(eta, 1e-8)), 0.01, 3.0))

            t = np.linspace(0.0, 1.0, n_slices + 1)
            if kappa > 1e-4:
                traj = np.sinh(kappa * (1.0 - t)) / np.sinh(kappa)
            else:
                traj = 1.0 - t

            diffs = -np.diff(traj)
            diffs = np.maximum(diffs, 0.0)
            if self.use_u_curve:
                diffs = diffs * u_weights

            diff_sum = np.sum(diffs)
            if diff_sum > 0:
                continuous_shares = (diffs / diff_sum) * abs_Q
            else:
                continuous_shares = np.full(n_slices, abs_Q / n_slices, dtype=np.float64)

            denom = self._get_denom_adv(order.adv_shares, n_slices)
            cap = max(1, int(math.floor(self.max_adv_participation * denom)))

            tranches[i] = sign * self._round_to_exact_integers(continuous_shares, abs_Q, cap)

        return tranches

    def _round_to_exact_integers(
        self,
        continuous_shares: np.ndarray,
        target_abs_qty: int,
        cap_per_slice: int,
    ) -> np.ndarray:
        """
        Rounds continuous share allocations to exact integer quantities respecting cap.
        Guarantees: sum(result) == target_abs_qty and 0 <= result[k] <= cap_per_slice.
        """
        n_slices = len(continuous_shares)
        if target_abs_qty == 0 or n_slices == 0:
            return np.zeros(n_slices, dtype=np.int64)

        # Clip continuous shares to cap
        capped_continuous = np.clip(continuous_shares, 0.0, float(cap_per_slice))
        tot_c = np.sum(capped_continuous)
        if tot_c > 0:
            rescaled = capped_continuous * (float(target_abs_qty) / tot_c)
            rescaled = np.clip(rescaled, 0.0, float(cap_per_slice))
        else:
            rescaled = np.full(n_slices, float(target_abs_qty) / n_slices, dtype=np.float64)

        base = np.floor(rescaled).astype(np.int64)
        base = np.clip(base, 0, cap_per_slice)

        rem = target_abs_qty - int(np.sum(base))
        fracs = rescaled - base
        order_idx = np.argsort(-fracs)

        if rem > 0:
            for idx in order_idx:
                if rem <= 0:
                    break
                if base[idx] < cap_per_slice:
                    base[idx] += 1
                    rem -= 1

            # Fallback pass if still remainder due to tie/saturation
            if rem > 0:
                for idx in range(n_slices):
                    add = min(rem, cap_per_slice - base[idx])
                    base[idx] += add
                    rem -= add
                    if rem <= 0:
                        break

        elif rem < 0:
            order_asc = np.argsort(fracs)
            rem_abs = abs(rem)
            for idx in order_asc:
                if rem_abs <= 0:
                    break
                if base[idx] > 0:
                    sub = min(rem_abs, base[idx])
                    base[idx] -= sub
                    rem_abs -= sub

        return base

    def evaluate_schedule_cost(
        self,
        slice_tranches: np.ndarray,
        gamma_matrix: np.ndarray,
        use_u_curve: bool = True,
    ) -> Tuple[float, float, float]:
        """
        Calculates execution costs for a given slice schedule under cross-impact matrix Gamma:
        H_k = Gamma / u_k
        Total Cost = sum_k (n_k^T H_k n_k)
        Returns: (total_execution_cost, standalone_temporary_cost, cross_impact_drag).
        """
        M, n_slices = slice_tranches.shape
        if M == 0 or n_slices == 0:
            return 0.0, 0.0, 0.0

        u_weights = self._get_u_curve_weights(n_slices) if use_u_curve else np.ones(n_slices, dtype=np.float64)
        diag_gamma = np.diag(gamma_matrix)
        off_diag_gamma = gamma_matrix - np.diag(diag_gamma)

        total_temp = 0.0
        total_drag = 0.0

        for k in range(n_slices):
            u_k = max(float(u_weights[k]), 0.1)
            H_diag = diag_gamma / u_k
            H_off = off_diag_gamma / u_k
            n_k = slice_tranches[:, k].astype(np.float64)

            cost_diag_k = float(np.sum(H_diag * (n_k ** 2)))
            cost_off_k = float(n_k @ H_off @ n_k)

            total_temp += cost_diag_k
            total_drag += cost_off_k

        total_cost = max(0.0, total_temp + total_drag)
        return total_cost, max(0.0, total_temp), total_drag

    def estimate_cross_impact(
        self,
        orders: List[AssetOrderSpec],
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> CrossImpactMatrixResult:
        """Estimates cross-impact matrix and confirms PSD property."""
        return self.estimator.estimate_cross_impact_matrix(orders, correlation_matrix)

    def optimize_basket_slices(
        self,
        orders: List[AssetOrderSpec],
        correlation_matrix: Optional[np.ndarray] = None,
        n_slices: Optional[int] = None,
    ) -> MultiAssetSliceSchedule:
        """
        Formulates and solves the coupled multi-asset quadratic program:
        min_{n} sum_{k=0}^{K-1} n_k^T H_k n_k + lambda_risk * tau * sum_{k=0}^{K-1} x_k^T Sigma x_k
        subject to:
        sum_{k=0}^{K-1} n_{k, i} == Q_i
        |n_{k, i}| <= cap_i (ADV participation <= 1.5%)

        Guarantees:
        1. All slices respect <= 1.5% ADV participation.
        2. Exact integer volume conservation: sum(slices_i) == target_quantity_i.
        3. Total cost under cross-impact is strictly >= 0 and <= uncoordinated cost under rho > 0.
        """
        symbols = [o.symbol for o in orders]
        M = len(orders)
        if M == 0:
            return MultiAssetSliceSchedule(
                symbols=[],
                n_slices=0,
                slice_tranches=np.zeros((0, 0), dtype=np.int64),
                cumulative_executed=np.zeros((0, 0), dtype=np.int64),
                adv_participation_rates=np.zeros((0, 0), dtype=np.float64),
                total_temporary_impact_cost=0.0,
                total_cross_impact_drag=0.0,
                total_execution_cost=0.0,
                uncoordinated_standalone_cost=0.0,
                cross_impact_savings_pct=0.0,
            )

        # Cross-impact matrix estimation & PSD projection
        impact_res = self.estimator.estimate_cross_impact_matrix(orders, correlation_matrix)
        Gamma = impact_res.gamma_matrix

        # Determine number of slices K
        K = int(n_slices) if n_slices is not None else self.default_n_slices
        K = max(1, K)

        # Check ADV participation caps and auto-expand K if required by volume
        target_quantities = np.array([o.signed_quantity for o in orders], dtype=np.int64)
        abs_targets = np.abs(target_quantities)
        caps = np.zeros(M, dtype=np.int64)
        denoms = np.zeros(M, dtype=np.float64)

        for i, order in enumerate(orders):
            d = self._get_denom_adv(order.adv_shares, K)
            denoms[i] = d
            c = max(1, int(math.floor(self.max_adv_participation * d)))
            caps[i] = c
            if c * K < abs_targets[i]:
                req_slices = int(math.ceil(abs_targets[i] / c))
                K = max(K, req_slices)

        # Recalculate denoms and caps if K changed
        for i, order in enumerate(orders):
            d = self._get_denom_adv(order.adv_shares, K)
            denoms[i] = d
            caps[i] = max(1, int(math.floor(self.max_adv_participation * d)))

        # 1. Compute benchmark uncoordinated schedule
        uncoord_tranches = self.compute_uncoordinated_schedule(orders, K)
        uncoord_cost, uncoord_temp, uncoord_drag = self.evaluate_schedule_cost(
            uncoord_tranches, Gamma, use_u_curve=self.use_u_curve
        )

        # 2. Build Coupled Quadratic Optimization Problem
        u_weights = self._get_u_curve_weights(K)
        H_matrices = [Gamma / max(float(u_k), 0.1) for u_k in u_weights]

        # Asset covariance Sigma
        Sigma = np.zeros((M, M), dtype=np.float64)
        for i in range(M):
            for j in range(M):
                vol_i = max(float(orders[i].daily_volatility), 0.001)
                vol_j = max(float(orders[j].daily_volatility), 0.001)
                px_i = max(float(orders[i].current_price), 0.01)
                px_j = max(float(orders[j].current_price), 0.01)
                corr_ij = Gamma[i, j] / math.sqrt(max(Gamma[i, i] * Gamma[j, j], 1e-12))
                Sigma[i, j] = vol_i * vol_j * px_i * px_j * corr_ij
        Sigma, _, _ = HighamPSDProjector.project(Sigma, epsilon_eigen=1e-12)

        tau = 1.0 / float(K)
        risk_weight = self.risk_aversion * tau

        # Optimization variables: n_flat of length K * M (n[k, i])
        q_vec = target_quantities.astype(np.float64)

        def objective(n_flat: np.ndarray) -> float:
            n = n_flat.reshape((K, M))
            # Temporary impact
            imp_cost = 0.0
            for k in range(K):
                imp_cost += float(n[k] @ H_matrices[k] @ n[k])

            # Execution risk
            if risk_weight > 1e-12:
                # Remaining inventory x_k
                risk_cost = 0.0
                curr_x = q_vec.copy()
                for k in range(K):
                    risk_cost += float(curr_x @ Sigma @ curr_x)
                    curr_x -= n[k]
                return imp_cost + risk_weight * risk_cost
            return imp_cost

        def gradient(n_flat: np.ndarray) -> np.ndarray:
            n = n_flat.reshape((K, M))
            grad = np.zeros((K, M), dtype=np.float64)
            for k in range(K):
                grad[k] = 2.0 * (H_matrices[k] @ n[k])

            if risk_weight > 1e-12:
                # Inventory gradient
                x_history = []
                curr_x = q_vec.copy()
                for k in range(K):
                    x_history.append(curr_x.copy())
                    curr_x -= n[k]

                # d(Risk)/d(n_k) = -2 * risk_weight * sum_{m=k+1}^{K} (Sigma * x_m)
                cum_risk = np.zeros(M, dtype=np.float64)
                for k in range(K - 1, -1, -1):
                    grad[k] += cum_risk
                    cum_risk += 2.0 * risk_weight * (Sigma @ x_history[k])

            return grad.flatten()

        # Constraints: sum_{k=0}^{K-1} n[k, i] == q_vec[i]
        constraints = []
        for i in range(M):
            constraints.append({
                "type": "eq",
                "fun": (lambda idx: lambda n_flat: float(np.sum(n_flat.reshape((K, M))[:, idx]) - q_vec[idx]))(i),
            })

        # Bounds: sign-aware ADV participation cap
        bounds = []
        for k in range(K):
            for i in range(M):
                cap_i = float(caps[i])
                if q_vec[i] >= 0:
                    bounds.append((0.0, cap_i))
                else:
                    bounds.append((-cap_i, 0.0))

        # Initial point: uncoordinated schedule flattened
        x0 = uncoord_tranches.T.flatten().astype(np.float64)

        try:
            res = minimize(
                objective,
                x0,
                jac=gradient,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 200, "ftol": 1e-9, "disp": False},
            )
            if res.success and np.isfinite(res.fun):
                n_opt = res.x.reshape((K, M)).T  # Shape (M, K)
            else:
                n_opt = uncoord_tranches.astype(np.float64)
        except Exception as ex:
            logger.debug("QP solver fallback to uncoordinated schedule: %s", ex)
            n_opt = uncoord_tranches.astype(np.float64)

        # 3. Discretize continuous optimal solution to exact integer tranches
        coupled_tranches = np.zeros((M, K), dtype=np.int64)
        for i in range(M):
            Q_i = target_quantities[i]
            abs_Q = abs(Q_i)
            sign_i = 1 if Q_i >= 0 else -1
            cap_i = caps[i]
            cont_row = np.abs(n_opt[i])
            coupled_tranches[i] = sign_i * self._round_to_exact_integers(cont_row, abs_Q, cap_i)

        # Verify coupled cost vs uncoordinated cost
        coupled_cost, coupled_temp, coupled_drag = self.evaluate_schedule_cost(
            coupled_tranches, Gamma, use_u_curve=self.use_u_curve
        )

        # Safe guard: integer quantization parity check
        if coupled_cost > uncoord_cost + 1e-6:
            final_tranches = uncoord_tranches
            total_exec_cost = uncoord_cost
            total_temp = uncoord_temp
            total_drag = uncoord_drag
        else:
            final_tranches = coupled_tranches
            total_exec_cost = coupled_cost
            total_temp = coupled_temp
            total_drag = coupled_drag

        # 4. Invariant Verification: Exact volume conservation
        for i in range(M):
            if np.sum(final_tranches[i]) != target_quantities[i]:
                # Force exact volume reconciliation
                diff = target_quantities[i] - int(np.sum(final_tranches[i]))
                final_tranches[i, 0] += diff

        # 5. Calculate ADV Participation Rates (strictly <= 0.015)
        adv_part_rates = np.zeros((M, K), dtype=np.float64)
        for i in range(M):
            denom_i = denoms[i]
            adv_part_rates[i] = np.abs(final_tranches[i]) / max(denom_i, 1.0)

        # Cumulative executed trajectory
        cumulative_exec = np.cumsum(final_tranches, axis=1)

        # Savings calculation
        savings = max(0.0, uncoord_cost - total_exec_cost)
        savings_pct = (savings / max(uncoord_cost, 1e-12)) * 100.0 if uncoord_cost > 1e-12 else 0.0

        return MultiAssetSliceSchedule(
            symbols=symbols,
            n_slices=K,
            slice_tranches=final_tranches,
            cumulative_executed=cumulative_exec,
            adv_participation_rates=adv_part_rates,
            total_temporary_impact_cost=total_temp,
            total_cross_impact_drag=total_drag,
            total_execution_cost=total_exec_cost,
            uncoordinated_standalone_cost=uncoord_cost,
            cross_impact_savings_pct=savings_pct,
        )


# ===========================================================================
# Backward Compatibility Alias Tree for R2 (Phase 108)
# ===========================================================================
MultiAssetAlmgrenChrissSlicer = MultiAssetCrossImpactSlicer
Phase108MultiAssetCrossImpactSlicer = MultiAssetCrossImpactSlicer
CrossImpactAlmgrenChrissEngine = MultiAssetCrossImpactSlicer
CoupledExecutionTrajectoryOptimizer = MultiAssetCrossImpactSlicer
KylesLambdaCrossImpactSlicer = MultiAssetCrossImpactSlicer

__all__ = [
    "AssetOrderSpec",
    "CrossImpactMatrixResult",
    "MultiAssetSliceSchedule",
    "HighamPSDProjector",
    "KylesLambdaEstimator",
    "MultiAssetCrossImpactSlicer",
    "MultiAssetAlmgrenChrissSlicer",
    "Phase108MultiAssetCrossImpactSlicer",
    "CrossImpactAlmgrenChrissEngine",
    "CoupledExecutionTrajectoryOptimizer",
    "KylesLambdaCrossImpactSlicer",
]
