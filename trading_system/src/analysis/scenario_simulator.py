import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class SectorOutlookScenario:
    """
    섹터별 경기 전망 시나리오 (-1.0: 강한 하락, 0.0: 횡보/중립, +1.0: 강한 상승)
    """
    semiconductor: float = 0.0      # 반도체 / IT / 전기전자
    battery_auto: float = 0.0       # 이차전지 / 자동차 / 운수장비
    bio_pharma: float = 0.0         # 바이오 / 제약 / 헬스케어
    finance: float = 0.0            # 금융 / 은행 / 증권 / 보험
    energy_chemical: float = 0.0    # 에너지 / 화학 / 철강
    consumer_staples: float = 0.0   # 식음료 / 필수소비재 / 유통
    utilities: float = 0.0          # 전기가스 / 유틸리티
    defense_shipbuilding: float = 0.0 # 방산 / 조선 / 기계

@dataclass
class MacroIndicatorScenario:
    """
    거시경제 지표 변동 시나리오 (변동률 % 및 수치)
    """
    usdkrw_change_pct: float = 0.0   # 환율 (원/달러) 변동률 (%) (예: +3.0 = 환율 3% 상승/원화 약세)
    wti_change_pct: float = 0.0      # 유가 (WTI) 변동률 (%) (예: +10.0 = 유가 10% 급등)
    us10y_rate: float = 4.0          # 미국 10년물 국채 금리 (%) (예: 4.5 = 금리 인상)
    vix_change_pct: float = 0.0      # 변동성지수 VIX 변동률 (%) (예: +20.0 = 시장 공포/위기 상승)

class ScenarioSimulationEngine:
    """
    섹터 및 거시경제(Macro) 시나리오 기반 주가 상승 수혜/타격 종목 예측 시뮬레이션 엔진.

    31대 다변화 앙상블 시스템의 CARD(Cross-Asset Regime Divergence) & Sector Rotation 팩터와 연동하여,
    사용자 지정 경기/매크로 변동 시나리오 하에서 3,379개 전 종목의 수혜 탄력성(Elasticity Score) 및
    조건부 앙상블 상승 예측 점수를 산출합니다.
    """

    # GICS 11 & KRX 주 섹터 민감도 (Beta Matrix)
    SECTOR_MACRO_ELASTICITY: Dict[str, Dict[str, Any]] = {
        'Information Technology': {'usdkrw': 0.6, 'wti': -0.2, 'us10y': -0.4, 'vix': -0.3, 'sector_key': 'semiconductor'},
        'Consumer Discretionary': {'usdkrw': 0.4, 'wti': -0.3, 'us10y': -0.3, 'vix': -0.4, 'sector_key': 'battery_auto'},
        'Health Care': {'usdkrw': 0.1, 'wti': -0.1, 'us10y': -0.5, 'vix': 0.2, 'sector_key': 'bio_pharma'},
        'Financials': {'usdkrw': -0.2, 'wti': 0.1, 'us10y': 0.7, 'vix': -0.2, 'sector_key': 'finance'},
        'Energy': {'usdkrw': -0.1, 'wti': 0.9, 'us10y': 0.2, 'vix': -0.1, 'sector_key': 'energy_chemical'},
        'Materials': {'usdkrw': 0.2, 'wti': 0.6, 'us10y': 0.1, 'vix': -0.3, 'sector_key': 'energy_chemical'},
        'Industrials': {'usdkrw': 0.5, 'wti': -0.4, 'us10y': 0.0, 'vix': -0.3, 'sector_key': 'defense_shipbuilding'},
        'Consumer Staples': {'usdkrw': -0.4, 'wti': -0.5, 'us10y': 0.1, 'vix': 0.3, 'sector_key': 'consumer_staples'},
        'Utilities': {'usdkrw': -0.6, 'wti': -0.7, 'us10y': -0.3, 'vix': 0.4, 'sector_key': 'utilities'},
        'Communication Services': {'usdkrw': -0.1, 'wti': -0.1, 'us10y': -0.2, 'vix': 0.1, 'sector_key': 'consumer_staples'},
        'Real Estate': {'usdkrw': -0.2, 'wti': -0.2, 'us10y': -0.8, 'vix': -0.2, 'sector_key': 'finance'},
    }

    def __init__(self):
        pass

    def simulate(
        self,
        base_ensemble_scores: Dict[str, float],
        sector_map: Dict[str, str],
        sector_scenario: SectorOutlookScenario,
        macro_scenario: MacroIndicatorScenario
    ) -> pd.DataFrame:
        """
        기존 앙상블 예측 점수에 시나리오 충격(Macro + Sector Shock)을 가산하여
        시나리오 조건부 예측 점수(Simulated Score) 및 상승 확률 변화량을 계산합니다.

        :param base_ensemble_scores: {symbol: base_score} (0.0 ~ 1.0)
        :param sector_map: {symbol: raw_sector_or_gics_sector}
        :param sector_scenario: SectorOutlookScenario 인스턴스
        :param macro_scenario: MacroIndicatorScenario 인스턴스
        :return: 시뮬레이션 결과 DataFrame
        """
        if not base_ensemble_scores:
            return pd.DataFrame()

        results = []
        sector_outlook_dict = {
            'semiconductor': sector_scenario.semiconductor,
            'battery_auto': sector_scenario.battery_auto,
            'bio_pharma': sector_scenario.bio_pharma,
            'finance': sector_scenario.finance,
            'energy_chemical': sector_scenario.energy_chemical,
            'consumer_staples': sector_scenario.consumer_staples,
            'utilities': sector_scenario.utilities,
            'defense_shipbuilding': sector_scenario.defense_shipbuilding,
        }

        for sym, raw_base_score in base_ensemble_scores.items():
            try:
                base_score = float(raw_base_score)
                if not np.isfinite(base_score):
                    base_score = 0.0
            except (ValueError, TypeError):
                base_score = 0.0

            raw_sec = sector_map.get(sym, 'General') if sector_map else 'General'
            gics_sec = self._normalize_gics(raw_sec)

            elas = self.SECTOR_MACRO_ELASTICITY.get(gics_sec, {
                'usdkrw': 0.0, 'wti': 0.0, 'us10y': 0.0, 'vix': 0.0, 'sector_key': 'consumer_staples'
            })

            # 1. Macro Impact Calculation
            def _sf_val(v: Any, default: float = 0.0) -> float:
                try:
                    f = float(v)
                    return f if np.isfinite(f) else default
                except (ValueError, TypeError):
                    return default

            _usdkrw: float = _sf_val(macro_scenario.usdkrw_change_pct)
            _wti: float = _sf_val(macro_scenario.wti_change_pct)
            _us10y: float = _sf_val(macro_scenario.us10y_rate, 4.0)
            _vix: float = _sf_val(macro_scenario.vix_change_pct)
            _elas_usdkrw: float = _sf_val(elas.get('usdkrw', 0.0))
            _elas_wti: float = _sf_val(elas.get('wti', 0.0))
            _elas_us10y: float = _sf_val(elas.get('us10y', 0.0))
            _elas_vix: float = _sf_val(elas.get('vix', 0.0))
            macro_shock = (
                (_usdkrw / 10.0) * _elas_usdkrw +
                (_wti / 10.0) * _elas_wti +
                ((_us10y - 4.0) / 2.0) * _elas_us10y +
                (_vix / 20.0) * _elas_vix
            )

            # 2. Direct Sector Outlook Impact Calculation
            sec_key = str(elas.get('sector_key', 'consumer_staples'))
            sector_outlook = _sf_val(sector_outlook_dict.get(sec_key, 0.0))
            sector_shock = sector_outlook * 0.25  # 최대 ±25% 충격 가중치

            # 3. Total Combined Scenario Shock & Simulated Score
            total_shock = macro_shock * 0.15 + sector_shock
            simulated_score = float(np.clip(base_score + total_shock, 0.0, 1.0))
            score_delta = simulated_score - base_score

            results.append({
                'symbol': sym,
                'sector': gics_sec,
                'base_score': round(base_score, 4),
                'simulated_score': round(simulated_score, 4),
                'score_delta': round(score_delta, 4),
                'macro_shock': round(macro_shock, 4),
                'sector_shock': round(sector_shock, 4),
                'impact_rationale': self._build_rationale(gics_sec, sector_outlook, macro_scenario, elas)
            })

        df_res = pd.DataFrame(results)
        if not df_res.empty:
            df_res = df_res.sort_values(by='simulated_score', ascending=False).reset_index(drop=True)
            df_res['sim_rank'] = df_res.index + 1

        return df_res

    def _normalize_gics(self, raw_sec: str, symbol: Optional[str] = None, name: Optional[str] = None) -> str:
        try:
            from src.core.sector_rotation import SectorRotationEngine
            return str(SectorRotationEngine.normalize_sector(raw_sec, symbol=symbol, name=name))
        except Exception:
            if not raw_sec or not isinstance(raw_sec, str):
                return 'Consumer Staples'
            if raw_sec in self.SECTOR_MACRO_ELASTICITY:
                return raw_sec
            return 'Consumer Staples'

    def _build_rationale(
        self,
        gics_sec: str,
        sector_outlook: float,
        macro: MacroIndicatorScenario,
        elas: Dict[str, Any]
    ) -> str:
        reasons = []
        s_out = float(sector_outlook) if (sector_outlook is not None and np.isfinite(sector_outlook)) else 0.0
        if s_out > 0.2:
            reasons.append(f"섹터 업황 호조 (+{s_out:.1f})")
        elif s_out < -0.2:
            reasons.append(f"섹터 업황 둔화 ({s_out:.1f})")

        _usdkrw = float(macro.usdkrw_change_pct) if (macro.usdkrw_change_pct is not None and np.isfinite(macro.usdkrw_change_pct)) else 0.0
        _wti = float(macro.wti_change_pct) if (macro.wti_change_pct is not None and np.isfinite(macro.wti_change_pct)) else 0.0
        _us10y = float(macro.us10y_rate) if (macro.us10y_rate is not None and np.isfinite(macro.us10y_rate)) else 4.0

        if _usdkrw != 0 and elas.get('usdkrw', 0.0) != 0:
            direction = "수혜" if (_usdkrw * float(elas.get('usdkrw', 0.0))) > 0 else "부담"
            reasons.append(f"환율변동({_usdkrw:+.1f}%) {direction}")

        if _wti != 0 and elas.get('wti', 0.0) != 0:
            direction = "수혜" if (_wti * float(elas.get('wti', 0.0))) > 0 else "원가부담"
            reasons.append(f"유가변동({_wti:+.1f}%) {direction}")

        if _us10y >= 4.3 and float(elas.get('us10y', 0.0)) > 0:
            reasons.append(f"고금리({_us10y:.2f}%) 마진 확대")
        elif _us10y >= 4.3 and float(elas.get('us10y', 0.0)) < -0.3:
            reasons.append(f"고금리({_us10y:.2f}%) 할인율 부담")

        return ", ".join(reasons) if reasons else "중립 시나리오 유지"
