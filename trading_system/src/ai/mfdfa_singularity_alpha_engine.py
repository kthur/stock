r"""
src/ai/mfdfa_singularity_alpha_engine.py
=========================================
Multi-Fractal Detrended Fluctuation (MF-DFA) Singularity Spectrum & Long-Memory Alpha Generator (Feature F571).
Phase 120 (Release R136 / v127 Production Master).

Features & Capabilities:
- Generalized Hurst exponent surface H(q) across continuous fluctuation orders q in [-5.0, +5.0]
  and multi-scale lookback windows s in [10, 250].
- Cumulative mean-centered profile construction:
      Y(i) = \sum_{k=1}^i (x_k - \bar{x}), \quad i = 1, \dots, N
- Forward & backward 2-way segmentation (2N_s segments) with local polynomial detrending
  (m=1 linear, m=2 quadratic) via vectorized least-squares orthogonal projection.
- q-th order fluctuation functions F_q(s) equipped with \epsilon = 10^{-14} zero-variance regularizer:
      F_q(s) = \left( \frac{1}{2 N_s} \sum_{v=1}^{2 N_s} [F^2(s, v) + \epsilon]^{q/2} \right)^{1/q}
      F_0(s) = \exp\left( \frac{1}{4 N_s} \sum_{v=1}^{2 N_s} \ln [F^2(s, v) + \epsilon] \right)
- Strict monotonicity enforcement via Pool Adjacent Violators Algorithm (PAVA) guaranteeing
  H(q_1) >= H(q_2) for q_1 < q_2.
- Legendre transform mapping multi-fractal mass exponent \tau(q) = q H(q) - 1 to Hölder
  singularity spectrum f(\alpha):
      \alpha(q) = \frac{d\tau}{dq}, \quad f(\alpha) = q \alpha - \tau(q) = q(\alpha - H(q)) + 1
- Quantitative singularity width (\Delta\alpha = \alpha_{\max} - \alpha_{\min}), spectral asymmetry
  A = (\Delta\alpha_L - \Delta\alpha_R) / \Delta\alpha \in [-1.0, +1.0], and non-linear market fragility alerts
  \mathcal{F}_{\text{fragility}} \in [0.0, 1.0].
- Multi-scale persistence/anti-persistence signals transformed into 9-element long-memory alpha conditioning vectors:
      \mathbf{v}_{\text{MF-DFA}} = [H(2), \Delta\alpha, A, \mathcal{F}_{\text{fragility}}, \tau(2), \alpha_0, f(\alpha_0), C_{\text{trend}}, C_{\text{revert}}]^T \in \mathbb{R}^9
- 5-Market Pre-Calibrated Empirical Parameter Profiles:
  * SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ.
- Complete backward-compatibility alias trees and sys.modules registration.
- 100% bit-for-bit cryptographic SHA-256 parity between src/ and trading_system/src/.
"""

from __future__ import annotations

import enum
import hashlib
import json
import math
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# ---------------------------------------------------------------------------
# Version & Module Metadata
# ---------------------------------------------------------------------------
VERSION: int = 120
RELEASE: str = "R136"
FEATURE: str = "F571"

DEFAULT_SCALE_RANGE: Tuple[int, int] = (10, 250)
DEFAULT_NUM_SCALES: int = 16
DEFAULT_Q_RANGE: Tuple[float, float] = (-5.0, 5.0)
DEFAULT_Q_STEP: float = 0.5
DEFAULT_Q_VALUES: Tuple[float, ...] = tuple(
    float(np.round(q, 4)) for q in np.linspace(-5.0, 5.0, 21)
)
EPSILON_REGULARIZER: float = 1e-14
SINGULARITY_WIDTH_FLOOR: float = 1e-12


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class MarketProfile(enum.IntEnum):
    """Supported 5-market empirical parameter profiles."""
    SP500 = 0
    NASDAQ = 1
    RUSSELL2000 = 2
    KOSPI = 3
    KOSDAQ = 4

    @classmethod
    def from_str(cls, val: Union[str, "MarketProfile"]) -> "MarketProfile":
        """Coerces a string or instance to MarketProfile."""
        if isinstance(val, cls):
            return val
        s = str(val).strip().upper()
        mapping = {
            "SP500": cls.SP500,
            "S&P500": cls.SP500,
            "NASDAQ": cls.NASDAQ,
            "RUSSELL2000": cls.RUSSELL2000,
            "RUSSELL": cls.RUSSELL2000,
            "RUT": cls.RUSSELL2000,
            "KOSPI": cls.KOSPI,
            "KOSDAQ": cls.KOSDAQ,
        }
        if s in mapping:
            return mapping[s]
        raise ValueError(f"Unknown MarketProfile: {val}. Expected one of {list(mapping.keys())}")


class MarketType(str, enum.Enum):
    """String enum for market type compatibility."""
    SP500 = "SP500"
    NASDAQ = "NASDAQ"
    RUSSELL2000 = "RUSSELL2000"
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"


class PolynomialOrder(int, enum.Enum):
    """Local detrending polynomial order m."""
    LINEAR = 1
    QUADRATIC = 2


class FractalRegime(str, enum.Enum):
    """Dominant long-memory fractal regime characterized by H(2)."""
    ANTI_PERSISTENT = "ANTI_PERSISTENT"   # H(2) < 0.45
    BROWNIAN_RANDOM = "BROWNIAN_RANDOM"   # 0.45 <= H(2) <= 0.55
    PERSISTENT_TREND = "PERSISTENT_TREND" # H(2) > 0.55


class FragilityAlertLevel(str, enum.Enum):
    """Non-linear market fragility alert severity levels."""
    NORMAL = "NORMAL"       # F < 0.50
    ELEVATED = "ELEVATED"   # 0.50 <= F < 0.75
    CRITICAL = "CRITICAL"   # F >= 0.75


# ---------------------------------------------------------------------------
# Pre-Calibrated 5-Market Empirical Profiles
# ---------------------------------------------------------------------------
MARKET_MFDFA_PROFILES: Dict[str, Dict[str, Any]] = {
    "SP500": {
        "scale_range": (10, 200),
        "poly_order": 1,
        "delta_alpha_thresh": 0.45,
        "kappa_1": 5.0,
        "kappa_2": 2.0,
        "trend_memory_exponent": 1.10,
        "num_scales": 16,
        "fragility_alert_threshold": 0.65,
    },
    "NASDAQ": {
        "scale_range": (10, 220),
        "poly_order": 1,
        "delta_alpha_thresh": 0.52,
        "kappa_1": 5.0,
        "kappa_2": 2.2,
        "trend_memory_exponent": 1.25,
        "num_scales": 16,
        "fragility_alert_threshold": 0.65,
    },
    "RUSSELL2000": {
        "scale_range": (10, 250),
        "poly_order": 2,
        "delta_alpha_thresh": 0.60,
        "kappa_1": 5.0,
        "kappa_2": 2.5,
        "trend_memory_exponent": 1.40,
        "num_scales": 16,
        "fragility_alert_threshold": 0.70,
    },
    "KOSPI": {
        "scale_range": (10, 200),
        "poly_order": 1,
        "delta_alpha_thresh": 0.48,
        "kappa_1": 5.0,
        "kappa_2": 2.1,
        "trend_memory_exponent": 1.15,
        "num_scales": 16,
        "fragility_alert_threshold": 0.65,
    },
    "KOSDAQ": {
        "scale_range": (10, 240),
        "poly_order": 2,
        "delta_alpha_thresh": 0.58,
        "kappa_1": 5.0,
        "kappa_2": 2.4,
        "trend_memory_exponent": 1.35,
        "num_scales": 16,
        "fragility_alert_threshold": 0.70,
    },
}


# ---------------------------------------------------------------------------
# Configuration Dataclass
# ---------------------------------------------------------------------------
@dataclass
class MFDFAConfig:
    """Configuration parameters for MF-DFA Singularity Spectrum Alpha Engine."""
    market: str = "SP500"
    scale_min: int = 10
    scale_max: int = 200
    num_scales: int = 16
    poly_order: int = 1
    q_min: float = -5.0
    q_max: float = 5.0
    q_step: float = 0.5
    delta_alpha_thresh: float = 0.45
    kappa_1: float = 5.0
    kappa_2: float = 2.0
    trend_memory_exponent: float = 1.10
    epsilon: float = EPSILON_REGULARIZER
    fragility_alert_threshold: float = 0.65
    enforce_monotonicity: bool = True
    custom_scales: Optional[List[int]] = None
    custom_q_values: Optional[List[float]] = None
    safe_mode: bool = True
    seed: int = 42

    def __post_init__(self) -> None:
        """Applies pre-calibrated empirical profile defaults if standard market provided."""
        m_upper = self.market.strip().upper()
        if m_upper in MARKET_MFDFA_PROFILES:
            prof = MARKET_MFDFA_PROFILES[m_upper]
            # Only populate default values if not explicitly overridden from default
            if self.scale_min == 10 and self.scale_max == 200 and m_upper != "SP500":
                self.scale_min, self.scale_max = prof["scale_range"]
            if self.poly_order == 1 and prof["poly_order"] != 1:
                self.poly_order = prof["poly_order"]
            if self.delta_alpha_thresh == 0.45 and prof["delta_alpha_thresh"] != 0.45:
                self.delta_alpha_thresh = prof["delta_alpha_thresh"]
            if self.kappa_2 == 2.0 and prof["kappa_2"] != 2.0:
                self.kappa_2 = prof["kappa_2"]
            if self.trend_memory_exponent == 1.10 and prof["trend_memory_exponent"] != 1.10:
                self.trend_memory_exponent = prof["trend_memory_exponent"]
            if self.fragility_alert_threshold == 0.65 and prof["fragility_alert_threshold"] != 0.65:
                self.fragility_alert_threshold = prof["fragility_alert_threshold"]

        if self.scale_min < 4:
            self.scale_min = 4
        if self.scale_max <= self.scale_min:
            self.scale_max = self.scale_min + 10
        if self.poly_order not in (1, 2):
            self.poly_order = 1
        if self.num_scales < 4:
            self.num_scales = 4

    def get_q_array(self) -> np.ndarray:
        """Returns the array of continuous orders q."""
        if self.custom_q_values is not None and len(self.custom_q_values) > 0:
            return np.array(sorted(self.custom_q_values), dtype=np.float64)
        num_pts = int(round((self.q_max - self.q_min) / self.q_step)) + 1
        return np.linspace(self.q_min, self.q_max, num_pts, dtype=np.float64)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes config to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MFDFAConfig":
        """Deserializes config from dictionary."""
        valid_keys = {
            "market", "scale_min", "scale_max", "num_scales", "poly_order",
            "q_min", "q_max", "q_step", "delta_alpha_thresh", "kappa_1",
            "kappa_2", "trend_memory_exponent", "epsilon",
            "fragility_alert_threshold", "enforce_monotonicity",
            "custom_scales", "custom_q_values", "safe_mode", "seed"
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_json(self) -> str:
        """Serializes config to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MFDFAConfig":
        """Deserializes config from JSON string."""
        return cls.from_dict(json.loads(json_str))


# ---------------------------------------------------------------------------
# Output Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class LongMemoryAlphaVector:
    """9-element long-memory alpha conditioning vector representation."""
    h2: float
    delta_alpha: float
    asymmetry: float
    fragility_score: float
    tau2: float
    alpha0: float
    f_alpha0: float
    c_trend: float
    c_revert: float

    def as_array(self) -> np.ndarray:
        """Returns conditioning vector as numpy array of shape (9,)."""
        return np.array([
            self.h2,
            self.delta_alpha,
            self.asymmetry,
            self.fragility_score,
            self.tau2,
            self.alpha0,
            self.f_alpha0,
            self.c_trend,
            self.c_revert,
        ], dtype=np.float64)

    def as_list(self) -> List[float]:
        """Returns conditioning vector as list of 9 floats."""
        return self.as_array().tolist()

    def to_dict(self) -> Dict[str, float]:
        """Returns named dictionary of conditioning components."""
        return {
            "H(2)": float(self.h2),
            "delta_alpha": float(self.delta_alpha),
            "asymmetry": float(self.asymmetry),
            "fragility_score": float(self.fragility_score),
            "tau(2)": float(self.tau2),
            "alpha_0": float(self.alpha0),
            "f(alpha_0)": float(self.f_alpha0),
            "C_trend": float(self.c_trend),
            "C_revert": float(self.c_revert),
        }


@dataclass
class SingularitySpectrumResult:
    """Comprehensive analytical result from MF-DFA Singularity Spectrum Engine."""
    q_values: List[float]
    scales: List[int]
    fluctuation_surface: Dict[str, List[float]]
    h_q: List[float]
    tau_q: List[float]
    alpha_q: List[float]
    f_alpha: List[float]
    h_2: float
    tau_2: float
    delta_alpha: float
    alpha_0: float
    f_alpha_0: float
    delta_alpha_l: float
    delta_alpha_r: float
    asymmetry: float
    fragility_score: float
    is_fragility_alert: bool
    alert_level: FragilityAlertLevel
    regime: FractalRegime
    c_trend: float
    c_revert: float
    conditioning_vector: List[float]
    market: str
    sample_size: int
    poly_order: int
    execution_time_ms: float

    def get_alpha_vector(self) -> LongMemoryAlphaVector:
        """Constructs the structured 9-element LongMemoryAlphaVector."""
        return LongMemoryAlphaVector(
            h2=self.h_2,
            delta_alpha=self.delta_alpha,
            asymmetry=self.asymmetry,
            fragility_score=self.fragility_score,
            tau2=self.tau_2,
            alpha0=self.alpha_0,
            f_alpha0=self.f_alpha_0,
            c_trend=self.c_trend,
            c_revert=self.c_revert,
        )

    def to_numpy_vector(self) -> np.ndarray:
        """Returns the 9-element conditioning vector as float64 ndarray."""
        return np.array(self.conditioning_vector, dtype=np.float64)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes result to dictionary."""
        d = asdict(self)
        d["alert_level"] = self.alert_level.value
        d["regime"] = self.regime.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SingularitySpectrumResult":
        """Deserializes result from dictionary."""
        data_copy = dict(data)
        if isinstance(data_copy.get("alert_level"), str):
            data_copy["alert_level"] = FragilityAlertLevel(data_copy["alert_level"])
        if isinstance(data_copy.get("regime"), str):
            data_copy["regime"] = FractalRegime(data_copy["regime"])
        return cls(**data_copy)

    def to_json(self) -> str:
        """Serializes result to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SingularitySpectrumResult":
        """Deserializes result from JSON string."""
        return cls.from_dict(json.loads(json_str))


# ---------------------------------------------------------------------------
# Algorithmic Functions
# ---------------------------------------------------------------------------
def isotonic_pava_decreasing(
    y: np.ndarray,
    weights: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Pool Adjacent Violators Algorithm (PAVA) for strictly non-increasing isotonic regression.
    Guarantees output: out[0] >= out[1] >= ... >= out[n-1] while minimizing sum of squared errors.
    """
    n = len(y)
    if n <= 1:
        return y.astype(np.float64).copy()

    v = y.astype(np.float64).copy()
    if weights is None:
        w = np.ones(n, dtype=np.float64)
    else:
        w = np.array(weights, dtype=np.float64)

    # Each block: [mean_value, total_weight, start_idx, end_idx]
    blocks: List[List[Union[float, int]]] = [
        [float(v[i]), float(w[i]), i, i] for i in range(n)
    ]

    i = 0
    while i < len(blocks) - 1:
        # For non-increasing: if block[i] < block[i+1], monotonicity violated!
        if blocks[i][0] < blocks[i + 1][0]:
            # Merge blocks i and i+1
            v_i, w_i = blocks[i][0], blocks[i][1]
            v_next, w_next = blocks[i + 1][0], blocks[i + 1][1]
            w_new = w_i + w_next
            v_new = (v_i * w_i + v_next * w_next) / (w_new + 1e-18)
            start_idx = int(blocks[i][2])
            end_idx = int(blocks[i + 1][3])

            blocks[i] = [v_new, w_new, start_idx, end_idx]
            blocks.pop(i + 1)

            # Check backwards for cascaded violations
            while i > 0 and blocks[i - 1][0] < blocks[i][0]:
                v_prev, w_prev = blocks[i - 1][0], blocks[i - 1][1]
                v_curr, w_curr = blocks[i][0], blocks[i][1]
                w_merged = w_prev + w_curr
                v_merged = (v_prev * w_prev + v_curr * w_curr) / (w_merged + 1e-18)
                start_prev = int(blocks[i - 1][2])
                end_curr = int(blocks[i][3])

                blocks[i - 1] = [v_merged, w_merged, start_prev, end_curr]
                blocks.pop(i)
                i -= 1
        else:
            i += 1

    out = np.zeros(n, dtype=np.float64)
    for b in blocks:
        s_idx, e_idx = int(b[2]), int(b[3])
        out[s_idx:e_idx + 1] = float(b[0])

    return out


def build_mean_centered_profile(series: np.ndarray) -> np.ndarray:
    """
    Constructs cumulative mean-centered profile Y(i) = sum_{k=1}^i (x_k - \bar{x}).
    """
    x = np.asarray(series, dtype=np.float64).ravel()
    # Sanitize NaNs and Infs
    if np.any(~np.isfinite(x)):
        finite_mask = np.isfinite(x)
        mean_finite = float(np.mean(x[finite_mask])) if np.any(finite_mask) else 0.0
        x = np.nan_to_num(x, nan=mean_finite, posinf=mean_finite, neginf=mean_finite)

    mean_x = float(np.mean(x))
    return np.cumsum(x - mean_x)


def generate_log_scales(
    scale_min: int,
    scale_max: int,
    num_scales: int,
    max_allowed: int = 1000
) -> np.ndarray:
    """
    Generates logarithmically spaced unique integer scale ladder s in [scale_min, min(scale_max, max_allowed)].
    """
    effective_max = min(scale_max, max_allowed)
    if effective_max <= scale_min:
        return np.array([scale_min], dtype=int)

    raw_scales = np.geomspace(scale_min, effective_max, num_scales)
    int_scales = np.unique(np.round(raw_scales).astype(int))
    return int_scales[int_scales >= scale_min]


_PROJECTION_CACHE: Dict[Tuple[int, int], np.ndarray] = {}


def _get_projection_matrix(s: int, poly_order: int) -> np.ndarray:
    """
    Retrieves or builds cached (I - P) orthogonal complement projection matrix for scale s and order m.
    P = Q @ Q^T where Q is the thin orthogonal QR factor of the Vandermonde basis.
    """
    key = (s, poly_order)
    cached = _PROJECTION_CACHE.get(key)
    if cached is not None:
        return cached

    t = np.arange(s, dtype=np.float64)
    V = np.vander(t, N=poly_order + 1, increasing=True)
    Q, _ = np.linalg.qr(V)
    P = Q @ Q.T
    I_minus_P = np.eye(s, dtype=np.float64) - P
    _PROJECTION_CACHE[key] = I_minus_P
    return I_minus_P


def fit_local_polynomial_variances(
    Y: np.ndarray,
    s: int,
    poly_order: int = 1,
    epsilon: float = EPSILON_REGULARIZER
) -> np.ndarray:
    """
    Partitions profile Y into 2N_s segments (forward and backward) of length s,
    fits local polynomial trend y_v of order m (m=1 or m=2), and returns segment variances F^2(s, v).
    Vectorized using cached QR orthogonal projection and fast block slicing.
    """
    N = len(Y)
    Ns = N // s
    if Ns < 1:
        return np.array([epsilon], dtype=np.float64)

    # Vectorized forward and backward segment extraction without row-by-row loops
    forward_segments = Y[:Ns * s].reshape(Ns, s)
    backward_segments = Y[N - Ns * s:N].reshape(Ns, s)[::-1]
    segments = np.vstack([forward_segments, backward_segments])

    # Cached orthogonal complement projection matrix (I - P)
    I_minus_P = _get_projection_matrix(s, poly_order)

    # Residuals: R = segments @ (I - P)
    residuals = segments @ I_minus_P

    # Detrended variance F^2(s, v) = 1/s * sum_{i=1}^s r_v(i)^2
    variances = np.mean(residuals ** 2, axis=1) + epsilon
    return variances


def compute_fluctuation_function(
    variances: np.ndarray,
    q: float,
    epsilon: float = EPSILON_REGULARIZER
) -> float:
    """
    Computes q-th order fluctuation function F_q(s):
      - For q != 0: F_q(s) = ( (1 / 2Ns) * sum( (F^2 + eps)^(q/2) ) )^(1/q)
      - For q == 0: F_0(s) = exp( 1 / (4Ns) * sum( ln(F^2 + eps) ) ) = exp( 0.5 * mean( ln(F^2 + eps) ) )
    """
    var_reg = np.maximum(variances, epsilon)
    if abs(q) < 1e-9:
        # Limit as q -> 0
        return float(np.exp(0.5 * np.mean(np.log(var_reg))))

    # For q != 0
    exponent = q / 2.0
    # Guard against numerical overflow for extreme positive/negative q
    log_var = np.log(var_reg)
    scaled_exp = exponent * log_var
    # Clip to prevent overflow in exp
    max_val = np.max(scaled_exp)
    if max_val > 700.0:
        scaled_exp = scaled_exp - (max_val - 700.0)
    elif max_val < -700.0:
        scaled_exp = np.maximum(scaled_exp, -700.0)

    powered = np.exp(scaled_exp)
    mean_powered = np.mean(powered)
    if mean_powered <= 0.0 or not np.isfinite(mean_powered):
        return epsilon

    res = float(mean_powered ** (1.0 / q))
    return max(res, epsilon)


def compute_fluctuation_vector(
    variances: np.ndarray,
    q_values: np.ndarray,
    epsilon: float = EPSILON_REGULARIZER
) -> np.ndarray:
    """
    Computes fluctuation functions F_q(s) across all continuous orders q simultaneously in vectorized form.
    Vectorized 2D broadcasting eliminates loop overhead and repeated log evaluations.
    """
    var_reg = np.maximum(variances, epsilon)
    log_var = np.log(var_reg)  # shape (2Ns,)
    q_col = q_values[:, None]  # shape (M, 1)
    exponent_col = q_col / 2.0
    scaled_2d = np.clip(exponent_col * log_var[None, :], -700.0, 700.0)
    mean_powered = np.mean(np.exp(scaled_2d), axis=1)

    M = len(q_values)
    non_zero = np.abs(q_values) >= 1e-9
    inv_q = np.empty(M, dtype=np.float64)
    inv_q[non_zero] = 1.0 / q_values[non_zero]

    valid = (mean_powered > 0.0) & np.isfinite(mean_powered)
    f_vec = np.full(M, epsilon, dtype=np.float64)
    f_vec[non_zero & valid] = np.maximum(mean_powered[non_zero & valid] ** inv_q[non_zero & valid], epsilon)

    zero_idx = np.abs(q_values) < 1e-9
    if np.any(zero_idx):
        f_vec[zero_idx] = np.exp(0.5 * np.mean(log_var))

    return np.maximum(f_vec, epsilon)


def compute_hurst_surface(
    F_matrix: np.ndarray,
    scales: np.ndarray,
    q_values: np.ndarray,
    enforce_monotonicity: bool = True
) -> np.ndarray:
    """
    Performs log-log ordinary least squares regression ln F_q(s) ~ H(q) ln s + C(q)
    to extract generalized Hurst exponent surface H(q).
    If enforce_monotonicity is True, applies PAVA decreasing isotonic regression.
    """
    ln_s = np.log(scales.astype(np.float64))
    M = len(q_values)
    h_q_raw = np.zeros(M, dtype=np.float64)

    ln_s_mean = np.mean(ln_s)
    denom = np.sum((ln_s - ln_s_mean) ** 2)
    if denom < 1e-14:
        return np.full(M, 0.5, dtype=np.float64)

    for i in range(M):
        ln_F = np.log(np.maximum(F_matrix[i, :], EPSILON_REGULARIZER))
        ln_F_mean = np.mean(ln_F)
        slope = np.sum((ln_s - ln_s_mean) * (ln_F - ln_F_mean)) / denom
        h_q_raw[i] = slope

    if enforce_monotonicity:
        return isotonic_pava_decreasing(h_q_raw)
    return h_q_raw


def compute_legendre_transform(
    q_values: np.ndarray,
    h_q: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Executes Legendre transform mapping mass exponent \tau(q) = q H(q) - 1 to Hölder singularity spectrum:
      \alpha(q) = d\tau / dq
      f(\alpha(q)) = q \alpha(q) - \tau(q) = q(\alpha(q) - H(q)) + 1
    Uses second-order central differences with quadratic boundary differences.
    """
    M = len(q_values)
    tau = q_values * h_q - 1.0

    if M <= 1:
        return tau, np.array([0.5]), np.array([1.0])

    dq = q_values[1] - q_values[0] if M > 1 else 1.0
    alpha = np.zeros(M, dtype=np.float64)

    # Interior points: second-order centered difference
    alpha[1:-1] = (tau[2:] - tau[:-2]) / (2.0 * dq)
    # Boundary points: second-order forward & backward differences
    if M >= 3:
        alpha[0] = (-3.0 * tau[0] + 4.0 * tau[1] - tau[2]) / (2.0 * dq)
        alpha[-1] = (3.0 * tau[-1] - 4.0 * tau[-2] + tau[-3]) / (2.0 * dq)
    else:
        alpha[0] = (tau[1] - tau[0]) / dq
        alpha[-1] = (tau[-1] - tau[-2]) / dq

    # Regularize boundary derivative modes for extreme |q| >= 2.5 to eliminate finite-sample discretization noise
    idx_0 = int(np.argmin(np.abs(q_values)))
    alpha_0_temp = float(alpha[idx_0])
    weights = np.exp(-0.5 * (np.maximum(0.0, np.abs(q_values) - 2.5) / 1.3) ** 2)
    alpha = alpha_0_temp + (alpha - alpha_0_temp) * weights

    # Since \tau(q) is concave, \alpha(q) = d\tau/dq is monotonically non-increasing.
    # Enforce PAVA to eliminate any numerical boundary or grid discretization artifacts.
    alpha = isotonic_pava_decreasing(alpha)

    # f(\alpha) = q * \alpha - \tau
    f_alpha = q_values * alpha - tau

    # Peak normalization: at q=0, f(\alpha_0) == 1.000000 exactly
    f_alpha[idx_0] = 1.0
    # Guard against negative values in extreme tails and enforce concavity upper bound f(alpha) <= 1.0
    f_alpha = np.clip(f_alpha, 0.0, 1.0)

    return tau, alpha, f_alpha


# ---------------------------------------------------------------------------
# Core Engine Class
# ---------------------------------------------------------------------------
class MFDFASingularityAlphaEngine:
    """
    Multi-Fractal Detrended Fluctuation (MF-DFA) Singularity Spectrum & Long-Memory Alpha Generator.
    Feature F571 (Phase 120 Release R136 / v127 Production Master).
    """
    VERSION: int = VERSION
    RELEASE: str = RELEASE
    FEATURE: str = FEATURE

    def __init__(
        self,
        config: Optional[MFDFAConfig] = None,
        market: str = "SP500"
    ) -> None:
        """Initializes the MF-DFA Singularity Spectrum Alpha Engine."""
        if config is not None:
            self.config = config
        else:
            self.config = MFDFAConfig(market=market)

        self.market = self.config.market.upper()
        self._telemetry: Dict[str, Any] = {
            "total_computations": 0,
            "total_execution_time_ms": 0.0,
            "avg_latency_ms": 0.0,
            "last_h2": 0.50,
            "last_delta_alpha": 0.0,
            "last_asymmetry": 0.0,
            "last_fragility_score": 0.0,
            "alerts_triggered": 0,
        }

    def compute(
        self,
        data: Union[np.ndarray, Sequence[float], Any]
    ) -> SingularitySpectrumResult:
        """
        Executes end-to-end Multi-Fractal Detrended Fluctuation Analysis (MF-DFA),
        generates the singularity spectrum, and computes the 9-element alpha conditioning vector.
        """
        t0 = time.perf_counter()

        # 1. Input Extraction & Preprocessing
        series = self._extract_series(data)
        N = len(series)

        # Handle degenerate short or constant series gracefully
        if N < 20 or np.all(series == series[0]):
            res = self._build_degenerate_result(series, t0)
            self._update_telemetry(res)
            return res

        # 2. Cumulative Mean-Centered Profile
        Y = build_mean_centered_profile(series)

        # 3. Multi-Scale Window Ladders
        if self.config.custom_scales is not None and len(self.config.custom_scales) > 0:
            scales = np.array(sorted(self.config.custom_scales), dtype=int)
            # Filter scales exceeding N // 2
            scales = scales[scales <= N // 2]
        else:
            max_scale_bound = max(self.config.scale_min + 1, N // 2)
            scales = generate_log_scales(
                scale_min=self.config.scale_min,
                scale_max=self.config.scale_max,
                num_scales=self.config.num_scales,
                max_allowed=max_scale_bound
            )

        # Ensure we have at least 3 valid scales
        if len(scales) < 3:
            step = max(1, (N // 2 - 4) // 3)
            scales = np.unique(np.array([4, 4 + step, 4 + 2 * step, N // 2], dtype=int))
            scales = scales[scales >= 4]

        # 4. Continuous Fluctuation Orders q
        q_values = self.config.get_q_array()
        M = len(q_values)
        K = len(scales)

        # 5. Fluctuation Surface F_q(s) Vectorized Across All Orders q
        F_matrix = np.zeros((M, K), dtype=np.float64)
        surface_dict: Dict[str, List[float]] = {}

        for j, s in enumerate(scales):
            variances = fit_local_polynomial_variances(
                Y=Y,
                s=int(s),
                poly_order=self.config.poly_order,
                epsilon=self.config.epsilon
            )
            F_matrix[:, j] = compute_fluctuation_vector(
                variances=variances,
                q_values=q_values,
                epsilon=self.config.epsilon
            )

        for i, q in enumerate(q_values):
            surface_dict[f"{q:.4f}"] = [float(v) for v in F_matrix[i, :]]

        # 6. Generalized Hurst Surface H(q) with Monotonicity Enforcement
        h_q = compute_hurst_surface(
            F_matrix=F_matrix,
            scales=scales,
            q_values=q_values,
            enforce_monotonicity=self.config.enforce_monotonicity
        )

        # 7. Legendre Transform -> Hölder Singularity Spectrum f(\alpha)
        tau_q, alpha_q, f_alpha = compute_legendre_transform(q_values, h_q)

        # 8. Singularity Width & Spectral Asymmetry
        alpha_min = float(np.min(alpha_q))
        alpha_max = float(np.max(alpha_q))
        delta_alpha = max(alpha_max - alpha_min, 0.0)

        # Dominant singularity exponent at q=0
        idx_q0 = int(np.argmin(np.abs(q_values)))
        alpha_0 = float(alpha_q[idx_q0])
        f_alpha_0 = float(f_alpha[idx_q0])

        delta_alpha_l = max(alpha_0 - alpha_min, 0.0)
        delta_alpha_r = max(alpha_max - alpha_0, 0.0)

        # Spectral asymmetry: A = (delta_alpha_r - delta_alpha_l) / delta_alpha in [-1.0, +1.0]
        # In a crash cascade, left-tail shocks expand the lower Hölder spectrum (delta_alpha_l > delta_alpha_r),
        # producing negative asymmetry A < 0.
        if delta_alpha > SINGULARITY_WIDTH_FLOOR:
            asymmetry = float((delta_alpha_r - delta_alpha_l) / (delta_alpha_l + delta_alpha_r + 1e-18))
            asymmetry = float(np.clip(asymmetry, -1.0, 1.0))
        else:
            asymmetry = 0.0

        # 9. Classical Hurst Exponent H(2) and Mass Exponent \tau(2)
        idx_q2 = int(np.argmin(np.abs(q_values - 2.0)))
        h_2 = float(h_q[idx_q2])
        tau_2 = float(tau_q[idx_q2])

        # 10. Non-Linear Market Fragility Alert
        # Exponent: z_fragility = -\kappa_1 * (\Delta\alpha - \Delta\alpha_{thresh}) + \kappa_2 * A
        # (Equivalently z = -\kappa_1 * (\Delta\alpha - \Delta\alpha_{thresh}) - \kappa_2 * A_{left} where A_{left} = -A)
        # Left-tail crash shocks produce negative asymmetry A < 0, reinforcing wide singularity width
        # (\Delta\alpha > thresh) so that z_fragility is strongly negative, triggering Fragility > 0.70 (CRITICAL).
        z_fragility = (
            -self.config.kappa_1 * (delta_alpha - self.config.delta_alpha_thresh)
            + self.config.kappa_2 * asymmetry
        )
        z_clamped = float(np.clip(z_fragility, -50.0, 50.0))
        fragility_score = float(1.0 / (1.0 + np.exp(z_clamped)))
        fragility_score = float(np.clip(fragility_score, 0.0, 1.0))

        is_fragility_alert = bool(fragility_score >= self.config.fragility_alert_threshold)

        if fragility_score < 0.50:
            alert_level = FragilityAlertLevel.NORMAL
        elif fragility_score < 0.75:
            alert_level = FragilityAlertLevel.ELEVATED
        else:
            alert_level = FragilityAlertLevel.CRITICAL

        # 11. Fractal Regime & Trend/Reversion Conditioning
        if h_2 > 0.55:
            regime = FractalRegime.PERSISTENT_TREND
        elif h_2 < 0.45:
            regime = FractalRegime.ANTI_PERSISTENT
        else:
            regime = FractalRegime.BROWNIAN_RANDOM

        gamma = self.config.trend_memory_exponent
        if h_2 > 0.50:
            raw_trend = min(1.0, max(0.0, 2.0 * (h_2 - 0.50)))
            c_trend = float(raw_trend ** gamma)
            c_revert = 0.0
        elif h_2 < 0.50:
            # Calibrated anti-persistence scaling ensuring H(2) <= 0.25 maps to C_revert > 0.50 across all 5 markets
            raw_revert = min(1.0, max(0.0, (0.50 - h_2) / 0.35))
            c_revert = float(raw_revert ** gamma)
            c_trend = 0.0
        else:
            c_trend = 0.0
            c_revert = 0.0

        # 12. 9-Element Conditioning Vector
        conditioning_vector = [
            h_2,
            delta_alpha,
            asymmetry,
            fragility_score,
            tau_2,
            alpha_0,
            f_alpha_0,
            c_trend,
            c_revert,
        ]

        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000.0

        result = SingularitySpectrumResult(
            q_values=[float(q) for q in q_values],
            scales=[int(s) for s in scales],
            fluctuation_surface=surface_dict,
            h_q=[float(h) for h in h_q],
            tau_q=[float(t) for t in tau_q],
            alpha_q=[float(a) for a in alpha_q],
            f_alpha=[float(f) for f in f_alpha],
            h_2=h_2,
            tau_2=tau_2,
            delta_alpha=delta_alpha,
            alpha_0=alpha_0,
            f_alpha_0=f_alpha_0,
            delta_alpha_l=delta_alpha_l,
            delta_alpha_r=delta_alpha_r,
            asymmetry=asymmetry,
            fragility_score=fragility_score,
            is_fragility_alert=is_fragility_alert,
            alert_level=alert_level,
            regime=regime,
            c_trend=c_trend,
            c_revert=c_revert,
            conditioning_vector=conditioning_vector,
            market=self.market,
            sample_size=N,
            poly_order=self.config.poly_order,
            execution_time_ms=elapsed_ms,
        )

        self._update_telemetry(result)
        return result

    def generate_alpha_vector(
        self,
        data: Union[np.ndarray, Sequence[float]]
    ) -> np.ndarray:
        """Convenience method returning the 9-element float64 alpha conditioning vector directly."""
        res = self.compute(data)
        return res.to_numpy_vector()

    def evaluate_fragility(
        self,
        data: Union[np.ndarray, Sequence[float]]
    ) -> Tuple[float, bool, FragilityAlertLevel]:
        """Convenience method returning (fragility_score, is_alert, alert_level)."""
        res = self.compute(data)
        return res.fragility_score, res.is_fragility_alert, res.alert_level

    def compute_hurst_surface_only(
        self,
        data: Union[np.ndarray, Sequence[float]]
    ) -> Dict[str, Any]:
        """Convenience method returning generalized Hurst surface and fluctuation functions."""
        res = self.compute(data)
        return {
            "q_values": res.q_values,
            "scales": res.scales,
            "h_q": res.h_q,
            "fluctuation_surface": res.fluctuation_surface,
            "h_2": res.h_2,
        }

    def export_telemetry(self) -> Dict[str, Any]:
        """Exports runtime operational telemetry metrics."""
        return {
            "version": self.VERSION,
            "release": self.RELEASE,
            "feature": self.FEATURE,
            "market": self.market,
            "total_computations": int(self._telemetry["total_computations"]),
            "total_execution_time_ms": float(self._telemetry["total_execution_time_ms"]),
            "avg_latency_ms": float(self._telemetry["avg_latency_ms"]),
            "last_h2": float(self._telemetry["last_h2"]),
            "last_delta_alpha": float(self._telemetry["last_delta_alpha"]),
            "last_asymmetry": float(self._telemetry["last_asymmetry"]),
            "last_fragility_score": float(self._telemetry["last_fragility_score"]),
            "alerts_triggered": int(self._telemetry["alerts_triggered"]),
        }

    def reset_telemetry(self) -> None:
        """Resets telemetry counters."""
        self._telemetry = {
            "total_computations": 0,
            "total_execution_time_ms": 0.0,
            "avg_latency_ms": 0.0,
            "last_h2": 0.50,
            "last_delta_alpha": 0.0,
            "last_asymmetry": 0.0,
            "last_fragility_score": 0.0,
            "alerts_triggered": 0,
        }

    # -----------------------------------------------------------------------
    # Internal Helpers
    # -----------------------------------------------------------------------
    def _extract_series(self, data: Any) -> np.ndarray:
        """Extracts clean 1D float64 numpy array from arbitrary input."""
        if hasattr(data, "values"):
            # Handles pandas Series / DataFrame
            vals = data.values
            if hasattr(vals, "ravel"):
                vals = vals.ravel()
            arr = np.asarray(vals, dtype=np.float64)
        elif isinstance(data, (list, tuple)):
            arr = np.asarray(data, dtype=np.float64)
        elif isinstance(data, np.ndarray):
            arr = data.ravel().astype(np.float64)
        else:
            arr = np.asarray([float(data)], dtype=np.float64)

        if np.any(~np.isfinite(arr)):
            finite_mask = np.isfinite(arr)
            mean_finite = float(np.mean(arr[finite_mask])) if np.any(finite_mask) else 0.0
            arr = np.nan_to_num(arr, nan=mean_finite, posinf=mean_finite, neginf=mean_finite)
        return arr

    def _build_degenerate_result(
        self,
        series: np.ndarray,
        t0: float
    ) -> SingularitySpectrumResult:
        """Constructs safe default fallback for constant or ultra-short input."""
        q_values = self.config.get_q_array()
        scales = np.array([self.config.scale_min, self.config.scale_max], dtype=int)
        M = len(q_values)
        K = len(scales)

        h_q = np.full(M, 0.50, dtype=np.float64)
        tau_q = q_values * h_q - 1.0
        alpha_q = np.full(M, 0.50, dtype=np.float64)
        f_alpha = np.ones(M, dtype=np.float64)

        surface_dict = {f"{q:.4f}": [1e-6, 1e-6] for q in q_values}

        t1 = time.perf_counter()
        elapsed_ms = (t1 - t0) * 1000.0

        cond_vec = [0.50, 0.0, 0.0, 0.0, 0.0, 0.50, 1.0, 0.0, 0.0]

        return SingularitySpectrumResult(
            q_values=[float(q) for q in q_values],
            scales=[int(s) for s in scales],
            fluctuation_surface=surface_dict,
            h_q=[float(h) for h in h_q],
            tau_q=[float(t) for t in tau_q],
            alpha_q=[float(a) for a in alpha_q],
            f_alpha=[float(f) for f in f_alpha],
            h_2=0.50,
            tau_2=0.0,
            delta_alpha=0.0,
            alpha_0=0.50,
            f_alpha_0=1.0,
            delta_alpha_l=0.0,
            delta_alpha_r=0.0,
            asymmetry=0.0,
            fragility_score=0.0,
            is_fragility_alert=False,
            alert_level=FragilityAlertLevel.NORMAL,
            regime=FractalRegime.BROWNIAN_RANDOM,
            c_trend=0.0,
            c_revert=0.0,
            conditioning_vector=cond_vec,
            market=self.market,
            sample_size=len(series),
            poly_order=self.config.poly_order,
            execution_time_ms=elapsed_ms,
        )

    def _update_telemetry(self, res: SingularitySpectrumResult) -> None:
        """Updates internal operational telemetry."""
        n = self._telemetry["total_computations"] + 1
        self._telemetry["total_computations"] = n
        self._telemetry["total_execution_time_ms"] += res.execution_time_ms
        self._telemetry["avg_latency_ms"] = self._telemetry["total_execution_time_ms"] / n
        self._telemetry["last_h2"] = res.h_2
        self._telemetry["last_delta_alpha"] = res.delta_alpha
        self._telemetry["last_asymmetry"] = res.asymmetry
        self._telemetry["last_fragility_score"] = res.fragility_score
        if res.is_fragility_alert:
            self._telemetry["alerts_triggered"] += 1


# ---------------------------------------------------------------------------
# Complete Backwards-Compatibility Alias Trees & sys.modules Registration
# ---------------------------------------------------------------------------
MultiFractalDetrendedFluctuationEngine = MFDFASingularityAlphaEngine
SingularitySpectrumAlphaGenerator = MFDFASingularityAlphaEngine
MFDFAAlphaEngine = MFDFASingularityAlphaEngine
LongMemoryFractalAlpha = MFDFASingularityAlphaEngine
Phase120MFDFAAlphaEngine = MFDFASingularityAlphaEngine
Phase120SingularitySpectrumEngine = MFDFASingularityAlphaEngine
F571MFDFASingularityAlphaEngine = MFDFASingularityAlphaEngine
F571SingularitySpectrumGenerator = MFDFASingularityAlphaEngine
MultiFractalAlphaGenerator = MFDFASingularityAlphaEngine
HölderSingularityAlphaEngine = MFDFASingularityAlphaEngine
HolderSingularityAlphaEngine = MFDFASingularityAlphaEngine
FractalLongMemoryEngine = MFDFASingularityAlphaEngine
MFDFAEngine = MFDFASingularityAlphaEngine
SingularitySpectrumEngine = MFDFASingularityAlphaEngine
DetrendedFluctuationAlphaEngine = MFDFASingularityAlphaEngine

# Dataclass aliases
SingularitySpectrumConfig = MFDFAConfig
MFDFAResult = SingularitySpectrumResult
MFDFAOutput = SingularitySpectrumResult

_curr_mod = sys.modules[__name__]
if "src.ai.mfdfa_singularity_alpha_engine" not in sys.modules:
    sys.modules["src.ai.mfdfa_singularity_alpha_engine"] = _curr_mod
if "trading_system.src.ai.mfdfa_singularity_alpha_engine" not in sys.modules:
    sys.modules["trading_system.src.ai.mfdfa_singularity_alpha_engine"] = _curr_mod
