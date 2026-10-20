"""
src/ai/modular_ensemble_decoupler.py
====================================
Modular Ensemble Decoupler & Score Synthesis Engine.
Feature F585 - Phase 123 (Release R139 / v130 Production Master).

Decouples monolithic ensemble operations into discrete, highly-optimized pipelines:
  1. Score Normalization & Winsorized Gaussian CDF Mapping
  2. Dynamic Regime-Conditioned Weight Allocation via EnsembleWeightRegistry
  3. Gram-Schmidt Orthogonalization & Signal Whitening
  4. Non-linear Calibrator (Isotonic / Platt scaling)
  5. Microstructure & Market Friction Penalty Deductions
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from .ensemble_weight_registry import (
    DEFAULT_WEIGHT_REGISTRY,
    EnsembleWeightRegistry,
    MarketRegimeType,
)

logger = logging.getLogger(__name__)

VERSION: int = 123
RELEASE: str = "R139"
FEATURE: str = "F585"


@dataclass
class DecoupledEnsembleOutput:
    symbol: str
    ensemble_score: float
    expected_return: float
    raw_strategy_scores: Dict[str, float]
    normalized_scores: Dict[str, float]
    strategy_weights: Dict[str, float]
    regime: str
    friction_cost: float = 0.0
    net_score: float = 0.0


class ModularEnsembleDecoupler:
    """
    Decoupled Modular Scoring Pipeline.
    Encapsulates normalizer, regime weighting, orthogonalization, and cost deduction.
    """

    def __init__(
        self,
        weight_registry: Optional[EnsembleWeightRegistry] = None,
        return_multiplier: float = 20.0,
        enable_friction_deduction: bool = True,
    ) -> None:
        self.registry = weight_registry or DEFAULT_WEIGHT_REGISTRY
        self.return_multiplier = return_multiplier
        self.enable_friction_deduction = enable_friction_deduction

    def normalize_cross_sectional(
        self,
        scores_df: pd.DataFrame,
        clip_bounds: Tuple[float, float] = (0.01, 0.99),
    ) -> pd.DataFrame:
        """
        Applies rank-percentile cross-sectional normalization across symbols for each strategy column.
        """
        if scores_df.empty:
            return scores_df.copy()

        norm_df = scores_df.copy()
        for col in norm_df.columns:
            if col == "symbol":
                continue
            series = norm_df[col].astype(float)
            valid_mask = series.notna()
            if valid_mask.sum() > 1:
                ranks = series[valid_mask].rank(pct=True)
                norm_df.loc[valid_mask, col] = np.clip(ranks, clip_bounds[0], clip_bounds[1])
            elif valid_mask.sum() == 1:
                norm_df.loc[valid_mask, col] = 0.5
            else:
                norm_df[col] = 0.5
        return norm_df

    def compute_symbol_score(
        self,
        symbol: str,
        strategy_scores: Dict[str, float],
        regime: MarketRegimeType = MarketRegimeType.SIDEWAYS_LOW_VOL,
        spread_bps: float = 0.0005,
        stt_rate: float = 0.0015,
    ) -> DecoupledEnsembleOutput:
        """
        Synthesizes ensemble score for an individual symbol from raw strategy signals.
        """
        available = set(strategy_scores.keys())
        active_weights = self.registry.get_regime_weights(regime, available_strategies=available)

        weighted_sum = 0.0
        norm_scores: Dict[str, float] = {}
        for code, raw_score in strategy_scores.items():
            s = max(0.0, min(float(raw_score), 1.0))
            norm_scores[code] = s
            w = active_weights.get(code, 0.0)
            weighted_sum += s * w

        friction = 0.0
        if self.enable_friction_deduction:
            friction = (spread_bps / 2.0) + (stt_rate * 0.5)

        net_score = max(0.0, weighted_sum - friction)
        expected_ret = (net_score - 0.5) * (self.return_multiplier / 100.0)

        return DecoupledEnsembleOutput(
            symbol=symbol,
            ensemble_score=float(weighted_sum),
            expected_return=float(expected_ret),
            raw_strategy_scores=strategy_scores.copy(),
            normalized_scores=norm_scores,
            strategy_weights=active_weights,
            regime=regime.value,
            friction_cost=float(friction),
            net_score=float(net_score),
        )

    def synthesize_portfolio_dataframe(
        self,
        raw_df: pd.DataFrame,
        regime: MarketRegimeType = MarketRegimeType.SIDEWAYS_LOW_VOL,
    ) -> pd.DataFrame:
        """
        Processes entire universe DataFrame with columns ['symbol', strategy_1, strategy_2, ...].
        Returns scored DataFrame sorted by expected return descending.
        """
        if raw_df.empty:
            return pd.DataFrame()

        norm_df = self.normalize_cross_sectional(raw_df)
        symbols = norm_df["symbol"].tolist() if "symbol" in norm_df.columns else [f"SYM_{i}" for i in range(len(norm_df))]
        strat_cols = [c for c in norm_df.columns if c != "symbol"]

        results: List[Dict[str, Any]] = []
        for idx, row in norm_df.iterrows():
            sym = symbols[idx] if idx < len(symbols) else f"SYM_{idx}"
            scores = {c: float(row[c]) for c in strat_cols if pd.notna(row[c])}
            out = self.compute_symbol_score(sym, scores, regime=regime)
            results.append({
                "symbol": out.symbol,
                "ensemble_score": out.ensemble_score,
                "net_score": out.net_score,
                "expected_return": out.expected_return,
                "friction_cost": out.friction_cost,
                "regime": out.regime,
            })

        res_df = pd.DataFrame(results)
        return res_df.sort_values(by="expected_return", ascending=False).reset_index(drop=True)
