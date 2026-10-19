import asyncio
import logging
import threading
from typing import Any, Callable, Dict, List

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
        if listener is None:
            return
        event_name = str(event_type) if event_type is not None else ""
        with self._lock:
            if event_name not in self._listeners:
                self._listeners[event_name] = []
            if listener not in self._listeners[event_name]:
                self._listeners[event_name].append(listener)
                listener_name = listener.__name__ if hasattr(listener, "__name__") else str(listener)
                self.logger.info(f"EventBus: Subscribed listener '{listener_name}' to '{event_name}'")

    def unsubscribe(self, event_type: str, listener: Callable):
        """이벤트 구독 해제"""
        if listener is None:
            return
        event_name = str(event_type) if event_type is not None else ""
        with self._lock:
            if event_name in self._listeners and listener in self._listeners[event_name]:
                self._listeners[event_name].remove(listener)
                self.logger.info(f"EventBus: Unsubscribed listener from '{event_name}'")

    def publish(self, event_type: str, data: Any):
        """
        이벤트 발행.
        리스너가 비동기 함수(coroutine)인 경우, 실행 중인 이벤트 루프에 비동기 태스크로 예약합니다.
        동기 리스너인 경우 즉시 동기로 실행합니다.
        """
        event_name = str(event_type) if event_type is not None else ""
        with self._lock:
            if event_name not in self._listeners:
                return
            listeners = list(self._listeners[event_name])

        for listener in listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    try:
                        loop = asyncio.get_running_loop()
                        task = loop.create_task(listener(data))
                        with self._lock:
                            self._async_tasks.add(task)

                        def _cleanup(t):
                            with self._lock:
                                self._async_tasks.discard(t)

                        task.add_done_callback(_cleanup)
                    except RuntimeError:
                        run_async(listener(data))
                else:
                    listener(data)
            except Exception as e:
                self.logger.error(f"EventBus: Error executing listener for event '{event_name}': {e}")
