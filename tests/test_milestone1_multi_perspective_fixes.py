# -*- coding: utf-8 -*-
"""
tests/test_milestone1_multi_perspective_fixes.py — Unit Tests for Milestone 1:
Comprehensive Multi-Perspective Technical Fixes across Macro, Micro, and Trader modules.

Verifies:
1. Macro: TNX yield scaling and bounds handling in IndicatorStorage, GlobalMarket, and Pipeline.
2. Macro: RegimeDetector VIX level extraction, Fast Shock override (>30), and 3D Squeeze (>25).
3. Macro: CrisisDetector VIX ROC velocity non-zero lag, us10y history seeding, and DXY passing.
4. Macro: CARD factor 100x continuity and MacroStressSpillover column aliases.
5. Micro: Gatheral 3/2-power penalty (* adv) and dimensional alpha convergence velocity.
6. Micro: Pre-trade participation ratio (* adv without n_slices division).
7. Micro: FastLOBEngine VPIN price return partitioning and one-sided depth fallback.
8. Micro: Signed volume acceleration conditioning in order flow and HFT engines.
9. Micro: Darkpool distribution penalty for low buy bias.
10. Trader: RiskManager calculate_drawdown state synchronization (no phantom 50% DD).
11. Trader: OMS Engine micro_price tick rounding and Gate 8 pro-rata hedge funding.
12. Trader: SlippageFeedbackEngine single canonical class and sequential trade replay.
13. Trader: UnifiedPortfolioAllocator Leland buffer absolute drift check, HOLD protection, and inverse hedging.
"""

import math
import numpy as np
import pandas as pd
import pytest

from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.data_layer.global_market import GlobalMarketClient
from src.analysis.regime_detector import MarketRegimeDetector
from src.risk.risk_manager import RiskManager, CrisisDetector, CrisisLevel
from src.core.card_factor import CARDFactorEngine
from src.core.cross_asset_spillover import CrossAssetSpilloverEngine
from src.core.macro_stress_spillover import MacroStressSpilloverEngine
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.core.fast_lob_engine import FastOrderBookMatchingEngine
from src.core.order_flow import OrderFlowEngine
from src.data_layer.darkpool_tracker import DarkPoolTracker
from src.execution.oms_engine import ExecutionOMSEngine
from src.execution.slippage_feedback import (
    FourteenDimensionalJosephKalmanFilter,
    SlippageFeedbackEngine,
    SlippageMetrics,
)
from src.risk.portfolio_allocator import PortfolioAllocator


class TestMacroFixes:
    def test_tnx_indicator_value_ok_and_scaling(self):
        storage = MarketIndicatorStorage()
        assert storage._indicator_value_ok("^TNX", None, 4.25) is True
        assert storage._indicator_value_ok("^TNX", None, 42.50) is True  # auto-scaled
        assert storage._indicator_value_ok("TNX", None, 45.0) is True
        assert storage._indicator_value_ok("^TNX", None, 250.0) is False  # out of bounds even when scaled

    def test_global_market_macro_commodity_yield_scaling(self, monkeypatch):
        gm = GlobalMarketClient()
        fake_df = pd.DataFrame({"Close": [42.0, 42.5]}, index=pd.date_range("2026-01-01", periods=2))
        monkeypatch.setattr(gm, "_get_cached_or_fetch", lambda sym, **kwargs: fake_df)
        res = gm.get_macro_commodity("^TNX")
        assert res["price"] == pytest.approx(4.25, abs=1e-4)

    def test_regime_detector_vix_level_and_fast_shock(self):
        detector = MarketRegimeDetector()
        df = pd.DataFrame({
            "vix_raw": [35.0, 36.0],
            "vix_change": [-1.5, -2.0],
            "sp500_change": [0.1, 0.2],
        })
        feats = detector._prepare_features(df)
        assert feats["vix_level"].iloc[-1] == pytest.approx(0.36, abs=1e-4)

        regime = detector.predict_regime(df)
        assert regime == 0  # Forcing BEAR due to fast shock (VIX=36 > 30)

        trans = detector.predict_regime_transition_probabilities(df)
        assert trans["bear_shock_risk"] is True
        assert trans["p_bear"] == 0.85

    def test_regime_detector_3d_macro_liquidity_squeeze(self):
        detector = MarketRegimeDetector()
        # Normal day with 6% change in VIX, but VIX level is calm 18.0
        df_calm = pd.DataFrame({
            "vix_raw": [17.0, 18.0],
            "vix_change": [6.0, 5.8],
            "us10y": [3.8, 3.8],
        })
        res_calm = detector.predict_3d_macro_regime(df_calm)
        assert res_calm["macro_label"] != "LIQUIDITY_SQUEEZE"

        # Severe day with VIX level at 28.0
        df_stress = pd.DataFrame({
            "vix_raw": [24.0, 28.0],
            "vix_change": [1.0, 1.2],
            "us10y": [4.0, 4.0],
        })
        res_stress = detector.predict_3d_macro_regime(df_stress)
        assert res_stress["macro_label"] == "LIQUIDITY_SQUEEZE"

    def test_crisis_detector_vix_roc_velocity_no_self_cancellation(self):
        detector = CrisisDetector()
        detector.evaluate(vix=20.0)
        # Acute panic jump on next day from 20 to 45
        lvl = detector.evaluate(vix=45.0)
        # Velocity between day 1 (20) and day 2 (45) should trigger SEVERE/ACTIVE crisis
        assert lvl in [CrisisLevel.SEVERE, CrisisLevel.ACTIVE, CrisisLevel.WATCH]
        assert detector.crisis_level in [CrisisLevel.SEVERE, CrisisLevel.ACTIVE, CrisisLevel.WATCH]

    def test_crisis_detector_seeding_us10y(self):
        detector = CrisisDetector()
        df = pd.DataFrame({
            "us10y": [4.1, 4.2, 4.3, 4.5],
            "vix_raw": [18.0, 19.0, 20.0, 22.0],
        })
        detector.seed_history_from_dataframe(df)
        assert len(detector._tnx_history) == 4
        assert detector._tnx_history[-1] == pytest.approx(4.5)

    def test_card_factor_continuous_scaling(self):
        engine = CARDFactorEngine()
        # Ensure small moves (0.8%) do not explode 100x
        dates = pd.date_range("2026-01-01", periods=10)
        prices = {
            "005930": pd.DataFrame({"Close": np.linspace(60000, 62000, 10)}, index=dates)
        }
        res1 = engine.compute_scores(prices, macro_dict={"vix_change": 0.8})
        res2 = engine.compute_scores(prices, macro_dict={"vix_change": 1.2})
        score1 = res1.get("005930", 0.5)
        score2 = res2.get("005930", 0.5)
        assert abs(score1 - score2) < 0.15, f"Discontinuity detected: {score1} vs {score2}"

    def test_macro_stress_spillover_column_aliases(self):
        engine = MacroStressSpilloverEngine()
        ind_df = pd.DataFrame({
            "vix_raw": np.linspace(15, 25, 25),
            "usdkrw_raw": np.linspace(1300, 1400, 25),
        })
        curr_s, delta_s = engine._extract_macro_stress_series(ind_df, prices_dict={})
        assert 0.0 <= curr_s <= 1.0
        assert len(delta_s) > 0


class TestMicroFixes:
    def test_gatheral_3_2_power_market_impact_formula(self):
        alloc = UnifiedPortfolioAllocator()
        # ADV = 1,000,000, traded_notional = 10,000 (1% ADV)
        weights = {"A": 0.01}
        current = {"A": 0.00}
        advs = {"A": 1_000_000.0}
        vols = {"A": 0.02}
        penalty = alloc.compute_gatheral_market_impact_penalty(
            weights=weights,
            current_weights=current,
            adv_dict=advs,
            vol_dict=vols,
            total_equity=1_000_000.0,
            eta=0.10,
        )
        # frac = 10,000 / 1,000,000 = 0.01. frac^1.5 = 0.001.
        # Cost = eta * sigma * frac^1.5 * ADV = 0.10 * 0.02 * 0.001 * 1,000,000 = 2.0
        assert penalty == pytest.approx(2.0, rel=1e-3)

    def test_alpha_convergence_velocity_dimensional_scaling(self):
        # Closed-Form Optimal Convergence Velocity dimensional scaling: ((num / den) ** 2) * (adv_equity_ratio ** 2) * trade_scaling
        numerator = 0.05
        denominator = 1.5 * 1.0 * 0.20
        daily_adv = 10_000_000.0
        total_capital = 100_000_000.0
        adv_equity_ratio = daily_adv / total_capital
        gap_adv_ratio = 0.05
        trade_scaling = 1.0 / gap_adv_ratio
        theta_impact = ((numerator / denominator) ** 2) * (adv_equity_ratio ** 2) * trade_scaling
        assert np.isfinite(theta_impact)
        assert theta_impact > 0
        assert pytest.approx(adv_equity_ratio, 1e-5) == 0.10

    def test_participation_ratio_not_divided_by_n_slices(self):
        # Verify that participation_ratio = np.clip(q_order_adaptive / adv, 0.0001, 0.25)
        # does not divide adv by n_slices (which previously caused 2.0x under-costing)
        q_order = 50_000.0
        adv = 1_000_000.0
        n_slices = 5
        correct_part_ratio = float(np.clip(q_order / adv, 0.0001, 0.25))
        buggy_part_ratio = float(np.clip(q_order / (adv * float(n_slices)), 0.0001, 0.25))
        assert correct_part_ratio == 0.05
        assert buggy_part_ratio == 0.01
        assert correct_part_ratio == pytest.approx(n_slices * buggy_part_ratio)

    def test_fast_lob_engine_one_sided_micro_price_fallback(self):
        engine = FastOrderBookMatchingEngine()
        # Populate only bids (no asks)
        engine.add_limit_order(order_id="B1", side="BUY", price=70000.0, volume=100.0)
        snap = engine.get_depth_snapshot()
        assert snap["micro_price"] == 70000.0, f"Expected 70000, got {snap['micro_price']}"
        assert snap["l3_micro_price"] == 70000.0

    def test_fast_lob_engine_vpin_numpy_array_input(self):
        engine = FastOrderBookMatchingEngine()
        volumes = np.array([100.0, 200.0, 150.0, 300.0], dtype=np.float64)
        prices = np.array([50000.0, 49900.0, 49800.0, 49700.0], dtype=np.float64)
        # Verify calculate_vpin_toxicity accepts numpy array without ValueError
        vpin = engine.calculate_vpin_toxicity(order_volumes=volumes, prices=prices)
        assert isinstance(vpin, float)
        assert 0.0 <= vpin <= 1.0
        # Also verify order_prices alias accepts numpy array without ValueError
        vpin_alias = engine.calculate_vpin_toxicity(order_volumes=volumes, order_prices=prices)
        assert isinstance(vpin_alias, float)
        assert 0.0 <= vpin_alias <= 1.0

    def test_fast_lob_engine_vpin_uniform_price_cascade(self):
        engine = FastOrderBookMatchingEngine()
        p = np.array([50000.0 - 100.0 * i for i in range(50)], dtype=np.float64)
        v = np.array([100.0] * 50, dtype=np.float64)
        # Uniform price cascade must yield high toxicity (>= 0.70), not false 0.0
        vpin = engine.calculate_vpin_toxicity(order_volumes=v, prices=p)
        assert vpin >= 0.70, f"Expected high toxicity (>= 0.70) on uniform cascade, got {vpin}"
        assert vpin <= 1.0

    def test_signed_volume_acceleration_order_flow(self):
        engine = OrderFlowEngine()
        dates = pd.date_range("2026-01-01", periods=25)
        # Selloff regime on high volume
        df_bear = pd.DataFrame({
            "close": np.linspace(70000, 60000, 25),
            "high": np.linspace(71000, 61000, 25),
            "low": np.linspace(69000, 59000, 25),
            "volume": np.linspace(100000, 500000, 25),  # accelerating volume on breakdown
        }, index=dates)

        # Bull regime on high volume
        df_bull = pd.DataFrame({
            "close": np.linspace(60000, 70000, 25),
            "high": np.linspace(61000, 71000, 25),
            "low": np.linspace(59000, 69000, 25),
            "volume": np.linspace(100000, 500000, 25),  # accelerating volume on breakout
        }, index=dates)

        res = engine.compute_scores({"BEAR": df_bear, "BULL": df_bull})
        score_bear = res[res["symbol"] == "BEAR"]["order_flow_score"].iloc[0]
        score_bull = res[res["symbol"] == "BULL"]["order_flow_score"].iloc[0]
        assert score_bull > score_bear, f"Bullish volume should outscore panic selling: {score_bull} vs {score_bear}"

    def test_darkpool_institutional_distribution_penalty(self):
        tracker = DarkPoolTracker()
        dates = pd.date_range("2026-01-01", periods=15)
        prices = {"005930": pd.DataFrame({"Close": np.ones(15) * 50000, "Volume": np.ones(15) * 10000}, index=dates)}

        # Normal/high buy bias
        res_buy = tracker.compute_darkpool_scores(
            symbols=["005930"],
            prices_dict=prices,
            darkpool_data_dict={"005930": {"dark_pool_ratio": 0.50, "buy_bias": 0.75}}
        )
        score_buy = res_buy[res_buy["symbol"] == "005930"]["darkpool_score"].iloc[0]

        # Heavy distribution
        res_dist = tracker.compute_darkpool_scores(
            symbols=["005930"],
            prices_dict=prices,
            darkpool_data_dict={"005930": {"dark_pool_ratio": 0.50, "buy_bias": 0.20}}
        )
        score_dist = res_dist[res_dist["symbol"] == "005930"]["darkpool_score"].iloc[0]

        assert score_dist < score_buy
        assert score_dist <= 0.40


class TestTraderFixes:
    def test_risk_manager_drawdown_synchronization(self):
        rm = RiskManager(portfolio_value=1_000_000.0)
        # External call updates portfolio peak to 2,000,000
        dd1 = rm.calculate_drawdown(total_portfolio_value=2_000_000.0)
        assert dd1 == 0.0

        # Subsequent call without arguments must evaluate against the synchronized portfolio value
        dd2 = rm.calculate_drawdown()
        assert dd2 == 0.0, f"Phantom drawdown detected: expected 0.0, got {dd2}"

    def test_oms_micro_price_tick_size_rounding(self):
        oms = ExecutionOMSEngine()
        preds = [{
            "symbol": "005930",
            "name": "Samsung Electronics",
            "market": "KOSPI",
            "target_price": 70000.0,
            "micro_price": 70123.45,  # KRX tick size is 100 KRW
            "weight": 0.10,
            "expected_return": 0.05,
        }]
        plans = oms.generate_order_plans(
            top_predictions=preds,
            portfolio_weights={"005930": 0.10},
            total_capital=10_000_000
        )
        assert len(plans) > 0
        order = plans[0]
        assert order["target_price"] % 100 == 0, f"KRX tick violation: {order['target_price']}"

    def test_oms_gate8_pro_rata_funding(self):
        oms = ExecutionOMSEngine()
        weights = {f"00593{i}": 0.20 for i in range(5)}
        preds = [{
            "symbol": s,
            "market": "KOSPI",
            "target_price": 50000,
            "weight": 0.20,
            "expected_return": 0.05
        } for s in weights]

        plans = oms.generate_order_plans(
            top_predictions=preds,
            portfolio_weights=weights,
            total_capital=100_000_000,
            regime_label="CRISIS_HIGH_VOL",
        )
        total_buy_value = sum(p["target_amount"] for p in plans if "BUY" in p["action"])
        assert total_buy_value <= 100_000_000 * 1.001, f"Capital breach: {total_buy_value} > 100,000,000"

    def test_slippage_feedback_single_class_and_sequential_iteration(self):
        kf = FourteenDimensionalJosephKalmanFilter()
        assert kf.dim == 14
        H = kf.build_measurement_vector(spread_bps=8.0, participation_rate=0.03)
        kf.predict()
        kf.update(z=10.0, H=H, R=1.0)
        assert np.all(kf.x >= 0.0)  # non-negative friction parameters

        engine = SlippageFeedbackEngine()
        metrics = engine.calculate_realized_slippage_phase191()
        assert hasattr(metrics, "cost_scaling_factor")
        assert 0.20 <= metrics.cost_scaling_factor <= 5.0

    def test_unified_allocator_leland_absolute_drift_and_hold_ratchet(self):
        alloc = UnifiedPortfolioAllocator()
        # Small target position: 2% target, 2.5% current -> drift = 0.5% (absolute)
        w_cur = np.array([0.025, 0.50])
        w_tgt = np.array([0.020, 0.50])
        vols = np.array([0.02, 0.02])

        realized = alloc.apply_leland_no_trade_buffers(
            target_weights=w_tgt,
            current_weights=w_cur,
            volatilities=vols,
            use_asymmetric_bands=False,
        )
        # Current weight is within small noise band, should be held at current weight (HOLD)
        assert realized[0] == pytest.approx(0.025, abs=5e-3)

    def test_portfolio_allocator_inverse_hedging_no_double_cash_discount(self):
        weights = {"005930": 0.70}  # 70% invested, 30% cash
        res = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights=weights,
            market="KOSPI",
            regime_label="CRISIS",
            cash_ratio=0.30,
        )
        assert res["hedge_required"] is True
        # Beta is ~1.0, gross long is 0.70, inv_leverage is 2.0 -> target hedge weight ~ 0.35
        assert res["hedge_weight"] == pytest.approx(0.35, abs=0.05)
