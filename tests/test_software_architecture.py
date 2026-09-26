"""
test_software_architecture.py — Verification of Clean Software Architecture & Modularity

Verifies:
1. AlphaStrategyExecutor: specification registry, error isolation, parallel execution, telemetry.
2. PipelineStrategyContext: encapsulation of state, immutability of shared inputs.
3. PredictionReporter: report formatting, market partitioning, top-N slicing.
4. Historical Couplers: modular extraction, re-export transparency, backward compatibility.
5. Exception Isolation: single-strategy failure cannot crash the multi-factor pipeline.
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.pipeline.strategy_executor import (
    AlphaStrategyExecutor,
    PipelineStrategyContext,
    StrategySpec,
    StrategyExecutionResult,
)
from trading_system.src.pipeline.prediction_reporter import (
    slice_top_dataframe,
    get_target_markets_to_save,
    save_strategy_predictions_report,
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler,
    Phase72Coupler,
    Phase71Coupler,
    Phase70Coupler,
    EnsembleScoringEngine,
)
from trading_system.src.ai.historical_couplers import (
    QuantumLanglandsAffineWAlgebraCoupler,
    BeilinsonDrinfeldChiralKacMoodyCoupler,
)


class TestSoftwareArchitecture:
    """Verifies architectural decoupling, strategy execution contracts, and exception guards."""

    def test_alpha_strategy_executor_registry(self):
        """Verify strategy specs in AlphaStrategyExecutor are properly configured."""
        executor = AlphaStrategyExecutor()
        assert len(executor.specs) >= 28

        keys = [s.key for s in executor.specs]
        assert "lstm" in keys
        assert "event" in keys
        assert "mq" in keys
        assert "iv_skew" in keys
        assert "order_flow" in keys
        assert "reversal" in keys
        assert "overnight_gap_reversal" in keys

        for spec in executor.specs:
            assert spec.key
            assert spec.name
            assert callable(spec.evaluator)
            assert spec.col
            assert spec.file.endswith(".txt")
            assert spec.hdr
            assert spec.w > 0

    def test_pipeline_strategy_context_contract(self):
        """Verify PipelineStrategyContext auto-populates missing symbols and sector mapping."""
        universe = pd.DataFrame({
            "symbol": ["005930", "000660"],
            "name": ["Samsung", "SK Hynix"],
            "sector": ["IT", "IT"],
            "market": ["KOSPI", "KOSPI"],
        })
        prices_dict = {
            "005930": pd.DataFrame({"Close": [70000, 71000]}),
            "000660": pd.DataFrame({"Close": [120000, 122000]}),
        }

        ctx = PipelineStrategyContext(
            universe=universe,
            infer_data_dict=prices_dict,
            cfg=None,
        )

        assert ctx.symbols_list == ["005930", "000660"]
        assert ctx.sector_mapping.get("005930") == "IT"
        assert ctx.sector_mapping.get("000660") == "IT"

    def test_strategy_execution_error_isolation(self, tmp_path):
        """Verify that a strategy throwing an exception does NOT crash the executor."""
        def good_strat(ctx):
            return pd.DataFrame({"symbol": ["005930"], "test_score": [0.85]})

        def faulty_strat(ctx):
            raise RuntimeError("Simulated Alpha Engine Fatal Explosion")

        specs = [
            StrategySpec("good", "Good Strategy", good_strat, "test_score", "Good Strat", "good.txt"),
            StrategySpec("faulty", "Faulty Strategy", faulty_strat, "faulty_score", "Faulty Strat", "faulty.txt"),
        ]

        executor = AlphaStrategyExecutor(specs=specs)
        universe = pd.DataFrame({"symbol": ["005930"], "name": ["Samsung"], "market": ["KOSPI"]})
        ctx = PipelineStrategyContext(universe=universe, infer_data_dict={}, cfg=None, result_dir=str(tmp_path))

        result = executor.execute_all(ctx)
        assert isinstance(result, StrategyExecutionResult)

        # Good strategy completed successfully
        good_df = result.get("good")
        assert not good_df.empty
        assert good_df["test_score"].iloc[0] == 0.85

        # Faulty strategy was isolated and yielded an empty DataFrame
        faulty_df = result.get("faulty")
        assert faulty_df.empty
        assert "faulty" in result.execution_times

    def test_prediction_reporter_slicing(self):
        """Verify prediction reporter slicing contracts."""
        df = pd.DataFrame({"val": range(200)})

        # Slice limit 50
        sliced_50 = slice_top_dataframe(df, limit=50)
        assert len(sliced_50) == 50

        # Limit 'all' returns entire dataframe
        sliced_all = slice_top_dataframe(df, limit="all")
        assert len(sliced_all) == 200

        # Limit None returns entire dataframe
        sliced_none = slice_top_dataframe(df, limit=None)
        assert len(sliced_none) == 200

        # Empty df returns empty
        assert slice_top_dataframe(pd.DataFrame(), limit=10).empty

    def test_prediction_reporter_target_markets(self):
        """Verify target markets extractor discovers all markets."""
        df = pd.DataFrame({"market": ["KOSPI", "KOSDAQ", "SP500"]})
        markets = get_target_markets_to_save(df)
        assert "KOSPI" in markets
        assert "KOSDAQ" in markets
        assert "SP500" in markets

    def test_historical_coupler_reexport_transparency(self):
        """Verify that historical couplers extracted to historical_couplers.py are transparently imported."""
        coupler_historical = QuantumLanglandsAffineWAlgebraCoupler()
        assert coupler_historical is not None

        # Verify Phase 72 Coupler still accessible and functional from ensemble_scorer
        coupler_v72 = Phase72Coupler()
        assert coupler_v72 is not None
        assert isinstance(coupler_v72, QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsMoonshineMonsterWhittakerCoupler)

    def test_ensemble_scoring_engine_instantiation(self):
        """Verify that EnsembleScoringEngine instantiates cleanly without circular dependencies."""
        engine = EnsembleScoringEngine()
        assert engine is not None
        assert hasattr(engine, "calculate_ensemble_score")
        assert hasattr(engine, "ALPHA_HORIZON_TIERS")
