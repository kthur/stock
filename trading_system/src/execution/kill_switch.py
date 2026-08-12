"""Kill Switch — 실거래 즉시 중단 게이트.

운영자가 트레이딩 시스템을 즉시 정지시킬 수 있는 3중 안전장치:

1. 파일 기반:  프로젝트 루트(``KILL_SWITCH`` 파일)에 ``KILL_SWITCH`` 파일 생성 → 모든 신규 주문 차단.
2. 환경변수:   ``KILL_SWITCH=1`` (또는 true/yes) → 동일 효과.
3. API:        ``kill_switch.engage(reason)`` / ``disengage()`` — 동작 중 프로그래밍 방식 정지.

킬 스위치가 활성화되면:
- ``ExecutionOMSEngine.generate_order_plan`` → 신규 주문 계획 생성 차단
- ``TradeExecutor.execute`` → 매수/매도 신규 실행 차단 (포지션 청산 지시는 ``force_liquidate=True``로만 허용)
- 파이프라인 검증 단계에서 상태 로그 기록

활성화 상태는 ``trading_system/kill_switch_state.json`` 에 기록되어 운영자가 원인을 추적할 수 있다.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # trading_system/
KILL_SWITCH_FILE = _PROJECT_ROOT / "KILL_SWITCH"
STATE_FILE = _PROJECT_ROOT / "kill_switch_state.json"

_TRUTHY = {"1", "true", "yes", "on"}


def _file_engaged() -> bool:
    return KILL_SWITCH_FILE.exists()


def _env_engaged() -> bool:
    val = os.getenv("KILL_SWITCH", "").strip().lower()
    return val in _TRUTHY


def is_kill_switch_active() -> bool:
    """True이면 시스템 전체가 주문을 거부해야 한다."""
    return _file_engaged() or _env_engaged()


def engage(reason: str = "") -> None:
    """프로그래밍 방식으로 킬 스위치를 켠다 (KILL_SWITCH 파일 생성)."""
    KILL_SWITCH_FILE.touch(exist_ok=True)
    _write_state("engaged", reason or "programmatic engage()")
    logger.critical("KILL SWITCH ENGAGED: all order generation/execution blocked. reason=%s", reason)


def disengage() -> None:
    """킬 스위치를 해제한다 (KILL_SWITCH 파일 삭제)."""
    try:
        KILL_SWITCH_FILE.unlink(missing_ok=True)
    except OSError as e:
        logger.warning(f"KILL_SWITCH file removal failed: {e}")
    _write_state("disengaged", "")
    logger.warning("KILL SWITCH DISENGAGED: order generation/execution re-enabled.")


def get_state() -> dict[str, Any]:
    """현재 킬 스위치 상태 딕셔너리."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        logger.debug(f"kill_switch_state read failed: {e}")
    return {}


def _write_state(status: str, reason: str) -> None:
    from datetime import datetime

    try:
        payload = {
            "status": status,
            "reason": reason,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "file": str(KILL_SWITCH_FILE),
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug(f"kill_switch_state write failed: {e}")
