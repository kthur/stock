import os
import sys
import unittest
import numpy as np
import pandas as pd

# Add paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../trading_system')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk.portfolio_allocator import PortfolioAllocator
from src.ai.ensemble_scorer import EnsembleScoringEngine
from src.execution.oms_engine import ExecutionOMSEngine
from src.core.supply_chain import SupplyChainEngine


class TestInstitutionalTier1AuditEnhancements(unittest.TestCase):

    def setUp(self):
        self.allocator = PortfolioAllocator(default_max_weight=0.20)
        self.ensemble = EnsembleScoringEngine()
        self.oms = ExecutionOMSEngine(db_path=":memory:")
        self.supply_chain = SupplyChainEngine()

    # -------------------------------------------------------------------------
    # 1. Synthetic Beta Inverse Hedge Overlay in Bear Regimes
    # -------------------------------------------------------------------------
    def test_synthetic_inverse_hedge_overlay(self):
        """Verify compute_synthetic_inverse_hedge creates valid hedge allocation in Bear regime."""
        weights = {"005930": 0.30, "000660": 0.30, "035420": 0.20}
        beta_map = {"005930": 1.2, "000660": 1.4, "035420": 0.9}

        # In BULL regime -> No hedge required
        hedge_bull = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights=weights,
            market="KOSPI",
            regime_label="BULL",
            beta_map=beta_map
        )
        self.assertFalse(hedge_bull["hedge_required"])
        self.assertEqual(hedge_bull["hedge_weight"], 0.0)

        # In BEAR regime -> Hedge required using 114800 (KODEX 200 선물인버스2X)
        hedge_bear = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights=weights,
            market="KOSPI",
            regime_label="BEAR_HIGH_VOL",
            beta_map=beta_map,
            cash_ratio=0.10
        )
        self.assertTrue(hedge_bear["hedge_required"])
        self.assertEqual(hedge_bear["hedge_symbol"], "114800")
        self.assertEqual(hedge_bear["hedge_leverage"], 2.0)
        self.assertGreater(hedge_bear["hedge_weight"], 0.0)
        # Net portfolio beta after hedge should be neutralized towards zero
        self.assertLess(hedge_bear["net_portfolio_beta"], hedge_bear["portfolio_beta_before"] * 0.5)

        # In US NASDAQ Bear regime -> Hedge using PSQ
        hedge_us = PortfolioAllocator.compute_synthetic_inverse_hedge(
            portfolio_weights={"AAPL": 0.40, "NVDA": 0.40},
            market="NASDAQ",
            regime_label="BEAR"
        )
        self.assertTrue(hedge_us["hedge_required"])
        self.assertEqual(hedge_us["hedge_symbol"], "PSQ")

    # -------------------------------------------------------------------------
    # 2. ADV Market Capacity Bounds (1.5% ADV Limit)
    # -------------------------------------------------------------------------
    def test_adv_capacity_constraint(self):
        """Verify apply_adv_capacity_constraint caps trade value to 1.5% ADV."""
        weights = {"005930": 0.20, "SMALLCAP": 0.20}
        # SMALLCAP has only 100M KRW ADV, 005930 has 500B KRW ADV
        adv_map = {"005930": 500_000_000_000.0, "SMALLCAP": 100_000_000.0}
        tot_cap = 100_000_000.0  # 100M KRW capital

        # SMALLCAP target trade = 20M KRW, but 1.5% of 100M ADV is 1.5M KRW
        constrained = PortfolioAllocator.apply_adv_capacity_constraint(
            target_weights=weights,
            adv_map=adv_map,
            total_capital=tot_cap,
            max_adv_ratio=0.015
        )

        self.assertIn("005930", constrained)
        self.assertIn("SMALLCAP", constrained)
        # SMALLCAP weight should be significantly damped
        self.assertLess(constrained["SMALLCAP"], 0.05)
        # 005930 with huge ADV should retain its full weight
        self.assertGreaterEqual(constrained["005930"], 0.20)

    # -------------------------------------------------------------------------
    # 3. Dynamic Information Ratio (IR) Gating
    # -------------------------------------------------------------------------
    def test_dynamic_ir_gating(self):
        """Verify apply_dynamic_ir_gating prunes negative IR strategies to 0.0%."""
        base_weights = {
            "regression": 0.30,
            "surge": 0.20,
            "decayed_strategy": 0.25,
            "rim_valuation": 0.25
        }
        # decayed_strategy has negative IR (-0.45)
        strategy_ir = {
            "regression": 1.20,
            "surge": 0.80,
            "decayed_strategy": -0.45,
            "rim_valuation": 1.50
        }

        gated = EnsembleScoringEngine.apply_dynamic_ir_gating(
            base_weights=base_weights,
            strategy_ic_or_ir_map=strategy_ir,
            ir_cutoff=0.0
        )

        self.assertEqual(gated.get("decayed_strategy", 0.0), 0.0)
        self.assertGreater(gated.get("regression", 0.0), 0.0)
        self.assertGreater(gated.get("rim_valuation", 0.0), 0.0)
        self.assertAlmostEqual(sum(gated.values()), 1.0, places=4)

    # -------------------------------------------------------------------------
    # 4. Pre-Market Delta Modifier (Overnight & Auction Imbalance)
    # -------------------------------------------------------------------------
    def test_premarket_delta_modifier(self):
        """Verify apply_premarket_delta_modifier scales scores by overnight gap & auction imbalance."""
        df_scores = pd.DataFrame({
            "symbol": ["005930", "000660", "035420"],
            "ensemble_score": [0.60, 0.55, 0.50]
        })

        # NVDA/SOX surged overnight (+3.0%) & 000660 has strong buy imbalance (+5.0%)
        imbalance_map = {"000660": 0.05, "005930": 0.01, "035420": -0.04}
        modified = EnsembleScoringEngine.apply_premarket_delta_modifier(
            base_scores_df=df_scores,
            overnight_macro_delta=0.03,
            premarket_imbalance_map=imbalance_map,
            gamma_overnight=0.35
        )

        self.assertEqual(len(modified), 3)
        self.assertTrue((modified["ensemble_score"] >= 0.0).all() and (modified["ensemble_score"] <= 1.0).all())
        # 000660 with strong buy imbalance should receive a boost
        score_000660_after = modified.loc[modified["symbol"] == "000660", "ensemble_score"].iloc[0]
        self.assertGreater(score_000660_after, 0.55)

    # -------------------------------------------------------------------------
    # 5. OMS Engine: ADV Capacity Capping & Bear Regime Hedge Order Generation
    # -------------------------------------------------------------------------
    def test_oms_adv_capacity_and_hedge_order_generation(self):
        """Verify OMS Engine applies ADV cap Gate 7.5 and generates inverse hedge in Bear regime."""
        preds = [
            {
                "symbol": "005930",
                "name": "삼성전자",
                "market": "KOSPI",
                "close_price": 70000.0,
                "target_price": 70000.0,
                "expected_return": 15.0,
                "adv": 500_000_000_000.0
            },
            {
                "symbol": "000660",
                "name": "SK하이닉스",
                "market": "KOSPI",
                "close_price": 180000.0,
                "target_price": 180000.0,
                "expected_return": 18.0,
                "adv": 50_000_000.0  # Very small ADV (50M KRW)
            }
        ]
        weights = {"005930": 0.40, "000660": 0.40}

        plans = self.oms.generate_order_plan(
            top_predictions=preds,
            portfolio_weights=weights,
            total_capital=100_000_000.0,
            regime_label="BEAR_HIGH_VOL",
            max_adv_ratio=0.015
        )

        self.assertGreater(len(plans), 0)
        symbols_planned = [p["symbol"] for p in plans]
        actions_planned = [p["action"] for p in plans]

        # 1. Check ADV Capacity Capping on small ADV stock
        for p in plans:
            if p["symbol"] == "000660":
                # Max target amount = 0.015 * 50M = 750,000 KRW
                self.assertLessEqual(p["target_amount"], 800_000.0)

        # 2. Check Synthetic Inverse Hedge Order Plan generated
        self.assertIn("114800", symbols_planned)
        self.assertIn("BUY_HEDGE", actions_planned)

    # -------------------------------------------------------------------------
    # 6. Supply Chain Graph Diffusion Momentum
    # -------------------------------------------------------------------------
    def test_graph_diffusion_momentum(self):
        """Verify compute_graph_diffusion_momentum propagates signals across multi-hop suppliers."""
        # NVDA surges (+10%), SK Hynix (000660) and Hanmi Semi (042700) should receive diffused momentum
        rets = pd.Series({"NVDA": 0.10, "000660": 0.02, "042700": 0.01, "005930": 0.01})
        diffused = self.supply_chain.compute_graph_diffusion_momentum(
            returns_series=rets,
            max_hops=2,
            damping_factor=0.50
        )

        self.assertEqual(len(diffused), 4)
        # Hanmi Semi (042700) is downstream supplier to 000660 & NVDA, should receive positive diffusion
        self.assertGreater(diffused["042700"], rets["042700"])


if __name__ == "__main__":
    unittest.main()
