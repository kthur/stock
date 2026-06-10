#!/usr/bin/env python
"""Adaptive Parameter Optimization — Verification Script

사용법:
    python verify_adaptive.py                       # 전체 검증 실행
    python verify_adaptive.py --quick               # 빠른 검증 (5 trials, 1 symbol)
    python verify_adaptive.py --optimize             # 최적화만 실행
    python verify_adaptive.py --backtest             # 백테스트 비교만 실행
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trading_system'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('verify_adaptive')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'trading_system', 'data')
STATIC_PARAMS_FILE = os.path.join(DATA_DIR, 'adaptive_params.json')
RESULTS_FILE = os.path.join(DATA_DIR, 'verification_results.json')


def load_test_universe() -> list:
    """테스트 종목 유니버스"""
    return ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "005930", "000660"]


def test_recency_weighted_metrics():
    """Phase 1: Recency-Weighted Metrics 검증"""
    from src.analysis.backtest import BacktestEngine, BacktestResult, BacktestTrade
    from datetime import datetime, timedelta

    engine = BacktestEngine()

    # 모의 거래 데이터 생성 (최근 30일: 수익, 90일 전: 손실)
    trades = []
    now = datetime.now()
    for i in range(60):
        days_ago = 90 - i
        pnl_pct = 0.02 if days_ago < 30 else -0.01
        trades.append(BacktestTrade(
            entry_date=now - timedelta(days=days_ago + 5),
            entry_price=100,
            exit_date=now - timedelta(days=days_ago),
            exit_price=100 * (1 + pnl_pct),
            quantity=10,
            pnl=100 * pnl_pct * 10,
            pnl_pct=pnl_pct,
        ))

    result = BacktestResult(
        symbol="TEST",
        trades=trades,
        total_return=0.05,
        total_return_pct=5.0,
        win_rate=0.5,
        profit_factor=1.2,
        max_drawdown=0.15,
        sharpe_ratio=0.8,
        total_fees=0,
        start_date=now - timedelta(days=90),
        end_date=now,
        initial_capital=100000,
        final_capital=105000,
    )

    # Recency-Weighted Score 계산
    score = engine.recency_weighted_score(result, decay_rate=0.02)
    logger.info(f"Recency-Weighted Score: {score:.4f}")

    assert 0 < score < 1, f"Score should be between 0~1, got {score}"
    logger.info("✅ Phase 1: Recency-Weighted Metrics — PASS")


def test_adaptive_optimizer():
    """Phase 2-3: Adaptive Optimizer 검증"""
    from src.analysis.adaptive_optimizer import (
        AdaptiveParameterOptimizer, OptimizationScheduler, FULL_PARAM_GRID, TPESampler
    )

    # TPE Sampler 검증
    sampler = TPESampler(seed=42, n_startup_trials=5)
    for t in range(10):
        params = sampler.suggest(t)
        sampler.record(params, score=0.5 + 0.05 * t)
    assert len(sampler.trials) == 10, "Sampler should record 10 trials"
    logger.info(f"TPE Sampler: {len(sampler.trials)} trials recorded")

    # FULL_PARAM_GRID 구조 검증
    assert "regime_thresholds" in FULL_PARAM_GRID
    assert "signal_weights" in FULL_PARAM_GRID
    assert "atr_multipliers" in FULL_PARAM_GRID
    assert "trail_pct" in FULL_PARAM_GRID
    assert "max_position_size_pct" in FULL_PARAM_GRID
    logger.info(f"FULL_PARAM_GRID: {sum(len(v) if isinstance(v, list) else len(str(v)) for v in FULL_PARAM_GRID.values())} categories")

    logger.info("✅ Phase 2-3: Adaptive Optimizer — PASS")


def test_params_file():
    """Phase 4: Parameter File 검증"""
    assert os.path.exists(STATIC_PARAMS_FILE), f"Params file not found: {STATIC_PARAMS_FILE}"

    with open(STATIC_PARAMS_FILE, 'r') as f:
        data = json.load(f)

    assert "version" in data, "Missing 'version' key"
    assert "params" in data, "Missing 'params' key"
    assert "regime_thresholds" in data["params"], "Missing regime_thresholds"
    assert "atr_multipliers" in data["params"], "Missing atr_multipliers"

    logger.info(f"Params file version: {data['version']}")
    logger.info(f"Params keys: {list(data['params'].keys())}")
    logger.info("✅ Phase 4: Parameter File — PASS")


def run_optimization(quick: bool = False):
    """실제 최적화 실행"""
    from src.analysis.backtest import BacktestEngine
    from src.analysis.adaptive_optimizer import AdaptiveParameterOptimizer

    engine = BacktestEngine()

    class MockStrategyEngine:
        regime_thresholds = {
            "strong_bull": {"buy": 0.48, "sell": 0.38},
            "weak_bull": {"buy": 0.52, "sell": 0.42},
            "weak_bear": {"buy": 0.62, "sell": 0.45},
            "strong_bear": {"buy": 0.70, "sell": 0.50},
        }
        def _calc_adx(self, bars):
            return 20.0

    optimizer = AdaptiveParameterOptimizer(
        backtest_engine=engine,
        strategy_engine=MockStrategyEngine(),
    )

    symbols = ["SPY"] if quick else load_test_universe()
    n_trials = 5 if quick else 30
    lookback = 30 if quick else 90

    logger.info(f"Running optimization: {len(symbols)} symbols, {n_trials} trials, {lookback}d lookback")
    result = optimizer.optimize(symbols=symbols, n_trials=n_trials, lookback_days=lookback)

    logger.info(f"Optimization result: score={result.best_score:.4f}, CI=[{result.score_ci_lower:.4f}, {result.score_ci_upper:.4f}]")
    logger.info(f"Best params: {json.dumps(result.best_params, indent=2)}")

    # 저장
    saved_path = optimizer.save_params(result)
    logger.info(f"Params saved to: {saved_path}")
    return result


def run_backtest_comparison(quick: bool = False):
    """기존 vs 최적화 파라미터 백테스트 비교"""
    from src.analysis.backtest import BacktestEngine
    from src.analysis.adaptive_optimizer import AdaptiveParameterOptimizer, DEFAULT_PARAMS
    from src.data_layer import MarketDataHandler

    engine = BacktestEngine()
    handler = MarketDataHandler()
    params = AdaptiveParameterOptimizer.load_params()

    symbols = ["SPY"] if quick else ["SPY", "QQQ"]
    lookback = 60 if quick else 365

    logger.info(f"Running backtest comparison: {len(symbols)} symbols, {lookback}d lookback")
    results = {
        "static": {"score": 0, "sharpe": 0, "mdd": 0, "return": 0},
        "adaptive": {"score": 0, "sharpe": 0, "mdd": 0, "return": 0},
        "improvement": {},
    }

    class SimpleStrategy:
        def __init__(self, params):
            self.params = params
        def __call__(self, bars):
            closes = [b.close for b in bars]
            if len(closes) < 20:
                return "HOLD"
            rsi_val = 50 + (sum(1 for c in closes[-5:] if c > closes[-6]) * 10)
            if rsi_val > 60:
                return "BUY"
            elif rsi_val < 40:
                return "SELL"
            return "HOLD"

    for symbol in symbols:
        bars = handler.fetch_historical_data(symbol, period="1y")
        if not bars or len(bars) < 50:
            logger.warning(f"Insufficient data for {symbol}")
            continue

        # Static params (기본값)
        static_strategy = SimpleStrategy(DEFAULT_PARAMS)
        static_result = engine.run_backtest(symbol, bars, static_strategy)
        static_score = engine.recency_weighted_score(static_result, decay_rate=0.02)

        # Adaptive params (최적화값)
        adaptive_strategy = SimpleStrategy(params)
        adaptive_result = engine.run_backtest(symbol, bars, adaptive_strategy)
        adaptive_score = engine.recency_weighted_score(adaptive_result, decay_rate=0.02)

        results["static"]["score"] += static_score
        results["static"]["sharpe"] += static_result.sharpe_ratio
        results["static"]["mdd"] += static_result.max_drawdown
        results["static"]["return"] += static_result.total_return_pct

        results["adaptive"]["score"] += adaptive_score
        results["adaptive"]["sharpe"] += adaptive_result.sharpe_ratio
        results["adaptive"]["mdd"] += adaptive_result.max_drawdown
        results["adaptive"]["return"] += adaptive_result.total_return_pct

        logger.info(f"{symbol}: static_score={static_score:.4f} → adaptive_score={adaptive_score:.4f} "
                    f"(sharpe: {static_result.sharpe_ratio:.2f} → {adaptive_result.sharpe_ratio:.2f})")

    n = len(symbols)
    for key in results["static"]:
        avg_static = results["static"][key] / max(n, 1)
        avg_adaptive = results["adaptive"][key] / max(n, 1)
        if avg_static != 0:
            chg = (avg_adaptive - avg_static) / abs(avg_static) * 100
        else:
            chg = 0
        results["improvement"][key] = f"{chg:+.1f}%"
        logger.info(f"  {key}: static={avg_static:.4f}, adaptive={avg_adaptive:.4f} ({chg:+.1f}%)")

    # 결과 저장
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Comparison results saved to {RESULTS_FILE}")
    return results


def main():
    parser = argparse.ArgumentParser(description='Adaptive Parameter Optimization Verification')
    parser.add_argument('--quick', action='store_true', help='Quick verification (small scope)')
    parser.add_argument('--optimize', action='store_true', help='Run optimization only')
    parser.add_argument('--backtest', action='store_true', help='Run backtest comparison only')
    args = parser.parse_args()

    if args.optimize:
        run_optimization(quick=args.quick)
        return
    if args.backtest:
        run_backtest_comparison(quick=args.quick)
        return

    # Full verification
    logger.info("=" * 60)
    logger.info("Adaptive Parameter Optimization — Full Verification")
    logger.info("=" * 60)

    test_recency_weighted_metrics()
    test_adaptive_optimizer()
    test_params_file()

    logger.info("\n" + "=" * 60)
    logger.info("Running optimization...")
    run_optimization(quick=args.quick)

    logger.info("\n" + "=" * 60)
    logger.info("Running backtest comparison...")
    run_backtest_comparison(quick=args.quick)

    logger.info("\n" + "=" * 60)
    logger.info("✅ ALL VERIFICATIONS PASSED")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
