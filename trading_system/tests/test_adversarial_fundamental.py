import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.prediction_model import OnDevicePredictionModel, FALLBACK_METADATA

class TestAdversarialFundamental(unittest.TestCase):
    """
    Adversarial and stress tests for fundamental feature calculations and ML models.
    
    ⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
    DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
    """

    def setUp(self):
        self.model = OnDevicePredictionModel()
        self.length = 350  # Must be > max_horizon (200) + max_feature_window (60)
        self.dates = pd.date_range("2026-01-01", periods=self.length)

    def test_feature_calculations_under_extreme_edge_conditions(self):
        """
        Verify feature calculations under edge conditions:
        - Zero / NaN / Inf values for revenue, operating income, dividends, and Close.
        - Extreme out-of-bound metrics (overflow and underflow limits).
        """
        df_base = pd.DataFrame({
            "Close": [100.0] * self.length,
            "Open": [100.0] * self.length,
            "High": [101.0] * self.length,
            "Low": [99.0] * self.length,
            "Volume": [1000.0] * self.length,
            "shares_outstanding": [1000000.0] * self.length,
            "floating_shares": [800000.0] * self.length,
            "revenue": [1000000.0] * self.length,
            "operating_income": [200000.0] * self.length,
            "dividend_per_share": [1.5] * self.length
        }, index=self.dates)

        scenarios = [
            # 1. Zero values
            {"revenue": 0.0, "operating_income": 0.0, "dividend_per_share": 0.0, "Close": 100.0},
            {"revenue": 1000000.0, "operating_income": 0.0, "dividend_per_share": 0.0, "Close": 0.0},
            # 2. NaN values
            {"revenue": np.nan, "operating_income": np.nan, "dividend_per_share": np.nan, "Close": 100.0},
            {"revenue": 1000000.0, "operating_income": 200000.0, "dividend_per_share": 1.5, "Close": np.nan},
            # 3. Inf values
            {"revenue": np.inf, "operating_income": np.inf, "dividend_per_share": np.inf, "Close": 100.0},
            {"revenue": 1000000.0, "operating_income": 200000.0, "dividend_per_share": 1.5, "Close": np.inf},
            {"revenue": -np.inf, "operating_income": -np.inf, "dividend_per_share": -np.inf, "Close": 100.0},
            # 4. Mixed extreme / out-of-bound values
            {"revenue": 1e308, "operating_income": 1e308, "dividend_per_share": 1e308, "Close": 1e308},
            {"revenue": 1e-308, "operating_income": 1e-308, "dividend_per_share": 1e-308, "Close": 1e-308},
            {"revenue": -1e308, "operating_income": -1e308, "dividend_per_share": -1e308, "Close": 100.0},
        ]

        for i, sc in enumerate(scenarios):
            df = df_base.copy()
            for col, val in sc.items():
                df[col] = val

            df_feat = self.model._create_features(df)
            
            # If the df is empty, verify if it was because of invalid Close
            if df_feat.empty:
                # Close being zero, NaN or Inf causes pct_change to return NaN, which drops all rows.
                invalid_close = (
                    df["Close"].isna().any() or 
                    (df["Close"] == 0.0).any() or 
                    np.isinf(df["Close"]).any()
                )
                self.assertTrue(invalid_close, f"Scenario {i} returned empty df, but Close was not invalid")
                continue
            
            for col in ["operating_margin", "revenue_to_market_cap", "dividend_yield"]:
                self.assertIn(col, df_feat.columns)
                self.assertFalse(df_feat[col].isna().any(), f"Scenario {i} produced NaN in {col}")
                self.assertFalse(np.isinf(df_feat[col]).any(), f"Scenario {i} produced Inf in {col}")

    def test_timeseries_forward_filling_correctness_and_sorting(self):
        """
        Verify time-series forward-filling correctness for daily resolution.
        - Test chronological order preservation.
        - CHALLENGE: Test lookahead bias. What if df_prices is sorted in DESCENDING order?
          Verify if future fundamentals leak to the past, or if we handle it.
        """
        # Create sparse fundamental updates
        df_fun = pd.DataFrame({
            "date": [pd.Timestamp("2026-01-15"), pd.Timestamp("2026-02-15")],
            "revenue": [1000000.0, 2000000.0],
            "operating_income": [100000.0, 300000.0],
            "dividend_per_share": [1.0, 2.0]
        })

        # Create daily price data
        df_prices = pd.DataFrame({
            "Close": [100.0] * 60,
            "Volume": [1000.0] * 60,
        }, index=pd.date_range("2026-01-01", periods=60))

        class MockStorage:
            def get_fundamentals(self, symbol):
                return df_fun

        # Test with ascending order
        df_asc = self.model.merge_fundamentals("TEST_TICKER", df_prices, storage=MockStorage())
        default_meta = FALLBACK_METADATA["TEST_TICKER"]
        self.assertEqual(df_asc.loc["2026-01-01", "revenue"], default_meta["revenue"])
        self.assertEqual(df_asc.loc["2026-01-15", "revenue"], 1000000.0)
        self.assertEqual(df_asc.loc["2026-01-20", "revenue"], 1000000.0)
        self.assertEqual(df_asc.loc["2026-02-15", "revenue"], 2000000.0)
        self.assertEqual(df_asc.loc["2026-02-25", "revenue"], 2000000.0)

        # CHALLENGE: Test descending order input (newest first)
        df_prices_desc = df_prices.iloc[::-1].copy()
        df_desc = self.model.merge_fundamentals("TEST_TICKER", df_prices_desc, storage=MockStorage())
        
        val_at_past = df_desc.loc["2026-02-10", "revenue"]
        is_leakage = (val_at_past == 2000000.0)
        print(f"\n[LEAKAGE CHECK] Value at 2026-02-10 (ascending): {df_asc.loc['2026-02-10', 'revenue']}")
        print(f"[LEAKAGE CHECK] Value at 2026-02-10 (descending): {val_at_past}")
        print(f"[LEAKAGE CHECK] Lookahead leakage detected: {is_leakage}")

    def test_model_training_and_prediction_robustness(self):
        """
        Verify if the 12-feature prediction models train and predict correctly without feature dimensionality mismatches under stress.
        """
        # 1. Generate multi-stock training data (length 350)
        dates = pd.date_range("2026-01-01", periods=self.length)
        prices_dict = {}
        for sym in ["AAPL", "MSFT", "GOOGL"]:
            prices_dict[sym] = pd.DataFrame({
                "Close": np.linspace(100.0, 150.0, self.length) + np.random.normal(0, 2, self.length),
                "Open": np.linspace(100.0, 150.0, self.length),
                "High": np.linspace(101.0, 151.0, self.length),
                "Low": np.linspace(99.0, 149.0, self.length),
                "Volume": np.random.uniform(1000.0, 5000.0, self.length),
            }, index=dates)

        # Prepare training data
        df_train = self.model.prepare_training_data(prices_dict)
        self.assertFalse(df_train.empty, "df_train should not be empty")

        # Train models
        self.model.train(df_train)
        
        # Verify all horizons have models trained
        for h in self.model.horizons:
            self.assertIn(h, self.model.models)

        # 2. Predict on normal data
        pred_single = self.model.predict_current(prices_dict["AAPL"])
        self.assertEqual(len(pred_single), len(self.model.horizons))

        pred_batch = self.model.process_and_predict_all(prices_dict)
        self.assertFalse(pred_batch.empty)
        self.assertEqual(len(pred_batch), len(prices_dict))

        # 3. STRESS: Predict with missing or extra features/columns
        # Scenario A: df_current is missing some core columns like Volume
        df_missing_col = prices_dict["AAPL"].drop(columns=["Volume"])
        try:
            res = self.model.predict_current(df_missing_col)
            print(f"[STRESS] predict_current with missing Volume succeeded, returned: {res}")
        except KeyError as e:
            print(f"[STRESS] predict_current raised KeyError as expected (no Volume): {e}")

        # Scenario B: df_current contains extra columns
        df_extra_col = prices_dict["AAPL"].copy()
        df_extra_col["extra_feature_1"] = 999.9
        df_extra_col["extra_feature_2"] = "test"
        res_extra = self.model.predict_current(df_extra_col)
        self.assertEqual(len(res_extra), len(self.model.horizons))
        print(f"[STRESS] predict_current with extra columns succeeded, returned size: {len(res_extra)}")

        # Scenario C: df_current contains infinite values in price/volume
        df_inf = prices_dict["AAPL"].copy()
        df_inf.loc[df_inf.index[-1], "Close"] = np.inf
        df_inf.loc[df_inf.index[-1], "Volume"] = np.inf
        try:
            res_inf = self.model.predict_current(df_inf)
            print(f"[STRESS] predict_current with Inf Close/Volume succeeded, returned: {res_inf}")
        except Exception as e:
            print(f"[STRESS] predict_current with Inf Close/Volume crashed: {e}")

        # Scenario D: df_current contains NaNs in the latest row
        df_nan = prices_dict["AAPL"].copy()
        df_nan.loc[df_nan.index[-1], "Close"] = np.nan
        try:
            res_nan = self.model.predict_current(df_nan)
            print(f"[STRESS] predict_current with NaN in latest Close succeeded, returned: {res_nan}")
        except Exception as e:
            print(f"[STRESS] predict_current with NaN in latest Close crashed: {e}")

        # Scenario E: df_current with pre-computed features and NaNs in latest row
        df_feat = self.model._create_features(prices_dict["AAPL"])
        df_feat.loc[df_feat.index[-1], "vol_20d"] = np.nan
        try:
            res_feat_nan = self.model.predict_current(df_feat)
            print(f"[STRESS] predict_current with pre-computed NaN feature succeeded, returned: {res_feat_nan}")
        except Exception as e:
            print(f"[STRESS] predict_current with pre-computed NaN feature crashed: {e}")

        # Scenario F: df_current with pre-computed features and Inf in latest row
        df_feat_inf = self.model._create_features(prices_dict["AAPL"])
        df_feat_inf.loc[df_feat_inf.index[-1], "vol_20d"] = np.inf
        try:
            res_feat_inf = self.model.predict_current(df_feat_inf)
            print(f"[STRESS] predict_current with pre-computed Inf feature succeeded, returned: {res_feat_inf}")
        except Exception as e:
            print(f"[STRESS] predict_current with pre-computed Inf feature crashed: {e}")

if __name__ == "__main__":
    unittest.main()

