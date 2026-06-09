"""Async Helper - 동기/비동기 연동을 위한 유틸리티"""

import asyncio
import threading
from typing import Coroutine, Any
from concurrent.futures import Future, TimeoutError as FutureTimeoutError


def run_async(coro: Coroutine, timeout: float = 60.0) -> Any:
    """
    실행 중인 이벤트 루프 내부/외부에서 안전하게 비동기 코루틴을 실행하고 결과를 반환하는 헬퍼 함수.
    주로 Flask 등의 동기 컨텍스트에서 비동기 데이터베이스 조회를 안전하게 동기식으로 대기할 때 사용됩니다.

    Args:
        coro: 실행할 코루틴
        timeout: 타임아웃 시간 (초), 기본 60초

    Returns:
        코루틴 실행 결과

    Raises:
        TimeoutError: 타임아웃 발생 시
    """
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
