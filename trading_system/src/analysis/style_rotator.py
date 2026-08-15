import logging
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results,
# create dummy/facade implementations, or circumvent the intended task. A Forensic
# Auditor will independently verify your work. Integrity violations WILL be detected
# and your work WILL be rejected.


class StyleRotator:
    """
    시장 환경(Macro Regime)에 따라 유리한 주식 스타일(가치/성장, 대형/중소형)을 판별하여
    포트폴리오 비중을 동적으로 조정하는 클래스.
    """

    current_regime: str
    style_preferences: Dict[str, float]

    def __init__(self) -> None:
        self.current_regime = "NEUTRAL"
        self.style_preferences = {"GROWTH": 1.0, "VALUE": 1.0, "LARGE_CAP": 1.0, "SMALL_CAP": 1.0}

    def detect_regime(self, macro_data: pd.DataFrame) -> str:
        """
        금리와 VIX 데이터를 기반으로 매크로 레짐(Macro Regime)을 판별.
        macro_data는 '^TNX' (10년물 금리), '^VIX' 등을 포함한다고 가정.
        """
        if macro_data.empty:
            return "NEUTRAL"

        try:
            latest = macro_data.iloc[-1]
            tnx_val = latest.get("^TNX_pct_change", None)
            if tnx_val is None or pd.isna(tnx_val):
                if "^TNX" in macro_data.columns and len(macro_data) >= 2:
                    prev_tnx = float(macro_data["^TNX"].iloc[-2])
                    curr_tnx = float(macro_data["^TNX"].iloc[-1])
                    tnx_change = (curr_tnx - prev_tnx) / prev_tnx if prev_tnx > 0 else 0.0
                else:
                    tnx_change = 0.0
            else:
                tnx_change = float(tnx_val)

            vix_val = latest.get("^VIX", 15.0)
            vix_level = float(vix_val) if not pd.isna(vix_val) else 15.0

            # 레짐 판별
            if vix_level > 25.0:
                self.current_regime = "DEFENSIVE"
            elif tnx_change > 0.02:  # 금리 급등기
                self.current_regime = "INFLATION_RISING"
            elif tnx_change < -0.02:  # 금리 하락기
                self.current_regime = "RATE_CUTTING"
            else:
                self.current_regime = "EXPANSION"

        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            self.current_regime = "NEUTRAL"

        return self.current_regime

    def update_style_preferences(self) -> Dict[str, float]:
        """
        현재 레짐에 맞추어 스타일 팩터 가중치를 갱신.
        """
        if self.current_regime == "DEFENSIVE":
            # 방어적 환경: 대형 가치주 선호
            self.style_preferences = {"GROWTH": 0.5, "VALUE": 1.5, "LARGE_CAP": 1.5, "SMALL_CAP": 0.5}
        elif self.current_regime == "INFLATION_RISING":
            # 금리 상승기: 가치주 선호, 중소형주 기피
            self.style_preferences = {"GROWTH": 0.7, "VALUE": 1.3, "LARGE_CAP": 1.2, "SMALL_CAP": 0.8}
        elif self.current_regime == "RATE_CUTTING":
            # 금리 하락기: 성장주 및 중소형주 선호
            self.style_preferences = {"GROWTH": 1.4, "VALUE": 0.8, "LARGE_CAP": 0.9, "SMALL_CAP": 1.3}
        elif self.current_regime == "EXPANSION":
            # 확장기: 전반적 상승, 성장주/대형주 약간 선호
            self.style_preferences = {"GROWTH": 1.2, "VALUE": 0.9, "LARGE_CAP": 1.1, "SMALL_CAP": 1.0}
        else:
            self.style_preferences = {"GROWTH": 1.0, "VALUE": 1.0, "LARGE_CAP": 1.0, "SMALL_CAP": 1.0}

        return self.style_preferences

    def apply_style_weights(
        self, base_weights: np.ndarray, tickers: list, ticker_styles: Dict[str, Dict[str, str]]
    ) -> np.ndarray:
        """
        리스크 패리티 등으로 구한 base_weights에 스타일 가중치를 곱하고 정규화.
        ticker_styles 예시: {'AAPL': {'size': 'LARGE_CAP', 'value': 'GROWTH'}, ...}
        """
        if len(base_weights) != len(tickers):
            return base_weights

        adjusted_weights = np.copy(base_weights)

        for i, ticker in enumerate(tickers):
            style_info = ticker_styles.get(ticker, {})
            size_style = style_info.get("size", "LARGE_CAP")
            value_style = style_info.get("value", "VALUE")

            size_multiplier = self.style_preferences.get(size_style, 1.0)
            value_multiplier = self.style_preferences.get(value_style, 1.0)

            adjusted_weights[i] *= size_multiplier * value_multiplier

        adjusted_weights = np.nan_to_num(adjusted_weights, nan=0.0, posinf=0.0, neginf=0.0)
        sum_w = float(np.sum(adjusted_weights))
        if sum_w > 1e-12:
            adjusted_weights = adjusted_weights / sum_w
        else:
            adjusted_weights = np.ones(len(tickers)) / len(tickers) if len(tickers) > 0 else adjusted_weights

        return adjusted_weights
