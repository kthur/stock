# 주식 트레이딩 시스템 전체 개선 플랜

## 생성일: 2025-06-09
## 상태: 승인 대기

---

## Phase 1: 🔴 치명적 버그 수정

### 1-1. EMA200 계산 오류 수정
**파일:** `trading_system/trading_system.py:340-351`

현재 코드 (SMA - 잘못됨):
```python
ema200 = sum(closes) / len(closes)
```

변경할 코드 (진짜 EMA):
```python
ema200 = closes[0]
multiplier = 2 / (200 + 1)
for close in closes[1:]:
    ema200 = close * multiplier + ema200 * (1 - multiplier)
```

동일한 수정이 `lines 457-458` (w_ema20, w_ema50)에도 필요:
```python
# 현재 (SMA)
w_ema20 = sum(weekly_closes[-20:]) / 20
w_ema50 = sum(weekly_closes[-50:]) / 50

# 수정 (EMA)
def _calc_ema(prices, period):
    ema = prices[0]
    multiplier = 2 / (period + 1)
    for p in prices[1:]:
        ema = p * multiplier + ema * (1 - multiplier)
    return ema

w_ema20 = _calc_ema(weekly_closes[-20:], 20)
w_ema50 = _calc_ema(weekly_closes[-50:], 50)
```

---

## Phase 2: 🟠 구조적 안정성

### 2-1. EventBus 스레드 안전성
**파일:** `trading_system/src/utils/event_bus.py`

변경 내용:
- `threading.Lock` 추가하여 `_listeners` 딕셔너리 보호
- `publish` 시 리스너 목록 복사본으로 순회 (변경 차단)
- `_async_tasks` 세트 추가하여 `create_task` 결과 추적

```python
import asyncio
import threading
from typing import Callable, Dict, List, Any
import logging

from .async_helper import run_async

logger = logging.getLogger(__name__)


class EventBus:
    """중앙 집중형 이벤트 버스 (동기 및 비동기 발행/구독 지원)"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._async_tasks: set = set()
        self.logger = logger

    def subscribe(self, event_type: str, listener: Callable):
        """이벤트 구독"""
        with self._lock:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            if listener not in self._listeners[event_type]:
                self._listeners[event_type].append(listener)
                listener_name = listener.__name__ if hasattr(listener, '__name__') else str(listener)
                self.logger.info(f"EventBus: Subscribed listener '{listener_name}' to '{event_type}'")

    def unsubscribe(self, event_type: str, listener: Callable):
        """이벤트 구독 해제"""
        with self._lock:
            if event_type in self._listeners and listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)
                self.logger.info(f"EventBus: Unsubscribed listener from '{event_type}'")

    def publish(self, event_type: str, data: Any):
        """이벤트 발행"""
        with self._lock:
            listeners = list(self._listeners.get(event_type, []))
        
        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    try:
                        loop = asyncio.get_running_loop()
                        task = loop.create_task(listener(data))
                        self._async_tasks.add(task)
                        task.add_done_callback(self._async_tasks.discard)
                    except RuntimeError:
                        run_async(listener(data))
                else:
                    listener(data)
            except Exception as e:
                self.logger.error(f"EventBus: Error executing listener for event '{event_type}': {e}")
```

### 2-2. results_history 메모리 누수 방지
**파일:** `trading_system/src/core/strategy_engine.py`

변경 내용:
- `from collections import deque` 추가
- `results_history`를 `deque(maxlen=1000)`로 변경

```python
from collections import deque

class HybridStrategyEngine:
    MAX_HISTORY = 1000
    
    def __init__(self, ...):
        self.results_history: deque = deque(maxlen=self.MAX_HISTORY)
```

### 2-3. error_history 메모리 누수 방지
**파일:** `trading_system/src/utils/error_handler.py`

변경 내용:
- `from collections import deque` 추가
- `error_history`를 `deque(maxlen=500)`로 변경

```python
from collections import deque

class ErrorHandler:
    MAX_ERROR_HISTORY = 500
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_history: deque = deque(maxlen=self.MAX_ERROR_HISTORY)
```

### 2-4. Database 초기화 레이스 컨디션 수정
**파일:** `trading_system/src/persistence/database.py`

변경 내용:
- `asyncio.Lock` 추가
- Double-check 패턴 적용

TradeLogger, AssetHistoryDB, AIPredictionDB 모두에 적용:

```python
import asyncio

class TradeLogger:
    def __init__(self, db_path: str = "trade_logs.db"):
        self.db_path = Path(db_path)
        self.logger = logger
        self._db_initialized = False
        self._init_lock = asyncio.Lock()
        self._conn_mgr = _DBConnection(self.db_path)
    
    async def _init_database(self):
        if self._db_initialized:
            return
        async with self._init_lock:
            if self._db_initialized:  # double-check
                return
            conn = await self._get_conn()
            cursor = await conn.cursor()
            # ... 기존 테이블 생성 로직 ...
            await conn.commit()
            self._db_initialized = True
```

---

## Phase 3: 🟡 성능 및 품질

### 3-1. config.py 개선
**파일:** `trading_system/src/config.py`

변경 내용:
- `debug_mode` 기본값을 `False`로 변경
- `parsed_authorized_user_ids` 캐싱 (property 대신 인스턴스 변수)
- API 키 검증 로그 추가

```python
from dataclasses import dataclass, field

@dataclass
class TradingConfig:
    initial_cash: float = 1000000.0
    max_retries: int = 3
    debug_mode: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_authorized_user_ids: str = os.getenv("TELEGRAM_AUTHORIZED_USER_IDS", "")
    
    _parsed_authorized_user_ids: list = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        self._parsed_authorized_user_ids = self._parse_authorized_ids()

    def _parse_authorized_ids(self) -> list:
        if not self.telegram_authorized_user_ids.strip():
            return []
        try:
            return [int(uid.strip()) for uid in self.telegram_authorized_user_ids.split(",") if uid.strip()]
        except ValueError:
            return []

    @property
    def parsed_authorized_user_ids(self) -> list:
        return self._parsed_authorized_user_ids

    def validate(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError(f"initial_cash must be positive: {self.initial_cash}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative: {self.max_retries}")
```

### 3-2. async_helper.py 타임아웃 개선
**파일:** `trading_system/src/utils/async_helper.py`

변경 내용:
- 타임아웃 값을 파라미터로 받도록 변경
- `TimeoutError` catch 추가

```python
from concurrent.futures import Future, TimeoutError as FutureTimeoutError

def run_async(coro: Coroutine, timeout: float = 60.0) -> Any:
    """실행 중인 이벤트 루프 내부/외부에서 안전하게 비동기 코루틴을 실행"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    
    if loop.is_running():
        future: Future = Future()
        
        def run_in_thread():
            try:
                res = asyncio.run(coro)
                future.set_result(res)
            except Exception as e:
                future.set_exception(e)
                
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            raise TimeoutError(f"async operation timed out after {timeout}s")
    else:
        return loop.run_until_complete(coro)
```

---

## Phase 4: 🟢 테스트 (나중에 구현)

### 신규 테스트 파일
- `tests/test_event_bus.py`
- `tests/test_database.py`
- `tests/test_async_helper.py`
- `tests/test_llm_integration.py`
- `tests/test_market_data_handler.py`

### 보강 테스트
- `tests/test_order_management.py`
- `tests/test_strategy_engine.py`

---

## Phase 5: 🔵 정리 (나중에 구현)

### 죽은 코드 정리
- `bot_engine.py`: `_cmd_news`, `_cmd_analyze`, `_cmd_connect` 실제 데이터 연동
- `strategy_engine.py`: `price_threshold` 변수 제거

### 의존성 고정
**파일:** `pyproject.toml`, `requirements.txt`
- `torch>=2.0.0,<3.0.0`
- `transformers>=4.30.0,<5.0.0`
- `dash>=2.14.0,<3.0.0`
- `reportlab>=4.0.0,<5.0.0`

### CI 개선
**파일:** `.github/workflows/test.yml`
- `actions/checkout@v4`, `actions/setup-python@v5` 업그레이드
- Python 3.11, 3.12 매트릭스 테스트 추가
- `pip install` 캐싱 추가

---

## 실행 순서

| Phase | 내용 | 예상 파일 수 |
|-------|------|-------------|
| Phase 1 | 치명적 버그 | 1개 |
| Phase 2 | 구조적 안정성 | 4개 |
| Phase 3 | 성능/품질 | 2개 |
| Phase 4 | 테스트 | 7개 |
| Phase 5 | 정리/최적화 | 6개 |

**총 변경 파일:** 약 20개
