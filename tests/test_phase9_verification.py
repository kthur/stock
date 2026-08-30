"""
Phase 9 Next-Generation System Verification Test Suite
Tests all 11 Phase 9 components across Quant AI, Microstructure & HFT, and MLOps:
- FeatureStoreManager (Feast Feature Store)
- TimescaleDBConnector (TimescaleDB / High-throughput storage)
- RayClusterOrchestrator (Ray Distributed Compute)
- PipelineObservability (OpenTelemetry & Prometheus)
- PatchTSTFoundationModel (Strategy #34 Time-Series Transformer)
- MultiAgentNLPEngine (Strategy #35 Multi-Agent LLM & Tone Drift)
- GNNSupplyChainLeadLagEngine (Strategy #36 GAT Supply Chain)
- DRLPortfolioAllocator (PPO/SAC DRL Agent)
- LimitOrderBookCalculator (L2/L3 OBI & Micro-Price)
- VPINCalculator (VPIN Adverse Selection Toxicity)
- SmartOrderRouter (SOR Nextrade/ATS Router)
"""

import numpy as np
import pandas as pd
import tempfile
import os

from src.feature_store.feature_definitions import FeatureStoreManager
from src.data_layer.timescale_db import TimescaleDBConnector
from src.utils.ray_cluster import RayClusterOrchestrator
from src.utils.observability import PipelineObservability
from src.ai.foundation_model import PatchTSTFoundationModel
from src.core.multi_agent_nlp import MultiAgentNLPEngine
from src.ai.gnn_lead_lag import GNNSupplyChainLeadLagEngine
from src.risk.drl_allocator import DRLPortfolioAllocator
from src.core.lob_obi import LimitOrderBookCalculator
from src.core.vpin_calculator import VPINCalculator
from src.execution.sor_router import SmartOrderRouter


def test_feast_feature_store_manager():
    fs = FeatureStoreManager()
    keys = [{"symbol": "005930"}, {"symbol": "AAPL"}]
    feats = ["volatility_20d", "momentum_12m_1m"]
    res = fs.get_online_features(keys, feats)
    assert len(res) == 2
    assert "volatility_20d" in res[0]


def test_timescaledb_connector():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_ts.db")
        ts = TimescaleDBConnector(fallback_sqlite_path=db_path)
        records = [
            {"time": "2026-08-13", "symbol": "005930", "market": "KOSPI", "open": 70000, "high": 71000, "low": 69500, "close": 70500, "volume": 1000000}
        ]
        assert ts.batch_insert_prices(records) is True


def test_ray_cluster_orchestrator():
    orchestrator = RayClusterOrchestrator()
    def square(x):
        return x * x
    items = [1, 2, 3, 4, 5]
    res = orchestrator.parallel_map(square, items)
    assert res == [1, 4, 9, 16, 25]


def test_pipeline_observability():
    obs = PipelineObservability()
    with obs.trace_stage("test_stage"):
        pass
    obs.record_metric("vix_value", 18.5)
    metrics = obs.get_all_metrics()
    assert "test_stage" in metrics
    assert metrics["vix_value"] == 18.5


def test_patchtst_foundation_model():
    model = PatchTSTFoundationModel()
    np.random.seed(42)
    prices = np.linspace(100, 150, 50) + np.random.normal(0, 2, 50)
    pred_ret = model.predict_patches(prices)
    assert isinstance(pred_ret, float)

    universe = pd.DataFrame([{"symbol": "005930", "name": "Samsung", "market": "KOSPI"}])
    price_dict = {"005930": pd.DataFrame({"Close": prices})}
    scores_df = model.calculate_scores(price_dict, universe)
    assert len(scores_df) == 1
    assert "patchtst_score" in scores_df.columns


def test_multi_agent_nlp_engine():
    engine = MultiAgentNLPEngine()
    res = engine.analyze_filing_text("Record revenue and margin growth achieved.", "Litigation pending.")
    assert res["catalyst_score"] > 50.0
    assert "tone_drift_score" in res

    universe = pd.DataFrame([{"symbol": "005930", "name": "Samsung", "market": "KOSPI"}])
    scores_df = engine.compute_scores(universe)
    assert len(scores_df) == 1
    assert "multi_agent_nlp_score" in scores_df.columns


def test_gnn_supply_chain_lead_lag():
    engine = GNNSupplyChainLeadLagEngine()
    universe = pd.DataFrame([
        {"symbol": "005930", "name": "Samsung", "market": "KOSPI"},
        {"symbol": "000660", "name": "SKHynix", "market": "KOSPI"}
    ])
    prices_dict = {
        "005930": pd.DataFrame({"Close": [100.0, 105.0]}),
        "000660": pd.DataFrame({"Close": [200.0, 202.0]})
    }
    graph = {"000660": ["005930"]}
    scores_df = engine.calculate_scores(universe, prices_dict, supply_chain_graph=graph)
    assert len(scores_df) == 2
    assert "gnn_lead_lag_score" in scores_df.columns


def test_drl_portfolio_allocator():
    allocator = DRLPortfolioAllocator()
    w = np.array([0.5, 0.5])
    w_prev = np.array([0.4, 0.6])
    r = np.array([0.02, 0.01])
    cov = np.array([[0.0004, 0.0001], [0.0001, 0.0003]])
    costs = np.array([0.0015, 0.0015])

    reward = allocator.compute_drl_reward(w, w_prev, r, cov, costs)
    assert isinstance(reward, float)

    preds = pd.DataFrame([{"symbol": "005930", "ensemble_score": 75.0}, {"symbol": "000660", "ensemble_score": 85.0}])
    returns_df = pd.DataFrame(np.random.normal(0, 0.02, (20, 2)), columns=["005930", "000660"])
    weights = allocator.allocate_weights_drl(preds, returns_df)
    assert len(weights) == 2
    assert abs(sum(weights.values()) - 1.0) < 1e-4


def test_limit_order_book_calculator():
    calc = LimitOrderBookCalculator()
    micro = calc.calculate_micro_price(70000.0, 1000.0, 70100.0, 500.0)
    assert 70000.0 < micro < 70100.0

    bids = [{"price": 70000.0, "volume": 1000.0}]
    asks = [{"price": 70100.0, "volume": 500.0}]
    snapshot = {"bids": bids, "asks": asks}

    eval_res = calc.evaluate_lob_snapshot(snapshot)
    assert "obi" in eval_res and "micro_price" in eval_res
    assert eval_res["obi"] > 0.0


def test_vpin_calculator():
    vpin_calc = VPINCalculator()
    prices = np.array([100.0, 101.0, 102.0, 101.5, 103.0])
    volumes = np.array([1000, 1500, 1200, 800, 2000])

    vpin = vpin_calc.compute_vpin(prices, volumes, bucket_volume=1000.0)
    assert 0.0 <= vpin <= 1.0

    risk = vpin_calc.evaluate_toxicity_risk(vpin, threshold=0.75)
    assert "is_toxic" in risk and "recommended_action" in risk


def test_smart_order_router():
    sor = SmartOrderRouter()
    venues = [
        {"venue_id": "NXT_ATS", "ask_price": 70000.0, "ask_vol": 500, "fee_bps": -0.5},
        {"venue_id": "KRX_PRIMARY", "ask_price": 70050.0, "ask_vol": 2000, "fee_bps": 0.5}
    ]
    routes = sor.route_order("005930", "BUY", total_quantity=1000, venues=venues)
    assert len(routes) >= 1
    assert sum(r["allocated_quantity"] for r in routes) == 1000
    assert routes[0]["venue_id"] == "NXT_ATS"  # Cheapest venue first
