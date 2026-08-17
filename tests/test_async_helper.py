import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.async_helper import run_async


class TestRunAsync(unittest.TestCase):
    """run_async 헬퍼 함수 테스트"""

    def test_simple_async(self):
        """기본 비동기 함수 실행"""
        async def add(a, b):
            return a + b

        result = run_async(add(1, 2))
        self.assertEqual(result, 3)

    def test_string_operation(self):
        """문자열 비동기 연산"""
        async def concat(a, b):
            return a + b

        result = run_async(concat("hello", " world"))
        self.assertEqual(result, "hello world")

    def test_list_result(self):
        """리스트 결과 반환"""
        async def get_list():
            return [1, 2, 3]

        result = run_async(get_list())
        self.assertEqual(result, [1, 2, 3])

    def test_dict_result(self):
        """딕셔너리 결과 반환"""
        async def get_dict():
            return {"key": "value"}

        result = run_async(get_dict())
        self.assertEqual(result, {"key": "value"})

    def test_nested_async(self):
        """중첩 비동기 호출"""
        async def inner():
            return 42

        async def outer():
            return await inner()

        result = run_async(outer())
        self.assertEqual(result, 42)

    def test_custom_timeout(self):
        """커스텀 타임아웃 파라미터"""
        async def quick():
            return "done"

        result = run_async(quick(), timeout=10.0)
        self.assertEqual(result, "done")


if __name__ == "__main__":
    unittest.main()
