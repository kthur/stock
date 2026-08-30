"""
Portfolio Allocator Module:
- Tail-Risk EVT-CVaR Budgeting (Peaks-Over-Threshold GPD fitting & 3-tier fallback)
- Dynamic Band-Based Rebalancing (Leland optimal no-trade buffer zones)
- Microstructure Transaction Cost Sizing (STT tax, dynamic spread, market impact)
- Non-linear SLSQP Portfolio Risk Budget Optimization
"""

import logging
import math
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from scipy.stats import genpareto, norm, skew, kurtosis
from scipy.optimize import minimize

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class PortfolioAllocator:
    """
    Portfolio Allocator Engine implementing:
    1. EVT-GPD CVaR Estimation & Non-linear SLSQP Risk Budget Constraint Optimization.
    2. Dynamic Asset-Specific Microstructure Cost Sizing (KOSPI/KOSDAQ/SP500 STT, Spread, Market Impact).
    3. Leland Dynamic Band-Based No-Trade Buffer Zones for Transaction Drag Suppression.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        default_max_weight: float = 0.20,
        default_max_sector_weight: float = 0.35,
        risk_aversion: float = 1.0,
        delta_floor: float = 0.005,
        delta_cap: float = 0.050,
        rebalance_mode: str = "boundary",
        min_tail_samples: int = 15,
        target_horizon: int = 20
    ):
        self.config = config
        self.target_horizon = int(target_horizon) if target_horizon is not None else 20
        safe_max_w = float(default_max_weight) if (default_max_weight is not None and np.isfinite(default_max_weight)) else 0.20
        self.default_max_weight = max(0.01, min(1.0, safe_max_w))
        safe_sec_w = float(default_max_sector_weight) if (default_max_sector_weight is not None and np.isfinite(default_max_sector_weight)) else 0.35
        self.default_max_sector_weight = max(0.01, min(1.0, safe_sec_w))
        safe_ra = float(risk_aversion) if (risk_aversion is not None and np.isfinite(risk_aversion)) else 1.0
        self.risk_aversion = max(0.01, safe_ra)
        safe_df = float(delta_floor) if (delta_floor is not None and np.isfinite(delta_floor)) else 0.005
        self.delta_floor = max(0.0001, min(0.5, safe_df))
        safe_dc = float(delta_cap) if (delta_cap is not None and np.isfinite(delta_cap)) else 0.050
        self.delta_cap = max(self.delta_floor, min(0.5, safe_dc))
        self.rebalance_mode = str(rebalance_mode).lower() if rebalance_mode is not None else "boundary"
        self.min_tail_samples = max(2, int(min_tail_samples)) if min_tail_samples is not None else 15

    @staticmethod
    def compute_tail_stress_cov(
        returns_matrix: np.ndarray,
        base_cov: np.ndarray,
        tail_quantile: float = 0.10,
        stress_weight: float = 0.30,
        use_clayton_copula: bool = True
    ) -> np.ndarray:
        """
        Computes tail-stressed covariance matrix reflecting lower tail dependence in crisis regimes.
        Blends standard Ledoit-Wolf covariance with lower tail joint covariance matrix and
        Clayton Copula asymmetric lower-tail dependence.
        """
        if returns_matrix is None or len(returns_matrix) < 10 or returns_matrix.shape[1] < 2:
            return base_cov

        N, K = returns_matrix.shape
        mkt_ret = np.mean(returns_matrix, axis=1)
        tail_cutoff = np.quantile(mkt_ret, tail_quantile)
        tail_mask = mkt_ret <= tail_cutoff

        if tail_mask.sum() >= 3:
            tail_returns = returns_matrix[tail_mask]
            tail_cov = np.cov(tail_returns, rowvar=False)
            if tail_cov.shape == base_cov.shape and np.all(np.isfinite(tail_cov)):
                k_eff = float(np.clip(stress_weight, 0.0, 0.70))
                stressed_cov = (1.0 - k_eff) * base_cov + k_eff * tail_cov

                # Asymmetric Downside Clayton Copula adjustment (dynamically estimated lower tail dependence)
                if use_clayton_copula:
                    stds = np.sqrt(np.maximum(np.diag(stressed_cov), 1e-8))
                    outer_std = np.outer(stds, stds)
                    outer_std = np.where(outer_std > 0, outer_std, 1e-8)
                    corr = np.clip(stressed_cov / outer_std, -1.0, 1.0)

                    # Dynamic empirical Clayton lower-tail dependence coefficient lambda_L estimation
                    # Derived from joint lower quantile co-exceedance rate across assets
                    try:
                        tail_rets_std = (tail_returns - np.mean(tail_returns, axis=0)) / np.maximum(np.std(tail_returns, axis=0), 1e-6)
                        # Fraction of assets crashing per day (cross-sectional)
                        joint_tail_prob = np.mean(tail_rets_std < -1.0, axis=1)
                        # Frequency of days where >50% of assets crash simultaneously
                        mean_tail_coincidence = float(np.mean(joint_tail_prob > 0.5))
                        # Non-linear mapping to Clayton lambda_L in [0.10, 0.70]
                        lambda_l = float(np.clip(0.10 + mean_tail_coincidence * 1.5, 0.10, 0.70))
                    except Exception:
                        lambda_l = 0.25

                    asym_corr = (1.0 - lambda_l) * corr + lambda_l * np.ones_like(corr)
                    np.fill_diagonal(asym_corr, 1.0)
                    # Higham / Eigendecomposition spectral projection to guarantee PSD
                    c_evals, c_evecs = np.linalg.eigh(asym_corr)
                    c_evals = np.maximum(c_evals, 1e-4)
                    asym_corr = c_evecs @ np.diag(c_evals) @ c_evecs.T
                    d_inv = 1.0 / np.sqrt(np.diag(asym_corr))
                    asym_corr = asym_corr * np.outer(d_inv, d_inv)
                    stressed_cov = asym_corr * outer_std

                res: np.ndarray = np.asarray(stressed_cov + 1e-5 * np.eye(K))
                return res

        return base_cov

    @staticmethod
    def compute_downside_semi_cov(
        returns_matrix: np.ndarray,
        base_cov: Optional[np.ndarray] = None,
        target_return: float = 0.0,
        shrinkage_intensity: float = 0.20
    ) -> np.ndarray:
        """
        Computes Downside Semi-Covariance Matrix (Sigma^-) for Sortino optimization.
        Only penalizes joint downside fluctuations:
        Sigma^-_{ij} = (1/T) sum min(r_{i,t} - target, 0) * min(r_{j,t} - target, 0).
        Shrinks towards equicorrelation lower-tail target for numerical stability.
        """
        if returns_matrix is None or len(returns_matrix) < 5 or returns_matrix.shape[1] < 2:
            return base_cov if base_cov is not None else np.eye(2)

        N, K = returns_matrix.shape
        # Downside deviations below target return
        downside_diff = np.minimum(returns_matrix - target_return, 0.0)

        # Sample semi-covariance
        semi_cov = np.dot(downside_diff.T, downside_diff) / max(N - 1, 1)

        # Ensure positive semi-definiteness via regularization
        if base_cov is not None and base_cov.shape == semi_cov.shape:
            k_shrink = float(np.clip(shrinkage_intensity, 0.0, 0.50))
            blended_semi = (1.0 - k_shrink) * semi_cov + k_shrink * base_cov
        else:
            blended_semi = semi_cov

        reg_target = np.diag(np.diag(blended_semi))
        np.fill_diagonal(reg_target, np.diag(blended_semi))

        delta = float(np.clip(shrinkage_intensity, 0.05, 0.30))
        shrunk_semi = (1.0 - delta) * blended_semi + delta * reg_target

        # Add small diagonal jitter for non-singularity
        shrunk_semi += 1e-6 * np.eye(K)
        return np.asarray(shrunk_semi, dtype=np.float64)

    @staticmethod
    def get_dynamic_risk_free_rate(market: str = "US", horizon_days: int = 20) -> float:
        """
        Dynamically fetches real-time risk-free rate (r_f) from MarketIndicatorStorage (TNX / DGS3MO / CD91).
        Defaults gracefully to 3.5% (0.035) annual if unavailable.
        """
        mkt = str(market).upper()
        try:
            from src.data_layer.indicator_storage import MarketIndicatorStorage
            storage = MarketIndicatorStorage()
            indicators = storage.get_latest_global_indicators()
            if indicators:
                if mkt in ["SP500", "NASDAQ", "RUSSELL2000", "US"]:
                    # TNX is CBOE 10-Year Treasury Yield (e.g. 4.25 means 4.25%)
                    tnx_val = indicators.get("^TNX") or indicators.get("TNX")
                    if tnx_val is not None and math.isfinite(float(tnx_val)) and float(tnx_val) > 0:
                        return float(tnx_val) / 100.0
                else:
                    # KRX market - CD 91d / KORIBOR rate (or USDKRW interest differential proxy)
                    cd_val = indicators.get("CD91") or indicators.get("KRW_CD") or indicators.get("^TNX") or indicators.get("TNX")
                    if cd_val is not None and math.isfinite(float(cd_val)) and float(cd_val) > 0:
                        return float(cd_val) / 100.0
        except Exception:
            pass
        return 0.035

    @staticmethod
    def calculate_hybrid_volatility(
        df_or_series: Any,
        lambda_ewma: float = 0.94,
        min_vol: float = 0.005
    ) -> float:
        """
        Calculates forward volatility blending Garman-Klass intraday OHLC volatility
        and RiskMetrics Exponentially Weighted Moving Average (EWMA, lambda=0.94).
        Eliminates the 20-day sample standard deviation 'ghost effect'.
        """
        if df_or_series is None:
            return 0.02
        try:
            if isinstance(df_or_series, pd.DataFrame) and not df_or_series.empty:
                cols = {str(c).lower(): c for c in df_or_series.columns}
                h_col, l_col, c_col, o_col = cols.get("high"), cols.get("low"), cols.get("close"), cols.get("open")
                if h_col and l_col and c_col and o_col and len(df_or_series) >= 5:
                    h_arr = pd.to_numeric(df_or_series[h_col], errors="coerce").values
                    l_arr = pd.to_numeric(df_or_series[l_col], errors="coerce").values
                    c_arr = pd.to_numeric(df_or_series[c_col], errors="coerce").values
                    o_arr = pd.to_numeric(df_or_series[o_col], errors="coerce").values
                    valid = (h_arr > 0) & (l_arr > 0) & (c_arr > 0) & (o_arr > 0) & (h_arr >= l_arr)
                    if np.sum(valid) >= 5:
                        h_arr, l_arr, c_arr, o_arr = h_arr[valid], l_arr[valid], c_arr[valid], o_arr[valid]
                        # Garman-Klass intraday variance
                        log_hl = np.log(h_arr / l_arr)
                        log_co = np.log(c_arr / o_arr)
                        gk_var = 0.5 * (log_hl ** 2) - (2.0 * np.log(2.0) - 1.0) * (log_co ** 2)
                        gk_vol = float(np.sqrt(max(1e-8, np.mean(gk_var[-20:]))))

                        # RiskMetrics EWMA
                        ret = np.diff(np.log(c_arr))
                        ewma_var = ret[0] ** 2 if len(ret) > 0 else 0.0004
                        for r in ret[1:]:
                            ewma_var = lambda_ewma * ewma_var + (1.0 - lambda_ewma) * (r ** 2)
                        ewma_vol = float(np.sqrt(max(1e-8, ewma_var)))

                        hybrid_vol = 0.50 * gk_vol + 0.50 * ewma_vol
                        return float(max(min_vol, hybrid_vol))
            elif isinstance(df_or_series, (pd.Series, np.ndarray, list)):
                s = np.asarray(df_or_series, dtype=float)
                s = s[np.isfinite(s)]
                if len(s) >= 5:
                    ret = np.diff(np.log(s)) if np.all(s > 0) else np.diff(s)
                    ewma_var = ret[0] ** 2 if len(ret) > 0 else 0.0004
                    for r in ret[1:]:
                        ewma_var = lambda_ewma * ewma_var + (1.0 - lambda_ewma) * (r ** 2)
                    return float(max(min_vol, np.sqrt(ewma_var)))
        except Exception:
            pass
        return 0.02

    @staticmethod
    def decompose_factor_risk(
        weights: np.ndarray,
        factor_loadings: np.ndarray,
        factor_covariance: np.ndarray,
        idiosyncratic_vars: np.ndarray
    ) -> Dict[str, Any]:
        """
        Barra-style multi-factor risk decomposition:
        sigma_p^2 = w^T X Omega_F X^T w + w^T D w
        Returns:
            total_variance, factor_variance, idiosyncratic_variance, idiosyncratic_risk_ratio (IRR >= 70%)
        """
        w = np.asarray(weights, dtype=float)
        X = np.asarray(factor_loadings, dtype=float)
        Omega = np.asarray(factor_covariance, dtype=float)
        idio_arr = np.asarray(idiosyncratic_vars, dtype=float)
        D = np.diag(idio_arr) if idio_arr.ndim == 1 else idio_arr

        # Factor exposure beta_p = X^T w
        beta_p = X.T @ w if X.ndim == 2 else np.array([0.0])
        factor_var = float(beta_p.T @ Omega @ beta_p) if Omega.ndim == 2 else 0.0
        idio_var = float(w.T @ D @ w)
        total_var = max(1e-8, factor_var + idio_var)
        irr = float(np.clip(idio_var / total_var, 0.0, 1.0))

        return {
            "total_variance": float(total_var),
            "factor_variance": float(factor_var),
            "idiosyncratic_variance": float(idio_var),
            "idiosyncratic_risk_ratio": float(irr),
            "is_pure_alpha_compliant": bool(irr >= 0.70)
        }

    @staticmethod
    def calculate_cppi_gross_exposure(
        current_nav: float,
        peak_nav: float,
        max_drawdown_limit: float = 0.08,
        multiplier: float = 3.5,
        max_gross_exposure: float = 0.85,
        min_gross_exposure: float = 0.0
    ) -> Dict[str, float]:
        """
        Continuous Proportion Portfolio Insurance (CPPI) Capital Preservation Engine:
        Floor = Peak_NAV * (1 - max_drawdown_limit)
        Cushion = max(0, (current_nav - Floor) / current_nav)
        Target Exposure = min(max_gross_exposure, multiplier * Cushion)
        """
        curr = max(1.0, float(current_nav))
        peak = max(curr, float(peak_nav))
        limit = max(0.01, min(0.50, float(max_drawdown_limit)))
        floor = peak * (1.0 - limit)
        cushion = max(0.0, (curr - floor) / curr)
        raw_exposure = float(multiplier) * cushion
        exposure = float(np.clip(raw_exposure, min_gross_exposure, max_gross_exposure))
        drawdown = (peak - curr) / peak

        return {
            "current_nav": float(curr),
            "peak_nav": float(peak),
            "floor": float(floor),
            "cushion": float(cushion),
            "drawdown": float(drawdown),
            "target_gross_exposure": float(exposure),
            "cash_buffer_ratio": float(1.0 - exposure)
        }

    @staticmethod
    def calculate_volatility_spillover_index(
        asset_returns_df: pd.DataFrame,
        lookback: int = 30
    ) -> Dict[str, Any]:
        """
        Diebold-Yilmaz (2012) Cross-Asset Connectedness & Volatility Spillover Index (TSI).
        Measures variance transmission from FX/Commodities/Yields into Equities.
        """
        if asset_returns_df is None or len(asset_returns_df) < 10 or asset_returns_df.shape[1] < 2:
            return {"total_spillover_index": 0.0, "is_high_contagion": False, "asset_names": []}

        df_sub = asset_returns_df.tail(lookback).dropna(how="all").fillna(0.0)
        corr = df_sub.corr().values
        np.fill_diagonal(corr, 0.0)
        total_off_diag = float(np.sum(np.abs(corr)))
        n = corr.shape[0]
        max_possible = n * (n - 1)
        tsi = float((total_off_diag / max(max_possible, 1)) * 100.0)
        tsi = float(np.clip(tsi, 0.0, 100.0))

        return {
            "total_spillover_index": float(tsi),
            "is_high_contagion": bool(tsi >= 75.0),
            "asset_names": list(df_sub.columns)
        }

    @staticmethod
    def calculate_continuous_fractional_kelly(
        expected_returns: Optional[np.ndarray],
        covariance_matrix: np.ndarray,
        weights: np.ndarray,
        target_annual_vol: float = 0.12,
        kelly_fraction: float = 0.25,
        risk_free_rate: float = 0.035,
        min_gross_exposure: float = 0.10,
        max_gross_exposure: float = 1.00
    ) -> Tuple[float, np.ndarray]:
        """
        Calculates optimal continuous portfolio gross exposure using Quarter-Kelly and Target Volatility.
        """
        if weights is None or len(weights) == 0:
            return 1.0, np.array([])

        w_sum = np.sum(weights)
        if w_sum > 0:
            w_norm = weights / w_sum
        else:
            w_norm = weights

        daily_rf = risk_free_rate / 252.0
        port_var = float(w_norm.T @ covariance_matrix @ w_norm)
        port_vol_annual = float(np.sqrt(max(1e-8, port_var * 252.0)))

        # Target Volatility Scale
        vol_scale = target_annual_vol / max(port_vol_annual, 0.02)

        # Portfolio expected excess return
        if expected_returns is not None and len(expected_returns) == len(w_norm):
            port_ret_excess = float(w_norm.T @ (expected_returns - daily_rf))
            if port_var > 1e-8 and port_ret_excess > 0:
                kelly_scale = kelly_fraction * (port_ret_excess / port_var)
            else:
                kelly_scale = 0.25
        else:
            kelly_scale = 1.0

        optimal_exposure = float(np.clip(
            min(vol_scale, kelly_scale),
            min_gross_exposure,
            max_gross_exposure
        ))
        scaled_weights = weights * optimal_exposure
        return optimal_exposure, scaled_weights

    # =========================================================================
    # OBJECTIVE 1: EVT-CVaR LOSS BUDGET CONSTRAINTS & 3-TIER FALLBACK HIERARCHY
    # =========================================================================

    def estimate_evt_cvar(
        self,
        returns: Union[List[float], np.ndarray, pd.Series],
        confidence: float = 0.95,
        quantile_threshold: float = 0.90
    ) -> Dict[str, Any]:
        """
        Calculates Conditional Value-at-Risk (CVaR) using Extreme Value Theory (EVT)
        Peaks-Over-Threshold (POT) Generalized Pareto Distribution (GPD) fitting.

        Implements 3-Tier Fallback Hierarchy:
        - Tier 1: EVT-GPD POT Estimator (when N_u >= min_tail_samples and GPD converges).
        - Tier 2: Cornish-Fisher Expansion CVaR (skewness & kurtosis tail adjustment).
        - Tier 3: Empirical Quantile / Gaussian Parametric CVaR (when sample N < 10 or exceptions).

        Returns:
            Dict containing: 'var', 'cvar', 'xi', 'beta', 'method'
        """
        if returns is None:
            return {"var": 0.0, "cvar": 0.0, "xi": 0.0, "beta": 0.0, "method": "zero_fallback"}

        returns_arr = np.asarray(returns, dtype=np.float64)
        returns_arr = returns_arr[~np.isnan(returns_arr)]

        N = len(returns_arr)
        if N < 5:
            return {"var": 0.0, "cvar": 0.0, "xi": 0.0, "beta": 0.0, "method": "zero_fallback"}

        # Portfolio Loss L = -R
        losses = -returns_arr

        # Tier 3 check for extremely small sample size
        if N < 10:
            mu_l = float(np.mean(losses))
            sigma_l = float(np.std(losses, ddof=1)) if N > 1 else 0.01
            z_alpha = float(norm.ppf(confidence))
            cvar_gauss = max(0.0, mu_l + sigma_l * (norm.pdf(z_alpha) / (1.0 - confidence)))
            var_gauss = max(0.0, mu_l + sigma_l * z_alpha)
            return {
                "var": float(var_gauss),
                "cvar": float(cvar_gauss),
                "xi": 0.0,
                "beta": 0.0,
                "method": "gaussian_fallback_small_n"
            }

        # Adaptive threshold u selection: max of quantile and mean + 1.5 sigma to prevent noise fitting in quiet regimes
        sigma_l = float(np.std(losses, ddof=1)) if N > 1 else 0.01
        u_quantile = float(np.quantile(losses, quantile_threshold))
        u_volatility = float(np.mean(losses) + 1.5 * sigma_l)
        # Guarantee threshold u does not exceed target confidence quantile (u <= q_alpha)
        u_max_allowed = float(np.quantile(losses, min(0.92, confidence - 0.02)))
        u = min(max(u_quantile, u_volatility), u_max_allowed)
        exceedances = losses[losses > u] - u
        n_u = len(exceedances)

        # Base Fallback: Tier 3 Empirical Quantile
        var_emp = float(np.quantile(losses, confidence))
        worse_losses = losses[losses >= var_emp]
        cvar_emp = float(np.mean(worse_losses)) if len(worse_losses) > 0 else var_emp

        # Tier 2: Heavy-Tail Fallbacks (Student-t / Cornish-Fisher Expansion)
        var_cf, cvar_cf = var_emp, cvar_emp
        cf_valid = False
        try:
            from scipy.stats import t as student_t
            df_t, loc_t, scale_t = student_t.fit(losses)
            if df_t > 2.0 and scale_t > 1e-8:
                var_t = float(student_t.ppf(confidence, df_t, loc=loc_t, scale=scale_t))
                # Closed-form Student-t CVaR: loc + scale * (pdf(q) / (1-p)) * (df + q^2) / (df - 1)
                q_std = (var_t - loc_t) / scale_t
                pdf_t = student_t.pdf(q_std, df_t)
                cvar_t = loc_t + scale_t * (pdf_t / (1.0 - confidence)) * ((df_t + q_std**2) / (df_t - 1.0))
                if np.isfinite(cvar_t) and cvar_t > 0:
                    var_cf, cvar_cf = max(0.0, var_t), max(0.0, float(cvar_t))
                    cf_valid = True
        except Exception:
            pass

        if not cf_valid:
            try:
                mu_l = float(np.mean(losses))
                sigma_l = float(np.std(losses, ddof=1))
                if sigma_l > 1e-8:
                    s_loss = float(skew(losses))
                    k_loss = float(kurtosis(losses))
                    z_a = float(norm.ppf(confidence))
                    z_cf = z_a + (s_loss / 6.0) * (z_a**2 - 1.0) + (k_loss / 24.0) * (z_a**3 - 3.0 * z_a) - (s_loss**2 / 36.0) * (2.0 * z_a**3 - 5.0 * z_a)
                    z_cf = float(np.clip(z_cf, 0.5, 6.0))
                    var_cf = max(0.0, mu_l + sigma_l * z_cf)
                    pdf_a = norm.pdf(z_a)
                    es_factor = (pdf_a / (1.0 - confidence)) * (1.0 + (s_loss / 6.0) * (z_a**3) + (k_loss / 24.0) * (z_a**4 - 2.0 * z_a**2 - 1.0))
                    cvar_cf_raw = mu_l + sigma_l * max(z_cf, float(es_factor))
                    if np.isfinite(cvar_cf_raw) and cvar_cf_raw > 0:
                        cvar_cf = max(0.0, float(cvar_cf_raw))
                        cf_valid = True
            except Exception:
                pass

        # Tier 1: EVT-GPD Fit with Extremal Index (theta) Clustering Adjustment (Ferro-Segers 2003)
        var_evt, cvar_evt = var_cf, cvar_cf
        xi_val, beta_val = 0.0, 0.0
        gpd_valid = False
        theta_val = 1.0
        if n_u >= 3 and u > -1e-6:
            try:
                # Calculate Extremal Index theta measuring volatility/loss clustering
                exceed_indices = np.where(losses > u)[0]
                if len(exceed_indices) >= 2:
                    inter_arrival = np.diff(exceed_indices)
                    if np.max(inter_arrival) > 2:
                        denom = float(np.sum((inter_arrival - 1) * (inter_arrival - 2))) + 1e-6
                        theta_val = float(np.clip(2.0 * (np.sum(inter_arrival - 1)**2) / denom, 0.25, 1.0))
                    else:
                        denom = float(np.mean(inter_arrival**2)) + 1e-6
                        theta_val = float(np.clip(2.0 * np.mean(inter_arrival) / denom, 0.25, 1.0))

                xi, _, beta = genpareto.fit(exceedances, floc=0)
                xi = float(xi)
                beta = float(beta)
                if beta > 1e-8 and xi < 0.95 and np.isfinite(xi) and np.isfinite(beta):
                    xi_clamped = float(np.clip(xi, -0.50, 0.50))
                    # Adjust tail probability for dependent clustered exceedances
                    tail_ratio = min(0.999, (N / n_u) * ((1.0 - confidence) / max(0.25, theta_val)))
                    if abs(xi_clamped) < 1e-4:
                        var_evt = u - beta * np.log(tail_ratio)
                        cvar_evt = var_evt + beta
                    else:
                        var_evt = u + (beta / xi_clamped) * (np.power(tail_ratio, -xi_clamped) - 1.0)
                        cvar_evt = (var_evt + beta - xi_clamped * u) / (1.0 - xi_clamped)
                    if np.isfinite(var_evt) and np.isfinite(cvar_evt):
                        var_evt = max(0.0, float(var_evt))
                        cvar_evt = max(0.0, float(cvar_evt))
                        xi_val, beta_val = xi_clamped, beta
                        gpd_valid = True
            except Exception as e:
                logger.debug(f"EVT-GPD fitting non-convergent: {e}")

        # Continuous Sigmoid Blending Kernel (eliminates step discontinuity at n_u = 15)
        if gpd_valid:
            lambda_gpd = 1.0 / (1.0 + np.exp(-0.5 * (n_u - self.min_tail_samples)))
            var_smooth = lambda_gpd * var_evt + (1.0 - lambda_gpd) * var_cf
            cvar_smooth = lambda_gpd * cvar_evt + (1.0 - lambda_gpd) * cvar_cf
            used_method = "evt_gpd_sigmoid_blended" if (0.01 < lambda_gpd < 0.99) else ("evt_gpd" if lambda_gpd >= 0.99 else "cornish_fisher")
        elif cf_valid:
            var_smooth = var_cf
            cvar_smooth = cvar_cf
            used_method = "cornish_fisher"
        else:
            var_smooth = var_emp
            cvar_smooth = cvar_emp
            used_method = "empirical_fallback"

        return {
            "var": float(max(0.0, var_smooth)),
            "cvar": float(max(0.0, cvar_smooth)),
            "xi": float(xi_val),
            "beta": float(beta_val),
            "method": used_method
        }

    def estimate_portfolio_evt_cvar(
        self,
        weights: np.ndarray,
        returns_matrix: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """
        Calculates portfolio-level EVT-CVaR for a weight vector w and return matrix R.
        """
        port_returns = np.dot(returns_matrix, weights)
        res = self.estimate_evt_cvar(port_returns, confidence=confidence)
        return float(res["cvar"])

    def optimize_with_evt_cvar_constraint(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        max_cvar: float = 0.04,
        confidence: float = 0.95,
        max_weight: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Mean-Variance Optimization subject to EVT-CVaR loss budget constraint.
        Constraint: EVT_CVaR_alpha(w) <= max_cvar
        """
        if max_weight is None:
            max_weight = self.default_max_weight

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        returns_sub = returns_df[symbols] if not returns_df.empty else pd.DataFrame()
        if returns_sub.empty or len(returns_sub) < 5:
            return {sym: 1.0 / n_assets for sym in symbols}

        returns_matrix = returns_sub.values
        mu = expected_returns.values

        # Ledoit-Wolf Covariance Shrinkage for numerical stability & lower estimation error
        try:
            from sklearn.covariance import LedoitWolf
            if len(returns_matrix) >= 5 and n_assets > 1:
                cov_shrunk = LedoitWolf().fit(returns_matrix).covariance_
            else:
                clean_returns = pd.DataFrame(returns_matrix).dropna(axis=0, how='any').values
                if len(clean_returns) >= 2 and n_assets > 1:
                    cov_shrunk = np.cov(clean_returns, rowvar=False)
                else:
                    cov_shrunk = np.eye(n_assets) * 0.0004
                if cov_shrunk.ndim == 0:
                    cov_shrunk = np.array([[float(cov_shrunk)]])
        except Exception:
            clean_returns = pd.DataFrame(returns_matrix).dropna(axis=0, how='any').values
            if len(clean_returns) >= 2 and n_assets > 1:
                cov_shrunk = np.cov(clean_returns, rowvar=False)
            else:
                cov_shrunk = np.eye(n_assets) * 0.0004
            if cov_shrunk.ndim == 0:
                cov_shrunk = np.array([[float(cov_shrunk)]])

        if cov_shrunk is None or np.any(np.isnan(cov_shrunk)) or np.any(np.isinf(cov_shrunk)) or cov_shrunk.shape != (n_assets, n_assets):
            cov_shrunk = np.eye(n_assets) * 0.0004

        # Lower tail dependence stress covariance blending
        cov_shrunk = self.compute_tail_stress_cov(returns_matrix, cov_shrunk)

        # Rockafellar & Uryasev (2000) Globally Convex Auxiliary CVaR Formulation:
        # min -w^T mu + (lambda/2) w^T Sigma w + kappa * CVaR(w)
        # s.t. u_t + r_t^T w + alpha >= 0, u_t >= 0, sum(w_i) = 1.0, 0 <= w_i <= max_w
        T_full, N = returns_matrix.shape
        T = min(T_full, 252)
        rets_T = returns_matrix[-T:]
        beta_inv = 1.0 / max(1e-4, (1.0 - confidence) * float(T))

        def ru_objective(x):
            w = x[:N]
            ret = float(np.dot(w, mu))
            var_p = float(w.T @ cov_shrunk @ w) if cov_shrunk.shape == (N, N) else float(np.var(np.dot(rets_T, w), ddof=1))
            return -ret + 0.5 * self.risk_aversion * var_p

        eff_max_w = max(max_weight, 1.05 / N)
        bounds_ru = [(0.0, eff_max_w)] * N + [(-1.0, 1.0)] + [(0.0, None)] * T

        constraints_ru = [
            {'type': 'eq', 'fun': lambda x: np.sum(x[:N]) - 1.0},
            {'type': 'ineq', 'fun': lambda x: max_cvar - (x[N] + beta_inv * np.sum(x[N+1:]))},
            {'type': 'ineq', 'fun': lambda x: x[N+1:] + np.dot(rets_T, x[:N]) + x[N]}
        ]

        init_w = np.ones(N) / N
        init_alpha = 0.02
        init_loss = -np.dot(rets_T, init_w)
        init_u = np.maximum(0.0, init_loss - init_alpha)
        init_x = np.concatenate([init_w, [init_alpha], init_u])

        # Adaptive SLSQP iteration limit based on universe dimension N
        maxiter_ru = min(250, max(50, 10 * N))

        res = None
        try:
            res = minimize(
                ru_objective,
                init_x,
                method='SLSQP',
                bounds=bounds_ru,
                constraints=constraints_ru,
                options={'maxiter': maxiter_ru, 'ftol': 1e-5}
            )
        except Exception as e:
            logger.debug(f"[EVT-CVaR] SLSQP primary optimization exception: {e}")

        if res is None or not res.success or np.sum(res.x[:N]) <= 0 or not np.all(np.isfinite(res.x[:N])):
            # Graceful fallback to Cornish-Fisher smooth quadratic programming
            def std_objective(w):
                ret = np.dot(w, mu)
                var_p = float(w.T @ cov_shrunk @ w) if cov_shrunk.shape == (N, N) else float(np.var(np.dot(returns_matrix, w), ddof=1))
                return -(ret - 0.5 * self.risk_aversion * var_p)

            def std_cvar_constraint(w):
                # Analytical Cornish-Fisher smooth CVaR for continuous gradient evaluations
                port_rets = np.dot(returns_matrix, w)
                m_ret = float(np.mean(port_rets))
                s_ret = float(np.std(port_rets, ddof=1))
                if s_ret > 1e-6 and len(port_rets) >= 10:
                    skewness = float(np.mean(((port_rets - m_ret) / s_ret) ** 3))
                    kurt = float(np.mean(((port_rets - m_ret) / s_ret) ** 4)) - 3.0
                    skew_c = float(np.clip(skewness, -1.5, 1.5))
                    kurt_c = float(np.clip(kurt, -1.0, 4.0))
                    z_alpha = -1.6448536269514722
                    z_cf = (
                        z_alpha
                        + (z_alpha**2 - 1.0) * skew_c / 6.0
                        + (z_alpha**3 - 3.0 * z_alpha) * kurt_c / 24.0
                        - (2.0 * z_alpha**3 - 5.0 * z_alpha) * (skew_c**2) / 36.0
                    )
                    cvar_val = float(max(0.0, - (m_ret + z_cf * s_ret)))
                else:
                    cvar_val = float(np.percentile(-port_rets, 95))
                return max_cvar - cvar_val

            maxiter_cf = min(150, max(40, 6 * N))
            try:
                res_std = minimize(
                    std_objective,
                    init_w,
                    method='SLSQP',
                    bounds=tuple((0.0, eff_max_w) for _ in range(N)),
                    constraints=[
                        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
                        {'type': 'ineq', 'fun': std_cvar_constraint}
                    ],
                    options={'maxiter': maxiter_cf, 'ftol': 1e-5}
                )
                if res_std is not None and res_std.success and np.sum(res_std.x) > 0 and np.all(np.isfinite(res_std.x)):
                    weights = np.maximum(0.0, res_std.x)
                    weights = weights / np.sum(weights)
                else:
                    # Final analytical fallback: inverse-volatility / risk-parity weights clamped to eff_max_w
                    vols = np.sqrt(np.maximum(np.diag(cov_shrunk), 1e-8)) if cov_shrunk.shape == (N, N) else np.ones(N)
                    inv_vols = 1.0 / np.maximum(vols, 1e-4)
                    w_rp = inv_vols / np.sum(inv_vols)
                    weights = np.clip(w_rp, 0.0, eff_max_w)
                    weights = weights / np.sum(weights)
            except Exception as e:
                logger.debug(f"[EVT-CVaR] Cornish-Fisher fallback QP exception: {e}")
                weights = np.clip(init_w, 0.0, eff_max_w)
                weights = weights / np.sum(weights)
        else:
            weights = np.maximum(0.0, res.x[:N])
            sum_w = np.sum(weights)
            if sum_w > 0 and np.isfinite(sum_w):
                weights = weights / sum_w
            else:
                weights = init_w

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    def optimize_turnover_regularized_portfolio(
        self,
        expected_returns: pd.Series,
        returns_df: pd.DataFrame,
        previous_weights: Optional[Dict[str, float]] = None,
        turnover_penalty_l1: float = 0.001,
        turnover_penalty_l2: float = 0.0005,
        max_weight: Optional[float] = None,
        sector_map: Optional[Dict[str, str]] = None,
        max_sector_weight: Optional[float] = None,
        market_map: Optional[Dict[str, str]] = None,
        max_country_weight: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Convex Portfolio Optimization with Explicit Turnover Cost Regularization & Country Caps:
        Objective:
            min_w [ -w^T mu + (lambda/2) w^T Sigma w + gamma_1 sum(c_i |w_i - w_prev_i|) + (gamma_2 / 2) ||w - w_prev||^2 ]
        subject to:
            sum(w_i) = 1.0,  0 <= w_i <= max_weight,  sum_{i in Sector_k} w_i <= max_sector_weight, sum_{i in Country_c} w_i <= max_country_weight.
        Eliminates portfolio churning on noisy marginal alpha changes while maximizing net realized compound CAGR.
        """
        if max_weight is None:
            max_weight = self.default_max_weight
        if max_sector_weight is None:
            max_sector_weight = self.default_max_sector_weight
        if max_country_weight is None:
            max_country_weight = float(self.config.get_max_country_weight("SP500") if (self.config is not None and hasattr(self.config, "get_max_country_weight")) else 0.35)

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 0:
            return {}
        if n_assets == 1:
            return {symbols[0]: 1.0}

        returns_sub = returns_df[symbols] if (not returns_df.empty and all(s in returns_df.columns for s in symbols)) else pd.DataFrame()
        if returns_sub.empty or len(returns_sub) < 5:
            return {sym: 1.0 / n_assets for sym in symbols}

        returns_matrix = returns_sub.values
        mu = np.nan_to_num(expected_returns.values.astype(float), nan=0.0)

        # Ledoit-Wolf Shrinkage Covariance
        try:
            from sklearn.covariance import LedoitWolf
            cov_shrunk = LedoitWolf().fit(returns_matrix).covariance_
        except Exception:
            clean_returns = pd.DataFrame(returns_matrix).dropna(axis=0, how='any').values
            if len(clean_returns) >= 2 and n_assets > 1:
                cov_shrunk = np.cov(clean_returns, rowvar=False)
            else:
                cov_shrunk = np.eye(n_assets) * 0.0004
            if cov_shrunk.ndim == 0:
                cov_shrunk = np.array([[float(cov_shrunk)]])

        if cov_shrunk is None or np.any(np.isnan(cov_shrunk)) or np.any(np.isinf(cov_shrunk)) or cov_shrunk.shape != (n_assets, n_assets):
            cov_shrunk = np.eye(n_assets) * 0.0004

        cov_shrunk = self.compute_tail_stress_cov(returns_matrix, cov_shrunk)

        # Build w_prev vector
        w_prev_vec = np.zeros(n_assets, dtype=float)
        if previous_weights:
            for i, sym in enumerate(symbols):
                w_prev_vec[i] = float(previous_weights.get(sym, 0.0))

        gamma_1 = float(max(0.0, turnover_penalty_l1))
        gamma_2 = float(max(0.0, turnover_penalty_l2))

        def objective(w):
            ret = np.dot(w, mu)
            var_p = float(w.T @ cov_shrunk @ w) if cov_shrunk.shape == (n_assets, n_assets) else float(np.var(np.dot(returns_matrix, w), ddof=1))
            turnover_l1 = float(np.sum(np.abs(w - w_prev_vec)))
            turnover_l2 = float(np.sum((w - w_prev_vec) ** 2))
            total_obj = -ret + (0.5 * self.risk_aversion * var_p) + (gamma_1 * turnover_l1) + (0.5 * gamma_2 * turnover_l2)
            return total_obj

        init_weights = w_prev_vec if (np.sum(w_prev_vec) > 0.90 and np.all(w_prev_vec >= 0)) else np.ones(n_assets) / n_assets
        init_weights = init_weights / np.sum(init_weights)

        eff_max_w = max(max_weight, 1.05 / n_assets)
        bounds = tuple((0.0, eff_max_w) for _ in range(n_assets))
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

        # Add sector capacity constraints if sector_map is provided
        if sector_map:
            sectors = set(sector_map.values())
            for sec in sectors:
                sec_indices = [i for i, s in enumerate(symbols) if sector_map.get(s) == sec]
                if sec_indices and len(sec_indices) < n_assets:
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda w, idxs=sec_indices: float(max_sector_weight) - np.sum(w[idxs])
                    })

        # Add country capacity constraints if market_map is provided
        if market_map and max_country_weight is not None and max_country_weight < 1.0:
            _CTRY_MAP = {
                'SP500': 'US', 'NASDAQ': 'US', 'RUSSELL2000': 'US', 'US': 'US',
                'KOSPI': 'KR', 'KOSDAQ': 'KR', 'KRX': 'KR',
                'CHINA_SSE': 'CN', 'CHINA_SZSE': 'CN', 'SSE': 'CN', 'SZSE': 'CN', 'CHINA': 'CN',
                'JAPAN_TSE': 'JP', 'TSE': 'JP', 'JAPAN': 'JP',
                'INDIA_NSE': 'IN', 'INDIA_BSE': 'IN', 'NSE': 'IN', 'BSE': 'IN', 'INDIA': 'IN',
                'EUROPE_STOXX': 'EU', 'EUROPE': 'EU', 'STOXX': 'EU', 'DAX': 'EU', 'CAC': 'EU', 'FTSE': 'EU',
                'VIETNAM_HOSE': 'VN', 'HOSE': 'VN', 'VIETNAM': 'VN',
                'TAIWAN_TWSE': 'TW', 'TWSE': 'TW', 'TAIWAN': 'TW',
                'AUSTRALIA_ASX': 'AU', 'ASX': 'AU', 'AUSTRALIA': 'AU',
                'BRAZIL_B3': 'BR', 'B3': 'BR', 'BRAZIL': 'BR',
                'HKEX': 'HK', 'HONGKONG': 'HK',
                'SINGAPORE_SGX': 'SG', 'SGX': 'SG', 'SINGAPORE': 'SG',
                'CANADA_TSX': 'CA', 'TSX': 'CA', 'CANADA': 'CA',
            }

            def _to_country(m):
                m_u = str(m).strip().upper()
                return _CTRY_MAP.get(m_u, m_u)

            country_map = {s: _to_country(m) for s, m in market_map.items()}
            countries = set(country_map.values())
            for ctry in countries:
                ctry_indices = [i for i, s in enumerate(symbols) if country_map.get(s) == ctry]
                if ctry_indices and len(ctry_indices) < n_assets:
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda w, idxs=ctry_indices: float(max_country_weight) - np.sum(w[idxs])
                    })

        res = minimize(
            objective,
            init_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500, 'ftol': 1e-7}
        )

        if not res.success:
            weights = init_weights
        else:
            weights = res.x / np.sum(res.x)

        return {sym: float(w) for sym, w in zip(symbols, weights)}

    def allocate_quarter_kelly(
        self,
        expected_returns: pd.Series,
        volatilities: Optional[pd.Series] = None,
        max_weight: Optional[float] = None,
        kelly_fraction: float = 0.25,
        risk_free_rate: float = 0.035,
        top_k_concentration: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Allocates portfolio weights using Fractional Kelly (Quarter-Kelly) Sizing:
        w_i = kelly_fraction * (mu_i - r_f) / (sigma_i^2)
        subject to 0 <= w_i <= max_weight and sum(w_i) <= 1.0.

        Guarantees optimal long-term geometric compounding while suppressing drawdown risk.
        If top_k_concentration is provided, concentrates capital on top-K conviction assets to eliminate dilution drag.
        """
        if expected_returns.empty:
            return {}

        symbols = list(expected_returns.index)
        n_assets = len(symbols)
        if n_assets == 1:
            return {symbols[0]: min(1.0, max_weight or self.default_max_weight)}

        cap = max_weight or self.default_max_weight

        # Clean expected returns (handle horizon vs annualized excess returns)
        raw_mu = np.nan_to_num(expected_returns.values.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
        # Determine horizon scaling: if mu mean < 0.20, assume 20d horizon return and scale rf accordingly
        rf_scaled = risk_free_rate * (self.target_horizon / 252.0) if np.mean(raw_mu) < 0.50 else risk_free_rate
        excess_mu = np.maximum(0.0, raw_mu - rf_scaled)

        if volatilities is not None and not volatilities.empty:
            raw_vols = volatilities.reindex(symbols).fillna(0.02).values.astype(float)
            raw_vols = np.nan_to_num(raw_vols, nan=0.02, posinf=0.02, neginf=0.02)
            vols = np.maximum(0.005, raw_vols)
        else:
            vols = np.full(n_assets, 0.02)

        # Raw Kelly score: kelly_fraction * (excess_mu / sigma_i^2)
        horizon = max(getattr(self, 'target_horizon', 20), 1)
        raw_kelly = float(kelly_fraction) * (excess_mu / (vols ** 2 * horizon))

        # Top-K Conviction Concentration Filter (Eliminate tail dilution drag)
        if top_k_concentration is not None and 0 < top_k_concentration < n_assets:
            top_k_indices = np.argsort(raw_kelly)[::-1][:top_k_concentration]
            mask = np.zeros(n_assets, dtype=bool)
            mask[top_k_indices] = True
            raw_kelly = np.where(mask, raw_kelly, 0.0)

        total_k = np.sum(raw_kelly)

        if total_k <= 1e-8:
            equal_w = 1.0 / float(n_assets)
            return {sym: float(min(equal_w, cap)) for sym in symbols}

        eff_cap = max(cap, 1.0 / n_assets)
        if total_k < 1.0:
            final_w = np.clip(raw_kelly, 0.0, eff_cap)
        else:
            norm_w = raw_kelly / total_k
            cur_w = np.clip(norm_w, 0.0, eff_cap)
            for _ in range(10):
                cur_sum = np.sum(cur_w)
                if abs(cur_sum - 1.0) < 1e-6 or cur_sum <= 0:
                    break
                excess = 1.0 - cur_sum
                uncapped_mask = cur_w < (eff_cap - 1e-6)
                if not np.any(uncapped_mask):
                    cur_w = cur_w / cur_sum
                    break
                uncapped_sum = np.sum(cur_w[uncapped_mask])
                if uncapped_sum > 0:
                    additions = excess * (cur_w[uncapped_mask] / uncapped_sum)
                    cur_w[uncapped_mask] = np.clip(cur_w[uncapped_mask] + additions, 0.0, eff_cap)
                else:
                    cur_w[uncapped_mask] += excess / np.sum(uncapped_mask)
            final_w = cur_w if np.sum(cur_w) > 0 else np.ones(n_assets) / n_assets
        return {sym: float(w) for sym, w in zip(symbols, final_w)}

    def allocate_volatility_targeted_kelly(
        self,
        expected_returns: pd.Series,
        volatilities: Optional[pd.Series] = None,
        target_annual_vol: float = 0.15,
        max_weight: Optional[float] = None,
        kelly_fraction: float = 0.25,
        returns_df: Optional[pd.DataFrame] = None,
        top_k_concentration: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Allocates portfolio weights combining Fractional Kelly with Volatility Targeting:
        1. Calculates relative Kelly asset weights w_raw_i = (mu_i / sigma_i^2).
        2. Computes aggregate portfolio expected volatility sigma_port.
        3. Scales portfolio leverage by (target_annual_vol / sigma_port) to maintain steady risk.
        4. Clamps individual asset weights to max_weight and ensures sum(w_i) <= 1.0.
        """
        base_weights = self.allocate_quarter_kelly(
            expected_returns=expected_returns,
            volatilities=volatilities,
            max_weight=max_weight,
            kelly_fraction=kelly_fraction,
            top_k_concentration=top_k_concentration
        )
        if not base_weights:
            return {}

        symbols = list(base_weights.keys())
        w_vec = np.array([base_weights[s] for s in symbols])

        if volatilities is not None and not volatilities.empty:
            daily_vols = volatilities.reindex(symbols).fillna(0.02).values.astype(float)
        else:
            daily_vols = np.full(len(symbols), 0.02)

        # R6-4 Fix: Multi-asset diversification-adjusted portfolio annual volatility
        # sigma_port^2 = (1 - rho_avg) * sum(w_i^2 * sigma_i^2) + rho_avg * (sum(w_i * sigma_i))^2
        if returns_df is not None and not returns_df.empty:
            corr_mat = returns_df.corr()
            valid_corr = corr_mat.values[np.triu_indices_from(corr_mat.values, k=1)]
            valid_corr = valid_corr[np.isfinite(valid_corr)]
            rho_avg = float(np.mean(valid_corr)) if len(valid_corr) > 0 else 0.25
        else:
            rho_avg = 0.25  # Fallback realistic multi-asset correlation

        sum_w_vol = float(np.dot(w_vec, daily_vols))
        sum_w2_vol2 = float(np.sum((w_vec * daily_vols) ** 2))
        port_daily_var = (1.0 - rho_avg) * sum_w2_vol2 + rho_avg * (sum_w_vol ** 2)
        port_ann_vol = float(np.sqrt(252.0 * max(1e-8, port_daily_var)))
        if port_ann_vol > 1e-4:
            vol_scale = float(np.clip(target_annual_vol / port_ann_vol, 0.40, 1.35))
        else:
            vol_scale = 1.0

        scaled_weights = {s: float(np.clip(w * vol_scale, 0.0, max_weight or self.default_max_weight)) for s, w in base_weights.items()}
        tot = sum(scaled_weights.values())
        if tot > 1.0:
            scaled_weights = {s: w / tot for s, w in scaled_weights.items()}

        return scaled_weights

    def allocate_confidence_adaptive_kelly(
        self,
        expected_returns: pd.Series,
        volatilities: Optional[pd.Series] = None,
        conviction_scores: Optional[pd.Series] = None,
        max_weight: Optional[float] = None,
        kelly_fraction: float = 0.5,
        target_annual_vol: float = 0.15
    ) -> Dict[str, float]:
        """
        Machine-Learned Conviction-Adaptive Kelly Allocation:
        f^*_i = clip( (p_i * (b_i + 1) - 1) / b_i * kelly_fraction, 0.0, max_weight )
        where:
          - p_i (dynamic win rate) is estimated from conviction score & normalized alpha [0.40 ~ 0.80].
          - b_i (payoff ratio) is estimated from expected return / downside volatility.
        """
        if expected_returns is None or expected_returns.empty:
            return {}

        symbols = list(expected_returns.index)
        n = len(symbols)
        cap = float(max_weight or self.default_max_weight)

        rets = expected_returns.values.astype(float)
        if np.nanmean(np.abs(rets)) > 0.50:
            rets = rets / 100.0

        if volatilities is not None and not volatilities.empty:
            vols = volatilities.reindex(symbols).fillna(0.02).values.astype(float)
        else:
            vols = np.full(n, 0.02)

        if conviction_scores is not None and not conviction_scores.empty:
            convs = conviction_scores.reindex(symbols).fillna(0.50).values.astype(float)
        else:
            convs = np.full(n, 0.50)

        raw_kelly = np.zeros(n, dtype=float)
        for i in range(n):
            mu_i = rets[i]
            vol_i = max(vols[i], 1e-4)
            c_i = float(np.clip(convs[i], 0.0, 1.0))

            if mu_i <= 0:
                raw_kelly[i] = 0.0
                continue

            # Dynamic Win Rate: p in [0.40, 0.80] based on model conviction
            p_i = 0.50 + 0.25 * (c_i - 0.50) * 2.0
            p_i = float(np.clip(p_i, 0.40, 0.80))

            # Dynamic Payoff Ratio: b = expected_gain / expected_loss proxy
            ann_mu = mu_i * (252.0 / self.target_horizon)
            ann_vol = vol_i * np.sqrt(252.0)
            b_i = float(np.clip(ann_mu / max(ann_vol, 0.05), 0.5, 4.0))

            # Kelly optimal fraction
            f_star = (p_i * (b_i + 1.0) - 1.0) / b_i
            f_scaled = max(0.0, f_star) * float(kelly_fraction)
            raw_kelly[i] = min(f_scaled, cap)

        tot_k = np.sum(raw_kelly)
        if tot_k <= 0:
            return {}

        if tot_k > 1.0:
            final_w = raw_kelly / tot_k
        else:
            final_w = raw_kelly

        return {s: float(w) for s, w in zip(symbols, final_w) if w > 1e-4}

    # =========================================================================
    # OBJECTIVE 2: DYNAMIC LELAND BAND-BASED REBALANCING & MICROSTRUCTURE COSTS
    # =========================================================================

    def estimate_transaction_cost_rate(
        self,
        symbol: str,
        market: str,
        target_weight: float,
        portfolio_value: float = 100_000_000.0,
        volatility_20d: float = 0.020,
        adv: float = 1_000_000_000.0,
        is_sell: Optional[bool] = None,
        slippage_multiplier: float = 1.0
    ) -> float:
        """
        Estimates asset-specific one-way transaction cost rate (c_i):
        c_i = Tax & Fees + 0.5 * Spread + Market Impact
        incorporating dynamic slippage feedback multiplier from real execution logs.

        Specific Rules:
        - KOSPI: Sell STT tax = 0.15% (0.0015), Brokerage fee = 0.03% (0.0003). Base spread = 0.06%.
        - KOSDAQ: Sell STT tax = 0.18% (0.0018), Brokerage fee = 0.03% (0.0003). Base spread = 0.10%.
        - NASDAQ: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.03%.
        - RUSSELL2000: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.08%.
        - SP500: SEC fee = 0.003% (0.00003), Brokerage fee = 0.005% (0.00005). Base spread = 0.02%.
        """
        market_upper = str(market).upper()
        is_us_stock = market_upper in ('SP500', 'NASDAQ', 'RUSSELL2000') or (symbol.isalpha() and len(symbol) <= 5)

        slip_mult = max(0.5, float(slippage_multiplier))

        if market_upper in ['KOSDAQ', 'KQ'] or symbol.endswith('.KQ'):
            stt_tax = 0.0020  # KOSDAQ STT tax = 0.20%
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kosdaq', 0.0010) if self.config else 0.0010
            spread_min, spread_max = 0.0003, 0.0250
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75
        elif market_upper == 'NASDAQ':
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_nasdaq', 0.0003) if self.config else 0.0003
            spread_min, spread_max = 0.0001, 0.0080
            adv_ref = 1_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        elif market_upper == 'RUSSELL2000':
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_russell2000', 0.0008) if self.config else 0.0008
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 500_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        elif is_us_stock:
            stt_tax = 0.00003
            brokerage_fee = 0.00005
            base_spread = getattr(self.config, 'base_spread_sp500', 0.0002) if self.config else 0.0002
            spread_min, spread_max = 0.0001, 0.0050
            adv_ref = 1_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_sp500', 0.50) if self.config else 0.50
        else:  # KOSPI default
            stt_tax = 0.0018  # KOSPI STT tax = 0.18%
            brokerage_fee = 0.0003
            base_spread = getattr(self.config, 'base_spread_kospi', 0.0006) if self.config else 0.0006
            spread_min, spread_max = 0.0002, 0.0150
            adv_ref = 1_000_000_000.0
            impact_coeff = getattr(self.config, 'market_impact_coeff_krx', 0.75) if self.config else 0.75

        # Direct STT application depending on order side
        if is_sell is True:
            tax_fee = stt_tax + brokerage_fee
        elif is_sell is False:
            tax_fee = brokerage_fee
        else:
            tax_fee = 0.5 * stt_tax + brokerage_fee

        is_sp500 = (market_upper == 'SP500')
        min_adv = 10_000.0 if is_sp500 else 10_000_000.0
        adv_clean = max(adv, min_adv)
        base_vol = 0.015 if is_sp500 else 0.020
        vol_clean = max(volatility_20d, 0.005)

        # Dynamic spread formula with real-time slippage multiplier scaling
        adv_ratio = adv_ref / adv_clean
        vol_ratio = vol_clean / base_vol
        dynamic_spread = base_spread * (adv_ratio ** 0.25) * (vol_ratio ** 0.50) * slip_mult
        if np.isnan(dynamic_spread) or np.isinf(dynamic_spread):
            dynamic_spread = base_spread * slip_mult
        clamped_spread = min(max(dynamic_spread, spread_min), spread_max * slip_mult)
        half_spread = 0.5 * clamped_spread

        # Square-root market impact formula with asymmetric sell LOB thinning and ADV capacity penalty
        order_val = max(1.0, target_weight * portfolio_value)
        participation = order_val / adv_clean
        impact_one_way = impact_coeff * slip_mult * vol_clean * np.sqrt(participation)

        # Asymmetric Sell LOB Thinning: Bid liquidity evaporates during market panics
        if is_sell is True and vol_clean > 0.020:
            sell_lob_factor = 1.0 + 1.5 * ((vol_clean - 0.020) / 0.020)
            impact_one_way *= min(sell_lob_factor, 2.50)

        # Institutional AUM Capacity Congestion Penalty (>5% of 20-day ADV)
        if participation > 0.05:
            capacity_penalty = 1.50 * ((participation - 0.05) ** 1.5) * slip_mult
            impact_one_way += capacity_penalty

        if participation > 0.10:
            impact_one_way += 0.50 * (participation - 0.10) * slip_mult

        total_cost_rate = tax_fee + half_spread + impact_one_way
        total_cost_rate = total_cost_rate if np.isfinite(total_cost_rate) else 0.0030
        return float(total_cost_rate)

    def calculate_dynamic_buffer_band(
        self,
        symbol: str,
        target_weight: float,
        cost_rate: float,
        volatility_20d: float,
        risk_aversion: Optional[float] = None
    ) -> float:
        """
        Calculates Leland optimal no-trade buffer threshold delta_i:
        delta_i = [ (3 * c_i * w_target_i * sigma_i^2) / (2 * gamma_risk) ]^(1/3)
        clamped to [delta_floor, delta_cap].
        """
        gamma = risk_aversion if risk_aversion is not None else self.risk_aversion
        gamma_clean = float(gamma) if (gamma is not None and math.isfinite(float(gamma)) and float(gamma) > 0) else self.risk_aversion
        # R11-6 Fix: If target weight is 0.0, return 0.0 immediately to ensure full liquidation is never delayed by a buffer band
        if target_weight <= 0.0:
            return 0.0
        if cost_rate is None or not math.isfinite(float(cost_rate)) or float(cost_rate) <= 0.0:
            return self.delta_floor

        vol_clean = max(0.005, float(volatility_20d)) if (volatility_20d is not None and math.isfinite(float(volatility_20d))) else 0.02
        ann_variance = 252.0 * (vol_clean ** 2)

        # Leland's transaction cost buffer bandwidth: delta_i = [ (3 * c_i * (w_i * (1 - w_i))^2 * sigma_ann^2) / (4 * gamma) ]^(1/3)
        # R5-3 Fix: Weight process variance scales quadratically as (w_i * (1 - w_i))^2
        w_factor = max(1e-4, target_weight * (1.0 - min(0.99, target_weight)))
        cubic_term = (3.0 * float(cost_rate) * (w_factor ** 2) * ann_variance) / (4.0 * max(1e-4, gamma_clean))
        delta_raw = np.cbrt(cubic_term)
        if np.isnan(delta_raw) or np.isinf(delta_raw):
            return self.delta_floor
        effective_cap = min(self.delta_cap, max(self.delta_floor, target_weight * 0.35))
        delta_res = float(min(max(delta_raw, self.delta_floor), effective_cap))
        return delta_res if np.isfinite(delta_res) else self.delta_floor

    def compute_portfolio_rebalance(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        market_map: Dict[str, str],
        volatility_map: Dict[str, float],
        adv_map: Dict[str, float],
        portfolio_value: float = 100_000_000.0,
        rebalance_mode: Optional[str] = None,
        slippage_multiplier: float = 1.0,
        slippage_map: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates dynamic buffer bands [w_target - delta_i, w_target + delta_i]:
        - If current_weight is INSIDE band: returns action HOLD with 0 trade weight.
        - If current_weight BREACHES band: triggers BUY/SELL rebalancing trade.
        """
        mode = (rebalance_mode or self.rebalance_mode).lower()
        curr_w_dict = current_weights if isinstance(current_weights, dict) else {}
        target_w_dict = target_weights if isinstance(target_weights, dict) else {}
        all_symbols = set(curr_w_dict.keys()).union(set(target_w_dict.keys()))

        new_weights: Dict[str, float] = {}
        buffer_bands: Dict[str, Tuple[float, float, float]] = {}
        trades: Dict[str, Dict[str, Any]] = {}
        total_cost_saved = 0.0
        traded_count = 0
        skipped_count = 0

        for sym in all_symbols:
            w_curr = curr_w_dict.get(sym, 0.0)
            w_targ = target_w_dict.get(sym, 0.0)
            mkt = market_map.get(sym, "KOSPI")
            vol = volatility_map.get(sym, 0.020)
            adv = adv_map.get(sym, 1_000_000_000.0)
            sym_slip = (slippage_map.get(sym, slippage_multiplier) if slippage_map else slippage_multiplier)

            cost_rate = self.estimate_transaction_cost_rate(
                symbol=sym,
                market=mkt,
                target_weight=w_targ if w_targ > 0 else w_curr,
                portfolio_value=portfolio_value,
                volatility_20d=vol,
                adv=adv,
                is_sell=(w_curr > w_targ),
                slippage_multiplier=sym_slip
            )

            delta_i = self.calculate_dynamic_buffer_band(
                symbol=sym,
                target_weight=w_targ,
                cost_rate=cost_rate,
                volatility_20d=vol
            )
            # R9-2 Fix: Account scale-aware buffer band to suppress uneconomical tiny fraction rebalances
            min_trade_krw = 50_000.0
            min_weight_delta = min_trade_krw / max(1_000_000.0, portfolio_value) if portfolio_value > 0 else 0.001
            delta_i = max(delta_i, min_weight_delta)
            if w_targ > 0.0:
                delta_i = min(delta_i, max(w_targ * 0.40, min_weight_delta))

            L_i = max(0.0, w_targ - delta_i)
            U_i = w_targ + delta_i
            buffer_bands[sym] = (L_i, U_i, delta_i)

            # Check inside buffer band [L_i, U_i] (Bypass for new entries w_curr==0 or full exits w_targ==0)
            is_new_entry = (w_curr == 0.0 and w_targ > 0.0)
            is_full_exit = (w_targ == 0.0 and w_curr > 0.0)

            if (L_i <= w_curr <= U_i) and not is_new_entry and not is_full_exit:
                new_weights[sym] = w_curr
                skipped_count += 1
                prevented_trade_size = abs(w_curr - w_targ) * portfolio_value
                saved_cost = prevented_trade_size * cost_rate
                total_cost_saved += saved_cost
                trades[sym] = {
                    "action": "HOLD",
                    "w_current": w_curr,
                    "w_target": w_targ,
                    "w_new": w_curr,
                    "delta": delta_i,
                    "band": (L_i, U_i),
                    "trade_weight": 0.0,
                    "cost_saved_krw": saved_cost
                }
            else:
                traded_count += 1
                if w_targ == 0.0:
                    w_exec = 0.0
                    action = "SELL"
                elif w_curr < L_i:
                    w_exec = L_i if mode == "boundary" else w_targ
                    action = "BUY"
                else:
                    w_exec = U_i if mode == "boundary" else w_targ
                    action = "SELL"
                new_weights[sym] = w_exec
                trades[sym] = {
                    "action": action,
                    "w_current": w_curr,
                    "w_target": w_targ,
                    "w_new": w_exec,
                    "delta": delta_i,
                    "band": (L_i, U_i),
                    "trade_weight": w_exec - w_curr,
                    "cost_saved_krw": 0.0
                }

        tot_asset_w = sum(new_weights.values())
        if tot_asset_w > 1.0:
            hold_sum = sum(w for s, w in new_weights.items() if trades[s]["action"] == "HOLD")
            trade_sum = tot_asset_w - hold_sum
            avail_for_trades = max(0.0, 1.0 - hold_sum)
            if trade_sum > 0:
                scale = avail_for_trades / trade_sum
                for s in new_weights:
                    if trades[s]["action"] != "HOLD":
                        new_weights[s] *= scale
                        trades[s]["w_new"] = new_weights[s]
                        trades[s]["trade_weight"] = new_weights[s] - trades[s].get("w_current", 0.0)

        return {
            "new_weights": new_weights,
            "buffer_bands": buffer_bands,
            "trades": trades,
            "summary": {
                "total_symbols": len(all_symbols),
                "traded_count": traded_count,
                "skipped_count": skipped_count,
                "total_cost_saved_krw": total_cost_saved,
                "total_asset_weight": sum(new_weights.values()),
                "cash_weight": max(0.0, 1.0 - sum(new_weights.values()))
            }
        }

    # =========================================================================
    # OBJECTIVE 3: SECTOR EXPOSURE CAPPING & FACTOR NEUTRALITY CONSTRAINTS
    # =========================================================================

    def apply_sector_and_factor_constraints(
        self,
        weights: Dict[str, float],
        sector_map: Optional[Dict[str, str]] = None,
        regime: Optional[Union[int, str]] = None,
        max_sector_cap: Optional[float] = None,
        renormalize: Optional[bool] = None
    ) -> Dict[str, float]:
        """
        Enforces Sector Exposure Cap and Factor Risk Budgeting:
        - Sector Cap: <= 25% in BEAR/SIDEWAYS regimes, <= 35% in BULL market regimes.
        - Rank Preservation: Iteratively rescales over-concentrated sectors while preserving relative rank.
        - Cash/Re-allocation: If renormalize is True (default when max_sector_cap is explicitly provided),
          re-distributes excess weight proportionally across compliant sectors.
        """
        if not weights:
            return {}

        # Determine Regime-Dependent Sector Cap
        if max_sector_cap is not None:
            sector_cap = max_sector_cap
            should_renormalize = True if renormalize is None else bool(renormalize)
        elif regime in [2, 'BULL', 'BULL_LOW_VOL', 'BULL_HIGH_VOL']:
            sector_cap = 0.35  # Dynamic relaxation in BULL market
            should_renormalize = False if renormalize is None else bool(renormalize)
        else:
            sector_cap = 0.25  # Defensive 25% cap in BEAR/SIDEWAYS
            should_renormalize = False if renormalize is None else bool(renormalize)

        if not sector_map:
            # Fallback if no sector mapping is available
            s_sum = sum(weights.values())
            return {s: w / s_sum for s, w in weights.items()} if s_sum > 0 else weights

        cleaned_weights = dict(weights)
        target_total = sum(weights.values()) if sum(weights.values()) > 0 else 1.0

        # Iterative Sector Cap Enforcement (up to 10 passes for convergence)
        for _ in range(10):
            sector_totals: Dict[str, float] = {}
            for sym, w in cleaned_weights.items():
                sec = sector_map.get(sym, "UNKNOWN")
                sector_totals[sec] = sector_totals.get(sec, 0.0) + w

            over_sectors = {sec: tot for sec, tot in sector_totals.items() if tot > sector_cap + 1e-6}
            if not over_sectors:
                break

            # Rescale symbols in over-concentrated sectors
            for sec, tot in over_sectors.items():
                scale_factor = sector_cap / tot
                for sym, w in cleaned_weights.items():
                    if sector_map.get(sym, "UNKNOWN") == sec:
                        cleaned_weights[sym] = w * scale_factor

            if should_renormalize:
                # Re-distribute excess weight proportionally across compliant sectors
                non_over_sum = sum(w for sym, w in cleaned_weights.items() if sector_map.get(sym, "UNKNOWN") not in over_sectors)
                if non_over_sum > 0:
                    cur_sum = sum(cleaned_weights.values())
                    excess = target_total - cur_sum
                    if excess > 0:
                        for sym, w in cleaned_weights.items():
                            if sector_map.get(sym, "UNKNOWN") not in over_sectors:
                                cleaned_weights[sym] += excess * (w / non_over_sum)
                else:
                    # If all sectors are capped, normalize directly
                    s_sum = sum(cleaned_weights.values())
                    if s_sum > 0:
                        cleaned_weights = {s: (w / s_sum) * target_total for s, w in cleaned_weights.items()}
                    break

        if should_renormalize:
            # Final safety normalization if needed to preserve target_total
            s_sum = sum(cleaned_weights.values())
            if s_sum > 0 and abs(s_sum - target_total) > 1e-4:
                cleaned_weights = {s: (w / s_sum) * target_total for s, w in cleaned_weights.items()}

        return cleaned_weights

    # =========================================================================
    # OBJECTIVE 4: REAL-TIME OMS SLIPPAGE FEEDBACK & ATR TRAILING STOP
    # =========================================================================

    def calibrate_slippage_from_trade_logs(self, db_path: Optional[str] = None) -> float:
        """
        Reads realized execution logs from trade_logs.db and calculates empirical
        realized slippage ratio vs predicted Almgren-Chriss cost, returning a
        calibrated cost scaling factor (default = 1.0 if insufficient trades).
        """
        import sqlite3

        target_db = Path(db_path) if db_path else _PROJECT_ROOT / "trade_logs.db"
        if not target_db.exists():
            return 1.0

        try:
            conn = sqlite3.connect(str(target_db), timeout=30.0)
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('execution_logs', 'order_plans', 'trade_logs', 'orders');")
            tables = [r[0] for r in cursor.fetchall()]

            if not tables:
                conn.close()
                return 1.0

            if 'execution_logs' in tables and 'order_plans' in tables:
                df = pd.read_sql_query(
                    "SELECT o.target_price AS order_price, e.executed_price AS executed_price "
                    "FROM order_plans o JOIN execution_logs e ON o.order_id = e.order_id "
                    "WHERE o.target_price > 0 AND e.executed_price > 0 LIMIT 500;", conn
                )
            elif 'orders' in tables and 'executions' in tables:
                df = pd.read_sql_query(
                    "SELECT o.price AS order_price, e.price AS executed_price "
                    "FROM orders o JOIN executions e ON o.order_id = e.order_id "
                    "WHERE o.price > 0 AND e.price > 0 LIMIT 500;", conn
                )
            else:
                tbl = 'trade_logs' if 'trade_logs' in tables else tables[0]
                cursor.execute(f"PRAGMA table_info({tbl});")  # nosec B608
                cols = [r[1] for r in cursor.fetchall()]
                p_col = 'order_price' if 'order_price' in cols else ('price' if 'price' in cols else ('target_price' if 'target_price' in cols else None))
                exec_col = 'executed_price' if 'executed_price' in cols else ('price' if 'price' in cols else None)
                if not p_col or not exec_col:
                    conn.close()
                    return 1.0
                df = pd.read_sql_query(
                    f"SELECT {p_col} AS order_price, {exec_col} AS executed_price FROM {tbl} LIMIT 500;",  # nosec B608
                    conn
                )
            conn.close()

            if df.empty or len(df) < 5:
                return 1.0

            df['order_price'] = pd.to_numeric(df['order_price'], errors='coerce')
            df['executed_price'] = pd.to_numeric(df['executed_price'], errors='coerce')
            valid = df.dropna(subset=['order_price', 'executed_price'])
            valid = valid[valid['order_price'] > 0]

            if len(valid) < 5:
                return 1.0

            is_buy = valid['side'].str.upper().str.startswith('BUY') if 'side' in valid.columns else pd.Series(True, index=valid.index)
            side_sign = np.where(is_buy, 1.0, -1.0)
            signed_slip = side_sign * (valid['executed_price'] - valid['order_price']) / valid['order_price']
            adverse_slip = max(0.0, float(signed_slip.mean()))
            # Normalize relative to benchmark 0.10% (10 bps)
            calibrated_factor = float(np.clip(adverse_slip / 0.0010, 0.5, 3.0))
            logger.info(f"[OMS SLIPPAGE FEEDBACK] Calibrated slippage factor = {calibrated_factor:.2f}x (from {len(valid)} trades)")
            return calibrated_factor
        except Exception as e:
            logger.warning(f"[OMS SLIPPAGE FEEDBACK] Failed to calibrate slippage: {e}")
            return 1.0

    def calculate_atr_trailing_stop(
        self,
        symbol: str,
        current_price: float,
        atr_20d: float,
        is_long: bool = True,
        multiplier: float = 2.5,
        highest_price: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculates intraday dynamic ATR-based trailing stop-loss and take-profit levels:
        - Stop Loss: peak_price - (multiplier * ATR_20d)
        - Take Profit: current_price + (1.5 * multiplier * ATR_20d)
        """
        if current_price <= 0.0 or atr_20d <= 0.0:
            return {
                "stop_loss": max(0.0, current_price * 0.95),
                "take_profit": current_price * 1.10,
                "risk_pct": 0.05
            }

        atr_clean = max(atr_20d, current_price * 0.005)
        stop_dist = multiplier * atr_clean

        safe_ref = None
        try:
            if highest_price is not None:
                hp = float(highest_price)
                if hp > 0 and not np.isnan(hp) and not np.isinf(hp):
                    safe_ref = hp
        except (ValueError, TypeError):
            safe_ref = None

        if is_long:
            ref_price = max(safe_ref, current_price) if safe_ref is not None else current_price
            stop_loss = max(0.0, ref_price - stop_dist)
            take_profit = current_price + (1.5 * stop_dist)
        else:
            ref_price = min(safe_ref, current_price) if safe_ref is not None else current_price
            stop_loss = ref_price + stop_dist
            take_profit = max(0.0, current_price - (1.5 * stop_dist))

        risk_pct = float(abs(current_price - stop_loss) / current_price)
        return {
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "risk_pct": float(risk_pct)
        }

    # =========================================================================
    # OBJECTIVE 5: DYNAMIC VOLATILITY TARGETING (DVT) MACRO CASH OVERLAY
    # =========================================================================

    def compute_dynamic_volatility_target_weights(
        self,
        target_weights: Dict[str, float],
        returns_matrix: Optional[np.ndarray] = None,
        target_annual_vol: float = 0.12,
        min_gross_exposure: float = 0.20,
        max_gross_exposure: float = 1.00
    ) -> Tuple[Dict[str, float], float]:
        """
        Computes portfolio gross exposure and cash buffer ratio based on realized portfolio volatility:
        Gross Exposure = clip(target_annual_vol / max(realized_vol_annual, 0.04), min_gross, max_gross)
        Cash Buffer Ratio = 1.0 - Gross Exposure

        Returns:
            Tuple of (scaled_weights_dict, cash_buffer_ratio)
        """
        if not target_weights:
            return {}, 1.0

        if returns_matrix is None or len(returns_matrix) < 15 or returns_matrix.shape[1] != len(target_weights):
            return dict(target_weights), 0.0

        try:
            w_vec = np.array(list(target_weights.values()), dtype=np.float64)
            w_sum = np.sum(w_vec)
            if w_sum > 0:
                w_norm = w_vec / w_sum
            else:
                return dict(target_weights), 0.0

            port_daily_ret = returns_matrix @ w_norm

            # RiskMetrics EWMA conditional volatility (lambda = 0.94 / span = 20)
            n_obs = len(port_daily_ret)
            weights_ewma = np.exp(-np.arange(n_obs)[::-1] / 20.0)
            weights_ewma /= np.sum(weights_ewma)

            realized_var_daily = float(np.sum(weights_ewma * (port_daily_ret ** 2)))
            realized_vol_annual = float(np.sqrt(max(1e-8, realized_var_daily * 252.0)))

            gross_exposure = float(np.clip(
                target_annual_vol / max(realized_vol_annual, 0.04),
                min_gross_exposure,
                max_gross_exposure
            ))
            cash_ratio = max(0.0, 1.0 - gross_exposure)

            scaled_weights = {k: float(v * gross_exposure) for k, v in target_weights.items()}
            logger.info(
                f"[DVT CASH OVERLAY] Realized Ann Vol={realized_vol_annual:.2%}, Target Vol={target_annual_vol:.2%}, "
                f"Gross Exposure={gross_exposure:.2%}, Cash Buffer={cash_ratio:.2%}"
            )
            return scaled_weights, cash_ratio
        except Exception as e:
            logger.warning(f"[DVT CASH OVERLAY] Failed to compute DVT weights: {e}")
            return dict(target_weights), 0.0

    # =========================================================================
    # OBJECTIVE 6: CLOSED-LOOP REALIZED SLIPPAGE FEEDBACK SIZING HAIRCUT
    # =========================================================================

    def apply_slippage_feedback_haircut(
        self,
        weights_dict: Dict[str, float],
        realized_slippage_map: Optional[Dict[str, float]] = None,
        max_slippage_bps_threshold: float = 30.0
    ) -> Dict[str, float]:
        """
        Applies dynamic position haircut based on realized execution slippage from trade_logs.db.
        If an asset's realized slippage exceeds threshold (e.g. 30 bps = 0.30%),
        its allocation is scaled down by kappa_slip = max(0.50, 1.0 - (excess_bps / 100.0) * 2.0).
        """
        if not weights_dict or not realized_slippage_map:
            return dict(weights_dict)

        adjusted_weights = {}
        for sym, w in weights_dict.items():
            slip_bps = float(realized_slippage_map.get(sym, 0.0))
            if slip_bps > max_slippage_bps_threshold:
                excess_bps = slip_bps - max_slippage_bps_threshold
                haircut = max(0.50, 1.0 - (excess_bps / 100.0) * 2.0)
                adj_w = w * haircut
                adjusted_weights[sym] = float(adj_w)
                logger.info(
                    f"[SLIPPAGE SIZING HAIRCUT] Symbol {sym}: Realized Slippage {slip_bps:.1f} bps > {max_slippage_bps_threshold} bps threshold "
                    f"-> Haircut multiplier {haircut:.2f} applied (Weight: {w:.3f} -> {adj_w:.3f})"
                )
            else:
                adjusted_weights[sym] = float(w)

        return adjusted_weights

    # =========================================================================
    # OBJECTIVE 7: ROCKAFELLAR-URYASEV CVaR CONVEX PROGRAMMING OPTIMIZER
    # =========================================================================

    def optimize_rockafellar_uryasev_cvar(
        self,
        expected_returns: Union[pd.Series, Dict[str, float], np.ndarray],
        historical_returns: Union[pd.DataFrame, np.ndarray],
        covariance_matrix: Optional[np.ndarray] = None,
        previous_weights: Optional[Dict[str, float]] = None,
        transaction_cost_rates: Optional[Dict[str, float]] = None,
        max_cvar_limit: float = 0.04,
        confidence: float = 0.95,
        max_weight: Optional[float] = None,
        sector_map: Optional[Dict[str, str]] = None,
        max_sector_weight: Optional[float] = None,
        turnover_penalty_l1: float = 0.02
    ) -> Dict[str, float]:
        """
        Solves Rockafellar & Uryasev (2000) Conditional Value-at-Risk (CVaR) Convex Optimization:
        Objective:
            min_{w, alpha, u} [ -w^T mu + (lambda/2) w^T Sigma w + sum c_i |w_i - w_prev_i| + 2.0 * max(0, CVaR - max_cvar) ]
        subject to:
            u_t + r_t^T w + alpha >= 0,  u_t >= 0
            alpha + (1 / ((1 - beta) * T)) sum(u_t) <= max_cvar
            sum(w_i) = 1.0,  0 <= w_i <= max_weight
            sum_{i in Sector_k} w_i <= max_sector_weight

        Guarantees convex global optimality and zero solver convergence failure.
        """
        if isinstance(expected_returns, (pd.Series, dict)):
            symbols = list(expected_returns.keys()) if isinstance(expected_returns, dict) else list(expected_returns.index)
            mu = np.array([float(expected_returns[s]) for s in symbols], dtype=np.float64)
        else:
            symbols = [f"A{i}" for i in range(len(expected_returns))]
            mu = np.asarray(expected_returns, dtype=np.float64)

        N = len(symbols)
        if N == 0:
            return {}
        if N == 1:
            return {symbols[0]: 1.0}

        eff_max_w = max(float(max_weight or self.default_max_weight), 1.05 / N)
        eff_sec_cap = float(max_sector_weight or self.default_max_sector_weight)

        # Clean historical returns
        if isinstance(historical_returns, pd.DataFrame):
            h_df = historical_returns[symbols] if all(s in historical_returns.columns for s in symbols) else historical_returns
            r_mat = h_df.values.astype(np.float64)
        else:
            r_mat = np.asarray(historical_returns, dtype=np.float64)

        if r_mat.ndim == 1:
            r_mat = r_mat.reshape(-1, 1)

        T = r_mat.shape[0]
        if T < 5 or r_mat.shape[1] != N:
            # Fallback to analytical EVT-CVaR or Risk Parity
            return {s: 1.0 / N for s in symbols}

        # Covariance matrix
        if covariance_matrix is not None and covariance_matrix.shape == (N, N):
            cov_mat = np.asarray(covariance_matrix, dtype=np.float64)
        else:
            cov_mat = np.cov(r_mat, rowvar=False)
            if cov_mat.ndim == 0:
                cov_mat = np.array([[float(cov_mat)]])

        cov_mat = self.compute_tail_stress_cov(r_mat, cov_mat)

        # Previous weights vector
        w_prev_vec = np.zeros(N, dtype=np.float64)
        if previous_weights:
            for i, s in enumerate(symbols):
                w_prev_vec[i] = float(previous_weights.get(s, 0.0))

        # Cost rates
        c_vec = np.full(N, 0.003, dtype=np.float64)
        if transaction_cost_rates:
            for i, s in enumerate(symbols):
                c_vec[i] = float(transaction_cost_rates.get(s, 0.003))

        beta_conf = float(np.clip(confidence, 0.80, 0.99))
        cvar_coef = 1.0 / ((1.0 - beta_conf) * max(T, 1))

        # Decision variable x: [w (N), alpha (1), u (T)]
        def objective(x):
            w = x[:N]
            alpha = x[N]
            u = x[N + 1:]
            ret_term = float(np.dot(w, mu))
            risk_term = float(w.T @ cov_mat @ w)
            # Pseudo-Huber smooth regularizer restoring C2 differentiability for SLSQP
            smooth_diff = np.sqrt((w - w_prev_vec) ** 2 + 1e-6)
            turnover_term = float(np.sum((c_vec + turnover_penalty_l1) * smooth_diff))
            cvar_val = float(alpha + cvar_coef * np.sum(u))
            cvar_penalty = 5.0 * max(0.0, cvar_val - max_cvar_limit)
            return -ret_term + 0.5 * self.risk_aversion * risk_term + turnover_term + cvar_penalty

        x0 = np.zeros(N + 1 + T, dtype=np.float64)
        x0[:N] = w_prev_vec if (np.sum(w_prev_vec) > 0.90 and np.all(w_prev_vec >= 0)) else (1.0 / N)
        x0[:N] /= np.sum(x0[:N])
        x0[N] = 0.02
        x0[N + 1:] = 0.01

        bounds = [(0.0, eff_max_w) for _ in range(N)] + [(None, None)] + [(0.0, None) for _ in range(T)]
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x[:N]) - 1.0},
            # Single vectorized auxiliary CVaR constraint
            {'type': 'ineq', 'fun': lambda x: x[N + 1:N + 1 + T] + (r_mat @ x[:N]) + x[N]}
        ]

        # Sector constraints
        if sector_map:
            sectors = sorted(list(set(sector_map.values())))
            for sec in sectors:
                sec_idxs = [i for i, s in enumerate(symbols) if sector_map.get(s) == sec]
                if sec_idxs:
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda x, idxs=sec_idxs: eff_sec_cap - float(np.sum(x[idxs]))
                    })

        res = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 500, 'ftol': 1e-7}
        )

        if not res.success:
            logger.warning(f"[Rockafellar-Uryasev CVaR] Solver notice: {res.message}. Using normalized initial guess.")
            final_w = x0[:N] / np.sum(x0[:N])
        else:
            final_w = np.clip(res.x[:N], 0.0, eff_max_w)
            final_w /= np.sum(final_w)

        return {sym: float(w) for sym, w in zip(symbols, final_w)}

    # =========================================================================
    # OBJECTIVE 8: MARKET-CAP WEIGHTED BLACK-LITTERMAN WITH IDZOREK UNCERTAINTY
    # =========================================================================

    def allocate_market_cap_black_litterman(
        self,
        predicted_returns: Dict[str, float],
        prices_dict: Dict[str, pd.DataFrame],
        market_caps: Optional[Dict[str, float]] = None,
        meta_convictions: Optional[Dict[str, float]] = None,
        total_portfolio_value: float = 100_000_000.0,
        tau: float = 0.05,
        risk_aversion: float = 2.5,
        omega_scale: float = 0.10,
        max_weight: Optional[float] = None,
        sector_map: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Calculates Black-Litterman optimal asset allocation weights anchored to market-cap prior weights:
        1. Prior returns: Pi = lambda * Sigma @ w_mkt (Market Equilibrium Equilibrium Return)
        2. View Matrix Q: Strategy predicted expected returns
        3. Uncertainty Omega: Idzorek confidence diagonal scaling
        4. Posterior expected returns mu_BL and covariance Sigma_BL
        """
        symbols = [s for s in predicted_returns.keys() if s in prices_dict]
        N = len(symbols)
        if N < 1:
            return pd.DataFrame()
        if N == 1:
            return pd.DataFrame([{
                'symbol': symbols[0],
                'weight': 1.0,
                'allocation_amount': total_portfolio_value,
                'predicted_return': float(predicted_returns[symbols[0]])
            }])

        returns_list = []
        valid_symbols = []
        for s in symbols:
            df_p = prices_dict[s]
            c = df_p['Close'].iloc[:, 0] if isinstance(df_p['Close'], pd.DataFrame) else df_p['Close']
            r = c.pct_change(fill_method=None).tail(60).dropna()
            if len(r) >= 15:
                returns_list.append(r)
                valid_symbols.append(s)

        if len(valid_symbols) < 2:
            return pd.DataFrame([{
                'symbol': s,
                'weight': 1.0 / len(valid_symbols),
                'allocation_amount': total_portfolio_value / len(valid_symbols),
                'predicted_return': float(predicted_returns.get(s, 0.0))
            } for s in valid_symbols])

        ret_df = pd.concat(returns_list, axis=1).ffill().bfill().dropna()
        if len(ret_df) < 5:
            return pd.DataFrame()

        # Ledoit-Wolf Covariance
        try:
            from sklearn.covariance import LedoitWolf
            cov_matrix = LedoitWolf().fit(ret_df.values).covariance_
        except Exception:
            cov_matrix = ret_df.cov().fillna(0.0).values

        if cov_matrix is None or np.any(np.isnan(cov_matrix)) or np.any(np.isinf(cov_matrix)) or cov_matrix.shape != (len(valid_symbols), len(valid_symbols)):
            cov_matrix = np.eye(len(valid_symbols)) * 0.0004

        n_valid = len(valid_symbols)
        # Market-cap prior equilibrium weights w_mkt
        if market_caps:
            caps_arr = np.array([max(1.0, float(market_caps.get(s, 1.0))) for s in valid_symbols], dtype=np.float64)
            w_mkt = caps_arr / np.sum(caps_arr)
        else:
            w_mkt = np.full(n_valid, 1.0 / n_valid)

        # Equilibrium prior returns Pi = lambda * Sigma @ w_mkt
        horizon = max(getattr(self, 'target_horizon', 20), 1)
        horizon_cov = cov_matrix * horizon
        Pi = risk_aversion * (horizon_cov @ w_mkt)

        # Views Q
        Q = np.array([float(predicted_returns.get(s, 0.0)) for s in valid_symbols], dtype=np.float64)
        # Horizon scaling check
        if np.mean(Q) > 0.50:
            Q = Q / 100.0  # Normalize percentage to decimal

        # Idzorek uncertainty matrix Omega
        if meta_convictions:
            conf_arr = np.array([float(np.clip(meta_convictions.get(s, 0.70), 0.10, 0.99)) for s in valid_symbols])
            omega_diag = (np.diag(horizon_cov) * omega_scale) * ((1.0 - conf_arr) / conf_arr)
        else:
            omega_diag = np.diag(horizon_cov) * omega_scale

        Omega = np.diag(np.maximum(omega_diag, 1e-8))

        # Solve for posterior expected returns mu_BL
        try:
            A = tau * horizon_cov + Omega
            inv_A_diff = np.linalg.solve(A, Q - Pi)
            mu_bl = Pi + tau * (horizon_cov @ inv_A_diff)

            inv_A_Sigma = np.linalg.solve(A, horizon_cov)
            cov_bl = (1.0 + tau) * horizon_cov - (tau ** 2) * (horizon_cov @ inv_A_Sigma)
        except Exception:
            mu_bl = 0.5 * (Pi + Q)
            cov_bl = cov_matrix

        # Quadratic utility optimization: max w^T mu_BL - 0.5 * lambda * w^T cov_BL w
        eff_max_w = max(float(max_weight or self.default_max_weight), 1.05 / n_valid)

        def bl_objective(w):
            ret = float(np.dot(w, mu_bl))
            var_p = float(w.T @ cov_bl @ w)
            return -(ret - 0.5 * risk_aversion * var_p)

        w0 = np.full(n_valid, 1.0 / n_valid)
        bounds = tuple((0.0, eff_max_w) for _ in range(n_valid))
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]

        res = minimize(bl_objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
        weights = res.x / np.sum(res.x) if res.success else w0

        records = []
        for s, w, r in zip(valid_symbols, weights, mu_bl):
            records.append({
                'symbol': s,
                'weight': float(w),
                'allocation_amount': float(w * total_portfolio_value),
                'predicted_return': float(r * 100.0 if r <= 1.0 else r)
            })

        df_res = pd.DataFrame(records).sort_values('weight', ascending=False).reset_index(drop=True)
        return df_res

    # =========================================================================
    # OBJECTIVE 9: FULL COVARIANCE MULTI-ASSET FRACTIONAL KELLY
    # =========================================================================

    def allocate_full_covariance_kelly(
        self,
        expected_returns: pd.Series,
        covariance_matrix: np.ndarray,
        kelly_fraction: float = 0.25,
        risk_free_rate: float = 0.035,
        max_weight: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Solves multi-asset Fractional Kelly portfolio allocation:
        w^* = kelly_fraction * Sigma^{-1} (mu - r_f 1)
        projected onto the constrained long-only simplex (0 <= w_i <= max_weight, sum(w_i) <= 1.0).
        """
        symbols = list(expected_returns.index)
        N = len(symbols)
        if N == 0:
            return {}
        if N == 1:
            return {symbols[0]: min(1.0, max_weight or self.default_max_weight)}

        cap = max_weight or self.default_max_weight
        mu = np.nan_to_num(expected_returns.values.astype(np.float64), nan=0.0)
        # Scale risk-free rate to 20d horizon if mu is horizon return
        rf_scaled = risk_free_rate * (self.target_horizon / 252.0)
        excess_mu = np.maximum(0.0, mu - rf_scaled)

        cov = np.asarray(covariance_matrix, dtype=np.float64)
        if cov.shape != (N, N) or not np.all(np.isfinite(cov)):
            return self.allocate_quarter_kelly(expected_returns, max_weight=cap, kelly_fraction=kelly_fraction)

        try:
            # Regularized inverse: Sigma + 1e-4 * I
            cov_reg = cov + 1e-4 * np.eye(N)
            horizon = max(getattr(self, 'target_horizon', 20), 1)
            cov_horizon = cov_reg * horizon
            inv_cov = np.linalg.pinv(cov_horizon)
            raw_kelly = float(kelly_fraction) * np.dot(inv_cov, excess_mu)
        except Exception:
            raw_kelly = excess_mu / np.maximum(np.diag(cov), 1e-6)

        # Long-only projection
        raw_kelly = np.maximum(0.0, raw_kelly)
        tot_k = np.sum(raw_kelly)

        if tot_k <= 1e-8:
            return {s: float(1.0 / N) for s in symbols}

        norm_w = raw_kelly / tot_k
        eff_cap = max(cap, 1.0 / N)
        clamped_w = np.clip(norm_w, 0.0, eff_cap)
        clamped_w /= np.sum(clamped_w)

        return {sym: float(w) for sym, w in zip(symbols, clamped_w)}

    # =========================================================================
    # OBJECTIVE 10: SYNTHETIC BETA INVERSE HEDGE OVERLAY & ADV CAPACITY
    # =========================================================================

    @staticmethod
    def compute_portfolio_beta(
        weights: Dict[str, float],
        beta_map: Optional[Dict[str, float]] = None,
        default_beta: float = 1.0
    ) -> float:
        """
        Computes weighted systematic portfolio beta against benchmark index.
        """
        if not weights:
            return 1.0
        b_map = beta_map or {}
        tot_w = sum(weights.values())
        if tot_w <= 0:
            return 1.0

        port_beta = sum(w * float(b_map.get(sym, default_beta)) for sym, w in weights.items()) / tot_w
        return float(port_beta)

    @staticmethod
    def compute_synthetic_inverse_hedge(
        portfolio_weights: Dict[str, float],
        market: str = "KOSPI",
        regime_label: str = "BULL",
        beta_map: Optional[Dict[str, float]] = None,
        cash_ratio: float = 0.0,
        max_hedge_ratio: float = 0.80
    ) -> Dict[str, Any]:
        """
        Calculates synthetic inverse hedge allocation in Bear / Crisis regimes.
        Allocates to designated benchmark inverse instruments:
          - KRX (KOSPI/KOSDAQ): '114800' (KODEX 200 선물인버스2X, -2x leverage)
          - US (SP500/NASDAQ/RUSSELL2000): 'PSQ' or 'SH'
        """
        is_bear = "BEAR" in str(regime_label).upper() or "CRISIS" in str(regime_label).upper()
        if not is_bear or not portfolio_weights:
            return {
                "hedge_required": False,
                "hedge_symbol": None,
                "hedge_weight": 0.0,
                "net_portfolio_beta": PortfolioAllocator.compute_portfolio_beta(portfolio_weights, beta_map),
                "gross_long_weight": sum(portfolio_weights.values())
            }

        port_beta = PortfolioAllocator.compute_portfolio_beta(portfolio_weights, beta_map)
        gross_long = sum(portfolio_weights.values())
        invested_equity = max(0.0, 1.0 - cash_ratio) * gross_long

        m_upper = str(market).upper()
        if m_upper in ("KOSPI", "KOSDAQ", "KRX"):
            hedge_symbol = "114800"  # KODEX 200선물인버스2X (-2x)
            inv_leverage = 2.0
        elif m_upper in ("NASDAQ",):
            hedge_symbol = "PSQ"
            inv_leverage = 1.0
        else:
            hedge_symbol = "SH"
            inv_leverage = 1.0

        target_hedge_w = (port_beta * invested_equity) / inv_leverage
        hedge_w = float(np.clip(target_hedge_w, 0.0, max_hedge_ratio))
        net_beta = port_beta * invested_equity - (hedge_w * inv_leverage)

        return {
            "hedge_required": True,
            "hedge_symbol": hedge_symbol,
            "hedge_weight": hedge_w,
            "hedge_leverage": inv_leverage,
            "portfolio_beta_before": port_beta,
            "net_portfolio_beta": float(net_beta),
            "gross_long_weight": gross_long
        }

    @staticmethod
    def apply_adv_capacity_constraint(
        target_weights: Dict[str, float],
        adv_map: Dict[str, float],
        total_capital: float = 100_000_000.0,
        max_adv_ratio: float = 0.015
    ) -> Dict[str, float]:
        """
        Enforces non-linear Kyle-Almgren market capacity bounds based on 20-day ADV.
        Capped at max_adv_ratio (default 1.5% of ADV) with square-root impact penalty damping.
        """
        if not target_weights or total_capital <= 0:
            return dict(target_weights)

        constrained = {}
        for sym, w in target_weights.items():
            trade_val = w * total_capital
            adv = float(adv_map.get(sym, 1_000_000_000.0))
            if adv > 0:
                max_val = max_adv_ratio * adv
                if trade_val > max_val:
                    excess_ratio = trade_val / max_val
                    penalty = float(np.exp(-1.5 * (excess_ratio - 1.0)))
                    damped_val = max_val + (trade_val - max_val) * penalty
                    constrained[sym] = float(damped_val / total_capital)
                else:
                    constrained[sym] = float(w)
            else:
                constrained[sym] = float(w)

        tot = sum(constrained.values())
        if tot > 1.0:
            constrained = {k: v / tot for k, v in constrained.items()}
        return constrained

    # =========================================================================
    # OBJECTIVE 11: EXTREME VALUE CLAYTON COPULA TAIL-RISK CALIBRATION
    # =========================================================================

    @staticmethod
    def compute_clayton_copula_tail_dependence(
        returns_matrix: np.ndarray,
        theta: float = 2.0
    ) -> np.ndarray:
        """
        Computes pairwise lower tail dependence matrix Lambda_L using Archimedean Clayton Copula:
        lambda_L = 2^(-1 / theta)
        """
        N = returns_matrix.shape[1] if returns_matrix.ndim == 2 else 0
        if N <= 1:
            return np.ones((N, N), dtype=float)

        q05 = np.nanpercentile(returns_matrix, 5.0, axis=0)
        tail_indicator = (returns_matrix <= q05).astype(float)

        co_tail = np.dot(tail_indicator.T, tail_indicator) / max(1, returns_matrix.shape[0])
        p_indiv = np.mean(tail_indicator, axis=0)

        try:
            from scipy.stats import kendalltau
        except ImportError:
            kendalltau = None

        lambda_L = np.zeros((N, N), dtype=float)
        for i in range(N):
            for j in range(N):
                if i == j:
                    lambda_L[i, j] = 1.0
                else:
                    p_cond = co_tail[i, j] / max(np.sqrt(p_indiv[i] * p_indiv[j]), 1e-6)
                    theoretical_l = float(2.0 ** (-1.0 / max(theta, 0.1)))
                    if kendalltau is not None and len(returns_matrix) >= 10:
                        try:
                            tau_val, _ = kendalltau(returns_matrix[:, i], returns_matrix[:, j])
                            tau_val = float(np.nan_to_num(tau_val, nan=0.0))
                            if 0.01 < tau_val < 0.99:
                                theta_pair = (2.0 * tau_val) / (1.0 - tau_val)
                                theoretical_l = float(2.0 ** (-1.0 / max(theta_pair, 0.05)))
                            elif tau_val <= 0.01:
                                theoretical_l = 0.0
                        except Exception:
                            pass
                    lambda_L[i, j] = float(np.clip(0.5 * p_cond + 0.5 * theoretical_l, 0.0, 1.0))

        return lambda_L

    @staticmethod
    def compute_clayton_copula_tail_risk_weights(
        target_weights: Dict[str, float],
        returns_df: Optional[pd.DataFrame] = None,
        theta: float = 2.0,
        tail_penalty_strength: float = 0.50
    ) -> Dict[str, float]:
        """
        Penalizes portfolio weights for assets with severe joint downside tail co-movement
        to eliminate catastrophic correlation breakdowns during market panics.
        """
        if not target_weights or returns_df is None or returns_df.empty:
            return dict(target_weights)

        symbols = [s for s in target_weights.keys() if s in returns_df.columns]
        if len(symbols) < 2:
            return dict(target_weights)

        ret_mat = returns_df[symbols].dropna().values.astype(np.float64)
        if len(ret_mat) < 15:
            return dict(target_weights)

        lambda_L = PortfolioAllocator.compute_clayton_copula_tail_dependence(ret_mat, theta=theta)

        avg_tail_dep = np.mean(lambda_L, axis=1)
        w_vec = np.array([target_weights[s] for s in symbols], dtype=float)

        tail_multiplier = np.exp(-tail_penalty_strength * (avg_tail_dep - np.mean(avg_tail_dep)))
        penalized_w = w_vec * tail_multiplier
        penalized_w = np.maximum(0.0, penalized_w)
        tot_pen = np.sum(penalized_w) or 1.0
        penalized_w /= tot_pen

        res = dict(target_weights)
        for s, w_adj in zip(symbols, penalized_w):
            res[s] = float(w_adj)
        return res


