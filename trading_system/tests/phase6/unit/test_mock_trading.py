"""Mock Trading 연동 단위 테스트 (모의투자 구현 계획서 영역)
dash 미설치 환경에서도 동작하도록 trading_system 직접 임포트 회피"""

import unittest
from unittest.mock import MagicMock, patch
from typing import Dict, List
import sys

from src.core.order_management import OrderManagementSystem, OrderType, OrderStatus, Order
from src.config import TradingConfig


class TestMockTradingConfig(unittest.TestCase):
    """TradingConfig 모의투자 설정 테스트"""

    def test_mock_trading_default_true(self):
        """mock_trading 기본값이 True인지 확인"""
        config = TradingConfig()
        self.assertTrue(config.mock_trading)

    @patch.dict("os.environ", {"KIS_MOCK_APP_KEY": "", "KIS_MOCK_APP_SECRET": "", "KIS_MOCK_ACCOUNT": ""})
    @patch("src.config.os.getenv")
    def test_kis_mock_keys_default_empty(self, mock_getenv):
        """KIS 모의투자 키 기본값이 빈 문자열인지 확인"""
        mock_getenv.side_effect = lambda k, d="": "" if k in ["KIS_MOCK_APP_KEY", "KIS_MOCK_APP_SECRET", "KIS_MOCK_ACCOUNT"] else os.getenv(k, d)
        config = TradingConfig()
        self.assertEqual(config.kis_mock_app_key, "")
        self.assertEqual(config.kis_mock_app_secret, "")
        self.assertEqual(config.kis_mock_account, "")


class TestOrderBrokerOrderId(unittest.TestCase):
    """Order.broker_order_id 필드 테스트"""

    def test_broker_order_id_default_empty(self):
        """broker_order_id 기본값이 빈 문자열인지 확인"""
        order = Order(symbol="AAPL", order_type=OrderType.BUY, quantity=10, price=150.0)
        self.assertEqual(order.broker_order_id, "")

    def test_broker_order_id_set_and_get(self):
        """broker_order_id 설정/조회"""
        order = Order(symbol="AAPL", order_type=OrderType.BUY, quantity=10, price=150.0)
        order.broker_order_id = "MOCK-12345"
        self.assertEqual(order.broker_order_id, "MOCK-12345")


class TestNormalizeHoldings(unittest.TestCase):
    """normalize_holdings 정규화 테스트"""

    def setUp(self):
        from src.broker.utils import normalize_holdings
        self.normalize = normalize_holdings

    def test_normalize_list_of_dicts(self):
        """List[Dict] 입력 정규화"""
        raw = [
            {"symbol": "005930", "qty": 10},
            {"symbol": "000660", "qty": 5},
        ]
        result = self.normalize(raw)
        self.assertEqual(result, {"005930": 10, "000660": 5})

    def test_normalize_dict_of_int(self):
        """Dict[str, int] 입력 정규화"""
        raw = {"005930": 10, "000660": 5}
        result = self.normalize(raw)
        self.assertEqual(result, raw)

    def test_normalize_dict_of_dicts(self):
        """Dict[str, Dict] 입력 정규화"""
        raw = {
            "005930": {"qty": 10, "price": 50000},
            "000660": {"quantity": 5, "price": 100000},
        }
        result = self.normalize(raw)
        self.assertEqual(result, {"005930": 10, "000660": 5})

    def test_normalize_empty(self):
        """빈 입력 처리"""
        self.assertEqual(self.normalize({}), {})
        self.assertEqual(self.normalize([]), {})


class TestMockOrderCreation(unittest.TestCase):
    """모의투자 주문 생성 및 broker_order_id 매핑 테스트"""

    def setUp(self):
        self.oms = OrderManagementSystem()

    def test_order_created_with_broker_id(self):
        """주문 생성 후 broker_order_id 매핑"""
        order = self.oms.create_order("AAPL", OrderType.BUY, 10, 150.0)
        order.broker_order_id = "BROKER-TEST-001"
        self.assertEqual(order.broker_order_id, "BROKER-TEST-001")
        self.assertIn(order.order_id, self.oms.orders)

    def test_unfilled_orders_filter(self):
        """미체결 주문 중 broker_order_id 있는 것만 필터링"""
        o1 = self.oms.create_order("AAPL", OrderType.BUY, 10, 150.0)
        o1.broker_order_id = "BID-001"
        o2 = self.oms.create_order("MSFT", OrderType.BUY, 5, 300.0)
        o2.broker_order_id = ""

        unfilled = self.oms.get_unfilled_orders()
        with_broker_ids = [o for o in unfilled if o.broker_order_id]
        self.assertEqual(len(with_broker_ids), 1)
        self.assertEqual(with_broker_ids[0].symbol, "AAPL")

    def test_mock_trading_config_creates_order_with_signal_name(self):
        """signal_name을 포함한 주문 생성"""
        order = self.oms.create_order("AAPL", OrderType.BUY, 10, 150.0, "mock_strategy")
        self.assertEqual(order.signal_name, "mock_strategy")


if __name__ == "__main__":
    unittest.main()
