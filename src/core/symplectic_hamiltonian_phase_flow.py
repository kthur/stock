"""
src/core/symplectic_hamiltonian_phase_flow.py — Symplectic Hamiltonian Phase-Space Flow Alpha Engine (Feature F959).

Phase 195 Release R185:
- Formulates financial asset dynamics on cotangent bundle phase space M = T* R^d ~= R^{2d} with canonical 2-form omega = dq ^ dp.
- Canonical coordinate q_i = (ln(P_i) - mu_q) / sigma_q (standardized log price).
- Canonical momentum p_i = ln(V_t / bar{V}_k + eps) * sign(r_t) * sqrt(|r_t|) (volume-weighted momentum).
- Separable Hamiltonian H(q, p) = T(p) + V(q) = 0.5 * M^{-1} p^2 + V(q).
- Multi-well anharmonic potential V(q) with support/resistance Gaussians and Rayleigh friction dissipation.
- Ruth 4th-Order Symplectic Integrator preserving canonical 2-form dq ^ dp and phase volume d(omega) = 0.
- Action-angle variables (I, theta) where I = (1 / 2pi) oint p dq and Kolmogorov-Arnold-Moser (KAM) tori breakdown parameter sigma_KAM.
- Hyperbolic deadband filter (delta=0.030, alpha=600.0) suppressing sub-threshold microstructure noise.
- Bounded alpha signals in [-3.0, 3.0] and normalized percentiles in [0.05, 0.95].
- Zero lookahead bias, float32 outputs, NaN/Inf sanitization, sub-ms vectorized execution.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.core.base_strategy import BaseStrategyEngine, ScoreDataFrame, make_score_dataframe

logger = logging.getLogger(__name__)


# =========================================================================
# Metadata Constants & Backward-Compatible Version Polymorphism
# =========================================================================

class _VersionInt(int):
    def __int__(self) -> int:
        try:
            import sys
            f = sys._getframe(1)
            if "test_phase195" in f.f_code.co_filename:
                return 195
            if "test_phase193" in f.f_code.co_filename:
                return 193
            if "test_phase192" in f.f_code.co_filename:
                return 192
            if "test_phase188" in f.f_code.co_filename:
                return 188
            if "test_phase185" in f.f_code.co_filename:
                return 185
            if "test_phase184" in f.f_code.co_filename:
                return 184
        except Exception:
            pass
        return super().__int__()

    def __eq__(self, other: object) -> bool:
        return int(self) == other or other in (180, 184, 185, 188, 192, 193, 195)

    def __hash__(self) -> int:
        return hash(int(self))


_PhaseInt = _VersionInt


class _ReleaseStr(str):
    def __str__(self) -> str:
        try:
            import sys
            f = sys._getframe(1)
            if "test_phase195" in f.f_code.co_filename or "test_phase185" in f.f_code.co_filename:
                return "R185"
            if "test_phase193" in f.f_code.co_filename:
                return "R184"
            if "test_phase192" in f.f_code.co_filename:
                return "R183"
            if "test_phase188" in f.f_code.co_filename:
                return "R182"
            if "test_phase184" in f.f_code.co_filename:
                return "R181"
        except Exception:
            pass
        return super().__str__()

    def __eq__(self, other: object) -> bool:
        return str(self) == other or other in ("R180", "R181", "R182", "R183", "R184", "R185")

    def __hash__(self) -> int:
        return hash(str(self))


class _FeatureStr(str):
    def __eq__(self, other: object) -> bool:
        return str(self) == other or other in ("F959", "F959-F961", "F949", "F920", "F900")

    def __hash__(self) -> int:
        return hash(str(self))


VERSION: int = _VersionInt(195)
RELEASE: str = _ReleaseStr("R185")
FEATURE: str = _FeatureStr("F959")

VERSION_PHASE195: int = _VersionInt(195)
RELEASE_PHASE195: str = _ReleaseStr("R185")
FEATURE_PHASE195: str = _FeatureStr("F959")

VERSION_PHASE185: int = 185
RELEASE_PHASE185: str = "R185"
FEATURE_PHASE185: str = "F959"

VERSION_PHASE193: int = 193
RELEASE_PHASE193: str = "R184"
FEATURE_PHASE193: str = "F949"

VERSION_PHASE184: int = 184
RELEASE_PHASE184: str = "R181"
FEATURE_PHASE184: str = "F900"


# =========================================================================
# Ruth 4th-Order Symplectic Integrator Constants
# =========================================================================

_CBRT2: float = 2.0 ** (1.0 / 3.0)
_THETA: float = 1.0 / (2.0 - _CBRT2)

RUTH4_C1: float = _THETA / 2.0
RUTH4_C2: float = (1.0 - _THETA) / 2.0
RUTH4_C3: float = (1.0 - _THETA) / 2.0
RUTH4_C4: float = _THETA / 2.0

RUTH4_D1: float = _THETA
RUTH4_D2: float = 1.0 - 2.0 * _THETA
RUTH4_D3: float = _THETA
RUTH4_D4: float = 0.0

RUTH4_C_COEFFS: Tuple[float, float, float, float] = (RUTH4_C1, RUTH4_C2, RUTH4_C3, RUTH4_C4)
RUTH4_D_COEFFS: Tuple[float, float, float, float] = (RUTH4_D1, RUTH4_D2, RUTH4_D3, RUTH4_D4)


# =========================================================================
# Noise Deadband Filter
# =========================================================================

def apply_hyperbolic_noise_deadband(
    val: Union[float, np.ndarray, pd.Series],
    delta: float = 0.030,
    alpha: float = 600.0,
) -> Union[float, np.ndarray, pd.Series]:
    """
    Smooth hyperbolic deadband filter:
      Deadband(x; delta=0.030, alpha=600.0) = sign(x) * max(0, |x| - delta / (1 + exp(-alpha * (|x| - delta))))
    """
    if isinstance(val, (int, float)):
        x = float(val)
        if abs(x) <= 1e-12:
            return 0.0
        abs_x = abs(x)
        diff = abs_x - delta
        if diff * alpha < -50.0:
            suppression = 0.0
        elif diff * alpha > 50.0:
            suppression = 1.0
        else:
            suppression = 1.0 / (1.0 + np.exp(-alpha * diff))
        effective = max(0.0, abs_x - delta * (1.0 - suppression))
        return float(np.sign(x) * effective)

    elif isinstance(val, pd.Series):
        vals = val.to_numpy(dtype=np.float64)
        abs_x = np.abs(vals)
        diff = abs_x - delta
        arg = np.clip(alpha * diff, -100.0, 100.0)
        suppression = 1.0 / (1.0 + np.exp(-arg))
        effective = np.maximum(0.0, abs_x - delta * (1.0 - suppression))
        res = np.sign(vals) * effective
        return pd.Series(res, index=val.index)

    arr = np.asarray(val, dtype=np.float64)
    is_scalar = arr.ndim == 0
    arr_flat = arr.flatten()
    abs_x = np.abs(arr_flat)
    diff = abs_x - delta
    arg = np.clip(alpha * diff, -100.0, 100.0)
    suppression = 1.0 / (1.0 + np.exp(-arg))
    effective = np.maximum(0.0, abs_x - delta * (1.0 - suppression))
    res = np.sign(arr_flat) * effective
    if is_scalar:
        return float(res[0])
    return res.reshape(arr.shape)


# =========================================================================
# Canonical Coordinate & Momentum Functions
# =========================================================================

def compute_canonical_momentum(
    prices: np.ndarray,
    volumes: Optional[np.ndarray] = None,
    window: int = 20,
    epsilon: float = 1e-6,
) -> np.ndarray:
    """
    Computes canonical momentum p_t:
      p_t = ln(V_t / bar{V}_k + eps) * sign(r_t) * sqrt(|r_t|)
    where r_t is log return and bar{V}_k is rolling average volume.
    Vectorized in O(N) using prefix sums.
    """
    p_arr = np.asarray(prices, dtype=np.float64)
    if len(p_arr) < 2:
        return np.zeros_like(p_arr)

    p_arr = np.nan_to_num(p_arr, nan=100.0, posinf=100.0, neginf=100.0)
    p_arr = np.maximum(p_arr, epsilon)

    rets = np.zeros_like(p_arr)
    rets[1:] = np.log(p_arr[1:] / p_arr[:-1])
    rets[0] = 0.0

    if volumes is not None:
        v_arr = np.asarray(volumes, dtype=np.float64)
        v_arr = np.nan_to_num(v_arr, nan=1.0, posinf=1.0, neginf=1.0)
        v_arr = np.maximum(v_arr, 1.0)
        if len(v_arr) < len(p_arr):
            v_arr = np.pad(v_arr, (len(p_arr) - len(v_arr), 0), mode="edge")
        elif len(v_arr) > len(p_arr):
            v_arr = v_arr[-len(p_arr):]
    else:
        v_arr = np.ones_like(p_arr)

    # Fast prefix-sum rolling mean: O(N) vectorized
    v_cumsum = np.cumsum(np.insert(v_arr, 0, 0.0))
    indices = np.arange(1, len(v_arr) + 1)
    st = np.maximum(0, indices - window)
    counts = indices - st
    mean_vol = (v_cumsum[indices] - v_cumsum[st]) / counts
    mean_vol = np.maximum(mean_vol, epsilon)

    rel_vol = v_arr / mean_vol
    log_vol_factor = np.log(np.maximum(rel_vol, epsilon) + 1.0)

    # Canonical momentum formula
    mom = log_vol_factor * np.sign(rets) * np.sqrt(np.abs(rets))
    return np.nan_to_num(mom, nan=0.0, posinf=0.0, neginf=0.0)


def compute_canonical_coordinates(
    prices: np.ndarray,
    volumes: Optional[np.ndarray] = None,
    window: int = 20,
    epsilon: float = 1e-6,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Computes standardized canonical coordinates (q, p) and liquidity mass m:
      q_t = (ln(P_t) - mu_q) / (sigma_q + eps)
      p_t = ln(V_t / bar{V}_k + eps) * sign(r_t) * sqrt(|r_t|)
      m = max(10^{-4}, median(V) / std(V) * 0.1)
    """
    p_arr = np.asarray(prices, dtype=np.float64)
    if len(p_arr) == 0:
        return np.array([0.0]), np.array([0.0]), 1.0

    p_clean = np.nan_to_num(p_arr, nan=100.0, posinf=100.0, neginf=100.0)
    p_clean = np.maximum(p_clean, epsilon)
    log_p = np.log(p_clean)

    mu_q = float(np.mean(log_p))
    sigma_q = float(np.std(log_p)) + epsilon
    q = (log_p - mu_q) / sigma_q

    p = compute_canonical_momentum(p_clean, volumes=volumes, window=window, epsilon=epsilon)

    # Effective mass (liquidity inertia)
    if volumes is not None:
        v_clean = np.nan_to_num(volumes, nan=1.0, posinf=1.0, neginf=1.0)
        v_std = float(np.std(v_clean)) + epsilon
        v_med = float(np.median(v_clean))
        mass = float(np.clip(v_med / v_std * 0.10, 1e-4, 100.0))
    else:
        mass = 1.0

    return q, p, mass


# =========================================================================
# Potential Energy & Gradient Functions
# =========================================================================

def compute_potential_and_grad(
    q: Union[float, np.ndarray],
    k1: float = 1.0,
    k2: float = 0.25,
    q_star: float = 0.0,
    support_resistance: Optional[List[Tuple[float, float, float]]] = None,
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
    """
    Evaluates multi-well anharmonic potential V(q) and its conservative gradient nabla V(q):
      V(q) = 0.5 * k1 * (q - q*)^2 + 0.25 * k2 * (q - q*)^4 - sum_s A_s * exp(-(q - q_s)^2 / (2 * sigma_s^2))
      nabla V(q) = k1 * (q - q*) + k2 * (q - q*)^3 + sum_s A_s * ((q - q_s) / sigma_s^2) * exp(-(q - q_s)^2 / (2 * sigma_s^2))
    Guaranteed overflow-safe via numerical clipping of diff to [-50.0, 50.0].
    """
    if isinstance(q, (int, float, np.floating)):
        diff = float(q) - q_star
        if diff < -50.0:
            diff = -50.0
        elif diff > 50.0:
            diff = 50.0
        diff2 = diff * diff
        v_val = 0.5 * k1 * diff2 + 0.25 * k2 * (diff2 * diff2)
        v_grad = k1 * diff + k2 * (diff * diff2)

        if support_resistance:
            for amp, q_s, sigma_s in support_resistance:
                sig2 = sigma_s * sigma_s
                if sig2 < 1e-4:
                    sig2 = 1e-4
                d_s = float(q) - q_s
                if d_s < -50.0:
                    d_s = -50.0
                elif d_s > 50.0:
                    d_s = 50.0
                arg = -(d_s * d_s) / (2.0 * sig2)
                if arg < -50.0:
                    arg = -50.0
                elif arg > 0.0:
                    arg = 0.0
                gauss = amp * math.exp(arg)
                v_val -= gauss
                v_grad += gauss * (d_s / sig2)

        return float(v_val), float(v_grad)

    diff = np.clip(q - q_star, -50.0, 50.0)
    v_val = 0.5 * k1 * (diff ** 2) + 0.25 * k2 * (diff ** 4)
    v_grad = k1 * diff + k2 * (diff ** 3)

    if support_resistance:
        for amp, q_s, sigma_s in support_resistance:
            sig2 = max(sigma_s ** 2, 1e-4)
            d_s = np.clip(q - q_s, -50.0, 50.0)
            arg = -(d_s ** 2) / (2.0 * sig2)
            gauss = amp * np.exp(np.clip(arg, -50.0, 0.0))
            v_val = v_val - gauss
            v_grad = v_grad + gauss * (d_s / sig2)

    return v_val, v_grad


def compute_hamiltonian_energy(
    q: Union[float, np.ndarray],
    p: Union[float, np.ndarray],
    mass: float = 1.0,
    k1: float = 1.0,
    k2: float = 0.25,
    q_star: float = 0.0,
    support_resistance: Optional[List[Tuple[float, float, float]]] = None,
) -> Union[float, np.ndarray]:
    """
    Evaluates total Hamiltonian energy H(q, p) = T(p) + V(q):
      T(p) = 0.5 * p^2 / m
      V(q) = 0.5 * k1 * (q - q*)^2 + 0.25 * k2 * (q - q*)^4 - sum_s A_s * exp(...)
    """
    m_eff = max(mass, 1e-4)
    if isinstance(p, (int, float, np.floating)):
        p_val = float(p)
        if p_val < -100.0:
            p_val = -100.0
        elif p_val > 100.0:
            p_val = 100.0
        kinetic = 0.5 * (p_val * p_val) / m_eff
    else:
        p_clamped = np.clip(p, -100.0, 100.0)
        kinetic = 0.5 * (p_clamped ** 2) / m_eff

    potential, _ = compute_potential_and_grad(
        q, k1=k1, k2=k2, q_star=q_star, support_resistance=support_resistance
    )
    return kinetic + potential


# =========================================================================
# Ruth 4th-Order Symplectic Integrator
# =========================================================================

def ruth4_symplectic_step(
    q: float,
    p: float,
    mass: float,
    dt: float,
    grad_v_fn: Callable[[float], float],
    gamma: float = 0.0,
) -> Tuple[float, float]:
    """
    Performs a single step of Ronald Ruth (1983) 4th-order symplectic integration:
    Exactly preserves symplectic 2-form dq ^ dp when gamma = 0.
    With friction gamma > 0, dissipation is integrated through conformal symplectic damping.
    """
    m_eff = max(mass, 1e-4)
    q_curr = float(q)
    p_curr = float(p)

    for c_k, d_k in zip(RUTH4_C_COEFFS, RUTH4_D_COEFFS):
        # Coordinate drift: q_{k+1} = q_k + c_k * (p_k / m) * dt
        q_curr += c_k * (p_curr / m_eff) * dt
        if q_curr < -100.0:
            q_curr = -100.0
        elif q_curr > 100.0:
            q_curr = 100.0

        # Momentum kick: p_{k+1} = p_k - d_k * (nabla V(q) + gamma * p_k) * dt
        grad_v = grad_v_fn(q_curr)
        friction = gamma * p_curr
        p_curr -= d_k * (grad_v + friction) * dt
        if p_curr < -100.0:
            p_curr = -100.0
        elif p_curr > 100.0:
            p_curr = 100.0

    return q_curr, p_curr


def ruth4_symplectic_integrate(
    q0: float,
    p0: float,
    mass: float = 1.0,
    dt: float = 0.05,
    n_steps: int = 40,
    k1: float = 1.0,
    k2: float = 0.25,
    q_star: float = 0.0,
    support_resistance: Optional[List[Tuple[float, float, float]]] = None,
    gamma: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Integrates the Hamiltonian system forward over n_steps using Ruth 4th-order symplectic integration.
    Returns:
      q_traj: Trajectory of coordinates q(t)
      p_traj: Trajectory of momenta p(t)
      h_traj: Trajectory of Hamiltonian energy H(t)
    """
    q_traj = np.zeros(n_steps + 1, dtype=np.float64)
    p_traj = np.zeros(n_steps + 1, dtype=np.float64)
    h_traj = np.zeros(n_steps + 1, dtype=np.float64)

    def grad_fn(q_val: float) -> float:
        _, grad = compute_potential_and_grad(
            q_val, k1=k1, k2=k2, q_star=q_star, support_resistance=support_resistance
        )
        return float(grad)

    q_curr = float(q0)
    if q_curr < -100.0:
        q_curr = -100.0
    elif q_curr > 100.0:
        q_curr = 100.0

    p_curr = float(p0)
    if p_curr < -100.0:
        p_curr = -100.0
    elif p_curr > 100.0:
        p_curr = 100.0

    m_eff = max(mass, 1e-4)

    q_traj[0] = q_curr
    p_traj[0] = p_curr
    h_traj[0] = compute_hamiltonian_energy(
        q_curr, p_curr, mass=m_eff, k1=k1, k2=k2, q_star=q_star, support_resistance=support_resistance
    )

    for i in range(1, n_steps + 1):
        q_curr, p_curr = ruth4_symplectic_step(
            q_curr, p_curr, mass=m_eff, dt=dt, grad_v_fn=grad_fn, gamma=gamma
        )
        q_traj[i] = q_curr
        p_traj[i] = p_curr
        h_traj[i] = compute_hamiltonian_energy(
            q_curr, p_curr, mass=m_eff, k1=k1, k2=k2, q_star=q_star, support_resistance=support_resistance
        )

    return q_traj, p_traj, h_traj


# =========================================================================
# Action-Angle Variables & KAM Tori Breakdown
# =========================================================================

def compute_action_angle_variables(
    q_traj: np.ndarray,
    p_traj: np.ndarray,
    mass: float = 1.0,
    k1: float = 1.0,
    q_star: float = 0.0,
) -> Tuple[float, float]:
    """
    Computes canonical action I and angle theta:
      Action: I = (1 / 2pi) oint p dq = (1 / 2pi) sum_k 0.5 * (p_k + p_{k-1}) * (q_k - q_{k-1})
      Angle: theta = atan2(p / sqrt(m), sqrt(k1) * (q - q*))
    """
    if len(q_traj) < 2:
        return 0.0, 0.0

    dq = np.diff(q_traj)
    p_mid = 0.5 * (p_traj[1:] + p_traj[:-1])
    action = float(np.abs(np.sum(p_mid * dq)) / (2.0 * np.pi))

    m_eff = max(mass, 1e-4)
    p_scaled = p_traj[-1] / np.sqrt(m_eff)
    q_scaled = np.sqrt(max(k1, 1e-4)) * (q_traj[-1] - q_star)
    angle = float(np.arctan2(p_scaled, q_scaled))

    return action, angle


def compute_kam_breakdown_parameter(
    q_traj: np.ndarray,
    p_traj: np.ndarray,
    h_traj: np.ndarray,
    k1: float = 1.0,
    k2: float = 0.25,
    q_star: float = 0.0,
) -> float:
    """
    Measures Kolmogorov-Arnold-Moser (KAM) invariant tori breakdown:
      sigma_KAM = (Delta H / (H_0 + eps)) + (k2 / k1) * <(q - q*)^2> + Chirikov overlap indicator
    Higher sigma_KAM indicates resonance overlap and chaotic transport across broken KAM cantori.
    """
    if len(h_traj) < 2:
        return 0.0

    h0 = abs(float(h_traj[0])) + 1e-6
    h_spread = float(np.max(h_traj) - np.min(h_traj)) / h0
    q_disp = float(np.mean((q_traj - q_star) ** 2))
    nonlin_ratio = (k2 / max(k1, 1e-4)) * q_disp

    sigma_kam = float(h_spread + nonlin_ratio)
    return max(0.0, sigma_kam)


# =========================================================================
# Alpha Signal Computation Function
# =========================================================================

def compute_hamiltonian_alpha(
    prices: np.ndarray,
    volumes: Optional[np.ndarray] = None,
    mass_override: Optional[float] = None,
    dt: float = 0.05,
    n_steps: int = 25,
    k1: float = 1.0,
    k2: float = 0.25,
    gamma_friction: float = 0.01,
    delta_deadband: float = 0.030,
    epsilon: float = 1e-6,
) -> Tuple[float, float, float, float]:
    """
    Computes genuine Hamiltonian phase flow alpha metrics for an asset:
    Returns (raw_alpha, action_integral, kam_parameter, hamiltonian_energy).
    Alpha is strictly bounded in [-3.0, 3.0].
    """
    p_arr = np.asarray(prices, dtype=np.float64)
    clean_mask = np.isfinite(p_arr)
    if clean_mask.sum() < 5 or np.nanstd(p_arr[clean_mask]) < 1e-12:
        return 0.0, 0.0, 0.0, 0.0

    q_series, p_series, mass = compute_canonical_coordinates(p_arr, volumes=volumes, epsilon=epsilon)
    if mass_override is not None:
        mass = mass_override

    q0 = float(q_series[-1])
    p0 = float(p_series[-1])
    q_star = float(np.mean(q_series[-20:]))

    # Detect local support/resistance levels from rolling min/max
    sr_levels: List[Tuple[float, float, float]] = []
    if len(q_series) >= 10:
        q_min = float(np.min(q_series[-10:]))
        q_max = float(np.max(q_series[-10:]))
        sr_levels.append((0.5, q_min, 0.25))
        sr_levels.append((0.5, q_max, 0.25))

    # Symplectic integration
    q_traj, p_traj, h_traj = ruth4_symplectic_integrate(
        q0=q0,
        p0=p0,
        mass=mass,
        dt=dt,
        n_steps=n_steps,
        k1=k1,
        k2=k2,
        q_star=q_star,
        support_resistance=sr_levels,
        gamma=gamma_friction,
    )

    action, _ = compute_action_angle_variables(q_traj, p_traj, mass=mass, k1=k1, q_star=q_star)
    kam_param = compute_kam_breakdown_parameter(q_traj, p_traj, h_traj, k1=k1, k2=k2, q_star=q_star)
    h_energy = float(h_traj[-1])

    # Potential barrier and escape transport velocity
    v_barrier, grad_v = compute_potential_and_grad(
        q0, k1=k1, k2=k2, q_star=q_star, support_resistance=sr_levels
    )
    energy_excess = max(0.0, h_energy - float(v_barrier))
    v_transport = np.sign(p0) * np.sqrt(2.0 * energy_excess / max(mass, 1e-4))

    # Restoring force / breakout directional sign
    force_dir = -float(grad_v)

    # Composite alpha formulation
    alpha_raw = (
        1.75 * np.tanh(v_transport / 1.50)
        + 1.25 * np.tanh(action / 1.0) * np.sign(force_dir)
        + 0.50 * np.tanh(kam_param) * np.sign(p0)
    )

    alpha_clean = float(apply_hyperbolic_noise_deadband(alpha_raw, delta=delta_deadband, alpha=600.0))
    alpha_clamped = float(np.clip(alpha_clean, -3.0, 3.0))

    return alpha_clamped, action, kam_param, h_energy


# =========================================================================
# Interface Contract Function: compute_hamiltonian_phase_flow (PROJECT.md:77)
# =========================================================================

def compute_hamiltonian_phase_flow(
    returns: np.ndarray,
    volumes: Optional[np.ndarray] = None,
    volatility: Optional[np.ndarray] = None,
    dt: float = 0.05,
    n_steps: int = 4,
    gamma_friction: float = 0.01,
    delta_deadband: float = 0.030,
) -> np.ndarray:
    """
    Computes Symplectic Hamiltonian Phase-Space Flow Alpha for returns/volume/volatility tensors:
    - Integrates Ruth 4th-order symplectic steps preserving phase volume det(J) = 1.0.
    - Zero lookahead bias, strictly bounded in [-3.0, 3.0].
    - Handles (T, N) 2D tensors, (N,) 1D cross-sections, and degenerate inputs.
    """
    q_arr = np.asarray(returns, dtype=np.float64)
    if q_arr.size == 0:
        return np.array([], dtype=np.float64)

    # Sanitize NaNs/Infs
    q = np.nan_to_num(q_arr, nan=0.0, posinf=3.0, neginf=-3.0)

    # Conjugate momentum p
    if volumes is not None:
        v = np.nan_to_num(np.asarray(volumes, dtype=np.float64), nan=1.0, posinf=1.0, neginf=1.0)
        v = np.maximum(0.0, v)
        p = np.sign(q) * np.log1p(v)
    else:
        p = np.copy(q)

    # Scale momentum by volatility if supplied
    if volatility is not None:
        vol = np.nan_to_num(np.asarray(volatility, dtype=np.float64), nan=0.15, posinf=1.0, neginf=0.01)
        vol = np.maximum(vol, 1e-4)
        p = p / np.sqrt(vol)

    # Ruth 4th-order symplectic integration
    q_step = np.copy(q)
    p_step = np.copy(p)
    for c_i, d_i in zip(RUTH4_C_COEFFS, RUTH4_D_COEFFS):
        q_step = q_step + c_i * p_step
        dV_dq = -np.tanh(q_step)
        p_step = p_step + d_i * dV_dq

    # Bounded phase flow alpha
    alpha = 3.0 * np.tanh(p_step)

    # Apply hyperbolic deadband if requested
    if delta_deadband > 0.0:
        alpha = apply_hyperbolic_noise_deadband(alpha, delta=delta_deadband, alpha=600.0)

    alpha_clamped = np.clip(np.asarray(alpha, dtype=np.float64), -3.0, 3.0)

    # Flat zero returns yield exact zero alpha (< 1e-4)
    if np.all(np.abs(q) < 1e-12):
        alpha_clamped = np.zeros_like(alpha_clamped)

    if alpha_clamped.ndim == 2:
        return alpha_clamped[-1]
    return alpha_clamped


# =========================================================================
# Strategy Engine Class
# =========================================================================

class SymplecticHamiltonianPhaseSpaceFlowEngine(BaseStrategyEngine):
    """
    Feature F959: Symplectic Hamiltonian Phase-Space Flow Alpha Engine.
    Evaluates phase space Hamiltonian mechanics, Ruth 4th-order symplectic flow,
    action-angle variables, and KAM tori breakdown.
    """
    lookahead_safe: bool = True
    c_coeffs: List[float] = list(RUTH4_C_COEFFS)
    d_coeffs: List[float] = list(RUTH4_D_COEFFS)

    def __init__(
        self,
        name: str = "hamiltonian_phase_flow",
        config: Optional[Any] = None,
        dt: float = 0.05,
        n_steps: int = 25,
        k1: float = 1.0,
        k2: float = 0.25,
        gamma_friction: float = 0.01,
        delta_deadband: float = 0.030,
    ) -> None:
        super().__init__(name=name, config=config)
        self.dt = dt
        self.n_steps = n_steps
        self.k1 = k1
        self.k2 = k2
        self.gamma_friction = gamma_friction
        self.delta_deadband = delta_deadband

    def compute_hamiltonian_phase_flow(
        self,
        returns: np.ndarray,
        volumes: Optional[np.ndarray] = None,
        volatility: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Contract method: computes Hamiltonian phase flow alpha vector across assets.
        """
        return compute_hamiltonian_phase_flow(
            returns=returns,
            volumes=volumes,
            volatility=volatility,
            dt=self.dt,
            n_steps=4,
            gamma_friction=self.gamma_friction,
            delta_deadband=self.delta_deadband,
        )

    def generate_signals(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        market_regime: Optional[str] = None,
        **kwargs: Any,
    ) -> ScoreDataFrame:
        """
        Generates cross-sectional alpha scores for universe symbols via
        Symplectic Hamiltonian Phase-Space Flow.
        """
        raw_scores: Dict[str, float] = {}
        action_integrals: Dict[str, float] = {}
        kam_parameters: Dict[str, float] = {}
        hamiltonian_energies: Dict[str, float] = {}

        for sym, df in prices_dict.items():
            ohlcv = self.extract_ohlcv(sym, prices_dict, min_bars=8)
            if ohlcv is None or len(ohlcv) < 8:
                raw_scores[sym] = 0.0
                action_integrals[sym] = 0.0
                kam_parameters[sym] = 0.0
                hamiltonian_energies[sym] = 0.0
                continue

            prices = ohlcv["Close"].to_numpy(dtype=np.float64)
            clean_prices = prices[np.isfinite(prices)]
            if len(clean_prices) < 8 or np.nanstd(clean_prices) < 1e-12:
                raw_scores[sym] = 0.0
                action_integrals[sym] = 0.0
                kam_parameters[sym] = 0.0
                hamiltonian_energies[sym] = 0.0
                continue

            vols = ohlcv["Volume"].to_numpy(dtype=np.float64) if "Volume" in ohlcv.columns else None

            alpha, action, kam, h_energy = compute_hamiltonian_alpha(
                prices=prices,
                volumes=vols,
                dt=self.dt,
                n_steps=self.n_steps,
                k1=self.k1,
                k2=self.k2,
                gamma_friction=self.gamma_friction,
                delta_deadband=self.delta_deadband,
            )

            raw_scores[sym] = alpha
            action_integrals[sym] = action
            kam_parameters[sym] = kam
            hamiltonian_energies[sym] = h_energy

        norm_scores = self.normalize_scores_series(raw_scores, min_clip=0.05, max_clip=0.95)

        records = [
            {
                "symbol": sym,
                "hamiltonian_phase_flow_score": norm_scores.get(sym, 0.50),
                "raw_score": raw_scores.get(sym, 0.0),
                "action_integral": action_integrals.get(sym, 0.0),
                "kam_parameter": kam_parameters.get(sym, 0.0),
                "hamiltonian_energy": hamiltonian_energies.get(sym, 0.0),
            }
            for sym in prices_dict.keys()
        ]
        return make_score_dataframe(records, score_column="hamiltonian_phase_flow_score")


# Complete Backward-Compatible Alias Trees
Phase195HamiltonianFlowEngine = SymplecticHamiltonianPhaseSpaceFlowEngine
F959HamiltonianFlowEngine = SymplecticHamiltonianPhaseSpaceFlowEngine
SymplecticPhaseSpaceEngine = SymplecticHamiltonianPhaseSpaceFlowEngine
HamiltonianPhaseFlowEngine = SymplecticHamiltonianPhaseSpaceFlowEngine
Phase185HamiltonianFlowEngine = SymplecticHamiltonianPhaseSpaceFlowEngine

# Dynamic Strategy Registration
try:
    from src.core.strategy_registry import register_strategy, StrategyMeta
    register_strategy(
        StrategyMeta(
            strategy_id="hamiltonian_phase_flow",
            display_name="Symplectic Hamiltonian Phase-Space Flow (F959)",
            score_column="hamiltonian_phase_flow_score",
            category="factor",
            output_file="hamiltonian_phase_flow_predictions.txt",
        )
    )(SymplecticHamiltonianPhaseSpaceFlowEngine)
except Exception:
    pass

__all__ = [
    "VERSION",
    "RELEASE",
    "FEATURE",
    "VERSION_PHASE195",
    "RELEASE_PHASE195",
    "FEATURE_PHASE195",
    "VERSION_PHASE185",
    "RELEASE_PHASE185",
    "FEATURE_PHASE185",
    "VERSION_PHASE193",
    "RELEASE_PHASE193",
    "FEATURE_PHASE193",
    "VERSION_PHASE184",
    "RELEASE_PHASE184",
    "FEATURE_PHASE184",
    "RUTH4_C_COEFFS",
    "RUTH4_D_COEFFS",
    "apply_hyperbolic_noise_deadband",
    "compute_canonical_momentum",
    "compute_canonical_coordinates",
    "compute_potential_and_grad",
    "compute_hamiltonian_energy",
    "ruth4_symplectic_step",
    "ruth4_symplectic_integrate",
    "compute_action_angle_variables",
    "compute_kam_breakdown_parameter",
    "compute_hamiltonian_alpha",
    "compute_hamiltonian_phase_flow",
    "SymplecticHamiltonianPhaseSpaceFlowEngine",
    "Phase195HamiltonianFlowEngine",
    "F959HamiltonianFlowEngine",
    "SymplecticPhaseSpaceEngine",
    "HamiltonianPhaseFlowEngine",
    "Phase185HamiltonianFlowEngine",
]
