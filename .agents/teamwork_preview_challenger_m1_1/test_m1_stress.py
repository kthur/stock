import sys
import os
import math
import json
import time
import logging
import numpy as np
import pandas as pd

sys.path.insert(0, r"d:\Finance\code\stock")
sys.path.insert(0, r"d:\Finance\code\stock\trading_system")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("m1_stress_test")

def py_native(obj):
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj)
    if isinstance(obj, complex):
        return str(obj)
    if isinstance(obj, dict):
        return {k: py_native(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [py_native(x) for x in obj]
    return str(obj)

def test_1_hrp_weights():
    logger.info("=== TASK 1: Stress-testing calculate_hrp_weights ===")
    from src.analysis.portfolio_optimizer import calculate_hrp_weights

    results = []

    # Case 1.1: Singular covariance matrix (rank 1, all 1s)
    t0 = time.time()
    cov_singular = np.ones((5, 5))
    w = calculate_hrp_weights(cov_singular)
    r1 = {
        "scenario": "Singular matrix (all 1s)",
        "elapsed_sec": round(time.time() - t0, 3),
        "output_shape": len(w),
        "sum_weights": float(np.sum(w)),
        "has_nan": bool(np.isnan(w).any()),
        "has_inf": bool(np.isinf(w).any()),
        "min_w": float(np.min(w)) if len(w) > 0 else None,
        "max_w": float(np.max(w)) if len(w) > 0 else None,
        "passed": bool(len(w) == 5 and not np.isnan(w).any() and abs(np.sum(w) - 1.0) < 1e-4)
    }
    results.append(r1)

    # Case 1.2: Ill-conditioned covariance matrix
    t0 = time.time()
    rng = np.random.RandomState(42)
    A = rng.randn(10, 2)
    cov_ill = A @ A.T
    w_ill = calculate_hrp_weights(cov_ill)
    r2 = {
        "scenario": "Ill-conditioned matrix (rank 2, dim 10)",
        "elapsed_sec": round(time.time() - t0, 3),
        "output_shape": len(w_ill),
        "sum_weights": float(np.sum(w_ill)),
        "has_nan": bool(np.isnan(w_ill).any()),
        "has_inf": bool(np.isinf(w_ill).any()),
        "passed": bool(len(w_ill) == 10 and not np.isnan(w_ill).any() and abs(np.sum(w_ill) - 1.0) < 1e-4)
    }
    results.append(r2)

    # Case 1.3: Extreme high volatility matrix
    t0 = time.time()
    cov_high_vol = np.diag([1e8, 1e6, 1e-6, 1e4, 1.0])
    w_vol = calculate_hrp_weights(cov_high_vol)
    r3 = {
        "scenario": "Extreme high volatility (1e8 to 1e-6)",
        "elapsed_sec": round(time.time() - t0, 3),
        "output_shape": len(w_vol),
        "sum_weights": float(np.sum(w_vol)),
        "has_nan": bool(np.isnan(w_vol).any()),
        "has_inf": bool(np.isinf(w_vol).any()),
        "passed": bool(len(w_vol) == 5 and not np.isnan(w_vol).any() and abs(np.sum(w_vol) - 1.0) < 1e-4)
    }
    results.append(r3)

    # Case 1.4: Matrix with NaNs and Infs
    t0 = time.time()
    cov_nan = np.array([
        [1.0, np.nan, 0.2],
        [np.nan, 2.0, np.inf],
        [0.2, np.inf, 1.5]
    ])
    w_nan = calculate_hrp_weights(cov_nan)
    r4 = {
        "scenario": "Covariance with NaNs/Infs",
        "elapsed_sec": round(time.time() - t0, 3),
        "output_shape": len(w_nan),
        "sum_weights": float(np.sum(w_nan)) if len(w_nan) > 0 else 0.0,
        "has_nan": bool(np.isnan(w_nan).any()) if len(w_nan) > 0 else False,
        "has_inf": bool(np.isinf(w_nan).any()) if len(w_nan) > 0 else False,
        "passed": bool(len(w_nan) == 3 and not np.isnan(w_nan).any() and abs(np.sum(w_nan) - 1.0) < 1e-4)
    }
    results.append(r4)

    return results


def test_2_merge_fundamentals():
    logger.info("=== TASK 2: Stress-testing merge_fundamentals ===")
    from src.ai.prediction_model import OnDevicePredictionModel

    model = OnDevicePredictionModel()
    results = []

    class MockStorage:
        def __init__(self, df_fun):
            self.df_fun = df_fun
        def get_fundamentals(self, symbol):
            return self.df_fun.copy()

    fun_data = pd.DataFrame({
        'date': ['2022-12-31', '2023-12-31'],
        'symbol': ['TEST_SYM', 'TEST_SYM'],
        'revenue': [1000.0, 1500.0],
        'operating_income': [200.0, 300.0],
        'net_income': [150.0, 250.0],
        'eps': [1.5, 2.5],
        'dividend_per_share': [0.5, 0.6],
        'book_value': [10.0, 12.0]
    })

    # Case 2.1: Price data with unnamed DatetimeIndex
    t0 = time.time()
    dates_prices = pd.date_range('2023-12-01', '2024-04-01', freq='B')
    df_prices_unnamed = pd.DataFrame({
        'Open': 100.0,
        'High': 105.0,
        'Low': 95.0,
        'Close': 102.0,
        'Volume': 10000.0
    }, index=dates_prices)
    df_prices_unnamed.index.name = None

    try:
        merged_1 = model.merge_fundamentals('TEST_SYM', df_prices_unnamed, storage=MockStorage(fun_data))
        rev_jan15 = merged_1.loc['2024-01-15', 'revenue'] if '2024-01-15' in merged_1.index else None
        rev_mar15 = merged_1.loc['2024-03-15', 'revenue'] if '2024-03-15' in merged_1.index else None
        lookahead_pass = (rev_jan15 == 1000.0 and rev_mar15 == 1500.0)
        r1 = {
            "scenario": "Unnamed DatetimeIndex & 60d Filing Lag Verification",
            "elapsed_sec": round(time.time() - t0, 3),
            "rev_jan15_before_60d": float(rev_jan15) if rev_jan15 is not None else None,
            "rev_mar15_after_60d": float(rev_mar15) if rev_mar15 is not None else None,
            "lookahead_leakage_free": lookahead_pass,
            "passed": bool(lookahead_pass and len(merged_1) == len(df_prices_unnamed))
        }
    except Exception as e:
        r1 = {
            "scenario": "Unnamed DatetimeIndex & 60d Filing Lag Verification",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "passed": False
        }
    results.append(r1)

    # Case 2.2: Benchmark symbol like AAPL where 'book_value' key was missing in fallback dict
    t0 = time.time()
    try:
        merged_aapl = model.merge_fundamentals('AAPL', df_prices_unnamed, storage=MockStorage(fun_data))
        r_aapl = {
            "scenario": "Benchmark symbol AAPL (KeyError 'book_value' test)",
            "elapsed_sec": round(time.time() - t0, 3),
            "passed": True
        }
    except Exception as e:
        r_aapl = {
            "scenario": "Benchmark symbol AAPL (KeyError 'book_value' test)",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "passed": False
        }
    results.append(r_aapl)

    # Case 2.3: Out-of-order timestamps & Duplicate dates
    t0 = time.time()
    out_of_order_dates = pd.to_datetime(['2024-02-01', '2024-01-01', '2024-01-01', '2024-03-01'])
    df_prices_dupes = pd.DataFrame({
        'Date': out_of_order_dates,
        'Open': [100, 90, 91, 110],
        'High': [105, 95, 96, 115],
        'Low': [95, 85, 86, 105],
        'Close': [102, 92, 93, 112],
        'Volume': [1000, 1000, 1000, 1000]
    })
    
    fun_dupes = pd.DataFrame({
        'date': ['2023-12-31', '2023-12-31', '2022-12-31'],
        'symbol': ['TEST_SYM', 'TEST_SYM', 'TEST_SYM'],
        'revenue': [1400.0, 1500.0, 1000.0],
        'operating_income': [280.0, 300.0, 200.0],
        'net_income': [240.0, 250.0, 150.0],
        'eps': [2.4, 2.5, 1.5],
        'dividend_per_share': [0.6, 0.6, 0.5],
        'book_value': [11.0, 12.0, 10.0]
    })

    try:
        merged_2 = model.merge_fundamentals('TEST_SYM', df_prices_dupes, storage=MockStorage(fun_dupes))
        r2 = {
            "scenario": "Out-of-order timestamps & Duplicate dates",
            "elapsed_sec": round(time.time() - t0, 3),
            "output_rows": len(merged_2),
            "index_has_duplicates": bool(merged_2.index.has_duplicates),
            "is_chronological": bool(pd.Series(merged_2.index).is_monotonic_increasing),
            "passed": bool(not merged_2.index.has_duplicates and pd.Series(merged_2.index).is_monotonic_increasing)
        }
    except Exception as e:
        r2 = {
            "scenario": "Out-of-order timestamps & Duplicate dates",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "passed": False
        }
    results.append(r2)

    # Case 2.4: Missing columns in price dataframe
    t0 = time.time()
    df_prices_missing = pd.DataFrame({
        'Close': [100.0, 101.0, 102.0]
    }, index=pd.date_range('2024-01-01', periods=3))
    
    try:
        merged_3 = model.merge_fundamentals('TEST_SYM', df_prices_missing, storage=MockStorage(fun_data))
        r3 = {
            "scenario": "Missing price columns (only Close)",
            "elapsed_sec": round(time.time() - t0, 3),
            "columns_present": list(merged_3.columns),
            "has_revenue": 'revenue' in merged_3.columns,
            "has_has_fundamental": 'has_fundamental' in merged_3.columns,
            "passed": bool('revenue' in merged_3.columns and 'has_fundamental' in merged_3.columns)
        }
    except Exception as e:
        r3 = {
            "scenario": "Missing price columns (only Close)",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "passed": False
        }
    results.append(r3)

    return results


def test_3_advanced_statistics():
    logger.info("=== TASK 3: Stress-testing AdvancedStatistics.get_performance_summary ===")
    from src.analysis.statistics import AdvancedStatistics

    stats = AdvancedStatistics()
    results = []

    drawdown_cases = [
        ("total_return = -1.5 (Equity curve goes negative)", [100.0, 50.0, -50.0]),
        ("total_return = -2.0", [100.0, 0.0, -100.0]),
        ("total_return = 0.0", [100.0, 100.0, 100.0]),
        ("total_return = -1.0", [100.0, 50.0, 0.0])
    ]

    for label, eq in drawdown_cases:
        t0 = time.time()
        try:
            summary = stats.get_performance_summary(eq, trades=[])
            has_complex = any(isinstance(v, complex) for v in summary.values())
            
            json_serializable = True
            json_err = None
            try:
                json_str = json.dumps(summary)
                if "NaN" in json_str or "Infinity" in json_str:
                    json_serializable = False
                    json_err = "JSON contains NaN or Infinity non-standard tokens"
            except Exception as e:
                json_serializable = False
                json_err = str(e)

            res = {
                "scenario": label,
                "elapsed_sec": round(time.time() - t0, 3),
                "total_return": summary.get("total_return"),
                "annual_return": str(summary.get("annual_return")),
                "annual_return_type": type(summary.get("annual_return")).__name__,
                "has_complex": has_complex,
                "json_serializable": json_serializable,
                "json_error": json_err,
                "passed": bool(not has_complex and json_serializable)
            }
        except Exception as e:
            res = {
                "scenario": label,
                "elapsed_sec": round(time.time() - t0, 3),
                "error": str(e),
                "passed": False
            }
        results.append(res)

    # Test trades with 0 loss (profit factor = inf case)
    t0 = time.time()
    try:
        trades_zero_loss = [{"pnl": 100.0}, {"pnl": 50.0}]
        summary_inf = stats.get_performance_summary([100.0, 250.0], trades=trades_zero_loss)
        has_complex = any(isinstance(v, complex) for v in summary_inf.values())
        
        json_strict_pass = True
        json_err = None
        try:
            json_str_strict = json.dumps(summary_inf, allow_nan=False)
        except Exception as e:
            json_strict_pass = False
            json_err = str(e)

        r_inf = {
            "scenario": "Trades with 0 losses (profit_factor=inf)",
            "elapsed_sec": round(time.time() - t0, 3),
            "profit_factor": str(summary_inf.get("profit_factor")),
            "json_strict_serializable": json_strict_pass,
            "json_error": json_err if not json_strict_pass else None,
            "passed": json_strict_pass
        }
    except Exception as e:
        r_inf = {
            "scenario": "Trades with 0 losses (profit_factor=inf)",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "passed": False
        }
    results.append(r_inf)

    return results


def test_4_intraday_stop_loss():
    logger.info("=== TASK 4: Stress-testing IntradayStopLossEngine ===")
    from src.risk.intraday_stop_loss import IntradayStopLossEngine, IntradayTick

    engine = IntradayStopLossEngine()
    results = []

    # Case 4.1: Extreme price drop (50% drop)
    t0 = time.time()
    engine.reset_all()
    df_drop = pd.DataFrame({
        'close': [100.0, 95.0, 80.0, 50.0],
        'volume': [1000.0, 1000.0, 2000.0, 5000.0],
        'high': [100.0, 95.0, 80.0, 50.0]
    })
    sig_drop = engine.evaluate('AAPL', df_drop)
    r1 = {
        "scenario": "Extreme 50% price drop",
        "elapsed_sec": round(time.time() - t0, 3),
        "triggered": sig_drop.triggered,
        "reason": sig_drop.reason,
        "drop_pct": sig_drop.drop_pct,
        "recommended_action": sig_drop.recommended_action,
        "passed": bool(sig_drop.triggered and "PEAK_TO_TROUGH_DROP" in sig_drop.reason)
    }
    results.append(r1)

    # Case 4.2: NaN / Inf inputs in DataFrame
    t0 = time.time()
    engine.reset_all()
    df_nan = pd.DataFrame({
        'close': [100.0, np.nan, np.inf, 90.0],
        'volume': [1000.0, 1000.0, 1000.0, np.nan],
        'high': [100.0, np.nan, np.inf, 95.0]
    })
    sig_nan = engine.evaluate('AAPL', df_nan)
    r2 = {
        "scenario": "NaN/Inf inputs in DataFrame",
        "elapsed_sec": round(time.time() - t0, 3),
        "triggered": sig_nan.triggered,
        "reason": sig_nan.reason,
        "passed": bool(not np.isnan(sig_nan.drop_pct) and not np.isinf(sig_nan.drop_pct))
    }
    results.append(r2)

    # Case 4.3: Volume spike (20x volume with price drop)
    t0 = time.time()
    engine.reset_all()
    df_vol = pd.DataFrame({
        'close': [100.0]*19 + [98.0],
        'volume': [1000.0]*19 + [20000.0],
        'high': [100.0]*20
    })
    sig_vol = engine.evaluate('AAPL', df_vol)
    r3 = {
        "scenario": "Volume spike (20x volume with price drop)",
        "elapsed_sec": round(time.time() - t0, 3),
        "triggered": sig_vol.triggered,
        "reason": sig_vol.reason,
        "panic_volume_ratio": sig_vol.panic_volume_ratio,
        "passed": bool(sig_vol.triggered and "PANIC_VOLUME_SPIKE" in sig_vol.reason)
    }
    results.append(r3)

    # Case 4.4: IntradayTick with Inf price
    t0 = time.time()
    engine.reset_all()
    tick_inf = IntradayTick(symbol='AAPL', price=np.inf, volume=1000.0)
    sig_tick = engine.evaluate_tick(tick_inf)
    r4 = {
        "scenario": "IntradayTick with Inf price",
        "elapsed_sec": round(time.time() - t0, 3),
        "triggered": sig_tick.triggered,
        "reason": sig_tick.reason,
        "passed": bool(sig_tick.reason == "INVALID_PRICE")
    }
    results.append(r4)

    return results


if __name__ == "__main__":
    t1 = test_1_hrp_weights()
    t2 = test_2_merge_fundamentals()
    t3 = test_3_advanced_statistics()
    t4 = test_4_intraday_stop_loss()

    all_tests = py_native({
        "task_1_hrp_weights": t1,
        "task_2_merge_fundamentals": t2,
        "task_3_advanced_statistics": t3,
        "task_4_intraday_stop_loss": t4
    })

    out_file = r"d:\Finance\code\stock\.agents\teamwork_preview_challenger_m1_1\test_results.json"
    with open(out_file, "w") as f:
        json.dump(all_tests, f, indent=2)

    logger.info(f"Stress test complete. Results written to {out_file}")
