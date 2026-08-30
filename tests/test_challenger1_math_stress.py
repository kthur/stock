import numpy as np
import sympy as sp

def test_asymmetric_pseudo_huber():
    print('=== TESTING ASYMMETRIC PSEUDO-HUBER LOSS ===')
    y_sym, yhat_sym, delta_sym, alpha_sym = sp.symbols('y yhat delta alpha', real=True, positive=True)
    # Define error e = yhat - y
    e_sym = sp.Symbol('e', real=True)
    
    # Loss for e > 0: s(e) = (1 + alpha)
    L_pos = delta_sym**2 * (sp.sqrt(1 + (e_sym/delta_sym)**2) - 1) * (1 + alpha_sym)
    g_pos = sp.diff(L_pos, e_sym)
    h_pos = sp.diff(g_pos, e_sym)
    
    # Loss for e < 0: s(e) = (1 - alpha)
    L_neg = delta_sym**2 * (sp.sqrt(1 + (e_sym/delta_sym)**2) - 1) * (1 - alpha_sym)
    g_neg = sp.diff(L_neg, e_sym)
    h_neg = sp.diff(g_neg, e_sym)
    
    print('SymPy derived g_pos (e > 0):', g_pos)
    print('SymPy derived h_pos (e > 0):', h_pos)
    print('SymPy derived g_neg (e < 0):', g_neg)
    print('SymPy derived h_neg (e < 0):', h_neg)
    
    # Verify report formulas:
    # g(e) = (e / sqrt(1 + (e/delta)^2)) * (1 + alpha * sign(e))
    # h(e) = (1 / (1 + (e/delta)^2)^(3/2)) * (1 + alpha * sign(e))
    
    # Asymptotic limits:
    lim_g_pos_inf = sp.limit(g_pos, e_sym, sp.oo)
    lim_h_pos_inf = sp.limit(h_pos, e_sym, sp.oo)
    lim_g_neg_inf = sp.limit(g_neg, e_sym, -sp.oo)
    lim_h_neg_inf = sp.limit(h_neg, e_sym, -sp.oo)
    
    print('Limit g as e -> +oo (crash/overestimation):', lim_g_pos_inf)
    print('Limit h as e -> +oo (crash/overestimation):', lim_h_pos_inf)
    print('Limit g as e -> -oo (jump/underestimation):', lim_g_neg_inf)
    print('Limit h as e -> -oo (jump/underestimation):', lim_h_neg_inf)
    
    # Numerical testing
    delta = 1.0
    alpha = 0.2
    
    def loss_fn(y_true, y_pred):
        e = y_pred - y_true
        s = 1.0 + alpha * np.sign(e)
        return delta**2 * (np.sqrt(1.0 + (e/delta)**2) - 1.0) * s
        
    def grad_hess(y_true, y_pred):
        e = y_pred - y_true
        s = 1.0 + alpha * np.sign(e)
        u = e / delta
        denom = np.sqrt(1.0 + u**2)
        grad = (e / denom) * s
        hess = (1.0 / (denom**3)) * s
        return grad, hess

    # Extreme test cases:
    # 1. Extreme positive jump (y >> yhat, e.g. y = +100.0, yhat = 0.0 -> e = -100.0)
    g_jump, h_jump = grad_hess(100.0, 0.0)
    print(f'\nExtreme positive jump (y=100, yhat=0): e=-100, grad={g_jump:.6f}, hess={h_jump:.8f}')
    print(f'Expected asymptotic grad: {-delta * (1.0 - alpha):.6f}')
    
    # 2. Extreme negative crash (y << yhat, e.g. y = -100.0, yhat = 0.0 -> e = +100.0)
    g_crash, h_crash = grad_hess(-100.0, 0.0)
    print(f'Extreme negative crash (y=-100, yhat=0): e=+100, grad={g_crash:.6f}, hess={h_crash:.8f}')
    print(f'Expected asymptotic grad: {+delta * (1.0 + alpha):.6f}')
    
    # Asymmetry ratio
    print(f'Asymmetry ratio |g_crash / g_jump|: {abs(g_crash / g_jump):.4f} (Theoretical: {(1+alpha)/(1-alpha):.4f})')
    
    # Numerical finite differences check
    for e_val in [-50.0, -10.0, -1.0, -0.1, 0.1, 1.0, 10.0, 50.0]:
        y_t = 0.0
        y_p = e_val
        eps = 1e-6
        l_plus = loss_fn(y_t, y_p + eps)
        l_minus = loss_fn(y_t, y_p - eps)
        num_grad = (l_plus - l_minus) / (2 * eps)
        ana_grad, ana_hess = grad_hess(y_t, y_p)
        
        g_plus, _ = grad_hess(y_t, y_p + eps)
        g_minus, _ = grad_hess(y_t, y_p - eps)
        num_hess = (g_plus - g_minus) / (2 * eps)
        
        assert np.isclose(num_grad, ana_grad, atol=1e-4), f'Grad mismatch at e={e_val}: {num_grad} vs {ana_grad}'
        assert np.isclose(num_hess, ana_hess, atol=1e-4), f'Hess mismatch at e={e_val}: {num_hess} vs {ana_hess}'
        assert ana_hess > 0, f'Hessian non-positive at e={e_val}'
    print('Finite difference check: ALL PASSED')

def test_clayton_copula():
    print('\n=== TESTING CLAYTON COPULA TAIL DEPENDENCE ===')
    u_sym, theta_sym = sp.symbols('u theta', real=True, positive=True)
    # Bivariate Clayton copula C(u, u) = (2*u**(-theta) - 1)**(-1/theta)
    C_uu = (2 * u_sym**(-theta_sym) - 1)**(-1/theta_sym)
    
    # Lower tail dependence: lim_{u -> 0+} C(u, u) / u
    # C(u, u) / u = (2*u^(-theta) - 1)^(-1/theta) / (u^(-theta))^(-1/theta) = (2 - u^theta)^(-1/theta)
    ratio = (2 - u_sym**theta_sym)**(-1/theta_sym)
    lambda_L_sym = sp.limit(ratio, u_sym, 0)
    print('SymPy derived lambda_L:', lambda_L_sym)
    
    # Target lambda_L = 0.55 in report line 872
    target_lambda_L = 0.55
    theta_calc = -1.0 / np.log2(target_lambda_L)
    print(f'Calculated theta for lambda_L={target_lambda_L}: {theta_calc:.4f}')
    
    # Upper tail dependence: lim_{u -> 1-} (1 - 2u + C(u, u)) / (1 - u)
    lambda_U_sym = sp.limit((1 - 2*u_sym + C_uu)/(1 - u_sym), u_sym, 1)
    print('SymPy derived lambda_U:', lambda_U_sym)
    
    # Empirical simulation of Clayton Copula
    np.random.seed(42)
    N = 1_000_000
    # Sampling Clayton copula:
    # v1 ~ Uniform(0, 1)
    # v2 ~ Uniform(0, 1)
    # u1 = v1
    # u2 = (v1**(-theta) * (v2**(-theta / (1 + theta)) - 1) + 1)**(-1/theta)
    v1 = np.random.uniform(0, 1, N)
    v2 = np.random.uniform(0, 1, N)
    theta = theta_calc
    u1 = v1
    u2 = (v1**(-theta) * (v2**(-theta / (1.0 + theta)) - 1.0) + 1.0)**(-1.0 / theta)
    
    # Check empirical lower tail dependence at small u thresholds:
    for threshold in [0.05, 0.02, 0.01, 0.005, 0.001]:
        joint_prob = np.mean((u1 <= threshold) & (u2 <= threshold))
        emp_lambda_L = joint_prob / threshold
        print(f'Empirical lambda_L at u={threshold:.3f}: {emp_lambda_L:.4f} (Theoretical: {target_lambda_L:.4f})')
        
    # Check empirical upper tail dependence at u -> 1:
    for threshold in [0.95, 0.98, 0.99, 0.995]:
        joint_upper = np.mean((u1 > threshold) & (u2 > threshold))
        emp_lambda_U = joint_upper / (1.0 - threshold)
        print(f'Empirical lambda_U at u={threshold:.3f}: {emp_lambda_U:.4f} (Theoretical: 0.0000)')

if __name__ == '__main__':
    test_asymmetric_pseudo_huber()
    test_clayton_copula()
