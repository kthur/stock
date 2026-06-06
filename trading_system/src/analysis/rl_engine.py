import numpy as np
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class RLEngine:
    """강화학습(Reinforcement Learning) 기반 트레이딩 에이전트 인터페이스
    현재 시장의 상태(State)를 입력받아 최적의 행동(Action: Buy/Sell/Hold)을 반환합니다.
    (실제 학습은 외부 RL 프레임워크(Stable Baselines3 등)를 통해 오프라인으로 진행되었다고 가정하고,
    여기서는 학습된 모델을 로드하여 추론하는 구조를 시뮬레이션합니다.)
    """
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self._is_loaded = False
        self._load_model()
        
    def _load_model(self):
        """저장된 RL 모델 가중치 로드 (Mock)"""
        if self.model_path:
            logger.info(f"Loading RL model from {self.model_path}")
            self._is_loaded = True
        else:
            logger.warning("No RL model path provided. Running in simulation mode.")
            self._is_loaded = False

    def get_action(self, state_features: Dict[str, float]) -> Dict[str, Any]:
        """주어진 상태(State)에서 최적의 행동(Action) 추론
        
        Args:
            state_features: VIX, 현재 수익률, MA 이격도 등 시장 상태 특징 벡터
            
        Returns:
            Dict: 추천 행동 및 해당 행동의 Confidence(확률/Q-value)
        """
        # 특징 벡터 추출
        features = np.array([
            state_features.get('vix', 20.0),
            state_features.get('rsi', 50.0),
            state_features.get('macd', 0.0),
            state_features.get('trend_strength', 0.0)
        ])
        
        # 모델이 없는 경우 휴리스틱 시뮬레이션 (임시 로직)
        action_probs = self._simulate_policy_network(features)
        
        # 0: HOLD, 1: BUY, 2: SELL
        best_action_idx = np.argmax(action_probs)
        confidence = float(action_probs[best_action_idx])
        
        action_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
        action = action_map[best_action_idx]
        
        return {
            "action": action,
            "confidence": confidence,
            "q_values": action_probs.tolist()
        }
        
    def _simulate_policy_network(self, features: np.ndarray) -> np.ndarray:
        """RL 에이전트의 정책 신경망(Policy Network)을 흉내내는 임시 함수"""
        vix, rsi, macd, trend = features
        
        # 극단적인 공포(VIX 높고 RSI 과매도)일 때 BUY 확률 상승
        if vix > 30 and rsi < 30:
            return np.array([0.1, 0.8, 0.1])
        # 극단적 탐욕(VIX 낮고 RSI 과매수)일 때 SELL 확률 상승
        elif vix < 15 and rsi > 70:
            return np.array([0.1, 0.1, 0.8])
        # 강한 상승장일 때 BUY (추세 추종)
        elif trend > 0.5 and macd > 0:
            return np.array([0.2, 0.7, 0.1])
            
        # 기본적으로 HOLD 확률이 높음
        return np.array([0.6, 0.2, 0.2])
