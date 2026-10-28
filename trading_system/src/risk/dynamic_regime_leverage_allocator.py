"""
Dynamic Regime Leverage & Kelly Allocator Architecture (Phase 141, Features F685–F689).
Production Institutional Master Implementation.

Features Covered:
- Feature F685: Multi-Asset Fractional Kelly Criterion with 4th-Order Fat-Tail Contraction
- Feature F686: Dynamic Regime Leverage Frontiers across 8 Regimes & Portfolio Beta Clamping
- Feature F687: 4-Tier Protective Gating (VIX Velocity, TSR Contango Lock, HWM DD, Leland Buffer)
- Feature F688: OAS Covariance Shrinkage & Top-50 Mode-Exempt Marchenko-Pastur RMT Regularizer
- Feature F689: Production Allocator Integration & Leland Buffer Expansion
"""

from typing import Dict, List, Optional, Tuple, Any, Union
import logging
import math
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

VERSION: int = 141
RELEASE: str = "R141"
FEATURE: str = "F685-F689"


class DynamicRegimeLeverageAllocator:
    """
    Dynamic Regime Leverage & Multi-Asset Fractional Kelly Allocator.
    Orchestrates high-dimensional OAS + Top-50 mode-exempt RMT covariance regularizer,
    fractional Kelly with fat-tail contraction, dynamic gross leverage frontiers across 8 regimes,
    and 4-tier protective gating.
    """

    VERSION: int = VERSION
    RELEASE: str = RELEASE
    FEATURE: str = FEATURE

    REGIME_GROSS_LEVERAGE_FRONTIERS: Dict[str, float] = {
        "BULL_LOW_VOL": 1.25,
        "RELIEF_RALLY": 1.25,      # Subject to 5d Contango Lock (else 0.90)
        "BULL_HIGH_VOL": 1.10,
        "SIDEWAYS_LOW_VOL": 0.95,
        "SIDEWAYS_HIGH_VOL": 0.85,
        "BEAR_LOW_VOL": 0.60,
        "BEAR_HIGH_VOL": 0.30,      # Triggers Gate 8 Inverse Hedge
        "PANIC_CRISIS": 0.15,       # Cash & Treasuries
    }

    REGIME_FRACTIONAL_KELLY_KAPPA: Dict[str, float] = {
        "BULL_LOW_VOL": 0.48,
        "RELIEF_RALLY": 0.38,
        "BULL_HIGH_VOL": 0.32,
        "SIDEWAYS_LOW_VOL": 0.28,
        "SIDEWAYS_HIGH_VOL": 0.20,
        "BEAR_LOW_VOL": 0.12,
        "BEAR_HIGH_VOL": 0.06,
        "PANIC_CRISIS": 0.00,
    }

    def __init__(
        self,
        max_bull_leverage: float = 1.25,
        min_crisis_exposure: float = 0.15,
        borrowing_spread_bps: float = 60.0,
        hwm_dd_limit: float = -0.15,
        default_kappa: float = 0.375,
        top_k_modes: int = 50,
    ):
        self.max_bull_leverage = float(max_bull_leverage)
        self.min_crisis_exposure = float(min_crisis_exposure)
        self.borrow_spread = float(borrowing_spread_bps) / 10000.0
        self.hwm_dd_limit = float(hwm_dd_limit)
        self.default_kappa = float(default_kappa)
        self.top_k_modes = int(top_k_modes)
        self.hwm_peak = 0.0

    def compute_oas_rmt_covariance(
        self,
        returns_df: Union[pd.DataFrame, np.ndarray],
        top_k_modes: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        High-Dimensional Regularized Covariance via Oracle Approximating Shrinkage (OAS)
        and Top-K Systematic Mode-Exempt Marchenko-Pastur RMT Denoising (Feature F688).

        Parameters
        ----------
        returns_df : pd.DataFrame or np.ndarray
            T x N matrix of asset returns.
        top_k_modes : int, optional
            Number of leading systematic factor eigenvalues strictly exempted from clipping.
            Defaults to self.top_k_modes (50).

        Returns
        -------
        cov_final : np.ndarray (N x N)
            Symmetric, positive definite regularized covariance matrix.
        vols : np.ndarray (N,)
            Annualized volatility vector (scaled by sqrt(252)).
        """
        k_modes = self.top_k_modes if top_k_modes is None else int(top_k_modes)

        if isinstance(returns_df, pd.DataFrame):
            X = np.nan_to_num(returns_df.values.astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        else:
            X = np.nan_to_num(np.asarray(returns_df, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)

        if X.ndim == 1:
            X = X.reshape(-1, 1)

        T, N = X.shape

        # Minimal data edge case handling
        if T < 5 or N < 2:
            cov = np.cov(X, rowvar=False) if N > 1 else np.array([[0.04]])
            if cov.ndim == 0:
                cov = np.array([[float(cov)]])
            np.fill_diagonal(cov, cov.diagonal() + 1e-6)
            vols = np.sqrt(np.maximum(np.diag(cov) * 252.0, 1e-6))
            return cov, vols

        # Sample covariance & traces
        S = np.cov(X, rowvar=False)
        if S.ndim == 0:
            S = np.array([[float(S)]])

        tr_S = float(np.trace(S))
        tr_S2 = float(np.sum(S ** 2))

        # OAS optimal shrinkage intensity (Chen et al., 2010)
        # Target F = (tr(S)/N) * I
        num = (1.0 - 2.0 / N) * tr_S2 + (tr_S ** 2)
        den = (T + 1.0 - 2.0 / N) * (tr_S2 - (tr_S ** 2) / N)
        rho_oas = float(np.clip(num / den, 0.0, 1.0)) if den > 1e-12 else 0.20

        # In-place diagonal shrinkage (avoids redundant allocation)
        cov_oas = (1.0 - rho_oas) * S
        diag_boost = rho_oas * (tr_S / N)
        np.fill_diagonal(cov_oas, cov_oas.diagonal() + diag_boost)

        # Correlation matrix via broadcasting with zero-variance protection
        d_diag = np.sqrt(np.maximum(np.diag(cov_oas), 1e-8))
        inv_d = 1.0 / d_diag
        corr = inv_d[:, None] * cov_oas * inv_d[None, :]
        corr = 0.5 * (corr + corr.T)  # Enforce exact numerical symmetry

        # Eigendecomposition (LAPACK eigh)
        eigvals, eigvecs = np.linalg.eigh(corr)

        # Top-K Systematic Mode Exemption & Bulk Noise Boundary
        eff_top_k = min(k_modes, N - 1)
        if eff_top_k > 0 and len(eigvals) > eff_top_k:
            bulk_evals = eigvals[:-eff_top_k]
            sigma2_noise = float(np.mean(bulk_evals))
            q_eff = float(len(bulk_evals)) / float(T)
            lambda_plus = sigma2_noise * ((1.0 + np.sqrt(q_eff)) ** 2)

            noise_mask = np.zeros(N, dtype=bool)
            noise_mask[:-eff_top_k] = bulk_evals <= lambda_plus

            if np.any(noise_mask):
                mean_noise = float(np.mean(eigvals[noise_mask]))
                # Low-Rank Spectral Reconstruction identity: O(N^2 * M_signal)
                signal_mask = ~noise_mask
                V_sig = eigvecs[:, signal_mask]
                diff_sig = eigvals[signal_mask] - mean_noise
                corr_denoised = (V_sig * diff_sig) @ V_sig.T
                np.fill_diagonal(corr_denoised, corr_denoised.diagonal() + mean_noise)
            else:
                corr_denoised = corr
        else:
            corr_denoised = corr

        # Symmetric Diagonal Normalization (guarantees exact unit correlation diagonal)
        d_inv_den = 1.0 / np.sqrt(np.maximum(np.diag(corr_denoised), 1e-8))
        corr_norm = d_inv_den[:, None] * corr_denoised * d_inv_den[None, :]

        # Rescale to regularized covariance
        cov_denoised = d_diag[:, None] * corr_norm * d_diag[None, :]
        cov_final = 0.5 * (cov_denoised + cov_denoised.T)

        # Tikhonov jitter for strict positive definiteness
        np.fill_diagonal(cov_final, cov_final.diagonal() + 1.000001e-6)
        vols = np.sqrt(np.maximum(np.diag(cov_final) * 252.0, 1e-6))

        return cov_final, vols

    def evaluate_dynamic_leverage_frontier(
        self,
        current_nav: float,
        vix: float,
        vix_history: List[float],
        tsr_ratio: float,
        regime: str,
        tsr_history: Optional[List[float]] = None,
    ) -> float:
        """
        Evaluates dynamic gross leverage frontier across 8 regimes subject to 4-tier gating (Feature F687).
        Gates:
          1. Gate 1: VIX Level & Velocity (dVIX/dt)
          2. Gate 2: Volatility Term Structure Ratio (TSR = VIX9D/VIX30D) with 5d Contango Lock
          3. Gate 3: Piecewise continuous HWM Drawdown Tier
          4. Regime Target Resolution
        Returns optimal gross leverage L_t in [0.15, 1.25].
        """
        # Track High-Water Mark Peak
        c_nav = float(current_nav) if (current_nav is not None and math.isfinite(float(current_nav))) else 0.0
        if self.hwm_peak <= 0.0 or c_nav > self.hwm_peak:
            self.hwm_peak = c_nav
        dd = (c_nav - self.hwm_peak) / self.hwm_peak if self.hwm_peak > 0 else 0.0

        # Gate 3: HWM Drawdown Tier
        if dd <= -0.120:
            dd_cap = self.min_crisis_exposure
        elif dd <= -0.100:
            dd_cap = 0.50
        elif dd <= -0.070:
            dd_cap = 0.85
        elif dd < -0.040:
            dd_cap = 1.00 + 0.25 * ((-0.070 - dd) / (-0.030))
        else:
            dd_cap = self.max_bull_leverage

        # Gate 1: VIX Level & Velocity Filter
        vix_val = float(vix) if (vix is not None and math.isfinite(float(vix))) else 20.0
        vix_vel = (vix_val - float(vix_history[-5])) / 5.0 if (vix_history is not None and len(vix_history) >= 5) else 0.0

        if vix_val > 28.0 or vix_vel > 2.00:
            vix_cap = 0.40
        elif vix_val > 22.0 or vix_vel > 1.00:
            vix_cap = 0.75
        elif vix_val > 18.0 or vix_vel > 0.50:
            vix_cap = 1.00
        else:
            vix_cap = self.max_bull_leverage

        # Gate 2: Volatility Term Structure Ratio (TSR = VIX9D / VIX30D)
        tsr_val = float(tsr_ratio) if (tsr_ratio is not None and math.isfinite(float(tsr_ratio))) else 0.90
        if tsr_val >= 1.08:
            tsr_cap = 0.50
        elif tsr_val >= 1.00:
            tsr_cap = 0.80
        elif tsr_val > 0.95:
            tsr_cap = 1.00
        else:
            tsr_cap = self.max_bull_leverage

        # Regime Target Frontier Resolution
        reg_str = str(regime or "BULL_LOW_VOL").upper()
        if "BULL_LOW_VOL" in reg_str:
            reg_target = self.max_bull_leverage
        elif "RELIEF_RALLY" in reg_str:
            # 5-day contango hysteresis lock: TSR < 0.95 for 5 consecutive days required
            tsr_contango_5d = (
                tsr_history is not None
                and len(tsr_history) >= 5
                and all(float(r) < 0.95 for r in tsr_history[-5:])
            )
            reg_target = self.max_bull_leverage if tsr_contango_5d else 0.90
        elif "BULL_HIGH_VOL" in reg_str:
            reg_target = 1.10
        elif "SIDEWAYS_LOW_VOL" in reg_str:
            reg_target = 0.95
        elif "SIDEWAYS_HIGH_VOL" in reg_str:
            reg_target = 0.85
        elif "BEAR_LOW_VOL" in reg_str:
            reg_target = 0.60
        elif "BEAR_HIGH_VOL" in reg_str:
            reg_target = 0.30
        elif "PANIC" in reg_str or "CRISIS" in reg_str:
            reg_target = self.min_crisis_exposure
        else:
            reg_target = self.REGIME_GROSS_LEVERAGE_FRONTIERS.get(reg_str, 0.95)

        optimal_leverage = float(min(reg_target, dd_cap, vix_cap, tsr_cap))
        return float(max(self.min_crisis_exposure, optimal_leverage))

    def compute_higher_order_co_moments(
        self,
        returns_matrix: np.ndarray,
        weights: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes sample coskewness s(w) and cokurtosis k(w) vectors.
        s_i(w) = E[(R_i - mu_i)(w^T (R - mu))^2]
        k_i(w) = E[(R_i - mu_i)(w^T (R - mu))^3]
        """
        R = np.nan_to_num(np.asarray(returns_matrix, dtype=np.float64), nan=0.0)
        T, N = R.shape
        if T < 2 or N == 0:
            return np.zeros(N), np.zeros(N)

        mu = np.mean(R, axis=0)
        R_demean = R - mu

        if weights is None or len(weights) != N:
            w = np.full(N, 1.0 / N)
        else:
            w = np.asarray(weights, dtype=np.float64)
            if np.sum(np.abs(w)) > 1e-12:
                w = w / np.sum(np.abs(w))
            else:
                w = np.full(N, 1.0 / N)

        port_rets = R_demean @ w  # (T,)
        port_sq = port_rets ** 2   # (T,)
        port_cube = port_rets ** 3 # (T,)

        # Sample co-moments
        s_w = np.mean(R_demean * port_sq[:, None], axis=0)    # (N,)
        k_w = np.mean(R_demean * port_cube[:, None], axis=0) # (N,)

        return s_w, k_w

    def calculate_borrowing_cost_drag(
        self,
        leverage: float,
        borrowing_spread_bps: Optional[float] = None,
    ) -> float:
        """
        Calculates annualized borrowing spread drag: (L - 1) * spread for L > 1.0, 0 otherwise.
        """
        lev = float(leverage)
        if lev <= 1.0:
            return 0.0
        spread = (float(borrowing_spread_bps) / 10000.0) if borrowing_spread_bps is not None else self.borrow_spread
        return float((lev - 1.0) * spread)

    def calculate_leveraged_leland_buffer(
        self,
        delta_base: float,
        leverage: float,
    ) -> float:
        """
        Expands Leland dynamic buffer bandwidth by (1 + 0.40 * max(0, L - 1.0)) (Gate 4).
        """
        lev = float(leverage)
        expansion = 1.0 + 0.40 * max(0.0, lev - 1.0)
        return float(delta_base * expansion)

    def compute_fractional_kelly_weights(
        self,
        predicted_returns: np.ndarray,
        cov_matrix: np.ndarray,
        leverage: float,
        kappa: Optional[float] = None,
        max_single_stock: float = 0.05,
        max_sector_exposure: float = 0.25,
        asset_betas: Optional[np.ndarray] = None,
        coskewness: Optional[np.ndarray] = None,
        cokurtosis: Optional[np.ndarray] = None,
        returns_history: Optional[np.ndarray] = None,
        risk_free_rate: float = 0.03 / 252.0,
        sector_indices: Optional[Dict[str, List[int]]] = None,
        regime: Optional[str] = None,
    ) -> Tuple[np.ndarray, float]:
        """
        Computes multi-asset Fractional Kelly optimal portfolio weights (Feature F685, F686).
        Implements:
        - 4th-order fat-tail contraction (coskewness s(w) and cokurtosis k(w) penalties)
        - Single stock box cap (5.0% * leverage) via bounded simplex water-filling
        - Sector box cap (25.0% * leverage)
        - Strict portfolio beta clamping (beta_port <= 1.00 when leverage > 1.00)
        - Cash buffer calculation: w_cash = max(0.0, leverage - sum(w))

        Returns (weights, w_cash) satisfying sum(w) + w_cash == leverage with precision 1e-6.
        """
        p_rets = np.nan_to_num(np.asarray(predicted_returns, dtype=np.float64), nan=0.0)
        N = len(p_rets)
        if N == 0:
            return np.array([]), float(leverage)

        lev = float(leverage)
        cap_stock = float(max_single_stock * lev)
        cap_sector = float(max_sector_exposure * lev)

        # Resolve Fractional Kelly Kappa
        if kappa is not None:
            k = float(kappa)
        elif regime is not None:
            k = self.REGIME_FRACTIONAL_KELLY_KAPPA.get(str(regime).upper(), self.default_kappa)
        else:
            k = self.default_kappa

        # Compute higher-order co-moments if return history is available and not passed
        s_w = coskewness
        k_w = cokurtosis
        if (s_w is None or k_w is None) and returns_history is not None:
            s_w, k_w = self.compute_higher_order_co_moments(returns_history)

        # Effective expected return vector with 4th-order fat-tail contraction
        mu_eff = p_rets - float(risk_free_rate)
        if s_w is not None and len(s_w) == N:
            mu_eff = mu_eff + 0.5 * np.asarray(s_w, dtype=np.float64)
        if k_w is not None and len(k_w) == N:
            mu_eff = mu_eff - (1.0 / 6.0) * np.asarray(k_w, dtype=np.float64)

        # Unconstrained solve: w_raw = k * Sigma^-1 * mu_eff
        try:
            cov_reg = cov_matrix + 1e-6 * np.eye(N)
            w_raw = k * np.linalg.solve(cov_reg, mu_eff)
        except (np.linalg.LinAlgError, ValueError):
            try:
                w_raw = k * (np.linalg.pinv(cov_matrix) @ mu_eff)
            except Exception:
                w_raw = np.full(N, 1.0 / N)

        # Non-negativity rectification (long-only equity mandate)
        w_pos = np.maximum(0.0, w_raw)
        tot_pos = float(np.sum(w_pos))

        # Zero or all-negative return edge case: 100% Cash preservation
        if tot_pos <= 1e-12:
            return np.zeros(N), float(lev)

        # Initial scaling to target leverage
        w = (w_pos / tot_pos) * lev

        # Stage 1: Single-Stock Cap Water-Filling: w_i <= 0.05 * leverage
        for _ in range(N):
            over = w > (cap_stock + 1e-12)
            if not np.any(over):
                break
            excess = float(np.sum(w[over] - cap_stock))
            w[over] = cap_stock
            under = w < (cap_stock - 1e-12)
            if not np.any(under) or np.sum(w[under]) <= 1e-12:
                break
            w[under] += excess * (w[under] / np.sum(w[under]))

        w = np.clip(w, 0.0, cap_stock)

        # Stage 2: Sector Cap Water-Filling: sum(w_sector) <= 0.25 * leverage
        if sector_indices and isinstance(sector_indices, dict):
            for _ in range(N):
                sector_breached = False
                for sec_name, idx_list in sector_indices.items():
                    valid_idx = [i for i in idx_list if i < N]
                    if not valid_idx:
                        continue
                    sec_sum = float(np.sum(w[valid_idx]))
                    if sec_sum > cap_sector + 1e-9:
                        sector_breached = True
                        sec_excess = sec_sum - cap_sector
                        w[valid_idx] = w[valid_idx] * (cap_sector / sec_sum)
                        # Redistribute excess proportionally only to sectors with headroom
                        eligible_other_idx = []
                        for other_sec, other_idxs in sector_indices.items():
                            if other_sec == sec_name:
                                continue
                            v_other = [i for i in other_idxs if i < N]
                            if float(np.sum(w[v_other])) < cap_sector - 1e-9:
                                for i in v_other:
                                    if w[i] < cap_stock - 1e-9:
                                        eligible_other_idx.append(i)
                        if eligible_other_idx and np.sum(w[eligible_other_idx]) > 1e-12:
                            w[eligible_other_idx] += sec_excess * (w[eligible_other_idx] / np.sum(w[eligible_other_idx]))
                            w[eligible_other_idx] = np.clip(w[eligible_other_idx], 0.0, cap_stock)
                if not sector_breached:
                    break

            # Final clip to guarantee no sector exceeds cap_sector
            for sec_name, idx_list in sector_indices.items():
                valid_idx = [i for i in idx_list if i < N]
                if valid_idx:
                    sec_sum = float(np.sum(w[valid_idx]))
                    if sec_sum > cap_sector + 1e-9:
                        w[valid_idx] = w[valid_idx] * (cap_sector / sec_sum)

        w = np.clip(w, 0.0, cap_stock)

        # Stage 3: Strict Portfolio Beta Clamping (beta_port <= 1.00 when leverage > 1.00)
        if lev > 1.00 and asset_betas is not None:
            betas = np.nan_to_num(np.asarray(asset_betas, dtype=np.float64), nan=1.0)
            if len(betas) == N:
                port_beta = float(np.sum(w * betas))
                if port_beta > 1.000001:
                    w = w * (1.00 / port_beta)

        # Stage 4: Cash accounting & Simplex conservation
        tot_allocated = float(np.sum(w))
        w_cash = max(0.0, float(lev) - tot_allocated)

        return w, w_cash


# Complete class aliases for backwards compatibility and clean imports
FractionalKellyAllocator = DynamicRegimeLeverageAllocator
Phase141KellyAllocator = DynamicRegimeLeverageAllocator
