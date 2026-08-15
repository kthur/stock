"""Market session hours - KRX / US 정규장·프리마켓 시간 판별 (KST 기준).

KRX   : 09:00 ~ 15:30 KST (Mon-Fri)
NYSE  : 22:30 ~ 05:00 KST (Mon-Fri, KST 자정 넘김)  (DST: 21:30 ~ 04:00)
키움 실매매는 KRX 정규장에만 가능하므로 US는 감시·알림 전용으로 분리.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, time

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MarketSession:
    market: str
    is_open: bool
    is_krx_trading: bool  # 키움 실매매 가능 여부
    next_action: str = ""

    @property
    def label(self) -> str:
        if self.is_open:
            return "OPEN" if not self.is_krx_trading else "KRX_TRADING"
        return "CLOSED"


def _is_weekday_kst(now: datetime) -> bool:
    # KST 기준 평일이지만 US는 KST 금요일 새벽 = US 목요일 장중임을 별도 처리
    return now.weekday() < 5


def is_krx_open(now: datetime) -> bool:
    """KRX 정규장 여부 (09:00 ~ 15:30 KST, 평일)."""
    if not _is_weekday_kst(now):
        return False
    t = now.time()
    return time(9, 0) <= t <= time(15, 30)


def is_us_open(now: datetime) -> bool:
    """US 정규장 여부 (22:30 ~ 05:00 KST, 평일 새벽 구간 포함)."""
    t = now.time()
    if time(22, 30) <= t <= time(23, 59):
        # KST 월~금 저녁 22:30~23:59 = US 월~금 당일 개장 (정규장)
        return _is_weekday_kst(now)
    if time(0, 0) <= t <= time(5, 0):
        # KST 화~토 새벽 00:00~05:00 = US 월~금 정규장 후반부
        # KST 월요일 새벽 = US 일요일 (휴장)
        # KST 일요일 새벽 = US 토요일 (휴장)
        return now.weekday() in (1, 2, 3, 4, 5)
    return False


def get_session(now: datetime | None = None) -> MarketSession:
    """현재 시각의 시장 세션 판별."""
    now = now or datetime.now()
    krx_open = is_krx_open(now)
    us_open = is_us_open(now)

    if krx_open:
        return MarketSession(market="KRX", is_open=True, is_krx_trading=True,
                             next_action="KRX 정규장 — 키움 실매매 가능")
    if us_open:
        return MarketSession(market="US", is_open=True, is_krx_trading=False,
                             next_action="US 장중 — 감시/알림 전용 (키움 실매매 불가)")
    return MarketSession(market="CLOSED", is_open=False, is_krx_trading=False,
                         next_action="장 마감 — 실시간 모니터링 대기")
