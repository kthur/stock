"""Async Helper - 동기/비동기 연동을 위한 유틸리티"""

import asyncio
import threading
from typing import Coroutine, Any


def run_async(coro: Coroutine) -> Any:
    """
    실행 중인 이벤트 루프 내부/외부에서 안전하게 비동기 코루틴을 실행하고 결과를 반환하는 헬퍼 함수.
    주로 Flask 등의 동기 컨텍스트에서 비동기 데이터베이스 조회를 안전하게 동기식으로 대기할 때 사용됩니다.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 실행 중인 이벤트 루프가 없는 경우 새 루프를 생성해 실행
        return asyncio.run(coro)
    
    if loop.is_running():
        # 실행 중인 루프가 있는 경우 (예: asyncio 애플리케이션 내의 동기 호출)
        # 같은 스레드에서 run_until_complete를 수행하면 RuntimeError가 발생하므로,
        # 새로운 스레드에서 이벤트 루프를 열어 실행하고 대기합니다.
        from concurrent.futures import Future
        
        future = Future()
        
        def run_in_thread():
            try:
                res = asyncio.run(coro)
                future.set_result(res)
            except Exception as e:
                future.set_exception(e)
                
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        return future.result(timeout=60)
    else:
        return loop.run_until_complete(coro)
