import numpy as np
import pandas as pd
import pytest
from trading_system.src.ai.cpcv_stress_tester import (
    CPCVStressTester,
    StressTestReport,
    run_historical_stress_test,
)
from trading_system.src.risk.risk_manager import RiskManager, RiskLevel


def test_generate_purged_folds_combinatorics():
    tester = CPCVStressTester(n_splits=6, n_test_splits=2, purge_window=5, embargo_window=10)
    data = pd.DataFrame(np.random.randn(300, 4))
    folds = tester.generate_purged_folds(data)

    # C(6, 2) = 15 splits
    assert len(folds) == 15
    for train_idx, test_idx, test_blocks in folds:
        assert len(train_idx) > 0
        assert len(test_idx) > 0
        assert len(np.intersect1d(train_idx, test_idx)) == 0


def test_purging_and_embargo_boundaries():
    n_samples = 300
    n_splits = 6
    purge = 5
    embargo = 10
    tester = CPCVStressTester(
        n_splits=n_splits,
        n_test_splits=2,
        purge_window=purge,
        embargo_window=embargo,
    )
    data = np.random.randn(n_samples, 2)
    folds = tester.generate_purged_folds(data)

    block_bounds = np.linspace(0, n_samples, n_splits + 1, dtype=int)

    for train_idx, test_idx, test_blocks in folds:
        train_set = set(train_idx)
        for b in test_blocks:
            start_b = block_bounds[b]
            end_b = block_bounds[b + 1]

            # Purge region before test block
            purge_indices = set(range(max(0, start_b - purge), start_b))
            assert len(train_set.intersection(purge_indices)) == 0

            # Embargo region after test block
            embargo_indices = set(range(end_b, min(n_samples, end_b + embargo)))
            assert len(train_set.intersection(embargo_indices)) == 0


def test_pbo_calculation():
    tester = CPCVStressTester(n_splits=6, n_test_splits=2)
    np.random.seed(42)
    matrix = np.random.randn(300, 10) * 0.01
    res = tester.compute_pbo(matrix)

    assert "pbo" in res
    assert "logits" in res
    assert "ranks" in res
    assert "is_overfitted" in res
    assert 0.0 <= res["pbo"] <= 1.0
    assert len(res["logits"]) == 15
    assert len(res["ranks"]) == 15

    for logit in res["logits"]:
        assert np.isfinite(logit)


def test_historical_stress_test_scenarios():
    np.random.seed(42)
    returns = pd.Series(np.random.randn(250) * 0.01 + 0.0005)

    for scenario in ["2008_CRISIS", "2020_COVID", "2022_FED_HIKE"]:
        report = run_historical_stress_test(returns, scenario=scenario, mdd_threshold=0.35)

        assert isinstance(report, StressTestReport)
        assert report.scenario == scenario
        assert 0.0 <= report.mdd <= 1.0
        assert report.var_95 <= 0.0
        assert report.cvar_95 <= report.var_95
        assert report.var_99 <= report.var_95
        assert report.cvar_99 <= report.var_99
        assert isinstance(report.pass_flag, bool)
        assert isinstance(report.to_dict(), dict)


def test_stress_test_dataframe():
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "strat1": np.random.randn(200) * 0.01,
            "strat2": np.random.randn(200) * 0.01 + 0.001,
        }
    )
    reports = run_historical_stress_test(df, scenario="2008_CRISIS")

    assert isinstance(reports, dict)
    assert "strat1" in reports
    assert "strat2" in reports
    assert isinstance(reports["strat1"], StressTestReport)
    assert isinstance(reports["strat2"], StressTestReport)


def test_risk_manager_stress_integration():
    risk_mgr = RiskManager()
    assert risk_mgr.stress_test_passed is True
    assert risk_mgr.stress_test_adjustment_factor == 1.0

    pass_report = StressTestReport(
        scenario="2008_CRISIS",
        mdd=0.15,
        var_95=-0.02,
        var_99=-0.04,
        cvar_95=-0.03,
        cvar_99=-0.05,
        stress_sharpe=1.2,
        stress_recovery_time=20,
        pass_flag=True,
        details={},
    )
    risk_mgr.update_stress_test_results(pass_report)
    assert risk_mgr.stress_test_passed is True
    assert risk_mgr.stress_test_adjustment_factor == 1.0

    fail_report = StressTestReport(
        scenario="2008_CRISIS",
        mdd=0.45,
        var_95=-0.05,
        var_99=-0.08,
        cvar_95=-0.07,
        cvar_99=-0.10,
        stress_sharpe=-0.5,
        stress_recovery_time=100,
        pass_flag=False,
        details={},
    )
    risk_mgr.update_stress_test_results({"2008_CRISIS": fail_report})
    assert risk_mgr.stress_test_passed is False
    assert risk_mgr.stress_test_adjustment_factor == 0.75

    normal_max = risk_mgr.calculate_max_position_size(100.0)
    adjusted_pos = risk_mgr.get_risk_adjusted_position_size(100, RiskLevel.LOW)
    assert adjusted_pos == 75

    # Explicitly verify calculate_position_sizing scales by exactly 0.75x (not 0.5625x) when stress test fails
    risk_mgr.stress_test_adjustment_factor = 1.0
    unpenalized_qty = risk_mgr.calculate_position_sizing("AAPL", entry_price=100.0, stop_loss_price=95.0)
    assert unpenalized_qty == 2500

    risk_mgr.stress_test_adjustment_factor = 0.75
    failed_qty = risk_mgr.calculate_position_sizing("AAPL", entry_price=100.0, stop_loss_price=95.0)
    expected_0_75_quantity = int(unpenalized_qty * 0.75)  # 2,500 * 0.75 = 1875
    assert failed_qty == expected_0_75_quantity
    assert failed_qty == 1875


def test_cpcv_inf_nan_finiteness_guard():
    tester = CPCVStressTester(n_splits=6, n_test_splits=2)
    matrix = np.array([
        [0.01, np.nan],
        [np.inf, -0.02],
        [-np.inf, 0.015],
        [0.005, 0.01],
        [np.nan, np.nan],
        [0.02, -0.01]
    ])
    res = tester.compute_pbo(matrix)
    assert isinstance(res, dict)
    assert "pbo" in res

    series_with_inf = pd.Series([0.01, np.inf, -np.inf, np.nan, 0.02, -0.01])
    report = tester.run_historical_stress_test(series_with_inf, scenario="2008_CRISIS")
    assert isinstance(report, StressTestReport)
    assert np.isfinite(report.stress_sharpe)


def test_cpcv_small_sample_size_guard():
    tester = CPCVStressTester()
    # Small sample (<4 samples)
    matrix_small = np.random.randn(3, 2)
    res_small = tester.compute_pbo(matrix_small)
    assert res_small["pbo"] == 0.0
    assert res_small["n_combinations"] == 0

    # Single model (<2 models)
    matrix_1col = np.random.randn(10, 1)
    res_1col = tester.compute_pbo(matrix_1col)
    assert res_1col["pbo"] == 0.0

    # Single return bar in stress test (<2 bars)
    short_series = pd.Series([0.05])
    report = tester.run_historical_stress_test(short_series)
    assert report.stress_sharpe == 0.0

