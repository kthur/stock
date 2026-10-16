"""
AI & Quantitative Modeling Layer
Provides unified access to machine learning prediction models (XGBoost/LSTM/Surge),
cross-sectional score normalization, factor orthogonalization, ensemble scoring engines,
dynamic macro factor timing, and vectorized tensor score normalizers.
"""

from __future__ import annotations

try:
    from src.ai.prediction_model import OnDevicePredictionModel
    from src.ai.ensemble_scorer import EnsembleScoringEngine
    from src.ai.score_normalizer import CrossSectionalScoreNormalizer
    from src.ai.vectorized_score_normalizer import VectorizedScoreNormalizer
    from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
    from src.ai.factor_suppression import FactorSuppressionEngine
    from src.ai.llm_earnings_agent import LLMEarningsAgent
    from src.ai.llm_integration import InvestmentOpinion, LLMEngine, SentimentType
    from src.ai.sentiment import SentimentAnalyzer
    from src.ai.macro_factor_timing import (
        DynamicMacroFactorTimingEngine,
        MacroFactorTimingEngine,
        Phase106MacroFactorTimingEngine,
        MacroConditioningEngine,
        modulate_macro_factor_weights,
    )
except ImportError:
    from trading_system.src.ai.prediction_model import OnDevicePredictionModel
    from trading_system.src.ai.ensemble_scorer import EnsembleScoringEngine
    from trading_system.src.ai.score_normalizer import CrossSectionalScoreNormalizer
    from trading_system.src.ai.vectorized_score_normalizer import VectorizedScoreNormalizer
    from trading_system.src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
    from trading_system.src.ai.factor_suppression import FactorSuppressionEngine
    from trading_system.src.ai.llm_earnings_agent import LLMEarningsAgent
    from trading_system.src.ai.llm_integration import InvestmentOpinion, LLMEngine, SentimentType
    from trading_system.src.ai.sentiment import SentimentAnalyzer
    from trading_system.src.ai.macro_factor_timing import (
        DynamicMacroFactorTimingEngine,
        MacroFactorTimingEngine,
        Phase106MacroFactorTimingEngine,
        MacroConditioningEngine,
        modulate_macro_factor_weights,
    )

__all__ = [
    "OnDevicePredictionModel",
    "EnsembleScoringEngine",
    "CrossSectionalScoreNormalizer",
    "VectorizedScoreNormalizer",
    "FactorOrthogonalizerEngine",
    "FactorSuppressionEngine",
    "LLMEarningsAgent",
    "InvestmentOpinion",
    "LLMEngine",
    "SentimentAnalyzer",
    "SentimentType",
    "DynamicMacroFactorTimingEngine",
    "MacroFactorTimingEngine",
    "Phase106MacroFactorTimingEngine",
    "MacroConditioningEngine",
    "modulate_macro_factor_weights",
]
