import numpy as np

def test_performance_tables():
    markets = {
        'SP500': {'base_cagr': 17.2, 'opt_cagr': 24.6, 'base_sh': 1.28, 'opt_sh': 1.82, 'base_sort': 1.72, 'opt_sort': 2.58, 'base_cal': 1.16, 'opt_cal': 2.14, 'base_mdd': -14.8, 'opt_mdd': -11.5, 'base_win': 53.8, 'opt_win': 58.4, 'base_pf': 1.62, 'opt_pf': 1.94, 'base_to': 285, 'opt_to': 145},
        'NASDAQ': {'base_cagr': 20.8, 'opt_cagr': 30.4, 'base_sh': 1.31, 'opt_sh': 1.91, 'base_sort': 1.80, 'opt_sort': 2.74, 'base_cal': 1.11, 'opt_cal': 2.20, 'base_mdd': -18.7, 'opt_mdd': -13.8, 'base_win': 54.2, 'opt_win': 59.1, 'base_pf': 1.68, 'opt_pf': 2.05, 'base_to': 340, 'opt_to': 175},
        'RUSSELL2000': {'base_cagr': 15.4, 'opt_cagr': 23.8, 'base_sh': 1.08, 'opt_sh': 1.65, 'base_sort': 1.42, 'opt_sort': 2.32, 'base_cal': 0.76, 'opt_cal': 1.64, 'base_mdd': -20.2, 'opt_mdd': -14.5, 'base_win': 51.8, 'opt_win': 56.8, 'base_pf': 1.48, 'opt_pf': 1.82, 'base_to': 360, 'opt_to': 185},
        'KOSPI': {'base_cagr': 16.5, 'opt_cagr': 24.2, 'base_sh': 1.24, 'opt_sh': 1.80, 'base_sort': 1.65, 'opt_sort': 2.52, 'base_cal': 1.04, 'opt_cal': 2.02, 'base_mdd': -15.8, 'opt_mdd': -12.0, 'base_win': 53.2, 'opt_win': 57.9, 'base_pf': 1.58, 'opt_pf': 1.90, 'base_to': 290, 'opt_to': 150},
        'KOSDAQ': {'base_cagr': 18.2, 'opt_cagr': 27.5, 'base_sh': 1.18, 'opt_sh': 1.75, 'base_sort': 1.58, 'opt_sort': 2.45, 'base_cal': 0.93, 'opt_cal': 1.92, 'base_mdd': -19.5, 'opt_mdd': -14.3, 'base_win': 52.6, 'opt_win': 57.4, 'base_pf': 1.54, 'opt_pf': 1.88, 'base_to': 350, 'opt_to': 170},
        'Consolidated': {'base_cagr': 18.4, 'opt_cagr': 26.8, 'base_sh': 1.32, 'opt_sh': 1.88, 'base_sort': 1.78, 'opt_sort': 2.65, 'base_cal': 1.15, 'opt_cal': 2.09, 'base_mdd': -16.0, 'opt_mdd': -12.8, 'base_win': 53.5, 'opt_win': 58.2, 'base_pf': 1.60, 'opt_pf': 1.96, 'base_to': 320, 'opt_to': 165},
    }
    
    report_deltas = {
        'SP500': {'d_cagr': 7.4, 'd_sh': 0.54, 'd_sort': 0.86, 'd_cal': 0.98, 'd_mdd': 3.3, 'd_win': 4.6, 'd_pf': 0.32, 'd_to': -140},
        'NASDAQ': {'d_cagr': 9.6, 'd_sh': 0.60, 'd_sort': 0.94, 'd_cal': 1.09, 'd_mdd': 4.9, 'd_win': 4.9, 'd_pf': 0.37, 'd_to': -165},
        'RUSSELL2000': {'d_cagr': 8.4, 'd_sh': 0.57, 'd_sort': 0.90, 'd_cal': 0.88, 'd_mdd': 5.7, 'd_win': 5.0, 'd_pf': 0.34, 'd_to': -175},
        'KOSPI': {'d_cagr': 7.7, 'd_sh': 0.56, 'd_sort': 0.87, 'd_cal': 0.98, 'd_mdd': 3.8, 'd_win': 4.7, 'd_pf': 0.32, 'd_to': -140},
        'KOSDAQ': {'d_cagr': 9.3, 'd_sh': 0.57, 'd_sort': 0.87, 'd_cal': 0.99, 'd_mdd': 5.2, 'd_win': 4.8, 'd_pf': 0.34, 'd_to': -180},
        'Consolidated': {'d_cagr': 8.4, 'd_sh': 0.56, 'd_sort': 0.87, 'd_cal': 0.94, 'd_mdd': 3.2, 'd_win': 4.7, 'd_pf': 0.36, 'd_to': -155},
    }

    for m, v in markets.items():
        rep = report_deltas[m]
        assert np.isclose(v['opt_cagr'] - v['base_cagr'], rep['d_cagr'], atol=1e-5), f"{m} CAGR delta mismatch"
        assert np.isclose(v['opt_sh'] - v['base_sh'], rep['d_sh'], atol=1e-5), f"{m} Sharpe delta mismatch"
        assert np.isclose(v['opt_sort'] - v['base_sort'], rep['d_sort'], atol=1e-5), f"{m} Sortino delta mismatch"
        assert np.isclose(abs(v['base_mdd']) - abs(v['opt_mdd']), rep['d_mdd'], atol=1e-5), f"{m} MDD delta mismatch"
        assert np.isclose(v['opt_win'] - v['base_win'], rep['d_win'], atol=1e-5), f"{m} Win Rate delta mismatch"
        assert np.isclose(v['opt_pf'] - v['base_pf'], rep['d_pf'], atol=1e-5), f"{m} Profit Factor delta mismatch"
        assert v['opt_to'] - v['base_to'] == rep['d_to'], f"{m} Turnover delta mismatch"
        
        # Check Calmar ratio definition: CAGR / |MDD|
        calc_base_cal = round(v['base_cagr'] / abs(v['base_mdd']), 2)
        calc_opt_cal = round(v['opt_cagr'] / abs(v['opt_mdd']), 2)
        assert np.isclose(calc_base_cal, v['base_cal'], atol=0.01), f"{m} Base Calmar mismatch: {calc_base_cal} vs {v['base_cal']}"
        assert np.isclose(calc_opt_cal, v['opt_cal'], atol=0.01), f"{m} Opt Calmar mismatch: {calc_opt_cal} vs {v['opt_cal']}"
        assert np.isclose(v['opt_cal'] - v['base_cal'], rep['d_cal'], atol=1e-5), f"{m} Calmar delta mismatch"

def test_return_attribution_decomposition():
    attribution = [
        ('Alpha Unblocking (6 Zeroed Strategies)', 2.15, 0.14, -0.6, +15),
        ('Return-Tilted HRP (R-HRP)', 2.40, 0.16, -0.4, +10),
        ('Target Volatility sqrt(h) Scaling', 1.35, 0.09, -0.2, -5),
        ('Single-Stage Entropy Collinearity Allocation', 0.95, 0.07, -0.5, -25),
        ('Asymmetric Pseudo-Huber & Focal Loss', 0.80, 0.06, -0.8, -10),
        ('Kinematic Momentum Crisis Recovery', 0.75, 0.05, -0.3, +8),
        ('Microstructure Friction Sizing & Leland Bands', 0.65, 0.05, -0.4, -148),
    ]
    
    sum_cagr = sum(x[1] for x in attribution)
    sum_sh = sum(x[2] for x in attribution)
    sum_mdd = sum(x[3] for x in attribution)
    sum_to = sum(x[4] for x in attribution)
    
    print(f"Attribution sums: CAGR={sum_cagr:.4f}, Sharpe={sum_sh:.4f}, MDD={sum_mdd:.4f}, Turnover={sum_to}")
    
    # Check against report's total row (8.40%, +0.56, -3.2%, -155%)
    # Let's inspect the discrepancy!
    assert np.isclose(sum_mdd, -3.2, atol=1e-5), f"MDD sum mismatch: {sum_mdd}"
    assert sum_to == -155, f"Turnover sum mismatch: {sum_to}"

if __name__ == '__main__':
    test_performance_tables()
    test_return_attribution_decomposition()
    print("ALL BASIC TABLE CHECKS COMPLETE")
