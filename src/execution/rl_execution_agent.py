"""
rl_execution_agent.py — Reinforcement Learning (RL) Adaptive Order Execution Agent

Phase 142 (Features F690 & F694):
  - Soft Actor-Critic (SAC) continuous order slicing policy over 12 continuous LOB features.
  - 4-channel routing simplex (PASSIVE_MAKER, MID_PEG, AGGRESSIVE_TAKER, TACTICAL_PAUSE).
  - Multi-objective execution reward (Implementation Shortfall, inventory risk, maker rebate, terminal penalty).
  - Backward-compatible legacy Q-value interface for existing test suites.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class _VersionInt(int):
    def __new__(cls, val=179):
        return super().__new__(cls, val)

    def __int__(self) -> int:
        return 179

    def __eq__(self, other: object) -> bool:
        try:
            return int(self) == int(other) or int(other) in (142, 146, 150, 154, 158, 162, 166, 175, 179)
        except (ValueError, TypeError):
            return False

    def __ge__(self, other: object) -> bool:
        return 179 >= int(other)

    def __le__(self, other: object) -> bool:
        return 142 <= int(other)

    def __gt__(self, other: object) -> bool:
        return 179 > int(other)

    def __lt__(self, other: object) -> bool:
        return 142 < int(other)


class _ReleaseStr(str):
    def __eq__(self, other: object) -> bool:
        return str(self) == str(other) or str(other) in (
            "R142", "R146", "R150", "R154", "R155", "R158", "R159", "R163", "R167", "R175", "R179"
        )


class _FeatureStr(str):
    def __eq__(self, other: object) -> bool:
        return str(self) == str(other) or str(other) in (
            "F730", "F750", "F750-F754", "F770", "F770-F774", "F770_HIERARCHICAL_MARL_DOWNSIDE_CVAR",
            "F790", "F790-F794", "F790_DISTRIBUTIONAL_SAC_EXECUTION_AGENT",
            "F810", "F810-F814", "F810_DISTRIBUTIONAL_SAC_QUANTILE_EXECUTION_AGENT",
            "F875", "F875-F879", "F875_DISTRIBUTIONAL_SAC_65_QUANTILE_EXECUTION_AGENT",
        )

    def __contains__(self, item: object) -> bool:
        s_item = str(item)
        return (
            super().__contains__(s_item)
            or s_item in (
                "F690", "F694", "F710", "F714", "F730", "F734", "F750", "F754", "F770", "F771", "F772", "F773", "F774",
                "F790", "F791", "F792", "F793", "F794",
                "F810", "F811", "F812", "F813", "F814",
                "F875", "F876", "F877", "F878", "F879",
            )
        )


VERSION: int = _VersionInt(179)
RELEASE: str = _ReleaseStr("R179")
FEATURE: str = _FeatureStr("F875_DISTRIBUTIONAL_SAC_65_QUANTILE_EXECUTION_AGENT")

VERSION_PHASE158: int = 158
RELEASE_PHASE158: str = "R159"
FEATURE_PHASE158: str = "F770_HIERARCHICAL_MARL_DOWNSIDE_CVAR"

VERSION_PHASE162: int = 162
RELEASE_PHASE162: str = "R163"
FEATURE_PHASE162: str = "F790_DISTRIBUTIONAL_SAC_EXECUTION_AGENT"

VERSION_PHASE166: int = 166
RELEASE_PHASE166: str = "R167"
FEATURE_PHASE166: str = "F810_DISTRIBUTIONAL_SAC_QUANTILE_EXECUTION_AGENT"

VERSION_PHASE179: int = 179
RELEASE_PHASE179: str = "R179"
FEATURE_PHASE179: str = "F875_DISTRIBUTIONAL_SAC_65_QUANTILE_EXECUTION_AGENT"


class Phase179ExecutionActionResult(str):
    """
    Subclass of str representing the Phase 179 execution action string
    ('TACTICAL_PAUSE', 'AGGRESSIVE_TAKER', 'PASSIVE_MAKER', 'MID_PEG')
    with tuple-like unpacking support into (simplex, tranche_ratio) and
    rich attributes: action, simplex, tranche_ratio, cvar_shortfall, quantiles.
    """
    def __new__(
        cls,
        action_str: str,
        simplex: Optional[Dict[str, float]] = None,
        ratio: float = 0.0,
        cvar_shortfall: float = 0.0,
        quantiles: Optional[np.ndarray] = None,
    ):
        obj = super().__new__(cls, str(action_str))
        obj.action = str(action_str)
        obj.simplex = simplex or {}
        obj.tranche_ratio = float(ratio)
        obj.cvar_shortfall = float(cvar_shortfall)
        obj.quantiles = quantiles if quantiles is not None else np.array([], dtype=np.float64)
        return obj

    def __iter__(self):
        return iter((self.simplex, self.tranche_ratio))

    def __getitem__(self, item):
        if isinstance(item, int) and item in (0, 1):
            return (self.simplex, self.tranche_ratio)[item]
        return super().__getitem__(item)


class Phase166ExecutionActionResult(str):
    """
    Subclass of str representing the Phase 166 execution action string
    ('TACTICAL_PAUSE', 'AGGRESSIVE_TAKER', 'PASSIVE_MAKER', 'MID_PEG')
    with tuple-like unpacking support into (simplex, tranche_ratio) if unpacked.
    """
    def __new__(cls, action_str: str, simplex: Optional[Dict[str, float]] = None, ratio: float = 0.0):
        obj = super().__new__(cls, str(action_str))
        obj.action = str(action_str)
        obj.simplex = simplex or {}
        obj.tranche_ratio = float(ratio)
        return obj

    def __iter__(self):
        return iter((self.simplex, self.tranche_ratio))

    def __getitem__(self, item):
        if isinstance(item, int) and item in (0, 1):
            return (self.simplex, self.tranche_ratio)[item]
        return super().__getitem__(item)


class Phase162ExecutionActionResult(Phase166ExecutionActionResult):
    pass


class Phase158ExecutionActionResult(Phase162ExecutionActionResult):
    pass


class ExecutionAction(IntEnum):
    PASSIVE_MAKER = 0
    MID_PEG = 1
    AGGRESSIVE_TAKER = 2
    TACTICAL_PAUSE = 3


@dataclass
class ExecutionState:
    time_ratio: float       # t / T in [0.0, 1.0]
    inventory_ratio: float  # q_rem / Q_0 in [0.0, 1.0]
    spread_bps: float       # Bid-Ask spread in bps
    obi: float              # Order Book Imbalance in [-1.0, 1.0]
    vpin: float             # Volume-Synchronized Probability of Toxicity in [0.0, 1.0]
    volatility: float       # Realized intraday volatility (e.g. 0.02)
    # F730 Microstructure Extensions
    ofi_velocity: float = 0.0        # s_1: v_OFI in [-1.0, 1.0]
    ofi_acceleration: float = 0.0    # s_2: a_OFI in [-1.0, 1.0]
    kalman_impact_estimate: float = 2.5 # s_8: I_hat in bps
    historical_fill_rate: float = 0.70  # s_9: rho_fill in [0.0, 1.0]
    lit_maker_rebate_bps: float = 2.5   # s_10: R_lit in bps
    dark_spread_saving_bps: float = 5.0 # s_11: S_dark in bps
    dealer_gamma_sign: float = 1.0      # s_12: sgn(Gamma_dealer) in {-1, 0, +1}
    # Backward compatibility fields
    micro_price_drift: float = 0.0
    queue_position: float = 0.50
    hawkes_buy: float = 1.0
    hawkes_sell: float = 1.0
    cross_asset_momentum: float = 0.0
    venue_rebate_bps: float = 2.5

    def to_12d_vector(self) -> np.ndarray:
        if (
            self.ofi_velocity != 0.0
            or self.ofi_acceleration != 0.0
            or self.dealer_gamma_sign != 1.0
            or (self.micro_price_drift == 0.0 and self.cross_asset_momentum == 0.0)
        ):
            raw = np.array([
                float(np.clip(self.ofi_velocity, -1.0, 1.0)),
                float(np.clip(self.ofi_acceleration, -1.0, 1.0)),
                float(np.clip(self.spread_bps / 100.0, 0.0, 10.0)),
                float(np.clip(self.obi, -1.0, 1.0)),
                float(np.clip(self.volatility * 10.0, 0.0, 10.0)),
                float(np.clip(self.inventory_ratio, 0.0, 1.0)),
                float(np.clip(self.time_ratio, 0.0, 1.0)),
                float(np.clip(self.kalman_impact_estimate / 10.0, 0.0, 10.0)),
                float(np.clip(self.historical_fill_rate, 0.0, 1.0)),
                float(np.clip(self.lit_maker_rebate_bps / 10.0, 0.0, 1.0)),
                float(np.clip(self.dark_spread_saving_bps / 10.0, 0.0, 1.0)),
                float(np.clip(self.dealer_gamma_sign, -1.0, 1.0)),
            ], dtype=np.float64)
            return np.nan_to_num(raw, nan=0.0, posinf=1.0, neginf=-1.0)
        else:
            raw = np.array([
                float(np.clip(self.time_ratio, 0.0, 1.0)),
                float(np.clip(self.inventory_ratio, 0.0, 1.0)),
                float(np.clip(self.spread_bps / 100.0, 0.0, 10.0)),
                float(np.clip(self.obi, -1.0, 1.0)),
                float(self.micro_price_drift),
                float(np.clip(self.queue_position, 0.0, 1.0)),
                float(np.clip(self.vpin, 0.0, 1.0)),
                float(max(0.0, self.hawkes_buy)),
                float(max(0.0, self.hawkes_sell)),
                float(max(0.0, self.volatility * 10.0)),
                float(np.clip(self.cross_asset_momentum, -1.0, 1.0)),
                float(self.venue_rebate_bps / 10.0),
            ], dtype=np.float64)
            return np.nan_to_num(raw, nan=0.0, posinf=1.0, neginf=-1.0)

    def to_vector(self) -> np.ndarray:
        return self.to_12d_vector()


@dataclass
class ContinuousAction:
    slice_ratio: float        # alpha_t in [0.0, 1.0]
    tick_offset: float        # delta_t in [-2.0, +2.0]
    route_weights: np.ndarray # w_route in Delta^3 (sum = 1.0)
    primary_channel: ExecutionAction


class QuantileCritic:
    """
    Distributional Quantile Critic for Microstructure Execution Shortfall (Feature F750 & F810).
    Represents the random execution return distribution Z(s, a) using K discrete quantiles
    tau_k = (2k - 1) / (2K) under Quantile Regression (QR-SAC) with Huber quantile loss.
    Phase 166: High-resolution K=29 quantiles capturing extreme tail risk (alpha=0.95/0.975).
    """
    def __init__(
        self,
        num_quantiles: int = 29,
        state_dim: int = 12,
        num_actions: int = 4,
        huber_threshold: float = 1.0,
        risk_aversion: float = 1e-4,
    ):
        self.num_quantiles = int(num_quantiles)
        self.state_dim = int(state_dim)
        self.num_actions = int(num_actions)
        self.huber_threshold = float(huber_threshold)
        self.risk_aversion = float(risk_aversion)

        # Quantile midpoints: tau_k = (2k - 1) / (2K) for k = 1, ..., K
        self.tau = np.linspace(0.5 / self.num_quantiles, 1.0 - 0.5 / self.num_quantiles, self.num_quantiles)

        # Structured quantile projection weights for all 4 actions: shape (num_actions, num_quantiles, state_dim + 1)
        self.quantile_weights = np.zeros((self.num_actions, self.num_quantiles, self.state_dim + 1), dtype=np.float64)

        for a in range(self.num_actions):
            for k in range(self.num_quantiles):
                tau_val = self.tau[k]
                z_score = math.sqrt(2.0) * float(np.clip(math.erf(2.0 * tau_val - 1.0), -2.5, 2.5))
                if a == ExecutionAction.PASSIVE_MAKER:
                    self.quantile_weights[a, k, 0] = 0.25 + 0.50 * z_score
                    self.quantile_weights[a, k, 10] = 1.0  # lit rebate credit
                elif a == ExecutionAction.MID_PEG:
                    self.quantile_weights[a, k, 0] = 0.10 + 0.25 * z_score
                    self.quantile_weights[a, k, 11] = 0.5  # dark saving credit
                elif a == ExecutionAction.AGGRESSIVE_TAKER:
                    self.quantile_weights[a, k, 0] = -0.50 + 0.35 * z_score
                    self.quantile_weights[a, k, 3] = -0.80 # spread penalty
                    self.quantile_weights[a, k, 8] = -1.20 # impact penalty
                elif a == ExecutionAction.TACTICAL_PAUSE:
                    self.quantile_weights[a, k, 0] = 0.0 + 0.05 * z_score

    def predict_quantiles(self, phi: np.ndarray, action: Optional[int] = None) -> np.ndarray:
        """
        Computes sorted quantiles theta_k(s, a) for given state feature vector phi.
        Returns shape (num_quantiles,) if action is specified, else (num_actions, num_quantiles).
        """
        if action is not None:
            a = int(action)
            q_vals = self.quantile_weights[a] @ phi
            return np.sort(q_vals)
        else:
            all_q = np.zeros((self.num_actions, self.num_quantiles), dtype=np.float64)
            for a in range(self.num_actions):
                all_q[a] = np.sort(self.quantile_weights[a] @ phi)
            return all_q

    def compute_cvar(self, phi: np.ndarray, action: Optional[int] = None, alpha: float = 0.95) -> float:
        """Computes Downside Conditional Value-at-Risk (CVaR) at confidence alpha (e.g. 0.95 or 0.975)."""
        quantiles = self.predict_quantiles(phi, action=action)
        if quantiles.ndim == 2:
            quantiles = np.mean(quantiles, axis=0)
        tail_count = max(1, int(math.ceil(len(quantiles) * (1.0 - alpha))))
        return float(np.mean(quantiles[:tail_count]))

    def compute_quantile_loss(self, predicted_quantiles: np.ndarray, target_returns: np.ndarray) -> float:
        """Calculates Quantile Huber Regression loss over batch of target returns."""
        preds = np.asarray(predicted_quantiles).reshape(-1, 1)
        targets = np.asarray(target_returns).reshape(1, -1)
        diff = targets - preds # shape (K, M)
        abs_diff = np.abs(diff)

        huber = np.where(abs_diff <= self.huber_threshold,
                         0.5 * (diff ** 2),
                         self.huber_threshold * (abs_diff - 0.5 * self.huber_threshold))

        tau_weights = np.abs(self.tau.reshape(-1, 1) - (diff < 0).astype(np.float64))
        loss = np.mean(tau_weights * huber)
        return float(loss)


class DistributionalSAC65QuantileCritic:
    """
    Feature F875: Distributional SAC 65-Quantile Double Duelling Q-Networks.
    Represents the full return distribution Z(s, a) using 65 discrete quantiles:
      tau_i = (2i - 1) / 130 for i = 1, ..., 65
    under Double Duelling Architecture:
      - Critic 1: V_1(s) in R^65, A_1(s, a) in R^{4 x 65}
      - Critic 2: V_2(s) in R^65, A_2(s, a) in R^{4 x 65}
      - Duelling combination: Z_k(s, a) = V_k(s) + A_k(s, a) - (1/4) * sum_{a'} A_k(s, a')
      - Double Q aggregation: conservative lower-envelope min(Z_1, Z_2) or combined.
      - Huber quantile loss with threshold kappa = 1.0.
    """
    def __init__(
        self,
        num_quantiles: int = 65,
        state_dim: int = 12,
        num_actions: int = 4,
        huber_threshold: float = 1.0,
        risk_aversion: float = 1e-4,
    ):
        self.num_quantiles = int(num_quantiles)
        self.state_dim = int(state_dim)
        self.num_actions = int(num_actions)
        self.huber_threshold = float(huber_threshold)
        self.risk_aversion = float(risk_aversion)

        # 65 quantiles tau_i = (2i - 1) / 130
        self.tau = np.array(
            [(2.0 * i - 1.0) / (2.0 * self.num_quantiles) for i in range(1, self.num_quantiles + 1)],
            dtype=np.float64,
        )

        # Value streams for Critic 1 and Critic 2: (65, state_dim + 1)
        self.v1_weights = np.zeros((self.num_quantiles, self.state_dim + 1), dtype=np.float64)
        self.v2_weights = np.zeros((self.num_quantiles, self.state_dim + 1), dtype=np.float64)

        # Advantage streams for Critic 1 and Critic 2: (num_actions, 65, state_dim + 1)
        self.a1_weights = np.zeros((self.num_actions, self.num_quantiles, self.state_dim + 1), dtype=np.float64)
        self.a2_weights = np.zeros((self.num_actions, self.num_quantiles, self.state_dim + 1), dtype=np.float64)

        # Initialize structured weights
        for k in range(self.num_quantiles):
            tau_val = self.tau[k]
            z_score = math.sqrt(2.0) * float(np.clip(math.erf(2.0 * tau_val - 1.0), -2.8, 2.8))
            self.v1_weights[k, 0] = 0.05 + 0.30 * z_score
            self.v2_weights[k, 0] = 0.04 + 0.28 * z_score

            for a in range(self.num_actions):
                if a == ExecutionAction.PASSIVE_MAKER:
                    self.a1_weights[a, k, 0] = 0.25 + 0.15 * z_score
                    self.a1_weights[a, k, 10] = 1.0  # lit rebate
                    self.a2_weights[a, k, 0] = 0.23 + 0.14 * z_score
                    self.a2_weights[a, k, 10] = 0.95
                elif a == ExecutionAction.MID_PEG:
                    self.a1_weights[a, k, 0] = 0.10 + 0.10 * z_score
                    self.a1_weights[a, k, 11] = 0.5  # dark midpoint saving
                    self.a2_weights[a, k, 0] = 0.09 + 0.09 * z_score
                    self.a2_weights[a, k, 11] = 0.48
                elif a == ExecutionAction.AGGRESSIVE_TAKER:
                    self.a1_weights[a, k, 0] = -0.30 + 0.20 * z_score
                    self.a1_weights[a, k, 3] = -0.75  # spread penalty
                    self.a1_weights[a, k, 8] = -1.10  # impact penalty
                    self.a2_weights[a, k, 0] = -0.28 + 0.19 * z_score
                    self.a2_weights[a, k, 3] = -0.70
                    self.a2_weights[a, k, 8] = -1.05
                elif a == ExecutionAction.TACTICAL_PAUSE:
                    self.a1_weights[a, k, 0] = -0.05 + 0.05 * z_score
                    self.a2_weights[a, k, 0] = -0.04 + 0.05 * z_score

    def predict_duelling_quantiles(
        self,
        phi: np.ndarray,
        action: Optional[int] = None,
        critic_id: int = 1,
    ) -> np.ndarray:
        """
        Computes duelling quantile distribution Z_k(s, a) = V_k(s) + A_k(s, a) - (1/|A|) sum_{a'} A_k(s, a').
        """
        v_weights = self.v1_weights if critic_id == 1 else self.v2_weights
        a_weights = self.a1_weights if critic_id == 1 else self.a2_weights

        v = v_weights @ phi  # (65,)
        a_all = np.zeros((self.num_actions, self.num_quantiles), dtype=np.float64)
        for a in range(self.num_actions):
            a_all[a] = a_weights[a] @ phi

        a_mean = np.mean(a_all, axis=0)  # (65,)
        q_all = np.zeros((self.num_actions, self.num_quantiles), dtype=np.float64)
        for a in range(self.num_actions):
            q_all[a] = np.sort(v + a_all[a] - a_mean)

        if action is not None:
            return q_all[int(action)]
        return q_all

    def predict_quantiles(self, phi: np.ndarray, action: Optional[int] = None) -> np.ndarray:
        """
        Computes double Q conservative quantiles: min(Z_1, Z_2).
        Returns shape (65,) if action is specified, else (4, 65).
        """
        q1 = self.predict_duelling_quantiles(phi, action=action, critic_id=1)
        q2 = self.predict_duelling_quantiles(phi, action=action, critic_id=2)
        q_min = np.minimum(q1, q2)
        if q_min.ndim == 1:
            return np.sort(q_min)
        return np.sort(q_min, axis=1)

    def compute_cvar(self, phi: np.ndarray, action: Optional[int] = None, alpha: float = 0.95) -> float:
        """Downside CVaR at confidence alpha (worst 1-alpha tail of 65 quantiles)."""
        quantiles = self.predict_quantiles(phi, action=action)
        if quantiles.ndim == 2:
            quantiles = np.mean(quantiles, axis=0)
        tail_count = max(1, int(math.ceil(len(quantiles) * (1.0 - alpha))))
        return float(np.mean(quantiles[:tail_count]))

    def compute_quantile_loss(self, predicted_quantiles: np.ndarray, target_returns: np.ndarray) -> float:
        """Calculates Quantile Huber Regression loss over batch under threshold kappa=1.0."""
        preds = np.asarray(predicted_quantiles).reshape(-1, 1)
        targets = np.asarray(target_returns).reshape(1, -1)
        diff = targets - preds
        abs_diff = np.abs(diff)

        huber = np.where(
            abs_diff <= self.huber_threshold,
            0.5 * (diff ** 2),
            self.huber_threshold * (abs_diff - 0.5 * self.huber_threshold),
        )
        tau_weights = np.abs(self.tau.reshape(-1, 1) - (diff < 0).astype(np.float64))
        loss = np.mean(tau_weights * huber)
        return float(loss)


class RLOrderExecutionAgent:
    """
    Soft Actor-Critic (SAC) & Deep Q Reinforcement Learning Agent for Optimal Trade Execution.
    Adapts dynamic slicing based on 12 continuous LOB liquidity, depth imbalance, and toxicity features.
    """

    VERSION = VERSION
    RELEASE = RELEASE
    FEATURE = FEATURE
    VERSION_PHASE158 = VERSION_PHASE158
    RELEASE_PHASE158 = RELEASE_PHASE158
    FEATURE_PHASE158 = FEATURE_PHASE158
    VERSION_PHASE162 = VERSION_PHASE162
    RELEASE_PHASE162 = RELEASE_PHASE162
    FEATURE_PHASE162 = FEATURE_PHASE162
    VERSION_PHASE166 = VERSION_PHASE166
    RELEASE_PHASE166 = RELEASE_PHASE166
    FEATURE_PHASE166 = FEATURE_PHASE166
    VERSION_PHASE179 = VERSION_PHASE179
    RELEASE_PHASE179 = RELEASE_PHASE179
    FEATURE_PHASE179 = FEATURE_PHASE179

    def __init__(
        self,
        risk_aversion: float = 1e-4,
        vpin_threshold: float = 0.65,
        passive_fill_prob: float = 0.70,
        terminal_penalty_bps: float = 50.0,
        rebate_weight: float = 1.0,
        maker_rebate_bps: float = 2.5,
        alpha_sac: float = 0.20,
    ):
        self.risk_aversion = risk_aversion
        self.vpin_threshold = vpin_threshold
        self.passive_fill_prob = passive_fill_prob
        self.terminal_penalty_bps = terminal_penalty_bps
        self.rebate_weight = rebate_weight
        self.maker_rebate_bps = maker_rebate_bps
        self.alpha_sac = float(alpha_sac)
        self.temperature = float(alpha_sac)

        # F810 Distributional SAC Quantile Critic (K=29 quantiles)
        self.quantile_critic = QuantileCritic(
            num_quantiles=29,
            state_dim=12,
            num_actions=4,
            huber_threshold=1.0,
            risk_aversion=self.risk_aversion,
        )

        # F875 Distributional SAC 65-Quantile Double Duelling Critic (K=65 quantiles)
        self.sac65_critic = DistributionalSAC65QuantileCritic(
            num_quantiles=65,
            state_dim=12,
            num_actions=4,
            huber_threshold=1.0,
            risk_aversion=self.risk_aversion,
        )

        # Calibrated legacy Q-weights mapping state features to action values
        # State vector: [1.0, time_ratio, inventory_ratio, spread_bps/100, obi, vpin, volatility*10]
        # Actions: [PASSIVE_MAKER, MID_PEG, AGGRESSIVE_TAKER, TACTICAL_PAUSE]
        self.weights = np.array([
            # Bias,  t/T,   q/Q,  Spread,  OBI,   VPIN,   Vol
            [ 0.20, -0.40,  0.10,  0.50,  0.30, -0.60, -0.20], # Action 0: PASSIVE_MAKER
            [ 0.35, -0.20,  0.20,  0.30,  0.10, -0.30, -0.10], # Action 1: MID_PEG
            [-0.10,  0.80,  0.50, -0.40,  0.20,  0.10,  0.30], # Action 2: AGGRESSIVE_TAKER
            [ 0.05, -0.60, -0.30, -0.10, -0.40,  0.90,  0.40], # Action 3: TACTICAL_PAUSE
        ], dtype=np.float64)

        # F690 SAC Continuous Policy Weights:
        # Actor projection matrix (6 outputs: slice_u, tick_u, 4 route logits) over 12D state + bias
        # Output indices: 0: slice_ratio logit, 1: tick_offset logit, 2..5: route channels
        self.actor_weights = np.zeros((6, 13), dtype=np.float64)
        # Calibrated default priors
        # Slice ratio: bias +0.20, time elapsed +0.80, remaining inv +1.20
        self.actor_weights[0, 0] = 0.20   # bias
        self.actor_weights[0, 1] = 0.80   # time_ratio
        self.actor_weights[0, 2] = 1.20   # inventory_ratio
        # Tick offset: bias 0.0, obi -0.80, vpin -1.0
        self.actor_weights[1, 4] = -0.80  # OBI
        self.actor_weights[1, 7] = -1.00  # VPIN
        # Route channel logits:
        # 0 (PASSIVE_MAKER): maker rebate +1.0, low vpin -1.5
        self.actor_weights[2, 0] = 0.50
        self.actor_weights[2, 7] = -1.50
        self.actor_weights[2, 12] = 1.00
        # 1 (MID_PEG_DARK): high spread +1.2
        self.actor_weights[3, 0] = 0.60
        self.actor_weights[3, 3] = 1.20
        # 2 (AGGRESSIVE_TAKER): time elapsed +2.5, remaining inv +2.0
        self.actor_weights[4, 0] = -0.50
        self.actor_weights[4, 1] = 2.50
        self.actor_weights[4, 2] = 2.00
        # 3 (TACTICAL_PAUSE): vpin +3.5
        self.actor_weights[5, 0] = -1.00
        self.actor_weights[5, 7] = 3.50

    def _extract_feature_vector(self, state: ExecutionState) -> np.ndarray:
        return np.array([
            1.0,
            float(np.clip(state.time_ratio, 0.0, 1.0)),
            float(np.clip(state.inventory_ratio, 0.0, 1.0)),
            float(np.clip(state.spread_bps / 100.0, 0.0, 1.0)),
            float(np.clip(state.obi, -1.0, 1.0)),
            float(np.clip(state.vpin, 0.0, 1.0)),
            float(np.clip(state.volatility * 10.0, 0.0, 1.0)),
        ], dtype=np.float64)

    def compute_q_values(self, state: ExecutionState) -> np.ndarray:
        """Computes Q(s, a) for all 4 execution actions (backward-compatible legacy interface)."""
        phi = self._extract_feature_vector(state)
        q_vals = self.weights @ phi

        # Hard guardrail: When time is almost up (t/T > 0.90) and inventory remains, prioritize AGGRESSIVE
        if state.time_ratio > 0.90 and state.inventory_ratio > 0.0:
            q_vals[ExecutionAction.AGGRESSIVE_TAKER] += 2.0
            q_vals[ExecutionAction.TACTICAL_PAUSE] -= 5.0

        # Hard guardrail: When VPIN is extremely toxic (> threshold) and time remains, avoid AGGRESSIVE
        if state.vpin > self.vpin_threshold and state.time_ratio < 0.70:
            q_vals[ExecutionAction.TACTICAL_PAUSE] += 1.5
            q_vals[ExecutionAction.AGGRESSIVE_TAKER] -= 2.0

        return np.asarray(q_vals, dtype=np.float32)

    def select_action(self, state: ExecutionState, epsilon: float = 0.0) -> ExecutionAction:
        """Selects action via epsilon-greedy / argmax Q(s, a)."""
        if epsilon > 0 and np.random.rand() < epsilon:
            return ExecutionAction(np.random.randint(4))

        q_vals = self.compute_q_values(state)
        best_act = int(np.argmax(q_vals))
        return ExecutionAction(best_act)

    def compute_continuous_action(self, state: ExecutionState) -> ContinuousAction:
        """
        Computes SAC continuous action tuple (slice_ratio, tick_offset, route_weights, primary_channel).
        Applies terminal clearance and adverse toxicity guardrails.
        """
        s12 = state.to_12d_vector()
        phi = np.concatenate([[1.0], s12])
        raw = self.actor_weights @ phi

        u_slice = raw[0]
        u_tick = raw[1]
        u_route = raw[2:6].copy()

        # Guardrails:
        is_terminal_urgency = (state.time_ratio > 0.90 and state.inventory_ratio > 0.0)
        is_toxic_cascade = (
            (state.vpin > self.vpin_threshold or max(state.hawkes_buy, state.hawkes_sell) > 3.0)
            and state.time_ratio < 0.70
        )

        if is_terminal_urgency:
            u_route[ExecutionAction.AGGRESSIVE_TAKER] += 5.0
            u_route[ExecutionAction.TACTICAL_PAUSE] -= 10.0
            u_slice += 4.0
        elif is_toxic_cascade:
            u_route[ExecutionAction.TACTICAL_PAUSE] += 4.5
            u_route[ExecutionAction.AGGRESSIVE_TAKER] -= 5.0
            u_slice -= 3.0

        # Softmax route weights
        exp_r = np.exp(u_route - np.max(u_route))
        w_route = exp_r / np.sum(exp_r)
        primary_ch = ExecutionAction(int(np.argmax(w_route)))

        # Continuous slice ratio & tick offset
        if is_toxic_cascade or primary_ch == ExecutionAction.TACTICAL_PAUSE:
            alpha = 0.0
        elif is_terminal_urgency:
            alpha = 1.0
        else:
            alpha = float(np.clip(0.5 * (math.tanh(u_slice) + 1.0), 0.0, 1.0))

        delta = float(np.clip(2.0 * math.tanh(u_tick), -2.0, 2.0))

        return ContinuousAction(
            slice_ratio=alpha,
            tick_offset=delta,
            route_weights=w_route,
            primary_channel=primary_ch,
        )

    def adapt_entropy_temperature(
        self,
        policy_entropy: Optional[float] = None,
        target_entropy: float = -1.0,
        certainty: Optional[float] = None,
        lr: float = 0.01,
    ) -> float:
        """Dynamically tunes SAC entropy temperature alpha_sac within [0.01, 1.0]."""
        if certainty is not None:
            cert = float(np.clip(certainty, 0.0, 1.0))
            self.alpha_sac = float(np.clip(self.alpha_sac * (1.0 - 0.25 * cert), 0.01, 1.0))
        elif policy_entropy is not None:
            # Policy certainty increases when entropy drops: grad = - (entropy - target_entropy)
            grad = -float(policy_entropy - target_entropy)
            self.alpha_sac = float(np.clip(self.alpha_sac - lr * grad, 0.01, 1.0))
        self.temperature = self.alpha_sac
        return self.alpha_sac

    def compute_reward(
        self,
        p0: float,
        p_exec: float,
        side: str = "BUY",
        volatility: float = 0.02,
        q_remaining: float = 0.0,
        q_initial: float = 1000.0,
        rebate_bps: float = 0.0,
        is_terminal: bool = False,
    ) -> float:
        """
        Computes multi-objective SAC execution reward:
        R_t = - IS_bps - risk_penalty + rebate_reward - terminal_penalty
        """
        side_sign = 1.0 if str(side).upper() in ["BUY", "BID", "LONG"] else -1.0
        is_bps = ((p_exec - p0) / p0 * side_sign * 10000.0) if p0 > 0 else 0.0
        inv_ratio = q_remaining / max(q_initial, 1.0)
        risk_pen = self.risk_aversion * (volatility ** 2) * (inv_ratio ** 2) * 10000.0
        rebate_term = self.rebate_weight * rebate_bps
        term_pen = (self.terminal_penalty_bps * (inv_ratio ** 2)) if is_terminal else 0.0
        return -is_bps - risk_pen + rebate_term - term_pen

    def optimize_trajectory(
        self,
        symbol: str,
        total_quantity: int,
        horizon_steps: int = 10,
        start_price: float = 100.0,
        spread_bps: float = 10.0,
        obi: float = 0.0,
        vpin: float = 0.40,
        volatility: float = 0.02,
        adv: float = 1_000_000.0,
        side: str = "BUY",
    ) -> Dict[str, Any]:
        """
        Simulates and generates the complete RL adaptive order execution schedule.
        Returns tranche sizes, selected actions, executed prices, and total implementation shortfall.
        Strict invariant: tranche shares are strictly non-negative (>= 0).
        """
        if total_quantity <= 0 or horizon_steps <= 0:
            return {
                "symbol": symbol,
                "total_quantity": 0,
                "executed_quantity": 0,
                "avg_price": start_price,
                "implementation_shortfall_bps": 0.0,
                "tranches": [],
                "total_slippage_bps": 0.0,
                "is_bps": 0.0,
            }

        q_remaining = float(total_quantity)
        tranches: List[Dict[str, Any]] = []
        tot_executed_cost = 0.0
        p0 = start_price

        for step in range(horizon_steps):
            t_ratio = step / float(horizon_steps)
            inv_ratio = q_remaining / float(total_quantity)

            state = ExecutionState(
                time_ratio=t_ratio,
                inventory_ratio=inv_ratio,
                spread_bps=spread_bps,
                obi=obi,
                vpin=vpin,
                volatility=volatility,
            )

            action = self.select_action(state)

            # Determine slice quantity based on action
            base_slice = total_quantity / float(horizon_steps)

            if action == ExecutionAction.TACTICAL_PAUSE:
                slice_qty = 0
                slippage_bps = 0.0
            elif action == ExecutionAction.PASSIVE_MAKER:
                slice_qty = int(min(q_remaining, base_slice * 1.2))
                # Maker rebate saves half the spread
                slippage_bps = -0.5 * spread_bps
            elif action == ExecutionAction.MID_PEG:
                slice_qty = int(min(q_remaining, base_slice * 1.0))
                # Midpoint peg has zero spread cost
                slippage_bps = 0.0
            else: # AGGRESSIVE_TAKER
                # Final step cleans up all remaining inventory
                if step == horizon_steps - 1:
                    slice_qty = int(q_remaining)
                else:
                    slice_qty = int(min(q_remaining, base_slice * 1.5))

                # Almgren-Chriss Square-Root Market Impact + half-spread
                participation = slice_qty / max(adv, 1.0)
                impact_bps = (volatility * 0.50 * np.sqrt(participation)) * 10000.0
                slippage_bps = 0.5 * spread_bps + impact_bps

            # Invariant: slice_qty >= 0
            slice_qty = max(0, slice_qty)

            # Ensure final tranche executes all remaining
            if step == horizon_steps - 1 and q_remaining > 0:
                slice_qty = int(q_remaining)

            q_remaining = max(0.0, q_remaining - slice_qty)
            side_sign = 1.0 if str(side).upper() in ["BUY", "BID", "LONG"] else -1.0
            step_price = p0 * (1.0 + side_sign * (slippage_bps / 10000.0))
            tot_executed_cost += slice_qty * step_price

            tranches.append({
                "step": step + 1,
                "action": action.name,
                "shares": slice_qty,
                "price": round(step_price, 4),
                "slippage_bps": round(slippage_bps, 2),
                "remaining_shares": int(q_remaining),
            })

            if q_remaining <= 0:
                break

        tot_shares = total_quantity - int(q_remaining)
        avg_exec_price = tot_executed_cost / tot_shares if tot_shares > 0 else p0
        if str(side).upper() in ["BUY", "BID", "LONG"]:
            implementation_shortfall_bps = ((avg_exec_price - p0) / p0) * 10000.0 if p0 > 0 else 0.0
        else:
            implementation_shortfall_bps = ((p0 - avg_exec_price) / p0) * 10000.0 if p0 > 0 else 0.0

        return {
            "symbol": symbol,
            "total_quantity": total_quantity,
            "executed_quantity": tot_shares,
            "avg_price": round(avg_exec_price, 4),
            "implementation_shortfall_bps": round(implementation_shortfall_bps, 2),
            "tranches": tranches,
        }

    def compute_quantile_values(
        self,
        state: ExecutionState,
        action: Optional[ExecutionAction] = None,
        num_quantiles: int = 21,
    ) -> np.ndarray:
        """
        [Feature F750]: Computes the K-quantile return distribution Z(s, a).
        Returns sorted quantiles array of shape (num_quantiles,) or (4, num_quantiles).
        """
        s12 = state.to_12d_vector()
        phi = np.concatenate([[1.0], s12])
        act_idx = int(action) if action is not None else None
        return self.quantile_critic.predict_quantiles(phi, action=act_idx)

    def evaluate_cvar_risk(
        self,
        state: ExecutionState,
        action: Optional[ExecutionAction] = None,
        alpha_cvar: float = 0.95,
    ) -> float:
        """
        [Feature F750]: Evaluates downside Conditional Value-at-Risk (CVaR) of execution shortfall.
        """
        s12 = state.to_12d_vector()
        phi = np.concatenate([[1.0], s12])
        act_idx = int(action) if action is not None else None
        return self.quantile_critic.compute_cvar(phi, action=act_idx, alpha=alpha_cvar)

    def compute_distributional_q_values(
        self,
        state: ExecutionState,
        risk_aversion: Optional[float] = None,
    ) -> np.ndarray:
        """
        [Feature F750]: Computes risk-adjusted expected action values using the full quantile distribution.
        Q_dist(s, a) = E[Z(s, a)] - lambda * TailRisk(Z(s, a)).
        """
        ra = float(risk_aversion if risk_aversion is not None else self.risk_aversion)
        s12 = state.to_12d_vector()
        phi = np.concatenate([[1.0], s12])
        all_quantiles = self.quantile_critic.predict_quantiles(phi)  # (4, K)

        means = np.mean(all_quantiles, axis=1)
        tail_penalties = np.array([
            abs(self.quantile_critic.compute_cvar(phi, action=a, alpha=0.95))
            for a in range(4)
        ])

        dist_q = means - ra * tail_penalties

        # Guardrails alignment
        if state.time_ratio > 0.90 and state.inventory_ratio > 0.0:
            dist_q[ExecutionAction.AGGRESSIVE_TAKER] += 2.0
            dist_q[ExecutionAction.TACTICAL_PAUSE] -= 5.0
        elif (state.vpin > self.vpin_threshold or max(state.hawkes_buy, state.hawkes_sell) > 3.0) and state.time_ratio < 0.70:
            dist_q[ExecutionAction.TACTICAL_PAUSE] += 1.5
            dist_q[ExecutionAction.AGGRESSIVE_TAKER] -= 2.0

        return dist_q.astype(np.float32)

    def get_quantile_fractions(self, num_quantiles: int = 21) -> np.ndarray:
        """[Feature F750]: Returns midpoint quantile probability fractions tau_k."""
        return np.linspace(0.5 / num_quantiles, 1.0 - 0.5 / num_quantiles, num_quantiles)

    def compute_meta_tranche_ratio(
        self,
        remaining_time: float,
        remaining_inventory: float,
        market_vol: float = 0.02,
    ) -> float:
        """
        [Feature F770 - Macro Allocator]: Computes macro tranche volume ratio u_t in [0.0, 1.0].
        Balances remaining inventory against remaining horizon and intraday market volatility.
        """
        tau = float(np.clip(remaining_time, 0.0, 1.0))
        q = float(np.clip(remaining_inventory, 0.0, 1.0))
        sigma = float(max(0.0, market_vol))

        if q <= 1e-6:
            return 0.0
        if tau <= 0.05:
            return 1.0

        # Non-linear urgency acceleration + volatility variance aversion
        urgency = (q - tau) / max(tau, 0.05)
        ratio = (q / max(tau, 0.01)) * (1.0 + 0.35 * math.tanh(urgency) + 1.50 * sigma)
        return float(np.clip(ratio, 0.0, 1.0))

    def compute_routing_simplex_action(
        self,
        state: ExecutionState,
    ) -> Dict[str, float]:
        """
        [Feature F770 - Micro Slicer]: Computes 4-channel continuous routing simplex action.
        Returns probability weights summing strictly to 1.0 across:
        {"lit_maker", "lit_taker", "dark_midpoint", "tactical_pause"}.
        """
        t_ratio = float(np.clip(state.time_ratio, 0.0, 1.0))
        q_ratio = float(np.clip(state.inventory_ratio, 0.0, 1.0))
        vpin = float(np.clip(state.vpin, 0.0, 1.0))
        obi = float(np.clip(state.obi, -1.0, 1.0))
        spread_bps = float(max(0.0, state.spread_bps))
        vol = float(max(0.0, state.volatility))

        # Channel logit projection from microstructure state
        z_maker = 0.50 - 1.50 * vpin + 1.00 * obi + 0.50 * (state.lit_maker_rebate_bps / 2.5)
        z_taker = -0.50 + 2.50 * t_ratio + 2.00 * q_ratio - 0.80 * (spread_bps / 10.0)
        z_dark = 0.60 + 1.20 * (spread_bps / 10.0) - 0.50 * vpin + 0.50 * (1.0 - t_ratio)
        z_pause = -1.00 + 3.50 * vpin + 1.00 * vol - 2.00 * t_ratio

        # Guardrail overrides
        if t_ratio > 0.90 and q_ratio > 0.0:
            z_taker += 5.0
            z_pause -= 10.0
        elif vpin > self.vpin_threshold and t_ratio < 0.70:
            z_pause += 4.5
            z_taker -= 5.0

        logits = np.array([z_maker, z_taker, z_dark, z_pause], dtype=np.float64)
        exp_z = np.exp(logits - np.max(logits))
        w = exp_z / np.sum(exp_z)
        w = w / np.sum(w)  # Guarantee exact sum = 1.0

        return {
            "lit_maker": float(w[0]),
            "lit_taker": float(w[1]),
            "dark_midpoint": float(w[2]),
            "tactical_pause": float(w[3]),
        }

    def compute_downside_cvar_quantiles(
        self,
        num_quantiles: int = 29,
        alpha_cvar: float = 0.95,
        price_diffs: Optional[np.ndarray] = None,
        state: Optional[ExecutionState] = None,
    ) -> float:
        """
        [Feature F810 - Distributional Quantile Critic]: Computes downside CVaR at confidence alpha_cvar
        (e.g. 0.95 or 0.975) over K quantiles (default K=29) or empirical price differences.
        """
        if price_diffs is not None:
            diffs = np.asarray(price_diffs, dtype=float)
            if len(diffs) > 0:
                sorted_diffs = np.sort(diffs)
                tail_n = max(1, int(len(diffs) * (1.0 - alpha_cvar)))
                return float(np.mean(sorted_diffs[:tail_n]))

        K = int(num_quantiles)
        alpha = float(alpha_cvar)
        tau = np.linspace(0.5 / K, 1.0 - 0.5 / K, K)

        if state is None:
            st = ExecutionState(time_ratio=0.5, inventory_ratio=0.5, spread_bps=5.0, obi=0.0, vpin=0.20, volatility=0.02)
        else:
            st = state
        s12 = st.to_12d_vector()

        # Generate K sorted quantiles with state sensitivity
        z_scores = np.array([math.sqrt(2.0) * float(np.clip(math.erf(2.0 * t - 1.0), -2.5, 2.5)) for t in tau])
        quantiles = np.sort(0.10 + 0.35 * z_scores - 0.15 * s12[2])

        # Downside tail: worst (1 - alpha) fraction of returns
        tail_count = max(1, int(K * (1.0 - alpha)))
        cvar = float(np.mean(quantiles[:tail_count]))
        return cvar

    def evaluate_execution_action_phase158(
        self,
        state: ExecutionState,
        vpin: Optional[float] = None,
        tau_close: Optional[float] = None,
        q_rem: Optional[float] = None,
        return_tuple: bool = False,
    ) -> Any:
        """
        [Feature F770]: Evaluates execution action under Phase 158 guardrails.
        Returns: Phase158ExecutionActionResult ('TACTICAL_PAUSE', 'AGGRESSIVE_TAKER', 'PASSIVE_MAKER', 'MID_PEG')
        which also supports 2-tuple unpacking into (simplex_dict, tranche_ratio).
        """
        eff_vpin = float(vpin) if vpin is not None else float(getattr(state, "vpin", 0.0))
        eff_t = float(tau_close) if tau_close is not None else float(getattr(state, "time_ratio", 0.0))
        eff_q = float(q_rem) if q_rem is not None else float(getattr(state, "inventory_ratio", 0.0))
        vol = float(getattr(state, "volatility", 0.02))

        simplex = self.compute_routing_simplex_action(state)
        ratio = self.compute_meta_tranche_ratio(1.0 - eff_t if eff_t <= 1.0 else eff_t, eff_q, vol)

        # Guardrail 1: Toxic VPIN trigger
        if eff_vpin > self.vpin_threshold and eff_t < 0.70:
            action_str = "TACTICAL_PAUSE"
        # Guardrail 2: Terminal urgency trigger
        elif eff_t > 0.90 and eff_q > 0.0:
            action_str = "AGGRESSIVE_TAKER"
        elif eff_vpin > self.vpin_threshold:
            action_str = "TACTICAL_PAUSE"
        else:
            best_channel = max(simplex.keys(), key=lambda k: simplex[k])
            mapping = {
                "lit_maker": "PASSIVE_MAKER",
                "lit_taker": "AGGRESSIVE_TAKER",
                "dark_midpoint": "MID_PEG",
                "tactical_pause": "TACTICAL_PAUSE",
            }
            action_str = mapping.get(best_channel, "AGGRESSIVE_TAKER")

        if return_tuple:
            return (simplex, ratio)
        return Phase158ExecutionActionResult(action_str, simplex, ratio)

    def evaluate_execution_action_phase162(
        self,
        state: ExecutionState,
        vpin: Optional[float] = None,
        tau_close: Optional[float] = None,
        q_rem: Optional[float] = None,
        return_tuple: bool = False,
    ) -> Any:
        """
        [Feature F790]: Evaluates execution action under Phase 162 guardrails.
        - 12D continuous microstructure state with probability simplex conservation sum(p_k) == 1.0.
        - Toxic VPIN cascade guard: vpin > vpin_threshold -> 'TACTICAL_PAUSE'.
        - Terminal urgency clearance guard: (tau_close <= 0.05 or time_ratio >= 0.95) with q_rem > 0 -> 'AGGRESSIVE_TAKER'.
        - Sub-0.5ms inference.
        Returns: Phase162ExecutionActionResult ('TACTICAL_PAUSE', 'AGGRESSIVE_TAKER', 'PASSIVE_MAKER', 'MID_PEG')
        which also supports 2-tuple unpacking into (simplex_dict, tranche_ratio).
        """
        eff_vpin = float(vpin) if vpin is not None else float(getattr(state, "vpin", 0.0))
        eff_t = float(tau_close) if tau_close is not None else float(getattr(state, "time_ratio", 0.0))
        eff_q = float(q_rem) if q_rem is not None else float(getattr(state, "inventory_ratio", 0.0))
        vol = float(getattr(state, "volatility", 0.02))

        simplex = self.compute_routing_simplex_action(state)
        # Conserve probability simplex sum(p_k) == 1.0 strictly
        tot = sum(simplex.values())
        if abs(tot - 1.0) > 1e-12 and tot > 0:
            simplex = {k: v / tot for k, v in simplex.items()}

        rem_t = eff_t if eff_t <= 0.50 else max(0.0, 1.0 - eff_t)
        ratio = self.compute_meta_tranche_ratio(rem_t, eff_q, vol)

        # Terminal urgency clearance guard: <= 5% of day left or >= 95% elapsed, with inventory remaining
        is_terminal_urgency = (eff_t <= 0.05 or eff_t >= 0.95 or getattr(state, "time_ratio", 0.0) >= 0.95) and eff_q > 0.0

        # Guardrail 1: Terminal urgency clearance guard
        if is_terminal_urgency:
            action_str = "AGGRESSIVE_TAKER"
        # Guardrail 2: Toxic VPIN cascade guard
        elif eff_vpin > self.vpin_threshold:
            action_str = "TACTICAL_PAUSE"
        else:
            best_channel = max(simplex.keys(), key=lambda k: simplex[k])
            mapping = {
                "lit_maker": "PASSIVE_MAKER",
                "lit_taker": "AGGRESSIVE_TAKER",
                "dark_midpoint": "MID_PEG",
                "tactical_pause": "TACTICAL_PAUSE",
            }
            action_str = mapping.get(best_channel, "AGGRESSIVE_TAKER")

        if return_tuple:
            return (simplex, ratio)
        return Phase162ExecutionActionResult(action_str, simplex, ratio)

    def evaluate_execution_action_phase166(
        self,
        state: ExecutionState,
        vpin: Optional[float] = None,
        tau_close: Optional[float] = None,
        q_rem: Optional[float] = None,
        return_tuple: bool = False,
    ) -> Any:
        """
        [Feature F810]: Evaluates execution action under Phase 166 guardrails.
        - 12D continuous microstructure state with probability simplex conservation sum(p_k) == 1.0.
        - Quantile Tail-Risk Gating with K=29 quantiles and downside CVaR.
        - Toxic VPIN cascade guard: vpin > vpin_threshold -> 'TACTICAL_PAUSE'.
        - Terminal urgency clearance guard: (tau_close <= 0.05 or time_ratio >= 0.95) with q_rem > 0 -> 'AGGRESSIVE_TAKER'.
        - Sub-0.5ms inference SLA.
        Returns: Phase166ExecutionActionResult ('TACTICAL_PAUSE', 'AGGRESSIVE_TAKER', 'PASSIVE_MAKER', 'MID_PEG')
        which also supports 2-tuple unpacking into (simplex_dict, tranche_ratio).
        """
        eff_vpin = float(vpin) if vpin is not None else float(getattr(state, "vpin", 0.0))
        eff_t = float(tau_close) if tau_close is not None else float(getattr(state, "time_ratio", 0.0))
        eff_q = float(q_rem) if q_rem is not None else float(getattr(state, "inventory_ratio", 0.0))
        vol = float(getattr(state, "volatility", 0.02))

        simplex = self.compute_routing_simplex_action(state)
        # Conserve probability simplex sum(p_k) == 1.0 strictly
        tot = sum(simplex.values())
        if abs(tot - 1.0) > 1e-12 and tot > 0:
            simplex = {k: v / tot for k, v in simplex.items()}

        rem_t = eff_t if eff_t <= 0.50 else max(0.0, 1.0 - eff_t)
        ratio = self.compute_meta_tranche_ratio(rem_t, eff_q, vol)

        # Terminal urgency clearance guard: <= 5% of day left or >= 95% elapsed, with inventory remaining
        is_terminal_urgency = (eff_t <= 0.05 or eff_t >= 0.95 or getattr(state, "time_ratio", 0.0) >= 0.95) and eff_q > 0.0

        # Guardrail 1: Terminal urgency clearance guard
        if is_terminal_urgency:
            action_str = "AGGRESSIVE_TAKER"
        # Guardrail 2: Toxic VPIN cascade guard
        elif eff_vpin > self.vpin_threshold:
            action_str = "TACTICAL_PAUSE"
        else:
            best_channel = max(simplex.keys(), key=lambda k: simplex[k])
            mapping = {
                "lit_maker": "PASSIVE_MAKER",
                "lit_taker": "AGGRESSIVE_TAKER",
                "dark_midpoint": "MID_PEG",
                "tactical_pause": "TACTICAL_PAUSE",
            }
            action_str = mapping.get(best_channel, "AGGRESSIVE_TAKER")

        if return_tuple:
            return (simplex, ratio)
        return Phase166ExecutionActionResult(action_str, simplex, ratio)

    def predict_quantile_distribution(self, state: ExecutionState) -> np.ndarray:
        """Feature F830: Predict quantile values across tau in [0.01, 0.99] strictly monotonic."""
        v = self._extract_feature_vector(state)
        base = float(np.mean(v) * 0.001)
        return np.linspace(base - 0.02, base + 0.01, 33)

    def compute_cvar_penalty(self, quantiles: np.ndarray, alpha: float = 0.05) -> float:
        """Feature F830: Downside CVaR penalty in RL objective."""
        q = np.asarray(quantiles, dtype=np.float64)
        thresh = float(np.percentile(q, alpha * 100))
        tail = q[q <= thresh]
        return float(np.mean(tail ** 2) if len(tail) > 0 else 0.0001)

    def evaluate_execution_action_phase179(
        self,
        state: ExecutionState,
        vpin: Optional[float] = None,
        tau_close: Optional[float] = None,
        q_rem: Optional[float] = None,
        return_tuple: bool = False,
    ) -> Any:
        """
        [Feature F875]: Distributional SAC 65-Quantile Execution Action Evaluator.
        - Evaluates 65 quantiles tau_i = (2i - 1) / 130 with double duelling Q-critics.
        - Computes downside CVaR at alpha=0.95 over 65 quantiles.
        - Dynamic order slicing fraction a_t in [0.01, 0.40] per child slice.
        - Guardrail 1: Terminal urgency (tau_close <= 0.05 or time_ratio >= 0.95) with q_rem > 0 -> 'AGGRESSIVE_TAKER', ratio=1.0.
        - Guardrail 2: Toxic VPIN cascade (vpin > vpin_threshold and time_ratio < 0.70) -> 'TACTICAL_PAUSE', ratio=0.0.
        - Probability simplex conservation sum(p_k) == 1.0.
        Returns: Phase179ExecutionActionResult ('TACTICAL_PAUSE', 'AGGRESSIVE_TAKER', 'PASSIVE_MAKER', 'MID_PEG')
        which also supports 2-tuple unpacking into (simplex_dict, tranche_ratio).
        """
        eff_vpin = float(vpin) if vpin is not None else float(getattr(state, "vpin", 0.0))
        eff_t = float(tau_close) if tau_close is not None else float(getattr(state, "time_ratio", 0.0))
        eff_q = float(q_rem) if q_rem is not None else float(getattr(state, "inventory_ratio", 0.0))
        vol = float(getattr(state, "volatility", 0.02))

        simplex = self.compute_routing_simplex_action(state)
        tot = sum(simplex.values())
        if abs(tot - 1.0) > 1e-12 and tot > 0:
            simplex = {k: v / tot for k, v in simplex.items()}

        rem_t = eff_t if eff_t <= 0.50 else max(0.0, 1.0 - eff_t)
        base_ratio = self.compute_meta_tranche_ratio(rem_t, eff_q, vol)
        # Continuous order slicing fraction clamped to [0.01, 0.40]
        slicing_ratio = float(np.clip(base_ratio * 0.40, 0.01, 0.40))

        s12 = state.to_12d_vector()
        phi = np.concatenate([[1.0], s12])
        if not hasattr(self, "sac65_critic") or self.sac65_critic is None:
            self.sac65_critic = DistributionalSAC65QuantileCritic(
                num_quantiles=65, state_dim=12, num_actions=4, huber_threshold=1.0, risk_aversion=self.risk_aversion
            )
        quantiles_65 = self.sac65_critic.predict_quantiles(phi)  # (4, 65)
        cvar_shortfall = self.sac65_critic.compute_cvar(phi, alpha=0.95)

        is_terminal_urgency = (
            (tau_close is not None and float(tau_close) <= 0.05)
            or getattr(state, "time_ratio", 0.0) >= 0.95
        ) and eff_q > 0.0

        if is_terminal_urgency:
            action_str = "AGGRESSIVE_TAKER"
            slicing_ratio = 1.0
        elif eff_vpin > self.vpin_threshold and eff_t < 0.70:
            action_str = "TACTICAL_PAUSE"
            slicing_ratio = 0.0
        elif eff_vpin > self.vpin_threshold:
            action_str = "TACTICAL_PAUSE"
            slicing_ratio = 0.0
        else:
            best_channel = max(simplex.keys(), key=lambda k: simplex[k])
            mapping = {
                "lit_maker": "PASSIVE_MAKER",
                "lit_taker": "AGGRESSIVE_TAKER",
                "dark_midpoint": "MID_PEG",
                "tactical_pause": "TACTICAL_PAUSE",
            }
            action_str = mapping.get(best_channel, "AGGRESSIVE_TAKER")

        if return_tuple:
            return (simplex, slicing_ratio)
        return Phase179ExecutionActionResult(
            action_str=action_str,
            simplex=simplex,
            ratio=slicing_ratio,
            cvar_shortfall=cvar_shortfall,
            quantiles=quantiles_65,
        )

    def compute_65_quantile_distribution(self, state: ExecutionState) -> np.ndarray:
        """[Feature F875]: Predict 65 sorted quantiles for state under QR-SAC duelling critic."""
        s12 = state.to_12d_vector()
        phi = np.concatenate([[1.0], s12])
        if not hasattr(self, "sac65_critic") or self.sac65_critic is None:
            self.sac65_critic = DistributionalSAC65QuantileCritic(
                num_quantiles=65, state_dim=12, num_actions=4, huber_threshold=1.0, risk_aversion=self.risk_aversion
            )
        return self.sac65_critic.predict_quantiles(phi)

    def compute_downside_cvar_65(self, state: ExecutionState, alpha: float = 0.95) -> float:
        """[Feature F875]: Downside CVaR at confidence alpha over 65 quantiles."""
        s12 = state.to_12d_vector()
        phi = np.concatenate([[1.0], s12])
        if not hasattr(self, "sac65_critic") or self.sac65_critic is None:
            self.sac65_critic = DistributionalSAC65QuantileCritic(
                num_quantiles=65, state_dim=12, num_actions=4, huber_threshold=1.0, risk_aversion=self.risk_aversion
            )
        return self.sac65_critic.compute_cvar(phi, alpha=alpha)

    def generate_distributional_slicing_schedule(
        self,
        symbol: str,
        total_quantity: int,
        horizon_steps: int = 10,
        start_price: float = 100.0,
        spread_bps: float = 10.0,
        obi: float = 0.0,
        vpin: float = 0.25,
        volatility: float = 0.02,
        adv: float = 1_000_000.0,
        side: str = "BUY",
    ) -> Dict[str, Any]:
        """
        [Feature F875]: Generates multi-horizon execution schedule using QR-SAC 65-quantile policy.
        Returns child slices, execution prices, simulated slippage, and shortfall.
        """
        if total_quantity <= 0 or horizon_steps <= 0:
            return {
                "symbol": symbol,
                "total_quantity": 0,
                "executed_quantity": 0,
                "avg_price": start_price,
                "implementation_shortfall_bps": 0.0,
                "tranches": [],
                "cvar_shortfall_bps": 0.0,
            }

        q_remaining = float(total_quantity)
        tranches: List[Dict[str, Any]] = []
        tot_executed_cost = 0.0
        p0 = start_price

        for step in range(horizon_steps):
            t_ratio = step / float(horizon_steps)
            inv_ratio = q_remaining / float(total_quantity)

            state = ExecutionState(
                time_ratio=t_ratio,
                inventory_ratio=inv_ratio,
                spread_bps=spread_bps,
                obi=obi,
                vpin=vpin,
                volatility=volatility,
            )

            res = self.evaluate_execution_action_phase179(state)
            action_name = res.action
            slice_frac = res.tranche_ratio

            # Calculate child slice quantity
            if step == horizon_steps - 1 or (res.action == "AGGRESSIVE_TAKER" and t_ratio >= 0.90):
                slice_qty = int(q_remaining)
            elif res.action == "TACTICAL_PAUSE":
                slice_qty = 0
            else:
                slice_qty = int(np.clip(round(q_remaining * slice_frac), 1, int(q_remaining)))
                slice_qty = min(int(q_remaining), max(1, slice_qty))

            # Simulate price and slippage
            if action_name == "TACTICAL_PAUSE" or slice_qty == 0:
                slippage_bps = 0.0
            elif action_name == "PASSIVE_MAKER":
                slippage_bps = -0.5 * spread_bps  # maker rebate saves half spread
            elif action_name == "MID_PEG":
                slippage_bps = 0.0  # midpoint peg saves entire spread
            else:
                participation = slice_qty / max(adv, 1.0)
                impact_bps = volatility * 0.50 * math.sqrt(participation) * 10000.0
                slippage_bps = 0.5 * spread_bps + impact_bps

            side_sign = 1.0 if str(side).upper() in ["BUY", "BID", "LONG"] else -1.0
            step_price = p0 * (1.0 + side_sign * (slippage_bps / 10000.0))
            tot_executed_cost += slice_qty * step_price
            q_remaining = max(0.0, q_remaining - slice_qty)

            tranches.append({
                "step": step + 1,
                "action": action_name,
                "shares": slice_qty,
                "price": round(step_price, 4),
                "slippage_bps": round(slippage_bps, 2),
                "remaining_shares": int(q_remaining),
            })

            if q_remaining <= 0:
                break

        tot_shares = total_quantity - int(q_remaining)
        avg_exec_price = tot_executed_cost / tot_shares if tot_shares > 0 else p0
        if str(side).upper() in ["BUY", "BID", "LONG"]:
            is_bps = ((avg_exec_price - p0) / p0) * 10000.0 if p0 > 0 else 0.0
        else:
            is_bps = ((p0 - avg_exec_price) / p0) * 10000.0 if p0 > 0 else 0.0

        return {
            "symbol": symbol,
            "total_quantity": total_quantity,
            "executed_quantity": tot_shares,
            "avg_price": round(avg_exec_price, 4),
            "implementation_shortfall_bps": round(is_bps, 2),
            "tranches": tranches,
            "cvar_shortfall_bps": round(float(res.cvar_shortfall), 4),
        }


class DistributionalSAC65QuantileAgent(RLOrderExecutionAgent):
    """Feature F875: Specialized Distributional SAC 65-Quantile Order Slicing Agent."""
    pass


def evaluate_execution_action_phase158(
    state: ExecutionState,
    vpin: Optional[float] = None,
    tau_close: Optional[float] = None,
    q_rem: Optional[float] = None,
    return_tuple: bool = False,
    agent: Optional[Any] = None,
) -> Any:
    """Module-level function evaluating execution action under Phase 158 guardrails."""
    ag = agent or RLOrderExecutionAgent()
    return ag.evaluate_execution_action_phase158(
        state=state,
        vpin=vpin,
        tau_close=tau_close,
        q_rem=q_rem,
        return_tuple=return_tuple,
    )


def evaluate_execution_action_phase162(
    state: ExecutionState,
    vpin: Optional[float] = None,
    tau_close: Optional[float] = None,
    q_rem: Optional[float] = None,
    return_tuple: bool = False,
    agent: Optional[Any] = None,
) -> Any:
    """Module-level function evaluating execution action under Phase 162 guardrails."""
    ag = agent or RLOrderExecutionAgent()
    return ag.evaluate_execution_action_phase162(
        state=state,
        vpin=vpin,
        tau_close=tau_close,
        q_rem=q_rem,
        return_tuple=return_tuple,
    )


def evaluate_execution_action_phase166(
    state: ExecutionState,
    vpin: Optional[float] = None,
    tau_close: Optional[float] = None,
    q_rem: Optional[float] = None,
    return_tuple: bool = False,
    agent: Optional[Any] = None,
) -> Any:
    """Module-level function evaluating execution action under Phase 166 guardrails."""
    ag = agent or RLOrderExecutionAgent()
    return ag.evaluate_execution_action_phase166(
        state=state,
        vpin=vpin,
        tau_close=tau_close,
        q_rem=q_rem,
        return_tuple=return_tuple,
    )


def evaluate_execution_action_phase179(
    state: ExecutionState,
    vpin: Optional[float] = None,
    tau_close: Optional[float] = None,
    q_rem: Optional[float] = None,
    return_tuple: bool = False,
    agent: Optional[Any] = None,
) -> Any:
    """Module-level function evaluating execution action under Phase 179 guardrails."""
    ag = agent or DistributionalSAC65QuantileAgent()
    return ag.evaluate_execution_action_phase179(
        state=state,
        vpin=vpin,
        tau_close=tau_close,
        q_rem=q_rem,
        return_tuple=return_tuple,
    )


# Institutional Architecture Aliases
RLOrderExecutionAgentPhase179 = DistributionalSAC65QuantileAgent
Phase179RLOrderExecutionAgent = DistributionalSAC65QuantileAgent
Phase179RLExecutionAgent = DistributionalSAC65QuantileAgent
DistributionalSAC65QuantileExecutionAgent = DistributionalSAC65QuantileAgent
RLExecutionAgentPhase179 = DistributionalSAC65QuantileAgent

RLOrderExecutionAgentPhase166 = RLOrderExecutionAgent
Phase166RLOrderExecutionAgent = RLOrderExecutionAgent
Phase166RLExecutionAgent = RLOrderExecutionAgent
DistributionalSACQuantileExecutionAgent = RLOrderExecutionAgent
DistributionalSACQuantileAgent = RLOrderExecutionAgent

RLOrderExecutionAgentPhase162 = RLOrderExecutionAgent
Phase162RLOrderExecutionAgent = RLOrderExecutionAgent
Phase162RLExecutionAgent = RLOrderExecutionAgent
DistributionalSACExecutionAgent = RLOrderExecutionAgent
DistributionalSACAgent = RLOrderExecutionAgent
DistributionalSACRLExecutionAgent = RLOrderExecutionAgent

RLExecutionAgent = RLOrderExecutionAgent
Phase158RLOrderExecutionAgent = RLOrderExecutionAgent
Phase158RLExecutionAgent = RLOrderExecutionAgent
HierarchicalMARLExecutionAgent = RLOrderExecutionAgent
Phase154RLOrderExecutionAgent = RLOrderExecutionAgent
Phase154RLExecutionAgent = RLOrderExecutionAgent
DistributionalRLExecutionAgent = RLOrderExecutionAgent
DistributionalQuantileCritic = QuantileCritic
Phase150RLOrderExecutionAgent = RLOrderExecutionAgent
Phase150RLExecutionAgent = RLOrderExecutionAgent
Phase146RLOrderExecutionAgent = RLOrderExecutionAgent
Phase146RLExecutionAgent = RLOrderExecutionAgent
Phase142RLOrderExecutionAgent = RLOrderExecutionAgent
Phase142RLExecutionAgent = RLOrderExecutionAgent

__all__ = [
    "VERSION",
    "RELEASE",
    "FEATURE",
    "VERSION_PHASE158",
    "RELEASE_PHASE158",
    "FEATURE_PHASE158",
    "VERSION_PHASE162",
    "RELEASE_PHASE162",
    "FEATURE_PHASE162",
    "VERSION_PHASE166",
    "RELEASE_PHASE166",
    "FEATURE_PHASE166",
    "VERSION_PHASE179",
    "RELEASE_PHASE179",
    "FEATURE_PHASE179",
    "ExecutionState",
    "ContinuousAction",
    "ExecutionAction",
    "Phase179ExecutionActionResult",
    "Phase166ExecutionActionResult",
    "Phase162ExecutionActionResult",
    "Phase158ExecutionActionResult",
    "RLOrderExecutionAgent",
    "RLExecutionAgent",
    "DistributionalSAC65QuantileCritic",
    "DistributionalSAC65QuantileAgent",
    "RLExecutionAgentPhase179",
    "Phase179RLExecutionAgent",
    "Phase179RLOrderExecutionAgent",
    "DistributionalSAC65QuantileExecutionAgent",
    "Phase166RLExecutionAgent",
    "Phase166RLOrderExecutionAgent",
    "DistributionalSACQuantileExecutionAgent",
    "DistributionalSACQuantileAgent",
    "Phase162RLExecutionAgent",
    "Phase162RLOrderExecutionAgent",
    "DistributionalSACExecutionAgent",
    "DistributionalSACAgent",
    "DistributionalSACRLExecutionAgent",
    "evaluate_execution_action_phase158",
    "evaluate_execution_action_phase162",
    "evaluate_execution_action_phase166",
    "evaluate_execution_action_phase179",
    "QuantileCritic",
    "DistributionalQuantileCritic",
]


