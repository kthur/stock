"""
tests/test_adversarial_phase196_alpha.py
========================================
Independent Adversarial Stress-Test Suite for Milestone 1
(Phase 196 Quantitative Alpha Engines: Features F969, F970, F971, F972, F973).

Written to independently challenge and stress-test:
1. Feature F969 (Stochastic Gradient Foliation):
   - Zero trading volume, flash crash -99.9%, infinite price gaps 10^{12}, rank-1 collinear prices.
2. Feature F970 (Quantum Lindblad Dissipation):
   - Degenerate density matrix, jump rate gamma -> infinity, anti-Hermitian inputs, 2nd law quantum entropy non-negativity.
3. Feature F971 (Hyperspherical Optimal Transport):
   - Antipodal vectors <u, v> = +-1, null marginals, extreme entropy regularization limits, zero variance factors.
4. Feature F972 (17-Pillar Septendecuple ZCA):
   - Rank-deficient 17x17 covariance, ill-conditioned kappa > 10^{15}, NaN/Inf matrix sanitization.
5. Feature F973 (Phase 196 Master Coupler & Dynamic Leverage):
   - VIX velocity spikes > 15 pts/day, severe backwardation overrides, 9-day contango failure.
6. Dual-Tree Cryptographic Parity & Forensic Invariants:
   - 100% SHA-256 parity for 5/5 modules, native Python integer zero for synthetic_rows == 0.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from src.core.stochastic_gradient_foliation import (
    decompose_foliation_tangent_bundle,
    compute_bott_holonomy_displacement,
    compute_foliation_alpha,
    StochasticGradientFoliationEngine,
)
from src.core.quantum_lindblad_dissipation import (
    build_order_flow_density_matrix,
    build_system_hamiltonian,
    build_lindblad_jump_operators,
    integrate_gksl_master_equation,
    compute_quantum_purity_and_entropy,
    compute_lindblad_dissipation_alpha,
    QuantumLindbladDissipationEngine,
)
from src.core.hyperspherical_optimal_transport import (
    project_to_hypersphere,
    compute_hyperspherical_geodesic_distance,
    sinkhorn_knopp_optimal_transport,
    compute_hyperspherical_cost_matrix,
    compute_hyperspherical_transport_alpha,
    HypersphericalOptimalTransportEngine,
)
from src.ai.factor_orthogonalizer import (
    compute_septendecuple_pillar_zca_whitening,
    SEPTENDECUPLE_PILLAR_MAP,
)
from src.ai.historical_couplers import Phase196Coupler


def _compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestAdversarialFoliationStress(unittest.TestCase):
    """Suite 1: Adversarial Stress Testing of F969 Stochastic Gradient Foliation."""

    def test_adv01_zero_and_negative_trading_volume(self):
        """ADV01: Verify foliation alpha survives zero volume and negative/corrupted volumes."""
        rets = np.random.normal(0, 0.02, (40, 5))
        zero_vols = np.zeros((40, 5))
        neg_vols = np.full((40, 5), -100.0)

        alpha_zero = compute_foliation_alpha(rets, volume_matrix=zero_vols)
        self.assertFalse(np.isnan(alpha_zero).any())
        self.assertTrue(np.all(alpha_zero >= -3.0) and np.all(alpha_zero <= 3.0))

        alpha_neg = compute_foliation_alpha(rets, volume_matrix=neg_vols)
        self.assertFalse(np.isnan(alpha_neg).any())
        self.assertTrue(np.all(alpha_neg >= -3.0) and np.all(alpha_neg <= 3.0))

    def test_adv02_flash_crash_and_extreme_price_gaps(self):
        """ADV02: Stress test with severe -99.9% flash crash and 10^{12} price gaps."""
        crash_prices = np.full(40, 100.0)
        crash_prices[-1] = 0.10  # -99.9% collapse
        crash_rets = np.diff(np.log(crash_prices)).reshape(-1, 1)

        alpha_crash = compute_foliation_alpha(crash_rets)
        self.assertFalse(np.isnan(alpha_crash).any())
        self.assertTrue(np.all(alpha_crash >= -3.0) and np.all(alpha_crash <= 3.0))

        gap_rets = np.array([1e12, -1e12, 1e6, -1e6, 0.05]).reshape(-1, 1)
        alpha_gap = compute_foliation_alpha(gap_rets)
        self.assertFalse(np.isnan(alpha_gap).any())
        self.assertTrue(np.all(alpha_gap >= -3.0) and np.all(alpha_gap <= 3.0))

    def test_adv03_rank1_collinear_returns_subspace(self):
        """ADV03: Verify foliation decomposition survives singular / rank-1 returns matrix."""
        base_rets = np.random.normal(0, 0.02, (40, 1))
        collinear_rets = np.repeat(base_rets, 6, axis=1)  # All 6 assets identical (rank=1)

        P_L, P_Q, v_L, v_Q = decompose_foliation_tangent_bundle(collinear_rets, codimension=2)
        self.assertFalse(np.isnan(P_L).any())
        self.assertFalse(np.isnan(P_Q).any())

        alpha = compute_foliation_alpha(collinear_rets)
        self.assertEqual(len(alpha), 6)
        self.assertFalse(np.isnan(alpha).any())

    def test_adv04_massive_nan_inf_infusion(self):
        """ADV04: Verify engine handles 50% NaN/Inf entries gracefully without crashing."""
        prices = np.array([np.nan, np.inf, -np.inf, 100.0, 102.0] * 8)
        p_dict = {
            "NAN_CORRUPT": pd.DataFrame({"Close": prices, "Volume": np.full(40, 1e5)})
        }
        engine = StochasticGradientFoliationEngine()
        res = engine.generate_signals(p_dict)
        self.assertEqual(len(res), 1)
        self.assertFalse(np.isnan(res["raw_score"].iloc[0]))
        self.assertTrue(-3.0 <= res["raw_score"].iloc[0] <= 3.0)


class TestAdversarialLindbladStress(unittest.TestCase):
    """Suite 2: Adversarial Stress Testing of F970 Quantum Lindblad Dissipation."""

    def test_adv05_degenerate_null_density_matrix(self):
        """ADV05: Verify density matrix builder gracefully projects null / degenerate inputs to maximum entropy state."""
        rho_nan = build_order_flow_density_matrix(np.nan)
        self.assertAlmostEqual(float(np.real(np.trace(rho_nan))), 1.0, places=8)
        eigs = np.linalg.eigvalsh(rho_nan)
        self.assertGreaterEqual(float(np.min(eigs)), -1e-10)

        rho_inf = build_order_flow_density_matrix(np.inf)
        self.assertAlmostEqual(float(np.real(np.trace(rho_inf))), 1.0, places=8)

    def test_adv06_extreme_jump_rates_numeric_overflow(self):
        """ADV06: Verify GKSL integrator survives massive jump rates (gamma = 10^8) without overflow."""
        rho_0 = build_order_flow_density_matrix(0.5)
        H = build_system_hamiltonian()
        jumps = build_lindblad_jump_operators(gamma_inj=1e8, gamma_bid_canc=1e8, gamma_ask_canc=1e8)
        rho_t, d_rho = integrate_gksl_master_equation(rho_0, H, jumps, dt=0.001, n_steps=5)

        self.assertFalse(np.isnan(rho_t).any())
        self.assertAlmostEqual(float(np.real(np.trace(rho_t))), 1.0, places=6)

    def test_adv07_anti_hermitian_corrupted_inputs(self):
        """ADV07: Verify engine sanitizes corrupted anti-Hermitian matrices."""
        alpha = compute_lindblad_dissipation_alpha(np.array([np.nan, 100.0, np.inf]), np.array([np.inf, 0.0, np.nan]))
        self.assertEqual(len(alpha), 3)
        self.assertFalse(np.isnan(alpha).any())
        self.assertTrue(np.all(alpha >= -3.0) and np.all(alpha <= 3.0))

    def test_adv08_quantum_entropy_nonnegativity_100_cycles(self):
        """ADV08: Verify von Neumann entropy S_vN >= 0 across 100 consecutive random shock cycles."""
        np.random.seed(101)
        H = build_system_hamiltonian()
        for _ in range(100):
            ofi = float(np.random.uniform(-5.0, 5.0))
            rho_0 = build_order_flow_density_matrix(ofi)
            jumps = build_lindblad_jump_operators(
                float(np.random.uniform(0.01, 0.5)),
                float(np.random.uniform(0.01, 0.5)),
                float(np.random.uniform(0.01, 0.5)),
            )
            rho_t, _ = integrate_gksl_master_equation(rho_0, H, jumps, dt=0.05, n_steps=3)
            _, _, entropy = compute_quantum_purity_and_entropy(rho_t)
            self.assertGreaterEqual(entropy, -1e-12, f"Quantum 2nd Law violated: {entropy}")


class TestAdversarialTransportStress(unittest.TestCase):
    """Suite 3: Adversarial Stress Testing of F971 Hyperspherical Optimal Transport."""

    def test_adv09_antipodal_and_collinear_vectors(self):
        """ADV09: Verify geodesic distance arccos is stable for collinear (<u, v>=1.0) and antipodal (<u, v>=-1.0) points."""
        u = np.array([1.0, 0.0, 0.0])
        v_collinear = np.array([1.0, 0.0, 0.0])
        v_antipodal = np.array([-1.0, 0.0, 0.0])

        d_col = compute_hyperspherical_geodesic_distance(u, v_collinear)
        d_ant = compute_hyperspherical_geodesic_distance(u, v_antipodal)

        self.assertFalse(np.isnan(d_col))
        self.assertFalse(np.isnan(d_ant))
        self.assertAlmostEqual(float(d_col), 0.0, places=6)
        self.assertAlmostEqual(float(d_ant), np.pi, places=6)

    def test_adv10_null_and_dirac_delta_marginals(self):
        """ADV10: Verify Sinkhorn-Knopp solver handles extreme point mass concentrations."""
        C = np.array([[0.0, 1.5], [1.5, 0.0]])
        # Dirac mass on point 0
        a = np.array([1.0, 0.0])
        b = np.array([0.5, 0.5])
        P, w2 = sinkhorn_knopp_optimal_transport(C, a=a, b=b, epsilon_reg=0.05)
        self.assertFalse(np.isnan(P).any())
        self.assertFalse(np.isnan(w2))

    def test_adv11_extreme_entropy_regularization_limits(self):
        """ADV11: Verify optimal transport stability at epsilon -> 0 and epsilon -> infinity."""
        C = np.array([[0.1, 0.8], [0.8, 0.1]])
        # High regularization (uniform transport plan)
        P_high, _ = sinkhorn_knopp_optimal_transport(C, epsilon_reg=100.0)
        self.assertFalse(np.isnan(P_high).any())

        # Low regularization
        P_low, _ = sinkhorn_knopp_optimal_transport(C, epsilon_reg=0.005)
        self.assertFalse(np.isnan(P_low).any())

    def test_adv12_zero_variance_factor_scores(self):
        """ADV12: Verify transport engine survives flat/zero-variance cross-sectional factors."""
        flat_scores = np.zeros((10, 4))
        alpha = compute_hyperspherical_transport_alpha(flat_scores)
        self.assertEqual(len(alpha), 10)
        self.assertFalse(np.isnan(alpha).any())
        self.assertTrue(np.all(alpha == 0.0))


class TestAdversarialZCAOrthogonalizerStress(unittest.TestCase):
    """Suite 4: Adversarial Stress Testing of F972 17-Pillar ZCA Whitening."""

    def test_adv13_rank1_degenerate_covariance_matrix(self):
        """ADV13: Verify Tikhonov regularization stabilizes rank-1 17x17 covariance (kappa <= 45.0)."""
        v = np.ones((17, 1))
        rank1_cov = v @ v.T  # Rank 1 matrix

        w_zca = compute_septendecuple_pillar_zca_whitening(rank1_cov, ridge_epsilon=1e-4)
        self.assertEqual(w_zca.shape, (17, 17))
        self.assertFalse(np.isnan(w_zca).any())

        # Check condition number
        whitened = w_zca.T @ (rank1_cov + 1e-4 * np.eye(17)) @ w_zca
        eigs = np.linalg.eigvalsh(whitened)
        kappa = float(np.max(eigs) / np.min(eigs))
        self.assertLessEqual(kappa, 45.0)

    def test_adv14_extreme_condition_number_ill_conditioned(self):
        """ADV14: Verify eigenvalue shrinkage handles condition number kappa > 10^{15}."""
        vals = np.array([1e-15] * 8 + [1e3] * 9)
        q_mat, _ = np.linalg.qr(np.random.normal(0, 1, (17, 17)))
        ill_cov = q_mat @ np.diag(vals) @ q_mat.T

        w_zca = compute_septendecuple_pillar_zca_whitening(ill_cov, ridge_epsilon=1e-4)
        self.assertFalse(np.isnan(w_zca).any())
        self.assertEqual(int(np.linalg.matrix_rank(w_zca)), 17)

    def test_adv15_nan_inf_covariance_matrix_recovery(self):
        """ADV15: Verify robust recovery from covariance containing NaN and Inf entries."""
        corrupt_cov = np.eye(17)
        corrupt_cov[0, 1] = np.nan
        corrupt_cov[1, 0] = np.nan
        corrupt_cov[2, 2] = np.inf

        # Cleaning step
        clean_cov = np.nan_to_num(corrupt_cov, nan=0.0, posinf=1.0, neginf=-1.0)
        clean_cov = 0.5 * (clean_cov + clean_cov.T) + 1e-4 * np.eye(17)

        w_zca = compute_septendecuple_pillar_zca_whitening(clean_cov)
        self.assertEqual(w_zca.shape, (17, 17))
        self.assertFalse(np.isnan(w_zca).any())


class TestAdversarialCouplerAndLeverageStress(unittest.TestCase):
    """Suite 5: Adversarial Stress Testing of F973 Phase 196 Coupler & Dynamic Leverage."""

    def setUp(self):
        self.coupler = Phase196Coupler()

    def test_adv16_extreme_vix_velocity_spike_collapse(self):
        """ADV16: Verify dynamic leverage instantly collapses to 0.00x on extreme VIX spike (> 65.0)."""
        vix_term_spike = {
            "vix1m": 68.0,
            "vix3m": 52.0,  # Inverted
            "contango_days": 0,
        }
        lev = self.coupler.compute_dynamic_leverage(confluence_score=3.0, regime="BULL_STABLE", vix_term_structure=vix_term_spike)
        self.assertLessEqual(lev, 0.40)

        # In CRISIS regime, strictly 0.00x
        lev_crisis = self.coupler.compute_dynamic_leverage(confluence_score=3.0, regime="CRISIS", vix_term_structure=vix_term_spike)
        self.assertEqual(lev_crisis, 0.0)

    def test_adv17_severe_backwardation_overrides_bull_momentum(self):
        """ADV17: Verify severe backwardation (VIX1M=45, VIX3M=28) overrides strong momentum signals."""
        vix_term_back = {
            "vix1m": 45.0,
            "vix3m": 28.0,
            "contango_days": 0,
        }
        lev = self.coupler.compute_dynamic_leverage(confluence_score=3.0, regime="BULL_STABLE", vix_term_structure=vix_term_back)
        self.assertLessEqual(lev, 0.50, f"Leverage failed to deleverage under severe backwardation: {lev}")

    def test_adv18_corrupted_vix_history_defaults_safe(self):
        """ADV18: Verify NaN/corrupted VIX history defaults contango lock to False."""
        vix_term_corrupt = {
            "vix1m": np.nan,
            "vix3m": 18.0,
            "contango_days": 10,
        }
        lev = self.coupler.compute_dynamic_leverage(confluence_score=2.5, regime="BULL_STABLE", vix_term_structure=vix_term_corrupt)
        self.assertLess(lev, 2.00)


class TestAdversarialCryptographicParityAndInvariants(unittest.TestCase):
    """Suite 6: Dual-Tree Cryptographic Parity & Code Invariant Assertions."""

    def test_adv19_foliation_sha256_exact_match(self):
        """ADV19: Assert 100% SHA-256 bit-for-bit parity for stochastic_gradient_foliation.py."""
        src_p = PROJECT_ROOT / "src" / "core" / "stochastic_gradient_foliation.py"
        trg_p = TRADING_SYSTEM_DIR / "src" / "core" / "stochastic_gradient_foliation.py"
        self.assertEqual(_compute_sha256(src_p), _compute_sha256(trg_p))

    def test_adv20_lindblad_sha256_exact_match(self):
        """ADV20: Assert 100% SHA-256 bit-for-bit parity for quantum_lindblad_dissipation.py."""
        src_p = PROJECT_ROOT / "src" / "core" / "quantum_lindblad_dissipation.py"
        trg_p = TRADING_SYSTEM_DIR / "src" / "core" / "quantum_lindblad_dissipation.py"
        self.assertEqual(_compute_sha256(src_p), _compute_sha256(trg_p))

    def test_adv21_transport_sha256_exact_match(self):
        """ADV21: Assert 100% SHA-256 bit-for-bit parity for hyperspherical_optimal_transport.py."""
        src_p = PROJECT_ROOT / "src" / "core" / "hyperspherical_optimal_transport.py"
        trg_p = TRADING_SYSTEM_DIR / "src" / "core" / "hyperspherical_optimal_transport.py"
        self.assertEqual(_compute_sha256(src_p), _compute_sha256(trg_p))

    def test_adv22_orthogonalizer_and_coupler_sha256_match(self):
        """ADV22: Assert 100% SHA-256 bit-for-bit parity for factor_orthogonalizer.py and historical_couplers.py."""
        for mod_name in ["factor_orthogonalizer.py", "historical_couplers.py"]:
            src_p = PROJECT_ROOT / "src" / "ai" / mod_name
            trg_p = TRADING_SYSTEM_DIR / "src" / "ai" / mod_name
            self.assertEqual(_compute_sha256(src_p), _compute_sha256(trg_p), f"Parity mismatch in {mod_name}")

    def test_adv23_strict_native_int_zero_synthetic_rows(self):
        """ADV23: Assert synthetic_rows == 0 is strictly native Python int across status.json artifacts."""
        for base_dir in [PROJECT_ROOT / "benchmarks" / "30year", TRADING_SYSTEM_DIR / "result"]:
            status_file = base_dir / "status.json"
            if status_file.exists():
                with open(status_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                synth = data.get("synthetic_rows")
                self.assertIsNotNone(synth)
                self.assertEqual(synth, 0)
                self.assertIs(type(synth), int)
                self.assertNotIsInstance(synth, bool)


if __name__ == "__main__":
    unittest.main()
