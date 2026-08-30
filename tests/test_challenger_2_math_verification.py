"""
Empirical Verification & Stress Test Harness for Challenger 2
Stress-testing all mathematical, statistical, and econometric formulations in system_improvement_report_v6.md.
"""
import unittest
import numpy as np
import scipy.stats as stats
from scipy.optimize import minimize


class TestChallenger2MathVerification(unittest.TestCase):
    """Empirical mathematical & econometric verification for v6 formulations."""

    # ==============================================================================
    # TEST 1: GPD Tail Index Bounds & POT CVaR Quantile Inversion (V6-11)
    # ==============================================================================
    def test_evt_pot_tail_index_bounds(self):
        def simulate_evt_pot(losses, confidence=0.95, quantile_threshold=0.90, fix_bounds=True):
            N = len(losses)
            sigma_l = float(np.std(losses))
            u_quantile = float(np.quantile(losses, quantile_threshold))
            u_volatility = float(np.mean(losses) + 1.5 * sigma_l)
            
            if fix_bounds:
                u_max_allowed = float(np.quantile(losses, min(0.92, confidence - 0.02)))
                u = min(max(u_quantile, u_volatility), u_max_allowed)
            else:
                u = max(u_quantile, u_volatility)
                
            exceedances = losses[losses > u] - u
            n_u = len(exceedances)
            
            if n_u < 5:
                return {"status": "insufficient_exceedances", "u": u, "n_u": n_u}
                
            mean_exc = np.mean(exceedances)
            var_exc = np.var(exceedances)
            if var_exc > 0:
                xi_est = 0.5 * (1.0 - (mean_exc ** 2) / var_exc)
                beta_est = 0.5 * mean_exc * ((mean_exc ** 2) / var_exc + 1.0)
            else:
                xi_est, beta_est = 0.1, max(1e-4, mean_exc)
                
            if fix_bounds:
                xi_clamped = float(np.clip(xi_est, -0.50, 0.50))
            else:
                xi_clamped = min(xi_est, 0.50)
                
            tail_ratio = (N / n_u) * (1.0 - confidence)
            
            if abs(xi_clamped) < 1e-4:
                var_alpha = u - beta_est * np.log(max(1e-8, tail_ratio))
                cvar_alpha = var_alpha + beta_est
            else:
                var_alpha = u + (beta_est / xi_clamped) * (max(1e-8, tail_ratio) ** (-xi_clamped) - 1.0)
                cvar_alpha = (var_alpha / (1.0 - xi_clamped)) + ((beta_est - xi_clamped * u) / (1.0 - xi_clamped))
                
            return {
                "u": u,
                "n_u": n_u,
                "tail_ratio": tail_ratio,
                "xi_clamped": xi_clamped,
                "var_alpha": var_alpha,
                "cvar_alpha": cvar_alpha,
                "is_inverted": var_alpha < u,
                "is_cvar_sub_var": cvar_alpha < var_alpha
            }

        np.random.seed(42)
        quiet_losses = -np.random.normal(loc=0.005, scale=0.010, size=500)
        res_fixed = simulate_evt_pot(quiet_losses, confidence=0.95, fix_bounds=True)
        self.assertFalse(res_fixed['is_inverted'], "Fixed EVT must not invert VaR < u")
        self.assertFalse(res_fixed['is_cvar_sub_var'], "CVaR must be >= VaR")

        t_losses = -stats.t.rvs(df=3, loc=0, scale=0.015, size=500)
        res_t_fixed = simulate_evt_pot(t_losses, confidence=0.95, fix_bounds=True)
        self.assertFalse(res_t_fixed['is_inverted'], "Fat-tail EVT must not invert VaR < u")
        self.assertFalse(res_t_fixed['is_cvar_sub_var'], "Fat-tail CVaR must be >= VaR")

    # ==============================================================================
    # TEST 2: Leland Dynamic Buffer Band & Boundary Conditions (V6-09)
    # ==============================================================================
    def test_leland_dynamic_buffer_band(self):
        def evaluate_leland_buffer(w_curr, w_targ, vol=0.02, cost=0.002, gamma=2.5, fix_boundary=True):
            delta_floor = 0.005
            delta_cap = 0.050
            if w_targ <= 0.0:
                delta_i = delta_floor
            else:
                ann_variance = 252.0 * (vol ** 2)
                cubic_term = (3.0 * cost * w_targ * ann_variance) / (4.0 * gamma)
                delta_raw = float(np.cbrt(cubic_term))
                delta_i = float(np.clip(delta_raw, delta_floor, delta_cap))
            
            if fix_boundary and w_targ > 0.0:
                delta_i = min(delta_i, w_targ * 0.40)
                
            L_i = max(0.0, w_targ - delta_i)
            U_i = w_targ + delta_i
            
            is_new_entry = (w_curr == 0.0 and w_targ > 0.0)
            is_full_exit = (w_targ == 0.0 and w_curr > 0.0)
            
            if fix_boundary:
                inside_band = (L_i <= w_curr <= U_i) and not is_new_entry and not is_full_exit
            else:
                inside_band = (L_i <= w_curr <= U_i)
                
            action = "HOLD" if inside_band else ("BUY" if w_targ > w_curr else "SELL")
            return {"delta": delta_i, "L": L_i, "U": U_i, "inside_band": inside_band, "action": action}

        entry_buggy = evaluate_leland_buffer(0.0, 0.005, fix_boundary=False)
        entry_fixed = evaluate_leland_buffer(0.0, 0.005, fix_boundary=True)
        exit_buggy = evaluate_leland_buffer(0.004, 0.0, fix_boundary=False)
        exit_fixed = evaluate_leland_buffer(0.004, 0.0, fix_boundary=True)

        self.assertEqual(entry_buggy['action'], "HOLD")
        self.assertEqual(entry_fixed['action'], "BUY")
        self.assertEqual(exit_buggy['action'], "HOLD")
        self.assertEqual(exit_fixed['action'], "SELL")

    # ==============================================================================
    # TEST 3: Rockafellar-Uryasev Auxiliary Variable Formulation & L1 Smoothing (V6-12)
    # ==============================================================================
    def test_rockafellar_uryasev_cvar(self):
        def optimize_ru_cvar(r_mat, w_prev, alpha_cvar=0.95, smooth_l1=True, vectorized=True):
            T, N = r_mat.shape
            cvar_coef = 1.0 / ((1.0 - alpha_cvar) * T)
            cov_mat = np.cov(r_mat, rowvar=False)
            
            x0 = np.zeros(N + 1 + T)
            x0[:N] = 1.0 / N
            x0[N] = 0.01
            x0[N+1:] = 0.01
            
            bounds = [(0.0, 0.20)] * N + [(-1.0, 1.0)] + [(0.0, None)] * T
            
            def objective(x):
                w = x[:N]
                zeta = x[N]
                u = x[N+1:]
                
                cvar_val = zeta + cvar_coef * np.sum(u)
                risk_term = 0.5 * float(w.T @ cov_mat @ w)
                
                if smooth_l1:
                    diff = np.sqrt((w - w_prev)**2 + 1e-6)
                    turnover_term = 0.002 * float(np.sum(diff))
                else:
                    turnover_term = 0.002 * float(np.sum(np.abs(w - w_prev)))
                    
                return cvar_val + risk_term + turnover_term
                
            constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x[:N]) - 1.0}]
            
            if vectorized:
                constraints.append({
                    'type': 'ineq',
                    'fun': lambda x: x[N+1:] + (r_mat @ x[:N]) + x[N]
                })
            else:
                for t in range(T):
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda x, t_i=t: x[N + 1 + t_i] + float(np.dot(r_mat[t_i], x[:N])) + x[N]
                    })
                    
            res = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints, options={'maxiter': 100})
            return res

        np.random.seed(42)
        R_sample = np.random.normal(loc=0.0005, scale=0.015, size=(60, 5))
        w_init = np.array([0.2, 0.2, 0.2, 0.2, 0.2])
        res_smooth = optimize_ru_cvar(R_sample, w_init, smooth_l1=True, vectorized=True)
        self.assertTrue(res_smooth.success)
        self.assertAlmostEqual(float(np.sum(res_smooth.x[:5])), 1.0, places=3)
    # ==============================================================================
    # TEST 4: Black-Litterman Objective & C1 Smoothness (V6-10)
    # ==============================================================================
    def test_black_litterman_c1_smoothness(self):
        def optimize_bl(mu_bl, cov_bl, rf=0.02, use_c1_smooth=True):
            N = len(mu_bl)
            w0 = np.ones(N) / N
            bounds = [(0.0, 0.40)] * N
            constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
            lambda_aversion = 2.5
            
            all_negative_excess = bool(np.max(mu_bl) <= rf)
            
            def objective(w):
                w = np.asarray(w)
                port_ret = float(w @ mu_bl)
                port_var = float(w @ cov_bl @ w)
                port_vol = float(np.sqrt(max(1e-8, port_var)))
                
                if use_c1_smooth:
                    if all_negative_excess:
                        return - (port_ret - 0.5 * lambda_aversion * port_var)
                    else:
                        excess = port_ret - rf
                        return - excess / port_vol if excess > 0 else (0.5 * lambda_aversion * port_var - excess * 10.0)
                else:
                    if port_ret <= rf:
                        return - (port_ret - 0.5 * lambda_aversion * port_var)
                    else:
                        return - (port_ret - rf) / port_vol
                        
            res = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
            return res

        mu_boundary = np.array([0.019, 0.021, 0.0205])
        cov_toy = np.array([[0.04, 0.01, 0.01], [0.01, 0.05, 0.015], [0.01, 0.015, 0.045]])
        res_bl_smooth = optimize_bl(mu_boundary, cov_toy, rf=0.02, use_c1_smooth=True)
        self.assertTrue(res_bl_smooth.success)

    # ==============================================================================
    # TEST 5: Almgren-Chriss Slicing Trajectory Hyperbolic Formulation (V6-27)
    # ==============================================================================
    def test_almgren_chriss_trajectory_formulation(self):
        def almgren_chriss_trajectory(total_qty, n_slices=5, vol=0.02, adv=1e9, urgency='medium', fix_scale=True):
            urgency_map = {'fast': 1.0e-3, 'medium': 1.0e-5, 'slow': 1.0e-7}
            lambda_urg = urgency_map.get(urgency, 1.0e-5)
            
            if fix_scale:
                eta = 0.5 * max(vol, 0.01)
                kappa = float(np.clip(np.sqrt(lambda_urg * (vol ** 2) / max(eta, 1e-8)), 0.01, 3.0))
            else:
                eta = 0.5 * (max(vol, 0.01) / max(adv, 1.0))
                kappa = np.sqrt(lambda_urg * (vol ** 2) / max(eta, 1e-8))
                
            t = np.linspace(0, 1, n_slices + 1)
            if kappa > 1e-4:
                traj = np.sinh(kappa * (1.0 - t)) / np.sinh(kappa)
                trades = -np.diff(traj)
                alloc = np.round(trades * total_qty).astype(int)
            else:
                alloc = np.full(n_slices, total_qty // n_slices, dtype=int)
                
            diff_total = total_qty - int(np.sum(alloc))
            if fix_scale:
                if diff_total > 0:
                    for i in range(diff_total):
                        alloc[i % n_slices] += 1
                elif diff_total < 0:
                    rem = abs(diff_total)
                    for i in range(n_slices - 1, -1, -1):
                        sub = min(alloc[i], rem)
                        alloc[i] -= sub
                        rem -= sub
                        if rem <= 0:
                            break
            else:
                alloc[-1] += diff_total
                
            return {'kappa': kappa, 'alloc': alloc, 'has_negative': np.any(alloc < 0), 'sum': np.sum(alloc)}

        res_ac_fixed = almgren_chriss_trajectory(total_qty=50, n_slices=5, vol=0.02, adv=1e9, urgency='fast', fix_scale=True)
        self.assertFalse(res_ac_fixed['has_negative'], 'Fixed AC must never produce negative order quantities')
        self.assertEqual(res_ac_fixed['sum'], 50, 'Fixed AC tranches must sum exactly to total quantity')

    # ==============================================================================
    # TEST 6: Cross-Market Currency Normalization (V6-25)
    # ==============================================================================
    def test_cross_market_currency_normalization(self):
        def compute_order_quantities(portfolio_capital_krw=100_000_000.0, weight=0.05, market='NASDAQ', price=150.0, usdkrw=1350.0, fix_fx=True):
            target_amount_krw = portfolio_capital_krw * weight
            is_krx = market in ['KOSPI', 'KOSDAQ', 'KRX']
            
            if fix_fx:
                effective_target_amount = target_amount_krw if is_krx else (target_amount_krw / usdkrw)
            else:
                effective_target_amount = target_amount_krw
                
            raw_qty = int(effective_target_amount // price)
            actual_cost_krw = (raw_qty * price) if is_krx else (raw_qty * price * usdkrw)
            return {'raw_qty': raw_qty, 'actual_cost_krw': actual_cost_krw, 'cost_ratio': actual_cost_krw / target_amount_krw}

        fx_buggy = compute_order_quantities(fix_fx=False)
        fx_fixed = compute_order_quantities(fix_fx=True)

        self.assertGreaterEqual(fx_buggy['cost_ratio'], 1349.0)
        self.assertTrue(0.95 <= fx_fixed['cost_ratio'] <= 1.0)

    # ==============================================================================
    # TEST 7: Random Matrix Theory (RMT) Noise Trace & Covariance Denoising (V6-16)
    # ==============================================================================
    def test_rmt_noise_variance_denoising(self):
        def run_rmt_denoising(n_assets=50, t_obs=252):
            np.random.seed(42)
            factors = np.random.normal(size=(t_obs, 3))
            loadings = np.random.normal(size=(n_assets, 3))
            noise = np.random.normal(scale=0.5, size=(t_obs, n_assets))
            returns = factors @ loadings.T + noise
            
            corr_mat = np.corrcoef(returns, rowvar=False)
            eigenvals, _ = np.linalg.eigh(corr_mat)
            eigenvals = np.sort(eigenvals)[::-1]
            
            q = float(t_obs) / float(n_assets)
            lambda_plus_buggy = 1.0 * (1.0 + np.sqrt(1.0 / q)) ** 2
            sigma_sq_fixed = float(np.mean(eigenvals[1:]))
            lambda_plus_fixed = sigma_sq_fixed * (1.0 + np.sqrt(1.0 / q)) ** 2
            
            signals_buggy = np.sum(eigenvals > lambda_plus_buggy)
            signals_fixed = np.sum(eigenvals > lambda_plus_fixed)
            return signals_buggy, signals_fixed

        sig_b, sig_f = run_rmt_denoising()
        self.assertGreaterEqual(sig_f, sig_b)


if __name__ == '__main__':
    unittest.main()
