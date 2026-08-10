"""Risk Management - 위험 관리 시스템"""

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import threading

import numpy as np
import pandas as pd

from src.risk.intraday_stop_loss import IntradayStopLossEngine, StopLossResult

logger = logging.getLogger(__name__)


class CrisisLevel(Enum):
    """위기 단계"""

    NONE = "NONE"
    WATCH = "WATCH"
    ACTIVE = "ACTIVE"
    SEVERE = "SEVERE"


class RiskLevel(Enum):
    """위험 수준"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EconomicCalendarAnalyzer:
    """
    Macro Economic Event Calendar & Surprise Index Analyzer
    FOMC, CPI, PCE, NFP 등 주요 경제지표 발표 D-1 ~ D+1 구간 위험 게이팅 및 서프라이즈 인덱스 산출.
    """

    def __init__(self):
        self._major_events = {
            "CPI": "Monthly Mid-Month",
            "FOMC": "8 Times per year",
            "NFP": "First Friday of Month",
        }

    def compute_event_risk_scaling(self, current_date: Optional[datetime] = None) -> float:
        """
        Computes risk scaling factor in [0.5, 1.0].
        Lower factor = Higher event risk (triggers defensive posture).
        """
        if current_date is None:
            current_date = datetime.now()

        day_of_week = current_date.weekday()
        day_of_month = current_date.day

        event_impact = 0.0
        # FOMC Months (Jan, Mar, May, Jun, Jul, Sep, Oct/Nov, Dec) mid/late-month window
        fomc_months = {1, 3, 5, 6, 7, 9, 11, 12}
        if current_date.month in fomc_months and 14 <= day_of_month <= 22 and day_of_week in (1, 2, 3):
            event_impact += 0.25
        # NFP Day (First Friday of month)
        elif day_of_week == 4 and 1 <= day_of_month <= 7:
            event_impact += 0.20
        # CPI Window (10th~15th of month)
        elif 10 <= day_of_month <= 15:
            event_impact += 0.15

        scaling_factor = max(0.5, 1.0 - event_impact)
        return float(scaling_factor)


class CrisisDetector:
    """위기 감지 및 방어 시스템 - 금융위기/코로나/전쟁 등 이상 징후 조기 탐지"""

    def __init__(self, risk_manager: Optional["RiskManager"] = None):
        self.rm = risk_manager
        self.logger = logger
        self._lock = threading.Lock()
        self.crisis_level = CrisisLevel.NONE
        self.calendar_analyzer = EconomicCalendarAnalyzer()
        self._vix_history: deque[float] = deque(maxlen=252)
        self._dd_history: deque[float] = deque(maxlen=63)
        self._usdkrw_history: deque[float] = deque(maxlen=252)
        self._oil_history: deque[float] = deque(maxlen=252)
        self._tnx_history: deque[float] = deque(maxlen=252)
        self._dxy_history: deque[float] = deque(maxlen=252)
        self._volume_spike_threshold = 3.0
        self._recovery_mode = False
        self._recovery_start_day: int | None = None
        self._days_in_crisis = 0
        self._days_since_crisis_ended = 0
        self._recovery_days = 0

    def get_target_cash_ratio(self) -> float:
        """
        Returns dynamic portfolio target cash allocation ratio based on CrisisLevel.
        - NONE: 0.0 (0% Cash)
        - WATCH: 0.15 (15% Cash)
        - ACTIVE: 0.35 (35% Cash)
        - SEVERE: 0.50 (50% Cash)
        """
        if self.crisis_level == CrisisLevel.SEVERE:
            return 0.50
        elif self.crisis_level == CrisisLevel.ACTIVE:
            return 0.35
        elif self.crisis_level == CrisisLevel.WATCH:
            return 0.15
        return 0.0

    def save_state(self, file_path: str = "models/crisis_state.json") -> None:
        """Persist CrisisDetector state and indicator histories to JSON file."""
        try:
            p = Path(file_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "crisis_level": self.crisis_level.value,
                "vix_history": list(self._vix_history),
                "dd_history": list(self._dd_history),
                "usdkrw_history": list(self._usdkrw_history),
                "oil_history": list(self._oil_history),
                "tnx_history": list(self._tnx_history),
                "dxy_history": list(self._dxy_history),
                "recovery_mode": self._recovery_mode,
                "days_in_crisis": self._days_in_crisis,
                "days_since_crisis_ended": self._days_since_crisis_ended,
            }
            tmp_p = p.with_suffix(".tmp")
            with open(tmp_p, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            tmp_p.replace(p)
            logger.info(f"CrisisDetector state persisted to {file_path}")
        except Exception as e:
            logger.warning(f"Failed to save CrisisDetector state: {e}")

    def load_state(self, file_path: str = "models/crisis_state.json") -> None:
        """Restore CrisisDetector state and indicator histories from JSON file."""
        try:
            p = Path(file_path)
            if not p.exists():
                return
            with open(p, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.crisis_level = CrisisLevel(state.get("crisis_level", "NONE"))
            self._vix_history = deque(state.get("vix_history", []), maxlen=252)
            self._dd_history = deque(state.get("dd_history", []), maxlen=63)
            self._usdkrw_history = deque(state.get("usdkrw_history", []), maxlen=252)
            self._oil_history = deque(state.get("oil_history", []), maxlen=252)
            self._tnx_history = deque(state.get("tnx_history", []), maxlen=252)
            self._dxy_history = deque(state.get("dxy_history", []), maxlen=252)
            self._recovery_mode = state.get("recovery_mode", False)
            self._days_in_crisis = state.get("days_in_crisis", 0)
            self._days_since_crisis_ended = state.get("days_since_crisis_ended", 0)
            logger.info(f"CrisisDetector state restored from {file_path} (level={self.crisis_level.value})")
        except Exception as e:
            logger.warning(f"Failed to load CrisisDetector state: {e}")


    def evaluate(
        self,
        vix: float = 20.0,
        positions: dict | None = None,
        daily_volume_ratio: float = 1.0,
        market_data_cache: dict | None = None,
        usdkrw: float | None = None,
        oil: float | None = None,
        tnx: float | None = None,
        dxy: float | None = None,
        cds_5y: float | None = None,
    ) -> CrisisLevel:
        """종합 위기 평가 - VIX + 거시지표(환율, 유가, 금리, 달러, CDS 신용스프레드) 융합"""
        dd = self.rm.calculate_drawdown() if self.rm is not None else 0.0
        with self._lock:
            self._vix_history.append(vix)
            self._dd_history.append(dd)
            for val, hist in [
                (usdkrw, self._usdkrw_history),
                (oil, self._oil_history),
                (tnx, self._tnx_history),
                (dxy, self._dxy_history),
            ]:
                if val is not None:
                    hist.append(val)

        vix_score = self._score_vix(vix)
        dd_score = self._score_drawdown(dd)
        volume_score = self._score_volume(daily_volume_ratio)
        trend_score = self._score_trend_breakdown(market_data_cache)
        macro_score = self._score_macro(usdkrw, oil, tnx, dxy)

        # Credit Default Swap (CDS) Risk Spike Booster (> 100bp or delta > 50bp)
        if cds_5y is not None and cds_5y > 100.0:
            macro_score = max(macro_score, 0.85)
            logger.info(f"[CREDIT RISK ENGINE] High CDS 5Y Premium detected ({cds_5y:.1f}bp); macro score boosted to {macro_score:.2f}")

        # Geopolitical Oil Shock Booster (3-day oil return > 8.0%)
        if len(self._oil_history) >= 4 and self._oil_history[-4] > 0:
            oil_3d_ret = (self._oil_history[-1] / self._oil_history[-4]) - 1.0
            if oil_3d_ret > 0.08:
                macro_score = max(macro_score, 0.75)
                logger.info(f"[GEOPOLITICAL RISK ENGINE] Oil shock surge detected ({oil_3d_ret*100:.1f}% 3D return); macro score boosted to {macro_score:.2f}")

        composite = vix_score * 0.25 + dd_score * 0.25 + volume_score * 0.15 + trend_score * 0.10 + macro_score * 0.25

        previous = self.crisis_level
        if composite >= 0.70:
            self.crisis_level = CrisisLevel.SEVERE
        elif composite >= 0.45:
            self.crisis_level = CrisisLevel.ACTIVE
        elif composite >= 0.25:
            self.crisis_level = CrisisLevel.WATCH
        else:
            self.crisis_level = CrisisLevel.NONE

        # Standalone VIX override check
        if vix >= 40.0:
            self.crisis_level = CrisisLevel.SEVERE
        elif vix >= 30.0:
            if self.crisis_level in (CrisisLevel.NONE, CrisisLevel.WATCH):
                self.crisis_level = CrisisLevel.ACTIVE

        # Standalone CDS credit risk override check
        if cds_5y is not None:
            if cds_5y > 150.0:
                self.crisis_level = CrisisLevel.SEVERE
            elif cds_5y > 100.0:
                if self.crisis_level in (CrisisLevel.NONE, CrisisLevel.WATCH):
                    self.crisis_level = CrisisLevel.ACTIVE

        if self.crisis_level in (CrisisLevel.ACTIVE, CrisisLevel.SEVERE):
            self._days_in_crisis += 1
            self._recovery_mode = False
            self._recovery_start_day = None
            self._recovery_days = 0
            self._days_since_crisis_ended = 0
        else:
            if self._recovery_mode:
                self._recovery_days += 1
                if self._recovery_days >= 20:
                    self._recovery_mode = False
                    self._recovery_days = 0
                    self.logger.info("Recovery complete: portfolio exposure fully restored")
            if self._days_in_crisis > 0:
                self._days_since_crisis_ended += 1
                self._check_recovery(vix, dd)

        if self.crisis_level != previous:
            self.logger.warning(
                f"Crisis level changed: {previous.value} -> {self.crisis_level.value} "
                f"(VIX={vix:.1f}, DD={dd:.2%}, vol={daily_volume_ratio:.1f}x, macro={macro_score:.2f}, "
                f"composite={composite:.2f})"
            )
        return self.crisis_level

    def _score_vix(self, vix: float) -> float:
        if vix <= 15:
            return 0.0
        vix_roc = 0.0
        if len(self._vix_history) >= 5:
            vix_roc = (vix - self._vix_history[-5]) / max(self._vix_history[-5], 0.1)
        raw = (vix - 15) / 40.0
        roc_bonus = max(0, min(0.3, vix_roc * 0.1))
        return min(1.0, raw + roc_bonus)

    def _score_drawdown(self, dd: float) -> float:
        dd_speed = 0.0
        if len(self._dd_history) >= 5:
            dd_speed = (dd - self._dd_history[-5]) / max(0.01, 5)
        raw = min(1.0, dd / 0.20)
        speed_bonus = max(0, min(0.3, dd_speed * 5.0))
        return min(1.0, raw + speed_bonus)

    def _score_volume(self, volume_ratio: float) -> float:
        if volume_ratio <= 1.0:
            return 0.0
        return min(1.0, (volume_ratio - 1.0) / (self._volume_spike_threshold - 1.0))

    def _score_trend_breakdown(self, cache: dict | None) -> float:
        if not cache:
            return 0.0
        bearish_count = 0
        total = 0
        for sym, data in cache.items():
            if isinstance(data, dict) and "ema20" in data and "ema50" in data:
                total += 1
                if data["ema20"] < data["ema50"]:
                    bearish_count += 1
        if total == 0:
            return 0.0
        return bearish_count / total

    def _score_macro(self, usdkrw: float | None, oil: float | None, tnx: float | None, dxy: float | None) -> float:
        """거시경제 지표 기반 위험 점수 (0.0 ~ 1.0)"""
        scores: List[float] = []

        # USD/KRW: 원화 약세(환율 상승) → 자본유출 위험
        if usdkrw is not None and len(self._usdkrw_history) >= 5:
            baseline = sum(list(self._usdkrw_history)[-5:]) / 5
            spike = (usdkrw - baseline) / max(baseline, 1.0)
            scores.append(min(1.0, max(0, spike * 5.0)))

        # WTI: 유가 급등($100+) → 인플레이션 → 긴축 위험
        if oil is not None and len(self._oil_history) >= 5:
            oil_z = max(0, (oil - 75.0) / 75.0)
            oil_mom = (oil - self._oil_history[-5]) / max(self._oil_history[-5], 1.0)
            scores.append(min(1.0, oil_z + max(0, oil_mom * 2.0)))

        # ^TNX: 금리 급등(5%+) or 급격한 상승 속도 → 시장 긴축
        if tnx is not None and len(self._tnx_history) >= 5:
            tnx_level = max(0, (tnx - 3.5) / 3.5)
            tnx_mom = (tnx - self._tnx_history[-5]) / max(self._tnx_history[-5], 0.01)
            scores.append(min(1.0, tnx_level + max(0, tnx_mom * 3.0)))

        # DXY: 달러 강세(105+) → 신흥국 부담
        if dxy is not None and len(self._dxy_history) >= 5:
            dxy_level = max(0, (dxy - 100.0) / 15.0)
            dxy_mom = (dxy - self._dxy_history[-5]) / max(self._dxy_history[-5], 0.01)
            scores.append(min(1.0, dxy_level + max(0, dxy_mom * 3.0)))

        return sum(scores) / max(len(scores), 1)

    def _check_recovery(self, vix: float, dd: float):
        """위기 종료(회복) 감지"""
        if self._recovery_start_day is not None:
            days_since = self._days_since_crisis_ended - self._recovery_start_day
            if days_since >= 5 and dd < 0.05 and vix < 25:
                self._recovery_mode = True
                self._recovery_days = 1
                self._days_in_crisis = 0
                self._days_since_crisis_ended = 0
                self._recovery_start_day = None
                self.logger.info("Recovery mode activated: crisis passed, gradually increasing exposure")
            return

        if vix < 25 and dd < 0.05 and self._days_in_crisis >= 10:
            self._recovery_start_day = self._days_since_crisis_ended

    @property
    def is_crisis(self) -> bool:
        return self.crisis_level in (CrisisLevel.ACTIVE, CrisisLevel.SEVERE)

    @property
    def is_recovery(self) -> bool:
        return self._recovery_mode

    def get_crisis_cash_target(self) -> float:
        targets = {
            CrisisLevel.NONE: 0.10,
            CrisisLevel.WATCH: 0.30,
            CrisisLevel.ACTIVE: 0.60,
            CrisisLevel.SEVERE: 0.85,
        }
        base = targets.get(self.crisis_level, 0.10)
        if self._recovery_mode:
            progress = min(1.0, (self._recovery_days or 1) / 20.0)
            return 0.10 + (base - 0.10) * (1.0 - progress)
        return base

    def get_crisis_position_multiplier(self) -> float:
        multipliers = {
            CrisisLevel.NONE: 1.0,
            CrisisLevel.WATCH: 0.70,
            CrisisLevel.ACTIVE: 0.40,
            CrisisLevel.SEVERE: 0.15,
        }
        base = multipliers.get(self.crisis_level, 1.0)
        if self._recovery_mode:
            progress = min(1.0, (self._recovery_days or 1) / 20.0)
            return 0.15 + (1.0 - 0.15) * progress
        return base

    def get_crisis_stop_multiplier(self) -> float:
        """위기 시 손절가를 더 타이트하게 설정"""
        multipliers = {
            CrisisLevel.NONE: 1.0,
            CrisisLevel.WATCH: 0.80,
            CrisisLevel.ACTIVE: 0.60,
            CrisisLevel.SEVERE: 0.40,
        }
        return multipliers.get(self.crisis_level, 1.0)

    def should_block_new_buys(self) -> bool:
        return self.crisis_level == CrisisLevel.SEVERE

    def should_liquidate(self) -> bool:
        return self.crisis_level == CrisisLevel.SEVERE and self._days_in_crisis >= 3


@dataclass
class RiskMetrics:
    """위험 지표"""

    current_value: float
    max_loss_limit: float
    max_position_size: float
    stop_loss_pct: float  # 1% = 0.01
    take_profit_pct: float
    current_drawdown: float
    max_drawdown_allowed: float
    portfolio_volatility: float
    risk_level: RiskLevel
    timestamp: datetime = field(default_factory=datetime.now)


class RiskManager:
    def __init__(
        self,
        portfolio_value: float = 1000000,
        max_loss_per_trade_pct: float = 0.02,
        max_portfolio_loss_pct: float = 0.10,
        max_position_size_pct: float = 0.25,
        default_stop_loss_pct: float = 0.05,
        default_take_profit_pct: float = 0.15,
        max_drawdown_allowed: float = 0.20,
        atr_multiplier_stop: float = 2.0,
        atr_multiplier_target: float = 3.0,
        volatility_scaling: bool = True,
        target_annual_volatility: float = 0.15,
        max_sector_exposure_pct: float = 0.30,
    ):
        self.portfolio_value = portfolio_value
        self.peak_value = portfolio_value
        self.logger = logger

        self.max_loss_per_trade_pct = max_loss_per_trade_pct
        self.max_portfolio_loss_pct = max_portfolio_loss_pct
        self.max_position_size_pct = max_position_size_pct
        self.default_stop_loss_pct = default_stop_loss_pct
        self.default_take_profit_pct = default_take_profit_pct
        self.max_drawdown_allowed = max_drawdown_allowed
        self.atr_multiplier_stop = atr_multiplier_stop
        self.atr_multiplier_target = atr_multiplier_target
        self.volatility_scaling = volatility_scaling
        self.target_annual_volatility = target_annual_volatility
        self.max_sector_exposure_pct = max_sector_exposure_pct
        self.position_limits: Dict[str, float] = {}
        self._correlation_matrix: Dict[str, Dict[str, float]] = {}
        self._daily_returns: deque[float] = deque(maxlen=252)
        self._consecutive_losses: int = 0
        import threading
        self._lock = threading.Lock()

        self.crisis_detector = CrisisDetector(self)
        self.intraday_stop_loss_engine = IntradayStopLossEngine()
        self.active_strategy = "HYBRID"

        self._load_config()

        self.metrics_history: List[RiskMetrics] = []
        self.alerts: List[Dict] = []
        self.stress_test_passed: bool = True
        self.stress_test_adjustment_factor: float = 1.0
        self.stress_test_reports: Dict[str, Any] = {}

    def update_stress_test_results(
        self,
        stress_reports: Union[Dict[str, Any], Any],
        fail_adjustment_factor: float = 0.75,
    ) -> None:
        """
        Updates RiskManager state with historical stress test results.
        If pass_flag is False for any evaluated scenario,
        applies dynamic stress adjustment factor (default 0.75) to position sizes.
        """
        all_passed = True
        if isinstance(stress_reports, dict):
            self.stress_test_reports = stress_reports
            for key, rep in stress_reports.items():
                if hasattr(rep, "pass_flag"):
                    if not rep.pass_flag:
                        all_passed = False
                elif isinstance(rep, dict) and "pass_flag" in rep:
                    if not rep["pass_flag"]:
                        all_passed = False
        elif hasattr(stress_reports, "pass_flag"):
            all_passed = bool(stress_reports.pass_flag)
            self.stress_test_reports = {"report": stress_reports}

        self.stress_test_passed = all_passed
        if not all_passed:
            self.stress_test_adjustment_factor = fail_adjustment_factor
            self.logger.warning(
                f"[RISK MANAGER] Stress test failed! Position size scaling factor set to {fail_adjustment_factor:.2f}"
            )
        else:
            self.stress_test_adjustment_factor = 1.0
            self.logger.info("[RISK MANAGER] Stress test passed. Full position capacity maintained.")

    def evaluate_crisis(
        self,
        vix: float = 20.0,
        positions: dict | None = None,
        daily_volume_ratio: float = 1.0,
        market_data_cache: dict | None = None,
        usdkrw: float | None = None,
        oil: float | None = None,
        tnx: float | None = None,
        dxy: float | None = None,
    ) -> CrisisLevel:
        """Evaluate crisis level using VIX + macro indicators + drawdown."""
        return self.crisis_detector.evaluate(
            vix=vix,
            positions=positions,
            daily_volume_ratio=daily_volume_ratio,
            market_data_cache=market_data_cache,
            usdkrw=usdkrw,
            oil=oil,
            tnx=tnx,
            dxy=dxy,
        )

    def evaluate_intraday_stop_loss(
        self,
        symbol: str,
        intraday_data: Union[pd.DataFrame, dict],
        entry_price: Optional[float] = None,
        atr: Optional[float] = None,
    ) -> StopLossResult:
        """
        Evaluates intraday stop-loss risk for a given symbol.
        Tightens thresholds based on active market crisis level.
        """
        cur_price = entry_price or 0.0
        if isinstance(intraday_data, pd.DataFrame) and not intraday_data.empty:
            prices = intraday_data['close'].values if 'close' in intraday_data.columns else intraday_data['Close'].values
            cur_price = float(prices[-1])

        signal = self.intraday_stop_loss_engine.evaluate(symbol, intraday_data)

        result = StopLossResult(
            symbol=symbol,
            triggered=signal.triggered,
            trigger_stop=signal.trigger_stop,
            scale_factor=signal.scale_factor,
            reason=signal.reason,
            intraday_return=signal.intraday_return,
            panic_score=signal.panic_score
        )
        if signal.trigger_stop:
            cur_price = 0.0
            if isinstance(intraday_data, pd.DataFrame) and not intraday_data.empty:
                prices = intraday_data['close'].values if 'close' in intraday_data.columns else intraday_data['Close'].values
                cur_price = float(prices[-1])
            elif isinstance(intraday_data, dict):
                cur_price = float(intraday_data.get('current_price', 0.0))

            eff_entry = entry_price if (entry_price is not None and entry_price > 0) else cur_price
            self._create_alert(
                alert_type=f"INTRADAY_STOP_LOSS_{result.reason}",
                symbol=symbol,
                current_price=cur_price,
                entry_price=eff_entry,
            )
            self.logger.warning(
                f"[INTRADAY STOP LOSS TRIGGERED] Symbol: {symbol} | Reason: {result.reason} | "
                f"Panic Score: {result.panic_score:.2f} | Scale Factor: {result.scale_factor:.2f}"
            )
        return result

    def check_intraday_risk(
        self,
        portfolio_intraday_data: Dict[str, Union[pd.DataFrame, dict]],
        positions: Optional[Dict[str, float]] = None,
    ) -> Dict[str, StopLossResult]:
        """
        Evaluates intraday stop-loss status across portfolio holdings or watchlist.
        Returns dictionary mapping symbol -> StopLossResult.
        """
        results = {}
        for symbol, data in portfolio_intraday_data.items():
            try:
                entry_price = positions.get(symbol) if positions else None
                res = self.evaluate_intraday_stop_loss(symbol, data, entry_price=entry_price)
                results[symbol] = res
            except Exception as e:
                self.logger.warning(
                    f"Error evaluating intraday stop loss for symbol {symbol}: {e}"
                )
                results[symbol] = StopLossResult(
                    symbol=symbol,
                    trigger_stop=False,
                    scale_factor=1.0,
                    reason="EVALUATION_ERROR",
                    intraday_return=0.0,
                    panic_score=0.0,
                )
        return results

    def calculate_atr_based_stop(self, entry_price: float, atr: float) -> float:
        stop_distance = atr * self.atr_multiplier_stop
        base = max(entry_price - stop_distance, entry_price * (1 - self.default_stop_loss_pct * 2))
        crisis_mult = self.crisis_detector.get_crisis_stop_multiplier()
        if crisis_mult < 1.0:
            tighter = entry_price - (entry_price - base) * crisis_mult
            self.logger.info(f"Crisis stop tightening: {base:.2f} -> {tighter:.2f} (mult={crisis_mult:.2f})")
            return tighter
        return base

    def calculate_atr_based_target(self, entry_price: float, atr: float) -> float:
        target_distance = atr * self.atr_multiplier_target
        base = min(entry_price + target_distance, entry_price * (1 + self.default_take_profit_pct * 2))
        crisis_mult = self.crisis_detector.get_crisis_stop_multiplier()
        if crisis_mult < 1.0:
            tighter = entry_price + (base - entry_price) * crisis_mult
            self.logger.info(f"Crisis target tightening: {base:.2f} -> {tighter:.2f} (mult={crisis_mult:.2f})")
            return tighter
        return base

    REGIME_ATR_MULTIPLIERS = {
        "strong_bull": {"stop": 3.0, "target": 5.0, "trail": 0.08},
        "weak_bull": {"stop": 2.5, "target": 4.0, "trail": 0.06},
        "weak_bear": {"stop": 1.5, "target": 2.5, "trail": 0.04},
        "strong_bear": {"stop": 1.0, "target": 2.0, "trail": 0.03},
    }

    def get_adaptive_atr_multipliers(self, regime: str = "weak_bull", adx: float = 20.0) -> dict:
        """시장 레짐과 ADX 강도에 따른 ATR 멀티플라이어 반환"""
        base = self.REGIME_ATR_MULTIPLIERS.get(regime, self.REGIME_ATR_MULTIPLIERS["weak_bull"]).copy()

        if adx > 30:
            base["stop"] *= 1.2
            base["target"] *= 1.2
        elif adx < 20:
            base["stop"] *= 0.8
            base["target"] *= 0.8

        return base

    def check_trailing_stop_signal(
        self,
        symbol: str,
        current_price: float,
        highest_price: float,
        atr: float,
        regime: str = "weak_bull",
        adx: float = 20.0,
    ) -> bool:
        if current_price <= 0.0:
            return True
        if atr <= 0.0:
            return False

        multipliers = self.get_adaptive_atr_multipliers(regime, adx)
        stop_multiplier = multipliers.get("stop", 2.0)
        stop_distance = atr * stop_multiplier

        crisis_mult = self.crisis_detector.get_crisis_stop_multiplier()
        if crisis_mult < 1.0:
            stop_distance *= crisis_mult

        drawdown = self.calculate_drawdown()
        if drawdown > 0.0 and self.max_drawdown_allowed > 0.0:
            drawdown_scaler = 1.0 - (drawdown / self.max_drawdown_allowed)
            drawdown_scaler = max(0.25, min(1.0, drawdown_scaler))
            stop_distance *= drawdown_scaler

        if highest_price - current_price >= stop_distance:
            return True
        return False

    def calculate_trailing_stop_price(
        self,
        highest_price: float,
        atr: float,
        regime: str = "weak_bull",
        adx: float = 20.0,
    ) -> float:
        """ATR 기반 동적 트레일링 스탑 가격 계산"""
        if atr <= 0.0 or highest_price <= 0.0:
            return 0.0

        multipliers = self.get_adaptive_atr_multipliers(regime, adx)
        stop_multiplier = multipliers.get("stop", 2.0)
        stop_distance = atr * stop_multiplier

        crisis_mult = self.crisis_detector.get_crisis_stop_multiplier()
        if crisis_mult < 1.0:
            stop_distance *= crisis_mult

        drawdown = self.calculate_drawdown()
        if drawdown > 0.0 and self.max_drawdown_allowed > 0.0:
            drawdown_scaler = 1.0 - (drawdown / self.max_drawdown_allowed)
            drawdown_scaler = max(0.25, min(1.0, drawdown_scaler))
            stop_distance *= drawdown_scaler

        return float(max(0.0, highest_price - stop_distance))

    def check_sentiment_blacklist(self, symbol: str, blacklist: Optional[set | list | dict] = None) -> bool:
        """Returns True if the symbol is blacklisted due to critical sentiment/disclosure risk."""
        if not symbol or not blacklist:
            return False
        b_set = set(blacklist.keys()) if isinstance(blacklist, dict) else set(blacklist)
        is_blocked = symbol in b_set
        if is_blocked:
            logger.warning(f"[RISK MANAGER] Order blocked for symbol '{symbol}': Present in sentiment blacklist!")
        return is_blocked

    def screen_liquidity(self, symbol: str, name: str = "", volume: float = 1.0) -> bool:
        """
        Liquidity screening gate:
        Returns False if preferred stock ('우', '우B', etc.), SPAC ('스팩', 'SPAC'),
        or zero volume symbol (volume <= 0). Returns True if valid.
        """
        if not symbol:
            return False
        # Preferred stock check
        if name.endswith('우') or name.endswith('우B') or name.endswith('1우') or name.endswith('2우B') or name.endswith('3우B'):
            return False
        if len(symbol) == 6 and symbol[-1] in ['K', 'L', 'M', 'N', 'O']:
            return False
        # SPAC check
        if '스팩' in name or 'SPAC' in name.upper():
            return False
        # Zero volume check
        if volume <= 0:
            return False
        return True

    def is_illiquid_or_preferred(self, symbol: str, name: str = "", volume: float = 1.0) -> bool:
        """Returns True if preferred stock, SPAC, or zero volume symbol."""
        return not self.screen_liquidity(symbol, name, volume)

    def check_sector_risk_cap(
        self,
        sector: str,
        current_sector_exposure: float,
        new_trade_exposure: float,
        total_portfolio_value: float,
    ) -> bool:
        """Return True if sector exposure stays within max_sector_exposure_pct (default 30%)."""
        if total_portfolio_value <= 0:
            return False
        total_sector_val = current_sector_exposure + new_trade_exposure
        return (total_sector_val / total_portfolio_value) <= self.max_sector_exposure_pct


    def calculate_max_sector_position_value(
        self,
        sector: str,
        current_sector_exposure: float,
        total_portfolio_value: float,
    ) -> float:
        """Calculate maximum additional capital allowed for a specific sector under the sector risk cap."""
        max_allowed = total_portfolio_value * self.max_sector_exposure_pct
        return max(0.0, max_allowed - current_sector_exposure)

    def _volatility_scalar(self, vix: float = 20.0) -> float:
        if not self.volatility_scaling or vix <= 0:
            return 1.0
        return float(max(0.25, min(1.5, 20.0 / vix)))

    def record_daily_return(self, daily_return: float) -> None:
        """Record daily portfolio return for volatility estimation."""
        self._daily_returns.append(daily_return)

    def get_volatility_scaler(self) -> float:
        """Return scaler to target annualized volatility using recent daily returns."""
        if len(self._daily_returns) < 10:
            return 1.0
        daily_vol = float(np.std(self._daily_returns, ddof=1))
        if daily_vol == 0.0:
            return 1.0
        annualized_vol = daily_vol * (252**0.5)
        scaler = self.target_annual_volatility / annualized_vol
        return float(max(0.25, min(2.0, scaler)))

    def check_risk_off_signal(self, vix_value: Optional[float] = None) -> bool:
        """
        Returns True if VIX index >= 25.0.
        If vix_value is not provided, fetch it using AlternativeDataClient().fetch_vix()
        with a safety try-except block, falling back to 20.0 on error.
        """
        if vix_value is None:
            try:
                from src.data_layer.alt_data import AlternativeDataClient

                vix_value = AlternativeDataClient().fetch_vix()
            except Exception as e:
                self.logger.error(f"Failed to fetch VIX value in check_risk_off_signal: {e}")
                vix_value = 20.0
        return vix_value >= 25.0

    def _get_config_path(self):
        return Path(__file__).parent.parent.parent / "risk_config.json"

    def _load_config(self):
        config_path = self._get_config_path()
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.default_stop_loss_pct = data.get("default_stop_loss_pct", self.default_stop_loss_pct)
                    self.max_portfolio_loss_pct = data.get("max_portfolio_loss_pct", self.max_portfolio_loss_pct)
                    self.max_position_size_pct = data.get("max_position_size_pct", self.max_position_size_pct)
                    self.active_strategy = data.get("active_strategy", self.active_strategy).upper()
                self.logger.info(
                    f"Risk configuration loaded from {config_path}: "
                    f"StopLoss={self.default_stop_loss_pct:.2%}, "
                    f"MaxPortfolioLoss={self.max_portfolio_loss_pct:.2%}, "
                    f"MaxPositionSize={self.max_position_size_pct:.2%}, "
                    f"ActiveStrategy={self.active_strategy}"
                )
            except Exception as e:
                self.logger.error(f"Failed to load risk configuration: {e}")

    def save_config(self):
        config_path = self._get_config_path()
        try:
            data = {
                "default_stop_loss_pct": self.default_stop_loss_pct,
                "max_portfolio_loss_pct": self.max_portfolio_loss_pct,
                "max_position_size_pct": self.max_position_size_pct,
                "active_strategy": self.active_strategy,
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.logger.info(
                f"Risk configuration saved to {config_path}: "
                f"StopLoss={self.default_stop_loss_pct:.2%}, "
                f"MaxPortfolioLoss={self.max_portfolio_loss_pct:.2%}, "
                f"MaxPositionSize={self.max_position_size_pct:.2%}, "
                f"ActiveStrategy={self.active_strategy}"
            )
        except Exception as e:
            self.logger.error(f"Failed to save risk configuration: {e}")

    def set_position_limit(self, symbol: str, max_quantity: int):
        """종목별 최대 수량 설정"""
        self.position_limits[symbol] = max_quantity
        self.logger.info(f"Position limit set for {symbol}: {max_quantity}")

    def calculate_max_position_size(self, current_price: float) -> int:
        """최대 포지션 크기 계산"""
        max_value = self.portfolio_value * self.max_position_size_pct * self.stress_test_adjustment_factor
        max_quantity = int(max_value / current_price)
        return max_quantity

    def calculate_kelly_fraction(self, win_rate: float, win_loss_ratio: float, half_kelly: bool = True) -> float:
        """Kelly Criterion을 사용한 최적 투자 비중 계산 (f*)"""
        if win_loss_ratio <= 0:
            return 0.0

        # Kelly 공식: f* = W - ((1 - W) / R)
        kelly_pct = win_rate - ((1.0 - win_rate) / win_loss_ratio)

        if kelly_pct <= 0:
            return 0.0

        # 보수적 운영을 위해 Half Kelly 적용
        if half_kelly:
            kelly_pct /= 2.0

        # 최대 포지션 한도를 초과하지 않도록 제한
        return min(kelly_pct, self.max_position_size_pct)

    def get_vix_position_cap(self, vix: float) -> float:
        """VIX 수준에 따른 포지션 크기 상한 (Risk-Off 스위치).
        VIX > 30 → 15%, VIX > 25 → 30%, VIX > 20 → 50%, else 100% (no cap).
        """
        if vix > 30:
            return 0.15
        elif vix > 25:
            return 0.30
        elif vix > 20:
            return 0.50
        return 1.0

    def calculate_robust_kelly(
        self, win_rate: float, win_loss_ratio: float, n_trades: int, consecutive_losses: int = 0
    ) -> float:
        """거래 수 기반 신뢰구간 + 연속 손실 감안 Kelly (영역 3-1)"""
        raw_kelly = win_rate - ((1.0 - win_rate) / max(win_loss_ratio, 0.01))
        if raw_kelly <= 0:
            return 0.0
        confidence_factor = min(1.0, n_trades / 50.0)
        adjusted = raw_kelly * confidence_factor * 0.5  # Half Kelly 시작
        if consecutive_losses >= 3:
            adjusted *= 0.5
        if consecutive_losses >= 5:
            adjusted *= 0.5
        if consecutive_losses >= 7:
            adjusted *= 0.25  # 쿨다운
        if consecutive_losses >= 10:
            adjusted = 0.0  # 거래 중단

        if consecutive_losses >= 10 or adjusted <= 0.0:
            return 0.0
        return max(0.01, min(adjusted, self.max_position_size_pct))

    def get_composite_volatility_scalar(self, vix: float, atr_ratio: float = 0.0, bb_width: float = 0.0) -> float:
        """VIX + ATR + BB Width 복합 변동성 스칼라 (영역 3-3)"""
        vix_score = max(0.3, min(1.5, 20.0 / max(vix, 1)))
        atr_score = max(0.3, min(1.5, 0.02 / max(atr_ratio, 0.001))) if atr_ratio > 0 else vix_score
        bb_score = max(0.5, min(1.3, 0.15 / max(bb_width, 0.01))) if bb_width > 0 else 1.0
        return vix_score * 0.4 + atr_score * 0.35 + bb_score * 0.25

    def get_drawdown_exposure_limit(self) -> float:
        """드로다운 깊이에 따라 점진적으로 노출 제한 (영역 6-3)"""
        dd = self.calculate_drawdown()
        if dd < 0.05:
            return 1.0
        elif dd < 0.10:
            return 0.75
        elif dd < 0.15:
            return 0.50
        elif dd < 0.20:
            return 0.25
        return 0.0

    def calculate_position_sizing(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        win_rate: float = 0.0,
        win_loss_ratio: float = 0.0,
        vix: float = 20.0,
        atr: float = 0.0,
    ) -> int:
        """Kelly Criterion 기반 포지션 사이징 (선택적) 및 리스크 기반 사이징"""
        # 위험금 계산
        risk_per_share = entry_price - stop_loss_price
        if risk_per_share <= 0:
            self.logger.warning("Invalid stop loss price")
            return 0

        # Kelly 공식 적용 (정보가 있는 경우)
        if win_rate > 0 and win_loss_ratio > 0:
            kelly_pct = self.calculate_kelly_fraction(win_rate, win_loss_ratio)
            if atr > 0.0:
                asset_vol_annual = (atr / entry_price) * (252**0.5) if entry_price > 0.0 else 0.0
                if asset_vol_annual > 0.0:
                    vol_scaler = self.target_annual_volatility / asset_vol_annual
                    vol_scaler = max(0.25, min(1.5, vol_scaler))
                    kelly_pct *= vol_scaler
            max_value = self.portfolio_value * kelly_pct
        else:
            crisis_risk_mult_map = {
                CrisisLevel.NONE: 1.0,
                CrisisLevel.WATCH: 0.75,
                CrisisLevel.ACTIVE: 0.50,
                CrisisLevel.SEVERE: 0.25
            }
            risk_mult = crisis_risk_mult_map.get(self.crisis_detector.crisis_level, 1.0)
            scaled_max_loss_pct = self.max_loss_per_trade_pct * risk_mult
            max_loss = self.portfolio_value * scaled_max_loss_pct
            max_value = max_loss * (entry_price / risk_per_share)

        vol_scalar = self._volatility_scalar(vix)
        max_value *= vol_scalar

        # VIX Risk-Off 스위치: VIX 수준별 포지션 상한
        vix_cap = self.get_vix_position_cap(vix)
        if vix_cap < 1.0:
            max_value = min(max_value, self.portfolio_value * vix_cap)
            self.logger.info(f"VIX Risk-Off: {symbol} capped at {vix_cap:.0%} of portfolio (VIX={vix:.1f})")

        position_quantity = max(0, int(max_value / entry_price))
        unpenalized_max_position = int((self.portfolio_value * self.max_position_size_pct) / entry_price)
        position_quantity = min(position_quantity, unpenalized_max_position)

        # 위기 시 포지션 크기 감축
        crisis_mult = self.crisis_detector.get_crisis_position_multiplier()
        if crisis_mult < 1.0:
            old_qty = position_quantity
            position_quantity = max(0, int(position_quantity * crisis_mult))
            self.logger.info(
                f"Crisis position sizing: {symbol} qty {old_qty} -> {position_quantity} "
                f"(crisis_mult={crisis_mult:.2f}, level={self.crisis_detector.crisis_level.value})"
            )

        if self.stress_test_adjustment_factor < 1.0:
            old_qty = position_quantity
            position_quantity = max(0, int(position_quantity * self.stress_test_adjustment_factor))
            self.logger.info(
                f"Stress test position sizing: {symbol} qty {old_qty} -> {position_quantity} "
                f"(stress_factor={self.stress_test_adjustment_factor:.2f})"
            )

        if symbol in self.position_limits:
            position_quantity = int(min(position_quantity, self.position_limits[symbol]))

        if position_quantity <= 0:
            return 0

        if vol_scalar < 1.0:
            self.logger.info(f"Volatility scaling applied: {vol_scalar:.2f}x (VIX={vix})")

        self.logger.info(f"Calculated position size for {symbol}: {position_quantity} shares")
        return position_quantity

    def check_stop_loss(self, symbol: str, current_price: float, entry_price: float) -> bool:
        """Stop Loss 확인"""
        stop_loss_price = entry_price * (1 - self.default_stop_loss_pct)

        if current_price <= stop_loss_price:
            self._create_alert("STOP_LOSS", symbol, current_price, entry_price)
            return True

        return False

    def check_take_profit(self, symbol: str, current_price: float, entry_price: float) -> bool:
        """Take Profit 확인"""
        take_profit_price = entry_price * (1 + self.default_take_profit_pct)

        if current_price >= take_profit_price:
            self._create_alert("TAKE_PROFIT", symbol, current_price, entry_price)
            return True

        return False

    def update_portfolio_value(self, new_value: float):
        """포트폴리오 가치 업데이트"""
        with self._lock:
            self.portfolio_value = new_value
            if new_value > self.peak_value:
                self.peak_value = new_value

        self.logger.debug(f"Portfolio value updated: {new_value}")

    def check_crisis_liquidation(self) -> list[str]:
        """위기 상황에서 청산해야 할 심볼 목록 반환"""
        if self.crisis_detector.should_liquidate():
            self.logger.warning(
                f"CRISIS LIQUIDATION TRIGGERED: level={self.crisis_detector.crisis_level.value}, "
                f"day={self.crisis_detector._days_in_crisis}"
            )
            return ["*ALL*"]
        return []

    def get_crisis_new_buy_blocked(self) -> bool:
        """위기 시 신규 매수 차단 여부"""
        blocked = self.crisis_detector.should_block_new_buys()
        if blocked:
            self.logger.warning(f"New buys blocked: crisis level={self.crisis_detector.crisis_level.value}")
        return blocked

    def get_crisis_cash_target_pct(self) -> float:
        """위기 상황에 따른 목표 현금 비중"""
        return self.crisis_detector.get_crisis_cash_target()

    def calculate_drawdown(self, total_portfolio_value: Optional[float] = None) -> float:
        """현재 Drawdown 계산 (총 포트폴리오 가치 = 현금 + 오픈 포지션 평가액)"""
        with self._lock:
            val = total_portfolio_value if (total_portfolio_value is not None and total_portfolio_value > 0) else self.portfolio_value
            if val > self.peak_value:
                self.peak_value = val
            if self.peak_value == 0:
                return 0.0

            drawdown = (self.peak_value - val) / self.peak_value
            return drawdown

    def calculate_risk_level(self, positions: Dict[str, float]) -> RiskLevel:
        """현재 위험 수준 계산 (drawdown + 포지션 집중도 + 상관관계 + 위기 모드)"""
        # 위기 모드가 ACTIVE 이상이면 강제로 HIGH 이상
        if self.crisis_detector.crisis_level == CrisisLevel.SEVERE:
            return RiskLevel.CRITICAL
        if self.crisis_detector.crisis_level == CrisisLevel.ACTIVE:
            return RiskLevel.HIGH

        drawdown = self.calculate_drawdown()
        concentration_risk = 0.0

        if positions:
            total_exposure = sum(abs(v) for v in positions.values())
            if total_exposure > 0:
                max_single = max(abs(v) for v in positions.values())
                concentration_risk = max_single / total_exposure

        correlation_risk = self._calculate_correlation_risk(list(positions.keys()))

        combined_risk = max(concentration_risk, correlation_risk)

        if drawdown >= self.max_drawdown_allowed or combined_risk > 0.50:
            return RiskLevel.CRITICAL
        elif drawdown >= self.max_drawdown_allowed * 0.5 or combined_risk > 0.35:
            return RiskLevel.HIGH
        elif drawdown >= self.max_drawdown_allowed * 0.25 or combined_risk > 0.25:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def update_correlation(self, symbol_a: str, symbol_b: str, correlation: float) -> None:
        if symbol_a not in self._correlation_matrix:
            self._correlation_matrix[symbol_a] = {}
        if symbol_b not in self._correlation_matrix:
            self._correlation_matrix[symbol_b] = {}
        self._correlation_matrix[symbol_a][symbol_b] = correlation
        self._correlation_matrix[symbol_b][symbol_a] = correlation

    def _calculate_correlation_risk(self, symbols: list) -> float:
        if len(symbols) < 2:
            return 0.0
        high_corr_pairs = 0
        total_pairs = 0
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                total_pairs += 1
                corr = self._correlation_matrix.get(symbols[i], {}).get(symbols[j], 0.0)
                if abs(corr) > 0.7:
                    high_corr_pairs += 1
        if total_pairs == 0:
            return 0.0
        return high_corr_pairs / total_pairs

    def get_risk_adjusted_position_size(self, base_quantity: int, risk_level: RiskLevel) -> int:
        """위험 수준 기반 포지션 크기 조정"""
        adjustments = {RiskLevel.LOW: 1.0, RiskLevel.MEDIUM: 0.75, RiskLevel.HIGH: 0.5, RiskLevel.CRITICAL: 0.25}

        multiplier = adjustments.get(risk_level, 0.5) * self.stress_test_adjustment_factor
        adjusted_quantity = int(base_quantity * multiplier)

        self.logger.info(
            f"Position size adjusted from {base_quantity} to {adjusted_quantity} "
            f"(risk level: {risk_level.value}, multiplier: {multiplier})"
        )

        return adjusted_quantity

    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Value at Risk (VaR) 계산"""
        if not returns:
            return 0

        sorted_returns = sorted(returns)
        var_index = int(len(sorted_returns) * (1 - confidence))

        if var_index >= len(sorted_returns):
            var_index = 0

        var = sorted_returns[var_index]
        return var

    def calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        """Conditional Value at Risk (CVaR) 계산"""
        if not returns:
            return 0

        var = self.calculate_var(returns, confidence)
        worse_returns = [r for r in returns if r <= var]

        if not worse_returns:
            return var

        cvar = sum(worse_returns) / len(worse_returns)
        return cvar

    def generate_risk_report(self, positions: Dict[str, float], market_prices: Dict[str, float]) -> RiskMetrics:
        """위험 보고서 생성"""
        # 현재 포지션 가치 계산
        position_value = sum(market_prices.get(symbol, 0) * qty for symbol, qty in positions.items())

        total_value = self.portfolio_value + position_value
        current_drawdown = self.calculate_drawdown()
        risk_level = self.calculate_risk_level(positions)

        high_vol = self.max_drawdown_allowed * 0.75
        low_vol = self.max_drawdown_allowed * 0.5
        portfolio_volatility = high_vol if risk_level == RiskLevel.HIGH else low_vol

        metrics = RiskMetrics(
            current_value=total_value,
            max_loss_limit=self.portfolio_value * self.max_portfolio_loss_pct,
            max_position_size=self.portfolio_value * self.max_position_size_pct * self._volatility_scalar() * self.stress_test_adjustment_factor,
            stop_loss_pct=self.default_stop_loss_pct,
            take_profit_pct=self.default_take_profit_pct,
            current_drawdown=current_drawdown,
            max_drawdown_allowed=self.max_drawdown_allowed,
            portfolio_volatility=portfolio_volatility,
            risk_level=risk_level,
        )

        self.metrics_history.append(metrics)
        self.logger.info(f"Risk report generated: drawdown={current_drawdown:.2%}, level={risk_level.value}")

        return metrics

    def _create_alert(self, alert_type: str, symbol: str, current_price: float, entry_price: float):
        """경고 생성"""
        pnl_pct = ((current_price - entry_price) / entry_price * 100) if (entry_price and entry_price > 0) else 0.0
        alert = {
            "type": alert_type,
            "symbol": symbol,
            "current_price": current_price,
            "entry_price": entry_price,
            "pnl_pct": pnl_pct,
            "timestamp": datetime.now(),
        }

        self.alerts.append(alert)
        self.logger.warning(f"Risk alert: {alert_type} for {symbol} @ {current_price} (entry: {entry_price})")

    def get_active_alerts(self) -> List[Dict]:
        """활성 경고 조회"""
        return self.alerts

    def clear_alerts(self):
        """경고 초기화"""
        self.alerts.clear()
        self.logger.info("Alerts cleared")
