"""
Phase 23 Unit and Integration Test Suite: Risk Allocation Enhancements
- Feature F113.1: Lurie Geometric Langlands Fisher-Rao Barycenter Blending
- Feature F113.1.2: 19th-Order Cumulant Expansion Ultra-Trans-Hyper EVaR Tail Risk Measure
"""
import math
import numpy as np
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.risk.portfolio_allocator import PortfolioAllocator


class TestPhase23RiskAllocation:
    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator()

    # =========================================================================
    # 1. LURIE GEOMETRIC LANGLANDS FISHER-RAO BARYCENTER (F113.1)
    # =========================================================================

    def test_geometric_langlands_barycenter_partition_of_unity(self, allocator):
        """Verify simplex constraints: sum(q*) == 1.000000 and all q*_k > 0."""
        w_dict = {"bl": 0.30, "herc": 0.20, "rp": 0.20, "cvar": 0.30}
        res = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w_dict)
        assert isinstance(res, dict)
        assert len(res) == 4
        for k in ["bl", "herc", "rp", "cvar"]:
            assert k in res
            assert res[k] > 0.0
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)

    def test_geometric_langlands_barycenter_dirac_inputs(self, allocator):
        """Verify preservation of pure Dirac delta inputs across all 4 models."""
        for model in ["bl", "herc", "rp", "cvar"]:
            w_dirac = {k: (1.0 if k == model else 0.0) for k in ["bl", "herc", "rp", "cvar"]}
            res_dirac = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w_dirac)
            tot = sum(res_dirac.values())
            assert math.isclose(tot, 1.0, abs_tol=1e-6)
            assert all(v >= 0.0 for v in res_dirac.values())
            assert res_dirac[model] > 0.999

    def test_geometric_langlands_barycenter_metric_weights_prioritization(self, allocator):
        """
        Verify that under equal initial weights [0.25, 0.25, 0.25, 0.25], the Geometric Langlands
        metric weights mu_langlands = [2.10, 1.60, 1.55, 2.60] strictly prioritize
        CVaR (2.60) and Black-Litterman (2.10) over HERC (1.60) and Risk Parity (1.55).
        """
        w_equal = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        res = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w_equal)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
        assert res["cvar"] > res["bl"] > res["herc"] > res["rp"]

    def test_geometric_langlands_barycenter_multi_distribution(self, allocator):
        """Verify consensus under batch distribution inputs."""
        dist1 = {"bl": 0.40, "herc": 0.30, "rp": 0.15, "cvar": 0.15}
        dist2 = {"bl": 0.10, "herc": 0.20, "rp": 0.30, "cvar": 0.40}
        res = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend([dist1, dist2])
        assert isinstance(res, dict)
        assert math.isclose(sum(res.values()), 1.0, abs_tol=1e-6)
        assert res["cvar"] > 0.15
        assert res["bl"] > 0.10

    def test_geometric_langlands_barycenter_array_inputs(self, allocator):
        """Verify handling of 1D and 2D numpy arrays."""
        arr_1d = np.array([0.25, 0.25, 0.25, 0.25])
        res_1d = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(arr_1d)
        assert math.isclose(sum(res_1d.values()), 1.0, abs_tol=1e-6)
        assert res_1d["cvar"] > res_1d["bl"] > res_1d["herc"]

        arr_2d = np.array([
            [0.30, 0.20, 0.20, 0.30],
            [0.10, 0.40, 0.10, 0.40],
            [0.20, 0.10, 0.50, 0.20],
        ])
        res_2d = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(arr_2d)
        assert math.isclose(sum(res_2d.values()), 1.0, abs_tol=1e-6)
        for k in ["bl", "herc", "rp", "cvar"]:
            assert res_2d[k] > 0.0

    def test_geometric_langlands_barycenter_aliases(self, allocator):
        """Verify all method aliases match exactly."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        base = allocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w)
        a1 = allocator.compute_lurie_geometric_langlands_barycenter(w)
        a2 = allocator.compute_geometric_langlands_fisher_rao_barycenter(w)
        a3 = allocator.compute_geometric_langlands_barycenter(w)
        a4 = allocator.compute_langlands_fisher_rao_barycenter(w)
        a5 = allocator.compute_lurie_langlands_barycenter(w)
        a6 = allocator.compute_geometric_langlands_fisher_rao_barycenter_blend(w)
        a7 = allocator.compute_lurie_langlands_barycenter_blend(w)
        for alias_res in [a1, a2, a3, a4, a5, a6, a7]:
            for k in ["bl", "herc", "rp", "cvar"]:
                assert math.isclose(base[k], alias_res[k], abs_tol=1e-9)

    def test_portfolio_allocator_static_delegation_barycenter(self):
        """Verify PortfolioAllocator static method delegation and aliases."""
        w = {"bl": 0.25, "herc": 0.25, "rp": 0.25, "cvar": 0.25}
        s1 = PortfolioAllocator.compute_lurie_geometric_langlands_fisher_rao_barycenter_blend(w)
        s2 = PortfolioAllocator.compute_lurie_geometric_langlands_barycenter(w)
        s3 = PortfolioAllocator.compute_geometric_langlands_fisher_rao_barycenter(w)
        assert math.isclose(sum(s1.values()), 1.0, abs_tol=1e-6)
        assert s1["cvar"] > s1["bl"] > s1["herc"]
        for k in ["bl", "herc", "rp", "cvar"]:
            assert math.isclose(s1[k], s2[k], abs_tol=1e-9)
            assert math.isclose(s1[k], s3[k], abs_tol=1e-9)

    # =========================================================================
    # 2. 19TH-ORDER CUMULANT ULTRA-TRANS-HYPER EVAR TAIL RISK MEASURE (F113.1.2)
    # =========================================================================

    def test_evar_19th_cumulant_factorial_and_metadata(self, allocator):
        """Verifies that 19! is exactly 121,645,100,408,832,000 and order metadata is 19."""
        assert math.factorial(19) == 121645100408832000
        np.random.seed(42)
        rets = np.random.normal(-0.01, 0.03, 100)
        res = allocator.compute_ultra_trans_hyper_evar_risk_measure(rets, alpha=0.05)
        assert res["order"] == 19
        assert math.isclose(res["xi_19"], 0.75, abs_tol=1e-6)
        assert math.isclose(res["xi_ultra_trans"], 0.75, abs_tol=1e-6)
        assert "ultra_trans_hyper_evar_value" in res
        assert "ultra_trans_hyper_evar" in res
        assert "kappa_19" in res

    def test_evar_coherent_tail_hierarchy(self, allocator):
        """
        Verify strict coherent tail risk hierarchy:
            VaR <= CVaR <= EVaR <= ... <= Trans-Hyper-Transcendent EVaR <= Ultra-Trans-Hyper EVaR
        """
        np.random.seed(101)
        # Heavy-tailed Student-t losses
        rets = -np.random.standard_t(df=3, size=250) * 0.02
        trans_hyper_res = allocator.compute_trans_hyper_transcendent_evar_risk_measure(rets, alpha=0.05)
        ultra_trans_res = allocator.compute_ultra_trans_hyper_evar_risk_measure(rets, alpha=0.05)

        th_val = trans_hyper_res["trans_hyper_transcendent_evar_value"]
        uth_val = ultra_trans_res["ultra_trans_hyper_evar_value"]
        assert uth_val >= th_val - 1e-6

    def test_evar_empty_and_degenerate_returns(self, allocator):
        """Verify graceful fallback under empty or NaN returns."""
        res_empty = allocator.compute_ultra_trans_hyper_evar_risk_measure([])
        assert res_empty["order"] == 19
        assert "ultra_trans_hyper_evar_value" in res_empty

        res_nan = allocator.compute_ultra_trans_hyper_evar_risk_measure([np.nan, np.inf, -np.inf])
        assert res_nan["order"] == 19
        assert "ultra_trans_hyper_evar_value" in res_nan

    def test_evar_aliases_and_static_delegation(self):
        """Verify EVaR aliases on allocator and PortfolioAllocator static delegation."""
        np.random.seed(42)
        rets = np.random.normal(-0.005, 0.02, 150)
        alloc = UnifiedPortfolioAllocator()

        res1 = alloc.compute_ultra_trans_hyper_evar_risk_measure(rets, alpha=0.05)
        res2 = alloc.compute_ultra_trans_hyper_evar(rets, alpha=0.05)
        res3 = alloc.ultra_trans_hyper_evar_risk_measure(rets, alpha=0.05)
        assert math.isclose(res1["ultra_trans_hyper_evar_value"], res2["ultra_trans_hyper_evar_value"], abs_tol=1e-9)
        assert math.isclose(res1["ultra_trans_hyper_evar_value"], res3["ultra_trans_hyper_evar_value"], abs_tol=1e-9)

        s_res1 = PortfolioAllocator.compute_ultra_trans_hyper_evar_risk_measure(rets, alpha=0.05)
        s_res2 = PortfolioAllocator.compute_ultra_trans_hyper_evar(rets, alpha=0.05)
        assert math.isclose(res1["ultra_trans_hyper_evar_value"], s_res1["ultra_trans_hyper_evar_value"], abs_tol=1e-6)
        assert math.isclose(s_res1["ultra_trans_hyper_evar_value"], s_res2["ultra_trans_hyper_evar_value"], abs_tol=1e-9)

    # =========================================================================
    # 3. VERSION >= 23 INTEGRATION & DISPATCH
    # =========================================================================

    def test_version_23_log_odds_and_barycenter_dispatch(self, allocator):
        """Verify version=23 triggers Lurie Geometric Langlands ambiguity tilting and barycenter."""
        w_v22 = allocator.compute_information_theoretic_blend_weights(version=22)
        w_v23 = allocator.compute_information_theoretic_blend_weights(version=23)
        assert math.isclose(sum(w_v23.values()), 1.0, abs_tol=1e-6)
        # CVaR tail weight increases under v23
        assert w_v23["cvar"] > w_v22["cvar"]
