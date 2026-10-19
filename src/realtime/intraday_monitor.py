"""IntradayMonitor - 장중 실시간 리스크·시그널 보정 엔진.

입력: 15분 간격 폴링 시세(RealtimeQuote) + 일봉 기반 워치리스트(ensemble 신호)
출력: 손절/익절/시그널 다운그레이드/매크로 경보 액션.

핵심 규칙
- 손절  : 진입가 대비 하락 임계값(기본 -4%) 또는 IntradayStopLossEngine 트리거
- 익절  : 진입가 대비 상승 임계값(기본 +8%)
- 보정  : 신호(예상수익률)와 장중 방향이 크게 반대이면 시그널 다운그레이드
- 매크로: 실시간 VIX/USDKRW가 위기 임계를 넘으면 전체 다운그레이드
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from src.realtime.state_store import RealtimeStateStore

logger = logging.getLogger(__name__)


@dataclass
class WatchItem:
    symbol: str
    market: str
    entry_price: float = 0.0          # 진입가 (0이면 진입 없음 = 시그널 후보만)
    position_qty: int = 0             # 보유 수량
    stop_loss_pct: float = -0.04      # 진입 대비 손절 임계 (기본 -4%)
    take_profit_pct: float = 0.08     # 진입 대비 익절 임계 (기본 +8%)
    expected_return: float = 0.0      # 일봉 ensemble 예상 수익률 (0.05 = +5%)
    ensemble_score: float = 0.0       # 일봉 ensemble 스코어
    name: str = ""
    entry_score: float = 0.0          # 진입 시점 ensemble 스코어
    current_score: float = 0.0        # 현재 시점 ensemble 스코어
    days_held: int = 0                # 보유 거래일 수
    sleeve_type: str = "CORE"         # FAST | CORE


@dataclass
class MonitorAction:
    symbol: str
    action_type: str  # STOP_LOSS | TAKE_PROFIT | SIGNAL_DOWNGRADE | MACRO_ALERT | POSITION_OPEN | ALPHA_DECAY_EXIT | TIME_STOP_EXIT
    reason: str
    price: float = 0.0
    drop_pct: float = 0.0
    severity: str = "INFO"  # INFO | WARN | CRITICAL
    detail: str = ""

    def __post_init__(self):
        if self.action_type in ("STOP_LOSS", "MACRO_ALERT"):
            self.severity = "CRITICAL"
        elif self.action_type in ("SIGNAL_DOWNGRADE", "ALPHA_DECAY_EXIT"):
            self.severity = "WARN"
        elif self.action_type == "TIME_STOP_EXIT":
            self.severity = "INFO"


class IntradayMonitor:
    def __init__(
        self,
        stop_loss_pct: float = -0.04,
        take_profit_pct: float = 0.08,
        signal_reversal_threshold: float = -0.03,   # 예상수익률 대비 장중 역행 허용치
        macro_vix_threshold: float = 28.0,
        macro_usdkrw_threshold: float = 1450.0,
        state_store: Optional[RealtimeStateStore] = None,
        intraday_engine=None,
        crisis_detector=None,
    ):
        import math
        try:
            safe_sl = float(stop_loss_pct) if (stop_loss_pct is not None and math.isfinite(float(stop_loss_pct))) else -0.04
        except (ValueError, TypeError):
            safe_sl = -0.04
        self.stop_loss_pct = min(-0.001, max(-0.50, safe_sl))

        try:
            safe_tp = float(take_profit_pct) if (take_profit_pct is not None and math.isfinite(float(take_profit_pct))) else 0.08
        except (ValueError, TypeError):
            safe_tp = 0.08
        self.take_profit_pct = max(0.001, min(2.0, safe_tp))

        try:
            safe_rev = float(signal_reversal_threshold) if (signal_reversal_threshold is not None and math.isfinite(float(signal_reversal_threshold))) else -0.03
        except (ValueError, TypeError):
            safe_rev = -0.03
        self.signal_reversal_threshold = min(-0.001, max(-0.50, safe_rev))

        try:
            safe_vix = float(macro_vix_threshold) if (macro_vix_threshold is not None and math.isfinite(float(macro_vix_threshold))) else 28.0
        except (ValueError, TypeError):
            safe_vix = 28.0
        self.macro_vix_threshold = max(5.0, min(100.0, safe_vix))

        try:
            safe_usd = float(macro_usdkrw_threshold) if (macro_usdkrw_threshold is not None and math.isfinite(float(macro_usdkrw_threshold))) else 1450.0
        except (ValueError, TypeError):
            safe_usd = 1450.0
        self.macro_usdkrw_threshold = max(500.0, min(3000.0, safe_usd))

        self.state_store = state_store or RealtimeStateStore()
        self.intraday_engine = intraday_engine  # IntradayStopLossEngine (재사용)
        self.crisis_detector = crisis_detector  # CrisisDetector (재사용)

    # ── 매크로 위험 평가 ────────────────────────────────────────────────
    def evaluate_macro(self, vix: Optional[float], usdkrw: Optional[float]) -> Optional[MonitorAction]:
        """실시간 VIX/USDKRW 위험 경보. 위험 시 시그널 다운그레이드 전역 적용."""
        reasons = []
        if vix is not None and vix > self.macro_vix_threshold:
            reasons.append(f"VIX={vix:.1f} > {self.macro_vix_threshold}")
        if usdkrw is not None and usdkrw > self.macro_usdkrw_threshold:
            reasons.append(f"USD/KRW={usdkrw:.0f} > {self.macro_usdkrw_threshold}")

        # CrisisDetector 재사용: 활성 위기 단계면 경보
        if self.crisis_detector is not None:
            try:
                level = self.crisis_detector.evaluate(
                    vix=vix if vix is not None else 20.0,
                    usdkrw=usdkrw,
                )
                if getattr(level, "value", "") in ("ACTIVE", "SEVERE"):
                    reasons.append(f"CrisisLevel={getattr(level, 'value', '')}")
            except Exception as e:
                logger.debug(f"[MONITOR] crisis detector eval failed: {e}")

        if reasons:
            return MonitorAction(
                symbol="__MARKET__",
                action_type="MACRO_ALERT",
                reason="; ".join(reasons),
                severity="CRITICAL",
            )
        return None

    # ── 단일 종목 평가 ──────────────────────────────────────────────────
    def evaluate_symbol(
        self,
        item: WatchItem,
        quote_price: float,
        date: str,
        volume: float = 0.0,
        volume_ma20: float = 0.0,
        force_alert: bool = False,
    ) -> List[MonitorAction]:
        import math
        actions: List[MonitorAction] = []
        try:
            qp = float(quote_price) if (quote_price is not None and math.isfinite(float(quote_price))) else 0.0
        except (ValueError, TypeError):
            qp = 0.0

        if qp <= 0:
            return actions

        try:
            vol = float(volume) if (volume is not None and math.isfinite(float(volume))) else 0.0
            vol_ma = float(volume_ma20) if (volume_ma20 is not None and math.isfinite(float(volume_ma20))) else 0.0
        except (ValueError, TypeError):
            vol, vol_ma = 0.0, 0.0

        state = self.state_store.get_state(item.symbol, date)
        open_initialized = False
        if state.open_price <= 0:
            state.open_price = qp
            state.peak_price = qp
            state.low_price = qp
            open_initialized = True

        # 고점/저점 갱신
        state.peak_price = max(state.peak_price, qp)
        state.low_price = min(state.low_price if state.low_price > 0 else qp, qp)

        # 1) 손절: 진입가 대비 하락
        if not state.stop_triggered and item.entry_price > 0 and item.position_qty > 0:
            drop_pct = (qp - item.entry_price) / item.entry_price
            if math.isfinite(drop_pct) and drop_pct <= self.stop_loss_pct:
                state.stop_triggered = True
                state.stop_reasons = f"ENTRY_DROP {drop_pct*100:.1f}%"
                actions.append(MonitorAction(
                    symbol=item.symbol, action_type="STOP_LOSS",
                    reason=f"진입 대비 {drop_pct*100:.1f}% 하락 (임계 {self.stop_loss_pct*100:.0f}%)",
                    price=qp, drop_pct=drop_pct,
                ))

        # 2) 익절: 진입가 대비 상승
        if not state.take_profit_triggered and item.entry_price > 0 and item.position_qty > 0:
            gain_pct = (qp - item.entry_price) / item.entry_price
            if math.isfinite(gain_pct) and gain_pct >= self.take_profit_pct:
                state.take_profit_triggered = True
                actions.append(MonitorAction(
                    symbol=item.symbol, action_type="TAKE_PROFIT",
                    reason=f"진입 대비 {gain_pct*100:.1f}% 상승 (임계 {self.take_profit_pct*100:.0f}%)",
                    price=qp, drop_pct=gain_pct,
                ))

        # 3) IntradayStopLossEngine 재사용 (마이크로구조: ATR 트레일링/패닉 볼륨)
        if self.intraday_engine is not None and not state.stop_triggered:
            try:
                res = self.intraday_engine.evaluate(item.symbol, {
                    "current_price": qp,
                    "volume": vol,
                    "volume_ma_20": vol_ma,
                    "prev_price": qp,  # 15분 폴링이므로 이전 틱 대비로 단순화
                })
                if res.triggered:
                    state.stop_triggered = True
                    state.stop_reasons = res.reason
                    actions.append(MonitorAction(
                        symbol=item.symbol, action_type="STOP_LOSS",
                        reason=f"인트라데이 스탑: {res.reason}",
                        price=qp, drop_pct=res.drop_pct,
                    ))
            except Exception as e:
                logger.debug(f"[MONITOR] intraday engine failed for {item.symbol}: {e}")

        # 4) 시그널 보정: 예상수익률과 장중 방향 역행
        if (not state.stop_triggered and not state.signal_downgraded
                and item.expected_return > 0.0 and item.entry_price <= 0):
            # 매수 신호 종목이 장중 크게 이탈했으면 다운그레이드
            if state.open_price > 0:
                intraday_ret = (qp - state.open_price) / state.open_price
                if math.isfinite(intraday_ret) and intraday_ret <= self.signal_reversal_threshold:
                    state.signal_downgraded = True
                    actions.append(MonitorAction(
                        symbol=item.symbol, action_type="SIGNAL_DOWNGRADE",
                        reason=f"장중 {intraday_ret*100:.1f}% 하락 (시가 대비) — 매수 신호 다운그레이드",
                        price=qp, drop_pct=intraday_ret,
                    ))

        # 5) 알파 감쇠 선제 청산 (Alpha Decay Soft Exit): 앙상블 스코어 급락 (-30% 이상)
        if not state.stop_triggered and item.entry_price > 0 and item.position_qty > 0:
            eff_entry_score = item.entry_score if item.entry_score > 0 else item.ensemble_score
            if eff_entry_score > 0 and item.current_score > 0:
                if item.current_score < eff_entry_score * 0.70:
                    drop_pct = (qp - item.entry_price) / item.entry_price
                    actions.append(MonitorAction(
                        symbol=item.symbol, action_type="ALPHA_DECAY_EXIT",
                        reason=f"알파 스코어 30% 이상 급락 ({eff_entry_score:.2f} -> {item.current_score:.2f}) — 선제적 Soft Exit",
                        price=qp, drop_pct=drop_pct, severity="WARN"
                    ))

        # 6) 시간 손절 (Time-Stop Exit): 반감기 초과 유휴 자본 회수
        if not state.stop_triggered and item.entry_price > 0 and item.position_qty > 0 and item.days_held > 0:
            gain_pct = (qp - item.entry_price) / item.entry_price
            is_fast = str(item.sleeve_type).upper().startswith("FAST")
            if is_fast and item.days_held >= 5 and gain_pct < 0.03:
                actions.append(MonitorAction(
                    symbol=item.symbol, action_type="TIME_STOP_EXIT",
                    reason=f"Fast 슬리브 5일 시간 손절 (수익률 {gain_pct*100:.1f}% 미달) — 기회비용 회수 청산",
                    price=qp, drop_pct=gain_pct, severity="INFO"
                ))
            elif (not is_fast) and item.days_held >= 30 and gain_pct < 0.05:
                actions.append(MonitorAction(
                    symbol=item.symbol, action_type="TIME_STOP_EXIT",
                    reason=f"Core 슬리브 30일 시간 손절 (수익률 {gain_pct*100:.1f}% 미달) — 기회비용 회수 청산",
                    price=qp, drop_pct=gain_pct, severity="INFO"
                ))

        state.updated_at = datetime.now().isoformat(timespec="seconds")
        if force_alert or actions or open_initialized:
            self.state_store.update_state(state)
            for act in actions:
                self.state_store.log_event(date, item.symbol, act.action_type, act.reason, act.detail)
        return actions

    # ── 배치 평가 ───────────────────────────────────────────────────────
    def evaluate_batch(
        self,
        items: List[WatchItem],
        quotes: Dict[str, float],
        date: str,
        volumes: Optional[Dict[str, float]] = None,
        volume_ma20s: Optional[Dict[str, float]] = None,
        vix: Optional[float] = None,
        usdkrw: Optional[float] = None,
    ) -> List[MonitorAction]:
        volumes = volumes or {}
        volume_ma20s = volume_ma20s or {}
        all_actions: List[MonitorAction] = []

        macro_alert = self.evaluate_macro(vix, usdkrw)
        if macro_alert:
            all_actions.append(macro_alert)

        for item in items:
            price = quotes.get(item.symbol)
            if price is None or price <= 0:
                continue
            actions = self.evaluate_symbol(
                item, price, date,
                volume=volumes.get(item.symbol, 0.0),
                volume_ma20=volume_ma20s.get(item.symbol, 0.0),
            )
            all_actions.extend(actions)

        return all_actions

    def build_watch_items(
        self,
        symbols: List[str],
        market_of: Dict[str, str],
        expected_returns: Optional[Dict[str, float]] = None,
        scores: Optional[Dict[str, float]] = None,
        entry_prices: Optional[Dict[str, float]] = None,
        quantities: Optional[Dict[str, int]] = None,
        names: Optional[Dict[str, str]] = None,
    ) -> List[WatchItem]:
        items = []
        for sym in symbols:
            items.append(WatchItem(
                symbol=sym,
                market=market_of.get(sym, "KOSPI"),
                entry_price=float((entry_prices or {}).get(sym, 0.0) or 0.0),
                position_qty=int((quantities or {}).get(sym, 0) or 0),
                expected_return=float((expected_returns or {}).get(sym, 0.0) or 0.0),
                ensemble_score=float((scores or {}).get(sym, 0.0) or 0.0),
                name=(names or {}).get(sym, sym),
            ))
        return items
