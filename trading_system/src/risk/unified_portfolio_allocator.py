"""
Unified Institutional Portfolio Allocator Engine
Tier-1 Hedge Fund Portfolio Construction Framework:
1. 3-Model Regime-Adaptive Multi-Model Blending (Black-Litterman + HERC + EVT-CVaR + Risk Parity)
2. 3/2-Power Non-Linear Market Impact Penalty Objective Function (Gatheral & Almgren-Chriss)
3. Barra Multi-Factor Style Exposure Bounds & Sector Constraints
4. 12% Target Volatility Scaling & Bull Market Cash Drag Eliminator
5. Asymmetric Leland Dynamic No-Trade Buffer Bands for STT/Turnover Suppression
6. Inter-Market Dynamic Capital Flight Routing (US vs KR)
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Any, cast, Union
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.analysis.portfolio_optimizer import (
    calculate_risk_parity_weights,
    calculate_black_litterman_weights,
    calculate_herc_weights,
    calculate_hrp_weights,
    shrink_covariance_matrix,
    apply_portfolio_constraints,
)

logger = logging.getLogger(__name__)


class UnifiedPortfolioAllocator:
    """
    Unified Institutional Portfolio Allocator Engine.
    Orchestrates multi-model regime blending, non-linear market impact optimization,
    Barra factor bounds, target volatility scaling, and execution buffer bands.
    """

    # Regime-Adaptive Weights across 4 core optimization paradigms
    # [w_BL, w_HERC, w_RiskParity, w_CVaR]
    REGIME_OPTIMIZER_BLENDS = {
        "BULL_LOW_VOL": {"bl": 0.65, "herc": 0.25, "rp": 0.10, "cvar": 0.00},
        "BULL_HIGH_VOL": {"bl": 0.45, "herc": 0.35, "rp": 0.10, "cvar": 0.10},
        "SIDEWAYS_LOW_VOL": {"bl": 0.25, "herc": 0.45, "rp": 0.20, "cvar": 0.10},
        "SIDEWAYS_HIGH_VOL": {"bl": 0.15, "herc": 0.40, "rp": 0.20, "cvar": 0.25},
        "BEAR_LOW_VOL": {"bl": 0.05, "herc": 0.35, "rp": 0.20, "cvar": 0.40},
        "BEAR_HIGH_VOL": {"bl": 0.00, "herc": 0.20, "rp": 0.10, "cvar": 0.70},
        "CRISIS": {"bl": 0.00, "herc": 0.15, "rp": 0.05, "cvar": 0.80},
    }

    def __init__(
        self,
        target_volatility: float = 0.12,
        max_single_weight: float = 0.20,
        max_sector_weight: float = 0.35,
        default_max_total_allocation: float = 0.90,
        risk_aversion: float = 1.0,
        leland_cost_bps: float = 20.0,
        target_horizon: int = 20,
        rebalance_mode: str = "boundary",
    ):
        self.target_volatility = float(target_volatility)
        self.max_single_weight = float(max_single_weight)
        self.max_sector_weight = float(max_sector_weight)
        self.default_max_total_allocation = float(default_max_total_allocation)
        self.risk_aversion = float(risk_aversion)
        self.leland_cost_bps = float(leland_cost_bps)
        self.target_horizon = int(target_horizon)
        self.rebalance_mode = str(rebalance_mode).lower() if rebalance_mode is not None else "boundary"

    @staticmethod
    def calculate_asymmetric_leland_multipliers(
        unrealized_return: float,
        volatility_20d: float,
        downside_semi_volatility: Optional[float] = None,
    ) -> Tuple[float, float]:
        """
        Computes continuous volatility-normalized asymmetric Leland buffer multipliers:
            z_unrealized = u_ret / (volatility_20d * sqrt(5)) (for u_ret >= 0)
            z_unrealized = u_ret / (downside_semi_volatility * sqrt(5)) (for u_ret < 0, F43)
        - Runners (z > 0): smoothly expands upper band (1.0 -> 1.8x) to let winners run.
        - Laggards (z < 0): smoothly tightens lower band (1.0 -> 0.6x) for swift de-risking.
        Returns:
            Tuple of (upper_mult, lower_mult)
        """
        u_ret = float(unrealized_return) if (unrealized_return is not None and math.isfinite(float(unrealized_return))) else 0.0
        vol_clean = max(0.005, float(volatility_20d)) if (volatility_20d is not None and math.isfinite(float(volatility_20d))) else 0.02

        if u_ret < 0.0 and downside_semi_volatility is not None and math.isfinite(float(downside_semi_volatility)):
            eff_vol = max(0.005, float(downside_semi_volatility))
        else:
            eff_vol = vol_clean

        vol_5d = eff_vol * math.sqrt(5.0)
        z_unrealized = u_ret / vol_5d if vol_5d > 0.0 else 0.0

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

        return float(upper_mult), float(lower_mult)

    @staticmethod
    def compute_downside_semi_volatility(
        returns_matrix: np.ndarray,
        target_return: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        F43: Computes upside volatility sigma_i^+, downside semi-volatility sigma_i^-,
        and downside asymmetry ratio D_i = sigma_i^- / sigma_i^+.
        """
        R = np.asarray(returns_matrix, dtype=float)
        if R.ndim == 1:
            R = R.reshape(-1, 1)
        T, n = R.shape
        if T < 3 or n == 0:
            return np.full(n, 0.02), np.full(n, 0.02), np.ones(n)

        diff = R - target_return
        upside = np.maximum(diff, 0.0)
        downside = np.minimum(diff, 0.0)

        sigma_plus = np.sqrt(np.maximum(np.mean(upside ** 2, axis=0), 1e-8))
        sigma_minus = np.sqrt(np.maximum(np.mean(downside ** 2, axis=0), 1e-8))
        downside_ratio = np.clip(sigma_minus / sigma_plus, 0.20, 5.0)

        return sigma_plus, sigma_minus, downside_ratio

    @staticmethod
    def compute_component_cvar_risk_contributions(
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        k_alpha: float = 2.40,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        F43: Computes Euler marginal risk contribution MRC_i and percentage tail risk contribution TRC_i:
            MRC_i = k_alpha * (Sigma w)_i / sigma_p
            TRC_i = w_i * (Sigma w)_i / (w^T Sigma w)
        """
        w = np.asarray(weights, dtype=float)
        port_var = float(w @ cov_matrix @ w)
        port_std = math.sqrt(max(1e-8, port_var))

        cov_w = cov_matrix @ w
        mrc = k_alpha * (cov_w / port_std)
        trc = (w * cov_w) / max(1e-8, port_var)
        return mrc, trc

    @staticmethod
    def compute_higher_order_co_moments(
        returns_matrix: np.ndarray,
        market_returns: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes systematic higher-order co-skewness and co-kurtosis vectors:
            s_i^coskew = E[ \tilde{r}_i \tilde{r}_m^2 ] / (sigma_i * sigma_m^2)
            k_i^cokurt = E[ \tilde{r}_i \tilde{r}_m^3 ] / (sigma_i * sigma_m^3)
        where \tilde{r}_i, \tilde{r}_m are demeaned asset and market returns.
        """
        R = np.asarray(returns_matrix, dtype=float)
        if R.ndim == 1:
            R = R.reshape(-1, 1)
        T, n = R.shape
        if T < 5 or n == 0:
            return np.zeros(n), np.full(n, 3.0)

        # Demean returns
        R_mean = np.nanmean(R, axis=0, keepdims=True)
        R_tilde = np.nan_to_num(R - R_mean, nan=0.0)

        # Market returns (equal-weighted cross-sectional return if not provided)
        if market_returns is not None and len(market_returns) == T:
            r_m = np.asarray(market_returns, dtype=float)
        else:
            r_m = np.mean(R, axis=1)

        r_m_mean = np.nanmean(r_m)
        r_m_tilde = np.nan_to_num(r_m - r_m_mean, nan=0.0)

        sigma_i = np.sqrt(np.maximum(np.mean(R_tilde ** 2, axis=0), 1e-8))
        sigma_m = math.sqrt(max(float(np.mean(r_m_tilde ** 2)), 1e-8))

        r_m2 = r_m_tilde ** 2
        r_m3 = r_m_tilde ** 3

        # E[ \tilde{r}_i \tilde{r}_m^2 ]
        co_skew_num = np.mean(R_tilde * r_m2[:, np.newaxis], axis=0)
        co_skew = co_skew_num / (sigma_i * (sigma_m ** 2))

        # E[ \tilde{r}_i \tilde{r}_m^3 ]
        co_kurt_num = np.mean(R_tilde * r_m3[:, np.newaxis], axis=0)
        co_kurt = co_kurt_num / (sigma_i * (sigma_m ** 3))

        # Clean numerical outliers
        co_skew = np.clip(np.nan_to_num(co_skew, nan=0.0), -5.0, 5.0)
        co_kurt = np.clip(np.nan_to_num(co_kurt, nan=3.0), -2.0, 15.0)

        return co_skew, co_kurt

    @staticmethod
    def estimate_gpd_tail_index(
        returns_matrix: np.ndarray,
        tail_quantile: float = 0.90,
    ) -> float:
        """
        Estimates the Generalized Pareto Distribution (GPD) dynamic tail index xi in [0.05, 0.45]
        using Hill's heavy-tail order statistic estimator on lower tail portfolio/asset losses.
        xi approx 0.05 -> near-Gaussian thin tail.
        xi approx 0.25 -> Student-t fat tail.
        xi approx 0.40+ -> Fréchet heavy tail / crisis regime.
        """
        R = np.asarray(returns_matrix, dtype=float)
        if R.ndim == 1:
            losses = -np.nan_to_num(R, nan=0.0)
        else:
            losses = -np.nan_to_num(np.mean(R, axis=1), nan=0.0)

        losses = losses[np.isfinite(losses)]
        T = len(losses)
        if T < 10:
            return 0.15

        u = float(np.quantile(losses, tail_quantile))
        excesses = losses[losses > u] - u
        excesses = excesses[excesses > 1e-7]
        K = len(excesses)
        if K < 3:
            return 0.15

        # Hill's estimator on sorted positive excesses: Y_{(1)} <= ... <= Y_{(K)}
        sorted_excesses = np.sort(excesses)
        y_min = sorted_excesses[0]
        log_ratios = np.log(sorted_excesses / y_min)
        xi_hat = float(np.mean(log_ratios))
        return float(np.clip(xi_hat, 0.05, 0.45))

    @classmethod
    def resolve_market_cost_bps(
        cls,
        symbol: Optional[str] = None,
        market: Optional[str] = None,
        default_cost_bps: float = 20.0,
    ) -> float:
        """
        Resolves granular 5-market spread and tax friction cost in basis points (bps):
        - KOSDAQ: 35.0 bps (18 bps STT + 2 bps fee + 15 bps half-spread)
        - KOSPI: 25.0 bps (18 bps STT + 2 bps fee + 5 bps half-spread)
        - RUSSELL2000: 16.0 bps (0.5 bps reg fee + 15.5 bps half-spread)
        - NASDAQ: 7.0 bps (0.5 bps reg fee + 6.5 bps half-spread)
        - SP500: 5.0 bps (0.5 bps reg fee + 4.5 bps half-spread)
        """
        if market:
            m_str = str(market).upper().strip()
            if "KOSDAQ" in m_str or m_str in ("KQ", "KOSDAQ_INDEX"):
                return 35.0
            if "KOSPI" in m_str or m_str in ("KS", "KOSPI_INDEX"):
                return 25.0
            if "RUSSELL" in m_str or "R2000" in m_str or m_str == "RUSSELL2000":
                return 16.0
            if "NASDAQ" in m_str or "NDX" in m_str:
                return 7.0
            if "SP500" in m_str or "S&P500" in m_str or "SPX" in m_str or "S&P" in m_str:
                return 5.0

        if symbol:
            s_str = str(symbol).upper().strip()
            if s_str.endswith(".KQ"):
                return 35.0
            if s_str.endswith(".KS") or (s_str.split(".")[0].isdigit() and len(s_str.split(".")[0]) == 6):
                return 25.0

        return float(default_cost_bps)


    @staticmethod
    def compute_returns_matrix(
        symbols: List[str],
        prices_dict: Dict[str, pd.DataFrame],
        lookback: int = 60,
        fx_series: Optional[pd.Series] = None,
        base_currency: str = "KRW"
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Extracts synchronized daily return series for a universe of symbols.
        Supports cross-border multi-currency FX translation (USD/KRW) to ensure
        unbiased portfolio covariance and capture realistic currency-hedge correlations.
        """
        close_series = {}
        base_curr_norm = str(base_currency).upper().strip()
        for sym in symbols:
            candidates = [sym, str(sym).upper(), str(sym).lower()]
            if str(sym).endswith(('.KS', '.KQ')):
                candidates.append(str(sym).split('.')[0])
            elif str(sym).isdigit():
                candidates.extend([f"{sym}.KS", f"{sym}.KQ"])

            p_df = None
            if prices_dict and isinstance(prices_dict, dict):
                for c_sym in candidates:
                    if c_sym in prices_dict:
                        p_df = prices_dict[c_sym]
                        break

            if p_df is not None and not p_df.empty:
                c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
                if c_col:
                    s = p_df[c_col].dropna()
                    if len(s) >= 10:
                        s_tail = s.tail(lookback).copy()
                        # Cross-Border FX currency harmonization
                        if fx_series is not None and not fx_series.empty:
                            sym_str = str(sym)
                            is_krx = sym_str.isdigit() or sym_str.endswith(('.KS', '.KQ'))
                            try:
                                first_valid_fx = float(fx_series.dropna().iloc[0]) if not fx_series.dropna().empty else 1350.0
                                aligned_fx = fx_series.reindex(s_tail.index).ffill().fillna(first_valid_fx)
                                if not is_krx and base_curr_norm == "KRW":
                                    s_tail = s_tail * aligned_fx
                                elif is_krx and base_curr_norm == "USD":
                                    s_tail = s_tail / aligned_fx
                            except Exception:
                                pass
                        close_series[sym] = s_tail

        if not close_series:
            return pd.DataFrame(), []

        prices_df = pd.DataFrame(close_series).ffill()
        returns_df = prices_df.pct_change().dropna(how='all').fillna(0.0)
        valid_symbols = [s for s in symbols if s in returns_df.columns]
        return returns_df, valid_symbols

    @staticmethod
    def compute_hybrid_ewma_covariance(
        returns_df: pd.DataFrame,
        halflife: int = 15,
        lw_weight: float = 0.40
    ) -> np.ndarray:
        """
        Computes hybrid covariance matrix: (1 - lw_weight) * EWMA + lw_weight * Ledoit-Wolf Shrinkage.
        Captures fast volatility/correlation spikes without lagging 60 days, while maintaining
        positive-definiteness and well-conditioned numerical stability.
        """
        clean_df = returns_df.fillna(0.0)
        T, n = clean_df.shape
        if T <= 2 or n <= 1:
            cov_val = clean_df.cov().fillna(0.0).values if n > 0 else np.eye(max(n, 1))
            return shrink_covariance_matrix(cov_val, n_samples=max(T, 1))

        # EWMA weights with exponential decay
        alpha = 1.0 - np.exp(-np.log(2.0) / max(halflife, 2))
        weights = (1.0 - alpha) ** np.arange(T - 1, -1, -1)
        w_sum = weights.sum()
        if w_sum > 0:
            weights /= w_sum
        else:
            weights = np.full(T, 1.0 / T)

        vals = clean_df.values  # T x n
        mean_w = np.sum(vals * weights[:, None], axis=0)
        demeaned = vals - mean_w
        ewma_cov = (demeaned.T * weights) @ demeaned

        # Ledoit-Wolf Shrunk sample cov
        sample_cov = clean_df.cov().fillna(0.0).values
        shrunk_cov = shrink_covariance_matrix(sample_cov, n_samples=T)

        # Hybrid blend
        hybrid_cov = (1.0 - lw_weight) * ewma_cov + lw_weight * shrunk_cov
        # Symmetrize and ensure diagonal positivity
        hybrid_cov = 0.5 * (hybrid_cov + hybrid_cov.T)
        min_diag = np.min(np.diag(hybrid_cov))
        if min_diag <= 0:
            hybrid_cov += (abs(min_diag) + 1e-6) * np.eye(n)
        return cast(np.ndarray, hybrid_cov)

    def compute_dynamic_regime_blend_weights(
        self,
        regime: Optional[Union[str, int, Dict[str, float]]] = "BULL_LOW_VOL",
        vix_val: Optional[float] = None,
        crisis_severity: float = 0.0,
        apply_ema: bool = False,
        ema_halflife: float = 5.0,
    ) -> Dict[str, float]:
        """
        Continuous 4-Model Markov Blending:
        Computes blended confidence weights across 4 paradigms:
            c(t) = sum_m pi_{t, m} * c^(m)
        where c^(m) = [w_bl, w_herc, w_rp, w_cvar]^T from REGIME_OPTIMIZER_BLENDS.
        Ensures normalized sum = 1.0000 and backward compatibility with string/int regimes.
        Dynamically tilts towards EVT-CVaR and Risk Parity in high volatility / crisis regimes.
        """
        blend_cfg = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        v_vol = 0.0
        c_crisis = max(0.0, min(1.0, float(crisis_severity)))

        if isinstance(regime, dict):
            regime_probs = regime
            tot_p = sum(max(0.0, float(v)) for v in regime_probs.values())
            if tot_p > 0:
                for r_k, r_p in regime_probs.items():
                    norm_p = max(0.0, float(r_p)) / tot_p
                    r_str = str(r_k).upper()
                    sub_cfg = self.REGIME_OPTIMIZER_BLENDS.get(r_str, self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"])
                    for m_k in blend_cfg:
                        blend_cfg[m_k] += norm_p * sub_cfg[m_k]
                    if "CRISIS" in r_str:
                        c_crisis = max(c_crisis, norm_p)
                    if "HIGH_VOL" in r_str:
                        v_vol = max(v_vol, norm_p)
            else:
                blend_cfg = dict(self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"])
        else:
            if isinstance(regime, int):
                int_map = {
                    0: "BULL_LOW_VOL", 1: "BULL_HIGH_VOL",
                    2: "SIDEWAYS_LOW_VOL", 3: "SIDEWAYS_HIGH_VOL",
                    4: "BEAR_LOW_VOL", 5: "BEAR_HIGH_VOL",
                    6: "CRISIS"
                }
                reg_str = int_map.get(regime, "SIDEWAYS_LOW_VOL")
            else:
                reg_str = str(regime).upper() if regime else "BULL_LOW_VOL"

            if "CRISIS" in reg_str:
                c_crisis = max(c_crisis, 1.0)
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS["CRISIS"]
            elif reg_str in self.REGIME_OPTIMIZER_BLENDS:
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS[reg_str]
            elif "BEAR" in reg_str:
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS["BEAR_HIGH_VOL" if "HIGH" in reg_str else "BEAR_LOW_VOL"]
            elif "BULL" in reg_str:
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS["BULL_HIGH_VOL" if "HIGH" in reg_str else "BULL_LOW_VOL"]
            else:
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"]

            if "HIGH_VOL" in reg_str:
                v_vol = max(v_vol, 1.0)
            blend_cfg = dict(sub_cfg)

        # Dynamic VIX shock volatility indicator
        if vix_val is not None and math.isfinite(float(vix_val)):
            vix_f = float(vix_val)
            v_vol = max(v_vol, 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, (vix_f - 20.0) / 3.0)))))

        # Dynamic tilt towards EVT-CVaR and Risk Parity in high volatility / crisis regimes
        if v_vol > 0.10 or c_crisis > 0.05:
            cvar_boost = 0.20 * v_vol + 0.40 * c_crisis
            rp_boost = 0.10 * v_vol * (1.0 - c_crisis)
            bl_suppress = max(0.0, 1.0 - 0.70 * v_vol - 0.90 * c_crisis)

            blend_cfg["bl"] *= bl_suppress
            blend_cfg["cvar"] += cvar_boost
            blend_cfg["rp"] += rp_boost

        # Ensure normalized sum = 1.0000
        tot_b = sum(blend_cfg.values())
        if tot_b > 0:
            blend_cfg = {k: float(v / tot_b) for k, v in blend_cfg.items()}
        else:
            blend_cfg = dict(self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"])

        # Optional Temporal EMA smoothing with 5-day half-life
        if apply_ema and hasattr(self, "_last_blend_weights") and self._last_blend_weights:
            alpha_blend = 1.0 - math.exp(-math.log(2.0) / max(1.0, float(ema_halflife)))
            smooth_cfg = {}
            for k in blend_cfg:
                smooth_cfg[k] = alpha_blend * blend_cfg[k] + (1.0 - alpha_blend) * self._last_blend_weights.get(k, blend_cfg[k])
            tot_s = sum(smooth_cfg.values())
            blend_cfg = {k: float(v / tot_s) for k, v in smooth_cfg.items()}

        self._last_blend_weights = dict(blend_cfg)
        return blend_cfg

    def compute_information_theoretic_blend_weights(
        self,
        regime: Optional[Union[str, int, Dict[str, float]]] = "BULL_LOW_VOL",
        vix_val: Optional[float] = None,
        crisis_severity: float = 0.0,
        alpha_dispersion: Optional[float] = None,
        diversification_ratio: Optional[float] = None,
        gpd_tail_index: Optional[float] = None,
        market_coskewness: Optional[float] = None,
        temperature: float = 1.0,
    ) -> Dict[str, float]:
        """
        F43: Continuous Information-Theoretic 4-Model Reliability Optimization.
        Computes dynamic posterior log-odds updates Delta ell_m across:
        [Black-Litterman, HERC, Risk Parity, EVT-CVaR]
        and applies temperature-controlled Softmax blending.
        """
        # 1. Base Prior w^(0)
        w_prior = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        c_crisis = max(0.0, min(1.0, float(crisis_severity)))
        v_vol = 0.0
        u_entropy = 0.0

        if isinstance(regime, dict):
            probs = [max(0.0, float(v)) for v in regime.values()]
            tot_p = sum(probs)
            if tot_p > 0:
                norm_probs = [p / tot_p for p in probs]
                # Normalized Shannon entropy H_norm in [0, 1]
                h_val = -sum(p * math.log(p + 1e-12) for p in norm_probs if p > 0)
                u_entropy = float(np.clip(h_val / math.log(max(2, len(probs))), 0.0, 1.0))
                for (r_k, r_v), p_norm in zip(regime.items(), norm_probs):
                    r_str = str(r_k).upper()
                    sub_cfg = self.REGIME_OPTIMIZER_BLENDS.get(r_str, self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"])
                    for m_k in w_prior:
                        w_prior[m_k] += p_norm * sub_cfg[m_k]
                    if "CRISIS" in r_str:
                        c_crisis = max(c_crisis, p_norm)
                    if "HIGH_VOL" in r_str:
                        v_vol = max(v_vol, p_norm)
            else:
                w_prior = dict(self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"])
        else:
            if isinstance(regime, int):
                int_map = {
                    0: "BULL_LOW_VOL", 1: "BULL_HIGH_VOL",
                    2: "SIDEWAYS_LOW_VOL", 3: "SIDEWAYS_HIGH_VOL",
                    4: "BEAR_LOW_VOL", 5: "BEAR_HIGH_VOL",
                    6: "CRISIS"
                }
                reg_str = int_map.get(regime, "SIDEWAYS_LOW_VOL")
            else:
                reg_str = str(regime).upper() if regime else "BULL_LOW_VOL"

            if "CRISIS" in reg_str:
                c_crisis = max(c_crisis, 1.0)
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS["CRISIS"]
            elif reg_str in self.REGIME_OPTIMIZER_BLENDS:
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS[reg_str]
            elif "BEAR" in reg_str:
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS["BEAR_HIGH_VOL" if "HIGH" in reg_str else "BEAR_LOW_VOL"]
            elif "BULL" in reg_str:
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS["BULL_HIGH_VOL" if "HIGH" in reg_str else "BULL_LOW_VOL"]
            else:
                sub_cfg = self.REGIME_OPTIMIZER_BLENDS["SIDEWAYS_LOW_VOL"]

            w_prior = dict(sub_cfg)
            if "HIGH_VOL" in reg_str:
                v_vol = max(v_vol, 1.0)
            u_entropy = 0.0

        # VIX shock volatility indicator
        if vix_val is not None and math.isfinite(float(vix_val)):
            vix_f = float(vix_val)
            v_vol = max(v_vol, 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, (vix_f - 20.0) / 3.0)))))

        disp = float(alpha_dispersion) if (alpha_dispersion is not None and math.isfinite(float(alpha_dispersion))) else 0.02
        dr = float(diversification_ratio) if (diversification_ratio is not None and math.isfinite(float(diversification_ratio))) else 1.30
        xi = float(gpd_tail_index) if (gpd_tail_index is not None and math.isfinite(float(gpd_tail_index))) else 0.15
        coskew_mkt = float(market_coskewness) if (market_coskewness is not None and math.isfinite(float(market_coskewness))) else 0.0

        # 2. Compute Log-Odds Updates Delta ell_m
        delta_ell = {
            "bl": (
                0.35 * math.tanh((disp - 0.025) / 0.015)
                - 0.50 * (u_entropy ** 2)
                - 1.20 * (v_vol + 1.50 * c_crisis)
                + 0.20 * math.tanh(coskew_mkt)
            ),
            "herc": (
                0.40 * math.tanh((dr - 1.30) / 0.40)
                + 0.25 * u_entropy * (1.0 - c_crisis)
                - 0.30 * c_crisis
            ),
            "rp": (
                0.50 * math.tanh((dr - 1.30) / 0.35)
                - 0.40 * c_crisis
                - 0.20 * v_vol
            ),
            "cvar": (
                0.80 * v_vol
                + 1.40 * c_crisis
                + 0.60 * ((xi - 0.15) / 0.30)
                - 0.40 * math.tanh(coskew_mkt)
                + 0.35 * max(0.0, 1.20 - dr)
            ),
        }

        # 3. Temperature-controlled Softmax Blending
        tau = max(0.10, float(temperature))
        log_odds = {k: math.log(max(1e-4, w_prior[k])) + delta_ell[k] for k in w_prior}
        max_log = max(log_odds.values())
        exps = {k: math.exp((v - max_log) / tau) for k, v in log_odds.items()}
        tot_exp = sum(exps.values())

        return {k: float(v / tot_exp) for k, v in exps.items()}

    def calculate_cvar_weights(
        self,
        returns_df: pd.DataFrame,
        confidence_level: float = 0.95,
        predicted_returns: Optional[np.ndarray] = None,
        lambda_alpha: float = 0.50,
        cov_matrix: Optional[np.ndarray] = None,
        regime: Optional[Union[str, int, Dict[str, float]]] = None,
        use_downside_semi_cov: bool = True,
        semi_cov_weight: float = 0.35,
    ) -> np.ndarray:
        """
        Rockafellar & Uryasev (2000) Convex Conditional Value-at-Risk (CVaR) Minimization
        with Alpha-Tilt (Mean-CVaR Optimization) and Parametric EVT-CVaR Tail-Stressed Integration.
        When tail-stressed covariance is available, utilizes parametric Student-t EVT tail modeling
        to prevent extreme small-sample estimation variance under short lookback windows (T <= 60).
        F28: Downside Semi-Covariance (Sortino) EVT-CVaR Optimization:
        Blends downside semi-covariance (Sigma^-) into effective covariance:
            Sigma_effective = (1 - lambda_semi) * Sigma_tail + lambda_semi * Sigma^-
        penalizing only downside deviations while preserving upside momentum.
        """
        n = returns_df.shape[1]
        T = returns_df.shape[0]
        if n == 0 or T < 5:
            return np.full(max(n, 1), 1.0 / max(n, 1))
        if n == 1:
            return np.array([1.0])

        alpha = float(np.clip(confidence_level, 0.90, 0.99))

        # Dynamic alpha-tilt modulation in high volatility / crisis regimes
        v_vol = 0.0
        c_crisis = 0.0
        if isinstance(regime, dict):
            for r_k, r_p in regime.items():
                r_str = str(r_k).upper()
                if "CRISIS" in r_str:
                    c_crisis = max(c_crisis, float(r_p))
                if "HIGH_VOL" in r_str:
                    v_vol = max(v_vol, float(r_p))
        elif regime:
            reg_str = str(regime).upper()
            if "CRISIS" in reg_str:
                c_crisis = 1.0
            if "HIGH_VOL" in reg_str:
                v_vol = 1.0

        eff_lambda_alpha = float(lambda_alpha) * max(0.05, 1.0 - 0.85 * v_vol - 0.90 * c_crisis)

        has_alpha = (
            predicted_returns is not None
            and len(predicted_returns) == n
            and np.all(np.isfinite(predicted_returns))
            and eff_lambda_alpha > 0
        )
        if has_alpha:
            p_rets = np.asarray(predicted_returns, dtype=float)
            if np.any(np.abs(p_rets) >= 1.0):
                p_rets = p_rets / 100.0  # normalize percentage to decimal
        else:
            p_rets = np.zeros(n)

        max_w = min(1.0, max(self.max_single_weight, 1.0 / max(n - 1, 1)))

        # Feature 10 & F28: Parametric EVT-CVaR using Tail-Stressed & Downside Semi-Covariance Matrix
        # Prevents extreme sample underestimation when lookback window T is short (T <= 60)
        eff_base_cov = cov_matrix
        if eff_base_cov is None and returns_df is not None and returns_df.shape[0] >= 5 and returns_df.shape[1] == n:
            try:
                eff_base_cov = returns_df.cov().values
            except Exception:
                eff_base_cov = None

        if eff_base_cov is not None and eff_base_cov.shape == (n, n) and np.all(np.isfinite(eff_base_cov)):
            try:
                # Student-t EVT heavy-tail Cornish-Fisher CVaR expansion multiplier
                # For nu=5 degrees of freedom at alpha=0.95, k_alpha approx 2.40 (vs Gaussian 2.06)
                k_alpha = 2.40 if alpha >= 0.95 else 2.10

                # F28: Construct effective covariance with downside semi-covariance
                eff_cov = eff_base_cov
                if use_downside_semi_cov and returns_df is not None and len(returns_df) >= 5:
                    try:
                        from src.risk.portfolio_allocator import PortfolioAllocator
                        semi_cov = PortfolioAllocator.compute_downside_semi_cov(
                            returns_matrix=returns_df.values,
                            base_cov=eff_base_cov,
                            target_return=0.0,
                            shrinkage_intensity=0.20
                        )
                        if semi_cov is not None and semi_cov.shape == (n, n) and np.all(np.isfinite(semi_cov)):
                            lam_semi = float(np.clip(semi_cov_weight, 0.0, 1.0))
                            eff_cov = (1.0 - lam_semi) * eff_base_cov + lam_semi * semi_cov
                    except Exception as e_semi:
                        logger.debug(f"[EVT-CVaR Downside Semi-Cov] Fallback to base cov: {e_semi}")
                        eff_cov = eff_base_cov

                # F37: Dynamic Cornish-Fisher EVT-CVaR tail expansion & Hill/Pickands GPD dynamic tail index
                z_alpha = 1.645 if alpha >= 0.95 else 1.282
                co_skew, co_kurt = None, None
                eff_xi = 0.15
                if returns_df is not None and returns_df.shape[0] >= 5 and returns_df.shape[1] == n:
                    try:
                        co_skew, co_kurt = self.compute_higher_order_co_moments(returns_df.values)
                        eff_xi = self.estimate_gpd_tail_index(returns_df.values, tail_quantile=0.90)
                    except Exception as e_moments:
                        logger.debug(f"[EVT-CVaR Co-Moments] Fallback: {e_moments}")

                def obj_evt_cvar(w):
                    port_var = float(w @ eff_cov @ w)
                    port_std = math.sqrt(max(1e-8, port_var))
                    # F37: Dynamic Cornish-Fisher EVT-CVaR tail expansion adapting to portfolio co-skewness and co-kurtosis
                    if co_skew is not None and co_kurt is not None:
                        s_p = float(np.dot(w, co_skew))
                        k_p = float(np.dot(w, co_kurt - 3.0))
                        k_alpha_w = float(np.clip(
                            z_alpha + 0.41 - ((z_alpha ** 2 - 1.0) / 6.0) * s_p + 0.10 * max(0.0, k_p) + 1.25 * eff_xi,
                            2.05, 3.20
                        ))
                    else:
                        k_alpha_w = float(np.clip(k_alpha + 1.25 * (eff_xi - 0.15), 2.05, 3.20))

                    cvar_est = k_alpha_w * port_std
                    if has_alpha:
                        return cvar_est - float(eff_lambda_alpha * np.dot(w, p_rets))
                    return cvar_est

                def constr_sum(w):
                    return float(np.sum(w) - 1.0)

                w0 = np.full(n, 1.0 / n)
                bounds = [(0.0, max_w) for _ in range(n)]

                res = minimize(
                    obj_evt_cvar,
                    w0,
                    method="SLSQP",
                    bounds=bounds,
                    constraints=[{"type": "eq", "fun": constr_sum}],
                    options={"maxiter": 150, "ftol": 1e-5}
                )

                if res.success and np.all(np.isfinite(res.x)):
                    w = np.clip(res.x, 0.0, max_w)
                    tot = np.sum(w)
                    return w / tot if tot > 0 else np.full(n, 1.0 / n)
            except Exception as e:
                logger.debug(f"[EVT-CVaR Parametric] Solver fallback to empirical: {e}")

        # Empirical Sample Rockafellar & Uryasev Optimization
        R = returns_df.values  # T x n
        try:
            def obj_cvar(var):
                w = var[:n]
                cvar_part = float(var[n] + (1.0 / ((1.0 - alpha) * T)) * np.sum(var[n + 1:]))
                if has_alpha:
                    return cvar_part - float(eff_lambda_alpha * np.dot(w, p_rets))
                return cvar_part

            def constr_sum_w(var):
                return float(np.sum(var[:n]) - 1.0)

            bounds = [(0.0, max_w) for _ in range(n)] + [(None, None)] + [(0.0, None) for _ in range(T)]

            def constr_tail_losses(var):
                w = var[:n]
                gamma = var[n]
                u = var[n + 1:]
                return u + (R @ w) + gamma

            x0 = np.zeros(n + 1 + T)
            x0[:n] = 1.0 / n
            x0[n] = float(np.quantile(-R @ x0[:n], alpha))
            x0[n + 1:] = np.maximum(0.0, -R @ x0[:n] - x0[n])

            res = minimize(
                obj_cvar,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=[
                    {"type": "eq", "fun": constr_sum_w},
                    {"type": "ineq", "fun": constr_tail_losses},
                ],
                options={"maxiter": 150, "ftol": 1e-4}
            )

            if res.success and np.all(np.isfinite(res.x[:n])):
                w = np.clip(res.x[:n], 0.0, max_w)
                tot = np.sum(w)
                return w / tot if tot > 0 else np.full(n, 1.0 / n)
        except Exception as e:
            logger.debug(f"[CVaR Optimization] Solver fallback to inverse volatility: {e}")

        # Fallback to inverse volatility
        vols = np.maximum(returns_df.std().values, 1e-6)
        inv_v = 1.0 / vols
        return np.asarray(inv_v / np.sum(inv_v), dtype=float)

    def optimize_multi_model_blend(
        self,
        predicted_returns: np.ndarray,
        returns_df: pd.DataFrame,
        cov_matrix: np.ndarray,
        symbols: List[str],
        sectors: Optional[List[str]] = None,
        regime: Optional[Union[str, int, Dict[str, float]]] = "BULL_LOW_VOL",
        current_weights: Optional[np.ndarray] = None,
        advs: Optional[np.ndarray] = None,
        total_capital: float = 100_000_000.0,
        market_caps: Optional[np.ndarray] = None,
        factor_loadings: Optional[Any] = None,
        alpha_half_lives: Optional[Union[np.ndarray, Dict[str, float], float]] = None,
        darkpool_scores: Optional[Union[np.ndarray, Dict[str, float]]] = None,
        cost_scaling_factor: Optional[float] = None,
    ) -> np.ndarray:
        """
        Continuous 4-Model Regime-Adaptive Multi-Model Blending:
        Blends Black-Litterman, HERC, Risk Parity, and EVT-CVaR based on the current regime,
        then applies non-linear dark-pool-adjusted market impact penalty and Barra factor constraints.
        """
        n = len(symbols)
        if n == 0:
            return np.array([])
        if n == 1:
            return np.array([1.0])

        # Feature 9 & F43: Continuous Information-Theoretic 4-Model Reliability Blending
        alpha_disp = None
        if predicted_returns is not None and len(predicted_returns) == n:
            p_rets = np.asarray(predicted_returns, dtype=float)
            if np.any(np.abs(p_rets) >= 1.0):
                p_rets = p_rets / 100.0
            alpha_disp = float(np.nanstd(p_rets))

        dr_base = 1.30
        if cov_matrix is not None and cov_matrix.shape == (n, n):
            try:
                diag_vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-8))
                mean_vol = float(np.mean(diag_vols))
                eq_w = np.full(n, 1.0 / n)
                port_vol_eq = math.sqrt(max(1e-8, float(eq_w @ cov_matrix @ eq_w)))
                dr_base = float(mean_vol / port_vol_eq) if port_vol_eq > 0 else 1.30
            except Exception:
                dr_base = 1.30

        eff_xi = 0.15
        co_skew = None
        co_kurt = None
        mkt_coskew = 0.0
        if returns_df is not None and returns_df.shape[0] >= 5 and returns_df.shape[1] == n:
            try:
                co_skew, co_kurt = self.compute_higher_order_co_moments(returns_df.values)
                eff_xi = self.estimate_gpd_tail_index(returns_df.values, tail_quantile=0.90)
                mkt_coskew = float(np.nanmean(co_skew))
            except Exception:
                pass

        c_crisis = 0.0
        if isinstance(regime, dict):
            c_crisis = max(0.0, float(regime.get("CRISIS", 0.0)))
        elif regime and "CRISIS" in str(regime).upper():
            c_crisis = 1.0

        blend_cfg = self.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=c_crisis,
            alpha_dispersion=alpha_disp,
            diversification_ratio=dr_base,
            gpd_tail_index=eff_xi,
            market_coskewness=mkt_coskew,
        )

        # F37: Systematic Higher-Order Co-Moments Alpha Conviction Adjustment
        eff_predicted_returns = predicted_returns
        if predicted_returns is not None and len(predicted_returns) == n and co_skew is not None and co_kurt is not None:
            try:
                p_rets_arr = np.asarray(predicted_returns, dtype=float)
                # mu_i^adj = mu_i * (1 + lambda_skew * s_i^coskew - lambda_kurt * (k_i^cokurt - 3))
                co_tilt = np.clip(1.0 + 0.15 * co_skew - 0.05 * (co_kurt - 3.0), 0.20, 2.50)
                eff_predicted_returns = p_rets_arr * co_tilt
            except Exception as e_cm:
                logger.debug(f"[Higher-Order Co-Moments Tilt] Exception: {e_cm}")
                eff_predicted_returns = predicted_returns

        # 1. Model A: Black-Litterman Conviction (with CAPM Equilibrium Market-Cap Priors)
        w_bl = np.full(n, 1.0 / n)
        if blend_cfg["bl"] > 0:
            try:
                prior_w = None
                if market_caps is not None and len(market_caps) == n:
                    tot_cap = float(np.sum(market_caps))
                    if tot_cap > 0:
                        prior_w = np.asarray(market_caps, dtype=float) / tot_cap

                w_bl = calculate_black_litterman_weights(
                    cov_matrix=cov_matrix,
                    predicted_returns=eff_predicted_returns,
                    prior_weights=prior_w,
                    risk_aversion=self.risk_aversion,
                    symbols=symbols,
                    sectors=sectors,
                    max_single_stock_weight=self.max_single_weight,
                    max_sector_weight=self.max_sector_weight,
                    returns_are_percentage=False,
                    view_horizon=self.target_horizon,
                )
            except Exception as e:
                logger.debug(f"[BL] Failed, fallback to equal: {e}")
                w_bl = np.full(n, 1.0 / n)

        # 2. Model B: HERC (Hierarchical Equal Risk Contribution)
        w_herc = np.full(n, 1.0 / n)
        if blend_cfg["herc"] > 0:
            try:
                w_herc = calculate_herc_weights(
                    cov_matrix=cov_matrix,
                    symbols=symbols,
                    sectors=sectors,
                    max_k=min(5, max(2, n // 2)),
                    max_single_stock_weight=self.max_single_weight,
                    max_sector_weight=self.max_sector_weight,
                )
            except Exception as e:
                logger.debug(f"[HERC] Failed, fallback to HRP: {e}")
                w_hrp_raw = calculate_hrp_weights(cov_matrix, symbols=symbols, sectors=sectors)
                w_herc = np.array([w_hrp_raw.get(s, 0.0) for s in symbols], dtype=float) if isinstance(w_hrp_raw, dict) else np.asarray(w_hrp_raw, dtype=float)

        # 3. Model C: Equal Risk Contribution / Risk Parity
        w_rp = np.full(n, 1.0 / n)
        if blend_cfg["rp"] > 0:
            try:
                w_rp = calculate_risk_parity_weights(cov_matrix)
            except Exception as e:
                logger.debug(f"[RP] Failed, fallback: {e}")
                w_rp = np.full(n, 1.0 / n)

        # 4. Model D: Tail-Risk CVaR Minimizer with Alpha Tilt & Clayton Copula Tail Covariance
        w_cvar = np.full(n, 1.0 / n)
        if blend_cfg["cvar"] > 0:
            try:
                tail_cov = None
                if cov_matrix is not None:
                    try:
                        from src.risk.portfolio_allocator import PortfolioAllocator
                        tail_cov = PortfolioAllocator.compute_tail_stress_cov(
                            returns_df.values,
                            cov_matrix,
                            tail_quantile=0.10,
                            stress_weight=0.35,
                            use_clayton_copula=True
                        )
                    except Exception:
                        tail_cov = cov_matrix

                # Dynamic lambda_semi for F43
                v_vol_cvar = 1.0 if "HIGH_VOL" in str(regime).upper() else 0.0
                if isinstance(regime, dict):
                    v_vol_cvar = max(0.0, sum(float(v) for k, v in regime.items() if "HIGH_VOL" in str(k).upper()))
                dyn_semi_cov_weight = float(np.clip(
                    0.25 + 0.35 * v_vol_cvar + 0.40 * c_crisis + 0.20 * max(0.0, -mkt_coskew),
                    0.20, 0.75
                ))

                w_cvar = self.calculate_cvar_weights(
                    returns_df,
                    confidence_level=0.95,
                    predicted_returns=eff_predicted_returns,
                    lambda_alpha=0.50,
                    cov_matrix=tail_cov if tail_cov is not None else cov_matrix,
                    regime=regime,
                    use_downside_semi_cov=True,
                    semi_cov_weight=dyn_semi_cov_weight,
                )
            except Exception as e:
                logger.debug(f"[CVaR] Failed, fallback: {e}")
                w_cvar = np.full(n, 1.0 / n)

        # Composite Multi-Model Blended Weight
        w_composite = (
            blend_cfg["bl"] * w_bl +
            blend_cfg["herc"] * w_herc +
            blend_cfg["rp"] * w_rp +
            blend_cfg["cvar"] * w_cvar
        )

        # F43: Downside Sortino Tail Multiplier Tilting
        down_ratios = np.ones(n)
        if returns_df is not None and returns_df.shape[0] >= 3 and returns_df.shape[1] == n:
            try:
                _, _, down_ratios = self.compute_downside_semi_volatility(returns_df.values)
            except Exception:
                down_ratios = np.ones(n)

        if eff_predicted_returns is not None and len(eff_predicted_returns) == n:
            preds = np.asarray(eff_predicted_returns, dtype=float)
            p_std = float(np.nanstd(preds))
            p_mean = float(np.nanmean(preds))
            z_alpha = np.clip((preds - p_mean) / max(p_std, 0.01), -2.5, 2.5) if p_std > 1e-6 else np.zeros(n)

            coskew_pen = np.zeros(n)
            if co_skew is not None and len(co_skew) == n:
                coskew_pen = np.maximum(0.0, -np.nan_to_num(co_skew, nan=0.0))

            tilt_mult = np.exp(
                0.35 * z_alpha
                - 0.50 * np.maximum(0.0, down_ratios - 1.0)
                + 0.25 * np.maximum(0.0, 1.0 - down_ratios)
                - 0.25 * coskew_pen
            )
            w_composite = w_composite * tilt_mult

        tot_w = np.sum(w_composite)
        w_blended = w_composite / tot_w if tot_w > 0 else np.full(n, 1.0 / n)

        # 5. Apply Portfolio Constraints & Sector Neutralization on Equilibrium Target Portfolio w*
        w_target = apply_portfolio_constraints(
            w_blended,
            symbols=symbols,
            sectors=sectors,
            max_single_stock_weight=self.max_single_weight,
            max_sector_weight=self.max_sector_weight,
            factor_loadings=factor_loadings
        )

        # F43: Euler Component CVaR (CCVaR) Risk Budget Enforcement
        if cov_matrix is not None and cov_matrix.shape == (n, n) and n > 1:
            try:
                _, trc = self.compute_component_cvar_risk_contributions(w_target, cov_matrix)
                trc_cap = max(1.75 / n, 0.20)
                viol_mask = trc > trc_cap
                if np.any(viol_mask) and np.any(~viol_mask):
                    w_target[viol_mask] *= (trc_cap / trc[viol_mask])
                    tot_w = np.sum(w_target)
                    if tot_w < 1.0:
                        unalloc = 1.0 - tot_w
                        fav_scores = np.maximum(w_target[~viol_mask], 0.0)
                        sum_fav = np.sum(fav_scores)
                        if sum_fav > 0:
                            w_target[~viol_mask] += unalloc * (fav_scores / sum_fav)
                        else:
                            w_target[~viol_mask] += unalloc / np.sum(~viol_mask)
                    w_target = np.clip(w_target, 0.0, self.max_single_weight)
                    sum_w = np.sum(w_target)
                    if sum_w > 0:
                        w_target = w_target / sum_w
            except Exception as e_cvar_budget:
                logger.debug(f"[Component CVaR Budget Enforcement] Exception: {e_cvar_budget}")

        # 6. Dynamic Alpha Half-Life Convergence Speed (theta_i*) & Dark-Pool Adjusted Gatheral 3/2-Power Liquidity Impact
        if advs is not None and len(advs) == n and total_capital > 0:
            w_curr = current_weights if (current_weights is not None and len(current_weights) == n) else np.zeros(n)
            w_curr = np.nan_to_num(np.asarray(w_curr, dtype=float), nan=0.0)
            vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-6))
            daily_advs = np.maximum(np.asarray(advs, dtype=float), 1000.0)

            # Resolve effective alpha half-life tau_{1/2, i}
            if alpha_half_lives is not None:
                if isinstance(alpha_half_lives, (int, float)):
                    half_lives = np.full(n, float(alpha_half_lives))
                elif isinstance(alpha_half_lives, dict):
                    half_lives = np.array([float(alpha_half_lives.get(s, 10.0)) for s in symbols], dtype=float)
                elif len(alpha_half_lives) == n:
                    half_lives = np.asarray(alpha_half_lives, dtype=float)
                else:
                    half_lives = np.full(n, 10.0)
            else:
                # Default regime-informed alpha half-life
                base_hl = 10.0
                reg_str = str(regime).upper() if regime else ""
                if "CRISIS" in reg_str:
                    base_hl = 3.0
                elif "HIGH_VOL" in reg_str:
                    base_hl = 5.0
                elif "BULL_LOW_VOL" in reg_str:
                    base_hl = 15.0
                half_lives = np.full(n, base_hl)

            half_lives = np.maximum(half_lives, 0.5)
            # Continuous daily alpha decay intensity: lambda_alpha = ln(2) / tau_{1/2}
            lambda_alpha = np.log(2.0) / half_lives

            # Daily expected return proxy (alpha_daily)
            if predicted_returns is not None and len(predicted_returns) == n:
                p_rets = np.asarray(predicted_returns, dtype=float)
                if np.any(np.abs(p_rets) >= 1.0):
                    p_rets = p_rets / 100.0
                daily_alpha = np.maximum(0.0, p_rets) / max(1.0, float(self.target_horizon))
            else:
                daily_alpha = np.full(n, 0.002)

            # Trade delta in portfolio weight and currency
            weight_gaps = w_target - w_curr
            delta_trades = np.abs(weight_gaps) * total_capital

            # Sizing participation ratio for the entire gap: delta_trades / daily_advs
            gap_adv_ratios = delta_trades / daily_advs

            # Feature 11 & F33: Dark-Pool Adjusted Gatheral 3/2-Power Market Impact with Slippage Scaling
            # kappa_eff = kappa_0 * cost_scaling_factor * (1.0 - phi_dark)
            # phi_dark = min(0.60, 1.2 * darkpool_score)
            kappa_0 = 1.0
            slippage_cost_scale = float(cost_scaling_factor) if cost_scaling_factor is not None else 1.0
            if cost_scaling_factor is None:
                try:
                    from src.execution.slippage_feedback import SlippageFeedbackEngine
                    slip_engine = SlippageFeedbackEngine()
                    slip_metrics = slip_engine.calculate_realized_slippage()
                    if slip_metrics and hasattr(slip_metrics, "cost_scaling_factor"):
                        slippage_cost_scale = float(slip_metrics.cost_scaling_factor or 1.0)
                    elif slip_metrics and hasattr(slip_metrics, "recommended_market_impact_multiplier"):
                        slippage_cost_scale = float(slip_metrics.recommended_market_impact_multiplier or 1.0)
                except Exception as e_slip:
                    logger.debug(f"[UnifiedPortfolioAllocator] Slippage feedback query exception: {e_slip}")
                    slippage_cost_scale = 1.0

            if darkpool_scores is not None:
                if isinstance(darkpool_scores, dict):
                    dp_arr = np.array([float(darkpool_scores.get(s, 0.0) or 0.0) for s in symbols], dtype=float)
                elif len(darkpool_scores) == n:
                    dp_arr = np.asarray(darkpool_scores, dtype=float)
                else:
                    dp_arr = np.zeros(n, dtype=float)
                dp_arr = np.nan_to_num(dp_arr, nan=0.0)
                phi_dark = np.minimum(0.60, 1.2 * np.maximum(0.0, dp_arr))
                kappa_eff = kappa_0 * slippage_cost_scale * (1.0 - phi_dark)
            else:
                kappa_eff = np.full(n, kappa_0 * slippage_cost_scale, dtype=float)

            kappa_eff = np.maximum(kappa_eff, 0.20)

            # Closed-Form Optimal Convergence Velocity:
            # theta_impact* = ((daily_alpha + lambda_alpha) / (1.5 * kappa_eff * vols))^2 * (ADV / delta_trades)
            theta_impact = np.ones(n, dtype=float)
            active_mask = (delta_trades > 1e-6) & (gap_adv_ratios > 1e-6)
            if np.any(active_mask):
                numerator = daily_alpha[active_mask] + lambda_alpha[active_mask]
                denominator = 1.5 * kappa_eff[active_mask] * vols[active_mask]
                trade_scaling = 1.0 / gap_adv_ratios[active_mask]
                theta_impact[active_mask] = ((numerator / denominator) ** 2) * trade_scaling

            # Dynamic maximum ADV liquidity participation cap (5% for slow alpha, up to 15% for urgent fast alpha)
            # max_adv_frac_i = 0.05 + 0.10 * exp(-tau_{1/2, i} / 3.0)
            max_adv_fracs = 0.05 + 0.10 * np.exp(-half_lives / 3.0)
            max_delta_w = (max_adv_fracs * daily_advs) / float(total_capital)

            # Bounded desired weight step
            theta_bounded = np.clip(theta_impact, 0.15, 1.0)
            theta_bounded[~active_mask] = 1.0
            delta_w_desired = theta_bounded * weight_gaps

            # Bound executed step by maximum liquidity capacity: |delta_w| <= max_delta_w
            delta_w_exec = np.sign(delta_w_desired) * np.minimum(np.abs(delta_w_desired), max_delta_w)

            # Execute partial convergence step: w_{t+1, i} = w_{t, i} + delta_w_exec
            w_next = w_curr + delta_w_exec
            w_next = np.clip(w_next, 0.0, self.max_single_weight)

            # Feature 8: Route unallocated liquidity-constrained capital to cash buffer!
            # DO NOT re-normalize or divide by sum(w_next)
            final_w = w_next
        else:
            final_w = w_target

        return final_w

    def apply_target_volatility_scaling(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        regime: Optional[Union[str, int, Dict[str, float]]] = "BULL_LOW_VOL",
        expected_returns: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, float]:
        """
        Dynamic Target Volatility (12% Annualized) Scaling & Cash Drag Eliminator:
        Scales total portfolio allocation up or down based on current realized volatility.
        - In Bull Low-Vol: scales allocation up to 98% (eliminating cash drag).
        - In High-Conviction Bull (Sharpe >= 1.5): scales allocation up to 100% (Kelly boost).
        - In Bear High-Vol / Crisis: scales allocation down to 40~50% (preserving cash).
        F37: Entropy-Weighted Adaptive Target Volatility Scaling under Shannon regime uncertainty:
            U_regime = H(pi) / ln(6)
            Scales target volatility by (1 - 0.25 * U_regime) and allocation cap by (1 - 0.20 * U_regime).
        """
        n = len(weights)
        if n == 0 or cov_matrix.shape[0] != n:
            return weights, self.default_max_total_allocation

        port_var = float(weights.T @ cov_matrix @ weights)
        annualized_port_vol = float(np.sqrt(max(1e-8, port_var * 252.0)))

        # F43: Quadratic Shannon Regime Entropy Uncertainty & Crisis Severity
        u_regime = 0.0
        c_crisis = 0.0
        if isinstance(regime, dict) and len(regime) > 0:
            probs = np.array([max(0.0, float(v)) for v in regime.values()], dtype=float)
            tot_p = np.sum(probs)
            if tot_p > 0:
                probs = probs / tot_p
                # Shannon entropy H(pi) = -sum(pi * ln(pi))
                h_pi = -float(np.sum([p * math.log(p + 1e-12) for p in probs if p > 0]))
                u_regime = float(np.clip(h_pi / math.log(6.0), 0.0, 1.0))
            c_crisis = max(0.0, float(regime.get("CRISIS", 0.0)))
        elif regime and isinstance(regime, str):
            u_regime = 0.0
            c_crisis = 1.0 if "CRISIS" in str(regime).upper() else 0.0

        if isinstance(regime, dict):
            regime_key = max(regime, key=regime.get) if regime else "BULL_LOW_VOL"
            regime_str = str(regime_key).upper()
        else:
            regime_str = str(regime).upper() if regime else ""
        if "BULL" in regime_str:
            max_alloc_cap = 0.98  # Cash drag eliminator
            min_alloc_floor = 0.80

            # High-Conviction Continuous Kelly Edge Boost
            if expected_returns is not None and len(expected_returns) == n:
                p_rets = np.asarray(expected_returns, dtype=float)
                if np.any(np.abs(p_rets) >= 1.0):
                    p_rets = p_rets / 100.0
                annualized_exp_ret = float(np.dot(weights, p_rets) * (252.0 / 20.0))
                sharpe_proxy = (annualized_exp_ret - 0.03) / max(annualized_port_vol, 0.05)
                if sharpe_proxy >= 1.50 and annualized_port_vol <= 0.15:
                    max_alloc_cap = 1.00
                    min_alloc_floor = 0.88
        elif "SIDEWAYS" in regime_str:
            max_alloc_cap = 0.85
            min_alloc_floor = 0.60
        else:  # Bear or Crisis
            max_alloc_cap = 0.50  # Risk off
            min_alloc_floor = 0.20

        # F43: Quadratic Shannon Regime Entropy Scaling & Macro Crisis Scaling
        u_regime_sq = u_regime ** 2
        eff_target_vol = self.target_volatility * (1.0 - 0.30 * u_regime_sq) * (1.0 - 0.20 * c_crisis)
        max_alloc_cap *= (1.0 - 0.20 * u_regime_sq) * (1.0 - 0.35 * c_crisis)
        min_alloc_floor *= (1.0 - 0.30 * u_regime_sq)

        # Scale factor = target_vol / realized_vol (C-06 fix: eliminate double-scaling cash drag)
        raw_scale = eff_target_vol / max(annualized_port_vol, 0.04)
        effective_alloc = float(np.clip(raw_scale, min_alloc_floor, max_alloc_cap))

        # Scale weights
        scaled_weights = weights * effective_alloc
        return scaled_weights, effective_alloc

    @staticmethod
    def is_korean_asset(symbol: str) -> bool:
        """Determines if a symbol represents a Korean asset (subject to 0.18% STT)."""
        s = str(symbol).strip().upper()
        if s.endswith(".KS") or s.endswith(".KQ"):
            return True
        base = s.split(".")[0]
        if base.isdigit() and len(base) == 6:
            return True
        return False

    def apply_leland_no_trade_buffers(
        self,
        target_weights: np.ndarray,
        current_weights: np.ndarray,
        volatilities: np.ndarray,
        unrealized_returns: Optional[np.ndarray] = None,
        rebalance_mode: Optional[str] = None,
        use_asymmetric_bands: bool = True,
        asset_cost_bps: Optional[Union[np.ndarray, List[float]]] = None,
        symbols: Optional[List[str]] = None,
        markets: Optional[List[str]] = None,
        downside_volatilities: Optional[Union[np.ndarray, List[float]]] = None,
    ) -> np.ndarray:
        """
        Volatility-Normalized Asymmetric Leland Dynamic No-Trade Buffer Bands:
        Suppresses unnecessary churn and transaction taxes (STT) when drift is within noise band.
        Uses continuous volatility-normalized Z-scores:
            z_unrealized = u_ret / (sigma_20d * sqrt(5)) (for u_ret >= 0)
            z_unrealized = u_ret / (sigma_minus * sqrt(5)) (for u_ret < 0, F43)
        - Winning runners (z > 0): upper band smoothly expands up to 1.8x to prevent premature rebalance sales.
        - Laggards (z < 0): lower band smoothly tightens down to 0.6x for prompt de-risking.
        - Boundary Rebalancing: when weight breaches band, rebalances to boundary (L_i or U_i) rather
          than full target, minimizing unnecessary turnover and market impact while controlling tracking error.
        F30 & F38: Granular 5-Market Spread & Tax-Aware Leland Dynamic Buffer Bands:
          - KOSDAQ: 35.0 bps (18 bps STT + 2 bps fee + 15 bps half-spread)
          - KOSPI: 25.0 bps (18 bps STT + 2 bps fee + 5 bps half-spread)
          - RUSSELL2000: 16.0 bps (0.5 bps reg fee + 15.5 bps half-spread)
          - NASDAQ: 7.0 bps (0.5 bps reg fee + 6.5 bps half-spread)
          - SP500: 5.0 bps (0.5 bps reg fee + 4.5 bps half-spread)
        Delta_i = ( 3/4 * Cost_i * w_i * (1 - w_i) * sigma_ann^2 / gamma )^(1/3)
        """
        n = len(target_weights)
        if current_weights is None or len(current_weights) != n or np.all(current_weights <= 0):
            return target_weights

        mode = (rebalance_mode or getattr(self, "rebalance_mode", "boundary")).lower()

        # F30 & F38: Resolve granular 5-market per-asset transaction cost fraction c_i
        if asset_cost_bps is not None:
            ac_arr = np.asarray(asset_cost_bps, dtype=float)
            if len(ac_arr) == n:
                cost_fraction = ac_arr / 10_000.0
            elif len(ac_arr) == 1:
                cost_fraction = np.full(n, float(ac_arr[0]) / 10_000.0)
            else:
                cost_fraction = np.full(n, self.leland_cost_bps / 10_000.0)
        elif markets is not None and len(markets) == n:
            costs = []
            for i in range(n):
                sym = symbols[i] if (symbols is not None and len(symbols) > i) else None
                mkt = markets[i]
                c_bps = self.resolve_market_cost_bps(symbol=sym, market=mkt, default_cost_bps=self.leland_cost_bps)
                costs.append(c_bps / 10_000.0)
            cost_fraction = np.asarray(costs, dtype=float)
        elif symbols is not None and len(symbols) == n:
            costs = []
            for s in symbols:
                c_bps = self.resolve_market_cost_bps(symbol=s, market=None, default_cost_bps=self.leland_cost_bps)
                if not self.is_korean_asset(s) and c_bps == self.leland_cost_bps:
                    costs.append(min(float(self.leland_cost_bps), 8.0) / 10_000.0)
                else:
                    costs.append(c_bps / 10_000.0)
            cost_fraction = np.asarray(costs, dtype=float)
        else:
            cost_fraction = np.full(n, self.leland_cost_bps / 10_000.0)  # e.g. 20 bps = 0.0020

        vols = np.maximum(volatilities, 0.005)
        ann_variance = 252.0 * (vols ** 2)
        gamma = max(1e-4, float(self.risk_aversion))
        w_factor = np.maximum(1e-4, target_weights * (1.0 - np.minimum(0.99, target_weights)))
        # Leland half-width delta (typically 0.5% ~ 4.5%): Delta_i proportional to (c_i * sigma_ann^2 / gamma)^(1/3)
        cubic_term = (0.75 * cost_fraction * w_factor * ann_variance) / gamma
        leland_deltas = np.clip(
            np.cbrt(cubic_term),
            0.005,
            0.045
        )

        realized_w = np.copy(target_weights)
        for i in range(n):
            curr_w = current_weights[i]
            tgt_w = target_weights[i]
            delta = leland_deltas[i]

            # Bypass buffer for new entries (curr <= 1e-4) or full liquidations (tgt <= 1e-4)
            if curr_w <= 1e-4 or tgt_w <= 1e-4:
                realized_w[i] = tgt_w
                continue

            # Continuous volatility-normalized asymmetric multipliers
            if use_asymmetric_bands and unrealized_returns is not None:
                u_ret = float(unrealized_returns[i]) if (len(unrealized_returns) > i and np.isfinite(unrealized_returns[i])) else 0.0
                vol_i = float(vols[i]) if (len(vols) > i and np.isfinite(vols[i])) else 0.02
                down_vol_i = None
                if downside_volatilities is not None and len(downside_volatilities) > i:
                    dv = float(downside_volatilities[i])
                    if np.isfinite(dv):
                        down_vol_i = dv
                upper_mult, lower_mult = self.calculate_asymmetric_leland_multipliers(
                    u_ret, vol_i, downside_semi_volatility=down_vol_i
                )
            else:
                upper_mult = 1.0
                lower_mult = 1.0

            upper_band = tgt_w + upper_mult * delta
            lower_band = max(0.0, tgt_w - lower_mult * delta)

            if lower_band <= curr_w <= upper_band:
                # Within asymmetric no-trade band: hold current weight to save turnover and tax
                realized_w[i] = curr_w
            elif curr_w < lower_band:
                # Breached below lower band: rebalance to lower boundary L_i in boundary mode, or target
                realized_w[i] = lower_band if mode == "boundary" else tgt_w
            else:
                # Breached above upper band: rebalance to upper boundary U_i in boundary mode, or target
                realized_w[i] = upper_band if mode == "boundary" else tgt_w

        return realized_w

    def allocate(
        self,
        predictions_df: pd.DataFrame,
        prices_dict: Dict[str, pd.DataFrame],
        total_portfolio_value: float = 100_000_000.0,
        regime: Optional[str] = "BULL_LOW_VOL",
        current_holdings: Optional[Dict[str, Dict[str, Any]]] = None,
        sector_map: Optional[Dict[str, str]] = None,
        top_n: int = 20,
        base_currency: str = "KRW",
        usd_krw: float = 1350.0,
        rebalance_mode: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Master Pipeline Allocation Method:
        Executes end-to-end multi-model blending, target volatility scaling,
        Leland buffer filtering, and share discretization.
        """
        if predictions_df is None or predictions_df.empty:
            return pd.DataFrame()

        # Extract top-N candidate symbols based on return or ensemble score
        score_col = None
        for col in ["ensemble_expected_return", 20, "raw_score", "predicted_return", "score"]:
            if col in predictions_df.columns:
                score_col = col
                break

        df_candidates = predictions_df.sort_values(score_col, ascending=False).head(top_n).copy() if score_col else predictions_df.head(top_n).copy()
        raw_symbols = [str(s) for s in df_candidates["symbol"].tolist()]

        # Extract synchronized return series & covariance matrix (with FX cross-border calibration)
        fx_series = None
        if prices_dict and isinstance(prices_dict, dict):
            for fx_k in ["USDKRW", "USD/KRW", "FX_USDKRW", "KRW=X"]:
                if fx_k in prices_dict and isinstance(prices_dict[fx_k], pd.DataFrame) and not prices_dict[fx_k].empty:
                    c_col = "Close" if "Close" in prices_dict[fx_k].columns else ("close" if "close" in prices_dict[fx_k].columns else None)
                    if c_col:
                        fx_series = prices_dict[fx_k][c_col].dropna()
                        break

        returns_df, valid_symbols = self.compute_returns_matrix(
            raw_symbols, prices_dict, lookback=60, fx_series=fx_series, base_currency=base_currency
        )
        if len(valid_symbols) < 2 or returns_df.empty:
            logger.warning("[UnifiedPortfolioAllocator] Insufficient historical data for covariance. Falling back to heuristic allocation.")
            df_candidates = df_candidates.head(min(len(df_candidates), 10)).copy()
            df_candidates["weight"] = self.default_max_total_allocation / len(df_candidates)
            df_candidates["allocation_amount"] = df_candidates["weight"] * total_portfolio_value
            return df_candidates

        # Filter candidate dataframe to valid symbols
        df_candidates = df_candidates[df_candidates["symbol"].astype(str).isin(valid_symbols)].copy()
        valid_symbols = [str(s) for s in df_candidates["symbol"].tolist()]
        returns_df = returns_df[valid_symbols]

        # Calculate hybrid EWMA (half-life 15d) + Ledoit-Wolf shrunk covariance matrix
        # Captures fast-moving volatility/correlation spikes without 60-day lag
        cov_matrix = self.compute_hybrid_ewma_covariance(returns_df, halflife=15, lw_weight=0.40)

        # Extract expected returns vector (C-01 fix: scale alignment between percentage and decimal)
        if score_col:
            pred_rets = df_candidates[score_col].values.astype(float)
            if score_col in ["raw_score", "score", "ensemble_score"] and np.all(pred_rets >= 0.0) and np.all(pred_rets <= 1.0):
                # Convert normalized [0, 1] probability score to a reasonable 20D expected return proxy [-5%, +10%]
                pred_rets = (pred_rets - 0.50) * 0.15
            elif np.any(np.abs(pred_rets) >= 1.0):
                # Values like 15.0 represent 15.0%, normalize to decimal 0.15
                pred_rets = pred_rets / 100.0
        else:
            pred_rets = returns_df.mean().values * 20.0

        # Extract sectors
        sec_map = sector_map or {}
        sectors = [sec_map.get(s, "General") for s in valid_symbols]

        # Extract ADVs (trading turnover in currency) if available
        advs = None
        if "adv" in df_candidates.columns:
            advs = df_candidates["adv"].values.astype(float)
        elif "trading_value" in df_candidates.columns:
            advs = df_candidates["trading_value"].values.astype(float)
        elif "volume" in df_candidates.columns:
            px = df_candidates["close"].values.astype(float) if "close" in df_candidates.columns else np.ones(len(df_candidates))
            advs = df_candidates["volume"].values.astype(float) * px

        # Extract market caps if available for Black-Litterman CAPM equilibrium prior
        market_caps = None
        for cap_col in ["market_cap", "marcap", "market_capitalization"]:
            if cap_col in df_candidates.columns:
                c_vals = df_candidates[cap_col].values.astype(float)
                if np.any(np.isfinite(c_vals)) and np.nanmax(c_vals) > 0:
                    market_caps = np.nan_to_num(c_vals, nan=np.nanmedian(c_vals[c_vals > 0]) if np.any(c_vals > 0) else 1.0)
                    break

        # Extract current weights from current_holdings (supports float weight map or dict holding details)
        current_weights = np.zeros(len(valid_symbols))
        if current_holdings and total_portfolio_value > 0:
            for i, sym in enumerate(valid_symbols):
                sym_str = str(sym)
                base_sym = sym_str.split('.')[0]
                candidates = [sym_str, sym, base_sym, f"{base_sym}.KS", f"{base_sym}.KQ"]
                h = None
                for c_k in candidates:
                    if c_k in current_holdings:
                        h = current_holdings[c_k]
                        break

                if h is not None:
                    if isinstance(h, (int, float)):
                        current_weights[i] = float(h)
                    elif isinstance(h, dict):
                        qty = float(h.get("quantity") or 0.0)
                        cp = h.get("current_price") or h.get("entry_price") or 0.0
                        p_val = float(cp)
                        current_weights[i] = (qty * p_val) / total_portfolio_value

        # Extract per-symbol alpha half-lives based on active strategies and 2D regime
        symbol_half_lives = []
        regime_strats = {}
        try:
            from src.ai.ensemble_scorer import EnsembleScoringEngine
            regime_strats = EnsembleScoringEngine.get_regime_adaptive_half_lives(regime or "BULL_LOW_VOL")
        except Exception:
            pass

        for sym in valid_symbols:
            sub = df_candidates[df_candidates["symbol"].astype(str) == str(sym)]
            hl_list = []
            if not sub.empty:
                r_dict = sub.iloc[0].to_dict()
                for strat, hl in regime_strats.items():
                    val = r_dict.get(strat)
                    if val is None:
                        val = r_dict.get(f"{strat}_score") or r_dict.get(f"{strat}_prob")
                    if val is not None and isinstance(val, (int, float)) and val > 0.5:
                        hl_list.append(hl)
            eff_hl = float(np.min(hl_list)) if hl_list else (15.0 if "BULL" in str(regime).upper() else 10.0)
            symbol_half_lives.append(eff_hl)

        # Extract dark pool scores for Gatheral liquidity impact modulation (F11)
        darkpool_scores = None
        for dp_col in ["darkpool_score", "dark_pool_score", "darkpool_ratio"]:
            if dp_col in df_candidates.columns:
                darkpool_scores = df_candidates[dp_col].values.astype(float)
                break

        # Step 1: Multi-Model Regime-Adaptive Blending
        w_opt = self.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=valid_symbols,
            sectors=sectors,
            regime=regime,
            current_weights=current_weights,
            advs=advs,
            total_capital=total_portfolio_value,
            market_caps=market_caps,
            alpha_half_lives=symbol_half_lives,
            darkpool_scores=darkpool_scores,
        )

        # Step 2: Target Volatility Scaling & Cash Drag Eliminator
        w_scaled, effective_alloc = self.apply_target_volatility_scaling(
            w_opt, cov_matrix, regime=regime, expected_returns=pred_rets
        )

        # Step 3: Asymmetric Leland Dynamic No-Trade Buffer
        vols = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-6))
        unrealized_rets = np.zeros(len(valid_symbols))
        if current_holdings:
            for i, sym in enumerate(valid_symbols):
                sym_str = str(sym)
                base_sym = sym_str.split('.')[0]
                candidates = [sym_str, sym, base_sym, f"{base_sym}.KS", f"{base_sym}.KQ"]
                h = None
                for c_k in candidates:
                    if c_k in current_holdings:
                        h = current_holdings[c_k]
                        break
                if isinstance(h, dict):
                    ret_val = h.get("unrealized_return")
                    if ret_val is None:
                        cp = float(h.get("current_price", 0.0))
                        ep = float(h.get("entry_price", 0.0))
                        if ep > 0 and cp > 0:
                            ret_val = (cp - ep) / ep
                    if ret_val is not None and math.isfinite(float(ret_val)):
                        unrealized_rets[i] = float(ret_val)

        w_final = self.apply_leland_no_trade_buffers(
            w_scaled, current_weights, volatilities=vols, unrealized_returns=unrealized_rets,
            rebalance_mode=rebalance_mode, symbols=valid_symbols
        )

        # Step 4: Compute shares, lot sizes, and allocation amounts
        latest_prices = []
        for sym in valid_symbols:
            candidates = [sym, str(sym).upper(), str(sym).lower()]
            if str(sym).endswith(('.KS', '.KQ')):
                candidates.append(str(sym).split('.')[0])
            elif str(sym).isdigit():
                candidates.extend([f"{sym}.KS", f"{sym}.KQ"])

            p: Optional[float] = None
            if prices_dict and isinstance(prices_dict, dict):
                for c_sym in candidates:
                    if c_sym in prices_dict:
                        p_df = prices_dict[c_sym]
                        if p_df is not None and not p_df.empty:
                            c_col = "Close" if "Close" in p_df.columns else ("close" if "close" in p_df.columns else None)
                            if c_col and len(p_df[c_col].dropna()) > 0:
                                val = float(p_df[c_col].dropna().iloc[-1])
                                if math.isfinite(val) and val > 0:
                                    p = val
                                    break
            # Fallback to close/close_price in df_candidates
            if p is None or p <= 1.0:
                sub_df = df_candidates[df_candidates["symbol"].astype(str) == str(sym)]
                for col in ["close", "close_price", "price", "current_price"]:
                    if col in sub_df.columns and not sub_df[col].dropna().empty:
                        c_val = float(sub_df[col].dropna().iloc[0])
                        if math.isfinite(c_val) and c_val > 0:
                            p = c_val
                            break

            latest_prices.append(max(float(p if p is not None else 1.0), 1.0))

        df_candidates["weight"] = w_final
        df_candidates["target_weight"] = w_scaled
        df_candidates["current_weight"] = current_weights
        df_candidates["delta_weight"] = w_final - current_weights
        df_candidates["volatility"] = vols
        df_candidates["predicted_return"] = pred_rets
        df_candidates["allocation_amount"] = w_final * total_portfolio_value

        # Lot size resolution (KRX: 1 share since 2014, TSE/HKEX/HOSE: 100 shares, US: 1 share)
        # V8-CRIT-01 Fix: Multi-currency aware FX translation
        shares_list = []
        lot_list = []
        rate_val = float(usd_krw) if usd_krw and usd_krw > 0 else 1350.0
        base_curr_norm = str(base_currency).upper().strip()
        for i, row in enumerate(df_candidates.itertuples()):
            sym = str(row.symbol)
            mkt = str(getattr(row, "market", "KOSPI")).upper()
            is_krx = sym.isdigit() or mkt in ["KOSPI", "KOSDAQ", "KRX"]
            is_us = mkt in ["SP500", "NASDAQ", "RUSSELL2000", "US"] or not is_krx
            lot = 1 if is_krx else (100 if mkt in ["JAPAN_TSE", "HKEX", "VIETNAM_HOSE"] else 1)
            px = float(latest_prices[i])
            alloc_amt = float(row.allocation_amount)

            # V8-CRIT-01 Fix: Multi-currency aware FX translation
            if is_us and base_curr_norm == "KRW":
                eff_price = px * rate_val
            elif is_krx and base_curr_norm == "USD":
                eff_price = px / rate_val
            else:
                eff_price = px

            raw_shares = int(alloc_amt // eff_price) if eff_price > 0 else 0
            adj_shares = (raw_shares // lot) * lot
            shares_list.append(adj_shares)
            lot_list.append(lot)

        df_candidates["shares"] = shares_list
        df_candidates["target_shares"] = shares_list
        df_candidates["lot_size"] = lot_list

        tot_invested = float(df_candidates['weight'].sum())
        cash_buffer_weight = max(0.0, 1.0 - tot_invested)
        cash_buffer_amount = cash_buffer_weight * total_portfolio_value
        df_candidates.attrs["cash_buffer_weight"] = cash_buffer_weight
        df_candidates.attrs["cash_buffer_amount"] = cash_buffer_amount
        df_candidates.attrs["total_invested_weight"] = tot_invested

        logger.info(
            f"[UnifiedPortfolioAllocator] Allocated {len(df_candidates)} assets. "
            f"Total Invested: {tot_invested:.1%}, Cash Buffer: {cash_buffer_weight:.1%} "
            f"({cash_buffer_amount:,.0f} {base_currency}) (Effective Alloc: {effective_alloc:.1%})"
        )

        return df_candidates

    def allocate_black_litterman(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        predicted_returns: Dict[str, float],
        total_portfolio_value: float = 100_000_000.0,
        tau: float = 0.05,
        risk_aversion: Optional[float] = None,
        market_caps: Optional[Dict[str, float]] = None,
        regime: Optional[str] = "BULL_LOW_VOL",
        base_currency: str = "KRW",
        usd_krw: float = 1350.0,
    ) -> pd.DataFrame:
        """
        Standalone Bayesian Black-Litterman Portfolio Allocator:
        Derives equilibrium prior from CAPM / market caps, integrates strategy views,
        and discretizes optimal weights into execution lots.
        """
        symbols = [str(s) for s in predicted_returns.keys()]
        if len(symbols) < 2:
            return pd.DataFrame()

        df_input = pd.DataFrame({
            "symbol": symbols,
            "ensemble_expected_return": [predicted_returns[s] for s in symbols]
        })
        if market_caps:
            df_input["market_cap"] = [market_caps.get(s, 1.0) for s in symbols]

        return self.allocate(
            predictions_df=df_input,
            prices_dict=prices_dict,
            total_portfolio_value=total_portfolio_value,
            regime="BULL_LOW_VOL" if not regime else str(regime),
            top_n=len(symbols),
            base_currency=base_currency,
            usd_krw=usd_krw,
        )

