"""
tests/test_phase14_portfolio_execution.py

Unit test suite for Phase 14 Omnipotent (v21 Production Master) Portfolio Allocation & Execution:
- Feature F77.1: Grothendieck Motives & Quantum Information Geometric Fisher-Rao Barycenter Blending
- Feature F77.1: Infinite-Order Super-Coherent Tail Risk Measure (Infinite-EVaR)
- Feature F77.2: 98% Preemptive Darkpool Routing & Navier-Stokes Order Flow Hydrodynamics
- Feature F77.2: Micro-Tick Preemptive Shading in ExecutionOMSEngine
- SmartOrderRouter version=14 verification
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.core.fast_lob_engine import DeepHawkesArrivalProcess
from src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler
from src.execution.smart_order_router import SmartOrderRouter


class TestPhase14PortfolioExecution:
    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    def test_grothendieck_fisher_rao_barycenter_blend_basic(self, allocator):
        # 4 models: BL, HERC, RP, CVaR
        input_weights = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        res = allocator.compute_grothendieck_fisher_rao_barycenter_blend(input_weights)
        assert isinstance(res, dict)
        assert len(res) == 4
        for k in ["bl", "herc", "rp", "cvar"]:
            assert k in res
            assert res[k] > 0.0
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)

    def test_grothendieck_fisher_rao_barycenter_blend_multi_distribution(self, allocator):
        dist1 = {"bl": 0.40, "herc": 0.30, "rp": 0.15, "cvar": 0.15}
        dist2 = {"bl": 0.10, "herc": 0.20, "rp": 0.30, "cvar": 0.40}
        res = allocator.compute_grothendieck_motive_barycenter([dist1, dist2])
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-5)
        # CVaR should have strong presence due to higher motive weight (mu_motive[3]=1.55)
        assert res["cvar"] > 0.15

    def test_infinite_evar_coherent_hierarchy(self, allocator):
        np.random.seed(42)
        # Generate heavy-tailed fat loss distribution
        returns = np.random.standard_t(df=3.0, size=200) * 0.02
        res = allocator.compute_infinite_evar_risk_measure(returns, alpha=0.05, xi_inf=0.30)

        var_val = res["var_value"]
        cvar_val = res["cvar_value"]
        evar_val = res["evar_value"]
        super_evar_val = res["super_evar_value"]
        ultra_evar_val = res["ultra_evar_value"]
        trans_evar_val = res["transfinite_evar_value"]
        inf_evar_val = res["infinite_evar_value"]

        # Strictly satisfies the coherent tail risk hierarchy:
        # VaR <= CVaR <= EVaR <= Super-EVaR <= Ultra-EVaR <= Transfinite-EVaR <= Infinite-EVaR
        assert cvar_val >= var_val - 1e-5
        assert evar_val >= cvar_val - 1e-5
        assert super_evar_val >= evar_val - 1e-5
        assert ultra_evar_val >= super_evar_val - 1e-5
        assert trans_evar_val >= ultra_evar_val - 1e-5
        assert inf_evar_val >= trans_evar_val - 1e-5

    def test_infinite_evar_monotonicity_and_edge_cases(self, allocator):
        np.random.seed(123)
        returns = np.random.normal(0, 0.02, size=150)

        # Monotonicity with respect to alpha (smaller alpha -> higher risk)
        res_01 = allocator.compute_infinite_evar_risk_measure(returns, alpha=0.01)
        res_05 = allocator.compute_infinite_evar_risk_measure(returns, alpha=0.05)
        assert res_01["infinite_evar_value"] >= res_05["infinite_evar_value"] - 1e-6

        # Monotonicity with respect to xi_inf (higher shape param -> higher risk)
        res_xi_low = allocator.compute_infinite_evar_risk_measure(returns, xi_inf=0.10)
        res_xi_high = allocator.compute_infinite_evar_risk_measure(returns, xi_inf=0.45)
        assert res_xi_high["infinite_evar_value"] >= res_xi_low["infinite_evar_value"] - 1e-6

        # Edge cases: empty array and zeros
        res_empty = allocator.compute_infinite_evar_risk_measure(np.array([]))
        assert math.isfinite(res_empty["infinite_evar_value"])

        res_zeros = allocator.compute_infinite_evar_risk_measure(np.zeros(50))
        assert math.isfinite(res_zeros["infinite_evar_value"])

    def test_information_theoretic_blend_weights_v14(self, allocator):
        regime = {"BULL_LOW_VOL": 0.3, "CRISIS": 0.7}
        blend = allocator.compute_information_theoretic_blend_weights(
            regime=regime,
            crisis_severity=0.7,
            version=14
        )
        assert isinstance(blend, dict)
        assert math.isclose(sum(blend.values()), 1.0, abs_tol=1e-5)
        # Under crisis and v14, CVaR and HERC should dominate BL and RP
        assert blend["cvar"] > blend["bl"]
        assert blend["cvar"] > blend["rp"]

    def test_optimize_multi_model_blend_v14(self, allocator):
        np.random.seed(42)
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        n = len(symbols)
        returns_df = pd.DataFrame(
            np.random.normal(0.001, 0.02, size=(60, n)),
            columns=symbols
        )
        cov_matrix = returns_df.cov().values
        preds = np.array([0.05, 0.03, 0.04, 0.02, 0.06])
        cascade_vec = np.array([0.1, 0.4, 0.2, 0.8, 0.05])

        w = allocator.optimize_multi_model_blend(
            predicted_returns=preds,
            returns_df=returns_df,
            cov_matrix=cov_matrix,
            symbols=symbols,
            version=14,
            asset_cascade_vector=cascade_vec
        )
        assert len(w) == n
        assert np.all(w >= 0.0)
        assert math.isclose(float(np.sum(w)), 1.0, abs_tol=1e-4)

    def test_fast_lob_dark_routing_cap_v14(self):
        process = DeepHawkesArrivalProcess()
        process.lambda_state = np.array([10.0, 0.5, 0.2])  # LIT=10.0, ATS=0.5, DARK=0.2
        ratio_res = process.compute_preemptive_dark_routing(version=14)
        assert ratio_res["preemptive_dark_routing_ratio"] <= 0.98
        assert ratio_res["preemptive_dark_routing_ratio"] >= 0.65
        # Test alias
        alias_res = process.calculate_preemptive_dark_ratio(version=14)
        assert alias_res["preemptive_dark_routing_ratio"] == ratio_res["preemptive_dark_routing_ratio"]

    def test_oms_hawkes_shading_v14(self):
        oms = ExecutionOMSEngine()
        scheduler = AlmgrenChrissScheduler()

        # Test ExecutionOMSEngine peg price with h_val > 0.18
        peg_oms = oms.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.40},
            version=14
        )
        assert 99.5 <= peg_oms <= 100.5

        peg_sched = scheduler.calculate_peg_limit_price(
            target_price=100.0,
            bid_price=99.5,
            ask_price=100.5,
            action="BUY",
            hawkes_intensity={"cross_excitation_toxicity": 0.40},
            version=14
        )
        assert 99.5 <= peg_sched <= 100.5

    def test_smart_order_router_v14(self):
        sor = SmartOrderRouter()
        plan = {
            "symbol": "005930",
            "action": "BUY",
            "quantity": 1000,
            "target_price": 70000.0,
            "market_spread_bps": 10.0,
            "gamma_toxic_dir": 0.90,
            "darkpool_score": 0.85,
            "version": 14
        }
        res = sor.route_order(plan, ats_available=True)
        legs = res.get("legs", [])
        assert len(legs) >= 1
        # In v14 with extreme toxicity, dark leg allocation should expand towards 0.98
        dark_legs = [l for l in legs if "DARK" in l.get("venue_type", "")]
        assert len(dark_legs) > 0
        assert dark_legs[0]["quantity"] >= 800
        # anti gaming active
        assert dark_legs[0].get("anti_gaming_active", False) is True
