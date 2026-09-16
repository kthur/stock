import numpy as np
import pandas as pd
import math
from trading_system.src.ai.factor_suppression import (
    apply_centaheptacontahexagonal_hyperbolic_deadband,
    compute_phase46_hyperconvex_rank_modulation,
    get_regime_adaptive_gamma_top_v46
)
from trading_system.src.ai.ensemble_scorer import (
    QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler
)
from trading_system.src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator

print('--- Adversarial Test 1: Rank Modulation Edge Cases ---')
r_test = np.array([-0.5, 0.0, 0.5, 1.0, 1.5])
res_r = compute_phase46_hyperconvex_rank_modulation(r_test, gamma_top=5.30)
print('Rank modulation out of bounds clip check:', res_r[0] == res_r[1], res_r[-1] == res_r[-2])
assert res_r[0] == res_r[1]
assert res_r[-1] == res_r[-2]

print('--- Adversarial Test 2: Hyperbolic Deadband Extreme Cases ---')
z_test = np.array([0.0, 1e-15, -1e-15, 1e3, -1e3])
res_z = apply_centaheptacontahexagonal_hyperbolic_deadband(z_test)
print('Deadband extreme values:', res_z)
assert res_z[0] == 0.0
assert abs(res_z[1]) < 1e-100
assert abs(res_z[2]) < 1e-100
assert np.isclose(res_z[3], 1e3)
assert np.isclose(res_z[4], -1e3)

print('--- Adversarial Test 3: Coupler Extreme/NaN/Zero Cases ---')
coupler = QuantumGeometricLanglandsChiralAffineLieSuperalgebraBorcherdsKacMoodyWhittakerCoupler()
p_nan = pd.DataFrame({
    'val': [np.nan, 0.0],
    'mom': [0.5, np.nan],
    'flow': [0.5, 0.5],
    'cat': [0.5, 0.5],
    'net': [0.5, 0.5]
})
res_nan = coupler(p_nan)
print('Coupler NaN handling:', np.all(np.isfinite(res_nan['h_borch_whit'])))
assert np.all(np.isfinite(res_nan['h_borch_whit']))

print('--- Adversarial Test 4: EVaR Degenerate/Extreme Return Cases ---')
allocator = UnifiedPortfolioAllocator()
r_const = np.zeros(100)
evar_const = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_risk_measure(r_const)
print('EVaR constant zeros:', evar_const['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_value'])
assert np.isfinite(evar_const['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_value'])

r_extreme = np.array([-0.99, -0.95, -0.90, -0.85])
evar_ext = allocator.compute_trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_risk_measure(r_extreme)
print('EVaR extreme crash:', evar_ext['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_value'])
assert np.isfinite(evar_ext['trans_singular_eternal_omni_cosmic_infinite_supreme_transcendent_clausen_scholze_deligne_beilinson_w_algebra_virasoro_kac_moody_borcherds_evar_value'])

print('--- Adversarial Test 5: Barycenter Extreme/Corner Weights ---')
w_corner = {'bl': 1.0, 'herc': 0.0, 'rp': 0.0, 'cvar': 0.0}
bary_corner = allocator.compute_lurie_borcherds_whittaker_fisher_rao_barycenter_blend(w_corner)
print('Barycenter corner weights:', bary_corner)
assert math.isclose(sum(bary_corner.values()), 1.0, rel_tol=1e-5)
assert all(v > 0 for v in bary_corner.values())

print('ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY!')
