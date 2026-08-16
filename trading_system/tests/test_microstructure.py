"""
test_microstructure.py — Unit tests for Microstructure Cost Model
"""

import unittest
from src.risk.microstructure import MicrostructureCostModel


class TestMicrostructureCostModel(unittest.TestCase):

    def setUp(self):
        self.model = MicrostructureCostModel()

    def test_tax_fee_rates(self):
        # KRX buy vs sell: buy = brokerage fee only, sell = STT + brokerage fee
        self.assertAlmostEqual(self.model.get_tax_fee_rate("KOSPI", is_sell=False), self.model.cfg.brokerage_fee_rate)
        self.assertAlmostEqual(self.model.get_tax_fee_rate("KOSPI", is_sell=True), self.model.cfg.kospi_stt_rate + self.model.cfg.brokerage_fee_rate)

        # US sell: SEC fee + US brokerage fee
        self.assertAlmostEqual(self.model.get_tax_fee_rate("SP500", is_sell=True), 0.0000278 + 0.00005)

    def test_net_expected_return(self):
        gross_return = 0.05  # +5.0%
        net = self.model.net_expected_return(
            gross_return=gross_return,
            symbol="005930",
            market="KOSPI",
            price=70000.0,
            volatility=0.20,
            order_amount=1000000.0,
            adv=50000000.0
        )
        self.assertLess(net, gross_return)
        self.assertGreater(net, 0.04)


if __name__ == "__main__":
    unittest.main()
