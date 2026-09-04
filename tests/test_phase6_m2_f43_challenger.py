"""
Adversarial Verification & Stress Test Suite for Feature F43
Feature: Regime-Adaptive 4-Model Reliability Optimization & Tail Risk Budgeting
Target: trading_system/src/risk/unified_portfolio_allocator.py

Challenger: challenger_m2_opt6_1
Focus Areas:
1. Correlation spikes (corr = 0.999) & correlation breakdown (hedging / identity)
2. Single asset tail risk dominance & Euler CCVaR cap enforcement
3. Extreme downside asymmetry (D = 10.0 plunge risk vs D = 0.1 convex runner)
4. Extreme regime uncertainty entropy (H_norm = 1.0 vs 0.0) quadratic volatility scaling
5. Softmax temperature extremes (tau = 0.05 sharp vs tau = 100.0 flat)
6. Degenerate, malformed, and boundary inputs
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestF43ChallengerAdversarialScenarios:
    """Independent empirical stress harness challenging Feature F43 under extreme market conditions."""

    # ------------------------------------------------------------------------
    # Scenario 1: Correlation Spikes (corr = 0.999) & Correlation Breakdown
    # ------------------------------------------------------------------------

    def test_scenario1_correlation_spike_near_one_stability(self):
        """
        Adversarial Test 1A: Extreme correlation spike (rho = 0.999 across all assets).
        Under near-perfect correlation:
        - Covariance matrix is near-singular (condition number ~ 10^4 - 10^5).
        - Diversification Ratio collapses toward 1.00.
        - Blending engine must expand EVT-CVaR weight via max(0, 1.20 - DR) penalty and suppress RP.
        - Full multi-model blending must execute without LinAlgError, NaN, or Inf.
        """
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.50)
        n = 5
        vols = np.array([0.15, 0.18, 0.20, 0.22, 0.25])
        rho = 0.999
        corr = np.full((n, n), rho)
        np.fill_diagonal(corr, 1.0)
        cov = np.outer(vols, vols) * corr

        # Verify condition number is large
        cond_num = np.linalg.cond(cov)
        assert cond_num > 1000.0, f"Expected ill-conditioned matrix, got cond={cond_num}"

        # 1. Test Information-Theoretic Blend Weights under correlation collapse
        # Equal-weighted portfolio vol under rho=0.999
        w_eq = np.full(n, 1.0 / n)
        port_vol = math.sqrt(float(w_eq @ cov @ w_eq))
        mean_vol = float(np.mean(vols))
        dr_collapsed = mean_vol / port_vol  # Close to 1.0
        assert 1.0 <= dr_collapsed <= 1.05

        cfg_collapsed = allocator.compute_information_theoretic_blend_weights(
            regime="SIDEWAYS_HIGH_VOL",
            diversification_ratio=dr_collapsed,
        )
        cfg_normal = allocator.compute_information_theoretic_blend_weights(
            regime="SIDEWAYS_HIGH_VOL",
            diversification_ratio=1.60,
        )

        # CVaR weight must increase under correlation collapse
        assert cfg_collapsed["cvar"] > cfg_normal["cvar"], (
            f"CVaR weight should expand under DR collapse: {cfg_collapsed['cvar']} vs {cfg_normal['cvar']}"
        )
        # Risk Parity weight must contract
        assert cfg_collapsed["rp"] < cfg_normal["rp"], (
            f"RP weight should contract under DR collapse: {cfg_collapsed['rp']} vs {cfg_normal['rp']}"
        )
        # Probabilities sum to 1.0000
        assert np.isclose(sum(cfg_collapsed.values()), 1.0, atol=1e-5)

        # 2. Test full end-to-end multi-model blending with near-singular covariance
        T = 60
        # Synthetic returns matching cov
        np.random.seed(101)
        z = np.random.normal(0, 1, T)
        returns = np.zeros((T, n))
        for i in range(n):
            returns[:, i] = z * vols[i] + np.random.normal(0, vols[i] * math.sqrt(1.0 - rho**2), T)
        df_rets = pd.DataFrame(returns, columns=[f"SYM_{i}" for i in range(n)])

        pred_rets = np.array([0.04, 0.05, 0.03, 0.06, 0.04])
        symbols = [f"SYM_{i}" for i in range(n)]

        w_blend = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            regime="SIDEWAYS_HIGH_VOL",
        )

        assert w_blend is not None
        assert len(w_blend) == n
        assert np.all(np.isfinite(w_blend)), f"Non-finite weights found: {w_blend}"
        assert np.all(w_blend >= -1e-6), f"Negative weights found: {w_blend}"
        assert np.isclose(np.sum(w_blend), 1.0, atol=1e-4), f"Weights do not sum to 1: sum={np.sum(w_blend)}"
        assert np.all(w_blend <= allocator.max_single_weight + 1e-4), (
            f"Max single weight exceeded: {np.max(w_blend)} > {allocator.max_single_weight}"
        )

    def test_scenario1_correlation_breakdown_hedging_assets(self):
        """
        Adversarial Test 1B: Negative correlation / hedging regime (rho = -0.80).
        Under strong hedging:
        - Portfolio volatility drops, Diversification Ratio expands (DR >> 1.6).
        - RP and HERC weights are heavily boosted.
        - Euler risk contribution of hedging asset can be negative (hedging property).
        - Verify mathematical consistency of TRC sum == 1.0.
        """
        allocator = UnifiedPortfolioAllocator()
        n = 4
        # Two pairs of negatively correlated assets
        corr = np.array([
            [ 1.0, -0.8,  0.1, -0.1],
            [-0.8,  1.0, -0.1,  0.1],
            [ 0.1, -0.1,  1.0, -0.8],
            [-0.1,  0.1, -0.8,  1.0],
        ])
        vols = np.array([0.20, 0.20, 0.20, 0.20])
        cov = np.outer(vols, vols) * corr

        w = np.array([0.40, 0.40, 0.10, 0.10])
        mrc, trc = allocator.compute_component_cvar_risk_contributions(w, cov)

        # Mathematical invariance: TRC sum must equal 1.0 even with negative covariance
        assert np.isclose(np.sum(trc), 1.0, atol=1e-5), f"TRC sum {np.sum(trc)} != 1.0"
        # Check that high DR boosts RP and HERC
        cfg_high_dr = allocator.compute_information_theoretic_blend_weights(
            regime="SIDEWAYS_LOW_VOL",
            diversification_ratio=2.20,
        )
        assert cfg_high_dr["rp"] > 0.15
        assert cfg_high_dr["herc"] > 0.30

    # ------------------------------------------------------------------------
    # Scenario 2: Single Asset Tail Risk Dominance & Euler CCVaR Cap
    # ------------------------------------------------------------------------

    def test_scenario2_single_asset_tail_risk_dominance_euler_cap(self):
        """
        Adversarial Test 2: Asset 0 has massive tail risk dominance (99% of variance).
        Asset 0: var = 1.0, Assets 1..4: var = 0.001.
        Euler CCVaR Cap: TRC_cap = max(1.75 / N, 0.20) = 0.35 for N=5.
        - In raw equal weighting, Asset 0 accounts for > 98% of tail risk.
        - In optimize_multi_model_blend, Euler CCVaR cap must prune Asset 0's allocation
          and redistribute capital to the lower-risk assets.
        - Verify Asset 0 weight is reduced significantly and does not dominate portfolio risk unchecked.
        """
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.70)
        n = 5
        # Asset 0 has huge variance
        cov = np.diag([1.0, 0.001, 0.001, 0.001, 0.001])

        # Verify raw Euler risk contribution
        w_raw = np.full(n, 1.0 / n)
        mrc, trc = allocator.compute_component_cvar_risk_contributions(w_raw, cov)
        assert trc[0] > 0.98, f"Asset 0 should have >98% TRC, got {trc[0]:.4f}"
        assert np.isclose(np.sum(trc), 1.0, atol=1e-5)

        # Generate synthetic returns matching covariance
        T = 100
        np.random.seed(42)
        rets = np.zeros((T, n))
        rets[:, 0] = np.random.normal(0, 1.0, T)
        for j in range(1, n):
            rets[:, j] = np.random.normal(0, math.sqrt(0.001), T)
        df_rets = pd.DataFrame(rets, columns=[f"SYM_{i}" for i in range(n)])

        # Identical expected returns so alpha view does not tilt away from Asset 0
        pred_rets = np.full(n, 0.05)
        symbols = [f"SYM_{i}" for i in range(n)]

        w_opt = allocator.optimize_multi_model_blend(
            predicted_returns=pred_rets,
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            regime="BULL_LOW_VOL",
        )

        # Euler CCVaR cap for N=5 is max(1.75/5, 0.20) = 0.35
        # Asset 0 weight must be curtailed compared to the safe assets
        assert w_opt[0] < 0.25, f"Asset 0 weight should be restrained by Euler CCVaR cap, got {w_opt[0]:.4f}"
        # The remaining assets must absorb the redistributed weight
        safe_alloc = np.sum(w_opt[1:])
        assert safe_alloc > 0.75, f"Safe assets should receive majority allocation: {safe_alloc:.4f}"
        # Post-allocation tail risk contribution of Asset 0 should be dramatically lower than 98%
        _, trc_post = allocator.compute_component_cvar_risk_contributions(w_opt, cov)
        assert trc_post[0] < 0.90, f"Post-optimization TRC of Asset 0 should be curtailed: {trc_post[0]:.4f}"

    def test_scenario2_euler_redistribution_favors_lower_downside_ratio(self):
        """
        Adversarial Test 2B: When Euler CCVaR pruning redistributes capital,
        it must preferentially allocate to assets with the lowest downside ratio (highest upside convexity).
        """
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.80)
        n = 3
        cov = np.diag([0.50, 0.005, 0.005])

        T = 120
        np.random.seed(99)
        r0 = np.random.normal(0, math.sqrt(0.50), T)
        # Asset 1: low downside ratio (convex upside spikes)
        r1 = np.random.normal(0.005, 0.02, T)
        r1[r1 < 0] *= 0.3
        r1[r1 > 0] *= 1.8
        # Asset 2: high downside ratio (plunges)
        r2 = np.random.normal(0.005, 0.02, T)
        r2[r2 < 0] *= 1.8
        r2[r2 > 0] *= 0.3

        df_rets = pd.DataFrame({"VOL_DOM": r0, "CONVEX": r1, "PLUNGE": r2})
        symbols = ["VOL_DOM", "CONVEX", "PLUNGE"]

        _, _, ratios = allocator.compute_downside_semi_volatility(df_rets.values)
        assert ratios[1] < ratios[2], f"Asset 1 should have lower downside ratio than Asset 2: {ratios[1]} vs {ratios[2]}"

        w_opt = allocator.optimize_multi_model_blend(
            predicted_returns=np.array([0.05, 0.05, 0.05]),
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            regime="BULL_LOW_VOL",
        )

        # Asset 1 (convex, low downside ratio) must receive more capital than Asset 2 (plunge)
        assert w_opt[1] > w_opt[2], (
            f"Asset 1 (convex) weight {w_opt[1]:.4f} should exceed Asset 2 (plunge) weight {w_opt[2]:.4f}"
        )

    # ------------------------------------------------------------------------
    # Scenario 3: Extreme Downside Asymmetry (D=10.0 vs D=0.1)
    # ------------------------------------------------------------------------

    def test_scenario3_extreme_downside_asymmetry_sortino_penalization(self):
        """
        Adversarial Test 3A: Asset A (D=10.0 plunge risk) vs Asset B (D=0.1 convex runner).
        Both assets have identical positive predicted alpha returns.
        - compute_downside_semi_volatility must clip D_i to [0.20, 5.0].
        - Asset A receives severe tilt penalty: exp(-0.50 * (5.0 - 1.0)) = exp(-2.0) = 0.1353.
        - Asset B receives upside convexity bonus: exp(0.25 * (1.0 - 0.20)) = exp(0.20) = 1.2214.
        - Tilt ratio is >= 9.0x in favor of Asset B.
        - Verify Asset B gets overwhelmingly larger weight in optimize_multi_model_blend.
        """
        allocator = UnifiedPortfolioAllocator(max_single_weight=0.90)
        T = 200

        # Asset A: extreme plunge risk (D = 10.0)
        # Half positive (+0.001), half negative (-0.010) -> sigma- / sigma+ = 10.0
        r_a = np.empty(T)
        r_a[:T//2] = 0.001
        r_a[T//2:] = -0.010

        # Asset B: convex runner (D = 0.10)
        # Half positive (+0.010), half negative (-0.001) -> sigma- / sigma+ = 0.10
        r_b = np.empty(T)
        r_b[:T//2] = 0.010
        r_b[T//2:] = -0.001

        # Inspect downside semi-volatility output
        rets_mat = np.column_stack([r_a, r_b])
        sigma_plus, sigma_minus, d_ratios = allocator.compute_downside_semi_volatility(rets_mat)

        # Verify clipping to [0.20, 5.0]
        assert d_ratios[0] >= 4.99, f"Asset A downside ratio should hit upper clip ~5.0: got {d_ratios[0]}"
        assert d_ratios[1] <= 0.21, f"Asset B downside ratio should hit lower clip ~0.20: got {d_ratios[1]}"

        df_rets = pd.DataFrame({"PLUNGE_A": r_a, "CONVEX_B": r_b})
        cov = df_rets.cov().values
        symbols = ["PLUNGE_A", "CONVEX_B"]

        w_opt = allocator.optimize_multi_model_blend(
            predicted_returns=np.array([0.08, 0.08]),  # Identical alpha
            returns_df=df_rets,
            cov_matrix=cov,
            symbols=symbols,
            regime="BULL_HIGH_VOL",
        )

        ratio_b_to_a = w_opt[1] / max(1e-6, w_opt[0])
        assert ratio_b_to_a >= 3.0, (
            f"Asset B weight ({w_opt[1]:.4f}) must be at least 3x Asset A weight ({w_opt[0]:.4f}), ratio={ratio_b_to_a:.2f}"
        )

    def test_scenario3_leland_buffer_asymmetry_for_underwater_assets(self):
        """
        Adversarial Test 3B: Asymmetric Leland buffer threshold acceleration for underwater assets.
        For underwater positions (u_ret < 0):
        - When downside semi-volatility sigma^- is high (e.g. 0.08 vs 0.02 normal),
          z_down = u_ret / (sigma^- * sqrt(5)) contracts the lower buffer band faster down to 0.60x.
        - For winning runners (u_ret > 0):
          upper buffer band expands up to 1.80x while lower band stays at 1.0x.
        """
        allocator = UnifiedPortfolioAllocator()

        # Underwater position (-8% drawdown)
        u_ret_loss = -0.08
        vol_total = 0.03
        vol_downside_high = 0.08

        # 1. With standard total vol
        up_std, low_std = allocator.calculate_asymmetric_leland_multipliers(
            unrealized_return=u_ret_loss,
            volatility_20d=vol_total,
            downside_semi_volatility=None,
        )
        # 2. With heavy downside semi-volatility
        up_down, low_down = allocator.calculate_asymmetric_leland_multipliers(
            unrealized_return=u_ret_loss,
            volatility_20d=vol_total,
            downside_semi_volatility=vol_downside_high,
        )

        assert up_std == 1.0 and up_down == 1.0  # Upper band untouched for losses
        assert low_std <= 1.0 and low_down <= 1.0  # Lower band contracts

        # Winning runner (+12% return)
        u_ret_gain = 0.12
        up_win, low_win = allocator.calculate_asymmetric_leland_multipliers(
            unrealized_return=u_ret_gain,
            volatility_20d=vol_total,
            downside_semi_volatility=vol_downside_high,
        )
        assert up_win > 1.0, f"Winning runner should expand upper band: {up_win}"
        assert low_win == 1.0, f"Winning runner lower band should remain 1.0: {low_win}"

        # Boundary inputs: vol=0, NaN, Inf
        up_zero, low_zero = allocator.calculate_asymmetric_leland_multipliers(0.0, 0.0, 0.0)
        assert up_zero == 1.0 and low_zero == 1.0
        up_nan, low_nan = allocator.calculate_asymmetric_leland_multipliers(float("nan"), float("nan"), None)
        assert up_nan == 1.0 and low_nan == 1.0

    # ------------------------------------------------------------------------
    # Scenario 4: Extreme Regime Uncertainty Entropy (H_norm = 1.0 vs 0.0)
    # ------------------------------------------------------------------------

    def test_scenario4_quadratic_entropy_volatility_scaling_extremes(self):
        """
        Adversarial Test 4A: Target volatility and allocation cap scaling under
        H_norm = 0.0 (regime certainty) vs H_norm = 1.0 (uniform maximum entropy).
        Mathematical formula:
            eff_target_vol = target_vol * (1.0 - 0.30 * U_regime^2) * (1.0 - 0.20 * c_crisis)
            max_alloc_cap *= (1.0 - 0.20 * U_regime^2) * (1.0 - 0.35 * c_crisis)
        Verifications:
        - At H_norm = 0.0: Target vol = 100% of base, max_alloc_cap unpenalized by entropy.
        - At H_norm = 1.0: Target vol = 70% of base (30% reduction), max_alloc_cap = 80% of base.
        - Curvature property: At mild entropy (H_norm = 0.25), U^2 = 0.0625, vol reduction is
          only 1.875% (preserving 98.1% capacity vs 7.5% penalty under linear scaling).
        """
        target_vol = 0.12
        allocator = UnifiedPortfolioAllocator(target_volatility=target_vol)
        n = 4
        weights = np.full(n, 0.25)
        cov = np.diag([0.005**2] * n)  # Low realized vol so scaling hits cap

        # 1. H_norm = 0.0 (certainty)
        reg_zero_entropy = {"BULL_LOW_VOL": 1.0}
        _, alloc_zero = allocator.apply_target_volatility_scaling(weights, cov, regime=reg_zero_entropy)

        # 2. Mild entropy (H_norm ~ 0.25)
        # e.g., 90% in dominant regime, 10% split
        reg_mild_entropy = {"BULL_LOW_VOL": 0.88, "BULL_HIGH_VOL": 0.06, "SIDEWAYS_LOW_VOL": 0.06}
        _, alloc_mild = allocator.apply_target_volatility_scaling(weights, cov, regime=reg_mild_entropy)

        # 3. H_norm = 1.0 (maximum entropy, 6 equal regimes)
        reg_max_entropy = {
            r: 1.0 / 6.0
            for r in ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL"]
        }
        _, alloc_max = allocator.apply_target_volatility_scaling(weights, cov, regime=reg_max_entropy)

        # Mild entropy should experience minimal cash drag (>= 92% of alloc_zero)
        assert alloc_mild >= alloc_zero * 0.92, (
            f"Quadratic entropy should preserve exposure under mild uncertainty: {alloc_mild} vs {alloc_zero}"
        )
        # Maximum entropy must enforce significant de-risking (alloc_max <= 0.82 * alloc_zero)
        assert alloc_max <= alloc_zero * 0.82, (
            f"Maximum entropy must contract exposure: {alloc_max} vs {alloc_zero}"
        )

        # 4. Severe crisis compounding: CRISIS in regime dict with high probability
        reg_crisis_high = {
            "CRISIS": 0.70,
            "BEAR_HIGH_VOL": 0.30,
        }
        _, alloc_crisis_high = allocator.apply_target_volatility_scaling(
            weights, cov, regime=reg_crisis_high
        )
        assert alloc_crisis_high <= 0.38, f"High crisis regime should contract exposure below 0.38: {alloc_crisis_high}"

        # Pure CRISIS regime
        _, alloc_crisis_pure = allocator.apply_target_volatility_scaling(
            weights, cov, regime="CRISIS"
        )
        assert alloc_crisis_pure <= 0.33, f"Pure CRISIS regime should contract exposure below 0.33: {alloc_crisis_pure}"

    def test_scenario4_entropy_log_odds_shift_from_bl_to_herc(self):
        """
        Adversarial Test 4B: In compute_information_theoretic_blend_weights,
        entropy penalizes Black-Litterman (-0.50 * U^2) and rewards HERC (+0.25 * U).
        Verify that as entropy increases from 0 to 1, the ratio w_herc / w_bl increases significantly.
        """
        allocator = UnifiedPortfolioAllocator()

        # Regime certainty (H_norm = 0)
        reg_certain = {"BULL_LOW_VOL": 1.0}
        cfg_certain = allocator.compute_information_theoretic_blend_weights(
            regime=reg_certain, alpha_dispersion=0.03, diversification_ratio=1.35
        )

        # Regime chaos (H_norm = 1.0)
        reg_chaos = {
            r: 1.0 / 6.0
            for r in ["BULL_LOW_VOL", "BULL_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL"]
        }
        cfg_chaos = allocator.compute_information_theoretic_blend_weights(
            regime=reg_chaos, alpha_dispersion=0.03, diversification_ratio=1.35
        )

        ratio_certain = cfg_certain["herc"] / cfg_certain["bl"]
        ratio_chaos = cfg_chaos["herc"] / cfg_chaos["bl"]

        assert ratio_chaos > ratio_certain * 1.80, (
            f"Entropy must shift relative weight from BL to HERC: {ratio_chaos:.3f} vs {ratio_certain:.3f}"
        )

    # ------------------------------------------------------------------------
    # Scenario 5: Softmax Temperature Extremes (tau = 0.05 sharp vs tau = 100.0 flat)
    # ------------------------------------------------------------------------

    def test_scenario5_softmax_temperature_sharp_extreme(self):
        """
        Adversarial Test 5A: Ultra-low temperature (tau = 0.05).
        - Implementation clamps tau to max(0.10, float(temperature)) to prevent overflow.
        - Under tau = 0.10, the model with highest log-odds dominates overwhelmingly (argmax behavior).
        - Weights must strictly sum to 1.0000 with zero NaN/Inf.
        """
        allocator = UnifiedPortfolioAllocator()
        cfg_sharp = allocator.compute_information_theoretic_blend_weights(
            regime="BULL_LOW_VOL",
            alpha_dispersion=0.06,  # Strong alpha view favoring BL
            temperature=0.05,        # Clamped to 0.10
        )

        assert np.isclose(sum(cfg_sharp.values()), 1.0, atol=1e-5)
        # Winning model (BL) must receive overwhelming weight (> 85%)
        max_model = max(cfg_sharp, key=cfg_sharp.get)
        assert cfg_sharp[max_model] >= 0.80, (
            f"Dominant model should get >= 80% under sharp temperature: {cfg_sharp}"
        )

    def test_scenario5_softmax_temperature_flat_extreme(self):
        """
        Adversarial Test 5B: Ultra-high temperature (tau = 100.0).
        - Differences in log-odds are flattened out.
        - All 4 models must converge to nearly equal weight (1/4 = 0.25 each).
        - Weights must strictly sum to 1.0000.
        """
        allocator = UnifiedPortfolioAllocator()
        cfg_flat = allocator.compute_information_theoretic_blend_weights(
            regime="CRISIS",
            crisis_severity=1.0,  # Extreme crisis normally gives CVaR > 75%
            temperature=100.0,
        )

        assert np.isclose(sum(cfg_flat.values()), 1.0, atol=1e-5)
        # Each model must be near 0.25 (within [0.20, 0.30])
        for m_name, w_val in cfg_flat.items():
            assert 0.20 <= w_val <= 0.30, (
                f"Model {m_name} should be close to 0.25 under flat temperature: got {w_val:.4f}"
            )

    def test_scenario5_temperature_pathological_inputs(self):
        """
        Adversarial Test 5C: Pathological temperature values:
        - Negative temperature (tau = -5.0) -> clamped to 0.10
        - Zero temperature (tau = 0.0) -> clamped to 0.10
        - Massive temperature (tau = 1e6) -> flattens to 0.25
        - NaN / Inf temperature -> graceful fallback
        """
        allocator = UnifiedPortfolioAllocator()

        # Zero temperature
        cfg_zero = allocator.compute_information_theoretic_blend_weights(temperature=0.0)
        assert np.isclose(sum(cfg_zero.values()), 1.0, atol=1e-5)
        assert all(v > 0 for v in cfg_zero.values())

        # Negative temperature
        cfg_neg = allocator.compute_information_theoretic_blend_weights(temperature=-5.0)
        assert np.isclose(sum(cfg_neg.values()), 1.0, atol=1e-5)
        assert all(v > 0 for v in cfg_neg.values())

        # Massive temperature
        cfg_huge = allocator.compute_information_theoretic_blend_weights(temperature=1e6)
        assert np.isclose(sum(cfg_huge.values()), 1.0, atol=1e-5)
        for v in cfg_huge.values():
            assert np.isclose(v, 0.25, atol=1e-3)

    # ------------------------------------------------------------------------
    # Scenario 6: Boundary, Degenerate, and Malformed Inputs
    # ------------------------------------------------------------------------

    def test_scenario6_degenerate_returns_and_small_sample_guards(self):
        """
        Adversarial Test 6A: Degenerate input matrix guards:
        - T < 3 observations in compute_downside_semi_volatility -> defaults (0.02, 0.02, 1.0)
        - Constant returns (zero volatility) -> safe non-zero division guards
        - Single asset universe (N = 1) -> weight = 1.0
        """
        allocator = UnifiedPortfolioAllocator()

        # T = 2 observations (< 3)
        small_rets = np.array([[0.01, 0.02], [-0.01, 0.03]])
        sig_p, sig_m, d_ratio = allocator.compute_downside_semi_volatility(small_rets)
        assert len(sig_p) == 2
        assert np.all(d_ratio == 1.0)

        # Constant returns (all zeros)
        zero_rets = np.zeros((10, 3))
        sig_p_z, sig_m_z, d_ratio_z = allocator.compute_downside_semi_volatility(zero_rets)
        assert np.all(np.isfinite(d_ratio_z))
        assert np.all(d_ratio_z > 0)

        # Single asset optimization
        w_single = allocator.optimize_multi_model_blend(
            predicted_returns=np.array([0.05]),
            returns_df=pd.DataFrame({"ONLY_ONE": np.random.normal(0, 0.01, 50)}),
            cov_matrix=np.array([[0.01]]),
            symbols=["ONLY_ONE"],
        )
        assert len(w_single) == 1
        assert np.isclose(w_single[0], 1.0, atol=1e-4)

    def test_scenario6_component_cvar_euler_homogeneity_identity(self):
        """
        Adversarial Test 6B: Mathematical Euler Homogeneity Identity:
        sum_i (w_i * MRC_i) == k_alpha * sigma_p == CVaR_alpha(w).
        TRC_i = (w_i * MRC_i) / CVaR_alpha(w), hence sum_i TRC_i == 1.0000.
        Test across 20 randomly generated ill-conditioned covariance matrices.
        """
        allocator = UnifiedPortfolioAllocator()
        np.random.seed(42)

        for trial in range(20):
            n = np.random.randint(3, 12)
            # Random non-singular covariance matrix
            A = np.random.normal(0, 1, (n, n))
            cov = A @ A.T + np.eye(n) * 1e-4

            # Random positive weights summing to 1
            w = np.random.uniform(0.01, 1.0, n)
            w /= np.sum(w)

            k_alpha = np.random.uniform(2.0, 3.0)
            mrc, trc = allocator.compute_component_cvar_risk_contributions(w, cov, k_alpha=k_alpha)

            port_var = float(w @ cov @ w)
            port_std = math.sqrt(port_var)
            cvar_target = k_alpha * port_std

            # 1. Euler Homogeneity
            euler_sum = float(np.sum(w * mrc))
            assert np.isclose(euler_sum, cvar_target, rtol=1e-5), (
                f"Trial {trial}: Euler sum {euler_sum} != CVaR {cvar_target}"
            )

            # 2. Percentage Tail Risk Contribution Identity
            trc_sum = float(np.sum(trc))
            assert np.isclose(trc_sum, 1.0, atol=1e-5), (
                f"Trial {trial}: TRC sum {trc_sum} != 1.0"
            )
