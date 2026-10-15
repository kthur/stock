"""
brinson_factor_attributor.py — Institutional Brinson-Fachler Multi-Currency Factor Performance Attributor.

Phase 108 / Feature F512 / Release R124 (v115 Production Master)
Milestone 3: Institutional Brinson-Fachler Multi-Currency Factor Performance Attributor.

Mathematical Core:
1. Single-Period Brinson-Fachler Multi-Currency Decomposition:
   - Allocation Effect: R_alloc,i = (w_p,i - w_b,i) * (R_b,i^local - R_b^local)
   - Selection Effect:  R_select,i = w_b,i * (R_p,i^local - R_b,i^local)
   - Interaction Effect: R_inter,i = (w_p,i - w_b,i) * (R_p,i^local - R_b,i^local)
   - Currency Effect:   R_curr,i = w_p,i * (c_p,i^hedged + R_p,i^local * c_p,i^hedged)
                                  - w_b,i * (c_b,i + R_b,i^local * c_b,i)
     where c_p,i^hedged = (1 - h_i) * c_p,i + h_i * f_i (CIP forward premium f_i, hedge ratio h_i).
   - Strict Arithmetic Identity:
     R_total = R_alloc + R_select + R_inter + R_curr
     with tolerance strictly < 1e-6 (empirically < 1e-15).
   - Currency Sub-Decomposition:
     R_curr_alloc = sum (w_p,i - w_b,i) * c_b,i
     R_curr_select = sum w_p,i * (c_p,i^hedged - c_b,i)
     R_curr_inter = sum [w_p,i * R_p,i^local * c_p,i^hedged - w_b,i * R_b,i^local * c_b,i]

2. Multi-Period Carino Compounding Linking:
   - For daily active returns Delta R_t = R_p,t - R_b,t compounding to cumulative R_p - R_b:
     k_t = [ln(1 + R_p,t) - ln(1 + R_b,t)] / (R_p,t - R_b,t) * (R_p - R_b) / [ln(1 + R_p) - ln(1 + R_b)]
     with smooth analytic limit k_t = [1 / (1 + R_b,t)] * (R_p - R_b) / [ln(1 + R_p) - ln(1 + R_b)]
     when |R_p,t - R_b,t| < 1e-12.
   - Cumulative components: R_k^multi = sum_t k_t * R_k,t, preserving exact arithmetic identity.

3. Factor Risk Mapping:
   - Multi-factor OLS regression on Fama-French 5-Factors (MKT, SMB, HML, RMW, CMA) + Momentum (UMD).
   - Computes annualized Jensen's Alpha, factor betas, t-statistics, p-values, R^2, adjusted R^2,
     and specific idiosyncratic risk.
   - 2D Market Regime conditional breakdown across canonical market regimes:
     BULL_LOW_VOL, BULL_HIGH_VOL, SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, BEAR_LOW_VOL, BEAR_HIGH_VOL, CRISIS.

4. Audit-Ready Institutional Tear Sheets:
   - Formats comprehensive executive summaries, segment attribution tables, currency breakdowns,
     factor risk exposures, and 2D regime performance in audit-ready text and markdown tables.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)

# Canonical 2D Market Regimes
CANONICAL_2D_REGIMES = (
    "BULL_LOW_VOL",
    "BULL_HIGH_VOL",
    "SIDEWAYS_LOW_VOL",
    "SIDEWAYS_HIGH_VOL",
    "BEAR_LOW_VOL",
    "BEAR_HIGH_VOL",
    "CRISIS",
)

# Standard Fama-French 5-Factors + Momentum
CANONICAL_FACTORS = ("MKT", "SMB", "HML", "RMW", "CMA", "UMD")


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SegmentAttribution:
    """Attribution breakdown for a single sector, asset class, or market segment."""
    segment: str
    portfolio_weight: float
    benchmark_weight: float
    active_weight: float
    portfolio_return_local: float
    benchmark_return_local: float
    active_return_local: float
    currency_return_portfolio: float
    currency_return_benchmark: float
    hedge_ratio: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    currency_effect: float
    total_active_return: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrinsonDecompositionResult:
    """Comprehensive single-period Brinson-Fachler multi-currency decomposition result."""
    portfolio_return_base: float
    benchmark_return_base: float
    total_active_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    currency_effect: float
    currency_allocation: float
    currency_selection: float
    currency_interaction: float
    segments: List[SegmentAttribution]
    arithmetic_identity_error: float
    is_identity_valid: bool
    base_currency: str = "KRW"
    as_of_date: Optional[str] = None


@dataclass
class MultiPeriodAttributionResult:
    """Multi-period cumulative attribution result linked via Carino logarithmic coefficients."""
    cumulative_portfolio_return: float
    cumulative_benchmark_return: float
    cumulative_active_return: float
    cumulative_allocation: float
    cumulative_selection: float
    cumulative_interaction: float
    cumulative_currency: float
    daily_results: List[BrinsonDecompositionResult]
    carino_coefficients: List[float]
    arithmetic_identity_error: float
    is_identity_valid: bool


@dataclass
class FactorRiskAttributionResult:
    """Multi-factor risk attribution and 2D market regime breakdown result."""
    alpha_annualized: float
    alpha_t_stat: float
    alpha_p_value: float
    factor_betas: Dict[str, float]
    factor_t_stats: Dict[str, float]
    factor_p_values: Dict[str, float]
    factor_contributions: Dict[str, float]
    r_squared: float
    adj_r_squared: float
    specific_risk: float
    regime_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core Attributor Class
# ---------------------------------------------------------------------------

class BrinsonFactorAttributor:
    """
    Institutional Brinson-Fachler Multi-Currency Factor Performance Attributor.

    Features:
    - Single-period Brinson-Fachler active return decomposition.
    - Full multi-currency integration with FX hedging ratios & CIP forward premiums.
    - Exact arithmetic identity preservation (tolerance < 1e-6, typically < 1e-15).
    - Multi-period Carino linking algorithm across multi-day horizons.
    - Fama-French 5-Factor + Momentum multi-factor regression with t-stats & p-values.
    - 2D Market Regime conditional alpha and beta evaluation.
    - Audit-ready institutional tear sheets in plain text and markdown formats.
    """

    def __init__(
        self,
        base_currency: str = "KRW",
        default_benchmark: str = "EQUAL_WEIGHT",
        tolerance: float = 1e-6,
        normalize_weights: bool = True,
    ) -> None:
        """
        Initialize BrinsonFactorAttributor.

        Args:
            base_currency: Portfolio base reporting currency (default 'KRW').
            default_benchmark: Default benchmark identifier.
            tolerance: Arithmetic identity error threshold (default 1e-6).
            normalize_weights: Whether to normalize weights to sum to 1.0 (default True).
        """
        self.base_currency = base_currency.upper()
        self.default_benchmark = default_benchmark
        self.tolerance = tolerance
        self.normalize_weights = normalize_weights

    # -----------------------------------------------------------------------
    # Single-Period Decomposition
    # -----------------------------------------------------------------------

    def decompose_single_period(
        self,
        portfolio_weights: Dict[str, float],
        benchmark_weights: Dict[str, float],
        asset_returns_local: Dict[str, float],
        benchmark_returns_local: Dict[str, float],
        currency_returns: Optional[Dict[str, float]] = None,
        hedge_ratios: Optional[Dict[str, float]] = None,
        forward_premiums: Optional[Dict[str, float]] = None,
        benchmark_currency_returns: Optional[Dict[str, float]] = None,
        segment_mapping: Optional[Dict[str, str]] = None,
        as_of_date: Optional[str] = None,
    ) -> BrinsonDecompositionResult:
        """
        Perform single-period multi-currency Brinson-Fachler active return decomposition.

        Args:
            portfolio_weights: Dict of portfolio weights by asset or segment.
            benchmark_weights: Dict of benchmark weights by asset or segment.
            asset_returns_local: Dict of local portfolio returns by asset or segment.
            benchmark_returns_local: Dict of local benchmark returns by asset or segment.
            currency_returns: Dict of FX returns vs base currency (0.0 for domestic).
            hedge_ratios: Dict of currency hedge ratios h in [0.0, 1.0] (default 0.0).
            forward_premiums: Dict of CIP forward premium rates f (default 0.0).
            benchmark_currency_returns: Dict of FX returns for benchmark (default == currency_returns).
            segment_mapping: Optional map from asset symbol to segment name.
            as_of_date: Optional date string for reporting.

        Returns:
            BrinsonDecompositionResult satisfying exact arithmetic identity.
        """
        currency_returns = currency_returns or {}
        hedge_ratios = hedge_ratios or {}
        forward_premiums = forward_premiums or {}
        benchmark_currency_returns = benchmark_currency_returns or currency_returns

        # 1. Aggregate to segment level if segment_mapping is provided
        if segment_mapping:
            seg_p_weights, seg_b_weights, seg_p_returns, seg_b_returns, seg_c_p, seg_c_b, seg_h, seg_f = (
                self._aggregate_assets_to_segments(
                    portfolio_weights,
                    benchmark_weights,
                    asset_returns_local,
                    benchmark_returns_local,
                    currency_returns,
                    hedge_ratios,
                    forward_premiums,
                    benchmark_currency_returns,
                    segment_mapping,
                )
            )
        else:
            all_segments = sorted(set(portfolio_weights.keys()) | set(benchmark_weights.keys()))
            seg_p_weights = {s: float(portfolio_weights.get(s, 0.0)) for s in all_segments}
            seg_b_weights = {s: float(benchmark_weights.get(s, 0.0)) for s in all_segments}
            seg_p_returns = {s: float(asset_returns_local.get(s, 0.0)) for s in all_segments}
            seg_b_returns = {s: float(benchmark_returns_local.get(s, 0.0)) for s in all_segments}
            seg_c_p = {s: float(currency_returns.get(s, 0.0)) for s in all_segments}
            seg_c_b = {s: float(benchmark_currency_returns.get(s, seg_c_p[s])) for s in all_segments}
            seg_h = {s: float(np.clip(hedge_ratios.get(s, 0.0), 0.0, 1.0)) for s in all_segments}
            seg_f = {s: float(forward_premiums.get(s, 0.0)) for s in all_segments}

        # 2. Normalize weights if requested
        if self.normalize_weights:
            sum_p = sum(seg_p_weights.values())
            sum_b = sum(seg_b_weights.values())
            if sum_p > 0.0:
                seg_p_weights = {s: w / sum_p for s, w in seg_p_weights.items()}
            if sum_b > 0.0:
                seg_b_weights = {s: w / sum_b for s, w in seg_b_weights.items()}

        segments_order = sorted(seg_p_weights.keys())

        # 3. Compute portfolio & benchmark total local returns
        r_p_local = sum(seg_p_weights[s] * seg_p_returns[s] for s in segments_order)
        r_b_local = sum(seg_b_weights[s] * seg_b_returns[s] for s in segments_order)

        # 4. Compute hedged currency returns & base currency returns
        seg_c_p_hedged: Dict[str, float] = {}
        seg_p_returns_base: Dict[str, float] = {}
        seg_b_returns_base: Dict[str, float] = {}

        for s in segments_order:
            c_p = seg_c_p[s]
            h = seg_h[s]
            f = seg_f[s]
            # Hedged currency return: c_hedged = (1 - h) * c_p + h * f
            c_hedged = (1.0 - h) * c_p + h * f
            seg_c_p_hedged[s] = c_hedged

            # Base returns: (1 + R_local) * (1 + c) - 1 = R_local + c + R_local * c
            r_p_loc = seg_p_returns[s]
            r_b_loc = seg_b_returns[s]
            c_b = seg_c_b[s]

            seg_p_returns_base[s] = r_p_loc + c_hedged + r_p_loc * c_hedged
            seg_b_returns_base[s] = r_b_loc + c_b + r_b_loc * c_b

        r_p_base = sum(seg_p_weights[s] * seg_p_returns_base[s] for s in segments_order)
        r_b_base = sum(seg_b_weights[s] * seg_b_returns_base[s] for s in segments_order)
        total_active_return = r_p_base - r_b_base

        # 5. Compute segment-level Brinson-Fachler & currency effects
        segment_attributions: List[SegmentAttribution] = []

        total_alloc = 0.0
        total_select = 0.0
        total_inter = 0.0
        total_curr = 0.0
        total_curr_alloc = 0.0
        total_curr_select = 0.0
        total_curr_inter = 0.0

        for s in segments_order:
            w_p = seg_p_weights[s]
            w_b = seg_b_weights[s]
            act_w = w_p - w_b

            r_p_loc = seg_p_returns[s]
            r_b_loc = seg_b_returns[s]
            act_r_loc = r_p_loc - r_b_loc

            c_hedged = seg_c_p_hedged[s]
            c_b = seg_c_b[s]
            h = seg_h[s]

            # Brinson-Fachler Allocation Effect: (w_p - w_b) * (R_b,i^loc - R_b^loc)
            alloc_eff = act_w * (r_b_loc - r_b_local)

            # Brinson-Fachler Selection Effect: w_b * (R_p,i^loc - R_b,i^loc)
            select_eff = w_b * act_r_loc

            # Brinson-Fachler Interaction Effect: (w_p - w_b) * (R_p,i^loc - R_b,i^loc)
            inter_eff = act_w * act_r_loc

            # Currency Effect per segment:
            # w_p * (c_p^hedged + r_p_loc * c_p^hedged) - w_b * (c_b + r_b_loc * c_b)
            curr_eff = w_p * (c_hedged + r_p_loc * c_hedged) - w_b * (c_b + r_b_loc * c_b)

            # Currency Sub-Decomposition
            curr_alloc = act_w * c_b
            curr_select = w_p * (c_hedged - c_b)
            curr_inter = w_p * r_p_loc * c_hedged - w_b * r_b_loc * c_b

            seg_total_act = alloc_eff + select_eff + inter_eff + curr_eff

            total_alloc += alloc_eff
            total_select += select_eff
            total_inter += inter_eff
            total_curr += curr_eff
            total_curr_alloc += curr_alloc
            total_curr_select += curr_select
            total_curr_inter += curr_inter

            seg_attr = SegmentAttribution(
                segment=s,
                portfolio_weight=w_p,
                benchmark_weight=w_b,
                active_weight=act_w,
                portfolio_return_local=r_p_loc,
                benchmark_return_local=r_b_loc,
                active_return_local=act_r_loc,
                currency_return_portfolio=c_hedged,
                currency_return_benchmark=c_b,
                hedge_ratio=h,
                allocation_effect=alloc_eff,
                selection_effect=select_eff,
                interaction_effect=inter_eff,
                currency_effect=curr_eff,
                total_active_return=seg_total_act,
                details={
                    "raw_currency_return": seg_c_p[s],
                    "forward_premium": seg_f[s],
                    "currency_allocation": curr_alloc,
                    "currency_selection": curr_select,
                    "currency_interaction": curr_inter,
                    "portfolio_return_base": seg_p_returns_base[s],
                    "benchmark_return_base": seg_b_returns_base[s],
                },
            )
            segment_attributions.append(seg_attr)

        # 6. Verify Exact Arithmetic Identity:
        # R_total == R_alloc + R_select + R_inter + R_curr
        decomposed_sum = total_alloc + total_select + total_inter + total_curr
        identity_error = abs(total_active_return - decomposed_sum)
        is_valid = bool(identity_error < self.tolerance)

        return BrinsonDecompositionResult(
            portfolio_return_base=r_p_base,
            benchmark_return_base=r_b_base,
            total_active_return=total_active_return,
            allocation_effect=total_alloc,
            selection_effect=total_select,
            interaction_effect=total_inter,
            currency_effect=total_curr,
            currency_allocation=total_curr_alloc,
            currency_selection=total_curr_select,
            currency_interaction=total_curr_inter,
            segments=segment_attributions,
            arithmetic_identity_error=identity_error,
            is_identity_valid=is_valid,
            base_currency=self.base_currency,
            as_of_date=as_of_date,
        )

    # -----------------------------------------------------------------------
    # Multi-Period Compounding via Carino Linking
    # -----------------------------------------------------------------------

    def decompose_multi_period(
        self,
        daily_results: Optional[List[BrinsonDecompositionResult]] = None,
        daily_inputs: Optional[List[Dict[str, Any]]] = None,
    ) -> MultiPeriodAttributionResult:
        """
        Compound multi-period daily decompositions using Carino logarithmic linking coefficients.

        Args:
            daily_results: Pre-computed daily BrinsonDecompositionResult objects.
            daily_inputs: Alternatively, list of keyword argument dicts for decompose_single_period.

        Returns:
            MultiPeriodAttributionResult with exact multi-period identity preservation.
        """
        if daily_results is None:
            if daily_inputs is None:
                raise ValueError("Either daily_results or daily_inputs must be provided.")
            daily_results = [self.decompose_single_period(**inp) for inp in daily_inputs]

        num_periods = len(daily_results)
        if num_periods == 0:
            return MultiPeriodAttributionResult(
                cumulative_portfolio_return=0.0,
                cumulative_benchmark_return=0.0,
                cumulative_active_return=0.0,
                cumulative_allocation=0.0,
                cumulative_selection=0.0,
                cumulative_interaction=0.0,
                cumulative_currency=0.0,
                daily_results=[],
                carino_coefficients=[],
                arithmetic_identity_error=0.0,
                is_identity_valid=True,
            )

        # 1. Compute cumulative compounded portfolio and benchmark returns
        cum_p_factor = 1.0
        cum_b_factor = 1.0
        daily_p_returns: List[float] = []
        daily_b_returns: List[float] = []

        for res in daily_results:
            cum_p_factor *= (1.0 + res.portfolio_return_base)
            cum_b_factor *= (1.0 + res.benchmark_return_base)
            daily_p_returns.append(res.portfolio_return_base)
            daily_b_returns.append(res.benchmark_return_base)

        cum_p_return = cum_p_factor - 1.0
        cum_b_return = cum_b_factor - 1.0
        cum_active_return = cum_p_return - cum_b_return

        # 2. Compute Carino Linking Coefficients k_t
        carino_coeffs = self.compute_carino_coefficients(
            daily_p_returns=daily_p_returns,
            daily_b_returns=daily_b_returns,
            cumulative_p_return=cum_p_return,
            cumulative_b_return=cum_b_return,
        )

        # 3. Apply Carino coefficients to scale daily components
        cum_alloc = sum(k * res.allocation_effect for k, res in zip(carino_coeffs, daily_results))
        cum_select = sum(k * res.selection_effect for k, res in zip(carino_coeffs, daily_results))
        cum_inter = sum(k * res.interaction_effect for k, res in zip(carino_coeffs, daily_results))
        cum_curr = sum(k * res.currency_effect for k, res in zip(carino_coeffs, daily_results))

        cum_decomposed_sum = cum_alloc + cum_select + cum_inter + cum_curr
        identity_error = abs(cum_active_return - cum_decomposed_sum)
        is_valid = bool(identity_error < self.tolerance)

        return MultiPeriodAttributionResult(
            cumulative_portfolio_return=cum_p_return,
            cumulative_benchmark_return=cum_b_return,
            cumulative_active_return=cum_active_return,
            cumulative_allocation=cum_alloc,
            cumulative_selection=cum_select,
            cumulative_interaction=cum_inter,
            cumulative_currency=cum_curr,
            daily_results=daily_results,
            carino_coefficients=carino_coeffs,
            arithmetic_identity_error=identity_error,
            is_identity_valid=is_valid,
        )

    @staticmethod
    def compute_carino_coefficients(
        daily_p_returns: List[float],
        daily_b_returns: List[float],
        cumulative_p_return: Optional[float] = None,
        cumulative_b_return: Optional[float] = None,
    ) -> List[float]:
        """
        Compute Carino logarithmic linking coefficients k_t.

        k_t = [ln(1 + R_p,t) - ln(1 + R_b,t)] / (R_p,t - R_b,t) *
              (R_p - R_b) / [ln(1 + R_p) - ln(1 + R_b)]
        """
        num_periods = len(daily_p_returns)
        if num_periods == 0:
            return []

        if cumulative_p_return is None:
            cum_p = 1.0
            for r in daily_p_returns:
                cum_p *= (1.0 + r)
            cumulative_p_return = cum_p - 1.0

        if cumulative_b_return is None:
            cum_b = 1.0
            for r in daily_b_returns:
                cum_b *= (1.0 + r)
            cumulative_b_return = cum_b - 1.0

        # Horizon scaling factor B:
        cum_diff = cumulative_p_return - cumulative_b_return
        u_p_cum = max(1e-8, 1.0 + cumulative_p_return)
        u_b_cum = max(1e-8, 1.0 + cumulative_b_return)
        ln_p_cum = math.log(u_p_cum)
        ln_b_cum = math.log(u_b_cum)
        ln_cum_diff = ln_p_cum - ln_b_cum

        if abs(cum_diff) > 1e-12 and abs(ln_cum_diff) > 1e-12:
            b_factor = cum_diff / ln_cum_diff
        else:
            b_factor = u_b_cum

        # Period scaling factors a_t:
        carino_coeffs: List[float] = []
        for r_p_t, r_b_t in zip(daily_p_returns, daily_b_returns):
            period_diff = r_p_t - r_b_t
            u_p_t = max(1e-8, 1.0 + r_p_t)
            u_b_t = max(1e-8, 1.0 + r_b_t)
            ln_p_t = math.log(u_p_t)
            ln_b_t = math.log(u_b_t)
            ln_period_diff = ln_p_t - ln_b_t

            if abs(period_diff) > 1e-12 and abs(ln_period_diff) > 1e-12:
                a_t = ln_period_diff / period_diff
            else:
                a_t = 1.0 / u_b_t

            k_t = a_t * b_factor
            carino_coeffs.append(k_t)

        return carino_coeffs

    # -----------------------------------------------------------------------
    # Factor Risk Mapping & 2D Market Regime Attribution
    # -----------------------------------------------------------------------

    def map_factor_risk(
        self,
        portfolio_returns: Union[List[float], np.ndarray, pd.Series],
        factor_returns: Union[pd.DataFrame, Dict[str, Union[List[float], np.ndarray]]],
        risk_free_rate: Union[float, List[float], np.ndarray] = 0.0,
        regime_labels: Optional[Union[List[str], np.ndarray, pd.Series]] = None,
        benchmark_returns: Optional[Union[List[float], np.ndarray, pd.Series]] = None,
        factor_order: Optional[List[str]] = None,
    ) -> FactorRiskAttributionResult:
        """
        Map portfolio returns to Fama-French 5-Factors + Momentum and 2D Market Regimes.

        Model:
            R_p,t - R_f,t = alpha + sum_k beta_k * Factor_k,t + epsilon_t

        Args:
            portfolio_returns: Daily portfolio returns series.
            factor_returns: DataFrame or Dict containing factor return series (MKT, SMB, HML, RMW, CMA, UMD).
            risk_free_rate: Risk-free rate (scalar or array).
            regime_labels: 2D market regime label for each period.
            benchmark_returns: Daily benchmark returns series for conditional active calculation.
            factor_order: Preferred order of factor regression columns.

        Returns:
            FactorRiskAttributionResult containing alpha, betas, t-stats, p-values, R^2, and regime breakdown.
        """
        # Convert portfolio returns to 1D numpy array
        y_raw = np.asarray(portfolio_returns, dtype=np.float64).flatten()
        n_obs = len(y_raw)
        if n_obs < 3:
            raise ValueError(f"Insufficient observations for factor regression: N = {n_obs} (minimum 3 required).")

        # Convert risk-free rate
        if isinstance(risk_free_rate, (int, float)):
            rf = np.full(n_obs, float(risk_free_rate), dtype=np.float64)
        else:
            rf = np.asarray(risk_free_rate, dtype=np.float64).flatten()
            if len(rf) != n_obs:
                rf = np.resize(rf, n_obs)

        y = y_raw - rf

        # Convert factor returns to DataFrame
        if isinstance(factor_returns, pd.DataFrame):
            factor_df = factor_returns.copy()
        else:
            factor_df = pd.DataFrame(factor_returns)

        # Standardize column names (case-insensitive lookup)
        col_lookup = {c.upper(): c for c in factor_df.columns}
        canonical_candidates = factor_order or list(CANONICAL_FACTORS)

        selected_factors: List[str] = []
        factor_matrix_cols: List[np.ndarray] = []

        for f_name in canonical_candidates:
            f_upper = f_name.upper()
            found_col = None
            if f_upper in col_lookup:
                found_col = col_lookup[f_upper]
            elif f_upper == "MKT":
                for alt in ("MKT-RF", "MARKET", "SP500", "KOSPI"):
                    if alt in col_lookup:
                        found_col = col_lookup[alt]
                        break
            elif f_upper == "UMD":
                for alt in ("MOM", "MOMENTUM"):
                    if alt in col_lookup:
                        found_col = col_lookup[alt]
                        break

            if found_col is not None:
                selected_factors.append(f_name)
                factor_series = np.asarray(factor_df[found_col], dtype=np.float64).flatten()
                if len(factor_series) != n_obs:
                    factor_series = np.resize(factor_series, n_obs)
                factor_matrix_cols.append(factor_series)

        # If none of canonical factors matched, use whatever columns are present in factor_df
        if not selected_factors and len(factor_df.columns) > 0:
            for col in factor_df.columns:
                selected_factors.append(str(col))
                factor_series = np.asarray(factor_df[col], dtype=np.float64).flatten()
                if len(factor_series) != n_obs:
                    factor_series = np.resize(factor_series, n_obs)
                factor_matrix_cols.append(factor_series)

        if not selected_factors:
            raise ValueError("No factor columns found for regression.")

        # Construct Design Matrix X: [1.0, Factor_1, Factor_2, ...]
        F_mat = np.column_stack(factor_matrix_cols)  # (N, M)
        n_factors = F_mat.shape[1]
        X = np.column_stack([np.ones(n_obs, dtype=np.float64), F_mat])  # (N, M+1)

        # OLS estimation via pseudo-inverse: beta = (X^T X)^(-1) X^T y
        xtx = X.T @ X
        xty = X.T @ y
        inv_xtx = np.linalg.pinv(xtx)
        beta_hat = inv_xtx @ xty

        y_pred = X @ beta_hat
        residuals = y - y_pred

        alpha_daily = float(beta_hat[0])
        alpha_annualized = alpha_daily * 252.0

        # Goodness of fit & Degrees of Freedom
        df_residuals = max(1, n_obs - (n_factors + 1))
        ss_res = float(np.sum(residuals ** 2))
        y_mean = float(np.mean(y))
        ss_tot = float(np.sum((y - y_mean) ** 2))

        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-14 else 0.0
        r_squared = float(np.clip(r_squared, 0.0, 1.0))

        if n_obs > (n_factors + 1):
            adj_r_squared = 1.0 - (1.0 - r_squared) * ((n_obs - 1) / df_residuals)
            adj_r_squared = float(np.clip(adj_r_squared, -1.0, 1.0))
        else:
            adj_r_squared = r_squared

        # Standard errors, t-statistics & p-values
        res_var = ss_res / df_residuals
        cov_beta = res_var * inv_xtx
        std_errs = np.sqrt(np.maximum(1e-16, np.diag(cov_beta)))
        t_stats = beta_hat / std_errs

        # Compute p-values via Student-t distribution
        p_values: np.ndarray
        if HAS_SCIPY:
            p_values = stats.t.sf(np.abs(t_stats), df_residuals) * 2.0
        else:
            # Fallback Gaussian approximation for p-values
            p_values = np.array([
                2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t) / math.sqrt(2.0))))
                for t in t_stats
            ])

        alpha_t_stat = float(t_stats[0])
        alpha_p_value = float(p_values[0])

        factor_betas: Dict[str, float] = {}
        factor_t_stats_dict: Dict[str, float] = {}
        factor_p_values_dict: Dict[str, float] = {}
        factor_contributions: Dict[str, float] = {}

        for idx, f_name in enumerate(selected_factors):
            beta_idx = idx + 1
            beta_val = float(beta_hat[beta_idx])
            factor_betas[f_name] = beta_val
            factor_t_stats_dict[f_name] = float(t_stats[beta_idx])
            factor_p_values_dict[f_name] = float(p_values[beta_idx])

            # Factor contribution = beta * mean(factor) * 252 (annualized)
            mean_f = float(np.mean(factor_matrix_cols[idx]))
            factor_contributions[f_name] = beta_val * mean_f * 252.0

        # Annualized specific idiosyncratic risk
        specific_risk = float(np.sqrt(max(0.0, res_var)) * np.sqrt(252.0))

        # 2D Market Regime conditional evaluation
        regime_breakdown: Dict[str, Dict[str, float]] = {}
        if regime_labels is not None:
            reg_array = np.asarray(regime_labels)
            if len(reg_array) != n_obs:
                reg_array = np.resize(reg_array, n_obs)

            bench_array = None
            if benchmark_returns is not None:
                bench_array = np.asarray(benchmark_returns, dtype=np.float64).flatten()
                if len(bench_array) != n_obs:
                    bench_array = np.resize(bench_array, n_obs)

            unique_regimes = sorted(set(reg_array))
            for r_name in unique_regimes:
                mask = (reg_array == r_name)
                count_r = int(np.sum(mask))
                if count_r == 0:
                    continue

                r_p_sub = y_raw[mask]
                mean_p_ret = float(np.mean(r_p_sub))

                if bench_array is not None:
                    r_b_sub = bench_array[mask]
                    mean_b_ret = float(np.mean(r_b_sub))
                    act_sub = r_p_sub - r_b_sub
                    mean_act_ret = float(np.mean(act_sub))
                    win_rate = float(np.mean(act_sub > 0.0))
                else:
                    mean_b_ret = 0.0
                    mean_act_ret = mean_p_ret
                    win_rate = float(np.mean(r_p_sub > 0.0))

                # Conditional beta to MKT if available
                cond_beta = 0.0
                if "MKT" in factor_betas:
                    mkt_idx = selected_factors.index("MKT")
                    mkt_sub = factor_matrix_cols[mkt_idx][mask]
                    cov_mkt = float(np.cov(r_p_sub, mkt_sub)[0, 1]) if count_r > 1 else 0.0
                    var_mkt = float(np.var(mkt_sub, ddof=1)) if count_r > 1 else 1e-8
                    cond_beta = cov_mkt / var_mkt if var_mkt > 1e-12 else 0.0

                regime_breakdown[str(r_name)] = {
                    "count": float(count_r),
                    "mean_portfolio_return": mean_p_ret,
                    "mean_benchmark_return": mean_b_ret,
                    "mean_active_return": mean_act_ret,
                    "win_rate": win_rate,
                    "conditional_beta": cond_beta,
                    "annualized_active_return": mean_act_ret * 252.0,
                }

        return FactorRiskAttributionResult(
            alpha_annualized=alpha_annualized,
            alpha_t_stat=alpha_t_stat,
            alpha_p_value=alpha_p_value,
            factor_betas=factor_betas,
            factor_t_stats=factor_t_stats_dict,
            factor_p_values=factor_p_values_dict,
            factor_contributions=factor_contributions,
            r_squared=r_squared,
            adj_r_squared=adj_r_squared,
            specific_risk=specific_risk,
            regime_breakdown=regime_breakdown,
        )

    # -----------------------------------------------------------------------
    # Institutional Tear Sheet Generator (Text & Markdown)
    # -----------------------------------------------------------------------

    def generate_tear_sheet(
        self,
        result: Union[BrinsonDecompositionResult, MultiPeriodAttributionResult],
        factor_result: Optional[FactorRiskAttributionResult] = None,
        format: str = "text",
        title: Optional[str] = None,
    ) -> str:
        """
        Generate audit-ready institutional performance attribution tear sheet.

        Args:
            result: BrinsonDecompositionResult or MultiPeriodAttributionResult.
            factor_result: Optional FactorRiskAttributionResult for factor & regime risk tear sheet.
            format: Output format ('text' or 'markdown', default 'text').
            title: Custom title for report.

        Returns:
            Formatted string of audit report.
        """
        format_lower = format.lower()
        if format_lower == "markdown":
            return self._format_markdown_tear_sheet(result, factor_result, title)
        return self._format_text_tear_sheet(result, factor_result, title)

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------

    def _aggregate_assets_to_segments(
        self,
        portfolio_weights: Dict[str, float],
        benchmark_weights: Dict[str, float],
        asset_returns_local: Dict[str, float],
        benchmark_returns_local: Dict[str, float],
        currency_returns: Dict[str, float],
        hedge_ratios: Dict[str, float],
        forward_premiums: Dict[str, float],
        benchmark_currency_returns: Dict[str, float],
        segment_mapping: Dict[str, str],
    ) -> Tuple[
        Dict[str, float],
        Dict[str, float],
        Dict[str, float],
        Dict[str, float],
        Dict[str, float],
        Dict[str, float],
        Dict[str, float],
        Dict[str, float],
    ]:
        """Aggregate asset-level inputs into segment-level attributes."""
        all_assets = sorted(set(portfolio_weights.keys()) | set(benchmark_weights.keys()))
        all_segments = sorted(set(segment_mapping.values()))

        seg_p_weights = {s: 0.0 for s in all_segments}
        seg_b_weights = {s: 0.0 for s in all_segments}

        for a in all_assets:
            s = segment_mapping.get(a, "UNCLASSIFIED")
            seg_p_weights[s] = seg_p_weights.get(s, 0.0) + float(portfolio_weights.get(a, 0.0))
            seg_b_weights[s] = seg_b_weights.get(s, 0.0) + float(benchmark_weights.get(a, 0.0))

        # Weighted return and currency metrics per segment
        seg_p_returns: Dict[str, float] = {}
        seg_b_returns: Dict[str, float] = {}
        seg_c_p: Dict[str, float] = {}
        seg_c_b: Dict[str, float] = {}
        seg_h: Dict[str, float] = {}
        seg_f: Dict[str, float] = {}

        for s in seg_p_weights.keys():
            w_p = seg_p_weights[s]
            w_b = seg_b_weights[s]

            sum_p_ret = 0.0
            sum_b_ret = 0.0
            sum_c_p = 0.0
            sum_c_b = 0.0
            sum_h = 0.0
            sum_f = 0.0

            for a in all_assets:
                if segment_mapping.get(a) != s:
                    continue
                a_wp = float(portfolio_weights.get(a, 0.0))
                a_wb = float(benchmark_weights.get(a, 0.0))

                sum_p_ret += a_wp * float(asset_returns_local.get(a, 0.0))
                sum_b_ret += a_wb * float(benchmark_returns_local.get(a, 0.0))
                sum_c_p += a_wp * float(currency_returns.get(a, 0.0))
                sum_c_b += a_wb * float(benchmark_currency_returns.get(a, currency_returns.get(a, 0.0)))
                sum_h += a_wp * float(hedge_ratios.get(a, 0.0))
                sum_f += a_wp * float(forward_premiums.get(a, 0.0))

            seg_p_returns[s] = (sum_p_ret / w_p) if w_p > 0.0 else 0.0
            seg_b_returns[s] = (sum_b_ret / w_b) if w_b > 0.0 else 0.0
            seg_c_p[s] = (sum_c_p / w_p) if w_p > 0.0 else 0.0
            seg_c_b[s] = (sum_c_b / w_b) if w_b > 0.0 else seg_c_p[s]
            seg_h[s] = float(np.clip((sum_h / w_p) if w_p > 0.0 else 0.0, 0.0, 1.0))
            seg_f[s] = (sum_f / w_p) if w_p > 0.0 else 0.0

        return (
            seg_p_weights,
            seg_b_weights,
            seg_p_returns,
            seg_b_returns,
            seg_c_p,
            seg_c_b,
            seg_h,
            seg_f,
        )

    def _format_text_tear_sheet(
        self,
        result: Union[BrinsonDecompositionResult, MultiPeriodAttributionResult],
        factor_result: Optional[FactorRiskAttributionResult] = None,
        title: Optional[str] = None,
    ) -> str:
        """Format tear sheet as plain text ASCII report."""
        lines: List[str] = []
        bar = "=" * 82
        sub_bar = "-" * 82

        lines.append(bar)
        default_title = "INSTITUTIONAL PERFORMANCE ATTRIBUTION TEAR SHEET"
        lines.append(f"  {title or default_title}  ({self.base_currency})")
        lines.append(bar)

        is_multi = isinstance(result, MultiPeriodAttributionResult)

        if is_multi:
            lines.append(f"  Horizon: Multi-Period ({len(result.daily_results)} periods, Carino Linked)")
            lines.append(f"  Cumulative Portfolio Return: {result.cumulative_portfolio_return * 100:+.4f}%")
            lines.append(f"  Cumulative Benchmark Return: {result.cumulative_benchmark_return * 100:+.4f}%")
            lines.append(f"  Cumulative Active Return:    {result.cumulative_active_return * 100:+.4f}%")
            lines.append(sub_bar)
            lines.append("  EXECUTIVE SUMMARY (Carino Multi-Period Decomposition):")
            lines.append(f"    Allocation Effect (R_alloc):   {result.cumulative_allocation * 100:+.4f}%")
            lines.append(f"    Selection Effect  (R_select):  {result.cumulative_selection * 100:+.4f}%")
            lines.append(f"    Interaction Effect(R_inter):   {result.cumulative_interaction * 100:+.4f}%")
            lines.append(f"    Currency Effect   (R_curr):    {result.cumulative_currency * 100:+.4f}%")
            lines.append(f"    Arithmetic Identity Error:     {result.arithmetic_identity_error:.2e} (Valid: {result.is_identity_valid})")
        else:
            lines.append(f"  Horizon: Single-Period (As-Of: {result.as_of_date or 'N/A'})")
            lines.append(f"  Portfolio Return (Base): {result.portfolio_return_base * 100:+.4f}%")
            lines.append(f"  Benchmark Return (Base): {result.benchmark_return_base * 100:+.4f}%")
            lines.append(f"  Total Active Return:     {result.total_active_return * 100:+.4f}%")
            lines.append(sub_bar)
            lines.append("  EXECUTIVE SUMMARY (Brinson-Fachler Multi-Currency Decomposition):")
            lines.append(f"    Allocation Effect (R_alloc):   {result.allocation_effect * 100:+.4f}%")
            lines.append(f"    Selection Effect  (R_select):  {result.selection_effect * 100:+.4f}%")
            lines.append(f"    Interaction Effect(R_inter):   {result.interaction_effect * 100:+.4f}%")
            lines.append(f"    Currency Effect   (R_curr):    {result.currency_effect * 100:+.4f}%")
            lines.append(f"      - Currency Allocation:       {result.currency_allocation * 100:+.4f}%")
            lines.append(f"      - Currency Selection/Hedge:  {result.currency_selection * 100:+.4f}%")
            lines.append(f"      - Currency Interaction:      {result.currency_interaction * 100:+.4f}%")
            lines.append(f"    Arithmetic Identity Error:     {result.arithmetic_identity_error:.2e} (Valid: {result.is_identity_valid})")

            # Segment Table
            lines.append(sub_bar)
            lines.append("  SEGMENT ATTRIBUTION BREAKDOWN:")
            header_fmt = "{:<16} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8} {:>8}"
            lines.append(header_fmt.format(
                "Segment", "W_p(%)", "W_b(%)", "R_p(%)", "R_b(%)", "Alloc(%)", "Sel(%)", "Inter(%)", "Curr(%)"
            ))
            row_fmt = "{:<16} {:>8.2f} {:>8.2f} {:>8.2f} {:>8.2f} {:>8.4f} {:>8.4f} {:>8.4f} {:>8.4f}"
            for seg in result.segments:
                lines.append(row_fmt.format(
                    seg.segment[:16],
                    seg.portfolio_weight * 100.0,
                    seg.benchmark_weight * 100.0,
                    seg.portfolio_return_local * 100.0,
                    seg.benchmark_return_local * 100.0,
                    seg.allocation_effect * 100.0,
                    seg.selection_effect * 100.0,
                    seg.interaction_effect * 100.0,
                    seg.currency_effect * 100.0,
                ))

        # Factor Risk Attribution Table
        if factor_result is not None:
            lines.append(sub_bar)
            lines.append("  FACTOR RISK MAPPING (Fama-French 5-Factors + Momentum):")
            lines.append(f"    Annualized Alpha:   {factor_result.alpha_annualized * 100:+.2f}% (t={factor_result.alpha_t_stat:+.2f}, p={factor_result.alpha_p_value:.4f})")
            lines.append(f"    R-Squared:          {factor_result.r_squared:.4f} (Adj R^2: {factor_result.adj_r_squared:.4f})")
            lines.append(f"    Specific Risk:      {factor_result.specific_risk * 100:.2f}% (Annualized)")
            lines.append("")
            f_hdr = "{:<12} {:>10} {:>10} {:>10} {:>14}"
            lines.append(f_hdr.format("Factor", "Beta", "t-stat", "p-value", "Contrib(%)"))
            f_row = "{:<12} {:>10.4f} {:>10.2f} {:>10.4f} {:>14.4f}"
            for f_name, beta_val in factor_result.factor_betas.items():
                t_val = factor_result.factor_t_stats.get(f_name, 0.0)
                p_val = factor_result.factor_p_values.get(f_name, 1.0)
                c_val = factor_result.factor_contributions.get(f_name, 0.0) * 100.0
                lines.append(f_row.format(f_name, beta_val, t_val, p_val, c_val))

            if factor_result.regime_breakdown:
                lines.append(sub_bar)
                lines.append("  2D MARKET REGIME CONDITIONAL PERFORMANCE:")
                r_hdr = "{:<20} {:>6} {:>10} {:>10} {:>10} {:>10} {:>10}"
                lines.append(r_hdr.format("Regime", "Count", "MeanPort(%)", "MeanAct(%)", "WinRate(%)", "CondBeta", "AnnAct(%)"))
                r_row = "{:<20} {:>6} {:>10.2f} {:>10.2f} {:>10.1f} {:>10.2f} {:>10.2f}"
                for r_name, r_metrics in factor_result.regime_breakdown.items():
                    lines.append(r_row.format(
                        r_name[:20],
                        int(r_metrics.get("count", 0)),
                        r_metrics.get("mean_portfolio_return", 0.0) * 100.0,
                        r_metrics.get("mean_active_return", 0.0) * 100.0,
                        r_metrics.get("win_rate", 0.0) * 100.0,
                        r_metrics.get("conditional_beta", 0.0),
                        r_metrics.get("annualized_active_return", 0.0) * 100.0,
                    ))

        lines.append(bar)
        return "\n".join(lines)

    def _format_markdown_tear_sheet(
        self,
        result: Union[BrinsonDecompositionResult, MultiPeriodAttributionResult],
        factor_result: Optional[FactorRiskAttributionResult] = None,
        title: Optional[str] = None,
    ) -> str:
        """Format tear sheet as GitHub-flavored Markdown report."""
        lines: List[str] = []
        default_title = "Institutional Performance Attribution Tear Sheet"
        lines.append(f"# {title or default_title} ({self.base_currency})")
        lines.append("")

        is_multi = isinstance(result, MultiPeriodAttributionResult)

        if is_multi:
            lines.append("## Executive Summary (Carino Multi-Period Linking)")
            lines.append(f"- **Periods Evaluated**: {len(result.daily_results)}")
            lines.append(f"- **Cumulative Portfolio Return**: `{result.cumulative_portfolio_return * 100:+.4f}%`")
            lines.append(f"- **Cumulative Benchmark Return**: `{result.cumulative_benchmark_return * 100:+.4f}%`")
            lines.append(f"- **Cumulative Total Active Return**: `{result.cumulative_active_return * 100:+.4f}%`")
            lines.append(f"- **Arithmetic Identity Error**: `{result.arithmetic_identity_error:.2e}` (Valid: **{result.is_identity_valid}**)")
            lines.append("")
            lines.append("### Active Return Decomposition")
            lines.append("| Component | Description | Contribution (%) |")
            lines.append("|---|---|---:|")
            lines.append(f"| $R_{{\\text{{alloc}}}}$ | Asset / Sector Allocation Effect | `{result.cumulative_allocation * 100:+.4f}%` |")
            lines.append(f"| $R_{{\\text{{select}}}}$ | Security Selection Effect | `{result.cumulative_selection * 100:+.4f}%` |")
            lines.append(f"| $R_{{\\text{{inter}}}}$ | Allocation-Selection Interaction | `{result.cumulative_interaction * 100:+.4f}%` |")
            lines.append(f"| $R_{{\\text{{curr}}}}$ | Multi-Currency Hedging & Spillover | `{result.cumulative_currency * 100:+.4f}%` |")
            lines.append(f"| **Total** | **Exact Active Return** | **`{result.cumulative_active_return * 100:+.4f}%`** |")
        else:
            lines.append(f"## Executive Summary (Single Period: {result.as_of_date or 'N/A'})")
            lines.append(f"- **Portfolio Base Return**: `{result.portfolio_return_base * 100:+.4f}%`")
            lines.append(f"- **Benchmark Base Return**: `{result.benchmark_return_base * 100:+.4f}%`")
            lines.append(f"- **Total Active Return**: `{result.total_active_return * 100:+.4f}%`")
            lines.append(f"- **Arithmetic Identity Error**: `{result.arithmetic_identity_error:.2e}` (Valid: **{result.is_identity_valid}**)")
            lines.append("")
            lines.append("### Active Return Decomposition")
            lines.append("| Component | Description | Contribution (%) |")
            lines.append("|---|---|---:|")
            lines.append(f"| $R_{{\\text{{alloc}}}}$ | Sector / Segment Allocation | `{result.allocation_effect * 100:+.4f}%` |")
            lines.append(f"| $R_{{\\text{{select}}}}$ | Within-Segment Security Selection | `{result.selection_effect * 100:+.4f}%` |")
            lines.append(f"| $R_{{\\text{{inter}}}}$ | Allocation-Selection Interaction | `{result.interaction_effect * 100:+.4f}%` |")
            lines.append(f"| $R_{{\\text{{curr}}}}$ | Currency Exposure & Hedging Alpha | `{result.currency_effect * 100:+.4f}%` |")
            lines.append(f"| **Total** | **Exact Active Return** | **`{result.total_active_return * 100:+.4f}%`** |")
            lines.append("")
            lines.append("### Currency Sub-Decomposition")
            lines.append("| Currency Component | Return Effect (%) |")
            lines.append("|---|---:|")
            lines.append(f"| Currency Allocation | `{result.currency_allocation * 100:+.4f}%` |")
            lines.append(f"| Currency Selection & Hedging | `{result.currency_selection * 100:+.4f}%` |")
            lines.append(f"| Currency Cross Interaction | `{result.currency_interaction * 100:+.4f}%` |")
            lines.append(f"| **Total Currency Effect** | **`{result.currency_effect * 100:+.4f}%`** |")
            lines.append("")
            lines.append("### Segment Attribution Table")
            lines.append("| Segment | Port Wgt (%) | Bench Wgt (%) | Port Ret (%) | Bench Ret (%) | Alloc (%) | Select (%) | Inter (%) | Curr (%) | Active (%) |")
            lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
            for s in result.segments:
                lines.append(
                    f"| {s.segment} | {s.portfolio_weight*100:.2f} | {s.benchmark_weight*100:.2f} | "
                    f"{s.portfolio_return_local*100:+.2f} | {s.benchmark_return_local*100:+.2f} | "
                    f"{s.allocation_effect*100:+.4f} | {s.selection_effect*100:+.4f} | "
                    f"{s.interaction_effect*100:+.4f} | {s.currency_effect*100:+.4f} | "
                    f"{s.total_active_return*100:+.4f} |"
                )

        if factor_result is not None:
            lines.append("")
            lines.append("## Factor Risk Attribution (Fama-French 5-Factors + Momentum)")
            lines.append(f"- **Annualized Alpha (\\(\\alpha\\))**: `{factor_result.alpha_annualized * 100:+.2f}%` (t = `{factor_result.alpha_t_stat:+.2f}`, p = `{factor_result.alpha_p_value:.4f}`)")
            lines.append(f"- **Coefficient of Determination (\\(R^2\\))**: `{factor_result.r_squared:.4f}` (Adj \\(R^2\\): `{factor_result.adj_r_squared:.4f}`)")
            lines.append(f"- **Specific Idiosyncratic Risk**: `{factor_result.specific_risk * 100:.2f}%` (Annualized)")
            lines.append("")
            lines.append("| Factor | Beta (\\(\\beta\\)) | t-statistic | p-value | Annualized Contribution (%) |")
            lines.append("|---|---:|---:|---:|---:|")
            for f_name, beta_val in factor_result.factor_betas.items():
                t_val = factor_result.factor_t_stats.get(f_name, 0.0)
                p_val = factor_result.factor_p_values.get(f_name, 1.0)
                c_val = factor_result.factor_contributions.get(f_name, 0.0) * 100.0
                lines.append(f"| **{f_name}** | `{beta_val:+.4f}` | `{t_val:+.2f}` | `{p_val:.4f}` | `{c_val:+.4f}%` |")

            if factor_result.regime_breakdown:
                lines.append("")
                lines.append("## 2D Market Regime Conditional Performance")
                lines.append("| Market Regime | Count | Mean Port Ret (%) | Mean Bench Ret (%) | Mean Active Ret (%) | Win Rate (%) | Cond Beta | Ann Active (%) |")
                lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
                for r_name, r_metrics in factor_result.regime_breakdown.items():
                    lines.append(
                        f"| **{r_name}** | {int(r_metrics.get('count', 0))} | "
                        f"{r_metrics.get('mean_portfolio_return', 0.0)*100:+.2f}% | "
                        f"{r_metrics.get('mean_benchmark_return', 0.0)*100:+.2f}% | "
                        f"{r_metrics.get('mean_active_return', 0.0)*100:+.2f}% | "
                        f"{r_metrics.get('win_rate', 0.0)*100:.1f}% | "
                        f"{r_metrics.get('conditional_beta', 0.0):.2f} | "
                        f"{r_metrics.get('annualized_active_return', 0.0)*100:+.2f}% |"
                    )

        lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full Alias Trees (Production Backward Compatibility)
# ---------------------------------------------------------------------------

InstitutionalBrinsonFactorAttributor = BrinsonFactorAttributor
Phase108BrinsonFactorAttributor = BrinsonFactorAttributor
MultiCurrencyBrinsonAttributor = BrinsonFactorAttributor
BrinsonFachlerPerformanceAttributor = BrinsonFactorAttributor
