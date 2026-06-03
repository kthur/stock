import asyncio
from typing import Callable, Dict, List, Any
import logging

from .async_helper import run_async

logger = logging.getLogger(__name__)


class EventBus:
    """중앙 집중형 이벤트 버스 (동기 및 비동기 발행/구독 지원)"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self.logger = logger

    def subscribe(self, event_type: str, listener: Callable):
        """이벤트 구독"""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)
            listener_name = listener.__name__ if hasattr(listener, '__name__') else str(listener)
            self.logger.info(f"EventBus: Subscribed listener '{listener_name}' to '{event_type}'")

    def unsubscribe(self, event_type: str, listener: Callable):
        """이벤트 구독 해제"""
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)
            self.logger.info(f"EventBus: Unsubscribed listener from '{event_type}'")

    def publish(self, event_type: str, data: Any):
        """
        이벤트 발행.
        리스너가 비동기 함수(coroutine)인 경우, 실행 중인 이벤트 루프에 비동기 태스크로 예약합니다.
        동기 리스너인 경우 즉시 동기로 실행합니다.
        """
        if event_type not in self._listeners:
            return
        
        for listener in self._listeners[event_type]:
            try:
                if asyncio.iscoroutinefunction(listener):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(listener(data))
                    except RuntimeError:
                        run_async(listener(data))
                else:
                    listener(data)
            except Exception as e:
                self.logger.error(f"EventBus: Error executing listener for event '{event_type}': {e}")
