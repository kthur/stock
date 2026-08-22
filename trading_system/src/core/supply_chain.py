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
    "137310": ["373220", "006400"],             # Cosmo AM&T -> Cathode
    "068270": ["JNJ", "PFE", "NVO"],            # Celltrion -> Global Bio / Pharma
    # Automotive OEM & Tier-1 Suppliers -> Hyundai / Kia / Tesla
    "005380": ["TSLA", "TM"],                   # Hyundai Motor -> Global Auto
    "000270": ["005380", "TSLA"],               # Kia -> Hyundai / Global EV
    "012330": ["005380", "000270"],             # Hyundai Mobis -> Hyundai / Kia
    "018880": ["005380", "000270", "F"],        # Hanon Systems -> Thermal Mgmt
    "204320": ["005380", "000270"],             # HL Mando -> Chassis / ADAS
    "005850": ["005380", "000270"],             # SL Corp -> Auto Lighting
    "011210": ["005380", "000270"],             # Hyundai Wia -> Powertrain
    # Global Technology & Semiconductor Supply Chain (TW, JP, EU, US, KR)
    "2330.TW": ["NVDA", "AAPL", "AMD", "QCOM"],         # TSMC -> Global Tech Giants
    "2454.TW": ["AAPL", "005930", "QCOM"],              # MediaTek -> Handset Ecosystem
    "2317.TW": ["AAPL", "NVDA", "TSLA"],                # Hon Hai (Foxconn) -> Apple/Nvidia
    "2308.TW": ["NVDA", "MSFT", "TSLA"],                # Delta Electronics -> AI Power
    "2382.TW": ["NVDA", "MSFT", "GOOGL"],               # Quanta Computer -> AI Servers
    "8035.T": ["2330.TW", "005930", "000660", "INTC"],  # Tokyo Electron -> Fabs
    "6857.T": ["NVDA", "2330.TW", "000660"],            # Advantest -> AI Testers
    "6758.T": ["AAPL", "MSFT", "SONY"],                 # Sony -> Image Sensors / Gaming
    "6981.T": ["AAPL", "005930"],                       # Murata -> MLCC to Apple/Samsung
    "6861.T": ["7203.T", "005930", "AAPL"],             # Keyence -> Sensors / Automation
    "4063.T": ["2330.TW", "005930", "INTC"],            # Shin-Etsu -> Silicon Wafers
    "7741.T": ["2330.TW", "ASML", "005930"],            # HOYA -> EUV Blankmasks
    "ASML.AS": ["2330.TW", "005930", "000660", "INTC"], # ASML Holding -> Lithography Fabs
    "SAP.DE": ["MSFT", "ORCL", "CRM"],                  # SAP -> Enterprise Cloud
    # Global IT & Auto Value Chain (India, Canada, Europe)
    "INFY.NS": ["MSFT", "GOOGL", "AAPL"],               # Infosys -> US Tech Cloud
    "TCS.NS": ["MSFT", "AAPL", "IBM"],                  # Tata Consultancy -> Global IT
    "TATAMOTORS.NS": ["TSLA", "005380"],                # Tata Motors -> Global EV
    "SHOP.TO": ["AMZN", "GOOGL"],                       # Shopify -> Global E-commerce
    # Global EV, Battery & Material Supply Chain (CN, JP, KR, AU, BR)
    "300750.SZ": ["TSLA", "BMW", "005380"],             # CATL -> Global EV
    "002594.SZ": ["TSLA"],                              # BYD -> Global Auto/Battery
    "7203.T": ["TSLA"],                                 # Toyota -> Global Auto
    "BHP.AX": ["005490", "POSCO", "VALE"],              # BHP -> Global Steel & Energy
    "RIO.AX": ["005490", "BHP"],                        # Rio Tinto -> Global Metals
    "FMG.AX": ["005490", "BHP"],                        # Fortescue -> Global Iron Ore
    "VALE3.SA": ["005490", "BHP", "PKX"],               # Vale -> Global Iron Ore
    "PETR4.SA": ["XOM", "CVX", "CL=F"],                 # Petrobras -> Global Oil
    "D05.SI": ["SGX", "HSBA.L"],                        # DBS Bank -> Asian Financial Flow
    "VNM.VN": ["005930"],                               # Vinamilk -> Consumer Flow
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
            elif isinstance(df_prices, dict) and df_prices:
                universe = pd.DataFrame([
                    {"symbol": s, "name": s, "market": "KOSPI" if str(s).isdigit() else "SP500"}
                    for s in df_prices.keys()
                ])
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
        # Timezone-aware approach: ffill() propagates latest valid prices rather than hardcoded shifting,
        # naturally aligning US (T-1 or T) to KR (T) depending on run time.
        close_pivot_filled = close_pivot.ffill()
        returns_1d = close_pivot_filled.pct_change(1).iloc[-1] if len(close_pivot_filled) >= 2 else pd.Series(dtype=float)
        returns_3d = close_pivot_filled.pct_change(3).iloc[-1] if len(close_pivot_filled) >= 4 else pd.Series(dtype=float)
        returns_5d = close_pivot_filled.pct_change(5).iloc[-1] if len(close_pivot_filled) >= 6 else pd.Series(dtype=float)

        def clean_sym(s: str) -> str:
            raw = s.split(".")[0].strip()
            return raw.zfill(6) if raw.isdigit() else raw

        for row in universe.itertuples(index=False):
            r_dict = row._asdict() if hasattr(row, '_asdict') else dict(zip(universe.columns, row))
            sym = str(r_dict.get("symbol", "")).strip()
            name = str(r_dict.get("name", sym))
            mkt = str(r_dict.get("market", "KRX"))
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

                # Compute US proxy return from indicators_df if present
                us_proxy_1d = 0.0
                if indicators_df is not None:
                    if isinstance(indicators_df, pd.DataFrame) and not indicators_df.empty:
                        for col_candidate in ['nasdaq_change', 'sp500_change', 'nasdaq', 'sp500']:
                            if col_candidate in indicators_df.columns:
                                val = indicators_df[col_candidate].iloc[-1]
                                if pd.notna(val):
                                    us_proxy_1d = float(val) / 100.0 if abs(val) > 0.5 else float(val)
                                    break
                    elif isinstance(indicators_df, dict):
                        for col_candidate in ['nasdaq_change', 'sp500_change', 'nasdaq', 'sp500']:
                            if col_candidate in indicators_df:
                                val = indicators_df[col_candidate]
                                if pd.notna(val):
                                    us_proxy_1d = float(val) / 100.0 if abs(val) > 0.5 else float(val)
                                    break

                cust_rets = []
                for c_sym, c_weight in zip(customers, weights):
                    r1_series = returns_1d
                    r3_series = returns_3d
                    r5_series = returns_5d

                    if c_sym in r1_series and pd.notna(r1_series.get(c_sym)):
                        r1 = float(r1_series.get(c_sym))
                        r3 = float(r3_series.get(c_sym, r1)) if pd.notna(r3_series.get(c_sym, np.nan)) else r1
                        r5 = float(r5_series.get(c_sym, r1)) if pd.notna(r5_series.get(c_sym, np.nan)) else r1
                    else:
                        # Fallback to US tech proxy for US leaders not present in prices_dict
                        is_us_leader = c_sym.upper() in ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'AMZN', 'ASML', 'TSM', 'GOOGL', 'META']
                        r1 = us_proxy_1d if is_us_leader else 0.0
                        r3 = r1 * 1.5
                        r5 = r1 * 2.0
                    # Non-linear Asymmetric Bullwhip Spillover (Forrester 1961, Lee et al. 1997):
                    # Downside customer shocks transmit immediately with panic amplification (1.35x),
                    # while upside demand expands with CAPEX gestation smoothing.
                    if r1 < 0:
                        r1_eff = r1 * 1.35
                    else:
                        r1_eff = float(np.sign(r1) * (abs(r1) ** 0.90) * 0.95)

                    if r3 < 0:
                        r3_eff = r3 * 1.25
                    else:
                        r3_eff = r3 * 1.05

                    spillover_ret = 0.45 * r1_eff + 0.35 * r3_eff + 0.20 * r5
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

    def compute_graph_diffusion_momentum(
        self,
        returns_series: pd.Series,
        max_hops: int = 2,
        damping_factor: float = 0.50
    ) -> pd.Series:
        """
        Computes multi-hop Graph Convolutional Diffusion momentum across supplier networks:
        H^(l+1) = sigma( D^-1/2 (A + I) D^-1/2 H^l )
        """
        if returns_series.empty:
            return returns_series

        all_syms = list(set(returns_series.index) | set(self.customer_map.keys()))
        sym_to_idx = {s: i for i, s in enumerate(all_syms)}
        N = len(all_syms)

        # Adjacency Matrix A
        A = np.zeros((N, N), dtype=float)
        for supp, custs in self.customer_map.items():
            if supp in sym_to_idx:
                s_idx = sym_to_idx[supp]
                for c in custs:
                    if c in sym_to_idx:
                        c_idx = sym_to_idx[c]
                        A[s_idx, c_idx] = 1.0

        # Renormalization Trick: A_tilde = A + I
        A_tilde = A + np.eye(N)
        deg = np.sum(A_tilde, axis=1)
        deg_inv_sqrt = np.power(np.maximum(deg, 1.0), -0.5)
        D_inv_sqrt = np.diag(deg_inv_sqrt)

        # Normalized Graph Diffusion Operator
        A_norm = D_inv_sqrt @ A_tilde @ D_inv_sqrt

        # Initial Signal vector H0
        H = np.zeros(N, dtype=float)
        for s, r in returns_series.items():
            if s in sym_to_idx:
                H[sym_to_idx[s]] = float(r) if pd.notna(r) else 0.0

        # Multi-hop diffusion
        diffused_H = H.copy()
        current_H = H.copy()
        for hop in range(1, max_hops + 1):
            current_H = (damping_factor ** hop) * (A_norm @ current_H)
            diffused_H += current_H

        diffused_series = pd.Series(
            [float(diffused_H[sym_to_idx[s]]) for s in returns_series.index],
            index=returns_series.index
        )
        return diffused_series

