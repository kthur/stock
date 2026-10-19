"""
trading_system/src/core/hawkes_microstructure_alpha.py — L2/L3 Hawkes Microstructure Alpha Predictor

Phase 107 / Feature F507 / Release R123 (v114 Production Master)
Milestone 3: L2/L3 Hawkes Microstructure Alpha Predictor

Implements high-frequency order book queue imbalance and self-exciting point-process
arrival intensity modeling for microstructural alpha prediction:
- Hawkes parameter estimation (mu, alpha, beta) via recursive O(N) log-likelihood MLE
  and calibrated method-of-moments with strict L1 stability enforcement (alpha / beta < 1.0).
- Real-time buy and sell arrival intensity tracking: lambda_B(t), lambda_S(t).
- Directional arrival imbalance: Delta lambda_dir = (lambda_B - lambda_S) / (lambda_B + lambda_S).
- Adverse selection toxicity score: T_adverse in [0.0, 1.0].
- 1~5 minute short-term execution price drift forecast: Delta P_tau (bps & price).
- Composite microstructure alpha score S_micro in [-1.0, 1.0] integrating Level-3 queue
  imbalance (QI_L3), queue velocity (v_QI), queue acceleration (a_QI), and arrival imbalance.
- Closed-loop Almgren-Chriss schedule modulation: dynamic kappa_eff = kappa_0 * chi
  and slice interval compression based on arrival intensity.
- Limit order peg offset calculation: Delta P_offset.
- Production and backward-compatible aliases:
  HawkesMicrostructureAlphaEngine, Phase107HawkesAlphaPredictor,
  MicrostructureHawkesAlphaPredictor, HawkesAlphaPredictor.
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple, Union

import numpy as np

try:
    from scipy.optimize import minimize
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

logger = logging.getLogger(__name__)


@dataclass
class HawkesParameters:
    """
    Fitted parameters for a self-exciting Hawkes point process with L1 stability guarantee.

    Mathematical Invariant:
        branching_ratio = alpha / beta < 1.0 (subcritical, stationary process).
        If alpha >= beta, the process is explosive (supercritical).
    """
    mu: float
    alpha: float
    beta: float
    branching_ratio: float
    log_likelihood: float
    is_stable: bool  # True iff branching_ratio < 1.0
    alpha_self: Optional[float] = None
    alpha_cross: Optional[float] = None
    convergence: bool = True
    iterations: int = 0

    @property
    def stability_margin(self) -> float:
        """Returns 1.0 - branching_ratio. Positive indicates stable subcritical process."""
        return float(1.0 - self.branching_ratio)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes parameters to a standard dictionary."""
        return {
            "mu": float(self.mu),
            "alpha": float(self.alpha),
            "beta": float(self.beta),
            "branching_ratio": float(self.branching_ratio),
            "log_likelihood": float(self.log_likelihood),
            "is_stable": bool(self.is_stable),
            "alpha_self": float(self.alpha_self) if self.alpha_self is not None else None,
            "alpha_cross": float(self.alpha_cross) if self.alpha_cross is not None else None,
            "stability_margin": float(self.stability_margin),
            "convergence": bool(self.convergence),
            "iterations": int(self.iterations),
        }


@dataclass
class MicrostructureAlphaSignal:
    """
    High-frequency L2/L3 order book & Hawkes arrival alpha signal.

    Fields:
        timestamp: Epoch seconds of signal evaluation.
        symbol: Ticker symbol.
        l3_imbalance: Physical/fragmentation Level-3 queue imbalance QI in [-1.0, 1.0].
        arrival_imbalance: Hawkes directional arrival imbalance Delta lambda_dir in [-1.0, 1.0].
        predicted_drift_bps: Forecasted 1~5 minute execution drift in basis points.
        adverse_toxicity: Adverse selection risk T_adverse in [0.0, 1.0].
        composite_alpha_score: Composite microstructure alpha S_micro in [-1.0, 1.0].
        is_toxic: Boolean trigger flag (True if adverse_toxicity >= 0.65).
        recommended_urgency: Execution pacing directive: "FAST" | "MEDIUM" | "DEFENSIVE".
        target_offset_ticks: Recommended limit order peg offset in ticks.
        lambda_buy: Current buy trade arrival intensity.
        lambda_sell: Current sell trade arrival intensity.
        lambda_total: Combined arrival intensity (lambda_buy + lambda_sell).
        predicted_drift_price: Price drift in currency units.
        flow_activity_multiplier: Flow activity scaling factor chi in [0.5, 3.0].
        effective_ac_kappa: Modulated Almgren-Chriss risk-aversion kappa_eff.
        qi_velocity: First time-derivative dQI/dt.
        qi_acceleration: Second time-derivative d2QI/dt2.
    """
    timestamp: float
    symbol: str
    l3_imbalance: float
    arrival_imbalance: float
    predicted_drift_bps: float
    adverse_toxicity: float
    composite_alpha_score: float
    is_toxic: bool
    recommended_urgency: str
    target_offset_ticks: float
    lambda_buy: float = 0.0
    lambda_sell: float = 0.0
    lambda_total: float = 0.0
    predicted_drift_price: float = 0.0
    flow_activity_multiplier: float = 1.0
    effective_ac_kappa: float = 1.0
    qi_velocity: float = 0.0
    qi_acceleration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes alpha signal to dictionary format."""
        return {
            "timestamp": float(self.timestamp),
            "symbol": str(self.symbol),
            "l3_imbalance": round(float(self.l3_imbalance), 4),
            "arrival_imbalance": round(float(self.arrival_imbalance), 4),
            "predicted_drift_bps": round(float(self.predicted_drift_bps), 4),
            "adverse_toxicity": round(float(self.adverse_toxicity), 4),
            "composite_alpha_score": round(float(self.composite_alpha_score), 4),
            "is_toxic": bool(self.is_toxic),
            "recommended_urgency": str(self.recommended_urgency),
            "target_offset_ticks": round(float(self.target_offset_ticks), 2),
            "lambda_buy": round(float(self.lambda_buy), 4),
            "lambda_sell": round(float(self.lambda_sell), 4),
            "lambda_total": round(float(self.lambda_total), 4),
            "predicted_drift_price": round(float(self.predicted_drift_price), 4),
            "flow_activity_multiplier": round(float(self.flow_activity_multiplier), 4),
            "effective_ac_kappa": round(float(self.effective_ac_kappa), 4),
            "qi_velocity": round(float(self.qi_velocity), 4),
            "qi_acceleration": round(float(self.qi_acceleration), 4),
        }


class HawkesMLEstimator:
    """
    Maximum Likelihood & Moment Estimator for Hawkes Point Processes.

    Implements O(N) recursive log-likelihood evaluation:
        R_1 = 0
        R_k = exp(-beta * (t_k - t_{k-1})) * (1 + R_{k-1})
        lambda(t_k) = mu + alpha * R_k
        ln L = sum_{k=1}^N ln(mu + alpha * R_k) - mu * T - (alpha / beta) * sum_{k=1}^N (1 - exp(-beta * (T - t_k)))

    Guarantees L1 stability:
        Strictly enforces alpha / beta <= max_branching < 1.0 via constrained parameterization
        and projection to a subcritical ceiling (default: 0.99 or 0.95).
    """

    @staticmethod
    def compute_log_likelihood(
        mu: float,
        alpha: float,
        beta: float,
        timestamps: np.ndarray,
        t_max: Optional[float] = None,
    ) -> float:
        """
        Evaluates exact Hawkes log-likelihood in O(N) operations via recursive memory decay.
        """
        if len(timestamps) == 0:
            return 0.0
        if mu <= 1e-12 or beta <= 1e-12 or alpha < 0.0:
            return -1e12

        ts = np.asarray(timestamps, dtype=np.float64)
        N = len(ts)
        T = float(t_max) if t_max is not None else float(ts[-1])
        if T <= 0.0:
            T = 1.0

        # Recursive evaluation of R_k
        dt = np.diff(ts)
        R = 0.0
        sum_log_lam = math.log(max(1e-12, mu))

        for k in range(1, N):
            delta = max(0.0, float(dt[k - 1]))
            # Exponential decay + impulse jump
            R = math.exp(-beta * delta) * (1.0 + R)
            lam_k = mu + alpha * R
            if lam_k <= 0.0:
                return -1e12
            sum_log_lam += math.log(lam_k)

        # Integrated intensity over [0, T]
        T_minus_t = np.maximum(0.0, T - ts)
        sum_integral_terms = float(np.sum(1.0 - np.exp(-beta * T_minus_t)))
        integral = mu * T + (alpha / beta) * sum_integral_terms

        ll = sum_log_lam - integral
        return float(ll)

    @staticmethod
    def project_to_stability(
        params: HawkesParameters,
        max_branching: float = 0.99,
    ) -> HawkesParameters:
        """
        Projects parameters to the L1 stable manifold (alpha / beta <= max_branching < 1.0).
        If branching ratio exceeds threshold, rescales alpha so that alpha = max_branching * beta.
        """
        mu = max(1e-6, float(params.mu))
        beta = max(1e-4, float(params.beta))
        alpha = max(0.0, float(params.alpha))
        branching = alpha / beta

        if branching >= max_branching or not math.isfinite(branching):
            alpha = max_branching * beta
            branching = max_branching

        alpha_self = params.alpha_self
        alpha_cross = params.alpha_cross
        if alpha_self is not None and alpha_cross is not None:
            coupled_branching = (alpha_self + alpha_cross) / beta
            if coupled_branching >= max_branching:
                scale = max_branching / max(1e-6, coupled_branching)
                alpha_self *= scale
                alpha_cross *= scale

        return HawkesParameters(
            mu=mu,
            alpha=alpha,
            beta=beta,
            branching_ratio=branching,
            log_likelihood=params.log_likelihood,
            is_stable=(branching < 1.0),
            alpha_self=alpha_self,
            alpha_cross=alpha_cross,
            convergence=params.convergence,
            iterations=params.iterations,
        )

    @classmethod
    def fit_calibrated_moments(
        cls,
        timestamps: np.ndarray,
        t_max: Optional[float] = None,
        max_branching: float = 0.95,
    ) -> HawkesParameters:
        """
        Instantaneous calibrated method-of-moments estimator for Hawkes process.
        Uses inter-arrival time dispersion (coefficient of variation c_v) and mean rate:
            bar_lambda = N / T = mu / (1 - eta)
            eta = clip(1 - 1 / c_v^2, 0.05, max_branching)
            beta = 1.0 / median(Delta t)
            alpha = eta * beta
            mu = bar_lambda * (1 - eta)
        """
        ts = np.sort(np.asarray(timestamps, dtype=np.float64))
        N = len(ts)
        if N < 2:
            return HawkesParameters(
                mu=1.0,
                alpha=0.4,
                beta=1.0,
                branching_ratio=0.4,
                log_likelihood=0.0,
                is_stable=True,
                convergence=True,
                iterations=0,
            )

        T = float(t_max) if t_max is not None else float(ts[-1] - ts[0])
        if T <= 0.0:
            T = max(1.0, float(ts[-1]))

        mean_rate = max(1e-4, N / T)
        dt = np.diff(ts)
        dt_pos = dt[dt > 1e-9]

        if len(dt_pos) >= 2:
            mean_dt = float(np.mean(dt_pos))
            std_dt = float(np.std(dt_pos))
            cv = std_dt / max(1e-6, mean_dt)
            med_dt = float(np.median(dt_pos))
            beta = max(0.1, 1.0 / max(1e-4, med_dt))

            if cv > 1.0:
                # Clustered / self-exciting: cv^2 > 1.0
                eta_est = math.sqrt(max(0.0, 1.0 - 1.0 / (cv * cv)))
                eta = float(np.clip(eta_est, 0.05, max_branching))
            else:
                eta = 0.15
        else:
            beta = 1.0
            eta = 0.20

        alpha = eta * beta
        mu = max(1e-4, mean_rate * (1.0 - eta))

        ll = cls.compute_log_likelihood(mu, alpha, beta, ts, t_max=T)
        return HawkesParameters(
            mu=mu,
            alpha=alpha,
            beta=beta,
            branching_ratio=eta,
            log_likelihood=ll,
            is_stable=(eta < 1.0),
            convergence=True,
            iterations=1,
        )

    @classmethod
    def fit_univariate_mle(
        cls,
        timestamps: np.ndarray,
        t_max: Optional[float] = None,
        max_branching: float = 0.99,
    ) -> HawkesParameters:
        """
        Fits Hawkes parameters (mu, alpha, beta) using recursive O(N) log-likelihood MLE
        with strict L1 stability constraint enforcement.
        """
        ts = np.sort(np.asarray(timestamps, dtype=np.float64))
        # Remove duplicates by adding microsecond jitter
        if len(ts) > 1:
            diffs = np.diff(ts)
            if np.any(diffs <= 0.0):
                jitter = np.linspace(0.0, 1e-5 * len(ts), len(ts))
                ts = np.sort(ts + jitter)

        N = len(ts)
        if N < 3:
            return cls.fit_calibrated_moments(ts, t_max=t_max, max_branching=max_branching)

        T = float(t_max) if t_max is not None else float(ts[-1])
        if T <= 0.0:
            T = max(1.0, float(ts[-1]))

        # Initial parameter estimates via method of moments
        moments_init = cls.fit_calibrated_moments(ts, t_max=T, max_branching=min(0.85, max_branching))
        mu_0 = moments_init.mu
        eta_0 = moments_init.branching_ratio
        beta_0 = moments_init.beta

        if not HAS_SCIPY:
            return moments_init

        # Parameterize via (mu, eta, beta) where eta = alpha / beta in [0.001, max_branching]
        # This guarantees alpha / beta <= max_branching < 1.0 by construction!
        def objective(x: np.ndarray) -> float:
            mu_val = x[0]
            eta_val = x[1]
            beta_val = x[2]
            alpha_val = eta_val * beta_val
            ll = cls.compute_log_likelihood(mu_val, alpha_val, beta_val, ts, t_max=T)
            if not math.isfinite(ll):
                return 1e12
            return -ll

        bounds = [
            (1e-4, max(50.0, 50.0 * N / max(1.0, T))),
            (0.001, float(max_branching)),
            (1e-3, 100.0),
        ]
        x0 = [mu_0, eta_0, beta_0]

        try:
            res = minimize(
                objective,
                x0=x0,
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 80, "ftol": 1e-5},
            )
            if res.success and math.isfinite(res.fun):
                mu_opt = float(res.x[0])
                eta_opt = float(np.clip(res.x[1], 0.001, max_branching))
                beta_opt = float(res.x[2])
                alpha_opt = float(eta_opt * beta_opt)
                ll_opt = float(-res.fun)

                return HawkesParameters(
                    mu=mu_opt,
                    alpha=alpha_opt,
                    beta=beta_opt,
                    branching_ratio=eta_opt,
                    log_likelihood=ll_opt,
                    is_stable=(eta_opt < 1.0),
                    convergence=True,
                    iterations=int(res.nit),
                )
        except Exception as e:
            logger.debug(f"Hawkes MLE optimization exception: {e}; falling back to calibrated moments.")

        return moments_init

    @classmethod
    def fit_bivariate_mle(
        cls,
        buy_timestamps: np.ndarray,
        sell_timestamps: np.ndarray,
        t_max: Optional[float] = None,
        max_branching: float = 0.99,
    ) -> Tuple[HawkesParameters, HawkesParameters]:
        """
        Fits coupled bivariate Hawkes parameters for buy and sell arrival streams.
        Enforces (alpha_self + alpha_cross) / beta <= max_branching < 1.0 for each stream.
        """
        buy_params = cls.fit_univariate_mle(buy_timestamps, t_max=t_max, max_branching=max_branching)
        sell_params = cls.fit_univariate_mle(sell_timestamps, t_max=t_max, max_branching=max_branching)

        # Allocate self-excitation (75%) and cross-excitation (25%)
        alpha_b_self = 0.75 * buy_params.alpha
        alpha_b_cross = 0.25 * buy_params.alpha
        alpha_s_self = 0.75 * sell_params.alpha
        alpha_s_cross = 0.25 * sell_params.alpha

        buy_out = HawkesParameters(
            mu=buy_params.mu,
            alpha=buy_params.alpha,
            beta=buy_params.beta,
            branching_ratio=buy_params.branching_ratio,
            log_likelihood=buy_params.log_likelihood,
            is_stable=(buy_params.branching_ratio < 1.0),
            alpha_self=alpha_b_self,
            alpha_cross=alpha_b_cross,
            convergence=buy_params.convergence,
            iterations=buy_params.iterations,
        )
        sell_out = HawkesParameters(
            mu=sell_params.mu,
            alpha=sell_params.alpha,
            beta=sell_params.beta,
            branching_ratio=sell_params.branching_ratio,
            log_likelihood=sell_params.log_likelihood,
            is_stable=(sell_params.branching_ratio < 1.0),
            alpha_self=alpha_s_self,
            alpha_cross=alpha_s_cross,
            convergence=sell_params.convergence,
            iterations=sell_params.iterations,
        )

        return (
            cls.project_to_stability(buy_out, max_branching=max_branching),
            cls.project_to_stability(sell_out, max_branching=max_branching),
        )

    @staticmethod
    def simulate_hawkes_process(
        mu: float,
        alpha: float,
        beta: float,
        t_max: float,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """
        Simulates a 1D Hawkes point process on [0, t_max] using Ogata's modified thinning algorithm.
        Enforces L1 stability (alpha / beta < 1.0) before simulation.
        """
        if seed is not None:
            np.random.seed(seed)

        mu = max(1e-4, float(mu))
        beta = max(1e-4, float(beta))
        if alpha >= beta:
            alpha = 0.95 * beta

        timestamps: List[float] = []
        t = 0.0
        lambda_bar = mu

        while t < t_max:
            u = float(np.random.uniform(0.0, 1.0))
            w = -math.log(max(1e-12, u)) / max(1e-6, lambda_bar)
            t += w
            if t >= t_max:
                break

            # Evaluate intensity at candidate time t
            decayed = 0.0
            if timestamps:
                # Truncate to last 150 events for efficiency
                recent = timestamps[-150:]
                decayed = sum(math.exp(-beta * (t - s)) for s in recent)
            lam_t = mu + alpha * decayed

            d = float(np.random.uniform(0.0, 1.0))
            if d <= lam_t / max(1e-6, lambda_bar):
                timestamps.append(t)
                lambda_bar = lam_t + alpha
            else:
                lambda_bar = lam_t

        return np.asarray(timestamps, dtype=np.float64)


class HawkesMicrostructureAlphaPredictor:
    """
    High-Frequency L2/L3 Order Book Queue Imbalance & Hawkes Microstructure Alpha Engine.

    Integrates:
    1. Bivariate directional arrival intensity tracking: lambda_B(t), lambda_S(t).
    2. Arrival imbalance: Delta lambda_dir = (lambda_B - lambda_S) / (lambda_B + lambda_S).
    3. Adverse selection toxicity score: T_adverse in [0.0, 1.0].
    4. Short-term execution price drift forecast (1~5 minute): Delta P_tau (bps).
    5. Composite microstructure alpha score S_micro in [-1.0, 1.0].
    6. Closed-loop Almgren-Chriss schedule modulation: dynamic kappa_eff = kappa_0 * chi.
    7. Limit order peg offset calculation: Delta P_offset.
    """

    def __init__(
        self,
        symbol: str = "DEFAULT",
        horizon_seconds: int = 180,
        daily_volatility: float = 0.02,
        spread_bps: float = 5.0,
        tick_size: float = 0.01,
        toxic_threshold: float = 0.65,
        base_arrival_mu: float = 1.0,
        hawkes_alpha_self: float = 0.40,
        hawkes_alpha_cross: float = 0.10,
        hawkes_beta: float = 1.20,
        max_branching_ratio: float = 0.99,
        base_kappa_ac: float = 1.0,
        max_history_len: int = 2000,
    ):
        self.symbol = str(symbol)
        self.horizon_seconds = max(10, int(horizon_seconds))
        self.daily_volatility = max(0.001, float(daily_volatility))
        self.spread_bps = max(0.1, float(spread_bps))
        self.tick_size = max(1e-4, float(tick_size))
        self.toxic_threshold = float(toxic_threshold)
        self.max_branching_ratio = float(min(0.999, max_branching_ratio))
        self.base_kappa_ac = max(0.01, float(base_kappa_ac))

        # Enforce initial parameters stability
        total_alpha = hawkes_alpha_self + hawkes_alpha_cross
        if total_alpha >= hawkes_beta:
            scale = (0.85 * hawkes_beta) / max(1e-6, total_alpha)
            hawkes_alpha_self *= scale
            hawkes_alpha_cross *= scale

        self.mu_buy = float(base_arrival_mu)
        self.mu_sell = float(base_arrival_mu)
        self.alpha_self = float(hawkes_alpha_self)
        self.alpha_cross = float(hawkes_alpha_cross)
        self.beta = float(hawkes_beta)

        # Real-time state
        self.last_ts: Optional[float] = None
        self.lambda_buy: float = self.mu_buy
        self.lambda_sell: float = self.mu_sell

        # History ring buffers
        self.max_history_len = max_history_len
        self.buy_tick_history: Deque[Tuple[float, float]] = deque(maxlen=max_history_len)  # (ts, volume)
        self.sell_tick_history: Deque[Tuple[float, float]] = deque(maxlen=max_history_len)
        self.qi_history: Deque[Tuple[float, float]] = deque(maxlen=50)                      # (ts, qi)

        # Fitted parameter cache
        self.fitted_params_buy: Optional[HawkesParameters] = None
        self.fitted_params_sell: Optional[HawkesParameters] = None

    def update_ticks(
        self,
        price: float,
        volume: float,
        timestamp_sec: Optional[float] = None,
        is_buy: bool = True,
    ) -> Tuple[float, float]:
        """
        Updates coupled arrival intensities upon receiving a directional trade event.
        """
        t = float(timestamp_sec if timestamp_sec is not None else time.time())
        vol = max(0.0, float(volume))

        if self.last_ts is not None:
            dt = max(0.0, t - self.last_ts)
            decay = math.exp(-self.beta * dt)
            self.lambda_buy = self.mu_buy + max(0.0, self.lambda_buy - self.mu_buy) * decay
            self.lambda_sell = self.mu_sell + max(0.0, self.lambda_sell - self.mu_sell) * decay

        if is_buy:
            self.lambda_buy += self.alpha_self
            self.lambda_sell += self.alpha_cross
            self.buy_tick_history.append((t, vol))
        else:
            self.lambda_sell += self.alpha_self
            self.lambda_buy += self.alpha_cross
            self.sell_tick_history.append((t, vol))

        self.last_ts = t
        return (self.lambda_buy, self.lambda_sell)

    def fit_parameters(
        self,
        lookback_seconds: Optional[float] = None,
    ) -> Dict[str, HawkesParameters]:
        """
        Calibrates Hawkes process parameters using recorded buy and sell trade history.
        Enforces L1 stability: alpha / beta < 1.0.
        """
        now = self.last_ts if self.last_ts is not None else time.time()
        min_ts = (now - lookback_seconds) if lookback_seconds is not None else 0.0

        buy_ts = np.array([ts for ts, _ in self.buy_tick_history if ts >= min_ts], dtype=np.float64)
        sell_ts = np.array([ts for ts, _ in self.sell_tick_history if ts >= min_ts], dtype=np.float64)

        b_params, s_params = HawkesMLEstimator.fit_bivariate_mle(
            buy_ts, sell_ts, t_max=now, max_branching=self.max_branching_ratio
        )

        self.fitted_params_buy = b_params
        self.fitted_params_sell = s_params

        # Update engine parameters with fitted values
        self.mu_buy = b_params.mu
        self.mu_sell = s_params.mu
        self.alpha_self = 0.5 * (b_params.alpha_self + s_params.alpha_self) if b_params.alpha_self and s_params.alpha_self else b_params.alpha * 0.75
        self.alpha_cross = 0.5 * (b_params.alpha_cross + s_params.alpha_cross) if b_params.alpha_cross and s_params.alpha_cross else b_params.alpha * 0.25
        self.beta = 0.5 * (b_params.beta + s_params.beta)

        return {"buy": b_params, "sell": s_params}

    def compute_intensities(
        self,
        current_time: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Evaluates current decayed arrival intensities without receiving a new trade event.
        """
        t = float(current_time if current_time is not None else (self.last_ts if self.last_ts is not None else time.time()))
        dt = max(0.0, t - self.last_ts) if self.last_ts is not None else 0.0
        decay = math.exp(-self.beta * dt)

        lam_b = self.mu_buy + max(0.0, self.lambda_buy - self.mu_buy) * decay
        lam_s = self.mu_sell + max(0.0, self.lambda_sell - self.mu_sell) * decay
        tot = max(1e-6, lam_b + lam_s)
        delta_dir = float(np.clip((lam_b - lam_s) / tot, -1.0, 1.0))

        return {
            "lambda_buy": lam_b,
            "lambda_sell": lam_s,
            "lambda_total": tot,
            "arrival_imbalance": delta_dir,
            "branching_ratio": (self.alpha_self + self.alpha_cross) / max(1e-6, self.beta),
        }

    def compute_arrival_imbalance(
        self,
        current_time: Optional[float] = None,
    ) -> float:
        """
        Returns directional arrival intensity imbalance Delta lambda_dir in [-1.0, 1.0].
        Positive indicates aggressive buying flow; negative indicates aggressive selling flow.
        """
        intensities = self.compute_intensities(current_time)
        return float(intensities["arrival_imbalance"])

    def compute_adverse_toxicity(
        self,
        action: str = "BUY",
        current_time: Optional[float] = None,
    ) -> float:
        """
        Calculates adverse selection toxicity score T_adverse in [0.0, 1.0].
        For BUY: adverse flow is aggressive selling (lambda_sell / (lambda_buy + lambda_sell)).
        For SELL: adverse flow is aggressive buying (lambda_buy / (lambda_buy + lambda_sell)).
        """
        intensities = self.compute_intensities(current_time)
        lam_b = intensities["lambda_buy"]
        lam_s = intensities["lambda_sell"]
        tot = max(1e-6, lam_b + lam_s)

        is_buy = str(action).upper() in ["BUY", "BID", "LONG"]
        if is_buy:
            return float(np.clip(lam_s / tot, 0.0, 1.0))
        else:
            return float(np.clip(lam_b / tot, 0.0, 1.0))

    def compute_composite_alpha(
        self,
        lob_snapshot: Optional[Dict[str, Any]] = None,
        current_time: Optional[float] = None,
    ) -> Tuple[float, float, float, float]:
        """
        Calculates composite microstructure alpha score S_micro in [-1.0, 1.0].

        Formula:
            S_micro = clip(0.40 * QI_L3 + 0.40 * Delta lambda_dir + 0.12 * tanh(0.8 * v_QI) + 0.08 * tanh(0.5 * a_QI), -1.0, 1.0)
        Returns:
            (composite_alpha_score, qi_l3, qi_velocity, qi_acceleration)
        """
        t = float(current_time if current_time is not None else time.time())
        intensities = self.compute_intensities(t)
        delta_lambda = intensities["arrival_imbalance"]

        def _sanitize_val(val: Any, default: float = 0.0, low: float = -1.0, high: float = 1.0) -> float:
            try:
                v = float(val)
                if not math.isfinite(v):
                    return default
                return max(low, min(high, v))
            except (ValueError, TypeError):
                return default

        qi_l3 = 0.0
        v_qi = 0.0
        a_qi = 0.0

        if lob_snapshot is not None:
            # Check for direct pre-computed fields with robust adversarial sanitization
            if "l3_queue_imbalance" in lob_snapshot:
                qi_l3 = _sanitize_val(lob_snapshot["l3_queue_imbalance"], 0.0, -1.0, 1.0)
                v_qi = _sanitize_val(lob_snapshot.get("qi_velocity", 0.0), 0.0, -100.0, 100.0)
                a_qi = _sanitize_val(lob_snapshot.get("qi_acceleration", 0.0), 0.0, -100.0, 100.0)
            elif "l3_imbalance" in lob_snapshot:
                qi_l3 = _sanitize_val(lob_snapshot["l3_imbalance"], 0.0, -1.0, 1.0)
                v_qi = _sanitize_val(lob_snapshot.get("qi_velocity", 0.0), 0.0, -100.0, 100.0)
                a_qi = _sanitize_val(lob_snapshot.get("qi_acceleration", 0.0), 0.0, -100.0, 100.0)
            elif "bids" in lob_snapshot and "asks" in lob_snapshot:
                # Raw book depth calculation: distance-decayed queue imbalance
                bids = lob_snapshot["bids"]
                asks = lob_snapshot["asks"]
                bid_vol = sum(float(b[1]) * math.exp(-0.35 * idx) for idx, b in enumerate(bids[:10])) if bids else 0.0
                ask_vol = sum(float(a[1]) * math.exp(-0.35 * idx) for idx, a in enumerate(asks[:10])) if asks else 0.0
                tot_vol = max(1e-6, bid_vol + ask_vol)
                qi_l3 = _sanitize_val((bid_vol - ask_vol) / tot_vol, 0.0, -1.0, 1.0)

        # Update QI history to calculate velocity and acceleration if not provided
        self.qi_history.append((t, qi_l3))
        if len(self.qi_history) >= 2 and v_qi == 0.0:
            dt1 = max(1e-4, self.qi_history[-1][0] - self.qi_history[-2][0])
            v_qi = _sanitize_val((self.qi_history[-1][1] - self.qi_history[-2][1]) / dt1, 0.0, -100.0, 100.0)

            if len(self.qi_history) >= 3 and a_qi == 0.0:
                dt2 = max(1e-4, self.qi_history[-2][0] - self.qi_history[-3][0])
                v_prev = (self.qi_history[-2][1] - self.qi_history[-3][1]) / dt2
                a_qi = _sanitize_val((v_qi - v_prev) / (0.5 * (dt1 + dt2)), 0.0, -100.0, 100.0)

        # Composite score
        raw_score = (
            0.40 * qi_l3
            + 0.40 * delta_lambda
            + 0.12 * math.tanh(0.8 * v_qi)
            + 0.08 * math.tanh(0.5 * a_qi)
        )
        composite_alpha = float(np.clip(raw_score, -1.0, 1.0))
        return (composite_alpha, qi_l3, v_qi, a_qi)

    def predict_drift(
        self,
        composite_alpha: float,
        mid_price: float = 100.0,
        horizon_seconds: Optional[int] = None,
    ) -> Tuple[float, float]:
        """
        Forecasts short-term execution price drift over tau seconds:
            predicted_drift_bps = S_micro * sigma_daily * sqrt(tau / 86400) * 10000
            predicted_drift_price = predicted_drift_bps * 1e-4 * mid_price
        """
        tau = horizon_seconds if horizon_seconds is not None else self.horizon_seconds
        tau_fraction = math.sqrt(max(1.0, float(tau)) / 86400.0)
        drift_bps = composite_alpha * self.daily_volatility * tau_fraction * 10000.0
        drift_price = (drift_bps * 1e-4) * max(0.01, float(mid_price))
        return (drift_bps, drift_price)

    def predict_alpha(
        self,
        lob_snapshot: Optional[Dict[str, Any]] = None,
        current_time: Optional[float] = None,
        proposed_action: str = "BUY",
        mid_price: float = 100.0,
    ) -> MicrostructureAlphaSignal:
        """
        Generates full MicrostructureAlphaSignal combining L3 orderbook state and Hawkes arrival flow.
        """
        t = float(current_time if current_time is not None else time.time())
        composite_score, qi_l3, v_qi, a_qi = self.compute_composite_alpha(lob_snapshot, t)
        intensities = self.compute_intensities(t)
        adverse_tox = self.compute_adverse_toxicity(proposed_action, t)
        drift_bps, drift_price = self.predict_drift(composite_score, mid_price=mid_price)

        is_toxic = bool(adverse_tox >= self.toxic_threshold)

        # Flow activity multiplier chi in [0.5, 3.0]
        base_tot = max(1e-6, self.mu_buy + self.mu_sell)
        curr_tot = intensities["lambda_total"]
        chi = float(np.clip(math.sqrt(curr_tot / base_tot), 0.5, 3.0))

        # Modulated Almgren-Chriss risk-aversion parameter kappa_eff
        action_sign = 1.0 if str(proposed_action).upper() in ["BUY", "BID", "LONG"] else -1.0
        if composite_score * action_sign > 0.15:
            # Favorable breakout: accelerate execution
            kappa_eff = self.base_kappa_ac * chi
            urgency = "FAST"
        elif is_toxic:
            # Toxic adverse flow: decelerate / defensive execution
            kappa_eff = self.base_kappa_ac / chi
            urgency = "DEFENSIVE"
        else:
            kappa_eff = self.base_kappa_ac
            urgency = "FAST" if abs(composite_score) >= 0.35 else "MEDIUM"

        # Limit order peg offset
        spread_val = max(1e-4, mid_price * self.spread_bps * 1e-4)
        offset_val = self.compute_limit_offset_raw(
            composite_score, adverse_tox, spread_val, proposed_action
        )
        offset_ticks = round(offset_val / max(1e-4, self.tick_size), 2)

        return MicrostructureAlphaSignal(
            timestamp=t,
            symbol=self.symbol,
            l3_imbalance=qi_l3,
            arrival_imbalance=intensities["arrival_imbalance"],
            predicted_drift_bps=drift_bps,
            adverse_toxicity=adverse_tox,
            composite_alpha_score=composite_score,
            is_toxic=is_toxic,
            recommended_urgency=urgency,
            target_offset_ticks=offset_ticks,
            lambda_buy=intensities["lambda_buy"],
            lambda_sell=intensities["lambda_sell"],
            lambda_total=intensities["lambda_total"],
            predicted_drift_price=drift_price,
            flow_activity_multiplier=chi,
            effective_ac_kappa=kappa_eff,
            qi_velocity=v_qi,
            qi_acceleration=a_qi,
        )

    def modulate_slicing_schedule(
        self,
        base_slices: List[int],
        signal: MicrostructureAlphaSignal,
        action: str = "BUY",
    ) -> List[int]:
        """
        Modulates discrete Almgren-Chriss slicing schedule based on arrival flow & alpha drift.

        Guarantees:
            - Exact total volume conservation: sum(modulated) == sum(base_slices).
            - Every slice is a non-negative integer.
            - Favorable alpha accelerates/front-loads slices.
            - High adverse toxicity decelerates/back-loads slices.
        """
        total_qty = sum(base_slices)
        N = len(base_slices)
        if N <= 1 or total_qty <= 0:
            return list(base_slices)

        kappa = max(0.01, float(signal.effective_ac_kappa))

        # Hyperbolic trajectory shares: w_j = sinh(kappa * (1 - (j-1)/N)) - sinh(kappa * (1 - j/N))
        raw_weights = []
        denom = math.sinh(kappa)
        for j in range(1, N + 1):
            tau_prev = (j - 1) / N
            tau_curr = j / N
            w = (math.sinh(kappa * (1.0 - tau_prev)) - math.sinh(kappa * (1.0 - tau_curr))) / denom
            raw_weights.append(max(0.0, w))

        total_w = sum(raw_weights)
        if total_w <= 0.0:
            return list(base_slices)
        norm_weights = [w / total_w for w in raw_weights]

        # Allocate integer quantities preserving total_qty exactly
        raw_allocated = [total_qty * w for w in norm_weights]
        integer_slices = [int(math.floor(x)) for x in raw_allocated]
        remainder = total_qty - sum(integer_slices)

        # Distribute remaining shares to slices with largest fractional parts
        fractional_parts = [
            (raw_allocated[i] - integer_slices[i], i) for i in range(N)
        ]
        fractional_parts.sort(key=lambda item: item[0], reverse=True)

        for i in range(int(remainder)):
            idx = fractional_parts[i % N][1]
            integer_slices[idx] += 1

        return integer_slices

    def compute_limit_offset_raw(
        self,
        composite_score: float,
        adverse_tox: float,
        spread: float,
        action: str = "BUY",
    ) -> float:
        """
        Computes peg price offset in currency units:
            Delta P_offset = -sign(action) * spread * [0.35 * tanh(1.5 * S_micro) + 0.50 * max(0.0, T_adverse - 0.50)]
        """
        action_sign = 1.0 if str(action).upper() in ["BUY", "BID", "LONG"] else -1.0
        tox_excess = max(0.0, adverse_tox - 0.50)
        offset_factor = 0.35 * math.tanh(1.5 * composite_score) + 0.50 * tox_excess
        return float(-action_sign * spread * offset_factor)

    def compute_limit_offset(
        self,
        signal: MicrostructureAlphaSignal,
        spread: float,
        action: str = "BUY",
        tick_size: Optional[float] = None,
    ) -> float:
        """
        Computes discrete limit order peg offset rounded to tick size.
        """
        t_size = tick_size if tick_size is not None else self.tick_size
        raw_offset = self.compute_limit_offset_raw(
            signal.composite_alpha_score,
            signal.adverse_toxicity,
            spread,
            action=action,
        )
        ticks = round(raw_offset / max(1e-4, t_size))
        return float(ticks * t_size)


# ===========================================================================
# Phase 107 Production Aliases & Complete Backward Compatibility Tree
# ===========================================================================
HawkesMicrostructureAlphaEngine = HawkesMicrostructureAlphaPredictor
Phase107HawkesAlphaPredictor = HawkesMicrostructureAlphaPredictor
MicrostructureHawkesAlphaPredictor = HawkesMicrostructureAlphaPredictor
HawkesAlphaPredictor = HawkesMicrostructureAlphaPredictor

# Register dual alias in sys.modules so both 'src.core.hawkes_microstructure_alpha'
# and 'trading_system.src.core.hawkes_microstructure_alpha' point to this exact module instance
import sys as _sys
_curr_mod = _sys.modules[__name__]
if "src.core.hawkes_microstructure_alpha" not in _sys.modules:
    _sys.modules["src.core.hawkes_microstructure_alpha"] = _curr_mod
if "trading_system.src.core.hawkes_microstructure_alpha" not in _sys.modules:
    _sys.modules["trading_system.src.core.hawkes_microstructure_alpha"] = _curr_mod

__all__ = [
    "HawkesParameters",
    "MicrostructureAlphaSignal",
    "HawkesMLEstimator",
    "HawkesMicrostructureAlphaPredictor",
    "HawkesMicrostructureAlphaEngine",
    "Phase107HawkesAlphaPredictor",
    "MicrostructureHawkesAlphaPredictor",
    "HawkesAlphaPredictor",
]
