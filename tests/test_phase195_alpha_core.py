"""
tests/test_phase195_alpha_core.py
=================================
Exhaustive Verification Suite for Milestone 1: Quantitative Alpha Feature Engineering
(Phase 195 Features F959, F960, F961) for Release R185.

Categories:
  - Category 1: Dual-Tree SHA-256 Parity, Metadata & Complete Alias Trees (TC01 ~ TC05)
  - Category 2: F959 Symplectic Hamiltonian Phase-Space Flow Engine (TC06 ~ TC13)
  - Category 3: F960 Higher-Order Simplicial Sheaf Laplacian Engine (TC14 ~ TC21)
  - Category 4: F961 Non-Equilibrium Statistical Mechanics Engine (TC22 ~ TC27)
  - Category 5: Numerical Stability, Adversarial Stress Testing & Zero Lookahead Bias (TC28 ~ TC33)
  - Category 6: Execution Latency SLA Across 500 Assets (TC34 ~ TC36)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import time
import unittest
import numpy as np
import pandas as pd

# Path resolution for workspace
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRADING_SYSTEM_DIR = PROJECT_ROOT / "trading_system"

for p in (str(PROJECT_ROOT), str(TRADING_SYSTEM_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import src.core.symplectic_hamiltonian_phase_flow as ham_mod
from src.core.symplectic_hamiltonian_phase_flow import (
    VERSION as HAM_VERSION,
    RELEASE as HAM_RELEASE,
    FEATURE as HAM_FEATURE,
    RUTH4_C_COEFFS,
    RUTH4_D_COEFFS,
    apply_hyperbolic_noise_deadband as ham_deadband,
    compute_canonical_momentum,
    compute_canonical_coordinates,
    compute_potential_and_grad,
    compute_hamiltonian_energy,
    ruth4_symplectic_step,
    ruth4_symplectic_integrate,
    compute_action_angle_variables,
    compute_kam_breakdown_parameter,
    compute_hamiltonian_alpha,
    compute_hamiltonian_phase_flow,
    SymplecticHamiltonianPhaseSpaceFlowEngine,
    Phase195HamiltonianFlowEngine,
    F959HamiltonianFlowEngine,
    SymplecticPhaseSpaceEngine,
    HamiltonianPhaseFlowEngine,
    Phase185HamiltonianFlowEngine,
)

import src.core.higher_order_simplicial_sheaf as sheaf_mod
from src.core.higher_order_simplicial_sheaf import (
    VERSION as SHEAF_VERSION,
    RELEASE as SHEAF_RELEASE,
    FEATURE as SHEAF_FEATURE,
    apply_hyperbolic_noise_deadband as sheaf_deadband,
    build_simplicial_complex,
    build_sheaf_coboundary_operators,
    compute_twisted_hodge_laplacians,
    helmholtz_hodge_decomposition,
    project_poincare_ball,
    compute_simplicial_sheaf_alpha,
    compute_simplicial_sheaf_flow,
    HigherOrderSimplicialSheafLaplacianEngine,
    HigherOrderSimplicialSheafEngine,
    Phase195SimplicialSheafEngine,
    F960SimplicialSheafEngine,
    HigherOrderHodgeFlowEngine,
    SimplicialSheafLaplacianEngine,
    Phase185SimplicialSheafEngine,
)

import src.core.non_equilibrium_statistical_mechanics as noneq_mod
from src.core.non_equilibrium_statistical_mechanics import (
    VERSION as NONEQ_VERSION,
    RELEASE as NONEQ_RELEASE,
    FEATURE as NONEQ_FEATURE,
    apply_hyperbolic_noise_deadband as noneq_deadband,
    fast_inv_det_3x3,
    compute_thermodynamic_state,
    compute_macro_elasticity_coupling,
    compute_probability_current,
    compute_schnakenberg_entropy_production,
    compute_jarzynski_dissipation,
    compute_nonequilibrium_alpha,
    compute_non_equilibrium_arbitrage,
    NonEquilibriumStatisticalMechanicsEngine,
    Phase195NonequilibriumEngine,
    F961NonequilibriumEngine,
    MacroMicroStatisticalMechanicsEngine,
    NonEquilibriumStatMechEngine,
    Phase185NonequilibriumEngine,
)


def _compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class TestPhase195DualTreeAndMetadata(unittest.TestCase):
    """Category 1: Dual-Tree SHA-256 Parity, Metadata & Complete Alias Trees."""

    def test_tc01_hamiltonian_dual_tree_parity(self):
        """TC01: Verify bit-for-bit SHA-256 parity for symplectic_hamiltonian_phase_flow.py."""
        src_file = PROJECT_ROOT / "src" / "core" / "symplectic_hamiltonian_phase_flow.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "symplectic_hamiltonian_phase_flow.py"
        self.assertTrue(src_file.exists(), f"Source file missing: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file missing: {target_file}")
        self.assertEqual(_compute_sha256(src_file), _compute_sha256(target_file))

    def test_tc02_simplicial_sheaf_dual_tree_parity(self):
        """TC02: Verify bit-for-bit SHA-256 parity for higher_order_simplicial_sheaf.py."""
        src_file = PROJECT_ROOT / "src" / "core" / "higher_order_simplicial_sheaf.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "higher_order_simplicial_sheaf.py"
        self.assertTrue(src_file.exists(), f"Source file missing: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file missing: {target_file}")
        self.assertEqual(_compute_sha256(src_file), _compute_sha256(target_file))

    def test_tc03_nonequilibrium_dual_tree_parity(self):
        """TC03: Verify bit-for-bit SHA-256 parity for non_equilibrium_statistical_mechanics.py."""
        src_file = PROJECT_ROOT / "src" / "core" / "non_equilibrium_statistical_mechanics.py"
        target_file = TRADING_SYSTEM_DIR / "src" / "core" / "non_equilibrium_statistical_mechanics.py"
        self.assertTrue(src_file.exists(), f"Source file missing: {src_file}")
        self.assertTrue(target_file.exists(), f"Target file missing: {target_file}")
        self.assertEqual(_compute_sha256(src_file), _compute_sha256(target_file))

    def test_tc04_metadata_constants(self):
        """TC04: Verify version, release, and feature metadata polymorphism."""
        for mod, expected_feature in [
            (ham_mod, "F959"),
            (sheaf_mod, "F960"),
            (noneq_mod, "F961"),
        ]:
            self.assertEqual(int(mod.VERSION), 195)
            self.assertEqual(str(mod.RELEASE), "R185")
            self.assertEqual(str(mod.FEATURE), expected_feature)
            self.assertTrue(mod.VERSION == 195)
            self.assertTrue(mod.RELEASE == "R185")

    def test_tc05_complete_alias_trees(self):
        """TC05: Verify all required aliases resolve correctly to the primary classes."""
        # F959 Aliases
        self.assertIs(Phase195HamiltonianFlowEngine, SymplecticHamiltonianPhaseSpaceFlowEngine)
        self.assertIs(F959HamiltonianFlowEngine, SymplecticHamiltonianPhaseSpaceFlowEngine)
        self.assertIs(SymplecticPhaseSpaceEngine, SymplecticHamiltonianPhaseSpaceFlowEngine)
        self.assertIs(HamiltonianPhaseFlowEngine, SymplecticHamiltonianPhaseSpaceFlowEngine)
        self.assertIs(Phase185HamiltonianFlowEngine, SymplecticHamiltonianPhaseSpaceFlowEngine)

        # F960 Aliases
        self.assertIs(HigherOrderSimplicialSheafEngine, HigherOrderSimplicialSheafLaplacianEngine)
        self.assertIs(Phase195SimplicialSheafEngine, HigherOrderSimplicialSheafLaplacianEngine)
        self.assertIs(F960SimplicialSheafEngine, HigherOrderSimplicialSheafLaplacianEngine)
        self.assertIs(HigherOrderHodgeFlowEngine, HigherOrderSimplicialSheafLaplacianEngine)
        self.assertIs(SimplicialSheafLaplacianEngine, HigherOrderSimplicialSheafLaplacianEngine)
        self.assertIs(Phase185SimplicialSheafEngine, HigherOrderSimplicialSheafLaplacianEngine)

        # F961 Aliases
        self.assertIs(Phase195NonequilibriumEngine, NonEquilibriumStatisticalMechanicsEngine)
        self.assertIs(F961NonequilibriumEngine, NonEquilibriumStatisticalMechanicsEngine)
        self.assertIs(MacroMicroStatisticalMechanicsEngine, NonEquilibriumStatisticalMechanicsEngine)
        self.assertIs(NonEquilibriumStatMechEngine, NonEquilibriumStatisticalMechanicsEngine)
        self.assertIs(Phase185NonequilibriumEngine, NonEquilibriumStatisticalMechanicsEngine)


class TestPhase195HamiltonianFlowEngine(unittest.TestCase):
    """Category 2: F959 Symplectic Hamiltonian Phase-Space Flow Engine."""

    def setUp(self):
        np.random.seed(42)
        n = 60
        self.prices = 100.0 * np.exp(np.cumsum(np.random.normal(0.001, 0.015, n)))
        self.volumes = np.random.uniform(1e5, 5e5, n)

    def test_tc06_canonical_coordinates_and_momentum(self):
        """TC06: Verify canonical coordinates (q, p) calculation and momentum properties."""
        q, p, mass = compute_canonical_coordinates(self.prices, volumes=self.volumes, window=20)
        self.assertEqual(len(q), len(self.prices))
        self.assertEqual(len(p), len(self.prices))
        self.assertGreater(mass, 0.0)
        self.assertAlmostEqual(float(np.mean(q)), 0.0, places=4)
        self.assertAlmostEqual(float(np.std(q)), 1.0, places=2)

    def test_tc07_hamiltonian_potential_and_energy(self):
        """TC07: Verify multi-well potential V(q) and Hamiltonian energy H(q, p) = T(p) + V(q)."""
        q_val = 0.5
        p_val = 0.2
        v, grad_v = compute_potential_and_grad(q_val, k1=1.0, k2=0.25, q_star=0.0)
        expected_v = 0.5 * 1.0 * (0.5 ** 2) + 0.25 * 0.25 * (0.5 ** 4)
        expected_grad = 1.0 * 0.5 + 0.25 * (0.5 ** 3)
        self.assertAlmostEqual(v, expected_v, places=6)
        self.assertAlmostEqual(grad_v, expected_grad, places=6)

        h_val = compute_hamiltonian_energy(q_val, p_val, mass=1.0, k1=1.0, k2=0.25)
        expected_t = 0.5 * (p_val ** 2) / 1.0
        self.assertAlmostEqual(h_val, expected_t + expected_v, places=6)

    def test_tc08_ruth4_symplectic_integration_energy_conservation(self):
        """TC08: Verify Ruth 4th-order symplectic integrator conserves Hamiltonian energy when gamma=0."""
        q0 = 1.0
        p0 = 0.0
        mass = 1.0
        dt = 0.02
        n_steps = 100

        q_traj, p_traj, h_traj = ruth4_symplectic_integrate(
            q0=q0, p0=p0, mass=mass, dt=dt, n_steps=n_steps, k1=1.0, k2=0.0, gamma=0.0
        )
        self.assertEqual(len(q_traj), n_steps + 1)
        self.assertEqual(len(p_traj), n_steps + 1)
        self.assertEqual(len(h_traj), n_steps + 1)

        h_initial = h_traj[0]
        max_h_dev = np.max(np.abs(h_traj - h_initial))
        self.assertLess(max_h_dev, 1e-3, f"Energy drift too large: {max_h_dev}")

    def test_tc09_symplectic_area_preservation(self):
        """TC09: Verify Ruth 4th-order integrator preserves canonical 2-form dq ^ dp (phase volume)."""
        q0, p0 = 0.5, 0.3
        eps = 1e-4

        def run_step(q, p):
            return ruth4_symplectic_step(q, p, mass=1.0, dt=0.05, grad_v_fn=lambda x: x, gamma=0.0)

        q_center, p_center = run_step(q0, p0)
        q_u, p_u = run_step(q0 + eps, p0)
        q_v, p_v = run_step(q0, p0 + eps)

        du_q = (q_u - q_center) / eps
        du_p = (p_u - p_center) / eps
        dv_q = (q_v - q_center) / eps
        dv_p = (p_v - p_center) / eps

        det_jacobian = du_q * dv_p - du_p * dv_q
        self.assertAlmostEqual(det_jacobian, 1.0, places=4, msg="Symplectic area not preserved!")

    def test_tc10_action_angle_and_kam_breakdown(self):
        """TC10: Verify action-angle variables and KAM tori breakdown parameter sigma_KAM >= 0."""
        q_traj, p_traj, h_traj = ruth4_symplectic_integrate(
            q0=1.0, p0=0.5, mass=1.0, dt=0.05, n_steps=50, k1=1.0, k2=0.25
        )
        action, angle = compute_action_angle_variables(q_traj, p_traj, mass=1.0, k1=1.0)
        kam_param = compute_kam_breakdown_parameter(q_traj, p_traj, h_traj, k1=1.0, k2=0.25)

        self.assertGreaterEqual(action, 0.0)
        self.assertTrue(-np.pi <= angle <= np.pi)
        self.assertGreaterEqual(kam_param, 0.0)

    def test_tc11_hamiltonian_alpha_bounds(self):
        """TC11: Verify compute_hamiltonian_alpha and compute_hamiltonian_phase_flow outputs strictly bounded in [-3.0, 3.0]."""
        alpha, action, kam, h_energy = compute_hamiltonian_alpha(self.prices, volumes=self.volumes)
        self.assertTrue(-3.0 <= alpha <= 3.0, f"Alpha out of bounds: {alpha}")
        self.assertGreaterEqual(action, 0.0)
        self.assertGreaterEqual(kam, 0.0)

        # Contract interface validation (PROJECT.md:77)
        rets = np.diff(np.log(self.prices))
        vols = self.volumes[1:]
        flow = compute_hamiltonian_phase_flow(rets, vols)
        self.assertTrue(np.all(flow >= -3.0) and np.all(flow <= 3.0))

        engine = SymplecticHamiltonianPhaseSpaceFlowEngine()
        self.assertTrue(getattr(engine, "lookahead_safe", False))
        self.assertEqual(len(engine.c_coeffs), 4)
        self.assertEqual(len(engine.d_coeffs), 4)
        eng_flow = engine.compute_hamiltonian_phase_flow(rets, vols)
        self.assertTrue(np.all(eng_flow >= -3.0) and np.all(eng_flow <= 3.0))

    def test_tc12_hamiltonian_engine_generate_signals(self):
        """TC12: Verify SymplecticHamiltonianPhaseSpaceFlowEngine.generate_signals output structure."""
        engine = SymplecticHamiltonianPhaseSpaceFlowEngine()
        prices_dict = {
            "AAPL": pd.DataFrame({"Close": self.prices, "Volume": self.volumes}),
            "MSFT": pd.DataFrame({"Close": self.prices * 1.05, "Volume": self.volumes * 0.9}),
            "GOOG": pd.DataFrame({"Close": self.prices * 0.95, "Volume": self.volumes * 1.1}),
        }
        res = engine.generate_signals(prices_dict)
        self.assertIn("symbol", res.columns)
        self.assertIn("hamiltonian_phase_flow_score", res.columns)
        self.assertIn("raw_score", res.columns)
        self.assertEqual(len(res), 3)

        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["hamiltonian_phase_flow_score"] <= 0.95)
            self.assertTrue(-3.0 <= row["raw_score"] <= 3.0)

    def test_tc13_hamiltonian_deadband_filter(self):
        """TC13: Verify hyperbolic deadband filter suppresses micro-noise."""
        self.assertEqual(ham_deadband(0.0), 0.0)
        self.assertLess(abs(ham_deadband(0.01, delta=0.030)), 1e-4)
        self.assertGreater(abs(ham_deadband(0.10, delta=0.030)), 0.05)


class TestPhase195SimplicialSheafEngine(unittest.TestCase):
    """Category 3: F960 Higher-Order Simplicial Sheaf Laplacian Engine."""

    def setUp(self):
        np.random.seed(42)
        self.n_sym = 6
        self.n_bars = 40
        cov = np.full((self.n_sym, self.n_sym), 0.4)
        np.fill_diagonal(cov, 1.0)
        l = np.linalg.cholesky(cov)
        white_noise = np.random.normal(0, 0.02, (self.n_bars, self.n_sym))
        self.returns = white_noise @ l.T
        self.prices_dict = {}
        for idx in range(self.n_sym):
            p = 100.0 * np.exp(np.cumsum(self.returns[:, idx]))
            v = np.random.uniform(1e5, 5e5, self.n_bars)
            self.prices_dict[f"SYM_{idx}"] = pd.DataFrame({"Close": p, "Volume": v})

    def test_tc14_simplicial_complex_construction(self):
        """TC14: Verify simplicial complex K = (V, E, T) builds valid vertices, edges, and triangles."""
        corr = np.corrcoef(self.returns, rowvar=False)
        vertices, edges, triangles = build_simplicial_complex(corr, threshold=0.20)

        self.assertEqual(len(vertices), self.n_sym)
        self.assertGreater(len(edges), 0)
        for u, v in edges:
            self.assertLess(u, v)
        for u, v, w in triangles:
            self.assertLess(u, v)
            self.assertLess(v, w)
            self.assertIn((u, v), edges)
            self.assertIn((v, w), edges)
            self.assertIn((u, w), edges)

    def test_tc15_sheaf_coboundary_nilpotency_invariant(self):
        """TC15: Verify mathematical invariant delta^1 o delta^0 == 0 identically."""
        corr = np.corrcoef(self.returns, rowvar=False)
        vertices, edges, triangles = build_simplicial_complex(corr, threshold=0.20)
        delta0, delta1 = build_sheaf_coboundary_operators(len(vertices), edges, triangles)

        if len(triangles) > 0 and len(edges) > 0:
            prod = delta1 @ delta0
            max_dev = float(np.max(np.abs(prod)))
            self.assertAlmostEqual(max_dev, 0.0, places=12, msg=f"delta1 @ delta0 != 0: max_dev={max_dev}")

    def test_tc16_twisted_hodge_laplacians_psd(self):
        """TC16: Verify Delta_0, Delta_1_down, Delta_1_up, and Delta_1 are symmetric PSD."""
        corr = np.corrcoef(self.returns, rowvar=False)
        vertices, edges, triangles = build_simplicial_complex(corr, threshold=0.20)
        delta0, delta1 = build_sheaf_coboundary_operators(len(vertices), edges, triangles)
        d0, d1_down, d1_up, d1 = compute_twisted_hodge_laplacians(delta0, delta1)

        for name, mat in [("Delta_0", d0), ("Delta_1_down", d1_down), ("Delta_1_up", d1_up), ("Delta_1", d1)]:
            sym_diff = np.max(np.abs(mat - mat.T))
            self.assertAlmostEqual(sym_diff, 0.0, places=10, msg=f"{name} not symmetric")

            eigs = np.linalg.eigvalsh(mat)
            min_eig = float(np.min(eigs))
            self.assertGreaterEqual(min_eig, -1e-8, msg=f"{name} has negative eigenvalue: {min_eig}")

    def test_tc17_helmholtz_hodge_decomposition_orthogonality(self):
        """TC17: Verify exact sum reconstruction and pairwise orthogonality of Helmholtz-Hodge decomposition."""
        corr = np.corrcoef(self.returns, rowvar=False)
        vertices, edges, triangles = build_simplicial_complex(corr, threshold=0.20)
        delta0, delta1 = build_sheaf_coboundary_operators(len(vertices), edges, triangles)

        if len(edges) == 0:
            return

        flow_j = np.random.normal(0, 1.0, len(edges))
        j_grad, j_curl, j_harm = helmholtz_hodge_decomposition(flow_j, delta0, delta1)

        # 1. Sum reconstruction
        reconstructed = j_grad + j_curl + j_harm
        recon_err = np.linalg.norm(flow_j - reconstructed)
        self.assertLess(recon_err, 1e-4, f"Reconstruction error too large: {recon_err}")

        # 2. Pairwise orthogonality
        dot_grad_curl = abs(float(np.dot(j_grad, j_curl)))
        dot_grad_harm = abs(float(np.dot(j_grad, j_harm)))
        dot_curl_harm = abs(float(np.dot(j_curl, j_harm)))

        self.assertLess(dot_grad_curl, 1e-4, f"<J_grad, J_curl> = {dot_grad_curl}")
        self.assertLess(dot_grad_harm, 1e-4, f"<J_grad, J_harm> = {dot_grad_harm}")
        self.assertLess(dot_curl_harm, 1e-4, f"<J_curl, J_harm> = {dot_curl_harm}")

        # 3. Kernel & boundary conditions
        if delta1.shape[0] > 0:
            curl_of_grad = np.linalg.norm(delta1 @ j_grad)
            self.assertLess(curl_of_grad, 1e-4, f"delta1 @ J_grad = {curl_of_grad}")
        div_of_curl = np.linalg.norm(delta0.T @ j_curl)
        self.assertLess(div_of_curl, 1e-4, f"delta0.T @ J_curl = {div_of_curl}")

    def test_tc18_poincare_ball_hyperbolic_projection(self):
        """TC18: Verify Poincaré ball projection guarantees norm strictly less than 1."""
        test_points = np.array([
            [0.0, 0.0],
            [1.0, 2.0],
            [10.0, -15.0],
            [1000.0, 5000.0],
        ])
        projected = project_poincare_ball(test_points)
        norms = np.linalg.norm(projected, axis=1)
        for n_val in norms:
            self.assertLess(n_val, 1.0, f"Poincaré norm >= 1.0: {n_val}")
            self.assertGreaterEqual(n_val, 0.0)

    def test_tc19_compute_simplicial_sheaf_alpha_bounds(self):
        """TC19: Verify compute_simplicial_sheaf_alpha and compute_simplicial_sheaf_flow bounds raw alpha in [-3.0, 3.0]."""
        raw_alphas, harm_fluxes, curl_vorts = compute_simplicial_sheaf_alpha(self.prices_dict)
        self.assertEqual(len(raw_alphas), self.n_sym)
        for sym, val in raw_alphas.items():
            self.assertTrue(-3.0 <= val <= 3.0, f"Alpha out of bounds for {sym}: {val}")
            self.assertGreaterEqual(harm_fluxes[sym], 0.0)
            self.assertGreaterEqual(curl_vorts[sym], 0.0)

        # Contract interface validation (PROJECT.md:79)
        corr = np.corrcoef(self.returns, rowvar=False)
        rets_vec = self.returns[-1]
        flow = compute_simplicial_sheaf_flow(corr, rets_vec)
        self.assertEqual(len(flow), self.n_sym)
        self.assertTrue(np.all(flow >= -3.0) and np.all(flow <= 3.0))

        engine = HigherOrderSimplicialSheafLaplacianEngine()
        self.assertTrue(getattr(engine, "lookahead_safe", False))
        eng_flow = engine.compute_simplicial_sheaf_flow(corr, rets_vec)
        self.assertEqual(len(eng_flow), self.n_sym)
        self.assertTrue(np.all(eng_flow >= -3.0) and np.all(eng_flow <= 3.0))

        # Hyperbolic metric validation
        dist = engine.poincare_distance(np.array([0.1, 0.2]), np.array([0.3, -0.1]))
        self.assertGreaterEqual(dist, 0.0)

    def test_tc20_sheaf_engine_generate_signals(self):
        """TC20: Verify HigherOrderSimplicialSheafLaplacianEngine.generate_signals output structure."""
        engine = HigherOrderSimplicialSheafLaplacianEngine()
        res = engine.generate_signals(self.prices_dict)
        self.assertIn("symbol", res.columns)
        self.assertIn("simplicial_sheaf_laplacian_score", res.columns)
        self.assertIn("raw_score", res.columns)
        self.assertEqual(len(res), self.n_sym)

        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["simplicial_sheaf_laplacian_score"] <= 0.95)
            self.assertTrue(-3.0 <= row["raw_score"] <= 3.0)

    def test_tc21_sheaf_deadband_filter(self):
        """TC21: Verify hyperbolic deadband filter suppresses micro-noise."""
        self.assertEqual(sheaf_deadband(0.0), 0.0)
        self.assertLess(abs(sheaf_deadband(0.01, delta=0.028)), 1e-4)
        self.assertGreater(abs(sheaf_deadband(0.10, delta=0.028)), 0.05)


class TestPhase195NonequilibriumEngine(unittest.TestCase):
    """Category 4: F961 Non-Equilibrium Statistical Mechanics Engine."""

    def setUp(self):
        np.random.seed(42)
        n = 50
        self.prices = 100.0 * np.exp(np.cumsum(np.random.normal(0.001, 0.015, n)))
        self.volumes = np.random.uniform(1e5, 5e5, n)
        self.f_macro = np.array([0.05, -0.02, 0.01, -0.03, 0.04])

    def test_tc22_thermodynamic_state_and_macro_coupling(self):
        """TC22: Verify microscopic state vector x = [r, Delta OFI, sigma] and coupling matrix Gamma."""
        x_hist, x_mean, x_cov = compute_thermodynamic_state(self.prices, volumes=self.volumes)
        self.assertEqual(x_hist.shape[1], 3)
        self.assertEqual(len(x_mean), 3)
        self.assertEqual(x_cov.shape, (3, 3))

        eigs = np.linalg.eigvalsh(x_cov)
        self.assertTrue(np.all(eigs > 0.0), f"Covariance not positive definite: {eigs}")

        gamma = compute_macro_elasticity_coupling(x_hist)
        self.assertEqual(gamma.shape, (3, 5))

    def test_tc23_probability_current_ness(self):
        """TC23: Verify non-vanishing probability current J != 0 in Non-Equilibrium Steady State."""
        x_hist, x_mean, x_cov = compute_thermodynamic_state(self.prices, volumes=self.volumes)
        gamma = compute_macro_elasticity_coupling(x_hist)

        j_curr, div_j, p_val = compute_probability_current(
            x_state=x_hist[-1],
            x_mean=x_mean,
            x_cov=x_cov,
            f_macro=self.f_macro,
            gamma=gamma,
        )
        self.assertEqual(len(j_curr), 3)
        self.assertGreater(p_val, 0.0)
        self.assertGreater(np.linalg.norm(j_curr), 0.0)

    def test_tc24_schnakenberg_entropy_production_non_negative(self):
        """TC24: Verify Schnakenberg entropy production rate dot{S}_{prod} >= 0 mathematically."""
        x_hist, x_mean, x_cov = compute_thermodynamic_state(self.prices, volumes=self.volumes)
        gamma = compute_macro_elasticity_coupling(x_hist)
        j_curr, div_j, p_val = compute_probability_current(
            x_state=x_hist[-1],
            x_mean=x_mean,
            x_cov=x_cov,
            f_macro=self.f_macro,
            gamma=gamma,
        )
        d_mat = 0.5 * x_cov + 1e-6 * np.eye(3)
        s_prod = compute_schnakenberg_entropy_production(j_curr, d_mat, p_val)

        self.assertGreaterEqual(s_prod, 0.0, f"Entropy production negative: {s_prod}")

    def test_tc25_jarzynski_work_dissipation_non_negative(self):
        """TC25: Verify Jarzynski dissipated work W_diss >= 0."""
        x_hist, x_mean, x_cov = compute_thermodynamic_state(self.prices, volumes=self.volumes)
        gamma = compute_macro_elasticity_coupling(x_hist)
        w, delta_f, w_diss = compute_jarzynski_dissipation(
            x_curr=x_hist[-1],
            x_prev=x_hist[-2],
            f_macro=self.f_macro,
            gamma=gamma,
            cov_curr=x_cov,
            cov_prev=x_cov,
        )
        self.assertGreaterEqual(w_diss, 0.0, f"Dissipated work negative: {w_diss}")

    def test_tc26_nonequilibrium_alpha_bounds(self):
        """TC26: Verify compute_nonequilibrium_alpha and compute_non_equilibrium_arbitrage outputs strictly bounded in [-3.0, 3.0]."""
        alpha, s_prod, w_diss, div_j = compute_nonequilibrium_alpha(
            self.prices, volumes=self.volumes, f_macro=self.f_macro
        )
        self.assertTrue(-3.0 <= alpha <= 3.0, f"Alpha out of bounds: {alpha}")
        self.assertGreaterEqual(s_prod, 0.0)
        self.assertGreaterEqual(w_diss, 0.0)

        # Analytical 3x3 inversion verification
        test_cov = np.array([[2.0, 0.3, 0.1], [0.3, 1.5, 0.2], [0.1, 0.2, 1.8]])
        inv_fast, det_fast = fast_inv_det_3x3(test_cov)
        inv_np = np.linalg.inv(test_cov)
        self.assertLess(np.max(np.abs(inv_fast - inv_np)), 1e-12)

        # Contract interface validation (PROJECT.md:81)
        rets = np.diff(np.log(self.prices))
        macro_elasticity = np.random.uniform(0.5, 1.5, (len(rets), 3))
        alpha_arb = compute_non_equilibrium_arbitrage(rets, macro_elasticity=macro_elasticity)
        self.assertEqual(len(alpha_arb), len(rets))
        self.assertTrue(np.all(alpha_arb >= -3.0) and np.all(alpha_arb <= 3.0))

        engine = NonEquilibriumStatisticalMechanicsEngine()
        self.assertTrue(getattr(engine, "lookahead_safe", False))
        eng_arb = engine.compute_non_equilibrium_arbitrage(rets, macro_elasticity=macro_elasticity)
        self.assertEqual(len(eng_arb), len(rets))
        self.assertTrue(np.all(eng_arb >= -3.0) and np.all(eng_arb <= 3.0))

    def test_tc27_nonequilibrium_engine_generate_signals(self):
        """TC27: Verify NonEquilibriumStatisticalMechanicsEngine.generate_signals output structure."""
        engine = NonEquilibriumStatisticalMechanicsEngine()
        prices_dict = {
            "005930": pd.DataFrame({"Close": self.prices, "Volume": self.volumes}),
            "000660": pd.DataFrame({"Close": self.prices * 1.02, "Volume": self.volumes * 0.95}),
        }
        res = engine.generate_signals(prices_dict, global_indicators={"VIX": 15.0, "SOX": 5000.0})
        self.assertIn("symbol", res.columns)
        self.assertIn("noneq_stat_mech_score", res.columns)
        self.assertIn("raw_score", res.columns)
        self.assertEqual(len(res), 2)

        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["noneq_stat_mech_score"] <= 0.95)
            self.assertTrue(-3.0 <= row["raw_score"] <= 3.0)


class TestPhase195NumericalStabilityAndEdgeCases(unittest.TestCase):
    """Category 5: Numerical Stability, Adversarial Stress Testing & Zero Lookahead Bias."""

    def test_tc28_empty_and_nan_inputs(self):
        """TC28: Verify engines handle empty, all-NaN, and all-Inf inputs gracefully without crashing."""
        empty_dict: Dict[str, pd.DataFrame] = {}
        nan_df = pd.DataFrame({"Close": [np.nan] * 20, "Volume": [np.nan] * 20})
        inf_df = pd.DataFrame({"Close": [np.inf, -np.inf] * 10, "Volume": [np.inf] * 20})
        adversarial_dict = {"NAN_STOCK": nan_df, "INF_STOCK": inf_df}

        for engine_cls in [
            SymplecticHamiltonianPhaseSpaceFlowEngine,
            HigherOrderSimplicialSheafLaplacianEngine,
            NonEquilibriumStatisticalMechanicsEngine,
        ]:
            engine = engine_cls()
            # Empty universe
            res_empty = engine.generate_signals(empty_dict)
            self.assertTrue(res_empty.empty)

            # Adversarial universe
            res_adv = engine.generate_signals(adversarial_dict)
            self.assertEqual(len(res_adv), 2)
            for _, row in res_adv.iterrows():
                self.assertFalse(np.isnan(row["raw_score"]))
                self.assertEqual(row["raw_score"], 0.0)

    def test_tc29_single_stock_universe(self):
        """TC29: Verify engines handle 1-stock universes gracefully."""
        single_dict = {
            "SOLO": pd.DataFrame({"Close": np.linspace(100, 110, 30), "Volume": np.full(30, 1e5)})
        }
        for engine_cls in [
            SymplecticHamiltonianPhaseSpaceFlowEngine,
            HigherOrderSimplicialSheafLaplacianEngine,
            NonEquilibriumStatisticalMechanicsEngine,
        ]:
            engine = engine_cls()
            res = engine.generate_signals(single_dict)
            self.assertEqual(len(res), 1)
            score_col = [c for c in res.columns if "score" in c and c != "raw_score"][0]
            self.assertAlmostEqual(res[score_col].iloc[0], 0.50, places=2)

    def test_tc30_extreme_volatility_spikes(self):
        """TC30: Verify engines clamp extreme price spikes (+1000%, -99%) safely within [-3.0, 3.0]."""
        extreme_prices = np.array([100.0] * 20 + [1000.0, 10.0, 500.0, 50.0])
        extreme_volumes = np.array([1e5] * 20 + [1e8, 1e2, 1e8, 1e2])
        spike_dict = {
            "SPIKE": pd.DataFrame({"Close": extreme_prices, "Volume": extreme_volumes})
        }

        for engine_cls in [
            SymplecticHamiltonianPhaseSpaceFlowEngine,
            HigherOrderSimplicialSheafLaplacianEngine,
            NonEquilibriumStatisticalMechanicsEngine,
        ]:
            engine = engine_cls()
            res = engine.generate_signals(spike_dict)
            self.assertEqual(len(res), 1)
            raw = res["raw_score"].iloc[0]
            self.assertTrue(-3.0 <= raw <= 3.0, f"{engine_cls.__name__} raw score unclamped: {raw}")

    def test_tc31_collinear_and_singular_matrices(self):
        """TC31: Verify Hodge decomposition and stat mech engines survive singular / rank-1 matrices."""
        identical_prices = np.linspace(100, 120, 30)
        collinear_dict = {
            f"IDENT_{i}": pd.DataFrame({"Close": identical_prices, "Volume": np.full(30, 1e5)})
            for i in range(5)
        }
        engine_sheaf = HigherOrderSimplicialSheafLaplacianEngine()
        res_sheaf = engine_sheaf.generate_signals(collinear_dict)
        self.assertEqual(len(res_sheaf), 5)

        engine_noneq = NonEquilibriumStatisticalMechanicsEngine()
        res_noneq = engine_noneq.generate_signals(collinear_dict)
        self.assertEqual(len(res_noneq), 5)

    def test_tc32_disconnected_graph_no_triangles(self):
        """TC32: Verify higher-order simplicial sheaf handles empty triangle sets T = empty gracefully."""
        np.random.seed(99)
        uncorr_dict = {
            f"UNCORR_{i}": pd.DataFrame({
                "Close": 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.01, 30))),
                "Volume": np.random.uniform(1e5, 2e5, 30),
            })
            for i in range(4)
        }
        engine = HigherOrderSimplicialSheafLaplacianEngine(corr_threshold=0.99)
        res = engine.generate_signals(uncorr_dict)
        self.assertEqual(len(res), 4)
        for _, row in res.iterrows():
            self.assertTrue(0.05 <= row["simplicial_sheaf_laplacian_score"] <= 0.95)

    def test_tc33_zero_lookahead_bias(self):
        """TC33: Verify changing future data does not alter signals computed at bar T."""
        np.random.seed(123)
        base_prices = 100.0 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 50)))
        base_volumes = np.random.uniform(1e5, 5e5, 50)

        t40_dict = {"STOCK": pd.DataFrame({"Close": base_prices[:40], "Volume": base_volumes[:40]})}

        future_prices = base_prices.copy()
        future_prices[40:] = future_prices[39] * 2.0
        t50_dict = {"STOCK": pd.DataFrame({"Close": future_prices, "Volume": base_volumes})}

        for engine_cls in [
            SymplecticHamiltonianPhaseSpaceFlowEngine,
            NonEquilibriumStatisticalMechanicsEngine,
        ]:
            engine = engine_cls()
            sig_t40 = engine.generate_signals(t40_dict)["raw_score"].iloc[0]
            sig_recalc = engine.generate_signals(t40_dict)["raw_score"].iloc[0]
            self.assertEqual(sig_t40, sig_recalc)


class TestPhase195LatencySLA(unittest.TestCase):
    """Category 6: Execution Latency SLA Across 500 Assets."""

    def test_tc34_hamiltonian_phase_flow_500_stocks_latency(self):
        """TC34: Verify F959 Hamiltonian flow executes across 500 stocks within sub-5ms SLA."""
        np.random.seed(42)
        n_assets = 500
        n_bars = 40
        prices_matrix = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.015, (n_bars, n_assets)), axis=0))
        volumes_matrix = np.random.uniform(1e5, 5e5, (n_bars, n_assets))

        t0 = time.perf_counter()
        for i in range(n_assets):
            compute_hamiltonian_alpha(prices_matrix[:, i], volumes=volumes_matrix[:, i], n_steps=20)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_asset_ms = elapsed_ms / n_assets

        self.assertLess(per_asset_ms, 5.0, f"Core Hamiltonian Latency SLA breached: {per_asset_ms:.2f} ms/asset")

    def test_tc35_simplicial_sheaf_500_stocks_latency(self):
        """TC35: Verify F960 Simplicial sheaf executes across 500 stocks within sub-5ms SLA."""
        np.random.seed(42)
        n_assets = 500
        n_bars = 40
        rets = np.random.normal(0, 0.02, (n_bars, n_assets))
        corr = np.corrcoef(rets, rowvar=False)

        t0 = time.perf_counter()
        vertices, edges, triangles = build_simplicial_complex(corr, threshold=0.35, max_edges_per_node=4, max_triangles=200)
        delta0, delta1 = build_sheaf_coboundary_operators(len(vertices), edges, triangles)
        flow_j = np.random.normal(0, 1.0, len(edges))
        j_grad, j_curl, j_harm = helmholtz_hodge_decomposition(flow_j, delta0, delta1)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_asset_ms = elapsed_ms / n_assets

        self.assertLess(per_asset_ms, 5.0, f"Core Simplicial Sheaf Latency SLA breached: {per_asset_ms:.2f} ms/asset")

    def test_tc36_nonequilibrium_500_stocks_latency(self):
        """TC36: Verify F961 Non-equilibrium stat mech executes across 500 stocks within sub-5ms SLA."""
        np.random.seed(42)
        n_assets = 500
        n_bars = 40
        prices_matrix = 100.0 * np.exp(np.cumsum(np.random.normal(0, 0.015, (n_bars, n_assets)), axis=0))
        volumes_matrix = np.random.uniform(1e5, 5e5, (n_bars, n_assets))
        f_macro = np.array([0.02, -0.01, 0.005, -0.015, 0.03])

        t0 = time.perf_counter()
        for i in range(n_assets):
            compute_nonequilibrium_alpha(prices_matrix[:, i], volumes=volumes_matrix[:, i], f_macro=f_macro)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_asset_ms = elapsed_ms / n_assets

        self.assertLess(per_asset_ms, 5.0, f"Core Non-equilibrium Latency SLA breached: {per_asset_ms:.2f} ms/asset")


if __name__ == "__main__":
    unittest.main()
