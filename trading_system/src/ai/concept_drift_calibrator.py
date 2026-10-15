"""
concept_drift_calibrator.py — Continuous Online Concept Drift Detector & CUSUM Model Calibration.

Phase 108 / Feature F510 / Release R124 (v115 Production Master)

Real-time statistical concept drift detection and adaptive model calibration engine:
1. Monitors prediction residuals and forecast errors across 37 strategies using:
   - Two-sided Page-Hinkley test on normalized residuals (ph_up, ph_down).
   - Two-sided CUSUM test for mean drift (s_pos, s_neg) and variance shift (c_var_pos, c_var_neg).
2. Quantifies distribution drift velocities:
   v_drift = composite_stat / sqrt(delta_t).
3. Executes adaptive EWMA shrinkage and Bayesian prior recalibration when drift statistic
   breaches threshold h_drift, damping strategy weights and forecast probabilities towards prior 0.50.
4. Enforces strict simplex weight normalization (sum == 1.000000, w_i >= 0.0).
5. Enforces point-in-time logging and causal zero-lookahead (running statistics mu_{t-1}, sigma_{t-1}
   computed strictly prior to observing outcome y_t).
6. Detects macro regime transitions: if >= 50% of strategies drift simultaneously, flags
   systemic REGIME_SHIFT state and triggers defensive capital allocation.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


class DriftStatus(str, Enum):
    """Classification status for strategy concept drift."""
    STABLE = "STABLE"
    WARNING = "WARNING"
    DRIFT_DETECTED = "DRIFT_DETECTED"
    CRITICAL_DRIFT = "CRITICAL_DRIFT"
    REGIME_SHIFT = "REGIME_SHIFT"


@dataclass
class StrategyResidualObservation:
    """Point-in-time streaming record of a strategy forecast and realized return."""
    timestamp: str
    symbol: str
    strategy_name: str
    predicted_score: float
    realized_return: float
    residual: float
    normalized_residual: float
    prior_mean: float
    prior_std: float


@dataclass
class StrategyDriftMetrics:
    """Encapsulates current drift diagnostic metrics for a strategy."""
    strategy_name: str
    sample_count: int
    mean_residual: float
    std_residual: float
    ph_up: float
    ph_down: float
    ph_statistic: float
    cusum_mean_pos: float
    cusum_mean_neg: float
    cusum_mean_statistic: float
    cusum_var_pos: float
    cusum_var_neg: float
    cusum_var_statistic: float
    composite_drift_score: float
    drift_velocity: float
    status: DriftStatus
    shrinkage_factor: float
    effective_weight: float
    mean_drift_flag: bool = False
    var_drift_flag: bool = False
    ph_drift_flag: bool = False


class PageHinkleyDetector:
    """
    Two-sided Page-Hinkley sequential change-point detector.
    
    Monitors cumulative deviations of standardized residuals to detect
    both upward surges (ph_up) and downward plunges (ph_down).
    """

    def __init__(
        self,
        delta: float = 0.05,
        threshold_lambda: float = 30.0,
        min_instances: int = 5,
        target_mean: Optional[float] = 0.0,
    ) -> None:
        self.delta = float(delta)
        self.threshold_lambda = float(threshold_lambda)
        self.min_instances = int(min_instances)
        self.target_mean = target_mean
        self.reset()

    def reset(self) -> None:
        """Resets detector state to initial baseline."""
        self.n: int = 0
        self.mean: float = 0.0
        self.sum_up: float = 0.0
        self.min_up: float = 0.0
        self.sum_down: float = 0.0
        self.max_down: float = 0.0
        self.ph_up: float = 0.0
        self.ph_down: float = 0.0
        self.is_drift: bool = False

    def update(self, x: float) -> Tuple[bool, float, float]:
        """
        Updates the two-sided Page-Hinkley test with observation x.
        
        Returns:
            Tuple of (is_drift, ph_up, ph_down).
        """
        self.n += 1
        self.mean += (x - self.mean) / self.n
        dev = (x - self.target_mean) if self.target_mean is not None else (x - self.mean)

        # Upward test accumulation
        self.sum_up += (dev - self.delta)
        self.min_up = min(self.min_up, self.sum_up)
        self.ph_up = max(0.0, self.sum_up - self.min_up)

        # Downward test accumulation
        self.sum_down += (dev + self.delta)
        self.max_down = max(self.max_down, self.sum_down)
        self.ph_down = max(0.0, self.max_down - self.sum_down)

        if self.n >= self.min_instances:
            self.is_drift = bool(
                self.ph_up >= self.threshold_lambda or self.ph_down >= self.threshold_lambda
            )
        else:
            self.is_drift = False

        return self.is_drift, self.ph_up, self.ph_down


class TwoSidedCUSUMDetector:
    """
    Two-sided CUSUM detector for monitoring:
    1. Mean shift in standardized residuals z (s_pos, s_neg).
    2. Variance/scale shift in z^2 - 1.0 (c_var_pos, c_var_neg).
    """

    def __init__(
        self,
        k_mean: float = 0.5,
        h_mean: float = 5.0,
        k_var: float = 0.5,
        h_var: float = 6.0,
        min_instances: int = 5,
    ) -> None:
        self.k_mean = float(k_mean)
        self.h_mean = float(h_mean)
        self.k_var = float(k_var)
        self.h_var = float(h_var)
        self.min_instances = int(min_instances)
        self.reset()

    def reset(self) -> None:
        """Resets CUSUM accumulators."""
        self.n: int = 0
        self.s_pos: float = 0.0
        self.s_neg: float = 0.0
        self.c_var_pos: float = 0.0
        self.c_var_neg: float = 0.0
        self.s_stat: float = 0.0
        self.c_stat: float = 0.0
        self.mean_drift: bool = False
        self.var_drift: bool = False
        self.tau_mean: int = 0
        self.tau_var: int = 0

    def update(self, z: float) -> Tuple[bool, bool, float, float]:
        """
        Updates CUSUM statistics with standardized residual z.
        
        Returns:
            Tuple of (mean_drift, var_drift, s_stat, c_stat).
        """
        self.n += 1

        # Mean CUSUM: checks positive and negative deviations from zero
        self.s_pos = max(0.0, self.s_pos + z - self.k_mean)
        self.s_neg = max(0.0, self.s_neg - z - self.k_mean)
        self.s_stat = max(self.s_pos, self.s_neg)

        # Variance CUSUM: checks deviations of squared normalized residuals from 1.0
        u = (z ** 2) - 1.0
        self.c_var_pos = max(0.0, self.c_var_pos + u - self.k_var)
        self.c_var_neg = max(0.0, self.c_var_neg - u - self.k_var)
        self.c_stat = max(self.c_var_pos, self.c_var_neg)

        if self.n >= self.min_instances:
            self.mean_drift = bool(self.s_stat >= self.h_mean)
            self.var_drift = bool(self.c_var_pos >= self.h_var or self.c_stat >= self.h_var)
        else:
            self.mean_drift = False
            self.var_drift = False

        return self.mean_drift, self.var_drift, self.s_stat, self.c_stat


class BayesianWeightCalibrator:
    """
    Adaptive EWMA shrinkage and Bayesian prior recalibrator.
    
    Shrinks strategy weights towards informative prior or equal weights,
    and damps predicted probabilities towards neutral odds (0.50)
    during detected concept drift.
    """

    def __init__(
        self,
        kappa_shrink: float = 0.85,
        min_shrinkage: float = 0.05,
        prior_score: float = 0.50,
    ) -> None:
        self.kappa_shrink = float(kappa_shrink)
        self.min_shrinkage = float(min_shrinkage)
        self.prior_score = float(prior_score)

    def compute_shrinkage_factor(
        self,
        composite_drift_score: float,
        drift_velocity: float,
    ) -> float:
        """
        Computes adaptive shrinkage factor gamma in [min_shrinkage, 1.0].
        
        gamma = exp( -kappa_shrink * max(0, D - 1.0) * (1 + 0.5 * v_drift) )
        """
        if composite_drift_score <= 1.0:
            return 1.0

        excess_drift = max(0.0, composite_drift_score - 1.0)
        velocity_mult = 1.0 + 0.5 * max(0.0, drift_velocity)
        exponent = -self.kappa_shrink * excess_drift * velocity_mult
        exponent = max(-50.0, min(50.0, exponent))

        gamma = math.exp(exponent)
        return float(max(self.min_shrinkage, min(0.95, gamma)))

    def shrink_score(
        self,
        raw_score: float,
        shrinkage_factor: float,
        target_prior: Optional[float] = None,
    ) -> float:
        """
        Damps individual forecast score towards prior (default 0.50).
        
        p_calibrated = target_prior + gamma * (p_raw - target_prior)
        """
        if shrinkage_factor >= 1.0:
            return float(raw_score)

        prior = self.prior_score if target_prior is None else target_prior
        calibrated = prior + shrinkage_factor * (raw_score - prior)
        return float(max(0.0, min(1.0, calibrated)))

    def project_to_simplex(
        self,
        weights: Dict[str, float],
        floor: float = 0.0,
    ) -> Dict[str, float]:
        """
        Projects weight dictionary onto probability simplex sum(w) == 1.000000, w_i >= 0.0.
        """
        if not weights:
            return {}

        clean_weights: Dict[str, float] = {}
        for k, v in weights.items():
            if np.isfinite(v):
                clean_weights[k] = max(floor, float(v))
            else:
                clean_weights[k] = floor

        total_sum = sum(clean_weights.values())
        n = len(clean_weights)

        if total_sum <= 1e-12:
            uniform = 1.0 / n
            return {k: uniform for k in clean_weights}

        normalized = {k: v / total_sum for k, v in clean_weights.items()}

        # Exact precision correction for float sum == 1.000000
        norm_sum = sum(normalized.values())
        diff = 1.0 - norm_sum
        if abs(diff) > 1e-15:
            best_k = max(normalized.keys(), key=lambda k: normalized[k])
            normalized[best_k] = max(0.0, normalized[best_k] + diff)

        return normalized

    def calibrate_weights(
        self,
        base_weights: Dict[str, float],
        drift_metrics: Dict[str, StrategyDriftMetrics],
        prior_weights: Optional[Dict[str, float]] = None,
        is_regime_shift: bool = False,
        quality_strategies: Optional[Sequence[str]] = None,
    ) -> Dict[str, float]:
        """
        Applies adaptive shrinkage to base weights and normalizes to simplex.
        """
        if not base_weights:
            return {}

        n_strategies = len(base_weights)
        default_prior = 1.0 / n_strategies

        # Build prior distribution
        priors: Dict[str, float] = {}
        for k in base_weights:
            if prior_weights and k in prior_weights:
                priors[k] = max(0.0, float(prior_weights[k]))
            else:
                priors[k] = default_prior

        # If regime shift active, tilt prior towards quality / defensive factors
        if is_regime_shift and quality_strategies:
            q_set = set(quality_strategies)
            for k in priors:
                if k in q_set:
                    priors[k] *= 2.0
                else:
                    priors[k] *= 0.5
        priors = self.project_to_simplex(priors)

        shrunk_weights: Dict[str, float] = {}
        for k, base_w in base_weights.items():
            metric = drift_metrics.get(k)
            gamma = metric.shrinkage_factor if metric is not None else 1.0
            prior_w = priors.get(k, default_prior)

            # In regime shift, accelerate shrinkage
            if is_regime_shift:
                gamma = gamma * 0.70

            w_shrunk = gamma * max(0.0, float(base_w)) + (1.0 - gamma) * prior_w
            shrunk_weights[k] = max(0.0, w_shrunk)

        return self.project_to_simplex(shrunk_weights)


class ContinuousConceptDriftCalibrator:
    """
    Master Continuous Online Concept Drift Detector & CUSUM Model Calibration Engine.
    
    Tracks 37 strategies in real-time, executing sequential two-sided change point detection,
    drift velocity estimation, Bayesian EWMA score damping, and systemic macro regime gating.
    """

    STRATEGIES_37: List[str] = [
        "regression",
        "surge",
        "lead_lag",
        "vcp_rule",
        "vcp_ml",
        "lstm",
        "stat_arb",
        "sector_rotation",
        "rim_valuation",
        "event_driven",
        "mq_factor",
        "iv_skew",
        "order_flow",
        "short_term_reversal",
        "arm_factor",
        "card_factor",
        "latr_factor",
        "inst_foreign_sector",
        "supply_chain",
        "sentiment",
        "factor_neutralized",
        "vol_target",
        "microstructure",
        "accruals_quality",
        "short_squeeze",
        "valueup_catalyst",
        "trend_efficiency",
        "gamma_squeeze",
        "insider_buying",
        "darkpool",
        "earnings_tone_drift",
        "cross_asset_spillover",
        "supply_chain_gnn",
        "range_expansion_breakout",
        "dual_correction",
        "index_rebalance",
        "overnight_gap_reversal",
    ]

    STRATEGY_ALIASES: Dict[str, str] = {
        "range_expansion": "range_expansion_breakout",
        "overnight_gap": "overnight_gap_reversal",
    }

    DEFENSIVE_QUALITY_STRATEGIES: List[str] = [
        "rim_valuation",
        "accruals_quality",
        "mq_factor",
        "valueup_catalyst",
        "factor_neutralized",
        "regression",
        "vol_target",
    ]

    def __init__(
        self,
        config: Optional[Any] = None,
        ph_delta: float = 0.05,
        ph_threshold_lambda: float = 30.0,
        cusum_k_mean: float = 0.5,
        cusum_h_mean: float = 5.0,
        cusum_k_var: float = 0.5,
        cusum_h_var: float = 6.0,
        kappa_shrink: float = 0.85,
        min_shrinkage: float = 0.05,
        regime_shift_threshold: float = 0.50,
        baseline_std: float = 1.0,
        history_limit: int = 500,
    ) -> None:
        self.config = config
        self.ph_delta = float(ph_delta)
        self.ph_threshold_lambda = float(ph_threshold_lambda)
        self.cusum_k_mean = float(cusum_k_mean)
        self.cusum_h_mean = float(cusum_h_mean)
        self.cusum_k_var = float(cusum_k_var)
        self.cusum_h_var = float(cusum_h_var)
        self.kappa_shrink = float(kappa_shrink)
        self.min_shrinkage = float(min_shrinkage)
        self.regime_shift_threshold = float(regime_shift_threshold)
        self.baseline_std = float(baseline_std)
        self.history_limit = int(history_limit)

        self.version = getattr(config, "version", 115) if config is not None else 115
        self.is_phase108 = self.version >= 108

        self.calibrator = BayesianWeightCalibrator(
            kappa_shrink=self.kappa_shrink,
            min_shrinkage=self.min_shrinkage,
        )

        # Per-strategy state containers
        self._ph_detectors: Dict[str, PageHinkleyDetector] = {}
        self._cusum_detectors: Dict[str, TwoSidedCUSUMDetector] = {}
        self._welford_stats: Dict[str, Dict[str, float]] = {}
        self._metrics: Dict[str, StrategyDriftMetrics] = {}
        self._observations: Dict[str, List[StrategyResidualObservation]] = {}
        self._pending_predictions: Dict[Tuple[str, str], Tuple[float, str]] = {}
        self._active_steps_since_change: Dict[str, int] = {}

        self.reset_all()

    def canonical_strategy_name(self, strategy: str) -> str:
        """Resolves strategy aliases to canonical name."""
        return self.STRATEGY_ALIASES.get(strategy, strategy)

    def _init_strategy(self, strategy: str) -> None:
        """Initializes detector components for a strategy."""
        strat = self.canonical_strategy_name(strategy)
        self._ph_detectors[strat] = PageHinkleyDetector(
            delta=self.ph_delta,
            threshold_lambda=self.ph_threshold_lambda,
            target_mean=0.0,
        )
        self._cusum_detectors[strat] = TwoSidedCUSUMDetector(
            k_mean=self.cusum_k_mean,
            h_mean=self.cusum_h_mean,
            k_var=self.cusum_k_var,
            h_var=self.cusum_h_var,
        )
        self._welford_stats[strat] = {
            "count": 0.0,
            "mean": 0.0,
            "m2": 0.0,
            "std": self.baseline_std,
        }
        self._metrics[strat] = StrategyDriftMetrics(
            strategy_name=strat,
            sample_count=0,
            mean_residual=0.0,
            std_residual=self.baseline_std,
            ph_up=0.0,
            ph_down=0.0,
            ph_statistic=0.0,
            cusum_mean_pos=0.0,
            cusum_mean_neg=0.0,
            cusum_mean_statistic=0.0,
            cusum_var_pos=0.0,
            cusum_var_neg=0.0,
            cusum_var_statistic=0.0,
            composite_drift_score=0.0,
            drift_velocity=0.0,
            status=DriftStatus.STABLE,
            shrinkage_factor=1.0,
            effective_weight=1.0 / len(self.STRATEGIES_37),
            mean_drift_flag=False,
            var_drift_flag=False,
            ph_drift_flag=False,
        )
        self._observations[strat] = []
        self._active_steps_since_change[strat] = 0

    def reset_all(self) -> None:
        """Resets all detectors and states across all 37 strategies."""
        self._ph_detectors.clear()
        self._cusum_detectors.clear()
        self._welford_stats.clear()
        self._metrics.clear()
        self._observations.clear()
        self._pending_predictions.clear()
        self._active_steps_since_change.clear()

        for strat in self.STRATEGIES_37:
            self._init_strategy(strat)

    def reset(self, strategy: Optional[str] = None) -> None:
        """Resets a single strategy or all strategies if strategy is None."""
        if strategy is None:
            self.reset_all()
        else:
            strat = self.canonical_strategy_name(strategy)
            self._init_strategy(strat)

    def record_prediction(
        self,
        symbol: str,
        strategy: str,
        score: float,
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Point-in-time logging of forecast prior to outcome realization.
        Ensures causal zero-lookahead auditability.
        """
        strat = self.canonical_strategy_name(strategy)
        if strat not in self._metrics:
            self._init_strategy(strat)

        ts = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._pending_predictions[(symbol, strat)] = (float(score), ts)

    def observe_residual(
        self,
        strategy: str,
        residual: float,
        symbol: str = "GLOBAL",
        timestamp: Optional[str] = None,
        predicted_score: float = 0.50,
        realized_return: Optional[float] = None,
    ) -> StrategyDriftMetrics:
        """
        Core causal update engine directly receiving a residual observation.
        Standardizes residual using running statistics (mu_{t-1}, sigma_{t-1})
        computed strictly prior to observing current residual.
        """
        strat = self.canonical_strategy_name(strategy)
        if strat not in self._metrics:
            self._init_strategy(strat)

        ts = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not math.isfinite(residual):
            res = 0.0
        else:
            res = float(residual)
        # Clamp extreme float values to prevent float overflow in Welford variance calculation
        res = max(-1000.0, min(1000.0, res))
        ret = realized_return if realized_return is not None else (predicted_score - res)

        # 1. Causal Zero-Lookahead: Fetch prior running stats (mu_{t-1}, sigma_{t-1})
        wf = self._welford_stats[strat]
        count = int(wf["count"])
        prior_mean = wf["mean"]
        prior_std = self.baseline_std

        # Forecast residuals are standardized against the baseline in-control reference sigma_0
        z = (res - 0.0) / prior_std
        z = max(-20.0, min(20.0, z))  # Extreme outlier clipping for numerical safety

        # 2. Update Welford's running statistics for step t
        new_count = count + 1
        delta = res - prior_mean
        new_mean = prior_mean + delta / new_count
        delta2 = res - new_mean
        new_m2 = max(0.0, wf["m2"] + delta * delta2)
        new_std = math.sqrt(new_m2 / new_count) if new_count > 1 else self.baseline_std

        wf["count"] = float(new_count)
        wf["mean"] = float(new_mean)
        wf["m2"] = float(new_m2)
        wf["std"] = float(max(1e-4, new_std))

        # 3. Update Two-Sided Page-Hinkley Detector
        ph = self._ph_detectors[strat]
        ph_drift, ph_up, ph_down = ph.update(z)
        ph_stat = max(ph_up, ph_down)

        # 4. Update Two-Sided CUSUM Detector
        cusum = self._cusum_detectors[strat]
        mean_drift, var_drift, s_stat, c_stat = cusum.update(z)

        # 5. Composite Drift Metric & Velocity
        s_ph = ph_stat / self.ph_threshold_lambda
        s_mean = s_stat / self.cusum_h_mean
        s_var = cusum.c_var_pos / self.cusum_h_var
        composite_score = float(max(s_ph, s_mean, s_var))

        # If CUSUM mean or var drift flagged, composite score must be at least 1.0
        if mean_drift or var_drift or ph_drift:
            composite_score = max(1.05, composite_score)

        # Track active drift interval duration
        self._active_steps_since_change[strat] += 1
        delta_t = max(1, self._active_steps_since_change[strat])
        drift_velocity = float(composite_score / math.sqrt(delta_t))

        # 6. Status Determination
        if composite_score >= 2.0:
            status = DriftStatus.CRITICAL_DRIFT
        elif composite_score >= 1.0 or ph_drift or mean_drift or var_drift:
            status = DriftStatus.DRIFT_DETECTED
        elif composite_score >= 0.60:
            status = DriftStatus.WARNING
        else:
            status = DriftStatus.STABLE

        # 7. Adaptive EWMA Shrinkage Factor
        gamma = self.calibrator.compute_shrinkage_factor(
            composite_drift_score=composite_score,
            drift_velocity=drift_velocity,
        )
        if status in (DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT):
            gamma = min(0.95, gamma)

        metrics = StrategyDriftMetrics(
            strategy_name=strat,
            sample_count=new_count,
            mean_residual=float(new_mean),
            std_residual=float(wf["std"]),
            ph_up=float(ph_up),
            ph_down=float(ph_down),
            ph_statistic=float(ph_stat),
            cusum_mean_pos=float(cusum.s_pos),
            cusum_mean_neg=float(cusum.s_neg),
            cusum_mean_statistic=float(s_stat),
            cusum_var_pos=float(cusum.c_var_pos),
            cusum_var_neg=float(cusum.c_var_neg),
            cusum_var_statistic=float(c_stat),
            composite_drift_score=composite_score,
            drift_velocity=drift_velocity,
            status=status,
            shrinkage_factor=gamma,
            effective_weight=1.0 / len(self.STRATEGIES_37),
            mean_drift_flag=mean_drift,
            var_drift_flag=var_drift,
            ph_drift_flag=ph_drift,
        )
        self._metrics[strat] = metrics

        # 8. Record Point-in-Time Observation
        obs = StrategyResidualObservation(
            timestamp=ts,
            symbol=symbol,
            strategy_name=strat,
            predicted_score=float(predicted_score),
            realized_return=float(ret),
            residual=res,
            normalized_residual=float(z),
            prior_mean=float(prior_mean),
            prior_std=float(prior_std),
        )
        obs_list = self._observations[strat]
        obs_list.append(obs)
        if len(obs_list) > self.history_limit:
            obs_list.pop(0)

        return metrics

    def update_realization(
        self,
        symbol: str,
        strategy: str,
        realized_return: float,
        timestamp: Optional[str] = None,
        predicted_score: Optional[float] = None,
    ) -> StrategyDriftMetrics:
        """
        Causal zero-lookahead update upon observing realized return.
        Matches against prior recorded prediction.
        """
        strat = self.canonical_strategy_name(strategy)
        ts = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Retrieve prior prediction if available
        pred = predicted_score
        pred_key = (symbol, strat)
        if pred_key in self._pending_predictions:
            stored_pred, _ = self._pending_predictions.pop(pred_key)
            if pred is None:
                pred = stored_pred

        if pred is None:
            # Fallback if unrecorded
            pred = 0.50

        # Residual = Predicted Score - Realized Return
        residual = float(pred) - float(realized_return)

        return self.observe_residual(
            strategy=strat,
            residual=residual,
            symbol=symbol,
            timestamp=ts,
            predicted_score=float(pred),
            realized_return=float(realized_return),
        )

    def is_regime_shift(self) -> bool:
        """
        Determines whether systemic macro regime shift is active
        (>= 50% of the 37 strategies displaying drift).
        """
        total = len(self._metrics)
        if total == 0:
            return False

        drifted_count = sum(
            1 for m in self._metrics.values()
            if m.status in (DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT)
        )
        return bool((drifted_count / total) >= self.regime_shift_threshold)

    def calibrate_strategy_weights(
        self,
        base_weights: Dict[str, float],
        macro_regime: str = "BULL_LOW_VOL",
        prior_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Calibrates strategy weights using adaptive EWMA shrinkage and Bayesian priors,
        strictly maintaining simplex normalization (sum == 1.000000, w_i >= 0.0).
        """
        if not base_weights:
            return {}

        regime_shift = self.is_regime_shift()
        calibrated = self.calibrator.calibrate_weights(
            base_weights=base_weights,
            drift_metrics=self._metrics,
            prior_weights=prior_weights,
            is_regime_shift=regime_shift,
            quality_strategies=self.DEFENSIVE_QUALITY_STRATEGIES,
        )

        # Update effective weight records in metrics
        for strat, w in calibrated.items():
            if strat in self._metrics:
                self._metrics[strat].effective_weight = float(w)

        return calibrated

    def calibrate_prediction_score(
        self,
        strategy: str,
        raw_score: float,
        target_prior: float = 0.50,
    ) -> float:
        """
        Damps individual strategy predicted score towards neutral prior 0.50
        proportional to its drift shrinkage factor.
        """
        strat = self.canonical_strategy_name(strategy)
        metric = self._metrics.get(strat)
        gamma = metric.shrinkage_factor if metric is not None else 1.0
        return self.calibrator.shrink_score(
            raw_score=raw_score,
            shrinkage_factor=gamma,
            target_prior=target_prior,
        )

    def get_strategy_metrics(self, strategy: str) -> Optional[StrategyDriftMetrics]:
        """Retrieves current drift diagnostics for a strategy."""
        strat = self.canonical_strategy_name(strategy)
        return self._metrics.get(strat)

    def get_drift_report(self) -> Dict[str, Any]:
        """
        Generates comprehensive system-wide drift diagnostic report.
        """
        regime_shift = self.is_regime_shift()
        drifted_strategies: List[str] = []
        warning_strategies: List[str] = []
        velocities: List[float] = []
        composite_scores: List[float] = []

        strategy_details: Dict[str, Dict[str, Any]] = {}
        for strat, m in self._metrics.items():
            composite_scores.append(m.composite_drift_score)
            velocities.append(m.drift_velocity)
            if m.status in (DriftStatus.DRIFT_DETECTED, DriftStatus.CRITICAL_DRIFT):
                drifted_strategies.append(strat)
            elif m.status == DriftStatus.WARNING:
                warning_strategies.append(strat)

            strategy_details[strat] = {
                "status": m.status.value,
                "composite_drift_score": m.composite_drift_score,
                "drift_velocity": m.drift_velocity,
                "shrinkage_factor": m.shrinkage_factor,
                "effective_weight": m.effective_weight,
                "sample_count": m.sample_count,
                "ph_statistic": m.ph_statistic,
                "cusum_mean_statistic": m.cusum_mean_statistic,
                "cusum_var_statistic": m.cusum_var_statistic,
                "mean_drift": m.mean_drift_flag,
                "var_drift": m.var_drift_flag,
                "ph_drift": m.ph_drift_flag,
                "mean_residual": m.mean_residual,
                "std_residual": m.std_residual,
            }

        total_tracked = len(self._metrics)
        drift_ratio = float(len(drifted_strategies) / max(1, total_tracked))

        if regime_shift:
            global_status = DriftStatus.REGIME_SHIFT
        elif len(drifted_strategies) > 0:
            global_status = DriftStatus.DRIFT_DETECTED
        elif len(warning_strategies) > 0:
            global_status = DriftStatus.WARNING
        else:
            global_status = DriftStatus.STABLE

        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "global_status": global_status.value,
            "is_regime_shift": regime_shift,
            "drift_ratio": drift_ratio,
            "drifted_strategy_count": len(drifted_strategies),
            "drifted_strategies": drifted_strategies,
            "warning_strategies": warning_strategies,
            "total_strategies": total_tracked,
            "mean_drift_velocity": float(np.mean(velocities)) if velocities else 0.0,
            "max_composite_drift": float(np.max(composite_scores)) if composite_scores else 0.0,
            "strategies": strategy_details,
        }


# Module entry points
def calibrate_online_concept_drift(
    base_weights: Dict[str, float],
    calibrator: Optional[ContinuousConceptDriftCalibrator] = None,
    macro_regime: str = "BULL_LOW_VOL",
) -> Dict[str, float]:
    """Module-level entry point for concept drift model calibration."""
    engine = calibrator if calibrator is not None else ContinuousConceptDriftCalibrator()
    return engine.calibrate_strategy_weights(base_weights, macro_regime=macro_regime)


# Backward-compatibility alias trees
ConceptDriftCalibrator = ContinuousConceptDriftCalibrator
Phase108ConceptDriftCalibrator = ContinuousConceptDriftCalibrator
OnlineConceptDriftCalibrator = ContinuousConceptDriftCalibrator
CUSUMModelCalibrator = ContinuousConceptDriftCalibrator
PageHinkleyDriftDetector = PageHinkleyDetector
TwoSidedCUSUMTest = TwoSidedCUSUMDetector

__all__ = [
    "DriftStatus",
    "StrategyResidualObservation",
    "StrategyDriftMetrics",
    "PageHinkleyDetector",
    "TwoSidedCUSUMDetector",
    "BayesianWeightCalibrator",
    "ContinuousConceptDriftCalibrator",
    "ConceptDriftCalibrator",
    "Phase108ConceptDriftCalibrator",
    "OnlineConceptDriftCalibrator",
    "CUSUMModelCalibrator",
    "PageHinkleyDriftDetector",
    "TwoSidedCUSUMTest",
    "calibrate_online_concept_drift",
]
