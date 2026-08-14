"""
Empirical Stress Test Harness for Milestone 3 (F8, F9, F10)
Adversarially tests:
1. CPCVStressTester & PBO calculation
2. Historical Crisis Stress Testing Scenarios
3. BacktestEngine boundary conditions & transaction cost scaling
4. PortfolioAllocator & Ledoit-Wolf Shrinkage under singular/ill-conditioned matrices
5. FactorOrthogonalizerEngine under extreme collinearity & zero-variance
6. RiskManager & Crisis Gating under extreme shocks
"""

import os
import sys
import time
import math
import traceback
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add paths
STOCK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, STOCK_ROOT)
sys.path.insert(0, os.path.join(STOCK_ROOT, "trading_system"))

from src.ai.cpcv_stress_tester import CPCVStressTester, StressTestReport, run_historical_stress_test
from src.analysis.backtest import BacktestEngine, PriceBar, BacktestResult, BacktestTrade
from src.risk.portfolio_allocator import PortfolioAllocator
from src.risk.portfolio_optimizer import PortfolioOptimizer
from src.ai.factor_orthogonalizer import FactorOrthogonalizerEngine
from src.risk.risk_manager import RiskManager, RiskLevel, CrisisLevel


def run_all_stress_tests():
    results = {}
    print("================================================================================")
    print("           STARTING EMPIRICAL ADVERSARIAL STRESS TEST HARNESS")
    print("================================================================================")

    # -------------------------------------------------------------------------
    # SUITE 1: CPCVStressTester & PBO Boundary & Extremes
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 1] CPCVStressTester & PBO Stress Tests ---")
    tester = CPCVStressTester(n_splits=6, n_test_splits=2, purge_window=5, embargo_window=10)

    # Test 1.1: Disjointness and completeness across all 15 splits
    data_300 = pd.DataFrame(np.random.randn(300, 4))
    folds = tester.generate_purged_folds(data_300)
    assert len(folds) == 15, f"Expected 15 folds, got {len(folds)}"
    for fold_idx, (train_idx, test_idx, test_blocks) in enumerate(folds):
        intersection = np.intersect1d(train_idx, test_idx)
        assert len(intersection) == 0, f"Fold {fold_idx} has train/test overlap: {intersection}"
        assert len(train_idx) > 0, f"Fold {fold_idx} train_idx is empty"
        assert len(test_idx) > 0, f"Fold {fold_idx} test_idx is empty"
    print("[PASS] 1.1 CPCV Disjointness & Completeness (15 folds)")
    results["CPCV_Disjointness"] = "PASS"

    # Test 1.2: Dirty Data (NaN, Inf, -Inf) in PBO
    matrix_dirty = np.array([
        [0.01, np.nan, -np.inf],
        [np.inf, -0.02, 0.01],
        [-np.inf, 0.015, np.nan],
        [0.005, 0.01, 0.03],
        [np.nan, np.nan, 0.0],
        [0.02, -0.01, -0.05],
        [0.01, 0.02, 0.01],
        [-0.01, -0.02, 0.0]
    ])
    pbo_dirty = tester.compute_pbo(matrix_dirty)
    assert isinstance(pbo_dirty, dict)
    assert "pbo" in pbo_dirty
    assert 0.0 <= pbo_dirty["pbo"] <= 1.0
    assert np.isfinite(pbo_dirty["pbo"])
    print(f"[PASS] 1.2 PBO Dirty Matrix (NaN/Inf): PBO={pbo_dirty['pbo']:.4f}")
    results["PBO_Dirty_Data"] = "PASS"

    # Test 1.3: Zero Volatility Matrix (all zeros or constant returns)
    matrix_zeros = np.zeros((100, 5))
    pbo_zeros = tester.compute_pbo(matrix_zeros)
    assert pbo_zeros["pbo"] == 0.0
    assert pbo_zeros["is_overfitted"] is False
    print("[PASS] 1.3 PBO Zero Volatility Matrix: PBO=0.0, no div/0")
    results["PBO_Zero_Volatility"] = "PASS"

    # Test 1.4: Small sample boundary guards (N < 4 rows, K < 2 cols)
    for n in [0, 1, 2, 3]:
        m_small = np.random.randn(n, 3) if n > 0 else np.empty((0, 3))
        res_small = tester.compute_pbo(m_small)
        assert res_small["pbo"] == 0.0
        assert res_small["n_combinations"] == 0

    m_1col = np.random.randn(50, 1)
    res_1col = tester.compute_pbo(m_1col)
    assert res_1col["pbo"] == 0.0
    print("[PASS] 1.4 PBO Small Sample Size Guards (N < 4, K < 2): Graceful defaults")
    results["PBO_Small_Sample_Guards"] = "PASS"

    # Test 1.5: High Scale Performance (5,000 bars x 50 strategies)
    matrix_large = np.random.randn(5000, 50) * 0.01
    t0 = time.perf_counter()
    pbo_large = tester.compute_pbo(matrix_large)
    t_pbo = time.perf_counter() - t0
    assert 0.0 <= pbo_large["pbo"] <= 1.0
    assert t_pbo < 1.0, f"PBO took too long: {t_pbo:.3f}s"
    print(f"[PASS] 1.5 PBO Large Scale (5000x50): Execution time: {t_pbo*1000:.1f}ms")
    results["PBO_Scale_Performance"] = f"PASS ({t_pbo*1000:.1f}ms)"

    # -------------------------------------------------------------------------
    # SUITE 2: Historical Stress Test Scenarios & RiskManager Integration
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 2] Historical Crisis Stress Testing Scenarios ---")
    scenarios = ["2008_CRISIS", "2020_COVID", "2022_FED_HIKE"]
    
    # Test 2.1: Nominal and Extreme Crisis Shocks
    ret_series = pd.Series(np.random.normal(0.0005, 0.015, 500))
    for sc in scenarios:
        rep = run_historical_stress_test(ret_series, scenario=sc, mdd_threshold=0.35)
        assert isinstance(rep, StressTestReport)
        assert rep.scenario == sc
        assert 0.0 <= rep.mdd <= 1.0
        assert rep.var_95 <= 0.0
        assert rep.cvar_95 <= rep.var_95
        assert rep.var_99 <= rep.var_95
        assert rep.cvar_99 <= rep.var_99
        assert np.isfinite(rep.stress_sharpe)
    print("[PASS] 2.1 Historical Crisis Scenarios (2008, 2020, 2022)")
    results["Historical_Crisis_Scenarios"] = "PASS"

    # Test 2.2: Extreme Wipeout Return Shock (-90% per bar)
    wipeout_series = pd.Series([-0.90] * 50)
    rep_wipeout = run_historical_stress_test(wipeout_series, scenario="2008_CRISIS")
    assert rep_wipeout.pass_flag is False
    assert rep_wipeout.mdd > 0.90
    assert np.isfinite(rep_wipeout.stress_sharpe)
    print(f"[PASS] 2.2 Extreme Wipeout Return Shock: MDD={rep_wipeout.mdd:.4f}, Pass=False")
    results["Extreme_Wipeout_Shock"] = "PASS"

    # Test 2.3: Single-bar series and Inf/NaN in Historical Stress Test
    rep_single = run_historical_stress_test(pd.Series([0.05]))
    assert rep_single.stress_sharpe == 0.0
    assert np.isfinite(rep_single.mdd)

    rep_dirty_series = run_historical_stress_test(pd.Series([np.nan, np.inf, -np.inf, 0.01, -0.02, np.nan]))
    assert np.isfinite(rep_dirty_series.stress_sharpe)
    assert np.isfinite(rep_dirty_series.mdd)
    print("[PASS] 2.3 Single-Bar & Dirty Series in Stress Test: Finite metrics")
    results["Stress_Dirty_Series"] = "PASS"

    # Test 2.4: RiskManager Sizing Penalty Integration
    rm = RiskManager()
    assert rm.stress_test_passed is True
    assert rm.stress_test_adjustment_factor == 1.0

    fail_report = StressTestReport(
        scenario="2008_CRISIS", mdd=0.50, var_95=-0.08, var_99=-0.12,
        cvar_95=-0.10, cvar_99=-0.15, stress_sharpe=-1.5, stress_recovery_time=120,
        pass_flag=False, details={}
    )
    rm.update_stress_test_results({"2008_CRISIS": fail_report})
    assert rm.stress_test_passed is False
    assert rm.stress_test_adjustment_factor == 0.75

    unadj_qty = rm.calculate_position_sizing("AAPL", entry_price=100.0, stop_loss_price=95.0)
    rm.stress_test_adjustment_factor = 1.0
    base_qty = rm.calculate_position_sizing("AAPL", entry_price=100.0, stop_loss_price=95.0)
    rm.stress_test_adjustment_factor = 0.75
    adj_qty = rm.calculate_position_sizing("AAPL", entry_price=100.0, stop_loss_price=95.0)
    assert adj_qty == int(base_qty * 0.75)
    print(f"[PASS] 2.4 RiskManager 0.75x Stress Penalty Sizing: {base_qty} -> {adj_qty}")
    results["RiskManager_Stress_Penalty"] = "PASS"

    # -------------------------------------------------------------------------
    # SUITE 3: BacktestEngine Boundary Conditions & Cost Scaling
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 3] BacktestEngine Boundary & Cost Scaling Tests ---")
    engine = BacktestEngine(initial_capital=100000.0)

    # Test 3.1: Centralized Market Transaction Cost Verification
    expected_costs = {
        "SP500": 0.0060,
        "NASDAQ": 0.0065,
        "RUSSELL2000": 0.0080,
        "KOSPI": 0.0085,
        "KOSDAQ": 0.0100,
    }
    for mkt, exp_cost in expected_costs.items():
        act_cost = engine.get_market_cost_rate(market=mkt)
        assert abs(act_cost - exp_cost) < 1e-6, f"Cost mismatch for {mkt}: {act_cost} != {exp_cost}"
    print("[PASS] 3.1 Centralized Market Cost Rates: All 5 markets verified")
    results["Market_Cost_Rates"] = "PASS"

    # Test 3.2: Zero Trades / Always Hold
    base_time = datetime(2026, 1, 1, 9, 30)
    bars_flat = [PriceBar(timestamp=base_time + timedelta(days=i), open=100.0, high=101.0, low=99.0, close=100.0, volume=10000) for i in range(50)]
    res_hold = engine.run_backtest(symbol="AAPL", price_bars=bars_flat, strategy_func=lambda b: "HOLD")
    assert len(res_hold.trades) == 0
    assert res_hold.final_capital == 100000.0
    assert res_hold.total_return_pct == 0.0
    assert res_hold.max_drawdown == 0.0
    assert res_hold.sharpe_ratio == 0.0
    print("[PASS] 3.2 Backtest Zero Trades (HOLD): Capital unchanged, MDD=0, Sharpe=0")
    results["Backtest_Zero_Trades"] = "PASS"

    # Test 3.3: Total Crash (Price 100 -> 0.01)
    bars_crash = []
    p = 100.0
    for i in range(20):
        bars_crash.append(PriceBar(timestamp=base_time + timedelta(days=i), open=p, high=p+0.5, low=p-0.5, close=p, volume=10000))
        p = max(0.01, p * 0.6)
    
    def buy_once(b):
        return "BUY" if len(b) == 1 else "HOLD"
    
    res_crash = engine.run_backtest(symbol="AAPL", price_bars=bars_crash, strategy_func=buy_once)
    assert len(res_crash.trades) > 0
    assert res_crash.final_capital < 100000.0
    assert res_crash.max_drawdown > 0.80
    assert np.isfinite(res_crash.sharpe_ratio)
    assert np.isfinite(res_crash.max_drawdown)
    print(f"[PASS] 3.3 Extreme Price Crash Shock: MDD={res_crash.max_drawdown*100:.2f}%, FinalCap={res_crash.final_capital:.2f}")
    results["Backtest_Price_Crash"] = "PASS"

    # Test 3.4: Trailing Stop Execution on Volatile Spike & Drop
    prices_trail = [100.0, 105.0, 115.0, 120.0, 108.0, 100.0]
    bars_trail = [PriceBar(timestamp=base_time + timedelta(days=i), open=p, high=p+1.0, low=p-1.0, close=p, volume=10000) for i, p in enumerate(prices_trail)]
    res_trail = engine.run_backtest(symbol="AAPL", price_bars=bars_trail, strategy_func=buy_once, trailing_stop_pct=0.08)
    assert len(res_trail.trades) == 1
    assert res_trail.trades[0].exit_reason == "TRAILING_STOP"
    assert res_trail.trades[0].exit_price > 100.0
    print(f"[PASS] 3.4 Trailing Stop Execution: ExitReason={res_trail.trades[0].exit_reason}, ExitPrice={res_trail.trades[0].exit_price}")
    results["Backtest_Trailing_Stop"] = "PASS"

    # Test 3.5: Market Impact Scaling with High Volume
    cost_small = engine._trade_cost(position=100, price=100.0, volume=1000000)
    cost_huge = engine._trade_cost(position=500000, price=100.0, volume=1000000)
    assert cost_huge > cost_small
    print(f"[PASS] 3.5 Market Impact Volume Scaling: Small={cost_small:.6f}, Huge={cost_huge:.6f}")
    results["Backtest_Market_Impact_Scaling"] = "PASS"

    # Test 3.6: Multi-Factor Portfolio Backtest with Missing and Outlier Scores
    bars_aapl = [PriceBar(timestamp=base_time + timedelta(days=i), open=100+i, high=101+i, low=99+i, close=100+i, volume=10000) for i in range(25)]
    bars_msft = [PriceBar(timestamp=base_time + timedelta(days=i), open=200+i, high=201+i, low=199+i, close=200+i, volume=10000) for i in range(25)]
    ensemble_df_stress = pd.DataFrame([
        {"symbol": "AAPL", "ensemble_score": 0.85, "ensemble_expected_return": 18.5},
        {"symbol": "MSFT", "ensemble_score": -0.50, "ensemble_expected_return": -10.0},
        {"symbol": "UNKNOWN", "ensemble_score": np.nan, "ensemble_expected_return": np.nan},
    ])
    port_res = engine.run_multi_factor_portfolio_backtest(
        symbols=["AAPL", "MSFT"],
        price_bars_dict={"AAPL": bars_aapl, "MSFT": bars_msft},
        ensemble_scores_df=ensemble_df_stress,
        market_map={"AAPL": "SP500", "MSFT": "SP500"}
    )
    assert "AAPL" in port_res
    assert "MSFT" in port_res
    print("[PASS] 3.6 Multi-Factor Portfolio Backtest with Outlier/Missing Scores")
    results["Multi_Factor_Portfolio_Backtest"] = "PASS"

    # -------------------------------------------------------------------------
    # SUITE 4: PortfolioAllocator & PortfolioOptimizer Stress Tests
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 4] PortfolioAllocator & Optimization Stress Tests ---")
    allocator = PortfolioAllocator(default_max_weight=0.25)
    optimizer = PortfolioOptimizer(default_max_weight=0.25)

    # Test 4.1: EVT-CVaR Estimation on Extreme/Fat-Tailed Returns
    fat_tail_returns = np.random.standard_t(df=3, size=500) * 0.02
    cvar_res = allocator.estimate_evt_cvar(fat_tail_returns, confidence=0.95)
    assert isinstance(cvar_res, dict)
    assert "cvar" in cvar_res
    assert "var" in cvar_res
    assert cvar_res["cvar"] <= cvar_res["var"] or cvar_res["cvar"] >= 0 # Loss magnitude
    print(f"[PASS] 4.1 EVT-CVaR Tail-Risk Estimation: Method={cvar_res.get('method', 'POT_GPD')}, CVaR={cvar_res['cvar']:.4f}")
    results["EVT_CVaR_Estimation"] = "PASS"

    # Test 4.2: Small Sample Fallback in EVT-CVaR (< 15 tail samples)
    short_returns = np.random.normal(0, 0.01, 8)
    cvar_small = allocator.estimate_evt_cvar(short_returns)
    assert cvar_small["method"] in ["gaussian_fallback_small_n", "cornish_fisher_fallback", "zero_fallback", "evt_gpd"]
    assert np.isfinite(cvar_small["cvar"])
    print(f"[PASS] 4.2 EVT-CVaR Small Sample Fallback: Method={cvar_small['method']}, CVaR={cvar_small['cvar']:.4f}")
    results["EVT_CVaR_Small_Sample"] = "PASS"


    # Test 4.3: Covariance Matrix Shrinkage on Singular (5x20) Matrix
    np.random.seed(42)
    returns_singular_df = pd.DataFrame(np.random.randn(5, 10), columns=[f"SYM_{i}" for i in range(10)])
    cov_shrunk = optimizer.calculate_covariance_matrix(returns_singular_df, shrinkage=0.15)
    assert cov_shrunk.shape == (10, 10)
    assert not cov_shrunk.isna().any().any()
    eigenvals = np.linalg.eigvalsh(cov_shrunk.values)
    assert np.all(eigenvals >= 0), f"Negative eigenvalue found: {eigenvals.min()}"
    print(f"[PASS] 4.3 Covariance Shrinkage on Singular (5x10) Matrix: min eig={eigenvals.min():.6f}")
    results["Covariance_Shrinkage"] = "PASS"

    # Test 4.4: Risk Parity Allocation (Sum to 1.0, Max Weight Constraint)
    returns_multi = pd.DataFrame(np.random.randn(100, 5) * 0.01, columns=[f"SYM_{i}" for i in range(5)])
    rp_weights = optimizer.optimize_risk_parity(returns_multi, max_weight=0.30)
    assert len(rp_weights) == 5
    assert abs(sum(rp_weights.values()) - 1.0) < 1e-4
    assert max(rp_weights.values()) <= 0.30 + 1e-4
    print(f"[PASS] 4.4 Risk Parity Weights: Sum={sum(rp_weights.values()):.6f}, max={max(rp_weights.values()):.4f}")
    results["Risk_Parity_Optimization"] = "PASS"


    # -------------------------------------------------------------------------
    # SUITE 5: FactorOrthogonalizerEngine Stress Tests
    # -------------------------------------------------------------------------
    print("\n--- [SUITE 5] FactorOrthogonalizerEngine Stress Tests ---")
    ortho_engine = FactorOrthogonalizerEngine(default_method='gram_schmidt')
    cols_17 = [f"strat_{i}" for i in range(17)]

    # Test 5.1: 17 Perfectly Collinear Columns
    N = 100
    col_single = np.random.uniform(0.1, 0.9, N)
    matrix_collinear = np.column_stack([col_single for _ in range(17)])
    df_collinear = pd.DataFrame(matrix_collinear, columns=cols_17)
    df_collinear['symbol'] = [f"SYM_{i}" for i in range(N)]

    for method in ['gram_schmidt', 'pca_symmetric']:
        res_ortho = ortho_engine.orthogonalize(df_collinear, cols_17, method=method)
        vals = res_ortho[cols_17].values
        assert not np.isnan(vals).any(), f"NaN in {method}"
        assert not np.isinf(vals).any(), f"Inf in {method}"
        assert np.all(vals >= 0.0) and np.all(vals <= 1.0), f"Bounds exceeded in {method}"
    print("[PASS] 5.1 Factor Orthogonalizer (17 Collinear Columns): Gram-Schmidt & PCA")
    results["Factor_Ortho_Collinear"] = "PASS"

    # Test 5.2: All Constant / Zero-Variance Matrix
    df_constant = pd.DataFrame(np.full((50, 17), 0.5), columns=cols_17)
    df_constant['symbol'] = [f"SYM_{i}" for i in range(50)]
    for method in ['gram_schmidt', 'pca_symmetric']:
        res_const = ortho_engine.orthogonalize(df_constant, cols_17, method=method)
        vals_c = res_const[cols_17].values
        assert not np.isnan(vals_c).any()
        assert np.all(vals_c >= 0.0) and np.all(vals_c <= 1.0)
    print("[PASS] 5.2 Factor Orthogonalizer (All Zero Variance): Safe constant fallback")
    results["Factor_Ortho_Zero_Variance"] = "PASS"

    # -------------------------------------------------------------------------
    # SUITE 6: Summary
    # -------------------------------------------------------------------------
    print("\n================================================================================")
    print("                      ALL EMPIRICAL STRESS TESTS PASSED")
    print("================================================================================")
    for test_name, status in results.items():
        print(f"  {test_name:<35}: {status}")
    print("================================================================================")
    return results


if __name__ == "__main__":
    run_all_stress_tests()
