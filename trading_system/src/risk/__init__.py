"""
Risk & Institutional Portfolio Allocation Layer
Provides unified access to regime-adaptive multi-model portfolio allocation,
tail-risk budgeting (EVT-CVaR), intraday dynamic stop-loss, and pre-trade gating.
"""

from __future__ import annotations

try:
    from src.risk.risk_manager import RiskLevel, RiskManager, RiskMetrics
    from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
    from src.risk.portfolio_allocator import PortfolioAllocator
    from src.risk.portfolio_optimizer import PortfolioOptimizer
    from src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossSignal, StopLossResult
    from src.risk.pretrade_gatekeeper import PreTradeRiskGatekeeper
    from src.risk.delta_beta_hedge import DeltaBetaHedgeEngine
except ImportError:
    try:
        from trading_system.src.risk.risk_manager import RiskLevel, RiskManager, RiskMetrics
        from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
        from trading_system.src.risk.portfolio_allocator import PortfolioAllocator
        from trading_system.src.risk.portfolio_optimizer import PortfolioOptimizer
        from trading_system.src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossSignal, StopLossResult
        from trading_system.src.risk.pretrade_gatekeeper import PreTradeRiskGatekeeper
        from trading_system.src.risk.delta_beta_hedge import DeltaBetaHedgeEngine
    except ImportError:
        pass

DeltaBetaHedgeOverlay = globals().get("DeltaBetaHedgeEngine", None)

# Phase 116 Avellaneda-Stoikov Controller (F552)
try:
    from src.risk.avellaneda_stoikov_controller import (
        AvellanedaStoikovController,
        AvellanedaStoikovConfig,
    )
except ImportError:
    try:
        from trading_system.src.risk.avellaneda_stoikov_controller import (
            AvellanedaStoikovController,
            AvellanedaStoikovConfig,
        )
    except ImportError:
        pass

# Phase 117 Dynamic Liquidity Risk Parity (F557)
try:
    from src.risk.dynamic_liquidity_risk_parity import (
        DynamicLiquidityRiskParityAllocator,
        LiquidityRiskParityConfig,
        AssetLiquidityMetrics,
        LiquidityRiskParityResult,
    )
except ImportError:
    try:
        from trading_system.src.risk.dynamic_liquidity_risk_parity import (
            DynamicLiquidityRiskParityAllocator,
            LiquidityRiskParityConfig,
            AssetLiquidityMetrics,
            LiquidityRiskParityResult,
        )
    except ImportError:
        pass

# Phase 118 Cross-Asset Lead-Lag Graph Flow Liquidity Rebalancing Allocator (F562)
try:
    from src.risk.cross_asset_graph_flow_allocator import (
        CrossAssetGraphFlowAllocator,
        GraphFlowConfig,
        GraphCentralityMetrics,
        GraphRebalancingResult,
        AssetClassType,
    )
except ImportError:
    try:
        from trading_system.src.risk.cross_asset_graph_flow_allocator import (
            CrossAssetGraphFlowAllocator,
            GraphFlowConfig,
            GraphCentralityMetrics,
            GraphRebalancingResult,
            AssetClassType,
        )
    except ImportError:
        pass

__all__ = [
    # Core Risk Management & Allocators
    "RiskLevel",
    "RiskManager",
    "RiskMetrics",
    "UnifiedPortfolioAllocator",
    "PortfolioAllocator",
    "PortfolioOptimizer",
    "IntradayStopLossEngine",
    "StopLossSignal",
    "StopLossResult",
    "PreTradeRiskGatekeeper",
    "DeltaBetaHedgeEngine",
    "DeltaBetaHedgeOverlay",
    # Phase 116 Exports (F552)
    "AvellanedaStoikovController",
    "AvellanedaStoikovConfig",
    # Phase 117 Exports (F557)
    "DynamicLiquidityRiskParityAllocator",
    "LiquidityRiskParityConfig",
    "AssetLiquidityMetrics",
    "LiquidityRiskParityResult",
    # Phase 118 Exports (F562)
    "CrossAssetGraphFlowAllocator",
    "GraphFlowConfig",
    "GraphCentralityMetrics",
    "GraphRebalancingResult",
    "AssetClassType",
    # Phase 119 Exports (F566)
    "QuantumAnnealingPortfolioOptimizer",
    "QuantumAnnealingConfig",
    "QuantumPortfolioAllocationResult",
    "CombinatorialConstraints",
    # Phase 120 Exports (F572)
    "RiemannianManifoldPortfolioAllocator",
    "RiemannianAllocatorConfig",
    "RiemannianOptimizationResult",
    "GeodesicLelandBand",
    "HyperbolicityDiagnostics",
    "CurvatureRegime",
    "BypassAction",
    "RiemannianProfile",
    "get_market_profile",
    "geodesic_distance",
    "compute_gromov_hyperbolicity",
    "apply_geodesic_leland_bands",
    # Phase 121 Exports (F577)
    "SymplecticManifoldHMCAllocator",
    "SymplecticAllocatorConfig",
    "SymplecticOptimizationResult",
    "SymplecticProfile",
    "AllocationMode",
    "MetricType",
    "get_symplectic_profile",
    "run_symplectic_allocation",
]

# Phase 119 Quantum-Inspired Annealing Portfolio Combinatorial Optimizer (F566)
try:
    from src.risk.quantum_annealing_portfolio_optimizer import (
        QuantumAnnealingPortfolioOptimizer,
        QuantumAnnealingConfig,
        QuantumPortfolioAllocationResult,
        CombinatorialConstraints,
    )
except ImportError:
    try:
        from trading_system.src.risk.quantum_annealing_portfolio_optimizer import (
            QuantumAnnealingPortfolioOptimizer,
            QuantumAnnealingConfig,
            QuantumPortfolioAllocationResult,
            CombinatorialConstraints,
        )
    except ImportError:
        pass

# Phase 120 Curvature-Aware Riemannian Manifold Portfolio Allocator (F572)
try:
    from src.risk.riemannian_manifold_portfolio_allocator import (
        RiemannianManifoldPortfolioAllocator,
        RiemannianAllocatorConfig,
        RiemannianOptimizationResult,
        GeodesicLelandBand,
        HyperbolicityDiagnostics,
        CurvatureRegime,
        BypassAction,
        RiemannianProfile,
        get_market_profile,
        geodesic_distance,
        compute_gromov_hyperbolicity,
        apply_geodesic_leland_bands,
    )
except ImportError:
    try:
        from trading_system.src.risk.riemannian_manifold_portfolio_allocator import (
            RiemannianManifoldPortfolioAllocator,
            RiemannianAllocatorConfig,
            RiemannianOptimizationResult,
            GeodesicLelandBand,
            HyperbolicityDiagnostics,
            CurvatureRegime,
            BypassAction,
            RiemannianProfile,
            get_market_profile,
            geodesic_distance,
            compute_gromov_hyperbolicity,
            apply_geodesic_leland_bands,
        )
    except ImportError:
        pass

# Phase 121 Symplectic Manifold Hamiltonian Monte Carlo Allocator (F577)
try:
    from src.risk.symplectic_hamiltonian_allocator import (
        SymplecticManifoldHMCAllocator,
        SymplecticAllocatorConfig,
        SymplecticOptimizationResult,
        SymplecticProfile,
        AllocationMode,
        MetricType,
        get_symplectic_profile,
        run_symplectic_allocation,
    )
except ImportError:
    try:
        from trading_system.src.risk.symplectic_hamiltonian_allocator import (
            SymplecticManifoldHMCAllocator,
            SymplecticAllocatorConfig,
            SymplecticOptimizationResult,
            SymplecticProfile,
            AllocationMode,
            MetricType,
            get_symplectic_profile,
            run_symplectic_allocation,
        )
    except ImportError:
        pass


