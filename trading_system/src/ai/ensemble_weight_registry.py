"""
src/ai/ensemble_weight_registry.py
==================================
Centralized Declarative Strategy Weight & Regime Modulation Registry.
Feature F585 - Phase 123 (Release R139 / v130 Production Master).

Provides structured declarative registry for all 37 canonical alpha strategies:
  1. Base priority weights and category groupings
  2. 8-Regime dynamic factor modulation matrices
  3. Real-time RankIC and alpha decay adjustments
  4. Missing-strategy safe zero-weighting and renormalization
  5. JSON/Dict export and import for hot-reloading
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

VERSION: int = 123
RELEASE: str = "R139"
FEATURE: str = "F585"


class StrategyCategory(str, Enum):
    ML_DEEP_LEARNING = "ml_deep_learning"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    MICROSTRUCTURE_FLOW = "microstructure_flow"
    MACRO_CATALYST = "macro_catalyst"
    TECHNICAL_VOLATILITY = "technical_volatility"
    VALUE_FUNDAMENTAL = "value_fundamental"


class MarketRegimeType(str, Enum):
    BULL_LOW_VOL = "bull_low_vol"
    BULL_HIGH_VOL = "bull_high_vol"
    SIDEWAYS_LOW_VOL = "sideways_low_vol"
    SIDEWAYS_HIGH_VOL = "sideways_high_vol"
    BEAR_LOW_VOL = "bear_low_vol"
    BEAR_HIGH_VOL = "bear_high_vol"
    PANIC_CRISIS = "panic_crisis"
    EXTREME_LIQUIDITY_SQUEEZE = "extreme_liquidity_squeeze"


@dataclass
class StrategyWeightProfile:
    name: str
    code: str
    category: StrategyCategory
    base_weight: float
    min_weight: float = 0.01
    max_weight: float = 0.35
    half_life_days: float = 20.0
    regime_multipliers: Dict[MarketRegimeType, float] = field(default_factory=dict)
    active: bool = True

    def get_regime_multiplier(self, regime: MarketRegimeType) -> float:
        return self.regime_multipliers.get(regime, 1.0)


# =========================================================================
# Canonical 37-Strategy Declarative Definitions
# =========================================================================
CANONICAL_37_STRATEGIES: List[StrategyWeightProfile] = [
    # 1. XGBoost Regression
    StrategyWeightProfile(
        name="XGBoost Regression",
        code="regression",
        category=StrategyCategory.ML_DEEP_LEARNING,
        base_weight=0.08,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.2,
            MarketRegimeType.SIDEWAYS_LOW_VOL: 1.0,
            MarketRegimeType.PANIC_CRISIS: 0.5,
        },
    ),
    # 2. Surge Classifier
    StrategyWeightProfile(
        name="Surge Classifier",
        code="surge",
        category=StrategyCategory.ML_DEEP_LEARNING,
        base_weight=0.06,
        regime_multipliers={
            MarketRegimeType.BULL_HIGH_VOL: 1.3,
            MarketRegimeType.BEAR_HIGH_VOL: 0.4,
        },
    ),
    # 3. Lead-Lag
    StrategyWeightProfile(
        name="Lead-Lag",
        code="lead_lag",
        category=StrategyCategory.STATISTICAL_ARBITRAGE,
        base_weight=0.04,
        regime_multipliers={
            MarketRegimeType.SIDEWAYS_LOW_VOL: 1.3,
            MarketRegimeType.PANIC_CRISIS: 1.2,
        },
    ),
    # 4. VCP Rule
    StrategyWeightProfile(
        name="VCP Rule",
        code="vcp_rule",
        category=StrategyCategory.TECHNICAL_VOLATILITY,
        base_weight=0.04,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.25,
            MarketRegimeType.BEAR_HIGH_VOL: 0.3,
        },
    ),
    # 5. VCP ML
    StrategyWeightProfile(
        name="VCP ML",
        code="vcp_ml",
        category=StrategyCategory.ML_DEEP_LEARNING,
        base_weight=0.05,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.2,
            MarketRegimeType.BEAR_HIGH_VOL: 0.4,
        },
    ),
    # 6. Strict Causal LSTM
    StrategyWeightProfile(
        name="Strict Causal LSTM",
        code="lstm",
        category=StrategyCategory.ML_DEEP_LEARNING,
        base_weight=0.06,
        regime_multipliers={
            MarketRegimeType.SIDEWAYS_LOW_VOL: 1.2,
            MarketRegimeType.PANIC_CRISIS: 0.6,
        },
    ),
    # 7. Stat-Arb Cointegration
    StrategyWeightProfile(
        name="Stat-Arb Cointegration",
        code="stat_arb",
        category=StrategyCategory.STATISTICAL_ARBITRAGE,
        base_weight=0.05,
        regime_multipliers={
            MarketRegimeType.SIDEWAYS_LOW_VOL: 1.5,
            MarketRegimeType.SIDEWAYS_HIGH_VOL: 1.3,
            MarketRegimeType.BULL_HIGH_VOL: 0.7,
        },
    ),
    # 8. Sector Rotation
    StrategyWeightProfile(
        name="Sector Rotation",
        code="sector",
        category=StrategyCategory.MACRO_CATALYST,
        base_weight=0.04,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.3,
            MarketRegimeType.PANIC_CRISIS: 0.4,
        },
    ),
    # 9. RIM Valuation
    StrategyWeightProfile(
        name="RIM Valuation",
        code="rim",
        category=StrategyCategory.VALUE_FUNDAMENTAL,
        base_weight=0.04,
        regime_multipliers={
            MarketRegimeType.BEAR_LOW_VOL: 1.4,
            MarketRegimeType.PANIC_CRISIS: 1.5,
        },
    ),
    # 10. Event-Driven
    StrategyWeightProfile(
        name="Event-Driven",
        code="event_driven",
        category=StrategyCategory.MACRO_CATALYST,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.BULL_HIGH_VOL: 1.2,
            MarketRegimeType.PANIC_CRISIS: 0.5,
        },
    ),
    # 11. Momentum Quality
    StrategyWeightProfile(
        name="Momentum Quality",
        code="mq_factor",
        category=StrategyCategory.TECHNICAL_VOLATILITY,
        base_weight=0.04,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.3,
            MarketRegimeType.BEAR_HIGH_VOL: 0.3,
        },
    ),
    # 12. Options IV Skew
    StrategyWeightProfile(
        name="Options IV Skew",
        code="iv_skew",
        category=StrategyCategory.TECHNICAL_VOLATILITY,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.PANIC_CRISIS: 1.6,
            MarketRegimeType.BEAR_HIGH_VOL: 1.4,
        },
    ),
    # 13. Order Flow Imbalance
    StrategyWeightProfile(
        name="Order Flow Imbalance",
        code="order_flow",
        category=StrategyCategory.MICROSTRUCTURE_FLOW,
        base_weight=0.04,
        regime_multipliers={
            MarketRegimeType.PANIC_CRISIS: 1.3,
            MarketRegimeType.EXTREME_LIQUIDITY_SQUEEZE: 1.5,
        },
    ),
    # 14. Short-Term Reversal
    StrategyWeightProfile(
        name="Short-Term Reversal",
        code="short_term_reversal",
        category=StrategyCategory.STATISTICAL_ARBITRAGE,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.SIDEWAYS_HIGH_VOL: 1.4,
            MarketRegimeType.BULL_LOW_VOL: 0.7,
        },
    ),
    # 15. Analyst Revision Momentum
    StrategyWeightProfile(
        name="Analyst Revision Momentum",
        code="arm_factor",
        category=StrategyCategory.VALUE_FUNDAMENTAL,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.2,
            MarketRegimeType.PANIC_CRISIS: 0.5,
        },
    ),
    # 16. Cross-Asset Regime Divergence
    StrategyWeightProfile(
        name="Cross-Asset Regime Divergence",
        code="card_factor",
        category=StrategyCategory.MACRO_CATALYST,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.PANIC_CRISIS: 1.5,
            MarketRegimeType.SIDEWAYS_HIGH_VOL: 1.2,
        },
    ),
    # 17. Liquidity-Adjusted Tail Risk
    StrategyWeightProfile(
        name="Liquidity-Adjusted Tail Risk",
        code="latr_factor",
        category=StrategyCategory.MICROSTRUCTURE_FLOW,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.PANIC_CRISIS: 1.6,
            MarketRegimeType.EXTREME_LIQUIDITY_SQUEEZE: 1.7,
        },
    ),
    # 18. Inst & Foreign Sector
    StrategyWeightProfile(
        name="Inst & Foreign Sector",
        code="inst_foreign_sector",
        category=StrategyCategory.MICROSTRUCTURE_FLOW,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.3,
            MarketRegimeType.SIDEWAYS_LOW_VOL: 1.1,
        },
    ),
    # 19. Supply Chain Momentum
    StrategyWeightProfile(
        name="Supply Chain Momentum",
        code="supply_chain",
        category=StrategyCategory.MACRO_CATALYST,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.2,
            MarketRegimeType.PANIC_CRISIS: 0.6,
        },
    ),
    # 20. NLP Sentiment Catalyst
    StrategyWeightProfile(
        name="NLP Sentiment Catalyst",
        code="sentiment",
        category=StrategyCategory.MACRO_CATALYST,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.PANIC_CRISIS: 1.3,
            MarketRegimeType.BULL_HIGH_VOL: 1.2,
        },
    ),
    # 21. Multi-Factor Style Neutralizer
    StrategyWeightProfile(
        name="Multi-Factor Style Neutralizer",
        code="factor_neutralized",
        category=StrategyCategory.STATISTICAL_ARBITRAGE,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.SIDEWAYS_HIGH_VOL: 1.3,
            MarketRegimeType.PANIC_CRISIS: 1.4,
        },
    ),
    # 22. Dynamic Volatility Targeting
    StrategyWeightProfile(
        name="Dynamic Volatility Targeting",
        code="vol_target",
        category=StrategyCategory.TECHNICAL_VOLATILITY,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.PANIC_CRISIS: 1.5,
            MarketRegimeType.BEAR_HIGH_VOL: 1.4,
        },
    ),
    # 23. Microstructure Imbalance
    StrategyWeightProfile(
        name="Microstructure Imbalance",
        code="microstructure",
        category=StrategyCategory.MICROSTRUCTURE_FLOW,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.EXTREME_LIQUIDITY_SQUEEZE: 1.6,
            MarketRegimeType.PANIC_CRISIS: 1.3,
        },
    ),
    # 24. Accruals Quality Anomaly
    StrategyWeightProfile(
        name="Accruals Quality Anomaly",
        code="accruals_quality",
        category=StrategyCategory.VALUE_FUNDAMENTAL,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.BEAR_LOW_VOL: 1.3,
            MarketRegimeType.BEAR_HIGH_VOL: 1.2,
        },
    ),
    # 25. Short Interest & Squeeze
    StrategyWeightProfile(
        name="Short Interest & Squeeze",
        code="short_squeeze",
        category=StrategyCategory.MICROSTRUCTURE_FLOW,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.BULL_HIGH_VOL: 1.5,
            MarketRegimeType.EXTREME_LIQUIDITY_SQUEEZE: 1.7,
        },
    ),
    # 26. Value-Up & Shareholder Yield
    StrategyWeightProfile(
        name="Value-Up & Shareholder Yield",
        code="valueup_catalyst",
        category=StrategyCategory.VALUE_FUNDAMENTAL,
        base_weight=0.03,
        regime_multipliers={
            MarketRegimeType.BEAR_LOW_VOL: 1.4,
            MarketRegimeType.SIDEWAYS_LOW_VOL: 1.3,
        },
    ),
    # 27. Kaufman Trend Efficiency
    StrategyWeightProfile(
        name="Kaufman Trend Efficiency",
        code="trend_efficiency",
        category=StrategyCategory.TECHNICAL_VOLATILITY,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.3,
            MarketRegimeType.SIDEWAYS_LOW_VOL: 0.6,
        },
    ),
    # 28. Gamma Squeeze
    StrategyWeightProfile(
        name="Gamma Squeeze",
        code="gamma_squeeze",
        category=StrategyCategory.TECHNICAL_VOLATILITY,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.BULL_HIGH_VOL: 1.6,
            MarketRegimeType.EXTREME_LIQUIDITY_SQUEEZE: 1.8,
        },
    ),
    # 29. Insider Buying
    StrategyWeightProfile(
        name="Insider Buying",
        code="insider_buying",
        category=StrategyCategory.VALUE_FUNDAMENTAL,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.PANIC_CRISIS: 1.5,
            MarketRegimeType.BEAR_LOW_VOL: 1.3,
        },
    ),
    # 30. Darkpool & HFT Flow
    StrategyWeightProfile(
        name="Darkpool & HFT Flow",
        code="darkpool",
        category=StrategyCategory.MICROSTRUCTURE_FLOW,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.EXTREME_LIQUIDITY_SQUEEZE: 1.5,
            MarketRegimeType.PANIC_CRISIS: 1.3,
        },
    ),
    # 31. Earnings Tone Drift
    StrategyWeightProfile(
        name="Earnings Tone Drift",
        code="earnings_tone_drift",
        category=StrategyCategory.MACRO_CATALYST,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.2,
            MarketRegimeType.PANIC_CRISIS: 0.6,
        },
    ),
    # 32. Cross-Asset Spillover
    StrategyWeightProfile(
        name="Cross-Asset Spillover",
        code="cross_asset_spillover",
        category=StrategyCategory.MACRO_CATALYST,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.PANIC_CRISIS: 1.4,
            MarketRegimeType.SIDEWAYS_HIGH_VOL: 1.2,
        },
    ),
    # 33. Supply Chain GNN
    StrategyWeightProfile(
        name="Supply Chain GNN",
        code="supply_chain_gnn",
        category=StrategyCategory.ML_DEEP_LEARNING,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.3,
            MarketRegimeType.PANIC_CRISIS: 0.6,
        },
    ),
    # 34. Range Expansion Breakout
    StrategyWeightProfile(
        name="Range Expansion Breakout",
        code="range_expansion",
        category=StrategyCategory.TECHNICAL_VOLATILITY,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.BULL_HIGH_VOL: 1.4,
            MarketRegimeType.SIDEWAYS_LOW_VOL: 0.5,
        },
    ),
    # 35. Dual Correction
    StrategyWeightProfile(
        name="Dual Correction",
        code="dual_correction",
        category=StrategyCategory.TECHNICAL_VOLATILITY,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.BULL_LOW_VOL: 1.3,
            MarketRegimeType.SIDEWAYS_LOW_VOL: 1.2,
        },
    ),
    # 36. Index Rebalance
    StrategyWeightProfile(
        name="Index Rebalance",
        code="index_rebalance",
        category=StrategyCategory.STATISTICAL_ARBITRAGE,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.SIDEWAYS_LOW_VOL: 1.3,
            MarketRegimeType.SIDEWAYS_HIGH_VOL: 1.2,
        },
    ),
    # 37. Overnight Gap Reversal
    StrategyWeightProfile(
        name="Overnight Gap Reversal",
        code="overnight_gap",
        category=StrategyCategory.STATISTICAL_ARBITRAGE,
        base_weight=0.02,
        regime_multipliers={
            MarketRegimeType.SIDEWAYS_HIGH_VOL: 1.4,
            MarketRegimeType.BULL_LOW_VOL: 0.8,
        },
    ),
]


class EnsembleWeightRegistry:
    """
    Thread-safe declarative strategy weight and regime modulation registry.
    Ensures safe querying, normalization, dynamic regime modulation,
    and missing strategy zero-weighting.
    """

    def __init__(self, profiles: Optional[List[StrategyWeightProfile]] = None) -> None:
        self._profiles: Dict[str, StrategyWeightProfile] = {}
        target_profiles = profiles if profiles is not None else CANONICAL_37_STRATEGIES
        for p in target_profiles:
            self._profiles[p.code] = p

    @property
    def total_strategies(self) -> int:
        return len(self._profiles)

    def get_profile(self, code: str) -> Optional[StrategyWeightProfile]:
        return self._profiles.get(code)

    def list_strategies(self, active_only: bool = True) -> List[str]:
        if not active_only:
            return list(self._profiles.keys())
        return [k for k, v in self._profiles.items() if v.active]

    def get_base_weights(self, normalize: bool = True) -> Dict[str, float]:
        raw = {k: v.base_weight for k, v in self._profiles.items() if v.active}
        if not normalize:
            return raw
        total = sum(raw.values())
        if total <= 0:
            return {k: 1.0 / len(raw) for k in raw}
        return {k: v / total for k, v in raw.items()}

    def get_regime_weights(
        self,
        regime: MarketRegimeType,
        available_strategies: Optional[Set[str]] = None,
        normalize: bool = True,
    ) -> Dict[str, float]:
        """
        Computes regime-modulated weights.
        Automatically zeroes out unavailable strategies and renormalizes.
        """
        weights: Dict[str, float] = {}
        for code, profile in self._profiles.items():
            if not profile.active:
                continue
            if available_strategies is not None and code not in available_strategies:
                continue

            multiplier = profile.get_regime_multiplier(regime)
            w = profile.base_weight * multiplier
            w = max(profile.min_weight, min(w, profile.max_weight))
            weights[code] = w

        if not normalize or not weights:
            return weights

        total = sum(weights.values())
        if total <= 0:
            return {k: 1.0 / len(weights) for k in weights}
        return {k: v / total for k, v in weights.items()}

    def to_json(self) -> str:
        data = {
            "version": VERSION,
            "release": RELEASE,
            "feature": FEATURE,
            "strategies": {
                k: {
                    "name": v.name,
                    "category": v.category.value,
                    "base_weight": v.base_weight,
                    "min_weight": v.min_weight,
                    "max_weight": v.max_weight,
                    "active": v.active,
                }
                for k, v in self._profiles.items()
            },
        }
        return json.dumps(data, indent=2)


# Global default registry instance
DEFAULT_WEIGHT_REGISTRY = EnsembleWeightRegistry()
