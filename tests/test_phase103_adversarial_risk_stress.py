"""
tests/test_phase103_adversarial_risk_stress.py

Adversarial Verification & Empirical Stress Testing Suite for Phase 103 (Release R119):
Milestone 2 Risk Layer (Features F487.1, F487.2)
Role: Empirical Challenger (critic, specialist)

Target Verification Axes:
1. Feature F487.2: 138th-Cumulant Expansion Trans-Singular EVaR Risk Measure
   - Parameter verification: order=138 (138! ~ 3.99e236), xi_monster with 39 nines (1.0 - 1e-39)
   - Numerical precision & stability across extreme return distributions:
     * Fat-tailed Student-t (df=2.5, df=1.5, df=0.8, df=0.5)
     * Cauchy-like jumps & heavy jump-diffusion
     * Zero volatility / degenerate constant / microscopic returns (1e-12)
     * 1000-sigma catastrophic market crashes (-50%, -90%, -99%, -99.9%, -10.0x losses)
   - Scale monotonicity: EVaR monotonically scales with loss amplitude
   - Alpha confidence sensitivity: EVaR(alpha=0.001) > EVaR(alpha=0.01) > EVaR(alpha=0.05)
   - High-order factorial 138! (~ 3.99e236) log-domain overflow safety
   - Consistency across all 33 aliases and delegation to PortfolioAllocator
2. Feature F487.1: Waterfall Capital Redistribution
   - Extreme ADV constraints: 99% of capital constrained on top asset, verifying
     complete cascade to secondary assets with ZERO CASH DRAG
   - Strict sum preservation: sum(w_final) == sum(w_target) == 1.000000 when capacity exists
   - Absolute position concentration limits: w_i <= max_single_weight for all i
   - Strict liquidity limits: |w_final - w_curr| <= max_delta_w for all i
   - Alpha conviction priority ordering: high alpha assets absorb capacity before lower alpha assets
   - Boundary condition: universe capacity fully exhausted -> cap respected, no violation
   - Input format invariance: dict, numpy ndarray, pandas Series, empty, N=1, N=500
"""

import math
import numpy as np
import pandas as pd
import pytest

from trading_system.src.risk.unified_portfolio_allocator import (
    UnifiedPortfolioAllocator,
    compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure,
    compute_phase103_evar,
    phase103_evar_risk_measure,
    trans_singular_evar_v103,
    redistribute_waterfall_capital,
    phase103_waterfall_capital_redistribution,
)
from trading_system.src.risk.portfolio_allocator import PortfolioAllocator


def _extract_evar_numeric(res):
    if isinstance(res, dict):
        for k in ["phase103_evar", "evar_risk_measure", "evar", "trans_singular_evar"]:
            if k in res:
                return float(res[k])
        for k, v in res.items():
            if "evar" in k.lower() and isinstance(v, (int, float)):
                return float(v)
        raise ValueError(f"No EVaR numeric key in dict: {res.keys()}")
    return float(res)


# =========================================================================
# AXIS 1: 138TH-CUMULANT EXPANSION EVAR PARAMETER & ALIAS INVARIANTS
# =========================================================================

class TestPhase103AdversarialEVaRParameterInvariants:
    """Empirical verification of order=138, xi_monster 39-nines, and alias invariants."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=103)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=103)

    def test_parameter_verification_order_138_and_xi_monster_39_nines(self, allocator, portfolio_allocator):
        """
        Verify exact parameters:
        - order = 138 (138! ~ 3.99e236)
        - xi_monster = 0.999999999999999999999999999999999999999 (39 nines, 1.0 - 1e-39)
        """
        dummy_ret = np.array([-0.03, -0.01, 0.02, 0.04, -0.02, 0.01])
        res_upa = allocator.compute_phase103_evar(dummy_ret)

        assert isinstance(res_upa, dict), "Result must be a dict"
        assert res_upa.get("order") == 138, f"Expected order=138, got {res_upa.get('order')}"
        # In float64, 39 nines rounds to 1.0 due to 53-bit mantissa precision
        assert math.isclose(float(res_upa.get("xi_monster", 0.0)), 1.0, abs_tol=1e-12)
        assert "phase103_evar" in res_upa, "phase103_evar key must be present in output"

        val_upa = _extract_evar_numeric(res_upa)
        assert np.isfinite(val_upa), "EVaR value must be finite"
        assert val_upa > 0.0, "EVaR value must be strictly positive"

        # Check PortfolioAllocator delegation
        res_pa = portfolio_allocator.compute_phase103_evar(dummy_ret)
        assert isinstance(res_pa, dict)
        assert res_pa.get("order") == 138
        assert math.isclose(float(res_pa.get("xi_monster", 0.0)), 1.0, abs_tol=1e-12)
        val_pa = _extract_evar_numeric(res_pa)
        assert math.isclose(val_upa, val_pa, rel_tol=1e-5)

    def test_all_33_aliases_exact_numerical_and_metadata_identity(self, allocator, portfolio_allocator):
        """Verify that all 33 EVaR aliases on UnifiedPortfolioAllocator and PortfolioAllocator return identical values."""
        returns = np.array([-0.04, -0.015, 0.005, 0.02, -0.035, 0.018, -0.01, 0.025])
        base_res = allocator.compute_phase103_evar(returns)
        base_val = _extract_evar_numeric(base_res)

        alias_list = [
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar",
            "trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_blend",
            "compute_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar",
            "singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_moonshine_monster_whittaker_evar_phase103",
            "compute_phase103_evar",
            "compute_phase103_evar_risk_measure",
            "phase103_evar_risk_measure",
            "compute_higher_homology_53_evar_risk_measure",
            "compute_higher_homology_53_evar",
            "compute_evar_order138",
            "compute_138th_cumulant_evar",
            "compute_monster_whittaker_138th_cumulant_evar",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_trans_singular_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar",
            "compute_borcherds_moonshine_monster_whittaker_drinfeld_higher_homology_53_evar",
            "compute_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_drinfeld_higher_homology_53_evar",
            "compute_lurie_drinfeld_higher_homology_53_evar_risk_measure",
            "compute_lurie_drinfeld_higher_homology_53_evar",
            "calculate_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_evar_138th_cumulant",
            "evar_138th_cumulant",
            "trans_singular_138th_cumulant_evar",
            "eternal_omni_cosmic_138th_cumulant_evar",
            "supreme_transcendent_evar_138",
            "higher_homology_53_evar",
            "phase103_tail_risk_evar",
            "phase103_evar_bound",
            "compute_lmbmwdh53_evar",
            "lmbmwdh53_evar",
            "trans_singular_evar_v103",
        ]
        assert len(alias_list) >= 33, f"Expected at least 33 aliases, got {len(alias_list)}"

        for alias in alias_list:
            fn_upa = getattr(allocator, alias, None)
            assert fn_upa is not None, f"Missing {alias} on UnifiedPortfolioAllocator"
            res = fn_upa(returns)
            val = _extract_evar_numeric(res)
            assert math.isclose(val, base_val, rel_tol=1e-5), f"Value mismatch for alias {alias}: {val} vs {base_val}"

            fn_pa = getattr(portfolio_allocator, alias, None)
            assert fn_pa is not None, f"Missing {alias} on PortfolioAllocator"
            pa_res = fn_pa(returns)
            pa_val = _extract_evar_numeric(pa_res)
            assert math.isclose(pa_val, base_val, rel_tol=1e-5), f"Value mismatch on PortfolioAllocator for {alias}"


# =========================================================================
# AXIS 2: EVAR NUMERICAL PRECISION & STABILITY UNDER EXTREME DISTRIBUTIONS
# =========================================================================

class TestPhase103AdversarialEVaRNumericalStability:
    """Stress testing EVaR calculation under extreme fat-tailed, jump, degenerate, and crash returns."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=103)

    def test_fat_tailed_student_t_distributions(self, allocator):
        """Stress EVaR across Student-t degrees of freedom from 2.5 down to 0.5 (infinite variance/mean)."""
        rng = np.random.RandomState(4872)

        dfs = [2.5, 1.5, 1.0, 0.8, 0.5]
        prev_evar = None

        for df in dfs:
            raw = rng.standard_t(df=df, size=1500) * 0.02
            res = allocator.compute_phase103_evar(raw)
            val = _extract_evar_numeric(res)

            assert np.isfinite(val), f"Non-finite EVaR for Student-t df={df}: got {val}"
            assert not np.isnan(val), f"NaN EVaR for Student-t df={df}"
            assert val > 0.0, f"EVaR must be positive for Student-t df={df}, got {val}"
            assert res.get("order") == 138
            assert "optimal_t" in res and res["optimal_t"] > 0

    def test_cauchy_like_jumps_and_jump_diffusion(self, allocator):
        """Stress EVaR under Cauchy jumps and compound Poisson jump processes."""
        rng = np.random.RandomState(138)

        # 1. Pure standard Cauchy
        cauchy_ret = rng.standard_cauchy(size=2000) * 0.015
        res_cauchy = allocator.compute_phase103_evar(cauchy_ret)
        val_cauchy = _extract_evar_numeric(res_cauchy)
        assert np.isfinite(val_cauchy), f"Non-finite Cauchy EVaR: {val_cauchy}"
        assert val_cauchy > 0.0

        # 2. Jump diffusion with massive discontinuous shocks
        diff_ret = rng.normal(0.0005, 0.01, size=1000)
        # Inject jump shocks up to +/- 50.0
        shock_idx = rng.choice(1000, size=20, replace=False)
        diff_ret[shock_idx] += rng.choice([-50.0, -25.0, -10.0, 10.0, 25.0], size=20)

        res_jump = allocator.compute_phase103_evar(diff_ret)
        val_jump = _extract_evar_numeric(res_jump)
        assert np.isfinite(val_jump), f"Non-finite jump EVaR: {val_jump}"
        assert val_jump > 0.0

    def test_zero_volatility_and_degenerate_returns(self, allocator):
        """Stress EVaR when volatility is zero, returns are constant, or returns are microscopic."""
        # 1. All zeros: no risk, EVaR should be finite and >= 0
        all_zeros = np.zeros(200)
        res_zero = allocator.compute_phase103_evar(all_zeros)
        val_zero = _extract_evar_numeric(res_zero)
        assert np.isfinite(val_zero)
        assert not np.isnan(val_zero)
        assert val_zero >= 0.0

        # 2. Constant returns: r_i = -0.04
        const_loss = np.full(100, -0.04)
        res_const = allocator.compute_phase103_evar(const_loss)
        val_const = _extract_evar_numeric(res_const)
        assert np.isfinite(val_const)
        # EVaR for constant return -mu is exactly mu - log(alpha)/t*
        opt_t = float(res_const["optimal_t"])
        expected = 0.04 - math.log(0.05) / opt_t
        assert math.isclose(val_const, expected, rel_tol=1e-4)

        # 3. Microscopic returns: 1e-12
        micro_ret = np.array([-1e-12, 1e-12, -2e-12, 2e-12, -0.5e-12])
        res_micro = allocator.compute_phase103_evar(micro_ret)
        val_micro = _extract_evar_numeric(res_micro)
        assert np.isfinite(val_micro)
        assert val_micro > 0.0

        # 4. Single-element and two-element degenerate returns
        single_ret = np.array([-0.05])
        res_single = allocator.compute_phase103_evar(single_ret)
        val_single = _extract_evar_numeric(res_single)
        assert np.isfinite(val_single)
        assert val_single >= 0.0

        two_ret = np.array([-0.05, -0.05])
        res_two = allocator.compute_phase103_evar(two_ret)
        val_two = _extract_evar_numeric(res_two)
        assert np.isfinite(val_two)
        assert val_two > 0.0

    def test_1000_sigma_catastrophic_crashes(self, allocator):
        """Stress EVaR under catastrophic tail events (100-sigma to 1000-sigma crashes)."""
        rng = np.random.RandomState(999)
        base = rng.normal(0.0005, 0.01, size=1000)

        # Extreme crashes: -50%, -90%, -99%, -500%, -1000%
        crashes = {
            "mild": np.concatenate([base, [-0.10, -0.15]]),
            "severe": np.concatenate([base, [-0.50, -0.70]]),
            "catastrophic": np.concatenate([base, [-0.90, -0.99]]),
            "1000_sigma": np.concatenate([base, [-5.0, -10.0]]),
        }

        evar_results = {}
        for name, ret in crashes.items():
            res = allocator.compute_phase103_evar(ret)
            val = _extract_evar_numeric(res)
            assert np.isfinite(val), f"Crash {name} returned non-finite EVaR: {val}"
            assert val > 0.0
            evar_results[name] = val

        # Crash risk hierarchy: catastrophic > severe > mild
        assert evar_results["1000_sigma"] >= evar_results["catastrophic"]
        assert evar_results["catastrophic"] > evar_results["severe"]
        assert evar_results["severe"] > evar_results["mild"]

    def test_evar_scale_monotonicity(self, allocator):
        """Verify that scaling negative returns up strictly increases or maintains EVaR."""
        base_losses = np.array([-0.01, -0.02, -0.03, -0.05, 0.01, 0.02])
        scales = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]

        vals = []
        for s in scales:
            scaled = base_losses * s
            res = allocator.compute_phase103_evar(scaled)
            vals.append(_extract_evar_numeric(res))

        for i in range(len(vals) - 1):
            assert vals[i + 1] >= vals[i] - 1e-6, f"Scale monotonicity violated: scale {scales[i]} ({vals[i]}) vs {scales[i+1]} ({vals[i+1]})"

    def test_confidence_level_alpha_sensitivity(self, allocator):
        """
        Verify that smaller alpha (stricter confidence) yields monotonically higher EVaR.
        EVaR(alpha=0.001) > EVaR(alpha=0.01) > EVaR(alpha=0.05) > EVaR(alpha=0.10).
        """
        returns = np.array([-0.08, -0.04, -0.02, 0.01, 0.03, -0.01, 0.02])
        alphas = [0.10, 0.05, 0.01, 0.001]
        vals = []

        for a in alphas:
            res = allocator.compute_phase103_evar(returns, alpha=a)
            vals.append(_extract_evar_numeric(res))

        for i in range(len(vals) - 1):
            assert vals[i + 1] > vals[i], f"Alpha monotonicity violated: alpha={alphas[i+1]} ({vals[i+1]}) <= alpha={alphas[i]} ({vals[i]})"

    def test_high_order_factorial_138_log_domain_overflow_safety(self, allocator):
        """Verify that 138! (~ 3.99e236) does not cause IEEE 754 overflow."""
        # Check fact_138 calculation
        log_fact_138 = math.lgamma(139.0)
        fact_138 = math.exp(log_fact_138)
        assert np.isfinite(fact_138)
        assert 6.0e236 < fact_138 < 7.5e236, f"138! expected ~6.92e236, got {fact_138}"

        # Large variance returns to test (t^138 / fact_138) term
        large_var = np.array([-1.0, 1.0, -2.0, 2.0, -1.5, 1.5])
        res = allocator.compute_phase103_evar(large_var)
        val = _extract_evar_numeric(res)
        assert np.isfinite(val)
        assert not math.isinf(val)


# =========================================================================
# AXIS 3: WATERFALL CAPITAL REDISTRIBUTION UNDER EXTREME CONSTRAINTS
# =========================================================================

class TestPhase103AdversarialWaterfallRedistribution:
    """Stress testing Waterfall Capital Redistribution under extreme ADV constraints, concentration, and cash drag."""

    @pytest.fixture
    def allocator(self):
        return UnifiedPortfolioAllocator(version=103)

    @pytest.fixture
    def portfolio_allocator(self):
        return PortfolioAllocator(version=103)

    def test_extreme_adv_constraint_99_percent_constrained_zero_cash_drag(self, allocator):
        """
        Adversarial Scenario: 99% of capital is constrained on the top asset.
        - Universe: 100 assets (Asset 0 to Asset 99)
        - Target weights: Asset 0 wants 0.99, Assets 1..99 want ~0.000101 (sum=1.000000)
        - ADV limit: Asset 0 max_delta_w = 0.01 (so Asset 0 can only take 0.01, 98% excess!)
        - Assets 1..99 have max_delta_w = 0.05, max_single_weight = 0.05
        - Total absorption headroom of Assets 1..99 = 99 * 0.05 = 4.95 >> 0.98
        - Verification:
          1. Asset 0 gets exactly 0.01
          2. Waterfall redistributes the remaining 0.98 capital across Assets 1..99
          3. Total allocated capital == 1.000000 (ZERO CASH DRAG!)
          4. Strict sum preservation: sum(w_final) == 1.000000 within 1e-5
          5. No asset exceeds max_single_weight or max_delta_w
        """
        n_assets = 100
        keys = [f"SYM_{i:03d}" for i in range(n_assets)]

        current_w = {k: 0.0 for k in keys}
        target_w = {keys[0]: 0.99}
        rem_each = (1.0 - 0.99) / (n_assets - 1)
        for k in keys[1:]:
            target_w[k] = rem_each

        assert math.isclose(sum(target_w.values()), 1.0, abs_tol=1e-7)

        # ADV constraints: top asset constrained to 0.01 delta; others have 0.05 delta
        max_delta = {keys[0]: 0.01}
        for k in keys[1:]:
            max_delta[k] = 0.05

        # Alpha scores: strictly descending conviction
        alphas = {k: float(100 - i) for i, k in enumerate(keys)}

        # Pre-waterfall: liquidity-clipped weights
        pre_waterfall = {}
        for k in keys:
            delta = target_w[k] - current_w[k]
            allowed = max(-max_delta[k], min(max_delta[k], delta))
            pre_waterfall[k] = current_w[k] + allowed

        # Pre-waterfall has massive idle cash: Asset 0 has 0.01, others have 0.01 / 99 each -> sum ~ 0.02
        pre_sum = sum(pre_waterfall.values())
        assert pre_sum < 0.03, f"Expected massive pre-waterfall cash drag, got sum={pre_sum}"

        # Apply Phase 103 Waterfall Redistribution
        redistributed = allocator.redistribute_waterfall_capital(
            current_weights=current_w,
            next_weights=pre_waterfall,
            target_weights=target_w,
            max_delta_w=max_delta,
            max_single_weight=0.05,
            alpha_scores=alphas,
        )

        assert isinstance(redistributed, dict)
        final_sum = sum(redistributed.values())

        # ZERO CASH DRAG ASSERTION:
        assert math.isclose(final_sum, 1.0, abs_tol=1e-4), (
            f"Zero cash drag violated: sum={final_sum}, expected 1.000000"
        )

        # Asset 0 ADV constraint strictly held
        assert math.isclose(redistributed[keys[0]], 0.01, abs_tol=1e-5), (
            f"Asset 0 breached ADV limit: {redistributed[keys[0]]} vs 0.01"
        )

        # Position limits strictly held for every single asset
        for k in keys:
            w_i = redistributed[k]
            assert w_i <= 0.05 + 1e-6, f"Asset {k} exceeded max_single_weight: {w_i} > 0.05"
            assert w_i >= 0.0, f"Asset {k} negative weight: {w_i}"
            delta_i = abs(w_i - current_w[k])
            assert delta_i <= max_delta[k] + 1e-6, f"Asset {k} breached max_delta_w: {delta_i} > {max_delta[k]}"

        # Alpha conviction ordering check: higher alpha assets hit their cap before lower ones
        # For Assets 1..20, alpha is high (99..80), they should absorb up to 0.05
        assert math.isclose(redistributed[keys[1]], 0.05, abs_tol=1e-4)
        assert math.isclose(redistributed[keys[2]], 0.05, abs_tol=1e-4)
        # Lowest alpha asset should have less or equal weight
        assert redistributed[keys[-1]] <= redistributed[keys[1]]

    def test_waterfall_strict_sum_preservation_and_capital_conservation(self, allocator):
        """
        Verify strict conservation of total target capital:
        sum(w_final) == sum(w_target) across various unconstrained / partially constrained configurations.
        """
        targets = [
            {"A": 0.50, "B": 0.30, "C": 0.20},
            {"A": 0.70, "B": 0.20, "C": 0.10},
            {"A": 0.333, "B": 0.333, "C": 0.334},
            {"A": 0.25, "B": 0.25, "C": 0.25, "D": 0.25},
        ]

        for tgt in targets:
            n = len(tgt)
            cur = {k: 0.05 for k in tgt}
            # Severe limit on A
            max_d = {k: (0.05 if k == "A" else 0.40) for k in tgt}
            alphas = {k: float(ord(k)) for k in tgt}

            pre = {}
            for k in tgt:
                d = tgt[k] - cur[k]
                pre[k] = cur[k] + max(-max_d[k], min(max_d[k], d))

            res = allocator.redistribute_waterfall_capital(
                current_weights=cur,
                next_weights=pre,
                target_weights=tgt,
                max_delta_w=max_d,
                max_single_weight=0.60,
                alpha_scores=alphas,
            )

            expected_sum = sum(tgt.values())
            actual_sum = sum(res.values())
            assert math.isclose(actual_sum, expected_sum, abs_tol=1e-4), (
                f"Sum conservation violated for target {tgt}: actual={actual_sum}, expected={expected_sum}"
            )

    def test_waterfall_all_capacity_exhausted_boundary(self, allocator):
        """
        When ALL assets in the portfolio hit their max capacity, the allocator
        must safely cap total allocation without breaching any limit or throwing errors.
        """
        cur = {"A": 0.0, "B": 0.0}
        tgt = {"A": 0.50, "B": 0.50}  # sum = 1.00
        # Total universe capacity is only 0.20 + 0.20 = 0.40
        max_d = {"A": 0.20, "B": 0.20}
        pre = {"A": 0.20, "B": 0.20}

        res = allocator.redistribute_waterfall_capital(
            current_weights=cur,
            next_weights=pre,
            target_weights=tgt,
            max_delta_w=max_d,
            max_single_weight=0.20,
        )

        assert math.isclose(res["A"], 0.20, abs_tol=1e-5)
        assert math.isclose(res["B"], 0.20, abs_tol=1e-5)
        assert math.isclose(sum(res.values()), 0.40, abs_tol=1e-5)

    def test_waterfall_numpy_array_and_pandas_series_inputs(self, allocator):
        """Verify waterfall redistribution works seamlessly with numpy arrays and pandas Series."""
        # 1. Numpy array input
        w_next_np = np.array([0.10, 0.10, 0.10])
        w_curr_np = np.array([0.05, 0.05, 0.05])
        w_tgt_np = np.array([0.60, 0.20, 0.20])
        max_d_np = np.array([0.05, 0.40, 0.40])
        alpha_np = np.array([0.9, 0.8, 0.7])

        res_np = allocator.redistribute_waterfall_capital(
            w_next=w_next_np,
            w_curr=w_curr_np,
            w_target=w_tgt_np,
            max_delta_w=max_d_np,
            max_single_weight=0.50,
            alpha_scores=alpha_np,
        )

        assert isinstance(res_np, np.ndarray)
        assert math.isclose(float(np.sum(res_np)), float(np.sum(w_tgt_np)), abs_tol=1e-4)
        assert res_np[0] <= 0.10 + 1e-6  # A could only take 0.05 delta from 0.05 curr -> 0.10 max

        # 2. Pandas Series input
        idx = ["AAPL", "MSFT", "GOOGL"]
        s_next = pd.Series(w_next_np, index=idx)
        s_curr = pd.Series(w_curr_np, index=idx)
        s_tgt = pd.Series(w_tgt_np, index=idx)

        res_s = allocator.redistribute_waterfall_capital(
            w_next=s_next,
            w_curr=s_curr,
            w_target=s_tgt,
            max_delta_w=max_d_np,
            max_single_weight=0.50,
            alpha_scores=alpha_np,
        )
        assert isinstance(res_s, (np.ndarray, pd.Series, dict))
        if isinstance(res_s, np.ndarray):
            assert math.isclose(float(np.sum(res_s)), 1.0, abs_tol=1e-4)
        else:
            assert math.isclose(sum(res_s.values()), 1.0, abs_tol=1e-4)

    def test_waterfall_empty_and_singleton_edge_cases(self, allocator):
        """Verify stability on empty and single-element portfolios."""
        # Empty dict
        res_empty = allocator.redistribute_waterfall_capital(w_next={})
        assert res_empty == {}

        # Empty numpy array
        res_empty_arr = allocator.redistribute_waterfall_capital(w_next=np.array([]))
        assert len(res_empty_arr) == 0

        # Singleton portfolio
        single_cur = {"AAPL": 0.20}
        single_tgt = {"AAPL": 0.80}
        single_pre = {"AAPL": 0.40}
        single_d = {"AAPL": 0.20}
        res_single = allocator.redistribute_waterfall_capital(
            current_weights=single_cur,
            next_weights=single_pre,
            target_weights=single_tgt,
            max_delta_w=single_d,
            max_single_weight=0.40,
        )
        assert math.isclose(res_single["AAPL"], 0.40, abs_tol=1e-5)

    def test_waterfall_portfolio_allocator_delegation(self, allocator, portfolio_allocator):
        """Verify that PortfolioAllocator delegates waterfall redistribution identically."""
        cur = {"A": 0.1, "B": 0.1, "C": 0.1}
        nxt = {"A": 0.1, "B": 0.1, "C": 0.1}
        tgt = {"A": 0.6, "B": 0.2, "C": 0.2}
        max_d = {"A": 0.05, "B": 0.4, "C": 0.4}
        alphas = {"A": 0.9, "B": 0.8, "C": 0.7}

        res_upa = allocator.phase103_waterfall_capital_redistribution(
            current_weights=cur,
            next_weights=nxt,
            target_weights=tgt,
            max_delta_w=max_d,
            max_single_weight=0.5,
            alpha_scores=alphas,
        )

        res_pa = portfolio_allocator.phase103_waterfall_capital_redistribution(
            current_weights=cur,
            next_weights=nxt,
            target_weights=tgt,
            max_delta_w=max_d,
            max_single_weight=0.5,
            alpha_scores=alphas,
        )

        assert isinstance(res_upa, dict)
        assert isinstance(res_pa, dict)
        for k in res_upa:
            assert math.isclose(res_upa[k], res_pa[k], abs_tol=1e-5)
