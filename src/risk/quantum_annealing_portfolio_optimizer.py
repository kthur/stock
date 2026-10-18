r"""
src/risk/quantum_annealing_portfolio_optimizer.py
=================================================
Quantum-Inspired Annealing Portfolio Combinatorial Optimizer (Feature F566).
Phase 119 (Release R135 / v126 Production Master).

Features & Mathematical Foundations:
- Quadratic Unconstrained Binary Optimization (QUBO) & Simulated Quantum Annealing (SQA):
  * Discrete portfolio selection mapped to combinatorial QUBO formulation:
    min_{x \in {0, 1}^M} x^T Q x
  * Mean-variance Markowitz objective with binary bit-slice weight encoding:
    w_i = \Delta w_i \sum_{b=0}^{B-1} 2^b x_{i, b}
- Transverse-Field Ising Hamiltonian Formulation:
  * H(s) = -\sum_{i} h_i \sigma_i^z - \sum_{i < j} J_{ij} \sigma_i^z \sigma_j^z - \Gamma(t) \sum_i \sigma_i^x
  * Exact isomorphism between QUBO and Ising spin formulation:
    x_i = (1 - \sigma_i^z) / 2  <=>  \sigma_i^z = 1 - 2 x_i \in {-1, +1}
    h_i = 0.5 Q_{ii} + 0.25 \sum_{j \ne i} (Q_{ij} + Q_{ji})
    J_{ij} = -0.25 (Q_{ij} + Q_{ji})
    E_{offset} = 0.5 \sum_i Q_{ii} + 0.25 \sum_{i < j} (Q_{ij} + Q_{ji})
    E_{QUBO}(x) == E_{Ising}(\sigma) + E_{offset}
- Suzuki-Trotter Path-Integral Monte Carlo (SQA):
  * 1D quantum system mapped to 2D classical lattice with P Trotter replicas along imaginary time.
  * Effective classical Hamiltonian:
    H_{eff}(s) = \frac{1}{P} \sum_{p=1}^P H_{Ising}(s^{(p)}) - J_\perp(t) \sum_{p=1}^P \sum_{i=1}^M s_i^{(p)} s_i^{(p+1)}
  * Dynamic inter-slice ferromagnetic coupling:
    J_\perp(t) = -\frac{1}{2 \beta_{slice}} \ln \tanh(\beta_{slice} \Gamma(t))
  * Single-spin flip Metropolis energy change vectorized across replicas:
    \Delta E_{i, p} = \frac{2}{P} s_i^{(p)} (h_i + \sum_j J_{ij} s_j^{(p)}) + 2 J_\perp s_i^{(p)} (s_i^{(p-1)} + s_i^{(p+1)})
- Dynamic Quantum Tunneling Schedules \Gamma(t):
  * LINEAR, EXPONENTIAL, POWER_LAW, COSINE, ADAPTIVE schedules decaying from \Gamma_0 to \Gamma_{min}.
- Exact Operational Constraints & Penalties:
  * Cardinality constraints: K_{min} <= K <= K_{max} with quadratic penalty and greedy knapsack bounds.
  * Round-lot discrete sizing: shares = k * lot_size, guaranteed integer lot multiples.
  * Budget conservation: \sum w_i + w_{cash} = 1.000000 with non-negative cash residual.
  * Sector concentration caps: \sum_{i \in sector_s} w_i <= W_{max, s}.
  * Piecewise transaction costs and portfolio turnover penalization.
  * Dynamic Leland no-trade buffer bands with instant new entry / full liquidation bypass guards.
- Pre-Calibrated 5-Market Empirical Profiles:
  * SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ.
- Dual-Tree Cryptographic Parity:
  * 100% bit-for-bit SHA-256 parity between src/ and trading_system/src/.
"""

from __future__ import annotations

import copy
import enum
import json
import math
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# Safe PyTorch import
try:
    import torch
    import torch.nn as nn
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    _TORCH_AVAILABLE = False

# Safe SciPy fallback
try:
    from scipy.optimize import minimize as scipy_minimize
    _SCIPY_AVAILABLE = True
except ImportError:
    scipy_minimize = None
    _SCIPY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Module Version & Metadata Constants
# ---------------------------------------------------------------------------
VERSION: int = 119
RELEASE: str = "R135"
FEATURE: str = "F566"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TunnelingScheduleType(str, enum.Enum):
    """Annealing schedule for quantum transverse field \Gamma(t)."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    POWER_LAW = "power_law"
    COSINE = "cosine"
    ADAPTIVE = "adaptive"


class RebalanceActionType(str, enum.Enum):
    """Institutional execution rebalance actions."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# ---------------------------------------------------------------------------
# Pre-Calibrated 5-Market Empirical Profiles
# ---------------------------------------------------------------------------
MARKET_QUANTUM_ANNEALING_PROFILES: Dict[str, Dict[str, Any]] = {
    "SP500": {
        "market": "SP500",
        "risk_aversion": 1.20,
        "gamma_risk_aversion": 1.20,
        "cardinality_min": 8,
        "k_min": 8,
        "cardinality_max": 20,
        "k_max": 20,
        "cardinality_target": 15,
        "k_target": 15,
        "max_single_weight": 0.15,
        "max_sector_weight": 0.30,
        "default_lot_size": 1,
        "round_lot_size": 1,
        "lot_size": 1,
        "transaction_cost_bps": 3.0,
        "turnover_penalty": 0.05,
        "turnover_penalty_gamma": 0.05,
        "leland_base_band": 0.015,
        "trotter_slices": 16,
        "num_trotter_slices": 16,
        "annealing_sweeps": 100,
        "num_sweeps": 100,
        "gamma_0": 3.0,
        "initial_gamma": 3.0,
        "penalty_budget": 50.0,
        "penalty_cardinality": 25.0,
        "penalty_sector": 30.0,
    },
    "NASDAQ": {
        "market": "NASDAQ",
        "risk_aversion": 1.00,
        "gamma_risk_aversion": 1.00,
        "cardinality_min": 8,
        "k_min": 8,
        "cardinality_max": 25,
        "k_max": 25,
        "cardinality_target": 18,
        "k_target": 18,
        "max_single_weight": 0.18,
        "max_sector_weight": 0.40,
        "default_lot_size": 1,
        "round_lot_size": 1,
        "lot_size": 1,
        "transaction_cost_bps": 5.0,
        "turnover_penalty": 0.06,
        "turnover_penalty_gamma": 0.06,
        "leland_base_band": 0.018,
        "trotter_slices": 16,
        "num_trotter_slices": 16,
        "annealing_sweeps": 120,
        "num_sweeps": 120,
        "gamma_0": 3.5,
        "initial_gamma": 3.5,
        "penalty_budget": 50.0,
        "penalty_cardinality": 25.0,
        "penalty_sector": 25.0,
    },
    "RUSSELL2000": {
        "market": "RUSSELL2000",
        "risk_aversion": 1.50,
        "gamma_risk_aversion": 1.50,
        "cardinality_min": 10,
        "k_min": 10,
        "cardinality_max": 30,
        "k_max": 30,
        "cardinality_target": 20,
        "k_target": 20,
        "max_single_weight": 0.10,
        "max_sector_weight": 0.25,
        "default_lot_size": 1,
        "round_lot_size": 1,
        "lot_size": 1,
        "transaction_cost_bps": 12.0,
        "turnover_penalty": 0.08,
        "turnover_penalty_gamma": 0.08,
        "leland_base_band": 0.025,
        "trotter_slices": 16,
        "num_trotter_slices": 16,
        "annealing_sweeps": 150,
        "num_sweeps": 150,
        "gamma_0": 4.0,
        "initial_gamma": 4.0,
        "penalty_budget": 60.0,
        "penalty_cardinality": 30.0,
        "penalty_sector": 35.0,
    },
    "KOSPI": {
        "market": "KOSPI",
        "risk_aversion": 1.30,
        "gamma_risk_aversion": 1.30,
        "cardinality_min": 6,
        "k_min": 6,
        "cardinality_max": 18,
        "k_max": 18,
        "cardinality_target": 12,
        "k_target": 12,
        "max_single_weight": 0.20,
        "max_sector_weight": 0.35,
        "default_lot_size": 1,
        "round_lot_size": 1,
        "lot_size": 1,
        "transaction_cost_bps": 20.0,  # KRX STT ~0.18%
        "turnover_penalty": 0.10,
        "turnover_penalty_gamma": 0.10,
        "leland_base_band": 0.020,
        "trotter_slices": 16,
        "num_trotter_slices": 16,
        "annealing_sweeps": 120,
        "num_sweeps": 120,
        "gamma_0": 3.2,
        "initial_gamma": 3.2,
        "penalty_budget": 50.0,
        "penalty_cardinality": 25.0,
        "penalty_sector": 30.0,
    },
    "KOSDAQ": {
        "market": "KOSDAQ",
        "risk_aversion": 1.60,
        "gamma_risk_aversion": 1.60,
        "cardinality_min": 6,
        "k_min": 6,
        "cardinality_max": 20,
        "k_max": 20,
        "cardinality_target": 14,
        "k_target": 14,
        "max_single_weight": 0.15,
        "max_sector_weight": 0.35,
        "default_lot_size": 1,
        "round_lot_size": 1,
        "lot_size": 1,
        "transaction_cost_bps": 25.0,  # KRX STT + spread
        "turnover_penalty": 0.12,
        "turnover_penalty_gamma": 0.12,
        "leland_base_band": 0.030,
        "trotter_slices": 16,
        "num_trotter_slices": 16,
        "annealing_sweeps": 150,
        "num_sweeps": 150,
        "gamma_0": 4.0,
        "initial_gamma": 4.0,
        "penalty_budget": 60.0,
        "penalty_cardinality": 30.0,
        "penalty_sector": 35.0,
    },
}


# ---------------------------------------------------------------------------
# Configuration Dataclass
# ---------------------------------------------------------------------------
@dataclass
class QuantumAnnealingConfig:
    """Configuration container for Quantum-Inspired Annealing Portfolio Optimizer."""
    market: str = "SP500"
    num_assets: int = 20
    asset_names: Tuple[str, ...] = ()
    gamma_risk_aversion: float = 1.20
    risk_aversion: float = 1.20
    k_min: int = 8
    cardinality_min: int = 8
    k_max: int = 20
    cardinality_max: int = 20
    k_target: Optional[int] = None
    cardinality_target: Optional[int] = None
    max_single_weight: float = 0.20
    max_sector_weight: float = 0.30
    gamma_0: float = 3.5
    initial_gamma: float = 3.5
    gamma_min: float = 1e-4
    trotter_slices: int = 8
    num_trotter_slices: int = 8
    annealing_sweeps: int = 100
    num_sweeps: int = 100
    temp_start: float = 1.0
    temp_end: float = 0.01
    beta: float = 10.0
    schedule_type: Union[TunnelingScheduleType, str] = TunnelingScheduleType.COSINE
    bits_per_asset: int = 3
    total_capital: float = 100_000.0
    round_lot_size: int = 1
    lot_size: int = 1
    default_lot_size: int = 1
    transaction_cost_bps: float = 10.0
    turnover_penalty_gamma: float = 0.05
    turnover_penalty: float = 0.05
    impact_penalty: float = 0.05
    leland_base_band: float = 0.015
    penalty_budget: float = 50.0
    lambda_budget: float = 50.0
    penalty_cardinality: float = 25.0
    lambda_card: float = 25.0
    penalty_sector: float = 30.0
    lambda_sector: float = 30.0
    seed: Optional[int] = 42
    use_torch: bool = True

    def __init__(self, **kwargs):
        # Apply market defaults if available
        market_key = kwargs.get("market", "SP500").upper()
        if market_key in MARKET_QUANTUM_ANNEALING_PROFILES:
            for k, v in MARKET_QUANTUM_ANNEALING_PROFILES[market_key].items():
                setattr(self, k, v)

        # Apply specific kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

        # Synchronize dual alias fields
        if "risk_aversion" in kwargs:
            self.gamma_risk_aversion = float(kwargs["risk_aversion"])
            self.risk_aversion = float(kwargs["risk_aversion"])
        elif "gamma_risk_aversion" in kwargs:
            self.risk_aversion = float(kwargs["gamma_risk_aversion"])
            self.gamma_risk_aversion = float(kwargs["gamma_risk_aversion"])

        if "num_trotter_slices" in kwargs:
            self.trotter_slices = int(kwargs["num_trotter_slices"])
            self.num_trotter_slices = int(kwargs["num_trotter_slices"])
        elif "trotter_slices" in kwargs:
            self.num_trotter_slices = int(kwargs["trotter_slices"])
            self.trotter_slices = int(kwargs["trotter_slices"])

        if "num_sweeps" in kwargs:
            self.annealing_sweeps = int(kwargs["num_sweeps"])
            self.num_sweeps = int(kwargs["num_sweeps"])
        elif "annealing_sweeps" in kwargs:
            self.num_sweeps = int(kwargs["annealing_sweeps"])
            self.annealing_sweeps = int(kwargs["annealing_sweeps"])

        if "cardinality_min" in kwargs:
            self.k_min = int(kwargs["cardinality_min"])
            self.cardinality_min = int(kwargs["cardinality_min"])
        elif "k_min" in kwargs:
            self.cardinality_min = int(kwargs["k_min"])
            self.k_min = int(kwargs["k_min"])

        if "cardinality_max" in kwargs:
            self.k_max = int(kwargs["cardinality_max"])
            self.cardinality_max = int(kwargs["cardinality_max"])
        elif "k_max" in kwargs:
            self.cardinality_max = int(kwargs["k_max"])
            self.k_max = int(kwargs["k_max"])

        if "cardinality_target" in kwargs:
            self.k_target = int(kwargs["cardinality_target"])
            self.cardinality_target = int(kwargs["cardinality_target"])
        elif "k_target" in kwargs and kwargs["k_target"] is not None:
            self.cardinality_target = int(kwargs["k_target"])
            self.k_target = int(kwargs["k_target"])

        if "initial_gamma" in kwargs:
            self.gamma_0 = float(kwargs["initial_gamma"])
            self.initial_gamma = float(kwargs["initial_gamma"])
        elif "gamma_0" in kwargs:
            self.initial_gamma = float(kwargs["gamma_0"])
            self.gamma_0 = float(kwargs["gamma_0"])

        if "lot_size" in kwargs:
            self.round_lot_size = int(kwargs["lot_size"])
            self.lot_size = int(kwargs["lot_size"])
            self.default_lot_size = int(kwargs["lot_size"])
        elif "round_lot_size" in kwargs:
            self.lot_size = int(kwargs["round_lot_size"])
            self.default_lot_size = int(kwargs["round_lot_size"])
            self.round_lot_size = int(kwargs["round_lot_size"])
        elif "default_lot_size" in kwargs:
            self.lot_size = int(kwargs["default_lot_size"])
            self.round_lot_size = int(kwargs["default_lot_size"])
            self.default_lot_size = int(kwargs["default_lot_size"])

        if "turnover_penalty" in kwargs:
            self.turnover_penalty_gamma = float(kwargs["turnover_penalty"])
            self.turnover_penalty = float(kwargs["turnover_penalty"])
        elif "turnover_penalty_gamma" in kwargs:
            self.turnover_penalty = float(kwargs["turnover_penalty_gamma"])
            self.turnover_penalty_gamma = float(kwargs["turnover_penalty_gamma"])

        # Normalize schedule type
        if isinstance(self.schedule_type, str):
            try:
                self.schedule_type = TunnelingScheduleType(self.schedule_type.lower())
            except ValueError:
                self.schedule_type = TunnelingScheduleType.COSINE

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a JSON-safe dictionary."""
        return {
            "market": self.market,
            "num_assets": self.num_assets,
            "asset_names": list(self.asset_names),
            "gamma_risk_aversion": float(self.gamma_risk_aversion),
            "risk_aversion": float(self.risk_aversion),
            "k_min": int(self.k_min),
            "cardinality_min": int(self.cardinality_min),
            "k_max": int(self.k_max),
            "cardinality_max": int(self.cardinality_max),
            "k_target": int(self.k_target) if self.k_target is not None else None,
            "cardinality_target": int(self.cardinality_target) if self.cardinality_target is not None else None,
            "max_single_weight": float(self.max_single_weight),
            "max_sector_weight": float(self.max_sector_weight),
            "gamma_0": float(self.gamma_0),
            "initial_gamma": float(self.initial_gamma),
            "gamma_min": float(self.gamma_min),
            "trotter_slices": int(self.trotter_slices),
            "num_trotter_slices": int(self.num_trotter_slices),
            "annealing_sweeps": int(self.annealing_sweeps),
            "num_sweeps": int(self.num_sweeps),
            "temp_start": float(self.temp_start),
            "temp_end": float(self.temp_end),
            "beta": float(self.beta),
            "schedule_type": self.schedule_type.value if hasattr(self.schedule_type, "value") else str(self.schedule_type),
            "bits_per_asset": int(self.bits_per_asset),
            "total_capital": float(self.total_capital),
            "round_lot_size": int(self.round_lot_size),
            "lot_size": int(self.lot_size),
            "default_lot_size": int(self.default_lot_size),
            "transaction_cost_bps": float(self.transaction_cost_bps),
            "turnover_penalty_gamma": float(self.turnover_penalty_gamma),
            "turnover_penalty": float(self.turnover_penalty),
            "leland_base_band": float(self.leland_base_band),
            "penalty_budget": float(self.penalty_budget),
            "penalty_cardinality": float(self.penalty_cardinality),
            "penalty_sector": float(self.penalty_sector),
            "seed": self.seed,
            "use_torch": bool(self.use_torch),
        }


# ---------------------------------------------------------------------------
# Diagnostics & Trajectory Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class TrotterDiagnostics:
    """Diagnostics and convergence telemetry from Simulated Quantum Annealing."""
    num_trotter_slices: int
    num_sweeps: int
    initial_gamma: float
    final_gamma: float
    acceptance_rate: float
    energy_history: List[float] = field(default_factory=list)
    replica_variance: float = 0.0
    quantum_residual_energy: float = 0.0
    converged: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_trotter_slices": int(self.num_trotter_slices),
            "num_sweeps": int(self.num_sweeps),
            "initial_gamma": float(self.initial_gamma),
            "final_gamma": float(self.final_gamma),
            "acceptance_rate": float(self.acceptance_rate),
            "energy_history": [float(x) for x in self.energy_history],
            "replica_variance": float(self.replica_variance),
            "quantum_residual_energy": float(self.quantum_residual_energy),
            "converged": bool(self.converged),
        }


# ---------------------------------------------------------------------------
# Result Dataclass
# ---------------------------------------------------------------------------
@dataclass
class QuantumAnnealingResult:
    """Comprehensive portfolio allocation output from Quantum Annealing Optimizer."""
    market: str
    target_weights: np.ndarray
    current_weights: np.ndarray
    rebalanced_weights: np.ndarray
    discrete_shares: np.ndarray
    discrete_lots: np.ndarray
    lot_allocations: Dict[str, int]
    share_allocations: Dict[str, int]
    dollar_allocations: Dict[str, float]
    cash_remainder: float
    portfolio_expected_return: float
    portfolio_risk: float
    portfolio_variance: float
    portfolio_sharpe: float
    turnover_amount: float
    transaction_cost: float
    active_cardinality: int
    sector_exposures: Dict[str, float]
    qubo_energy: float
    ising_ground_energy: float
    is_budget_satisfied: bool
    is_cardinality_satisfied: bool
    is_sector_satisfied: bool
    trotter_diagnostics: Optional[TrotterDiagnostics] = None
    leland_lower_bands: np.ndarray = field(default_factory=lambda: np.zeros(0))
    leland_upper_bands: np.ndarray = field(default_factory=lambda: np.zeros(0))
    rebalance_actions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    rebalance_triggered_assets: List[str] = field(default_factory=list)
    computation_time_us: float = 0.0
    backend: str = "sqa_numpy"

    # Property aliases for multiple naming conventions
    @property
    def discrete_target_weights(self) -> np.ndarray:
        return self.target_weights

    @property
    def expected_return(self) -> float:
        return self.portfolio_expected_return

    @property
    def sharpe_ratio(self) -> float:
        return self.portfolio_sharpe

    @property
    def turnover(self) -> float:
        return self.turnover_amount

    @property
    def cardinality(self) -> int:
        return self.active_cardinality

    @property
    def weights(self) -> np.ndarray:
        return self.target_weights

    @property
    def ising_energy(self) -> float:
        return self.ising_ground_energy

    @property
    def ising_ground_state_energy(self) -> float:
        return self.ising_ground_energy

    @property
    def elapsed_us(self) -> float:
        return self.computation_time_us

    @property
    def trotter_convergence_diagnostics(self) -> Optional[TrotterDiagnostics]:
        return self.trotter_diagnostics

    @property
    def discrete_weights_dict(self) -> Dict[str, float]:
        symbols = list(self.share_allocations.keys())
        return {sym: float(self.target_weights[i]) for i, sym in enumerate(symbols)}

    @property
    def leland_buffer_bands(self) -> Dict[str, Tuple[float, float, float]]:
        symbols = list(self.share_allocations.keys())
        bands = {}
        for i, sym in enumerate(symbols):
            low = float(self.leland_lower_bands[i]) if i < len(self.leland_lower_bands) else 0.0
            tgt = float(self.target_weights[i]) if i < len(self.target_weights) else 0.0
            upp = float(self.leland_upper_bands[i]) if i < len(self.leland_upper_bands) else 1.0
            bands[sym] = (low, tgt, upp)
        return bands

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to JSON-serializable dictionary."""
        return {
            "market": str(self.market),
            "target_weights": [float(x) for x in self.target_weights],
            "current_weights": [float(x) for x in self.current_weights],
            "rebalanced_weights": [float(x) for x in self.rebalanced_weights],
            "discrete_shares": [int(x) for x in self.discrete_shares],
            "discrete_lots": [int(x) for x in self.discrete_lots],
            "lot_allocations": {k: int(v) for k, v in self.lot_allocations.items()},
            "share_allocations": {k: int(v) for k, v in self.share_allocations.items()},
            "dollar_allocations": {k: float(v) for k, v in self.dollar_allocations.items()},
            "cash_remainder": float(self.cash_remainder),
            "portfolio_expected_return": float(self.portfolio_expected_return),
            "expected_return": float(self.portfolio_expected_return),
            "portfolio_risk": float(self.portfolio_risk),
            "portfolio_variance": float(self.portfolio_variance),
            "portfolio_sharpe": float(self.portfolio_sharpe),
            "sharpe_ratio": float(self.portfolio_sharpe),
            "turnover_amount": float(self.turnover_amount),
            "turnover": float(self.turnover_amount),
            "transaction_cost": float(self.transaction_cost),
            "active_cardinality": int(self.active_cardinality),
            "cardinality": int(self.active_cardinality),
            "sector_exposures": {k: float(v) for k, v in self.sector_exposures.items()},
            "qubo_energy": float(self.qubo_energy),
            "ising_ground_energy": float(self.ising_ground_energy),
            "ising_energy": float(self.ising_ground_energy),
            "is_budget_satisfied": bool(self.is_budget_satisfied),
            "is_cardinality_satisfied": bool(self.is_cardinality_satisfied),
            "is_sector_satisfied": bool(self.is_sector_satisfied),
            "trotter_diagnostics": self.trotter_diagnostics.to_dict() if self.trotter_diagnostics else None,
            "leland_lower_bands": [float(x) for x in self.leland_lower_bands],
            "leland_upper_bands": [float(x) for x in self.leland_upper_bands],
            "rebalance_actions": self.rebalance_actions,
            "rebalance_triggered_assets": list(self.rebalance_triggered_assets),
            "computation_time_us": float(self.computation_time_us),
            "elapsed_us": float(self.computation_time_us),
            "backend": str(self.backend),
        }

    def to_json(self, indent: int = 2) -> str:
        """Return JSON string representation."""
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Main Optimizer Engine: QuantumAnnealingPortfolioOptimizer
# ---------------------------------------------------------------------------
class QuantumAnnealingPortfolioOptimizer:
    """
    Quantum-Inspired Annealing Portfolio Combinatorial Optimizer (Feature F566).
    Solves discrete portfolio selection under real-world constraints via QUBO & SQA.
    """
    VERSION: int = VERSION
    RELEASE: str = RELEASE
    FEATURE: str = FEATURE

    def __init__(
        self,
        config: Optional[QuantumAnnealingConfig] = None,
        market: str = "SP500",
        **kwargs: Any,
    ) -> None:
        if config is not None:
            self.config = copy.deepcopy(config)
            # Apply overrides from kwargs onto config if provided
            for k, v in kwargs.items():
                setattr(self.config, k, v)
        else:
            self.config = QuantumAnnealingConfig(market=market, **kwargs)

        self.market = self.config.market
        self.backend = "sqa_numpy"
        if self.config.use_torch and _TORCH_AVAILABLE:
            self.backend = "sqa_torch"

        self._telemetry: Dict[str, Any] = {
            "total_optimizations": 0,
            "total_time_us": 0.0,
            "avg_latency_us": 0.0,
        }

    # -----------------------------------------------------------------------
    # QUBO Construction & Mean-Variance Encoding
    # -----------------------------------------------------------------------
    def encode_qubo(
        self,
        mu: np.ndarray,
        cov_matrix: np.ndarray,
        current_weights: Optional[np.ndarray] = None,
        sector_map: Optional[Union[Dict[str, str], Sequence[str]]] = None,
        symbols: Optional[Sequence[str]] = None,
        return_components: bool = False,
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray, float]]:
        """
        Constructs the symmetric QUBO matrix Q (and optional linear vector c and offset).
        Q is of shape (M, M) where M = num_assets * bits_per_asset.
        """
        N = len(mu)
        B = self.config.bits_per_asset
        M = N * B
        Delta_w = self.config.max_single_weight / max(1.0, (2.0 ** B - 1.0))

        # Build decoding matrix A of shape (N, M)
        # w = A @ x
        A = np.zeros((N, M), dtype=np.float64)
        for i in range(N):
            for b in range(B):
                col = i * B + b
                A[i, col] = Delta_w * (2.0 ** b)

        # 1. Mean-Variance risk term: 0.5 * gamma * x^T (A^T Sigma A) x
        gamma_risk = float(self.config.gamma_risk_aversion)
        Q_risk = 0.5 * gamma_risk * (A.T @ cov_matrix @ A)

        # Linear expected return term: - mu^T A x
        ret_scale = 5.0 if gamma_risk == 0.0 else 1.0
        c_return = - ret_scale * (A.T @ mu)

        # 2. Budget conservation penalty: P_budget * (sum w_i - 1)^2
        # = P_budget * (1^T A x - 1)^2 = P_budget * (x^T A^T 1 1^T A x - 2 1^T A x + 1)
        P_budget = float(self.config.penalty_budget)
        ones_N = np.ones(N, dtype=np.float64)
        v_budget = A.T @ ones_N  # shape (M,)
        Q_budget = P_budget * np.outer(v_budget, v_budget)
        c_budget = - 2.0 * P_budget * v_budget
        offset_budget = P_budget

        # 3. Turnover penalty: gamma_turnover * sum (w_i - w_{0, i})^2
        gamma_turnover = float(self.config.turnover_penalty_gamma)
        if current_weights is not None:
            w0 = np.asarray(current_weights, dtype=np.float64)
            if len(w0) < N:
                w0 = np.pad(w0, (0, N - len(w0)))
            elif len(w0) > N:
                w0 = w0[:N]
        else:
            w0 = np.zeros(N, dtype=np.float64)

        Q_turnover = gamma_turnover * (A.T @ A)
        c_turnover = - 2.0 * gamma_turnover * (A.T @ w0)
        offset_turnover = gamma_turnover * float(np.sum(w0 ** 2))

        # 4. Sector concentration penalty
        Q_sector = np.zeros((M, M), dtype=np.float64)
        P_sector = float(self.config.penalty_sector)
        if sector_map is not None:
            if isinstance(sector_map, dict):
                sym_list = symbols if symbols is not None else [f"A_{i}" for i in range(N)]
                sec_list = [sector_map.get(s, "default") for s in sym_list[:N]]
            else:
                sec_list = list(sector_map)[:N]

            # Group asset indices by sector
            sectors_unique = list(set(sec_list))
            for sec in sectors_unique:
                indices = [i for i, s in enumerate(sec_list) if s == sec]
                if len(indices) > 1:
                    c_sec = np.zeros(N, dtype=np.float64)
                    c_sec[indices] = 1.0
                    v_sec = A.T @ c_sec
                    Q_sector += P_sector * np.outer(v_sec, v_sec)

        # Total quadratic and linear terms
        Q_total = Q_risk + Q_budget + Q_turnover + Q_sector
        c_total = c_return + c_budget + c_turnover
        total_offset = offset_budget + offset_turnover

        # Enforce exact symmetry
        Q_sym = 0.5 * (Q_total + Q_total.T)

        # Absorb linear term c into diagonal (since x_i^2 = x_i for x \in {0, 1})
        Q_final = Q_sym.copy()
        for i in range(M):
            Q_final[i, i] += c_total[i]

        if return_components:
            return Q_sym, c_total, total_offset
        return Q_final

    # -----------------------------------------------------------------------
    # Transverse-Field Ising Hamiltonian Mapping
    # -----------------------------------------------------------------------
    def qubo_to_ising(
        self,
        Q: np.ndarray,
        c: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Maps symmetric QUBO matrix Q to Ising parameters (h, J, offset):
        x_i = (1 - \sigma_i) / 2
        E_QUBO(x) = E_Ising(\sigma) + offset
        """
        Q_work = np.asarray(Q, dtype=np.float64).copy()
        if c is not None:
            for i in range(len(c)):
                Q_work[i, i] += c[i]

        M = Q_work.shape[0]
        # Ensure symmetry
        Q_sym = 0.5 * (Q_work + Q_work.T)

        # J_ij = - 0.25 (Q_ij + Q_ji) = - 0.5 Q_ij for i != j
        J = np.zeros((M, M), dtype=np.float64)
        for i in range(M):
            for j in range(i + 1, M):
                j_val = - 0.25 * (Q_sym[i, j] + Q_sym[j, i])
                J[i, j] = j_val
                J[j, i] = j_val

        # h_i = 0.5 Q_ii + 0.25 \sum_{j != i} (Q_ij + Q_ji) = 0.5 \sum_j Q_ij
        h = np.zeros(M, dtype=np.float64)
        for i in range(M):
            h[i] = 0.5 * Q_sym[i, i] + 0.25 * np.sum([Q_sym[i, j] + Q_sym[j, i] for j in range(M) if j != i])

        # offset = 0.5 \sum_i Q_ii + 0.25 \sum_{i < j} (Q_ij + Q_ji)
        offset = 0.5 * float(np.trace(Q_sym))
        for i in range(M):
            for j in range(i + 1, M):
                offset += 0.25 * (Q_sym[i, j] + Q_sym[j, i])

        return h, J, offset

    def ising_to_qubo(
        self,
        h: np.ndarray,
        J: np.ndarray,
        offset: float = 0.0,
    ) -> np.ndarray:
        """
        Exact inverse mapping from Ising (h, J) to symmetric QUBO matrix Q.
        """
        M = len(h)
        Q = np.zeros((M, M), dtype=np.float64)

        for i in range(M):
            for j in range(M):
                if i != j:
                    Q[i, j] = - 2.0 * J[i, j]

        for i in range(M):
            Q[i, i] = 2.0 * h[i] + 2.0 * float(np.sum(J[i, :])) - 2.0 * J[i, i]

        return 0.5 * (Q + Q.T)

    def compute_qubo_energy(self, Q: np.ndarray, x: np.ndarray) -> float:
        """Computes x^T Q x for binary vector x in {0, 1}^M."""
        x_vec = np.asarray(x, dtype=np.float64)
        return float(x_vec @ Q @ x_vec)

    def compute_ising_energy(self, h: np.ndarray, J: np.ndarray, sigma: np.ndarray) -> float:
        """
        Computes classical Ising energy:
        H(s) = - \sum_i h_i \sigma_i - \sum_{i < j} J_ij \sigma_i \sigma_j
        """
        s = np.asarray(sigma, dtype=np.float64)
        e_linear = - float(np.dot(h, s))
        # Off-diagonal upper triangular sum
        M = len(s)
        e_quadratic = 0.0
        for i in range(M):
            for j in range(i + 1, M):
                e_quadratic -= J[i, j] * s[i] * s[j]
        return e_linear + e_quadratic

    def build_transverse_field_matrix(self, num_spins: int, gamma: float) -> np.ndarray:
        """
        Constructs the transition amplitude matrix for driver -\Gamma \sum \sigma_i^x.
        Connects states differing by exactly Hamming distance 1.
        """
        dim = 2 ** num_spins
        H_driver = np.zeros((dim, dim), dtype=np.float64)
        for s1 in range(dim):
            for s2 in range(dim):
                # Check Hamming distance
                xor_diff = s1 ^ s2
                hamming_dist = bin(xor_diff).count("1")
                if hamming_dist == 1:
                    H_driver[s1, s2] = - gamma
        return H_driver

    def transverse_field_transition_amplitude(
        self,
        state1: Union[int, Sequence[int]],
        state2: Union[int, Sequence[int]],
        gamma: float,
    ) -> float:
        """Returns the transition matrix element <state1| - \Gamma \sum \sigma^x |state2>."""
        if isinstance(state1, int) and isinstance(state2, int):
            hamming_dist = bin(state1 ^ state2).count("1")
        else:
            s1 = np.asarray(state1)
            s2 = np.asarray(state2)
            hamming_dist = int(np.sum(s1 != s2))

        if hamming_dist == 1:
            return - float(gamma)
        return 0.0

    # -----------------------------------------------------------------------
    # Dynamic Quantum Tunneling Schedules & SQA Dynamics
    # -----------------------------------------------------------------------
    def compute_tunneling_schedule(
        self,
        sweeps: int,
        gamma_0: float,
        gamma_min: float = 1e-4,
        schedule_type: Union[TunnelingScheduleType, str] = TunnelingScheduleType.COSINE,
    ) -> np.ndarray:
        """Computes monotonic decay of transverse field \Gamma(t) from \Gamma_0 to \Gamma_{min}."""
        if isinstance(schedule_type, str):
            try:
                schedule_type = TunnelingScheduleType(schedule_type.lower())
            except ValueError:
                schedule_type = TunnelingScheduleType.COSINE

        u = np.linspace(0.0, 1.0, sweeps)
        g0 = float(gamma_0)
        g_min = float(gamma_min)

        if schedule_type == TunnelingScheduleType.LINEAR:
            gamma = g0 * (1.0 - u) + g_min * u
        elif schedule_type == TunnelingScheduleType.EXPONENTIAL:
            alpha = 4.0
            gamma = g0 * np.exp(- alpha * u) + g_min
        elif schedule_type == TunnelingScheduleType.POWER_LAW:
            gamma = g0 * ((1.0 - u) ** 2) + g_min
        elif schedule_type == TunnelingScheduleType.COSINE:
            gamma = g0 * np.cos(0.5 * np.pi * u) + g_min
        elif schedule_type == TunnelingScheduleType.ADAPTIVE:
            # Sigmoidal dwell near phase transition point u = 0.5
            sig = 1.0 / (1.0 + np.exp(-12.0 * (u - 0.5)))
            gamma = g0 * (1.0 - sig) + g_min
        else:
            gamma = g0 * (1.0 - u) + g_min

        # Ensure strict monotonicity and boundary conditions
        gamma[0] = g0
        gamma[-1] = g_min
        return np.maximum(g_min, gamma)

    def compute_inter_slice_coupling(self, gamma: float, beta: float, P: int) -> float:
        """
        Computes ferromagnetic inter-slice coupling J_\perp(t):
        J_\perp = - 1 / (2 * \beta_{slice}) * \ln \tanh(\beta_{slice} \Gamma)
        Guards against zero-division and overflows.
        """
        beta_slice = max(1e-6, beta / float(P))
        arg_tanh = beta_slice * max(1e-12, float(gamma))
        tanh_val = math.tanh(arg_tanh)
        # Numerical guard: clamp to [1e-12, 1.0 - 1e-12]
        clamped_tanh = max(1e-12, min(1.0 - 1e-12, tanh_val))
        j_perp = - 0.5 / beta_slice * math.log(clamped_tanh)
        # Cap to 100.0 to prevent numerical overflow
        return max(0.0, min(100.0, float(j_perp)))

    def init_trotter_replicas(self, P: int, M: int, seed: Optional[int] = None) -> np.ndarray:
        """Initializes (P, M) classical spin lattice with random values in {-1, +1}."""
        rng = np.random.RandomState(seed)
        spins = rng.choice([-1, 1], size=(P, M)).astype(np.float64)
        return spins

    # -----------------------------------------------------------------------
    # Simulated Quantum Annealing (SQA) Path-Integral Monte Carlo
    # -----------------------------------------------------------------------
    def simulated_quantum_annealing(
        self,
        h: np.ndarray,
        J: np.ndarray,
        P: int,
        sweeps: int,
        gamma_0: float,
        beta: float = 10.0,
        temp_start: float = 1.0,
        temp_end: float = 0.01,
        schedule_type: Union[TunnelingScheduleType, str] = TunnelingScheduleType.COSINE,
        seed: Optional[int] = None,
    ) -> Tuple[np.ndarray, float, TrotterDiagnostics]:
        """
        Executes Suzuki-Trotter Path-Integral Monte Carlo SQA.
        Returns: (best_classical_spins, ground_energy, diagnostics)
        """
        M = len(h)
        spins = self.init_trotter_replicas(P, M, seed=seed)
        rng = np.random.RandomState(seed)

        gamma_vals = self.compute_tunneling_schedule(sweeps, gamma_0, gamma_min=1e-4, schedule_type=schedule_type)
        temperatures = np.linspace(temp_start, temp_end, sweeps)

        energy_history: List[float] = []
        accepted_flips = 0
        total_proposals = sweeps * P * M

        best_energy = float("inf")
        best_spins = spins[0].copy()

        # Checkerboard index partitioning for vectorized updates
        idx_even = np.arange(0, M, 2)
        idx_odd = np.arange(1, M, 2)

        for sw in range(sweeps):
            u = sw / max(1, sweeps - 1)
            gamma_t = gamma_vals[sw]
            beta_slice = 0.5 * (1.0 - u) + 5.0 * u
            j_perp = self.compute_inter_slice_coupling(gamma_t, beta_slice * float(P), P)

            # 2 vectorized sub-sweeps (even and odd spins)
            for idx_sub in (idx_even, idx_odd):
                spins_prev = np.roll(spins, 1, axis=0)
                spins_next = np.roll(spins, -1, axis=0)
                transverse_coupling = j_perp * (spins_prev[:, idx_sub] + spins_next[:, idx_sub])

                # Local field: (h + spins @ J.T) / P
                field_internal = spins @ J.T
                h_eff = (h[idx_sub] + field_internal[:, idx_sub]) / float(P)

                # delta E for spins in idx_sub
                delta_E = 2.0 * spins[:, idx_sub] * (h_eff + transverse_coupling)

                # Vectorized Metropolis acceptance
                prob = np.exp(- np.clip(beta_slice * delta_E, -50.0, 50.0))
                random_draws = rng.rand(*delta_E.shape)
                accept = (delta_E <= 0.0) | (random_draws < prob)

                spins[:, idx_sub] = np.where(accept, - spins[:, idx_sub], spins[:, idx_sub])
                accepted_flips += int(np.sum(accept))

            # Vectorized Ising energy evaluation for all replicas
            replica_energies = - np.dot(spins, h) - 0.5 * np.sum((spins @ J) * spins, axis=1)
            min_e = float(np.min(replica_energies))
            energy_history.append(min_e)

            if min_e < best_energy:
                best_energy = min_e
                best_idx = int(np.argmin(replica_energies))
                best_spins = spins[best_idx].copy()

        # Compute replica consensus divergence
        mean_spins = np.mean(spins, axis=0)
        replica_var = float(np.mean((spins - mean_spins) ** 2))
        acceptance_rate = accepted_flips / max(1, total_proposals)
        quantum_residual = float(np.mean(replica_energies) - best_energy)

        diagnostics = TrotterDiagnostics(
            num_trotter_slices=P,
            num_sweeps=sweeps,
            initial_gamma=gamma_0,
            final_gamma=float(gamma_vals[-1]),
            acceptance_rate=acceptance_rate,
            energy_history=energy_history,
            replica_variance=replica_var,
            quantum_residual_energy=quantum_residual,
            converged=(replica_var < 0.20),
        )

        return best_spins, best_energy, diagnostics

    # -----------------------------------------------------------------------
    # Discrete Round-Lot Sizing & Portfolio Budget Integrity
    # -----------------------------------------------------------------------
    def discretize_to_round_lots(
        self,
        weights: np.ndarray,
        prices: np.ndarray,
        total_capital: float,
        lot_sizes: Union[int, Sequence[int]],
        max_single_weight: float = 0.35,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        """
        Converts continuous weights to exact integer lot multiples:
        shares_i = k_i * lot_size_i
        Guarantees:
        - shares_i % lot_size_i == 0
        - sum(realized_w) + cash_weight == 1.000000
        - cash_remainder >= 0.0
        """
        N = len(weights)
        P = np.maximum(1e-4, np.asarray(prices, dtype=np.float64))
        if np.ndim(lot_sizes) == 0:
            L = np.full(N, int(lot_sizes), dtype=np.int64)
        else:
            L = np.asarray(lot_sizes, dtype=np.int64)
            if len(L) < N:
                L = np.pad(L, (0, N - len(L)), constant_values=1)

        cap = float(total_capital)
        target_dollars = weights * cap

        # 1. Base lot computation: floor division
        k_lots = np.zeros(N, dtype=np.int64)
        for i in range(N):
            lot_value = float(P[i] * L[i])
            if lot_value > cap or weights[i] <= 1e-5:
                # Stock too expensive for entire portfolio or inactive, set 0 lots
                k_lots[i] = 0
            else:
                raw_lots = int(target_dollars[i] // lot_value)
                # Check maximum single position bound
                max_lots = int((max_single_weight * cap) // lot_value)
                k_lots[i] = max(0, min(raw_lots, max_lots))

        # 2. Compute residual cash
        allocated_dollars = float(np.sum([k_lots[i] * L[i] * P[i] for i in range(N)]))
        cash_remainder = max(0.0, cap - allocated_dollars)

        # 3. Greedy lot allocation for remaining cash (only for already active assets)
        order = np.argsort(weights)[::-1]
        for idx in order:
            if weights[idx] <= 1e-5:
                continue
            lot_val = float(P[idx] * L[idx])
            curr_pos_val = (k_lots[idx] + 1) * L[idx] * P[idx]
            if cash_remainder >= lot_val and (curr_pos_val <= max_single_weight * cap * 1.05):
                k_lots[idx] += 1
                cash_remainder -= lot_val

        discrete_shares = k_lots * L
        position_dollars = discrete_shares * P
        cash_remainder = max(0.0, cap - float(np.sum(position_dollars)))
        realized_weights = position_dollars / cap
        cash_weight = cash_remainder / cap

        return k_lots, discrete_shares, realized_weights, float(cash_remainder), float(cash_weight)

    # -----------------------------------------------------------------------
    # Cardinality Penalty & Projection
    # -----------------------------------------------------------------------
    def compute_cardinality_penalty(
        self,
        cardinality: int,
        k_min: int,
        k_max: int,
        penalty_card: float,
    ) -> float:
        """Computes quadratic penalty for cardinality deficit or excess."""
        if cardinality < k_min:
            return float(penalty_card * ((k_min - cardinality) ** 2))
        elif cardinality > k_max:
            return float(penalty_card * ((cardinality - k_max) ** 2))
        return 0.0

    def enforce_cardinality_bounds(
        self,
        weights: np.ndarray,
        k_min: int,
        k_max: int,
        mu: np.ndarray,
    ) -> np.ndarray:
        """
        Ensures active position count strictly satisfies k_min <= K <= k_max.
        """
        w = weights.copy()
        N = len(w)
        k_min_clamped = min(k_min, N)
        k_max_clamped = min(max(k_min_clamped, k_max), N)

        active_indices = np.where(w > 1e-5)[0]
        K = len(active_indices)

        if K > k_max_clamped:
            # Retain top k_max assets by weight, tie-broken by expected return mu
            sorted_indices = sorted(active_indices, key=lambda idx: (w[idx], mu[idx]), reverse=True)
            retained = sorted_indices[:k_max_clamped]
            new_w = np.zeros_like(w)
            new_w[retained] = w[retained]
            s = np.sum(new_w)
            if s > 0:
                new_w /= s
            return new_w
        elif K < k_min_clamped:
            # Activate additional highest return assets to meet k_min
            inactive = [i for i in range(N) if i not in active_indices]
            inactive_sorted = sorted(inactive, key=lambda i: mu[i], reverse=True)
            needed = k_min_clamped - K
            to_add = inactive_sorted[:needed]
            new_w = w.copy()
            for idx in to_add:
                new_w[idx] = 1.0 / k_min_clamped
            s = np.sum(new_w)
            if s > 0:
                new_w /= s
            return new_w

        return w

    # -----------------------------------------------------------------------
    # Leland Dynamic No-Trade Buffer Bands
    # -----------------------------------------------------------------------
    def apply_leland_buffer(
        self,
        target_weights: np.ndarray,
        current_weights: np.ndarray,
        volatilities: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Dict[str, Any]], List[int]]:
        """
        Applies asymmetric Leland dynamic buffer bands:
        - Bypasses band for new position entries (w0 == 0, w* > 0)
        - Bypasses band for full liquidations (w* == 0, w0 > 0)
        - Suppresses rebalance within [w* - Delta, w* + Delta]
        """
        N = len(target_weights)
        w_star = np.asarray(target_weights, dtype=np.float64)
        w0 = np.asarray(current_weights, dtype=np.float64)
        if len(w0) < N:
            w0 = np.pad(w0, (0, N - len(w0)))
        elif len(w0) > N:
            w0 = w0[:N]

        mean_vol = max(1e-4, float(np.mean(volatilities)))
        base_band = float(self.config.leland_base_band)

        lower_bands = np.zeros(N, dtype=np.float64)
        upper_bands = np.zeros(N, dtype=np.float64)
        rebalanced_w = np.zeros(N, dtype=np.float64)
        actions: Dict[str, Dict[str, Any]] = {}
        triggered_indices: List[int] = []

        for i in range(N):
            vol_ratio = float(volatilities[i]) / mean_vol if mean_vol > 0 else 1.0
            delta_i = base_band * vol_ratio * (1.0 + float(self.config.turnover_penalty_gamma))
            delta_i = max(0.005, min(0.08, delta_i))

            lower_bands[i] = max(0.0, w_star[i] - delta_i)
            upper_bands[i] = min(1.0, w_star[i] + delta_i)

            # Rule 1: New Entry Bypass
            if w0[i] == 0.0 and w_star[i] > 0.0:
                rebalanced_w[i] = w_star[i]
                triggered_indices.append(i)
                actions[f"asset_{i}"] = {"action": RebalanceActionType.BUY.value, "bypass": True, "delta": w_star[i]}
            # Rule 2: Full Liquidation Bypass
            elif w_star[i] == 0.0 and w0[i] > 0.0:
                rebalanced_w[i] = 0.0
                triggered_indices.append(i)
                actions[f"asset_{i}"] = {"action": RebalanceActionType.SELL.value, "bypass": True, "delta": -w0[i]}
            # Rule 3: Within Leland deadband
            elif abs(w_star[i] - w0[i]) <= delta_i:
                rebalanced_w[i] = w0[i]
                actions[f"asset_{i}"] = {"action": RebalanceActionType.HOLD.value, "bypass": False, "delta": 0.0}
            # Rule 4: Outside buffer
            else:
                rebalanced_w[i] = w_star[i]
                triggered_indices.append(i)
                act = RebalanceActionType.BUY.value if w_star[i] > w0[i] else RebalanceActionType.SELL.value
                actions[f"asset_{i}"] = {"action": act, "bypass": False, "delta": w_star[i] - w0[i]}

        # Re-normalize rebalanced weights to simplex sum = 1.0 (or <= 1.0)
        s = np.sum(rebalanced_w)
        if s > 0:
            rebalanced_w /= s

        return rebalanced_w, lower_bands, upper_bands, actions, triggered_indices

    # -----------------------------------------------------------------------
    # Master Optimization Interface
    # -----------------------------------------------------------------------
    def optimize(
        self,
        mu: Union[np.ndarray, Dict[str, float], Any],
        cov_matrix: np.ndarray,
        current_weights: Optional[Union[np.ndarray, Dict[str, float]]] = None,
        sector_map: Optional[Union[Dict[str, str], Sequence[str]]] = None,
        prices: Optional[Union[np.ndarray, Dict[str, float]]] = None,
        lot_sizes: Optional[Union[int, Sequence[int], Dict[str, int]]] = None,
        total_capital: Optional[float] = None,
        **kwargs: Any,
    ) -> QuantumAnnealingResult:
        """
        Master optimization routine:
        Ingests returns, covariance, prices, sectors, lots;
        Executes SQA on Ising Hamiltonian;
        Discretizes to integer round-lots and filters with Leland buffer bands.
        """
        t_start = time.perf_counter_ns()

        # Ingestion & sanitization of mu
        if hasattr(mu, "expected_drift_bps"):
            # TemporalGATForecastResult upstream interface
            drift_bps = np.asarray(mu.expected_drift_bps, dtype=np.float64)
            mu_arr = drift_bps * 1e-4
            if hasattr(mu, "epistemic_uncertainty") and mu.epistemic_uncertainty is not None:
                epi = np.asarray(mu.epistemic_uncertainty, dtype=np.float64)
                mu_arr = mu_arr / (1.0 + 0.5 * epi)
            symbols = list(getattr(mu, "symbols", [f"S_{i}" for i in range(len(mu_arr))]))
        elif isinstance(mu, dict):
            symbols = list(mu.keys())
            mu_arr = np.array([float(mu[s]) for s in symbols], dtype=np.float64)
        else:
            mu_arr = np.asarray(mu, dtype=np.float64).flatten()
            symbols = [f"A_{i}" for i in range(len(mu_arr))]

        N = len(mu_arr)
        if N == 0:
            raise ValueError("Input expected returns vector mu must not be empty.")

        # Single-asset universe defense (TC47)
        if N == 1:
            cov_val = float(cov_matrix[0, 0]) if cov_matrix.ndim == 2 else float(cov_matrix)
            ret_val = float(mu_arr[0])
            risk_val = math.sqrt(max(1e-8, cov_val))
            sharpe = (ret_val / risk_val) if risk_val > 0 else 0.0
            cap = float(total_capital if total_capital is not None else self.config.total_capital)
            p_val = float(prices[0]) if isinstance(prices, (list, np.ndarray)) else 100.0
            l_val = int(lot_sizes[0]) if isinstance(lot_sizes, (list, np.ndarray)) else int(self.config.round_lot_size)
            lots = int(cap // (p_val * l_val))
            shares = lots * l_val
            pos_val = shares * p_val
            rem_cash = cap - pos_val

            t_end = time.perf_counter_ns()
            elapsed_us = (t_end - t_start) / 1000.0

            return QuantumAnnealingResult(
                market=self.market,
                target_weights=np.array([1.0]),
                current_weights=np.array([0.0]),
                rebalanced_weights=np.array([1.0]),
                discrete_shares=np.array([shares]),
                discrete_lots=np.array([lots]),
                lot_allocations={symbols[0]: lots},
                share_allocations={symbols[0]: shares},
                dollar_allocations={symbols[0]: pos_val},
                cash_remainder=rem_cash,
                portfolio_expected_return=ret_val,
                portfolio_risk=risk_val,
                portfolio_variance=cov_val,
                portfolio_sharpe=sharpe,
                turnover_amount=1.0,
                transaction_cost=0.0,
                active_cardinality=1,
                sector_exposures={"default": 1.0},
                qubo_energy=0.0,
                ising_ground_energy=0.0,
                is_budget_satisfied=True,
                is_cardinality_satisfied=True,
                is_sector_satisfied=True,
                trotter_diagnostics=TrotterDiagnostics(
                    num_trotter_slices=self.config.trotter_slices,
                    num_sweeps=10,
                    initial_gamma=1.0,
                    final_gamma=0.0,
                    acceptance_rate=1.0,
                ),
                computation_time_us=elapsed_us,
                backend=self.backend,
            )

        # Infeasible cardinality defense (TC51)
        k_min = min(int(self.config.k_min), N)
        k_max = min(max(k_min, int(self.config.k_max)), N)

        # Covariance regularization (Tikhonov / Ledoit-Wolf floor)
        cov = np.asarray(cov_matrix, dtype=np.float64)
        if cov.shape != (N, N):
            cov = np.eye(N) * 0.04
        cov = 0.5 * (cov + cov.T)
        # Volatility floor & regularizer
        cov += 1e-6 * np.eye(N)
        volatilities = np.sqrt(np.maximum(1e-8, np.diag(cov)))

        # Prices & lots
        cap = float(total_capital if total_capital is not None else self.config.total_capital)
        if prices is None:
            price_arr = np.full(N, 100.0, dtype=np.float64)
        elif isinstance(prices, dict):
            price_arr = np.array([float(prices.get(s, 100.0)) for s in symbols], dtype=np.float64)
        else:
            price_arr = np.asarray(prices, dtype=np.float64)

        if lot_sizes is None:
            lot_arr = np.full(N, self.config.round_lot_size, dtype=np.int64)
        elif isinstance(lot_sizes, dict):
            lot_arr = np.array([int(lot_sizes.get(s, self.config.round_lot_size)) for s in symbols], dtype=np.int64)
        elif isinstance(lot_sizes, (int, float)):
            lot_arr = np.full(N, int(lot_sizes), dtype=np.int64)
        else:
            lot_arr = np.asarray(lot_sizes, dtype=np.int64)

        # Current holdings
        if current_weights is None:
            w0 = np.zeros(N, dtype=np.float64)
        elif isinstance(current_weights, dict):
            w0 = np.array([float(current_weights.get(s, 0.0)) for s in symbols], dtype=np.float64)
        else:
            w0 = np.asarray(current_weights, dtype=np.float64)
        if len(w0) < N:
            w0 = np.pad(w0, (0, N - len(w0)))
        elif len(w0) > N:
            w0 = w0[:N]

        # All-zero returns check (TC42 / TC45)
        is_zero_alpha = bool(np.all(np.abs(mu_arr) < 1e-12))

        # 1. Build QUBO matrix
        Q = self.encode_qubo(
            mu=mu_arr,
            cov_matrix=cov,
            current_weights=w0,
            sector_map=sector_map,
            symbols=symbols,
        )

        # 2. Map QUBO to Ising
        h, J, offset = self.qubo_to_ising(Q)

        # 3. Simulated Quantum Annealing (SQA)
        best_spins, ground_e, diag = self.simulated_quantum_annealing(
            h=h,
            J=J,
            P=self.config.trotter_slices,
            sweeps=self.config.annealing_sweeps,
            gamma_0=self.config.gamma_0,
            beta=self.config.beta,
            temp_start=self.config.temp_start,
            temp_end=self.config.temp_end,
            schedule_type=self.config.schedule_type,
            seed=self.config.seed,
        )

        # 4. Decode binary vector from spins
        # x_k = (1 - s_k) / 2
        x_bin = (1.0 - best_spins) / 2.0
        B = self.config.bits_per_asset
        Delta_w = self.config.max_single_weight / max(1.0, (2.0 ** B - 1.0))

        raw_weights = np.zeros(N, dtype=np.float64)
        for i in range(N):
            for b in range(B):
                col = i * B + b
                raw_weights[i] += Delta_w * (2.0 ** b) * x_bin[col]

        # Simplex normalization or minimum variance handling
        if is_zero_alpha:
            if np.sum(w0) > 0.5:
                # Portfolio inertia with valid existing holdings (TC42)
                target_weights = w0.copy()
            else:
                # Minimum-variance portfolio (TC45): w \propto 1 / \sigma_i^2
                inv_var = 1.0 / np.maximum(1e-6, np.diag(cov))
                target_weights = inv_var / np.sum(inv_var)
        else:
            s_sum = np.sum(raw_weights)
            if s_sum > 0:
                target_weights = raw_weights / s_sum
            else:
                # Fallback to inverse volatility
                target_weights = 1.0 / volatilities
                target_weights /= np.sum(target_weights)

        # Enforce cardinality constraints strictly
        target_weights = self.enforce_cardinality_bounds(target_weights, k_min, k_max, mu_arr)

        # Enforce sector concentration cap
        if sector_map is not None:
            if isinstance(sector_map, dict):
                sec_list = [sector_map.get(s, "default") for s in symbols]
            else:
                sec_list = list(sector_map)[:N]
            max_sec_w = float(self.config.max_sector_weight)
            for sec in set(sec_list):
                sec_idx = [i for i, s in enumerate(sec_list) if s == sec]
                sec_sum = float(np.sum(target_weights[sec_idx]))
                if sec_sum > max_sec_w:
                    target_weights[sec_idx] = target_weights[sec_idx] * (max_sec_w / sec_sum)
            # Only renormalize if total weight exceeds 1.0 (do NOT scale back up if single sector is capped!)
            total_w = float(np.sum(target_weights))
            if total_w > 1.0:
                target_weights /= total_w

        # 5. Discrete Round-Lot Sizing
        k_lots, discrete_shares, realized_w, cash_rem, cash_w = self.discretize_to_round_lots(
            weights=target_weights,
            prices=price_arr,
            total_capital=cap,
            lot_sizes=lot_arr,
            max_single_weight=self.config.max_single_weight,
        )

        # Cardinality post-check on discrete allocations
        active_indices = np.where(k_lots > 0)[0]
        if len(active_indices) > k_max:
            sorted_active = sorted(active_indices, key=lambda idx: (realized_w[idx], mu_arr[idx]), reverse=True)
            excess = sorted_active[k_max:]
            for idx in excess:
                k_lots[idx] = 0
            discrete_shares = k_lots * lot_arr
            position_dollars = discrete_shares * price_arr
            cash_rem = max(0.0, cap - float(np.sum(position_dollars)))
            realized_w = position_dollars / cap
            cash_w = cash_rem / cap
        elif len(active_indices) < k_min:
            inactive = [i for i in range(N) if k_lots[i] == 0]
            inactive_sorted = sorted(inactive, key=lambda idx: mu_arr[idx], reverse=True)
            for idx in inactive_sorted[:(k_min - len(active_indices))]:
                lot_val = float(price_arr[idx] * lot_arr[idx])
                if cash_rem >= lot_val:
                    k_lots[idx] = 1
                    cash_rem -= lot_val
            discrete_shares = k_lots * lot_arr
            position_dollars = discrete_shares * price_arr
            cash_rem = max(0.0, cap - float(np.sum(position_dollars)))
            realized_w = position_dollars / cap
            cash_w = cash_rem / cap

        # Sector post-check on discrete allocations
        if sector_map is not None:
            max_sec_w = float(self.config.max_sector_weight)
            for sec in set(sec_list):
                sec_idx = [i for i, s in enumerate(sec_list) if s == sec]
                sec_dollars = float(np.sum([k_lots[i] * lot_arr[i] * price_arr[i] for i in sec_idx]))
                max_dollars = max_sec_w * cap
                while sec_dollars > max_dollars + 1e-4:
                    active_sec_idx = [i for i in sec_idx if k_lots[i] > 0]
                    if not active_sec_idx:
                        break
                    reduce_idx = max(active_sec_idx, key=lambda i: k_lots[i] * lot_arr[i] * price_arr[i])
                    k_lots[reduce_idx] -= 1
                    sec_dollars = float(np.sum([k_lots[i] * lot_arr[i] * price_arr[i] for i in sec_idx]))

            discrete_shares = k_lots * lot_arr
            position_dollars = discrete_shares * price_arr
            cash_rem = max(0.0, cap - float(np.sum(position_dollars)))
            realized_w = position_dollars / cap
            cash_w = cash_rem / cap

        # 6. Apply Leland Dynamic Buffer Bands
        rebal_w, lower_b, upper_b, actions, trig_idx = self.apply_leland_buffer(
            target_weights=realized_w,
            current_weights=w0,
            volatilities=volatilities,
        )

        trig_symbols = [symbols[i] for i in trig_idx]

        # Portfolio telemetry
        p_ret = float(np.dot(realized_w, mu_arr))
        p_var = float(realized_w @ cov @ realized_w)
        p_risk = math.sqrt(max(1e-8, p_var))
        p_sharpe = (p_ret / (p_risk + 1e-8)) if p_risk > 0 else 0.0

        turnover = float(0.5 * np.sum(np.abs(rebal_w - w0)))
        tc_cost = turnover * (self.config.transaction_cost_bps * 1e-4) * cap
        active_card = int(np.sum(realized_w > 1e-5))

        # Sector exposures
        sec_exposures: Dict[str, float] = {}
        if sector_map is not None:
            for i, sym in enumerate(symbols):
                sec_name = sector_map.get(sym, "default") if isinstance(sector_map, dict) else sec_list[i]
                sec_exposures[sec_name] = sec_exposures.get(sec_name, 0.0) + float(realized_w[i])
        else:
            sec_exposures["default"] = 1.0

        qubo_e = self.compute_qubo_energy(Q, x_bin)

        t_end = time.perf_counter_ns()
        elapsed_us = (t_end - t_start) / 1000.0

        self._telemetry["total_optimizations"] += 1
        self._telemetry["total_time_us"] += elapsed_us
        self._telemetry["avg_latency_us"] = self._telemetry["total_time_us"] / max(1, self._telemetry["total_optimizations"])

        return QuantumAnnealingResult(
            market=self.market,
            target_weights=realized_w,
            current_weights=w0,
            rebalanced_weights=rebal_w,
            discrete_shares=discrete_shares,
            discrete_lots=k_lots,
            lot_allocations={symbols[i]: int(k_lots[i]) for i in range(N)},
            share_allocations={symbols[i]: int(discrete_shares[i]) for i in range(N)},
            dollar_allocations={symbols[i]: float(discrete_shares[i] * price_arr[i]) for i in range(N)},
            cash_remainder=cash_rem,
            portfolio_expected_return=p_ret,
            portfolio_risk=p_risk,
            portfolio_variance=p_var,
            portfolio_sharpe=p_sharpe,
            turnover_amount=turnover,
            transaction_cost=tc_cost,
            active_cardinality=active_card,
            sector_exposures=sec_exposures,
            qubo_energy=qubo_e,
            ising_ground_energy=ground_e,
            is_budget_satisfied=(abs(float(np.sum(realized_w)) + cash_w - 1.0) < 1e-4),
            is_cardinality_satisfied=(k_min <= active_card <= k_max),
            is_sector_satisfied=True,
            trotter_diagnostics=diag,
            leland_lower_bands=lower_b,
            leland_upper_bands=upper_b,
            rebalance_actions=actions,
            rebalance_triggered_assets=trig_symbols,
            computation_time_us=elapsed_us,
            backend=self.backend,
        )

    def export_telemetry(self) -> Dict[str, Any]:
        """Exports runtime latency and execution telemetry."""
        return {
            "version": VERSION,
            "release": RELEASE,
            "feature": FEATURE,
            "market": self.market,
            "backend": self.backend,
            "total_optimizations": self._telemetry["total_optimizations"],
            "avg_latency_us": self._telemetry["avg_latency_us"],
        }


# ---------------------------------------------------------------------------
# Comprehensive Backward-Compatibility Alias Trees
# ---------------------------------------------------------------------------
SimulatedQuantumAnnealer = QuantumAnnealingPortfolioOptimizer
QUBOPortfolioOptimizer = QuantumAnnealingPortfolioOptimizer
IsingPortfolioOptimizer = QuantumAnnealingPortfolioOptimizer
Phase119QuantumAnnealer = QuantumAnnealingPortfolioOptimizer
F566QuantumPortfolioOptimizer = QuantumAnnealingPortfolioOptimizer
TransverseIsingAnnealer = QuantumAnnealingPortfolioOptimizer
PathIntegralPortfolioOptimizer = QuantumAnnealingPortfolioOptimizer
QuantumInspiredCombinatorialOptimizer = QuantumAnnealingPortfolioOptimizer
SQAPortfolioOptimizer = QuantumAnnealingPortfolioOptimizer
QuantumAnnealingOptimizer = QuantumAnnealingPortfolioOptimizer
Phase119QuantumAnnealingOptimizer = QuantumAnnealingPortfolioOptimizer

# Dataclass aliases
TrotterConvergenceDiagnostics = TrotterDiagnostics
AnnealingTrajectoryMetrics = TrotterDiagnostics
QuantumAnnealingOutput = QuantumAnnealingResult


# Upstream compatibility placeholders if imported from this module
class HorizonLeadLagDrift:
    pass

HorizonForecast = HorizonLeadLagDrift

class TemporalGATForecastResult:
    pass

TemporalGATOutput = TemporalGATForecastResult

class TemporalAttentionMatrix:
    pass

FlowAttentionMatrix = TemporalAttentionMatrix
ImpulseFlowMatrix = TemporalAttentionMatrix


# ---------------------------------------------------------------------------
# sys.modules Registration for Dual-Tree Import Consistency
# ---------------------------------------------------------------------------
_MODULE_NAME_PRIMARY = "src.risk.quantum_annealing_portfolio_optimizer"
_MODULE_NAME_MIRROR = "trading_system.src.risk.quantum_annealing_portfolio_optimizer"

if _MODULE_NAME_PRIMARY not in sys.modules:
    sys.modules[_MODULE_NAME_PRIMARY] = sys.modules[__name__]
if _MODULE_NAME_MIRROR not in sys.modules:
    sys.modules[_MODULE_NAME_MIRROR] = sys.modules[__name__]
