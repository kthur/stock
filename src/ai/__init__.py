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

# Phase 116 Microstructure Alpha Engines (F550 & F551)
try:
    from src.ai.hawkes_microstructure_engine import (
        HawkesMicrostructureEngine,
        HawkesChannel,
        MicrostructureEvent,
        HawkesParameters4D,
        HawkesIntensitySnapshot,
        HawkesFitResult,
    )
    from src.ai.microprice_drift_forecaster import (
        MicropriceDriftForecaster,
        MicropriceDriftConfig,
        DriftProjection,
        MicropriceForecasterOutput,
    )
except ImportError:
    try:
        from trading_system.src.ai.hawkes_microstructure_engine import (
            HawkesMicrostructureEngine,
            HawkesChannel,
            MicrostructureEvent,
            HawkesParameters4D,
            HawkesIntensitySnapshot,
            HawkesFitResult,
        )
        from trading_system.src.ai.microprice_drift_forecaster import (
            MicropriceDriftForecaster,
            MicropriceDriftConfig,
            DriftProjection,
            MicropriceForecasterOutput,
        )
    except ImportError:
        pass

# Phase 117 AI Modeling Engines (F555 & F556)
try:
    from src.ai.diffusion_denoiser_engine import (
        DiffusionDenoiserEngine,
        DiffusionDenoiserConfig,
        SdeType,
        TimeDecomposition,
        DiffusionDenoiserOutput,
    )
    from src.ai.lob_transformer_engine import (
        LOBTransformerEngine,
        LOBTransformerConfig,
        PriceDirection,
        HorizonPrediction,
        LOBAttentionHeatmap,
        LOBTransformerOutput,
    )
except ImportError:
    try:
        from trading_system.src.ai.diffusion_denoiser_engine import (
            DiffusionDenoiserEngine,
            DiffusionDenoiserConfig,
            SdeType,
            TimeDecomposition,
            DiffusionDenoiserOutput,
        )
        from trading_system.src.ai.lob_transformer_engine import (
            LOBTransformerEngine,
            LOBTransformerConfig,
            PriceDirection,
            HorizonPrediction,
            LOBAttentionHeatmap,
            LOBTransformerOutput,
        )
    except ImportError:
        pass

# Phase 118 Neural SDE Volatility Forecaster (F561)
try:
    from src.ai.neural_sde_volatility_forecaster import (
        NeuralSDEVolatilityForecaster,
        NeuralSDEConfig,
        JumpProcessType,
        VolatilitySurface,
        JumpDiffusionOutput,
    )
except ImportError:
    try:
        from trading_system.src.ai.neural_sde_volatility_forecaster import (
            NeuralSDEVolatilityForecaster,
            NeuralSDEConfig,
            JumpProcessType,
            VolatilitySurface,
            JumpDiffusionOutput,
        )
    except ImportError:
        pass

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
    # Phase 116 Exports (F550 & F551)
    "HawkesMicrostructureEngine",
    "HawkesChannel",
    "MicrostructureEvent",
    "HawkesParameters4D",
    "HawkesIntensitySnapshot",
    "HawkesFitResult",
    "MicropriceDriftForecaster",
    "MicropriceDriftConfig",
    "DriftProjection",
    "MicropriceForecasterOutput",
    # Phase 117 Exports (F555 & F556)
    "DiffusionDenoiserEngine",
    "DiffusionDenoiserConfig",
    "SdeType",
    "TimeDecomposition",
    "DiffusionDenoiserOutput",
    "LOBTransformerEngine",
    "LOBTransformerConfig",
    "PriceDirection",
    "HorizonPrediction",
    "LOBAttentionHeatmap",
    "LOBTransformerOutput",
    # Phase 118 Exports (F561)
    "NeuralSDEVolatilityForecaster",
    "NeuralSDEConfig",
    "JumpProcessType",
    "VolatilitySurface",
    "JumpDiffusionOutput",
    # Phase 119 Exports (F565)
    "TemporalGATLeadLagForecaster",
    "TemporalGATConfig",
    "GATDriftPrediction",
    "CrossMarketFlowEdge",
    "GATForecasterOutput",
    # Phase 120 Exports (F570 & F571)
    "PINOFluidPriceDiscoveryEngine",
    "PINOFluidConfig",
    "PINOFluidForecastResult",
    "FluidRegime",
    "SpectralConv1dNumPy",
    "SpectralConv2dNumPy",
    "PINONetworkNumPy",
    "MFDFASingularityAlphaEngine",
    "MFDFAConfig",
    "SingularitySpectrumResult",
    "LongMemoryAlphaVector",
    "FractalRegime",
    "FragilityAlertLevel",
    # Phase 121 Exports (F575)
    "PathSignatureAlphaEngine",
    "PathSignatureConfig",
    "PathSignatureOutput",
    "SignatureResult",
    "RoughHurstResult",
    "LevyAreaResult",
    "RoughVolatilityRegime",
    "RoughFragilityLevel",
    "ContinuousRoughPathSignatureForecaster",
    "RoughPathSignatureAlphaEngine",
    # Phase 121 Exports (F576)
    "MARLLiquidityHarvester",
    "MARLHarvesterConfig",
    "MARLLiquidityConfig",
    "HarvesterQuoteResult",
    "MARLHarvestingOutput",
    "InternalNettingResult",
    "NettingResult",
    "AgentObservation",
    "AgentAction",
    "QuoteAction",
    "AgentRole",
    "ToxicityLevel",
    "QuoteSide",
    "MultiAgentReinforcementLearningHarvester",
    "DecPOMDPLiquidityEngine",
    "AdaptiveLiquidityHarvester",
]

# Phase 119 Temporal GAT Forecaster (F565)
try:
    from src.ai.temporal_gat_lead_lag_forecaster import (
        TemporalGATLeadLagForecaster,
        TemporalGATConfig,
        GATDriftPrediction,
        CrossMarketFlowEdge,
        GATForecasterOutput,
    )
except ImportError:
    try:
        from trading_system.src.ai.temporal_gat_lead_lag_forecaster import (
            TemporalGATLeadLagForecaster,
            TemporalGATConfig,
            GATDriftPrediction,
            CrossMarketFlowEdge,
            GATForecasterOutput,
        )
    except ImportError:
        pass

# Phase 120 PINO Fluid Price Discovery & MF-DFA Singularity Alpha (F570 & F571)
try:
    from src.ai.pino_fluid_price_discovery import (
        PINOFluidPriceDiscoveryEngine,
        PINOFluidConfig,
        PINOFluidForecastResult,
        FluidRegime,
        SpectralConv1dNumPy,
        SpectralConv2dNumPy,
        PINONetworkNumPy,
    )
    from src.ai.mfdfa_singularity_alpha_engine import (
        MFDFASingularityAlphaEngine,
        MFDFAConfig,
        SingularitySpectrumResult,
        LongMemoryAlphaVector,
        FractalRegime,
        FragilityAlertLevel,
    )
except ImportError:
    try:
        from trading_system.src.ai.pino_fluid_price_discovery import (
            PINOFluidPriceDiscoveryEngine,
            PINOFluidConfig,
            PINOFluidForecastResult,
            FluidRegime,
            SpectralConv1dNumPy,
            SpectralConv2dNumPy,
            PINONetworkNumPy,
        )
        from trading_system.src.ai.mfdfa_singularity_alpha_engine import (
            MFDFASingularityAlphaEngine,
            MFDFAConfig,
            SingularitySpectrumResult,
            LongMemoryAlphaVector,
            FractalRegime,
            FragilityAlertLevel,
        )
    except ImportError:
        pass

# Phase 121 Path Signature Alpha Engine (F575)
try:
    from src.ai.path_signature_alpha_engine import (
        PathSignatureAlphaEngine,
        PathSignatureConfig,
        PathSignatureOutput,
        SignatureResult,
        RoughHurstResult,
        LevyAreaResult,
        RoughVolatilityRegime,
        RoughFragilityLevel,
        ContinuousRoughPathSignatureForecaster,
        RoughPathSignatureAlphaEngine,
    )
except ImportError:
    try:
        from trading_system.src.ai.path_signature_alpha_engine import (
            PathSignatureAlphaEngine,
            PathSignatureConfig,
            PathSignatureOutput,
            SignatureResult,
            RoughHurstResult,
            LevyAreaResult,
            RoughVolatilityRegime,
            RoughFragilityLevel,
            ContinuousRoughPathSignatureForecaster,
            RoughPathSignatureAlphaEngine,
        )
    except ImportError:
        pass

# Phase 121 MARL Liquidity Harvester (F576)
try:
    from src.ai.marl_liquidity_harvester import (
        MARLLiquidityHarvester,
        MARLHarvesterConfig,
        MARLLiquidityConfig,
        HarvesterQuoteResult,
        MARLHarvestingOutput,
        InternalNettingResult,
        NettingResult,
        AgentObservation,
        AgentAction,
        QuoteAction,
        AgentRole,
        ToxicityLevel,
        QuoteSide,
        MultiAgentReinforcementLearningHarvester,
        DecPOMDPLiquidityEngine,
        AdaptiveLiquidityHarvester,
    )
except ImportError:
    try:
        from trading_system.src.ai.marl_liquidity_harvester import (
            MARLLiquidityHarvester,
            MARLHarvesterConfig,
            MARLLiquidityConfig,
            HarvesterQuoteResult,
            MARLHarvestingOutput,
            InternalNettingResult,
            NettingResult,
            AgentObservation,
            AgentAction,
            QuoteAction,
            AgentRole,
            ToxicityLevel,
            QuoteSide,
            MultiAgentReinforcementLearningHarvester,
            DecPOMDPLiquidityEngine,
            AdaptiveLiquidityHarvester,
        )
    except ImportError:
        pass

# Phase 122 Score-Based Diffusion Volatility Surface Forecaster (F580)
try:
    from src.ai.diffusion_volatility_surface_forecaster import (
        ScoreDiffusionVolatilityForecaster,
        DiffusionVolatilitySurfaceForecaster,
        DiffusionVolatilityEngine,
        DiffusionVolatilityConfig,
        VolatilitySurfaceOutput,
        SDEType,
    )
except ImportError:
    try:
        from trading_system.src.ai.diffusion_volatility_surface_forecaster import (
            ScoreDiffusionVolatilityForecaster,
            DiffusionVolatilitySurfaceForecaster,
            DiffusionVolatilityEngine,
            DiffusionVolatilityConfig,
            VolatilitySurfaceOutput,
            SDEType,
        )
    except ImportError:
        pass

# Phase 122 Hawkes Cross-Excitation & Queue Imbalance Alpha Engine (F581)
try:
    from src.ai.hawkes_cross_excitation_alpha_engine import (
        HawkesCrossExcitationAlphaEngine,
        HawkesCrossExcitationEngine,
        HawkesQueueImbalanceEngine,
        HawkesConfig,
        HawkesAlphaOutput,
        MarketNode,
        FlowDirection,
    )
except ImportError:
    try:
        from trading_system.src.ai.hawkes_cross_excitation_alpha_engine import (
            HawkesCrossExcitationAlphaEngine,
            HawkesCrossExcitationEngine,
            HawkesQueueImbalanceEngine,
            HawkesConfig,
            HawkesAlphaOutput,
            MarketNode,
            FlowDirection,
        )
    except ImportError:
        pass

# Phase 123 Modular Ensemble Decoupler & Strategy Weight Registry (F585)
try:
    from src.ai.ensemble_weight_registry import (
        EnsembleWeightRegistry,
        StrategyWeightProfile,
        StrategyCategory,
        MarketRegimeType,
        CANONICAL_37_STRATEGIES,
        DEFAULT_WEIGHT_REGISTRY,
    )
    from src.ai.modular_ensemble_decoupler import (
        ModularEnsembleDecoupler,
        DecoupledEnsembleOutput,
    )
except ImportError:
    try:
        from trading_system.src.ai.ensemble_weight_registry import (
            EnsembleWeightRegistry,
            StrategyWeightProfile,
            StrategyCategory,
            MarketRegimeType,
            CANONICAL_37_STRATEGIES,
            DEFAULT_WEIGHT_REGISTRY,
        )
        from trading_system.src.ai.modular_ensemble_decoupler import (
            ModularEnsembleDecoupler,
            DecoupledEnsembleOutput,
        )
    except ImportError:
        pass

