import unittest
from src.utils.indicators import calc_sma, calc_ema_list, calc_ema, calc_macd, calc_rsi, calc_atr


class TestCalcSMA(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(calc_sma([], 5), [])

    def test_basic_sma(self):
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = calc_sma(prices, 3)
        self.assertAlmostEqual(result[2], 2.0)  # (1+2+3)/3
        self.assertAlmostEqual(result[3], 3.0)  # (2+3+4)/3
        self.assertAlmostEqual(result[4], 4.0)  # (3+4+5)/3

    def test_short_data(self):
        prices = [10.0, 20.0]
        result = calc_sma(prices, 5)
        self.assertEqual(len(result), 2)


class TestCalcEMA(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(calc_ema_list([], 5), [])
        self.assertEqual(calc_ema([], 5), 0.0)

    def test_short_data(self):
        prices = [10.0, 20.0]
        result = calc_ema_list(prices, 10)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0], 15.0)
        self.assertAlmostEqual(result[1], 15.0)

    def test_ema_values(self):
        prices = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        ema = calc_ema(prices, 5)
        self.assertGreater(ema, 6.0)  # EMA should follow recent trend
        self.assertLess(ema, 10.0)

    def test_single_ema(self):
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = calc_ema(prices, 3)
        self.assertGreater(result, 30.0)


class TestCalcMACD(unittest.TestCase):
    def test_short_data(self):
        self.assertEqual(calc_macd([1.0, 2.0], 12, 26, 9), 0.0)

    def test_macd_basic(self):
        prices = [float(i) for i in range(40, 100)]
        macd = calc_macd(prices, 12, 26, 9)
        self.assertNotEqual(macd, 0.0)


class TestCalcRSI(unittest.TestCase):
    def test_short_data(self):
        self.assertEqual(calc_rsi([1.0, 2.0], 14), 50.0)

    def test_rsi_oversold(self):
        prices = [100.0, 90.0, 81.0, 73.0, 66.0, 60.0, 55.0, 51.0, 48.0, 46.0,
                  45.0, 44.0, 43.0, 42.0, 41.0]
        rsi = calc_rsi(prices, 14)
        self.assertLess(rsi, 30)  # oversold territory

    def test_rsi_overbought(self):
        prices = [10.0, 20.0, 31.0, 43.0, 56.0, 70.0, 85.0, 96.0, 100.0, 105.0,
                  108.0, 112.0, 115.0, 118.0, 120.0]
        rsi = calc_rsi(prices, 14)
        self.assertGreater(rsi, 70)  # overbought territory


class TestCalcATR(unittest.TestCase):
    def test_short_data(self):
        self.assertEqual(calc_atr([10.0], [9.0], [9.5], 14), 0.0)

    def test_atr_basic(self):
        highs = [10.0, 11.0, 12.0, 11.5, 12.5, 13.0, 12.8, 13.5, 14.0, 13.5,
                 14.5, 15.0, 14.5, 15.5, 16.0]
        lows = [9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 11.8, 12.0, 12.5, 12.0,
                13.0, 13.5, 13.0, 14.0, 14.5]
        closes = [9.5, 10.0, 11.0, 11.0, 12.0, 12.5, 12.3, 13.0, 13.5, 13.0,
                  14.0, 14.5, 14.0, 15.0, 15.5]
        atr = calc_atr(highs, lows, closes, 14)
        self.assertGreater(atr, 0.0)
        self.assertLess(atr, 5.0)


if __name__ == "__main__":
    unittest.main()
