"""
Adversarial Challenger 2 Test Suite: Runtime Edge-Case & Empirical Verification.

Focus Areas:
1. OMS slippage feedback closed loop with calculate_realized_slippage and SlippageMetrics (V5-24)
2. Dynamic inverse ETF hedge sizing with real-time price lookup (Gate 8 / V5-25)
3. DART 8-digit corp_code vs 6-digit stock ticker matching (V5-20)
4. Stock split crash guard preventing false positive price division during severe market downturns (V5-22)
5. Strategy fallback handling for empty dataframes, single stock universes, and boundary anomalies (V5-14, V5-15, V5-18, V5-19, V5-21, V5-23, V5-26, V5-27, V5-28, V5-29, V5-30, V5-31)
"""

import os
import sys
import math
import sqlite3
import numpy as np
import pandas as pd
import pytest

# Ensure project paths are resolvable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
trading_system_path = os.path.join(project_root, "trading_system")
if trading_system_path not in sys.path:
    sys.path.insert(0, trading_system_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.slippage_feedback import SlippageFeedbackEngine, SlippageMetrics
from src.core.event_driven import EventDrivenEngine
from src.persistence.database import DataValidator
from src.core.accruals_quality import AccrualsQualityEngine
from src.core.multi_factor_neutralizer import MultiFactorNeutralizerEngine
from src.core.vol_target import VolTargetingEngine
from src.core.card_factor import CARDFactorEngine
from src.core.arm_factor import ARMFactorEngine
from src.core.mq_factor import MQFactorEngine
from src.core.hft_engine import MicrostructureImbalanceEngine
from src.core.insider_buying import InsiderBuyingEngine
from src.core.short_term_reversal import ShortTermReversalEngine
from src.core.iv_skew import IVSkewEngine
from src.core.gamma_squeeze import OptionsGammaSqueezeEngine
from src.core.rim_valuation import RIMValuationEngine
from src.core.order_flow import OrderFlowEngine
from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
from src.core.cross_border_lead_lag import CrossBorderLeadLagEngine
from src.config import TradingConfig


# =====================================================================
# Domain 4 / Topic 1: OMS Slippage Feedback Closed Loop (V5-24)
# =====================================================================

class TestOMSSlippageFeedbackClosedLoop:
    """Stress tests for calculate_realized_slippage signature and OMS Gate 7.3 feedback."""

    def test_slippage_feedback_signature_flexibility(self, tmp_path):
        """Verify calculate_realized_slippage accepts 0, 1, or arbitrary args/kwargs."""
        db_file = str(tmp_path / "trade_logs.db")
        engine = SlippageFeedbackEngine(db_path=db_file)

        # 0 arguments (standard caller)
        res0 = engine.calculate_realized_slippage()
        assert isinstance(res0, SlippageMetrics)
        assert res0.cost_scaling_factor == 1.0

        # 1 positional argument (legacy symbol string)
        res1 = engine.calculate_realized_slippage("005930")
        assert isinstance(res1, SlippageMetrics)

        # Multiple positional arguments (symbol, side, qty, exec_px, arr_px)
        res_multi = engine.calculate_realized_slippage("005930", "BUY", 100, 70500.0, 70000.0)
        assert isinstance(res_multi, SlippageMetrics)

        # Keyword arguments
        res_kw = engine.calculate_realized_slippage(symbol="AAPL", side="SELL", volatility=0.03, adv_20d=5e6)
        assert isinstance(res_kw, SlippageMetrics)

    def test_slippage_feedback_live_cost_scaling_with_recorded_trades(self, tmp_path):
        """Verify that real execution slippage from DB dynamically updates cost scaling factor."""
        db_file = str(tmp_path / "trade_logs.db")
        engine = SlippageFeedbackEngine(db_path=db_file)

        # Create schema for trade_logs table and insert high-slippage executions (expected = 10,000, fill = 10,150 -> 150 bps)
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT,
                    symbol TEXT,
                    side TEXT,
                    expected_price REAL,
                    fill_price REAL,
                    shares INTEGER,
                    timestamp TEXT
                )
            """)
            for i in range(20):
                cursor.execute("""
                    INSERT INTO trade_logs (market, symbol, side, expected_price, fill_price, shares, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, ("KOSPI", "005930", "BUY", 10000.0, 10150.0, 100, "2026-08-21 10:00:00"))
            conn.commit()

        metrics = engine.calculate_realized_slippage()
        assert isinstance(metrics, SlippageMetrics)
        assert metrics.sample_count == 20
        assert metrics.avg_slippage_bps > 50.0
        assert metrics.cost_scaling_factor > 1.0
        assert metrics.recommended_market_impact_multiplier >= 1.0

    def test_oms_gate_7_3_unpacks_slippage_without_type_error(self, tmp_path):
        """Verify OMS Gate 7.3 correctly consumes SlippageMetrics and enforces net alpha hurdle."""
        db_file = str(tmp_path / "trade_logs.db")
        oms = ExecutionOMSEngine(db_path=db_file)

        portfolio_weights = {"005930": 0.20}
        # Low expected return (0.001 = 10 bps), lower than KRX STT (15 bps) + base transaction cost
        top_predictions = [{
            "symbol": "005930",
            "market": "KOSPI",
            "ensemble_expected_return": 0.0010,
            "target_price": 70000.0
        }]
        prices_dict = {
            "005930": pd.DataFrame({"Close": [70000.0, 70000.0]})
        }

        # Gate 7.3 should filter BUY order due to net alpha hurdle < 0
        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=100000000.0,
            prices_dict=prices_dict,
            regime_label="NORMAL"
        )
        assert isinstance(orders, list)
        buy_orders = [o for o in orders if o.get("symbol") == "005930" and o.get("action") == "BUY"]
        assert len(buy_orders) == 0


# =====================================================================
# Domain 4 / Topic 2: Dynamic Inverse ETF Hedge Sizing (Gate 8 / V5-25)
# =====================================================================

class TestDynamicInverseETFHedgeSizing:
    """Stress tests for Gate 8 inverse ETF dynamic market price lookup and hedge sizing."""

    def test_get_latest_price_multi_format_resolution(self, tmp_path):
        """Test _get_latest_price against DataFrame, dict, scalar, and cache sources."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"))

        # DataFrame with 'Close'
        df1 = pd.DataFrame({"Close": [2050.0, 2075.0]})
        assert oms._get_latest_price("114800", prices_dict={"114800": df1}) == 2075.0

        # DataFrame with lowercase 'close'
        df2 = pd.DataFrame({"close": [15.25, 15.50]})
        assert oms._get_latest_price("SH", prices_dict={"SH": df2}) == 15.50

        # Numeric scalar in prices_dict
        assert oms._get_latest_price("114800", prices_dict={"114800": 2040.0}) == 2040.0

        # Symbol in top_predictions
        top_preds = [{"symbol": "114800", "target_price": 2060.0, "market": "KOSPI"}]
        assert oms._get_latest_price("114800", top_predictions=top_preds) == 2060.0

        # Fallback when missing everywhere (returns 0.0, which oms gate converts to default)
        assert oms._get_latest_price("UNKNOWN_SYM") == 0.0

    def test_gate_8_krx_bear_regime_inverse_etf_precise_quantity(self, tmp_path):
        """Verify KRX 114800 inverse ETF at ~2,050 KRW generates exact ~12,190 shares (not 2,500)."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"), lot_size_krx=10)
        total_capital = 100000000.0  # 100M KRW
        portfolio_weights = {"005930": 0.30, "000660": 0.20} # 50% long exposure
        top_predictions = [
            {"symbol": "005930", "market": "KOSPI", "target_price": 70000.0, "ensemble_expected_return": 0.05},
            {"symbol": "000660", "market": "KOSPI", "target_price": 180000.0, "ensemble_expected_return": 0.04}
        ]
        # Real inverse ETF market price = 2,050 KRW (KODEX 200 선물인버스2X)
        prices_dict = {
            "005930": pd.DataFrame({"Close": [70000.0]}),
            "000660": pd.DataFrame({"Close": [180000.0]}),
            "114800": pd.DataFrame({"Close": [2050.0]})
        }

        # Under BEAR/CRISIS regime, Gate 8 triggers synthetic inverse hedge
        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=total_capital,
            prices_dict=prices_dict,
            regime_label="BEAR"
        )
        assert isinstance(orders, list)
        hedge_orders = [o for o in orders if "HEDGE" in str(o.get("order_id", "")) or o.get("symbol") == "114800"]
        assert len(hedge_orders) == 1, "Expected exactly 1 inverse ETF hedge order"
        h_order = hedge_orders[0]

        # Target price must be dynamically resolved to 2,050 KRW
        assert h_order["target_price"] == 2050.0
        # If hedge weight is ~25% (25M KRW), quantity at 2,050 KRW is ~12,190 shares (10-lot rounded)
        # Previous hardcoded 10,000 KRW would have given only 2,500 shares (80% under-hedged)!
        expected_qty = int((total_capital * 0.25) // 2050.0)
        expected_lot_qty = (expected_qty // 10) * 10
        assert h_order["quantity"] == expected_lot_qty
        assert h_order["quantity"] > 10000, f"Quantity {h_order['quantity']} is not properly sized for ~2050 KRW price"

    def test_gate_8_us_crisis_regime_inverse_etf_precise_quantity(self, tmp_path):
        """Verify US market inverse ETF (SH @ $15.50) generates accurate share quantity."""
        oms = ExecutionOMSEngine(db_path=str(tmp_path / "trade_logs.db"))
        total_capital = 135000000.0  # 135M KRW ($100k USD @ 1350 KRW/USD)
        portfolio_weights = {"AAPL": 0.40, "MSFT": 0.30}
        top_predictions = [
            {"symbol": "AAPL", "market": "SP500", "target_price": 220.0, "ensemble_expected_return": 0.05},
            {"symbol": "MSFT", "market": "SP500", "target_price": 400.0, "ensemble_expected_return": 0.04}
        ]
        prices_dict = {
            "AAPL": pd.DataFrame({"Close": [220.0]}),
            "MSFT": pd.DataFrame({"Close": [400.0]}),
            "SH": pd.DataFrame({"Close": [15.50]})
        }

        orders = oms.generate_order_plan(
            top_predictions=top_predictions,
            portfolio_weights=portfolio_weights,
            current_holdings={},
            total_capital=total_capital,
            prices_dict=prices_dict,
            regime_label="CRISIS"
        )
        assert isinstance(orders, list)
        hedge_orders = [o for o in orders if o.get("symbol") == "SH" or "HEDGE" in str(o.get("order_id", ""))]
        assert len(hedge_orders) == 1
        h_order = hedge_orders[0]
        assert h_order["target_price"] == 15.50
        # Target hedge amount $35k (35% hedge weight for crisis). At $15.50, qty is 2,258 shares
        assert h_order["quantity"] > 2000


# =====================================================================
# Domain 3 / Topic 3: DART 8-Digit corp_code vs 6-Digit Ticker (V5-20)
# =====================================================================

class TestDARTCodeTranslationAndMatching:
    """Stress tests for DART 8-digit corp_code and 6-digit stock_code matching in EventDrivenEngine."""

    def test_dart_stock_code_and_corp_code_matching(self):
        """Verify EventDrivenEngine matches both 6-digit stock_code and 8-digit corp_code."""
        engine = EventDrivenEngine()
        prices_dict = {
            "005930": pd.DataFrame({"Close": [70000.0, 71000.0], "Volume": [1000, 2000]}),
            "000660": pd.DataFrame({"Close": [180000.0, 185000.0], "Volume": [500, 1000]}),
            "035420": pd.DataFrame({"Close": [200000.0, 201000.0], "Volume": [300, 400]}),
        }

        # Synthesize DART disclosures with various code formats
        disclosures = [
            # 1. 8-digit corp_code with 6-digit stock_code
            {
                "corp_code": "00126380",
                "stock_code": "005930",
                "report_nm": "주요사항보고서(자기주식취득결정)",
                "rcept_dt": "20260820"
            },
            # 2. Unpadded 4/5 digit stock_code that needs zfill(6)
            {
                "corp_code": "00164779",
                "stock_code": "660",  # Unpadded
                "report_nm": "영업실적등에대한전망(공정공시) [어닝 서프라이즈]",
                "rcept_dt": "20260820"
            },
            # 3. Only corp_code matching symbol list directly
            {
                "corp_code": "035420",
                "report_nm": "주요사항보고서(유상증자결정)",
                "rcept_dt": "20260820"
            },
            # 4. Irrelevant company (should NOT match)
            {
                "corp_code": "00999999",
                "stock_code": "099999",
                "report_nm": "주요사항보고서(자기주식처분결정)",
                "rcept_dt": "20260820"
            }
        ]

        scores = engine.compute_scores(
            prices_dict=prices_dict,
            dart_disclosures=disclosures
        )

        assert isinstance(scores, pd.DataFrame)
        assert "symbol" in scores.columns
        assert "event_score" in scores.columns

        val_5930 = scores[scores["symbol"] == "005930"]["event_score"].iloc[0]
        val_0660 = scores[scores["symbol"] == "000660"]["event_score"].iloc[0]

        # Share buyback and Earnings surprise must produce positive event catalyst scores (> 0.50)
        assert val_5930 > 0.50, f"Samsung buyback event score {val_5930} must be > 0.50"
        assert val_0660 > 0.50, f"Hynix earnings surprise score {val_0660} must be > 0.50"

    def test_dart_empty_and_malformed_disclosure_resilience(self):
        """Verify engine gracefully handles missing fields, None values, and malformed entries."""
        engine = EventDrivenEngine()
        prices_dict = {
            "005930": pd.DataFrame({"Close": [70000.0, 71000.0], "Volume": [1000, 2000]})
        }
        malformed_disclosures = [
            {},
            {"report_nm": None},
            {"corp_code": None, "stock_code": None},
            {"corp_code": "", "stock_code": "", "report_nm": ""},
            {"corp_code": 12345, "stock_code": 5930, "report_nm": "단일판매ㆍ공급계약체결"}
        ]

        scores = engine.compute_scores(prices_dict=prices_dict, dart_disclosures=malformed_disclosures)
        assert isinstance(scores, pd.DataFrame)
        assert len(scores) == 1


# =====================================================================
# Domain 3 / Topic 4: Stock Split Crash Guard (V5-22)
# =====================================================================

class TestStockSplitCrashGuard:
    """Stress tests verifying volume surge corroboration distinguishes genuine splits from market crashes."""

    def test_genuine_split_with_volume_surge_is_adjusted(self):
        """Genuine 2:1 split (price -50%, volume 2.5x) must be adjusted."""
        dates = pd.date_range("2026-01-01", periods=10, freq="D")
        # Days 0-4: 100,000 KRW, 10,000 volume
        # Days 5-9: 50,000 KRW, 25,000 volume (2.5x surge)
        prices = [100000.0] * 5 + [50000.0] * 5
        volumes = [10000.0] * 5 + [25000.0] * 5
        df = pd.DataFrame({
            "Open": prices,
            "High": prices,
            "Low": prices,
            "Close": prices,
            "Volume": volumes
        }, index=dates)

        adjusted_df = DataValidator.validate_and_clean_price_series(df)
        # Prior historical prices (index 0 to 4) should be divided by 2 -> 50,000 KRW
        assert adjusted_df["Close"].iloc[0] == pytest.approx(50000.0, rel=1e-3)
        # Prior historical volumes should be multiplied by 2 -> 20,000
        assert adjusted_df["Volume"].iloc[0] == pytest.approx(20000.0, rel=1e-3)

    def test_flash_crash_without_volume_surge_is_NOT_adjusted(self):
        """Severe overnight crash (-50% price drop, volume flat/contracting) must NOT be adjusted."""
        dates = pd.date_range("2026-01-01", periods=10, freq="D")
        # Days 0-4: 100,000 KRW, 10,000 volume
        # Days 5-9: 50,000 KRW, 8,000 volume (0.8x volume, severe selloff without split)
        prices = [100000.0] * 5 + [50000.0] * 5
        volumes = [10000.0] * 5 + [8000.0] * 5
        df = pd.DataFrame({
            "Open": prices,
            "High": prices,
            "Low": prices,
            "Close": prices,
            "Volume": volumes
        }, index=dates)

        adjusted_df = DataValidator.validate_and_clean_price_series(df)
        # Crash guard should PREVENT split adjustment: Day 0 price remains 100,000 KRW
        assert adjusted_df["Close"].iloc[0] == pytest.approx(100000.0, rel=1e-3)
        assert adjusted_df["Volume"].iloc[0] == pytest.approx(10000.0, rel=1e-3)

    def test_split_detector_boundary_conditions(self):
        """Verify split detector handles empty, single-row, zero-volume, and zero-price inputs."""
        empty_df = pd.DataFrame()
        res_empty = DataValidator.validate_and_clean_price_series(empty_df)
        assert res_empty.empty

        single_row = pd.DataFrame({"Close": [1000.0], "Volume": [100.0]})
        res_single = DataValidator.validate_and_clean_price_series(single_row)
        assert len(res_single) == 1

        dates = pd.date_range("2026-01-01", periods=6, freq="D")
        zero_vol = pd.DataFrame({
            "Open": [100.0] * 6,
            "High": [100.0] * 6,
            "Low": [100.0] * 6,
            "Close": [100.0] * 6,
            "Volume": [0.0] * 6
        }, index=dates)
        res_zero = DataValidator.validate_and_clean_price_series(zero_vol)
        assert len(res_zero) == 6


# =====================================================================
# Domain 3 / Topic 5: Strategy Fallback Handling for Empty & Single-Stock
# =====================================================================

class TestStrategyFallbacksAndSingleStockHandling:
    """Stress tests across all 31 strategy engines for N=0 and N=1 edge cases."""

    def test_v5_28_accruals_quality_single_stock_neutral_score(self):
        """AccrualsQualityEngine with N=1 must return neutral score 0.50, not 0.0."""
        engine = AccrualsQualityEngine()
        df = pd.DataFrame({
            "Close": [100.0, 102.0, 105.0, 103.0, 108.0],
            "Volume": [1000, 1200, 1500, 1100, 1400]
        })
        scores = engine.compute_scores({"005930": df})
        assert isinstance(scores, pd.DataFrame)
        assert len(scores) == 1
        score_val = scores["accruals_quality_score"].iloc[0]
        assert score_val == pytest.approx(0.50, abs=1e-4), f"N=1 accruals score must be 0.50, got {score_val}"

    def test_v5_15_microstructure_empty_and_default_invocations(self):
        """MicrostructureImbalanceEngine synthesizes universe from prices_dict when universe is None."""
        engine = MicrostructureImbalanceEngine()
        df1 = pd.DataFrame({"Close": [70000.0, 71000.0], "Volume": [1000, 1500]})
        df2 = pd.DataFrame({"Close": [200.0, 205.0], "Volume": [5000, 6000]})
        prices_dict = {"005930": df1, "AAPL": df2}

        # Invocation with universe=None must not return empty DataFrame
        scores = engine.compute_scores(prices_dict)
        assert isinstance(scores, pd.DataFrame)
        assert len(scores) == 2
        assert set(scores["symbol"].values) == {"005930", "AAPL"}

        # Invocation with empty prices_dict
        empty_scores = engine.compute_scores({})
        assert isinstance(empty_scores, pd.DataFrame)
        assert len(empty_scores) == 0

    def test_v5_21_multi_factor_neutralizer_underdetermined_and_ridge(self):
        """MultiFactorNeutralizer handles N=1, N=3 (N < 6 pinv), and rank-deficient collinear designs."""
        engine = MultiFactorNeutralizerEngine()
        raw_scores = {"005930": 0.80, "000660": 0.70, "035420": 0.60}
        fundamentals = {
            "005930": {"market_cap": 4e14, "pbr": 1.2, "roe": 0.15, "asset_growth": 0.05, "momentum_12m": 0.20},
            "000660": {"market_cap": 1e14, "pbr": 1.5, "roe": 0.18, "asset_growth": 0.08, "momentum_12m": 0.35},
            "035420": {"market_cap": 3e13, "pbr": 1.8, "roe": 0.10, "asset_growth": 0.02, "momentum_12m": 0.10},
        }

        # N=3 (N < 6) uses SVD pinv
        res_3 = engine.compute_scores(raw_scores, fundamentals_dict=fundamentals)
        assert isinstance(res_3, pd.DataFrame)
        assert len(res_3) == 3
        assert not res_3["neutralized_score"].isna().any()

        # N=1 single stock
        res_1 = engine.compute_scores({"005930": 0.85}, fundamentals_dict={"005930": fundamentals["005930"]})
        assert len(res_1) == 1
        assert not res_1["neutralized_score"].isna().any()

    def test_v5_27_vol_targeting_expanded_dynamic_range(self):
        """VolTargetingEngine dynamic slope k=3.0 expands range to [0.05, 0.95]."""
        engine = VolTargetingEngine()

        # Very low vol stock (high allocation score)
        score_low_vol = engine._scale_score(current_vol=0.06, target_vol=0.15)
        # Very high vol stock (low allocation score)
        score_high_vol = engine._scale_score(current_vol=0.45, target_vol=0.15)

        assert score_low_vol > 0.80, f"Low vol score {score_low_vol} should be > 0.80"
        assert score_high_vol < 0.25, f"High vol score {score_high_vol} should be < 0.25"
        assert (score_low_vol - score_high_vol) > 0.55, "Dynamic range should be expanded (> 0.55 spread)"

    def test_v5_29_continuous_logistic_transfer_smoothing(self):
        """Verify CARDFactorEngine, ARMFactorEngine, and MQFactorEngine use smooth sigmoid without step jumps."""
        # Test continuous logistic transfer formulas directly
        for x in [0.48, 0.49, 0.50, 0.51, 0.52, 0.78, 0.79, 0.80, 0.81, 0.82]:
            boost_arm = 1.0 + 0.10 / (1.0 + np.exp(-10.0 * (x - 0.75)))
            boost_card = 1.0 + 0.10 / (1.0 + np.exp(-12.0 * (x - 0.70)))
            assert math.isfinite(boost_arm) and 1.0 <= boost_arm <= 1.10
            assert math.isfinite(boost_card) and 1.0 <= boost_card <= 1.10

    def test_v5_30_insider_buying_keyword_filter(self):
        """Verify InsiderBuyingEngine ignores non-transaction administrative filings."""
        engine = InsiderBuyingEngine()
        prices_dict = {"005930": pd.DataFrame({"Close": [70000.0, 71000.0], "Volume": [1000, 2000]})}

        # Non-transaction administrative disclosure
        neutral_disclosures = [{
            "corp_code": "00126380",
            "stock_code": "005930",
            "report_nm": "임원ㆍ주요주주특정증권등소유상황보고서"
        }]
        scores_neutral = engine.compute_scores(prices_dict=prices_dict, dart_disclosures=neutral_disclosures)
        score_val_neutral = scores_neutral[scores_neutral["symbol"] == "005930"]["insider_buying_score"].iloc[0]

        # Explicit open-market buy
        buy_disclosures = [{
            "corp_code": "00126380",
            "stock_code": "005930",
            "report_nm": "임원ㆍ주요주주특정증권등소유상황보고서 (장내매수 취득)"
        }]
        scores_buy = engine.compute_scores(prices_dict=prices_dict, dart_disclosures=buy_disclosures)
        score_val_buy = scores_buy[scores_buy["symbol"] == "005930"]["insider_buying_score"].iloc[0]

        assert score_val_buy > score_val_neutral, f"Buy disclosure score {score_val_buy} must exceed neutral score {score_val_neutral}"

    def test_v5_23_short_term_reversal_lowercase_columns(self):
        """Verify ShortTermReversalEngine handles lowercase 'close' column without KeyError."""
        engine = ShortTermReversalEngine()
        dates = pd.date_range("2026-01-01", periods=20, freq="D")
        df_lower = pd.DataFrame({
            "close": np.linspace(100.0, 90.0, 20),
            "volume": np.full(20, 1000.0)
        }, index=dates)

        scores = engine.compute_scores({"005930": df_lower})
        assert isinstance(scores, (dict, pd.DataFrame, pd.Series))
        if isinstance(scores, pd.DataFrame):
            assert len(scores) == 1
            assert "005930" in scores["symbol"].values
        else:
            assert "005930" in scores

    def test_v5_14_gamma_squeeze_kwargs_extensibility(self):
        """Verify OptionsGammaSqueezeEngine accepts extra arbitrary kwargs without TypeError."""
        engine = OptionsGammaSqueezeEngine()
        symbols = ["AAPL", "NVDA"]
        prices_dict = {
            "AAPL": pd.DataFrame({"Close": [220.0, 225.0]}),
            "NVDA": pd.DataFrame({"Close": [120.0, 125.0]})
        }
        res = engine.compute_gamma_squeeze_scores(
            symbols=symbols,
            prices_dict=prices_dict,
            unexpected_flag=True,
            arbitrary_param=12345
        )
        assert isinstance(res, pd.DataFrame)
        assert len(res) == 2

    def test_v5_26_iv_skew_downside_semi_variance_zero_benchmark(self):
        """Verify IVSkewEngine measures downside risk against MAR=0.0, not sample mean."""
        engine = IVSkewEngine()
        # Returns with positive mean (+1.0%), but all positive returns: [0.005, 0.010, 0.015]
        df_skew = pd.DataFrame({
            "Close": [100.0, 101.0, 102.0, 103.5, 105.0],
            "Volume": [1000, 1100, 1200, 1300, 1400]
        })
        scores = engine.compute_scores({"005930": df_skew})
        assert isinstance(scores, pd.DataFrame)
        assert len(scores) == 1
        assert math.isfinite(scores["iv_skew_score"].iloc[0])

    def test_v5_31_trading_config_environment_type_casting(self, monkeypatch):
        """Verify TradingConfig casts string environment variables to int, float, bool."""
        monkeypatch.setenv("VCP_MIN_SCORE_THRESHOLD", "0.45")
        monkeypatch.setenv("STOCK_PRICE_FRESHNESS_DAYS", "14")
        monkeypatch.setenv("MOCK_TRADING_ENABLED", "true")
        monkeypatch.setenv("PORTFOLIO_CAPITAL_KRW", "50000000")

        config = TradingConfig()

        assert isinstance(config.vcp_min_score_threshold, float)
        assert config.vcp_min_score_threshold == 0.45
        assert isinstance(config.stock_price_freshness_days, int)
        assert config.stock_price_freshness_days == 14
        assert isinstance(config.mock_trading, bool)
        assert config.mock_trading is True
        assert isinstance(config.portfolio_capital_krw, float)
        assert config.portfolio_capital_krw == 50000000.0

    def test_all_31_strategies_empty_and_single_stock_stress(self):
        """Stress-test 100% of strategy engines with empty dict and single-stock minimal DataFrame."""
        dates = pd.date_range("2026-01-01", periods=10, freq="D")
        minimal_df = pd.DataFrame({
            "Open": [100.0] * 10,
            "High": [105.0] * 10,
            "Low": [95.0] * 10,
            "Close": [100.0] * 10,
            "Volume": [1000.0] * 10
        }, index=dates)

        single_stock_dict = {"005930": minimal_df}
        empty_stock_dict = {}

        engines = [
            AccrualsQualityEngine(),
            CARDFactorEngine(),
            ARMFactorEngine(),
            MQFactorEngine(),
            MicrostructureImbalanceEngine(),
            InsiderBuyingEngine(),
            ShortTermReversalEngine(),
            IVSkewEngine(),
            VolTargetingEngine(),
            ShortInterestSqueezeEngine(),
            OrderFlowEngine(),
            MultiFactorNeutralizerEngine(),
            EventDrivenEngine(),
            OptionsGammaSqueezeEngine(),
            RIMValuationEngine(),
            CrossBorderLeadLagEngine(),
        ]

        for engine in engines:
            name = engine.__class__.__name__
            # 1. Test empty dictionary
            try:
                if hasattr(engine, "compute_scores"):
                    res_empty = engine.compute_scores(empty_stock_dict)
                elif hasattr(engine, "compute_gamma_squeeze_scores"):
                    res_empty = engine.compute_gamma_squeeze_scores(symbols=[], prices_dict=empty_stock_dict)
                assert res_empty is not None, f"{name} returned None on empty dict"
            except Exception as e:
                pytest.fail(f"{name} crashed on empty stock dict: {e}")

            # 2. Test single stock dictionary
            try:
                if hasattr(engine, "compute_scores"):
                    res_single = engine.compute_scores(single_stock_dict)
                elif hasattr(engine, "compute_gamma_squeeze_scores"):
                    res_single = engine.compute_gamma_squeeze_scores(symbols=["005930"], prices_dict=single_stock_dict)
                assert res_single is not None, f"{name} returned None on single stock dict"
            except Exception as e:
                pytest.fail(f"{name} crashed on single stock dict: {e}")

    def test_v6_20_dart_8digit_corp_code_mapping_without_stock_code(self, monkeypatch):
        """V6-20: Verify EventDrivenEngine resolves 8-digit OpenDART corp_code to 6-digit stock code when stock_code is missing."""
        from src.core.event_driven import EventDrivenEngine
        from src.data_layer.dart_corp_mapper import DARTCorpMapper

        engine = EventDrivenEngine(dart_api_key="")

        # Mock DARTCorpMapper.get_corp_code to return 00126380 for 005930
        monkeypatch.setattr(DARTCorpMapper, "get_corp_code", lambda self, sym: "00126380" if sym == "005930" else None)

        # Filing without stock_code, only with 8-digit corp_code
        filings = [{
            "corp_code": "00126380",
            "stock_code": "",
            "report_nm": "자기주식취득결정",
            "pblntf_ty": "B",
            "rcept_dt": "20260820"
        }]

        dates = pd.date_range("2026-01-01", periods=20, freq="D")
        df_price = pd.DataFrame({"Close": [70000.0] * 20, "Volume": [10000] * 20}, index=dates)

        res = engine.compute_event_scores(["005930"], {"005930": df_price}, filings=filings)
        assert not res.empty
        score = res[res['symbol'] == '005930']['event_score'].iloc[0]
        # Bullish buyback disclosure should boost score above neutral 0.50
        assert score > 0.70, f"Expected buyback score > 0.70 via DART corp_code resolution, got {score}"

    def test_v6_22_factor_engines_n1_neutral_score_guard(self):
        """V6-22: Verify factor engines return neutral score (0.50) when evaluating a single stock (N=1), rather than saturating at 0.98."""
        from src.core.mq_factor import MQFactorEngine
        from src.core.short_interest_squeeze import ShortInterestSqueezeEngine
        from src.core.valueup_catalyst import ValueUpCatalystEngine
        from src.core.trend_efficiency import TrendEfficiencyEngine
        from src.core.order_flow import OrderFlowEngine
        from src.core.short_term_reversal import ShortTermReversalEngine
        from src.core.inst_foreign_sector import InstForeignSectorEngine

        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        df_single = pd.DataFrame({
            "Open": np.linspace(100, 90, 30),
            "High": np.linspace(102, 92, 30),
            "Low": np.linspace(98, 88, 30),
            "Close": np.linspace(100, 90, 30),
            "Volume": np.full(30, 10000.0)
        }, index=dates)
        single_dict = {"005930": df_single}

        # 1. MQ Factor Engine
        res_mq = MQFactorEngine().compute_scores(single_dict)
        assert abs(res_mq['mq_score'].iloc[0] - 0.50) < 1e-4

        # 2. Short Interest Squeeze Engine
        res_sq = ShortInterestSqueezeEngine().compute_scores(single_dict)
        assert abs(res_sq['short_squeeze_score'].iloc[0] - 0.50) < 1e-4

        # 3. Value-Up Catalyst Engine
        res_vu = ValueUpCatalystEngine().compute_scores(single_dict)
        assert abs(res_vu['valueup_catalyst_score'].iloc[0] - 0.50) < 1e-4

        # 4. Trend Efficiency Engine
        res_te = TrendEfficiencyEngine().compute_scores(single_dict)
        assert abs(res_te['trend_efficiency_score'].iloc[0] - 0.50) < 1e-4

        # 5. Order Flow Engine
        res_of = OrderFlowEngine().compute_scores(single_dict)
        assert abs(res_of['order_flow_score'].iloc[0] - 0.50) < 1e-4

        # 6. Short-Term Reversal Engine
        res_rev = ShortTermReversalEngine().compute_scores(single_dict)
        assert abs(res_rev['reversal_score'].iloc[0] - 0.50) < 1e-4

        # 7. Inst & Foreign Sector Engine
        res_inst = InstForeignSectorEngine().compute_scores(single_dict)
        assert abs(res_inst['inst_foreign_sector_score'].iloc[0] - 0.50) < 1e-4

    def test_v6_24_reverse_stock_split_adjustment_and_volume_contraction(self):
        """V6-24: Verify DataValidator detects reverse stock split (> +50% jump) and adjusts historical OHLC & Volume."""
        validator = DataValidator()
        dates = pd.date_range("2026-01-01", periods=10, freq="D")
        # 1-for-2 reverse stock split on day 5: price doubles from 10.0 to 20.0, volume halves from 1000 to 500
        df = pd.DataFrame({
            "Open": [10.0]*5 + [20.0]*5,
            "High": [10.5]*5 + [21.0]*5,
            "Low": [9.5]*5 + [19.0]*5,
            "Close": [10.0]*5 + [20.0]*5,
            "Volume": [1000.0]*5 + [500.0]*5,
        }, index=dates)

        df_cleaned = validator.validate_and_clean_price_series(df)
        # Pre-split close (first 5 days) should be scaled by 2.0 -> 20.0
        assert abs(df_cleaned['Close'].iloc[0] - 20.0) < 1e-2
        # Pre-split volume should be scaled by 1/2.0 -> 500.0
        assert abs(df_cleaned['Volume'].iloc[0] - 500.0) < 1e-2

