"""
supply_chain.py — Value Chain & Supply Chain Momentum Engine (Strategy 19)

Computes lead-lag momentum spillover from primary customer companies (e.g., NVIDIA, Apple,
Samsung Electronics, Hyundai Motor) to supplier and equipment vendors with 1-3 day lag.
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

from .base_strategy import BaseStrategyEngine

logger = logging.getLogger(__name__)

# Key customer-supplier value chain mappings (Symbol -> Lead Market Leaders)
LEAD_CUSTOMER_MAP: Dict[str, List[str]] = {
    # Semiconductor Memory & Foundries -> Global Tech / AI Leaders
    "005930": ["NVDA", "AAPL", "MSFT", "GOOGL"], # Samsung Electronics -> NVDA/AAPL/MSFT
    "000660": ["NVDA", "AAPL", "MSFT"],         # SK Hynix -> NVDA/AAPL
    "TSM": ["AAPL", "NVDA", "AMD", "QCOM"],      # TSMC -> Apple/NVIDIA/AMD
    # KRX Semiconductor Equipment & Packaging Vendors -> Samsung / SK Hynix / NVDA
    "042700": ["000660", "005930", "NVDA"],     # Hanmi Semiconductor -> HBM Lead Vendor
    "036540": ["005930", "000660"],             # SFA -> Samsung / SK Hynix
    "240810": ["005930", "000660", "TSM"],      # Wonik IPS -> Memory/Foundry
    "039030": ["005930", "000660"],             # EO Technics -> Semiconductor Laser
    "058470": ["005930", "000660"],             # L&C Bio / Reno Industrial
    "095610": ["005930", "000660"],             # TES -> Memory Fab
    "036930": ["005930", "000660"],             # Ju Sung Engineering
    "084370": ["005930", "000660"],             # YIK -> Memory Test
    "101490": ["005930", "000660"],             # SnS Tech -> EUV Blankmask
    "108320": ["005930", "000660"],             # Dongjin Semichem -> PR / Materials
    "067310": ["005930", "000660"],             # Hana Micron -> OSAT
    "053690": ["005930", "000660"],             # HanKook M&A / Hana Materials
    "222800": ["005930", "000660"],             # Simmtech -> PCB / Substrate
    "077360": ["005930", "000660"],             # Duksan Neolux -> OLED
    # EV & Battery Value Chain -> Tesla / Hyundai / LG Energy Solution
    "373220": ["TSLA", "GM", "F"],              # LG Energy Solution -> Tesla / US Autos
    "006400": ["TSLA", "AAPL", "BMW"],          # Samsung SDI -> Tesla / Premium EV
    "051910": ["373220", "TSLA"],               # LG Chem -> LGES / Battery
    "247540": ["373220", "006400", "TSLA"],     # Ecopro BM -> Cathode to LGES / SDI
    "086520": ["247540", "373220"],             # Ecopro -> Battery Eco
    "003670": ["373220", "006400"],             # POSCO Future M -> Cathode/Anode
    "096770": ["373220", "F"],                  # SK Innovation -> SK On
    "278280": ["373220", "006400"],             # Chunbo -> Electrolyte Additive
    "137310": ["373220", "006400"],             # Cosmax / Cosmo AM&T
    "091990": ["005930", "373220"],             # Celltrion Healthcare
    # Automotive OEM & Tier-1 Suppliers -> Hyundai / Kia / Tesla
    "053800": ["TSLA", "TM"],                   # Hyundai Motor -> Global Auto
    "000270": ["053800", "TSLA"],               # Kia -> Hyundai / Global EV
    "012330": ["053800", "000270"],             # Hyundai Mobis -> Hyundai / Kia
    "018880": ["053800", "000270", "F"],        # Hanon Systems -> Thermal Mgmt
    "204320": ["053800", "000270"],             # HL Mando -> Chassis / ADAS
    "005830": ["053800", "000270"],             # DB Insurance / SL Corp -> Lighting
    "011210": ["053800", "000270"],             # Hyundai Wia -> Powertrain
    # US AI / Cloud Hardware Value Chain -> Megacap Tech Leaders
    "NVDA": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"], # Nvidia -> Hyperscalers
    "AMD": ["MSFT", "GOOGL", "AMZN", "META"],          # AMD -> Cloud Hyperscalers
    "ASML": ["TSM", "INTC", "005930"],                  # ASML -> Lithography Customers
    "AMAT": ["TSM", "005930", "INTC", "000660"],       # Applied Materials -> Fabs
    "LRCX": ["TSM", "000660", "005930"],               # Lam Research -> Memory & Foundry
    "KLAC": ["TSM", "005930", "INTC"],                 # KLA -> Process Control
    "AVGO": ["AAPL", "GOOGL", "META"],                 # Broadcom -> Custom Silicon / Networking
    "MRVL": ["MSFT", "AMZN", "GOOGL"],                 # Marvell -> AI Optical & DSP
    "ANET": ["MSFT", "META", "GOOGL"],                 # Arista Networks -> Cloud Switches
    "SMCI": ["NVDA", "AMD", "INTC"],                   # Super Micro -> GPU Server Integration
    "VRT": ["MSFT", "AMZN", "NVDA"],                   # Vertiv -> Data Center Power & Cooling
    "ARM": ["AAPL", "NVDA", "QCOM", "GOOGL"],          # ARM -> IP Licensees
    "MU": ["NVDA", "AAPL", "MSFT"],                    # Micron -> Memory / AI Server
    "QCOM": ["AAPL", "SAMSUNG", "XIAOMI"],             # Qualcomm -> Handset & Auto
}


from src.core.strategy_registry import register_strategy, StrategyMeta


@register_strategy(
    StrategyMeta(
        strategy_id="supply_chain",
        display_name="Supply Chain Lead-Lag",
        score_column="supply_chain_score",
        category="factor",
        output_file="supply_chain_predictions.txt",
        default_regime_weights={
            "BEAR": 0.03, "BEAR_HIGH_VOL": 0.02, "SIDEWAYS_LOW_VOL": 0.04, "BULL_HIGH_VOL": 0.05, "BULL_LOW_VOL": 0.04
        },
    )
)
class SupplyChainEngine(BaseStrategyEngine):
    """Strategy 19: Supply Chain Lead-Lag Momentum Engine.

    Calculates spillover momentum score (0% to 100%) for supplier stocks based on
    1D, 3D, and 5D returns of their key customer/lead market leaders with relation weights.
    """

    def __init__(self, customer_map: Optional[Dict[str, Any]] = None, map_path: Optional[str] = None) -> None:
        self.customer_weights_map: Dict[str, Dict[str, Any]] = {}
        if customer_map is not None:
            self.customer_map = customer_map
        else:
            self.customer_map = self._load_supply_chain_map_json(map_path) or LEAD_CUSTOMER_MAP

    def _load_supply_chain_map_json(self, map_path: Optional[str] = None) -> Dict[str, List[str]]:
        """Load structured supply chain mappings from JSON database."""
        import json
        from pathlib import Path

        search_paths = [
            Path(map_path) if map_path else None,
            Path(__file__).resolve().parent.parent.parent / "data" / "supply_chain_map.json",
            Path("trading_system/data/supply_chain_map.json"),
            Path("data/supply_chain_map.json"),
        ]

        for p in search_paths:
            if p and p.exists() and p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    flat_map: Dict[str, List[str]] = {}
                    sectors = data.get("sectors", {})
                    for _, s_info in sectors.items():
                        mappings = s_info.get("mappings", {})
                        for sym, m_info in mappings.items():
                            customers = m_info.get("customers", [])
                            weights = m_info.get("weights", [])
                            flat_map[sym] = customers
                            self.customer_weights_map[sym] = {
                                "customers": customers,
                                "weights": weights if len(weights) == len(customers) else [1.0 / len(customers)] * len(customers),
                                "role": m_info.get("role", "")
                            }
                    if flat_map:
                        logger.info(f"Loaded {len(flat_map)} supply chain relations from {p}")
                        return flat_map
                except Exception as ex:
                    logger.warning(f"Failed to parse supply chain map from {p}: {ex}")
        return LEAD_CUSTOMER_MAP

    def compute_scores(
        self,
        prices_dict: Any = None,
        fundamentals_dict: Optional[Dict[str, Dict[str, Any]]] = None,
        indicators_df: Optional[Any] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """Compute supply chain lead-lag momentum score for all universe symbols."""
        df_prices = kwargs.get("df_prices", prices_dict)
        universe = kwargs.get("universe", kwargs.get("universe_df", None))

        if universe is None or not isinstance(universe, pd.DataFrame) or universe.empty:
            if isinstance(fundamentals_dict, pd.DataFrame):
                universe = fundamentals_dict
            elif isinstance(prices_dict, pd.DataFrame):
                universe = prices_dict
            else:
                return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])

        results: List[Dict[str, Any]] = []
        if df_prices is None or universe.empty:
            return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])

        if isinstance(df_prices, dict):
            if not df_prices:
                return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])
            close_dict = {}
            for sym, df_p in df_prices.items():
                if df_p is not None and hasattr(df_p, 'empty') and not df_p.empty:
                    c_col = "Close" if "Close" in df_p.columns else ("close" if "close" in df_p.columns else None)
                    if c_col:
                        c = df_p[c_col]
                        if isinstance(c, pd.DataFrame):
                            c = c.iloc[:, 0]
                        close_dict[sym] = c
            if not close_dict:
                return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])
            close_pivot = pd.DataFrame(close_dict)
        elif isinstance(df_prices, pd.DataFrame):
            if df_prices.empty:
                return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])
            if "symbol" in df_prices.columns and "Close" in df_prices.columns:
                close_pivot = df_prices.pivot(index="Date" if "Date" in df_prices.columns else df_prices.index, columns="symbol", values="Close")
            else:
                close_pivot = df_prices
        else:
            return pd.DataFrame(columns=["symbol", "name", "market", "supply_chain_score"])

        # Compute 1D, 3D, and 5D returns for all symbols
        returns_1d = close_pivot.pct_change(1).iloc[-1] if len(close_pivot) >= 2 else pd.Series(dtype=float)
        returns_3d = close_pivot.pct_change(3).iloc[-1] if len(close_pivot) >= 4 else pd.Series(dtype=float)
        returns_5d = close_pivot.pct_change(5).iloc[-1] if len(close_pivot) >= 6 else pd.Series(dtype=float)

        def clean_sym(s: str) -> str:
            raw = s.split(".")[0].strip()
            return raw.zfill(6) if raw.isdigit() else raw

        for _, row in universe.iterrows():
            sym = str(row["symbol"]).strip()
            name = str(row.get("name", sym))
            mkt = str(row.get("market", "KRX"))
            c_key = clean_sym(sym)

            customers = self.customer_map.get(c_key, self.customer_map.get(sym, []))
            if not customers:
                score = 0.50
            else:
                # Check for explicit customer relation weights
                w_info = self.customer_weights_map.get(c_key, self.customer_weights_map.get(sym, {}))
                weights = w_info.get("weights", []) if w_info else []
                if not weights or len(weights) != len(customers):
                    weights = [1.0 / len(customers)] * len(customers)

                # Normalize weights to sum to 1.0
                sum_w = sum(weights) or 1.0
                weights = [w / sum_w for w in weights]

                cust_rets = []
                for c_sym, c_weight in zip(customers, weights):
                    r1 = float(returns_1d.get(c_sym, 0.0)) if not pd.isna(returns_1d.get(c_sym, np.nan)) else 0.0
                    r3 = float(returns_3d.get(c_sym, 0.0)) if not pd.isna(returns_3d.get(c_sym, np.nan)) else 0.0
                    r5 = float(returns_5d.get(c_sym, 0.0)) if not pd.isna(returns_5d.get(c_sym, np.nan)) else 0.0
                    spillover_ret = 0.50 * r1 + 0.30 * r3 + 0.20 * r5
                    cust_rets.append(spillover_ret * c_weight)

                weighted_cust_ret = float(np.sum(cust_rets)) if cust_rets else 0.0
                score = float(np.clip(0.50 + weighted_cust_ret * 5.0, 0.0, 1.0))

            results.append({
                "symbol": sym,
                "name": name,
                "market": mkt,
                "supply_chain_score": round(score, 4),
            })

        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df = res_df.sort_values(by="supply_chain_score", ascending=False).reset_index(drop=True)
        return res_df
