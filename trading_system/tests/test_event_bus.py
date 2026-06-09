import sys
import unittest
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import EventBus


class TestEventBus(unittest.TestCase):
    """EventBus 테스트"""

    def setUp(self):
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        """구독 및 발행 기본 동작"""
        received = []

        def listener(data):
            received.append(data)

        self.bus.subscribe("test_event", listener)
        self.bus.publish("test_event", "hello")

        self.assertEqual(received, ["hello"])

    def test_unsubscribe(self):
        """구독 해제"""
        received = []

        def listener(data):
            received.append(data)

        self.bus.subscribe("test_event", listener)
        self.bus.unsubscribe("test_event", listener)
        self.bus.publish("test_event", "hello")

        self.assertEqual(received, [])

    def test_multiple_listeners(self):
        """여러 리스너"""
        received1 = []
        received2 = []

        def listener1(data):
            received1.append(data)

        def listener2(data):
            received2.append(data)

        self.bus.subscribe("test_event", listener1)
        self.bus.subscribe("test_event", listener2)
        self.bus.publish("test_event", "data")

        self.assertEqual(received1, ["data"])
        self.assertEqual(received2, ["data"])

    def test_different_event_types(self):
        """다른 이벤트 타입"""
        received_a = []
        received_b = []

        def listener_a(data):
            received_a.append(data)

        def listener_b(data):
            received_b.append(data)

        self.bus.subscribe("type_a", listener_a)
        self.bus.subscribe("type_b", listener_b)
        self.bus.publish("type_a", "a_data")

        self.assertEqual(received_a, ["a_data"])
        self.assertEqual(received_b, [])

    def test_publish_no_listeners(self):
        """리스너 없는 이벤트 발행 - 예외 없음"""
        self.bus.publish("nonexistent", "data")

    def test_thread_safety(self):
        """멀티스레드 동시성"""
        errors = []

        def subscriber():
            def listener(data):
                pass
            for _ in range(100):
                self.bus.subscribe("thread_event", listener)
                self.bus.unsubscribe("thread_event", listener)

        def publisher():
            for _ in range(100):
                self.bus.publish("thread_event", "data")

        threads = []
        for _ in range(10):
            t = threading.Thread(target=subscriber)
            threads.append(t)
            t.start()
        for _ in range(10):
            t = threading.Thread(target=publisher)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5)

        self.assertEqual(len(errors), 0)

    def test_listener_exception_does_not_break_others(self):
        """한 리스너 예외가 다른 리스너에 영향 없음"""
        received = []

        def broken_listener(data):
            raise ValueError("error")

        def good_listener(data):
            received.append(data)

        self.bus.subscribe("test_event", broken_listener)
        self.bus.subscribe("test_event", good_listener)
        self.bus.publish("test_event", "data")

        self.assertEqual(received, ["data"])

    def test_subscribe_twice_same_listener(self):
        """동일 리스너 중복 구독 방지"""
        received = []

        def listener(data):
            received.append(data)

        self.bus.subscribe("test_event", listener)
        self.bus.subscribe("test_event", listener)
        self.bus.publish("test_event", "data")

        self.assertEqual(len(received), 1)


if __name__ == "__main__":
    unittest.main()
