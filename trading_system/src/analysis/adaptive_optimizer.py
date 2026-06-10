"""Adaptive Parameter Optimizer - Recency-Weighted Bayesian Optimization"""

import json
import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def _make_hashable(obj):
    """list를 tuple로 변환하여 hashable하게 만듦"""
    if isinstance(obj, list):
        return tuple(_make_hashable(v) for v in obj)
    if isinstance(obj, dict):
        return tuple(sorted((k, _make_hashable(v)) for k, v in obj.items()))
    return obj


# ── Phase 2: Full Parameter Grid ──────────────────────────────────────

FULL_PARAM_GRID = {
    # 전략 엔진: 레짐별 매수/매도 임계값
    "regime_thresholds": {
        "strong_bull": {"buy": [0.45, 0.48, 0.50, 0.52], "sell": [0.35, 0.38, 0.40]},
        "weak_bull": {"buy": [0.50, 0.52, 0.55], "sell": [0.40, 0.42, 0.45]},
        "weak_bear": {"buy": [0.58, 0.62, 0.65], "sell": [0.42, 0.45, 0.48]},
        "strong_bear": {"buy": [0.65, 0.70, 0.75], "sell": [0.48, 0.50, 0.52]},
    },
    # 시그널 가중치
    "signal_weights": {
        "sentiment": [0.15, 0.20, 0.25, 0.30],
        "technical": [0.25, 0.30, 0.35, 0.40],
        "ml": [0.20, 0.25, 0.30],
        "llm": [0.05, 0.10, 0.15],
        "macro": [0.05, 0.08, 0.12, 0.15],
        "rl": [0.05, 0.10],
    },
    # ATR 멀티플라이어 (레짐별)
    "atr_multipliers": {
        "strong_bull": {"stop": [2.5, 3.0, 3.5], "target": [4.0, 5.0, 6.0]},
        "weak_bull": {"stop": [2.0, 2.5, 3.0], "target": [3.0, 4.0, 5.0]},
        "weak_bear": {"stop": [1.2, 1.5, 2.0], "target": [2.0, 2.5, 3.0]},
        "strong_bear": {"stop": [0.8, 1.0, 1.3], "target": [1.5, 2.0, 2.5]},
    },
    # 트레이딩 시스템 파라미터
    "trail_pct": [0.03, 0.04, 0.05, 0.06, 0.08, 0.10],
    "max_holding_days": [15, 20, 25, 30, 40],
    "max_position_size_pct": [0.15, 0.20, 0.25, 0.30, 0.35],
    # 익절 티어
    "take_profit_tiers": [
        [1.5, 3.0, 5.0],
        [2.0, 4.0, 6.0],
        [2.5, 5.0, 8.0],
    ],
}

# 레짐 전체 목록
REGIME_NAMES = ["strong_bull", "weak_bull", "weak_bear", "strong_bear"]

# 기본 파라미터 (fallback)
DEFAULT_PARAMS: Dict[str, Any] = {
    "regime_thresholds": {
        "strong_bull": {
            "buy": 0.48,
            "sell": 0.38,
            "min_buy_votes": 1,
            "position_pct": 1.0,
            "trail_pct": 0.08,
            "cash_target": 0.10,
        },
        "weak_bull": {
            "buy": 0.52,
            "sell": 0.42,
            "min_buy_votes": 1,
            "position_pct": 0.8,
            "trail_pct": 0.06,
            "cash_target": 0.20,
        },
        "weak_bear": {
            "buy": 0.62,
            "sell": 0.45,
            "min_buy_votes": 2,
            "position_pct": 0.5,
            "trail_pct": 0.04,
            "cash_target": 0.40,
        },
        "strong_bear": {
            "buy": 0.70,
            "sell": 0.50,
            "min_buy_votes": 3,
            "position_pct": 0.25,
            "trail_pct": 0.03,
            "cash_target": 0.70,
        },
    },
    "signal_weights": {
        "sentiment": 0.20,
        "technical": 0.30,
        "ml": 0.30,
        "rl": 0.10,
        "darkpool": 0.0,
        "llm": 0.10,
        "global_market": 0.0,
        "cash_ratio": 0.08,
        "macro": 0.08,
    },
    "atr_multipliers": {
        "strong_bull": {"stop": 3.0, "target": 5.0, "trail": 0.08},
        "weak_bull": {"stop": 2.5, "target": 4.0, "trail": 0.06},
        "weak_bear": {"stop": 1.5, "target": 2.5, "trail": 0.04},
        "strong_bear": {"stop": 1.0, "target": 2.0, "trail": 0.03},
    },
    "trail_pct": 0.04,
    "max_holding_days": 30,
    "max_position_size_pct": 0.20,
    "take_profit_tiers": [1.5, 3.0, 5.0],
}

# ── Phase 3: Simple TPE Sampler ───────────────────────────────────────


class TPESampler:
    """Tree-structured Parzen Estimator: 상위 25% vs 하위 75% 분포 비교"""

    def __init__(self, seed: int = 42, n_startup_trials: int = 10, n_ei_candidates: int = 100):
        self.seed = seed
        self.n_startup_trials = n_startup_trials
        self.n_ei_candidates = n_ei_candidates
        self.rng = random.Random(seed)
        self.trials: List[Dict] = []

    def suggest(self, trial_num: int) -> Dict:
        """파라미터 제안: 초기 n_startup_trials는 LHS, 이후 TPE"""
        if trial_num < self.n_startup_trials:
            return self._lhs_sample()
        return self._tpe_sample()

    def _lhs_sample(self) -> Dict:
        """Latin Hypercube Sampling: 균일 탐색"""
        params = {}
        param_ranges = self._flatten_grid()

        for name, values in param_ranges.items():
            if isinstance(values, list) and values:
                idx = self.rng.randint(0, len(values) - 1)
                params[name] = values[idx]
            else:
                params[name] = values
        return params

    def _tpe_sample(self) -> Dict:
        """TPE 기반 집중 탐색: 상위 25% 분포에서 제안"""
        param_ranges = self._flatten_grid()

        if len(self.trials) < 5:
            return self._lhs_sample()

        scores = np.array([t["score"] for t in self.trials])
        threshold = np.percentile(scores, 25)
        good_mask = scores >= threshold

        good_trials = [self.trials[i] for i in range(len(self.trials)) if good_mask[i]]
        bad_trials = [self.trials[i] for i in range(len(self.trials)) if not good_mask[i]]

        if not good_trials:
            return self._lhs_sample()

        params = {}
        for name, values in param_ranges.items():
            if not isinstance(values, list) or len(values) <= 1:
                params[name] = values
                continue

            good_values = [_make_hashable(t["params"].get(name)) for t in good_trials]
            bad_values = [_make_hashable(t["params"].get(name)) for t in bad_trials]
            hashable_options = [_make_hashable(v) for v in values]

            good_counts = {v: good_values.count(v) for v in hashable_options if v in good_values}
            bad_counts = {v: bad_values.count(v) for v in hashable_options if v in bad_values}

            best_value = values[0]
            best_ratio = -float("inf")

            for original_v, hashable_v in zip(values, hashable_options):
                p_good = (good_counts.get(hashable_v, 0) + 1) / (len(good_values) + len(hashable_options))
                p_bad = (bad_counts.get(hashable_v, 0) + 1) / (len(bad_values) + len(hashable_options))
                ratio = p_good / max(p_bad, 0.01)

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_value = original_v

            params[name] = best_value

        return params

    def _flatten_grid(self) -> Dict:
        """FULL_PARAM_GRID을 1차원 dict로 평탄화 (leaf 값이 list가 될 때까지 재귀)"""
        flat = {}

        def _recurse(prefix, obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    _recurse(f"{prefix}.{key}" if prefix else key, value)
            elif isinstance(obj, list) and obj and not isinstance(obj[0], list):
                flat[prefix] = obj
            elif isinstance(obj, list):
                flat[prefix] = obj

        _recurse("", FULL_PARAM_GRID)
        return flat

    def record(self, params: Dict, score: float) -> None:
        """시도 결과 기록"""
        self.trials.append({"params": params, "score": score})


# ── Adaptive Parameter Optimizer ──────────────────────────────────────


@dataclass
class OptimizationResult:
    """최적화 결과"""

    best_params: Dict
    best_score: float
    param_importance: Dict
    timestamp: datetime
    n_trials: int
    n_evaluated: int
    symbols_used: List[str]
    training_window_days: int
    decay_rate: float
    score_ci_lower: float
    score_ci_upper: float


class AdaptiveParameterOptimizer:
    """Recency-Weighted Bayesian 파라미터 최적화"""

    def __init__(self, backtest_engine, strategy_engine, trading_system=None):
        self.backtest = backtest_engine
        self.strategy = strategy_engine
        self.trading_system = trading_system
        self.default_params = DEFAULT_PARAMS.copy()
        self._history: List[Dict] = []

    def optimize(
        self, symbols: List[str], lookback_days: int = 90, n_trials: int = 50, decay_rate: float = 0.02, seed: int = 42
    ) -> OptimizationResult:
        """Bayesian 최적화 수행"""
        logger.info(
            f"Starting adaptive optimization: {len(symbols)} symbols, {lookback_days}d lookback, {n_trials} trials"
        )

        sampler = TPESampler(seed=seed)
        best_score = -float("inf")
        best_params: Dict[Any, Any] = {}
        all_scores = []

        for trial in range(n_trials):
            params = sampler.suggest(trial)
            trial_score = self._evaluate_params(symbols, params, lookback_days, decay_rate)

            sampler.record(params, trial_score)
            all_scores.append(trial_score)

            if trial_score > best_score:
                best_score = trial_score
                best_params = params
                logger.info(f"Trial {trial + 1}/{n_trials}: new best score = {best_score:.4f}")

            if trial % 10 == 0:
                logger.info(f"Trial {trial + 1}/{n_trials}: current best = {best_score:.4f}")

            # 조기 종료: 15회 연속 개선 없음
            if trial >= 20 and trial % 5 == 0:
                recent = all_scores[-15:]
                if max(recent) - min(recent) < 0.01:
                    logger.info(f"Early stopping at trial {trial + 1}: no improvement in 15 trials")
                    break

        scores = np.array(all_scores)
        ci_lower = float(np.percentile(scores, 5)) if len(scores) >= 5 else best_score
        ci_upper = float(np.percentile(scores, 95)) if len(scores) >= 5 else best_score

        param_importance = self._compute_importance(symbols, lookback_days, decay_rate)

        result = OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            param_importance=param_importance,
            timestamp=datetime.now(),
            n_trials=len(all_scores),
            n_evaluated=len(all_scores),
            symbols_used=symbols,
            training_window_days=lookback_days,
            decay_rate=decay_rate,
            score_ci_lower=ci_lower,
            score_ci_upper=ci_upper,
        )

        self._history.append(
            {
                "timestamp": result.timestamp.isoformat(),
                "best_score": best_score,
                "best_params": best_params,
            }
        )

        return result

    def _evaluate_params(self, symbols: List[str], params: Dict, lookback_days: int, decay_rate: float) -> float:
        """파라미터 조합 평가: recency-weighted multi-symbol score"""
        total_score = 0.0
        evaluated = 0

        for symbol in symbols:
            try:
                bars = self._fetch_bars(symbol, lookback_days)
                if bars and len(bars) >= 50:
                    score = self._single_symbol_score(symbol, bars, params, decay_rate)
                    total_score += score
                    evaluated += 1
            except Exception as e:
                logger.debug(f"Failed to evaluate {symbol}: {e}")

        if evaluated == 0:
            return 0.0
        return total_score / evaluated

    def _single_symbol_score(self, symbol: str, bars: list, params: Dict, decay_rate: float) -> float:
        """단일 종목 Recency-Weighted Score 계산"""
        strategy_func = self._build_strategy_from_params(params)
        result = self.backtest.run_backtest(symbol, bars, strategy_func)
        return float(self.backtest.recency_weighted_score(result, decay_rate))

    def _build_strategy_from_params(self, params: Dict) -> Callable:
        """파라미터 → 전략 함수 변환"""

        regime_thresholds = self._get_param(params, "regime_thresholds", DEFAULT_PARAMS["regime_thresholds"])
        atr_mult = self._get_param(params, "atr_multipliers", DEFAULT_PARAMS["atr_multipliers"])
        trail_pct = self._get_param(params, "trail_pct", DEFAULT_PARAMS["trail_pct"])
        max_hold = self._get_param(params, "max_holding_days", DEFAULT_PARAMS["max_holding_days"])

        def strategy(bars):
            engine = self._create_inline_engine(bars, regime_thresholds, atr_mult, trail_pct, max_hold)
            return engine

        return strategy

    def _create_inline_engine(self, bars, regime_thresholds, atr_mult, trail_pct, max_hold):
        """간이 백테스트 엔진: 복합 전략 + 무작위 레짐 탐지"""
        closes = [b.close for b in bars]
        if len(closes) < 50:
            return "HOLD"

        ema50 = self._ema(closes, 50)[-1]
        ema200 = self._ema(closes, 200)[-1] if len(closes) >= 200 else closes[0]
        roc_20 = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0

        adx = self._calc_adx(bars)
        strong_trend = adx > 25

        if ema50 > ema200 and (strong_trend or roc_20 > 0.03):
            regime = "strong_bull"
        elif ema50 > ema200:
            regime = "weak_bull"
        elif strong_trend or roc_20 < -0.03:
            regime = "strong_bear"
        else:
            regime = "weak_bear"

        threshold = regime_thresholds.get(regime, regime_thresholds["weak_bull"])
        buy_at = threshold["buy"]
        sell_at = threshold["sell"]

        # RSI + MACD 기반 듀얼 신호
        rsi = self._rsi(closes, 14)
        macd_hist = self._macd_histogram(closes)
        bb_pos = self._bollinger_position(closes)

        score = 0.5
        if rsi < 45:
            score += 0.15
        elif rsi > 60:
            score -= 0.10
        if macd_hist > 0:
            score += 0.15
        else:
            score -= 0.10
        if bb_pos > 0:
            score += 0.10
        else:
            score -= 0.05
        if roc_20 > 0.02:
            score += 0.10
        elif roc_20 < -0.02:
            score -= 0.10

        if score >= buy_at:
            return "BUY"
        elif score <= sell_at:
            return "SELL"
        return "HOLD"

    @staticmethod
    def _ema(prices, period):
        if len(prices) < period:
            return [prices[-1]] * len(prices)
        result = [prices[0]]
        m = 2 / (period + 1)
        for p in prices[1:]:
            result.append(p * m + result[-1] * (1 - m))
        return result

    @staticmethod
    def _rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(len(prices) - period, len(prices)):
            diff = prices[i] - prices[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - 100.0 / (1.0 + rs)

    @staticmethod
    def _macd_histogram(prices, fast=12, slow=26, signal=9):
        if len(prices) < slow + signal:
            return 0.0
        ema_fast = sum(prices[-fast:]) / fast
        ema_slow = sum(prices[-slow:]) / slow
        macd = ema_fast - ema_slow
        ema_signal = macd  # simplified
        return macd - ema_signal

    @staticmethod
    def _bollinger_position(prices, period=20):
        if len(prices) < period:
            return 0.0
        recent = prices[-period:]
        mean = sum(recent) / period
        std = (sum((x - mean) ** 2 for x in recent) / period) ** 0.5
        upper = mean + 2 * std
        lower = mean - 2 * std
        current = prices[-1]
        if current >= upper:
            return 1.0
        elif current <= lower:
            return -1.0
        return (current - lower) / (upper - lower) * 2 - 1 if std > 0 else 0.0

    @staticmethod
    def _calc_adx(bars, period=14):
        if len(bars) < period + 1:
            return 20.0
        trs, up_moves, down_moves = [], [], []
        for i in range(1, period + 1):
            tr = max(
                bars[i].high - bars[i].low, abs(bars[i].high - bars[i - 1].close), abs(bars[i].low - bars[i - 1].close)
            )
            trs.append(tr)
            up_moves.append(bars[i].high - bars[i - 1].high)
            down_moves.append(bars[i - 1].low - bars[i].low)
        atr = sum(trs) / period if trs else 0
        avg_up = sum(max(m, 0) for m in up_moves) / period
        avg_down = sum(max(m, 0) for m in down_moves) / period
        if atr <= 0:
            return 20.0
        plus_di = avg_up / atr * 100
        minus_di = avg_down / atr * 100
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
        return dx

    def _fetch_bars(self, symbol: str, lookback_days: int) -> list:
        """과거 가격 데이터 조회"""
        from ..data_layer import MarketDataHandler

        handler = MarketDataHandler()
        period_map = {30: "1mo", 60: "2mo", 90: "3mo", 180: "6mo", 365: "1y"}
        period = period_map.get(lookback_days, "3mo")
        return handler.fetch_historical_data(symbol, period=period)

    def _get_param(self, params: Dict, key: str, default: Any = None) -> Any:
        """중첩된 params에서 값 조회"""
        if not params:
            return default
        if key in params:
            return params[key]
        for category, content in FULL_PARAM_GRID.items():
            if isinstance(content, dict) and key.startswith(category + "."):
                sub_key = key[len(category) + 1 :]
                if category in params and isinstance(params[category], dict):
                    return params[category].get(sub_key, default)
        return default

    def _compute_importance(self, symbols: List[str], lookback_days: int, decay_rate: float) -> Dict:
        """파라미터 중요도 추정: 각 파라미터를 기본값으로 되돌렸을 때 점수 변화"""
        baseline = self._evaluate_params(symbols, DEFAULT_PARAMS, lookback_days, decay_rate)
        importance = {}

        if baseline <= 0:
            return {"note": "baseline evaluation failed"}

        for key in ["trail_pct", "max_holding_days", "max_position_size_pct"]:
            test_params = DEFAULT_PARAMS.copy()
            choices = FULL_PARAM_GRID.get(key, [test_params[key]])
            if isinstance(choices, list):
                test_params[key] = random.choice(choices)
            score = self._evaluate_params(symbols, test_params, lookback_days, decay_rate)
            importance[key] = max(0, baseline - score)

        return importance

    def save_params(self, result: OptimizationResult, filepath: Optional[str] = None) -> str:
        """최적화 결과를 JSON으로 저장"""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "adaptive_params.json"
            )
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        full_params = DEFAULT_PARAMS.copy()
        if result.best_params:
            for key, value in result.best_params.items():
                parts = key.split(".")
                target: Any = full_params
                for p in parts[:-1]:
                    if p.isdigit():
                        p = int(p)
                    if isinstance(target, dict):
                        if p not in target:
                            target[p] = {}
                        target = target[p]
                    elif isinstance(target, list) and isinstance(p, int):
                        while len(target) <= p:
                            target.append({})
                        target = target[p]
                    else:
                        break
                if isinstance(target, dict):
                    target[parts[-1]] = value

        # 레짐 임계값을 REGIME_THRESHOLDS 포맷으로 변환
        regime_thresholds = {}
        for regime in REGIME_NAMES:
            regime_thresholds[regime] = {
                "buy": full_params.get("regime_thresholds", {}).get(regime, {}).get("buy", 0.52),
                "sell": full_params.get("regime_thresholds", {}).get(regime, {}).get("sell", 0.42),
                "min_buy_votes": DEFAULT_PARAMS["regime_thresholds"][regime]["min_buy_votes"],
                "position_pct": DEFAULT_PARAMS["regime_thresholds"][regime]["position_pct"],
                "trail_pct": DEFAULT_PARAMS["regime_thresholds"][regime]["trail_pct"],
                "cash_target": DEFAULT_PARAMS["regime_thresholds"][regime]["cash_target"],
            }

        adaptive_params = {
            "version": 2,
            "optimized_at": result.timestamp.isoformat(),
            "training": {
                "symbols": result.symbols_used,
                "window_days": result.training_window_days,
                "decay_rate": result.decay_rate,
            },
            "metrics": {
                "score": round(result.best_score, 4),
                "score_ci_lower": round(result.score_ci_lower, 4),
                "score_ci_upper": round(result.score_ci_upper, 4),
                "n_trials": result.n_trials,
            },
            "params": {
                "regime_thresholds": regime_thresholds,
                "atr_multipliers": full_params.get("atr_multipliers", DEFAULT_PARAMS["atr_multipliers"]),
                "signal_weights": full_params.get("signal_weights", DEFAULT_PARAMS["signal_weights"]),
                "take_profit_tiers": full_params.get("take_profit_tiers", [1.5, 3.0, 5.0]),
                "trail_pct": full_params.get("trail_pct", 0.04),
                "max_position_size_pct": full_params.get("max_position_size_pct", 0.20),
                "max_holding_days": full_params.get("max_holding_days", 30),
            },
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(adaptive_params, f, indent=2, ensure_ascii=False)

        logger.info(f"Adaptive params saved to {filepath}")
        return filepath

    @staticmethod
    def load_params(filepath: Optional[str] = None) -> Dict:
        """저장된 파라미터 로드 (없으면 기본값 반환)"""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "adaptive_params.json"
            )

        if not os.path.exists(filepath):
            logger.info(f"No adaptive params found at {filepath}, using defaults")
            return DEFAULT_PARAMS.copy()

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            res = data.get("params", DEFAULT_PARAMS.copy())
            if isinstance(res, dict):
                return res
            return DEFAULT_PARAMS.copy()
        except Exception as e:
            logger.warning(f"Failed to load adaptive params: {e}, using defaults")
            return DEFAULT_PARAMS.copy()


# ── Phase 6: Optimization Scheduler ──────────────────────────────────


class OptimizationScheduler:
    """주기적/이벤트 기반 파라미터 재최적화 스케줄러"""

    SCHEDULE_INTERVAL_DAYS = 7
    TRIGGER_CONDITIONS = {
        "regime_change": True,
        "sharpe_decline": 0.20,
        "drawdown_exceed": 0.10,
        "volatility_spike": 1.5,
    }

    def __init__(self, optimizer: AdaptiveParameterOptimizer, trading_system=None):
        self.optimizer = optimizer
        self.trading_system = trading_system
        self.last_optimized = datetime.now() - timedelta(days=90)
        self._current_regime: Optional[str] = None
        self._prev_sharpe: float = 0.5
        self._prev_drawdown: float = 0.0
        self._current_optimization: Optional[OptimizationResult] = None

    def should_reoptimize(self, state: Dict) -> bool:
        """재최적화 필요 여부 판단"""
        days_since = (datetime.now() - self.last_optimized).days
        if days_since >= self.SCHEDULE_INTERVAL_DAYS:
            logger.info(f"Scheduler: {days_since}d since last opt, triggering reoptimization")
            return True

        regime = state.get("regime")
        if regime and self._current_regime and regime != self._current_regime:
            logger.info(f"Scheduler: regime changed {self._current_regime} → {regime}")
            return True

        sharpe = state.get("sharpe_ratio", 0.5)
        if self._prev_sharpe > 0 and (self._prev_sharpe - sharpe) / self._prev_sharpe > 0.2:
            logger.info(f"Scheduler: sharpe declined {self._prev_sharpe:.2f} → {sharpe:.2f}")
            return True

        dd = state.get("drawdown", 0.0)
        if dd > 0.10:
            logger.info(f"Scheduler: drawdown {dd:.2%} exceeds 10%")
            return True

        vix = state.get("vix", 20.0)
        prev_vix = state.get("prev_vix", 20.0)
        if prev_vix > 0 and vix / prev_vix > 1.5:
            logger.info(f"Scheduler: VIX spike {prev_vix:.0f} → {vix:.0f}")
            return True

        return False

    def run_optimization(
        self, symbols: List[str], lookback_days: int = 90, n_trials: int = 50, decay_rate: float = 0.02
    ) -> OptimizationResult:
        """최적화 실행 및 결과 저장"""
        self._current_optimization = self.optimizer.optimize(
            symbols=symbols,
            lookback_days=lookback_days,
            n_trials=n_trials,
            decay_rate=decay_rate,
        )
        self.optimizer.save_params(self._current_optimization)
        self.last_optimized = datetime.now()

        logger.info(
            f"Optimization complete: score={self._current_optimization.best_score:.4f}, "
            f"CI=[{self._current_optimization.score_ci_lower:.4f}, "
            f"{self._current_optimization.score_ci_upper:.4f}]"
        )
        return self._current_optimization

    def update_state(self, regime: Optional[str] = None, sharpe: Optional[float] = None, drawdown: Optional[float] = None, vix: Optional[float] = None) -> None:
        """현재 상태 업데이트"""
        if regime:
            self._current_regime = regime
        if sharpe is not None:
            self._prev_sharpe = sharpe
        if drawdown is not None:
            self._prev_drawdown = drawdown

    def get_status(self) -> Dict:
        """스케줄러 상태 반환"""
        return {
            "last_optimized": self.last_optimized.isoformat(),
            "days_since": (datetime.now() - self.last_optimized).days,
            "current_regime": self._current_regime,
            "has_result": self._current_optimization is not None,
        }
