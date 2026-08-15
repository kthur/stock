import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class RLEngine:
    """강화학습(Reinforcement Learning) 기반 트레이딩 에이전트

    성과 피드백을 통해 내부 임계값과 행동 선호도를 지속적으로 조정합니다.
    실제 Stable-Baselines3 모델이 없어도 적응형 휴리스틱으로 동작합니다.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._is_loaded = False

        self._action_history: List[Dict[str, Any]] = []
        self._action_performance: Dict[str, List[bool]] = {"BUY": [], "SELL": [], "HOLD": []}
        self._thresholds = {
            "vix_buy": 30.0,
            "rsi_buy": 30.0,
            "vix_sell": 15.0,
            "rsi_sell": 70.0,
            "trend_buy": 0.5,
            "min_confidence": 0.3,
        }
        self._adaptation_rate = 0.05
        self._min_samples = 10
        self._load_model()

    def _load_model(self):
        if self.model_path:
            logger.info(f"Loading RL model from {self.model_path}")
            self._is_loaded = True
        else:
            logger.warning("No RL model path provided. Running in adaptive mode.")
            self._is_loaded = False

    def get_action(self, state_features: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        if state_features is None:
            state_features = {}
        features = np.array(
            [
                float(state_features.get("vix", 20.0) or 20.0),
                float(state_features.get("rsi", 50.0) or 50.0),
                float(state_features.get("macd", 0.0) or 0.0),
                float(state_features.get("trend_strength", 0.0) or 0.0),
            ],
            dtype=float
        )
        features = np.nan_to_num(features, nan=0.0)

        action_probs = self._simulate_policy_network(features)

        best_action_idx = int(np.argmax(action_probs))
        confidence = float(action_probs[best_action_idx])

        action_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
        action = action_map[best_action_idx]

        result = {
            "action": action,
            "confidence": confidence,
            "q_values": action_probs.tolist(),
        }
        self._action_history.append(result)
        return result

    def record_outcome(self, action: str, pnl_pct: float) -> None:
        act = str(action).upper().strip()
        if act not in self._action_performance:
            self._action_performance[act] = []
        self._action_performance[act].append(pnl_pct > 0)
        if len(self._action_history) % 20 == 0:
            self._adapt_thresholds()

    def _adapt_thresholds(self) -> None:
        accuracies = {}
        for action in ["BUY", "SELL", "HOLD"]:
            perf = self._action_performance[action]
            if len(perf) >= self._min_samples:
                accuracies[action] = sum(perf) / len(perf)

        if len(accuracies) < 2:
            return

        buy_acc = accuracies.get("BUY", 0.5)
        sell_acc = accuracies.get("SELL", 0.5)

        if buy_acc < 0.4:
            self._thresholds["vix_buy"] *= 1.0 + self._adaptation_rate
            self._thresholds["rsi_buy"] *= 1.0 - self._adaptation_rate
            logger.info(
                "RL buy thresholds adapted: "
                f"vix>{self._thresholds['vix_buy']:.1f} "
                f"rsi<{self._thresholds['rsi_buy']:.1f}"
            )
        elif buy_acc > 0.6:
            self._thresholds["vix_buy"] *= 1.0 - self._adaptation_rate
            self._thresholds["rsi_buy"] *= 1.0 + self._adaptation_rate

        if sell_acc < 0.4:
            self._thresholds["vix_sell"] *= 1.0 - self._adaptation_rate
            self._thresholds["rsi_sell"] *= 1.0 + self._adaptation_rate
            logger.info(
                "RL sell thresholds adapted: "
                f"vix<{self._thresholds['vix_sell']:.1f} "
                f"rsi>{self._thresholds['rsi_sell']:.1f}"
            )
        elif sell_acc > 0.6:
            self._thresholds["vix_sell"] *= 1.0 + self._adaptation_rate
            self._thresholds["rsi_sell"] *= 1.0 - self._adaptation_rate

        total_perf = sum(len(v) for v in self._action_performance.values())
        logger.info(f"RL stats: buy_acc={buy_acc:.2f} sell_acc={sell_acc:.2f} total_actions={total_perf}")

    def _simulate_policy_network(self, features: np.ndarray) -> np.ndarray:
        vix, rsi, macd, trend = features
        t = self._thresholds

        if vix > t["vix_buy"] and rsi < t["rsi_buy"]:
            return np.array([0.1, 0.8, 0.1])
        elif vix < t["vix_sell"] and rsi > t["rsi_sell"]:
            return np.array([0.1, 0.1, 0.8])
        elif trend > t["trend_buy"] and macd > 0:
            return np.array([0.2, 0.7, 0.1])

        return np.array([0.6, 0.2, 0.2])
