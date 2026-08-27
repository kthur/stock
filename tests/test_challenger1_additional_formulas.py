import numpy as np

def test_additional_formulas():
    # 1. Return-Tilted HRP
    base_alpha = 0.6
    mu_L = 0.15
    mu_R = 0.05
    eta = 1.0
    tilt = (mu_L / mu_R) ** eta
    alpha_tilted = (base_alpha * tilt) / (base_alpha * tilt + (1.0 - base_alpha))
    print(f'R-HRP Tilt test: base={base_alpha}, tilt={tilt}, tilted_alpha={alpha_tilted:.4f}')
    assert alpha_tilted > base_alpha
    assert 0.0 < alpha_tilted < 1.0

    # 2. Kinematic Momentum Cooldown
    for delta_mom in [-1.0, 0.0, 0.5, 1.0, 2.0]:
        tau = max(3, int(np.floor(20.0 * np.exp(-3.0 * max(0.0, delta_mom)))))
        print(f'Kinematic recovery: delta_mom={delta_mom:+.1f} -> tau={tau} days')
        assert 3 <= tau <= 20
        # Position multiplier ramp
        for t in range(tau + 1):
            m_pos = 0.50 + 0.50 * (t / tau) ** 0.75
            assert 0.50 <= m_pos <= 1.0001
            
    print('Additional formulas: ALL VERIFIED')

if __name__ == '__main__':
    test_additional_formulas()
