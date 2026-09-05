"""
test_challenger_phase12_f69.py
Adversarial empirical stress tests for Phase 12 Genesis Quantitative Enhancement (F69.1, F69.2).
Author: Challenger 2 (Empirical Challenger)
"""

import math
import numpy as np
import pytest

from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from trading_system.src.core.fast_lob_engine import DeepHawkesArrivalProcess
from trading_system.src.execution.smart_order_router import SmartOrderRouter
from trading_system.src.execution.oms_engine import ExecutionOMSEngine, AlmgrenChrissScheduler


class TestAdversarialF69FisherRaoManifold:
    """Stress tests for Fisher-Rao Manifold Barycenter Blending on S^3 (F69.1)."""

    def test_karcher_mean_corner_distributions(self):
        """Test Karcher mean convergence with extreme corner distributions."""
        allocator = UnifiedPortfolioAllocator()

        # 4 pure corner distributions
        corners = [
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 1.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 1.0},
        ]
        q_star = allocator.compute_fisher_rao_barycenter_blend(corners, max_iter=100, tol=1e-7)

        # By symmetry on S^3, the barycenter of 4 orthogonal corners MUST be uniform [0.25, 0.25, 0.25, 0.25]
        assert np.isclose(sum(q_star.values()), 1.0, atol=1e-5)
        for k, v in q_star.items():
            assert np.isclose(v, 0.25, atol=1e-2), f"Corner barycenter not symmetric for {k}: {v}"

        # 2-corner mixture
        corners_2 = [
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0},
        ]
        q_star_2 = allocator.compute_fisher_rao_barycenter_blend(corners_2, max_iter=100, tol=1e-7)
        assert np.isclose(q_star_2["bl"], 0.50, atol=1e-2)
        assert np.isclose(q_star_2["herc"], 0.50, atol=1e-2)
        assert q_star_2["rp"] < 0.01
        assert q_star_2["cvar"] < 0.01

        # 3-corner mixture
        corners_3 = [
            {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 1.0, "rp": 0.0, "cvar": 0.0},
            {"bl": 0.0, "herc": 0.0, "rp": 1.0, "cvar": 0.0},
        ]
        q_star_3 = allocator.compute_fisher_rao_barycenter_blend(corners_3, max_iter=100, tol=1e-7)
        assert np.isclose(q_star_3["bl"], 1.0 / 3.0, atol=1e-2)
        assert np.isclose(q_star_3["herc"], 1.0 / 3.0, atol=1e-2)
        assert np.isclose(q_star_3["rp"], 1.0 / 3.0, atol=1e-2)
        assert q_star_3["cvar"] < 0.01

    def test_karcher_mean_orthogonal_vectors(self):
        """Test Karcher mean convergence with orthogonal vectors in ndarray format."""
        allocator = UnifiedPortfolioAllocator()

        # Orthogonal basis in R^4
        orth_basis = np.eye(4)
        q_star = allocator.compute_fisher_rao_barycenter_blend(orth_basis, max_iter=100, tol=1e-7)

        assert np.isclose(sum(q_star.values()), 1.0, atol=1e-5)
        for k, v in q_star.items():
            assert np.isclose(v, 0.25, atol=1e-2), f"Orthogonal basis centroid failed for {k}: {v}"

    def test_karcher_mean_random_simplex_distributions(self):
        """Test Karcher mean convergence on 100 sets of random simplex distributions."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(12345)

        for trial in range(100):
            k_models = np.random.randint(2, 9)
            alpha_dir = np.random.uniform(0.2, 5.0, size=4)
            dists = np.random.dirichlet(alpha_dir, size=k_models)

            q_star = allocator.compute_fisher_rao_barycenter_blend(dists, max_iter=80, tol=1e-6)

            # Verification 1: Valid probability distribution on simplex
            total_mass = sum(q_star.values())
            assert np.isclose(total_mass, 1.0, atol=1e-4), f"Sum of weights = {total_mass}"
            for k, v in q_star.items():
                assert 0.0 <= v <= 1.0, f"Weight {k}={v} out of bounds"
                assert math.isfinite(v), f"Weight {k} is NaN/Inf"

            # Verification 2: Fréchet variance reduction property
            sum_sq_bary = sum(allocator.compute_fisher_rao_distance(q_star, p)**2 for p in dists)
            sum_sq_corners = [
                sum(allocator.compute_fisher_rao_distance(dists[j], dists[m])**2 for m in range(k_models))
                for j in range(k_models)
            ]
            min_corner_var = min(sum_sq_corners)
            assert sum_sq_bary <= min_corner_var + 1e-3, (
                f"Fréchet barycenter variance {sum_sq_bary} exceeds corner {min_corner_var}"
            )

    def test_karcher_mean_invariance_and_single_distribution(self):
        """Test barycenter invariance under permutation and identity under single/identical distributions."""
        allocator = UnifiedPortfolioAllocator()

        # Single distribution
        p_single = {"bl": 0.40, "herc": 0.30, "rp": 0.20, "cvar": 0.10}
        q_single = allocator.compute_fisher_rao_barycenter_blend(p_single)
        for k in p_single:
            assert np.isclose(q_single[k], p_single[k], atol=1e-4)

        # Identical distributions
        p_list = [p_single, p_single, p_single]
        q_identical = allocator.compute_fisher_rao_barycenter_blend(p_list)
        for k in p_single:
            assert np.isclose(q_identical[k], p_single[k], atol=1e-4)

        # Permutation invariance
        p_a = {"bl": 0.50, "herc": 0.25, "rp": 0.15, "cvar": 0.10}
        p_b = {"bl": 0.10, "herc": 0.20, "rp": 0.40, "cvar": 0.30}
        q_ab = allocator.compute_fisher_rao_barycenter_blend([p_a, p_b], tol=1e-7)
        q_ba = allocator.compute_fisher_rao_barycenter_blend([p_b, p_a], tol=1e-7)
        for k in p_a:
            assert np.isclose(q_ab[k], q_ba[k], atol=1e-4), f"Permutation asymmetry for {k}"

    def test_fisher_rao_distance_axioms_adversarial(self):
        """Stress-test metric axioms of Fisher-Rao geodesic distance under degenerate inputs."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(333)

        p_zero = {"bl": 0.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}
        p_unit = {"bl": 1.0, "herc": 0.0, "rp": 0.0, "cvar": 0.0}

        # 1. Identity
        d_zz = allocator.compute_fisher_rao_distance(p_zero, p_zero)
        assert np.isclose(d_zz, 0.0, atol=1e-5)

        # 2. Positivity
        d_zu = allocator.compute_fisher_rao_distance(p_zero, p_unit)
        assert math.isfinite(d_zu)
        assert d_zu >= 0.0

        # 3. Triangle inequality across 50 random triples
        for _ in range(50):
            p1 = np.random.dirichlet([1, 1, 1, 1])
            p2 = np.random.dirichlet([1, 1, 1, 1])
            p3 = np.random.dirichlet([1, 1, 1, 1])

            d12 = allocator.compute_fisher_rao_distance(p1, p2)
            d23 = allocator.compute_fisher_rao_distance(p2, p3)
            d13 = allocator.compute_fisher_rao_distance(p1, p3)

            assert d13 <= d12 + d23 + 1e-6, f"Triangle inequality failed: {d13} > {d12} + {d23}"


class TestAdversarialF69UltraEVaR:
    """Stress tests for Ultra-EVaR coherent risk measure (F69.1)."""

    def test_strict_hierarchy_pareto_losses(self):
        """Empirically verify strict hierarchy VaR <= CVaR <= EVaR <= Super-EVaR <= Ultra-EVaR on heavy-tailed Pareto."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(999)

        shape_params = [1.2, 1.5, 2.0, 3.0]
        sample_sizes = [500, 1500, 3000]

        for shape in shape_params:
            for n_samples in sample_sizes:
                losses = (np.random.pareto(a=shape, size=n_samples) + 1.0) * 0.02
                returns = -losses

                res = allocator.compute_ultra_evar_risk_measure(
                    returns, alpha=0.01, xi_jump=0.15, xi_frechet=0.20
                )

                var = res["var_value"]
                cvar = res["cvar_value"]
                evar = res["evar_value"]
                s_evar = res["super_evar_value"]
                u_evar = res["ultra_evar_value"]

                assert cvar >= var - 1e-6, f"CVaR ({cvar}) < VaR ({var}) for Pareto shape {shape}"
                assert evar >= cvar - 1e-6, f"EVaR ({evar}) < CVaR ({cvar}) for Pareto shape {shape}"
                assert s_evar >= evar - 1e-6, f"Super-EVaR ({s_evar}) < EVaR ({evar}) for Pareto shape {shape}"
                assert u_evar >= s_evar - 1e-6, f"Ultra-EVaR ({u_evar}) < Super-EVaR ({s_evar}) for Pareto shape {shape}"

    def test_strict_hierarchy_student_t_and_jumps(self):
        """Empirically verify strict hierarchy on Student-t with degrees of freedom 1.5 to 5.0 and jumps."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(777)

        df_list = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

        for df in df_list:
            t_rets = np.random.standard_t(df=df, size=2000) * 0.03
            jumps = np.random.binomial(1, 0.05, size=2000) * np.random.normal(-0.10, 0.05, size=2000)
            returns = t_rets + jumps

            res = allocator.compute_ultra_evar_risk_measure(
                returns, alpha=0.01, xi_jump=0.20, xi_frechet=0.25
            )

            var = res["var_value"]
            cvar = res["cvar_value"]
            evar = res["evar_value"]
            s_evar = res["super_evar_value"]
            u_evar = res["ultra_evar_value"]

            assert cvar >= var - 1e-6, f"CVaR ({cvar}) < VaR ({var}) for t-df {df}"
            assert evar >= cvar - 1e-6, f"EVaR ({evar}) < CVaR ({cvar}) for t-df {df}"
            assert s_evar >= evar - 1e-6, f"Super-EVaR ({s_evar}) < EVaR ({evar}) for t-df {df}"
            assert u_evar >= s_evar - 1e-6, f"Ultra-EVaR ({u_evar}) < Super-EVaR ({s_evar}) for t-df {df}"

    def test_ultra_evar_monotonicity_alpha_and_frechet(self):
        """Verify monotonicity of Ultra-EVaR with respect to tail risk confidence alpha and Fréchet scale."""
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)

        returns = np.random.normal(-0.005, 0.04, size=1000)

        # Monotonicity with respect to alpha
        r_01 = allocator.compute_ultra_evar_risk_measure(returns, alpha=0.01, xi_frechet=0.20)
        r_05 = allocator.compute_ultra_evar_risk_measure(returns, alpha=0.05, xi_frechet=0.20)
        r_10 = allocator.compute_ultra_evar_risk_measure(returns, alpha=0.10, xi_frechet=0.20)

        assert r_01["ultra_evar_value"] > r_05["ultra_evar_value"]
        assert r_05["ultra_evar_value"] > r_10["ultra_evar_value"]

        # Monotonicity with respect to xi_frechet
        r_f0 = allocator.compute_ultra_evar_risk_measure(returns, alpha=0.05, xi_frechet=0.0)
        r_f2 = allocator.compute_ultra_evar_risk_measure(returns, alpha=0.05, xi_frechet=0.25)
        r_f5 = allocator.compute_ultra_evar_risk_measure(returns, alpha=0.05, xi_frechet=0.50)

        assert r_f5["ultra_evar_value"] >= r_f2["ultra_evar_value"] - 1e-6
        assert r_f2["ultra_evar_value"] >= r_f0["ultra_evar_value"] - 1e-6

    def test_ultra_evar_extreme_edge_cases(self):
        """Stress-test Ultra-EVaR on edge cases: empty, all zeros, extreme outlier, all gains."""
        allocator = UnifiedPortfolioAllocator()

        # 1. Empty returns
        r_empty = allocator.compute_ultra_evar_risk_measure(np.array([]))
        assert "ultra_evar_value" in r_empty
        assert math.isfinite(r_empty["ultra_evar_value"])

        # 2. All zeros (zero volatility, zero risk)
        r_zeros = allocator.compute_ultra_evar_risk_measure(np.zeros(100))
        assert math.isfinite(r_zeros["ultra_evar_value"])
        assert r_zeros["ultra_evar_value"] >= -1e-6

        # 3. Extreme outlier (-1000% loss)
        rets_outlier = np.zeros(500)
        rets_outlier[0] = -10.0
        r_outlier = allocator.compute_ultra_evar_risk_measure(rets_outlier, alpha=0.01)
        assert r_outlier["ultra_evar_value"] >= r_outlier["super_evar_value"] - 1e-6
        assert r_outlier["ultra_evar_value"] > 0.0

        # 4. Pure gains (all positive returns)
        rets_gains = np.random.uniform(0.01, 0.05, size=200)
        r_gains = allocator.compute_ultra_evar_risk_measure(rets_gains, alpha=0.05)
        assert r_gains["ultra_evar_value"] >= r_gains["super_evar_value"] - 1e-6


class TestAdversarialF69ExecutionAndSOR:
    """Stress tests for F69.2: Deep Hawkes L3, SOR dark preemption cap, lit floor, and dual peg shading."""

    def test_dark_routing_preemption_cap_never_exceeds_96_percent(self):
        """Adversarial stress test: DeepHawkesArrivalProcess and SOR dark routing never exceed 0.96."""
        # 1. Test DeepHawkesArrivalProcess directly with extreme toxic parameters
        for g_dobi in [0.0, 0.45, 1.0, 5.0, 10.0]:
            proc = DeepHawkesArrivalProcess(gamma_dobi=g_dobi, version=12)
            for i in range(20):
                proc.update("LIT", timestamp_sec=100.0 + 0.01 * i)
            proc.update_dobi([1.0, -1.0, 1.0])

            routing = proc.compute_preemptive_dark_routing(version=12)
            dark_ratio = routing["preemptive_dark_routing_ratio"]
            assert dark_ratio <= 0.96, f"DeepHawkes dark ratio {dark_ratio} exceeded 0.96 cap!"

        # 2. Test SmartOrderRouter with 500 adversarial combinations
        sor = SmartOrderRouter()
        np.random.seed(888)

        for _ in range(500):
            plan = {
                "symbol": "TEST",
                "market": "NASDAQ",
                "action": np.random.choice(["BUY", "SELL"]),
                "quantity": int(np.random.randint(100, 100000)),
                "target_price": float(np.random.uniform(10.0, 1000.0)),
                "queue_imbalance": float(np.random.uniform(-5.0, 5.0)),
                "qi_acceleration": float(np.random.uniform(-5.0, 5.0)),
                "gamma_toxic_dir": float(np.random.uniform(0.0, 1.0)),
                "cross_asset_toxicity": float(np.random.uniform(0.0, 1.0)),
                "darkpool_score": float(np.random.uniform(0.0, 1.0)),
                "is_accumulation": bool(np.random.choice([True, False])),
                "version": 12,
            }
            routed = sor.route_order(plan, version=12)
            eff_dark = routed["effective_dark_ratio"]
            assert eff_dark <= 0.96, f"SOR effective dark ratio {eff_dark} exceeded 0.96!"

    def test_lit_maker_floor_never_drops_below_0005_under_extreme_toxicity(self):
        """Verify lit maker floor never drops below 0.005 under extreme toxic flow across all conditions."""
        sor = SmartOrderRouter()

        extreme_toxic_plans = [
            {"gamma_toxic_dir": 1.0, "cross_asset_toxicity": 1.0, "version": 12},
            {"gamma_toxic_dir": 0.99, "cross_asset_toxicity": 0.99, "version": 12},
            {"gamma_toxic_dir": 1.0, "version": 12},
            {"cross_asset_toxicity": 1.0, "version": 12},
            {"hawkes_buy": 0.0, "hawkes_sell": 100.0, "action": "BUY", "version": 12},
            {"hawkes_buy": 100.0, "hawkes_sell": 0.0, "action": "SELL", "version": 12},
        ]

        for p in extreme_toxic_plans:
            plan = {
                "symbol": "TOXIC",
                "market": "SP500",
                "action": p.get("action", "BUY"),
                "quantity": 10000,
                "target_price": 500.0,
                **p,
            }
            routed = sor.route_order(plan, version=12)
            maker_ratio = routed["maker_ratio"]
            assert maker_ratio >= 0.005, f"Maker floor dropped below 0.005: {maker_ratio} for plan {p}"

    def test_anti_gaming_min_qty_scales_up_to_095(self):
        """Verify anti-gaming MinQty scales up to 0.95 and does not exceed 0.95."""
        sor = SmartOrderRouter()

        plan = {
            "symbol": "BLOCK",
            "market": "NASDAQ",
            "action": "BUY",
            "quantity": 50000,
            "target_price": 200.0,
            "gamma_toxic_dir": 1.0,
            "darkpool_score": 1.0,
            "is_accumulation": True,
            "version": 12,
        }
        routed = sor.route_order(plan, version=12)

        min_ratio = routed["min_ratio"]
        assert np.isclose(min_ratio, 0.95, atol=1e-3), f"Expected min_ratio 0.95, got {min_ratio}"
        assert min_ratio <= 0.95, f"MinQty exceeded 0.95: {min_ratio}"

    def test_dual_calculate_peg_limit_price_tick_shading(self):
        """
        Verify dual calculate_peg_limit_price (ExecutionOMSEngine and AlmgrenChrissScheduler):
        - Applies -0.60 * spread * (h - 0.25) tick shading for h > 0.25
        - Applies 0 shift for h <= 0.25
        - Both implementations produce identical results.
        """
        tp = 100.0
        spreads = [0.02, 0.05, 0.10, 0.20, 0.50, 1.0]
        h_values_benign = [0.0, 0.10, 0.20, 0.25]
        h_values_elevated = [0.26, 0.30, 0.40, 0.50, 0.70, 0.90, 1.0, 2.0]

        for spr in spreads:
            bid = tp - spr / 2.0
            ask = tp + spr / 2.0
            mid = (bid + ask) / 2.0

            # 1. Benign regime: h <= 0.25 -> 0 shift
            for h in h_values_benign:
                px_oms_buy = ExecutionOMSEngine.calculate_peg_limit_price(
                    target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
                    action="BUY", hawkes_intensity=h, alpha_urgency=0.50, version=12,
                )
                px_ac_buy = AlmgrenChrissScheduler.calculate_peg_limit_price(
                    target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
                    action="BUY", hawkes_intensity=h, alpha_urgency=0.50, version=12,
                )

                assert np.isclose(px_oms_buy, px_ac_buy, atol=1e-6)
                assert np.isclose(px_oms_buy, mid, atol=1e-5), f"Expected mid {mid} at h={h}, got {px_oms_buy}"

            # 2. Elevated regime: h > 0.25 -> -0.60 * spread * (h - 0.25) shift
            for h in h_values_elevated:
                expected_shift_buy = -0.60 * spr * (h - 0.25)
                expected_px_buy = np.clip(mid + expected_shift_buy, bid, ask)

                px_oms_buy = ExecutionOMSEngine.calculate_peg_limit_price(
                    target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
                    action="BUY", hawkes_intensity=h, alpha_urgency=0.50, version=12,
                )
                px_ac_buy = AlmgrenChrissScheduler.calculate_peg_limit_price(
                    target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
                    action="BUY", hawkes_intensity=h, alpha_urgency=0.50, version=12,
                )

                assert np.isclose(px_oms_buy, px_ac_buy, atol=1e-6), "Dual implementations diverged!"
                assert np.isclose(px_oms_buy, expected_px_buy, atol=1e-5), (
                    f"Expected BUY peg {expected_px_buy} for h={h}, spr={spr}, got {px_oms_buy}"
                )

                # For SELL: expected shift is +0.60 * spread * (h - 0.25)
                expected_shift_sell = +0.60 * spr * (h - 0.25)
                expected_px_sell = np.clip(mid + expected_shift_sell, bid, ask)

                px_oms_sell = ExecutionOMSEngine.calculate_peg_limit_price(
                    target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
                    action="SELL", hawkes_intensity=h, alpha_urgency=0.50, version=12,
                )
                px_ac_sell = AlmgrenChrissScheduler.calculate_peg_limit_price(
                    target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
                    action="SELL", hawkes_intensity=h, alpha_urgency=0.50, version=12,
                )

                assert np.isclose(px_oms_sell, px_ac_sell, atol=1e-6), "Dual SELL implementations diverged!"
                assert np.isclose(px_oms_sell, expected_px_sell, atol=1e-5), (
                    f"Expected SELL peg {expected_px_sell} for h={h}, spr={spr}, got {px_oms_sell}"
                )

    def test_dual_calculate_peg_limit_price_dict_intensity(self):
        """Verify dual calculate_peg_limit_price supports dict-based hawkes_intensity input."""
        tp = 100.0
        spr = 0.10
        bid = 99.95
        ask = 100.05
        mid = 100.0

        h_dict = {"cross_excitation_toxicity": 0.75, "total_intensity": 1.20}
        expected_shift = -0.60 * spr * (0.75 - 0.25)
        expected_px = mid + expected_shift

        px_oms = ExecutionOMSEngine.calculate_peg_limit_price(
            target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", hawkes_intensity=h_dict, alpha_urgency=0.50, version=12,
        )
        px_ac = AlmgrenChrissScheduler.calculate_peg_limit_price(
            target_price=tp, bid_price=bid, ask_price=ask, spread=spr,
            action="BUY", hawkes_intensity=h_dict, alpha_urgency=0.50, version=12,
        )

        assert np.isclose(px_oms, px_ac, atol=1e-6)
        assert np.isclose(px_oms, expected_px, atol=1e-5)
