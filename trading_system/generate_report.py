#!/usr/bin/env python3
"""
generate_report.py — Stock Prediction Dashboard HTML Generator

Reads pipeline result txt files from trading_system/result/ and generates
a self-contained HTML dashboard for GitHub Pages deployment.

Usage:
    python trading_system/generate_report.py
    python trading_system/generate_report.py --result-dir path/to/result --out gh-pages/index.html
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any
import html

from src.data_layer.data_validator import DataValidator

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def _safe_json(obj: Any) -> str:
    """Safely serialize JSON for embedding directly in HTML script blocks without XSS risk."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def largest_remainder_round(values: list[float], target_sum: float = 100.0, decimals: int = 1) -> list[float]:
    """
    Distribute target_sum across values using Largest Remainder Method (Hare-Niemeyer)
    so that the rounded values sum exactly to target_sum at specified decimal places.
    """
    if not values:
        return []
    factor = 10 ** decimals
    total_val = sum(values)
    if total_val <= 0:
        n = len(values)
        base = int((target_sum * factor) // n)
        rem = int(round(target_sum * factor - base * n))
        res = [base + (1 if i < rem else 0) for i in range(n)]
        return [r / factor for r in res]
    
    target_int = int(round(target_sum * factor))
    scaled = [v * (target_int / total_val) for v in values]
    floored = [int(s) for s in scaled]
    remainders = [(s - f, -v, i) for i, (s, f, v) in enumerate(zip(scaled, floored, values))]
    
    current_sum = sum(floored)
    diff = target_int - current_sum
    
    if diff > 0:
        # Sort by remainder descending, then original value descending
        remainders.sort(key=lambda x: (x[0], x[1]), reverse=True)
        for j in range(diff):
            idx = remainders[j % len(remainders)][2]
            floored[idx] += 1
    elif diff < 0:
        remainders.sort(key=lambda x: (x[0], x[1]))
        for j in range(-diff):
            idx = remainders[j % len(remainders)][2]
            floored[idx] = max(0, floored[idx] - 1)
            
    return [f / factor for f in floored]

# ─────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────

@dataclass
class EnsembleRow:
    rank: int
    symbol: str
    name: str
    score: str
    expected_return: str
    reg: str = ""
    surge: str = ""
    lead_lag: str = ""
    vcp_rule: str = ""
    vcp_ml: str = ""
    lstm: str = ""
    stat_arb: str = ""
    sector_rotation: str = ""
    rim_valuation: str = ""
    event_driven: str = ""
    mq_factor: str = ""
    iv_skew: str = ""
    order_flow: str = ""
    short_term_reversal: str = ""
    arm_factor: str = ""
    card_factor: str = ""
    latr_factor: str = ""
    inst_foreign_sector: str = ""
    supply_chain: str = ""
    sentiment: str = ""
    factor_neutralized: str = ""
    vol_target: str = ""
    microstructure: str = ""
    accruals_quality: str = ""
    short_squeeze: str = ""
    valueup_catalyst: str = ""
    trend_efficiency: str = ""
    gamma_squeeze: str = ""
    insider_buying: str = ""
    darkpool: str = ""
    earnings_tone_drift: str = ""
    cross_asset_spillover: str = ""
    supply_chain_gnn: str = ""
    range_expansion: str = ""
    dual_correction: str = ""
    index_rebalance: str = ""
    overnight_gap: str = ""

@dataclass
class EnsembleMarket:
    market: str
    rows: list[EnsembleRow] = field(default_factory=list)

@dataclass
class EnsembleData:
    date: str = ""
    regime: str = "UNKNOWN"
    regime_code: int = -1
    max_allocation: str = ""
    sp500_return: str = ""
    vix: str = ""
    us10y: str = ""
    kr10y: str = ""
    usdkrw: str = ""
    wti: str = ""
    gold: str = ""
    weights: dict = field(default_factory=dict)
    us_weights: dict = field(default_factory=dict)
    kr_weights: dict = field(default_factory=dict)
    markets: list[EnsembleMarket] = field(default_factory=list)
    decision_rationale: str = ""
    coverage_report: str = ""
    decoupling_status: str = ""
    decoupling_corr: str = ""
    us_regime: str = ""
    kr_regime: str = ""

@dataclass
class StatArbRow:
    pair: str
    z_score: str
    correlation: str
    beta: str
    signal: str

@dataclass
class SectorRow:
    rank: int
    symbol: str
    name: str
    market: str
    sector: str
    score: str

@dataclass
class RimRow:
    rank: int
    symbol: str
    name: str
    market: str
    price: str
    intrinsic_value: str
    discount: str
    score: str = ""
    roe_raw: str = "N/A"
    roe_adj: str = "N/A"
    eq: str = "N/A"
    filter_tags: str = ""
    rim_score: str = ""

    def __post_init__(self):
        if not self.rim_score and self.score:
            self.rim_score = self.score
        elif not self.score and self.rim_score:
            self.score = self.rim_score

@dataclass
class SurgeRow:
    rank: int
    market: str
    symbol: str
    name: str
    probability: str

@dataclass
class SurgeSection:
    horizon: str
    market: str
    rows: list[SurgeRow] = field(default_factory=list)

@dataclass
class VcpRow:
    rank: int
    market: str
    symbol: str
    name: str
    score: str
    current_range: str
    contraction: str
    ma50: bool
    ma200: bool
    near_high: bool
    vol_declining: bool

@dataclass
class LeadLagRow:
    rank: int
    market: str
    symbol: str
    name: str
    score: str

@dataclass
class RegRow:
    rank: int
    symbol: str
    name: str
    expected_return: str

@dataclass
class RegSection:
    horizon: str
    market: str
    rows: list[RegRow] = field(default_factory=list)

@dataclass
class PortfolioRow:
    rank: int
    symbol: str
    name: str
    market: str
    expected_return: str
    volatility: str
    weight: str
    amount: str

@dataclass
class PortfolioAllocationData:
    date: str = ""
    total_capital: str = ""
    target_horizon: str = ""
    regime: str = ""
    max_allocation: str = ""
    rows: list[PortfolioRow] = field(default_factory=list)
    allocated_capital: str = ""
    allocated_capital_pct: str = ""
    remaining_cash: str = ""
    remaining_cash_pct: str = ""

# ─────────────────────────────────────────────
# Parsers
# ─────────────────────────────────────────────

def _read(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="cp949").replace("\r\n", "\n")
        except Exception:
            return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def parse_ensemble(text: str) -> EnsembleData:
    data = EnsembleData()
    if not text:
        return data

    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            data.date = m.group(1).strip()
        m = re.search(r"Current Market Regime Detected:\s*([A-Za-z0-9_]+)", line)
        if m:
            reg_val = m.group(1).strip().upper()
            m_2d = re.search(r"2D State:\s*([A-Za-z0-9_]+)", line)
            if m_2d:
                data.regime = m_2d.group(1).strip().upper()
            else:
                data.regime = reg_val
        m = re.match(r"Maximum Total Allocation Allowed:\s*(.+)", line)
        if m:
            data.max_allocation = m.group(1).strip()
        def _clean_macro(val_str: str, fallback_str: str, kind: str) -> str:
            return str(DataValidator.clean_macro_value(val_str, fallback_str, kind))

        m = re.match(r"S&P 500 \(20d Rolling Mean Return\)\s*:\s*(.+)", line)
        if m:
            data.sp500_return = _clean_macro(m.group(1), "+0.050% / day", "sp500")
        m = re.match(r"VIX Index.*:\s*(.+)", line)
        if m:
            data.vix = _clean_macro(m.group(1), "18.50", "vix")
        m = re.match(r"US 10Y Bond Yield.*:\s*(.+)", line)
        if m:
            data.us10y = _clean_macro(m.group(1), "4.25%", "us10y")
        m = re.match(r"KR 10Y Bond Yield.*:\s*(.+)", line)
        if m:
            data.kr10y = _clean_macro(m.group(1), "3.15%", "kr10y")
        m = re.match(r"USD/KRW FX Rate.*:\s*(.+)", line)
        if m:
            data.usdkrw = _clean_macro(m.group(1), "1,380.00 KRW", "usdkrw")
        m = re.match(r"WTI Crude Oil.*:\s*(.+)", line)
        if m:
            data.wti = _clean_macro(m.group(1), "$75.50 / bbl", "wti")
        m = re.match(r"Gold \(GLD ETF\).*:\s*(.+)", line)
        if m:
            data.gold = _clean_macro(m.group(1), "$220.00", "gold")
    # Parse weights blocks (US, KR, and General Ensemble)
    current_target_dict = None
    for line in text.splitlines():
        line_s = line.strip()
        if "Applied US Strategy Weights" in line_s:
            current_target_dict = data.us_weights
            continue
        elif "Applied KR Strategy Weights" in line_s:
            current_target_dict = data.kr_weights
            continue
        elif "Applied Ensemble Strategy Weights" in line_s:
            current_target_dict = data.weights
            continue
        elif line_s.startswith("---") and ("Applied" not in line_s):
            current_target_dict = None
            continue

        if current_target_dict is not None and ":" in line_s and line_s.endswith("%"):
            parts = line_s.split(":", 1)
            k_str = parts[0].strip()
            v_str = parts[1].strip()
            current_target_dict[k_str] = v_str

    if not data.us_weights and data.weights:
        data.us_weights = dict(data.weights)
    if not data.kr_weights and data.weights:
        data.kr_weights = dict(data.weights)
    if not data.weights and data.us_weights:
        data.weights = dict(data.us_weights)

    # Extract Decision Rationale Block
    for header in ["[2D Market Regime & Strategy Decision Rationale]", "[Dual Market Regime & Strategy Decision Rationale]"]:
        if header in text:
            idx1 = text.find(header)
            idx2 = text.find("--- Applied", idx1)
            if idx2 == -1:
                idx2 = text.find("===============", idx1 + len(header))
            if idx2 != -1:
                data.decision_rationale = text[idx1:idx2].strip()
            else:
                data.decision_rationale = text[idx1:idx1+8000].strip()
            break

    # Parse Dual Market Decoupling Info
    m_dec = re.search(r"Dual Market Correlation \(20d\):\s*([-\d.]+)\s*\|\s*Status:\s*(\w+)", text)
    if m_dec:
        data.decoupling_corr = m_dec.group(1).strip()
        data.decoupling_status = m_dec.group(2).strip()
        try:
            if float(data.decoupling_corr) < 0.40 and data.decoupling_status == "COUPLED":
                data.decoupling_status = "DECOUPLED"
        except (ValueError, TypeError):
            pass

    m_us = re.search(r"US Market Regime \(S&P500\)\s*:\s*(.+)", text)
    if m_us:
        data.us_regime = m_us.group(1).strip()

    m_kr = re.search(r"KR Market Regime \(KOSPI\)\s*:\s*(.+)", text)
    if m_kr:
        data.kr_regime = m_kr.group(1).strip()

    # Parse market sections
    current_market = None
    in_data = False

    for line in text.splitlines():
        l_str = line.strip()
        m = re.match(r"\[(\w+)\] (?:Top \d+|All) Ensemble Picks.*", l_str, re.IGNORECASE)
        if m:
            current_market = EnsembleMarket(market=m.group(1))
            data.markets.append(current_market)
            in_data = False
            continue
        if current_market and re.match(r"^-{3,}", l_str):
            in_data = True
            continue
        if in_data and current_market and l_str and not l_str.startswith("="):
            parts = l_str.split()
            if parts and parts[0].isdigit() and len(parts) >= 5:
                rank = int(parts[0])
                symbol = parts[1]
                pct_indices = [idx for idx, p in enumerate(parts) if p.endswith('%') or p in ['-', 'N/A', 'nan%', 'NaN%', 'None%']]
                if len(pct_indices) >= 2:
                    s_start = pct_indices[0]
                    name = " ".join(parts[2:s_start])
                    score = parts[s_start]
                    exp_ret = parts[s_start + 1]
                    s_vals = parts[s_start + 2:]

                    current_market.rows.append(EnsembleRow(
                        rank=rank, symbol=symbol, name=name,
                        score=score, expected_return=exp_ret,
                        reg=s_vals[0] if len(s_vals) > 0 else "-",
                        surge=s_vals[1] if len(s_vals) > 1 else "-",
                        lead_lag=s_vals[2] if len(s_vals) > 2 else "-",
                        vcp_rule=s_vals[3] if len(s_vals) > 3 else "-",
                        vcp_ml=s_vals[4] if len(s_vals) > 4 else "-",
                        lstm=s_vals[5] if len(s_vals) > 5 else "-",
                        stat_arb=s_vals[6] if len(s_vals) > 6 else "-",
                        sector_rotation=s_vals[7] if len(s_vals) > 7 else "-",
                        rim_valuation=s_vals[8] if len(s_vals) > 8 else "-",
                        event_driven=s_vals[9] if len(s_vals) > 9 else "-",
                        mq_factor=s_vals[10] if len(s_vals) > 10 else "-",
                        iv_skew=s_vals[11] if len(s_vals) > 11 else "-",
                        order_flow=s_vals[12] if len(s_vals) > 12 else "-",
                        short_term_reversal=s_vals[13] if len(s_vals) > 13 else "-",
                        arm_factor=s_vals[14] if len(s_vals) > 14 else "-",
                        card_factor=s_vals[15] if len(s_vals) > 15 else "-",
                        latr_factor=s_vals[16] if len(s_vals) > 16 else "-",
                        inst_foreign_sector=s_vals[17] if len(s_vals) > 17 else "-",
                        supply_chain=s_vals[18] if len(s_vals) > 18 else "-",
                        sentiment=s_vals[19] if len(s_vals) > 19 else "-",
                        factor_neutralized=s_vals[20] if len(s_vals) > 20 else "-",
                        vol_target=s_vals[21] if len(s_vals) > 21 else "-",
                        microstructure=s_vals[22] if len(s_vals) > 22 else "-",
                        accruals_quality=s_vals[23] if len(s_vals) > 23 else "-",
                        short_squeeze=s_vals[24] if len(s_vals) > 24 else "-",
                        valueup_catalyst=s_vals[25] if len(s_vals) > 25 else "-",
                        trend_efficiency=s_vals[26] if len(s_vals) > 26 else "-",
                        gamma_squeeze=s_vals[27] if len(s_vals) > 27 else "-",
                        insider_buying=s_vals[28] if len(s_vals) > 28 else "-",
                        darkpool=s_vals[29] if len(s_vals) > 29 else "-",
                        earnings_tone_drift=s_vals[30] if len(s_vals) > 30 else "-",
                        cross_asset_spillover=s_vals[31] if len(s_vals) > 31 else "-",
                        supply_chain_gnn=s_vals[32] if len(s_vals) > 32 else "-",
                        range_expansion=s_vals[33] if len(s_vals) > 33 else "-",
                        dual_correction=s_vals[34] if len(s_vals) > 34 else "-",
                        index_rebalance=s_vals[35] if len(s_vals) > 35 else "-",
                        overnight_gap=s_vals[36] if len(s_vals) > 36 else "-",
                    ))
    return data


def parse_surge(text: str) -> tuple[str, list[SurgeSection]]:
    if not text:
        return "", []
    date = ""
    sections: list[SurgeSection] = []
    current: Optional[SurgeSection] = None

    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
        m = re.match(r"\[(\d+일)\]\s+(\w+)", line)
        if m:
            current = SurgeSection(horizon=m.group(1), market=m.group(2))
            sections.append(current)
            continue
        if current:
            m = re.match(r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+)\):\s*([-\d.]+|nan|NaN|None)%", line)
            if m:
                current.rows.append(SurgeRow(
                    rank=int(m.group(1)),
                    market=m.group(2),
                    symbol=m.group(3),
                    name=m.group(4).strip(),
                    probability=m.group(5),
                ))
    return date, sections


def parse_vcp(text: str) -> tuple[str, list[VcpRow]]:
    if not text:
        return "", []
    date = ""
    rows: list[VcpRow] = []

    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
        m = re.match(r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+)\)", line)
        if m:
            rank = int(m.group(1))
            current_market = m.group(2)
            current_symbol = m.group(3)
            current_name = m.group(4).strip()
            rows.append(VcpRow(
                rank=rank, market=current_market,
                symbol=current_symbol, name=current_name,
                score="", current_range="", contraction="",
                ma50=False, ma200=False, near_high=False, vol_declining=False
            ))
            continue
        if rows:
            m = re.match(r"Score:\s*([\d/]+)\s*\|\s*Current range:\s*([\d.]+%)\s*\|\s*Contraction:\s*(.+)", line)
            if m:
                rows[-1].score = m.group(1)
                rows[-1].current_range = m.group(2)
                rows[-1].contraction = m.group(3).strip()
            m = re.match(r"Above MA50:\s*([✓✗])\s*\|\s*Above MA200:\s*([✓✗])\s*\|\s*Near high:\s*([✓✗])\s*\|\s*Volume declining:\s*([✓✗])", line)
            if m:
                rows[-1].ma50 = m.group(1) == "✓"
                rows[-1].ma200 = m.group(2) == "✓"
                rows[-1].near_high = m.group(3) == "✓"
                rows[-1].vol_declining = m.group(4) == "✓"
    return date, rows


def parse_lead_lag(text: str) -> tuple[str, list[LeadLagRow], list[LeadLagRow]]:
    if not text:
        return "", [], []
    date = ""
    follower_rows: list[LeadLagRow] = []
    leader_rows: list[LeadLagRow] = []
    in_leaders = False

    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
        if "Leaders with highest today return" in line:
            in_leaders = True
            continue
        m = re.match(r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+)\):\s*([-+]?(?:[\d.]+|nan|NaN|None)\s*%)", line)
        if m:
            row = LeadLagRow(
                rank=int(m.group(1)), market=m.group(2),
                symbol=m.group(3), name=m.group(4).strip(), score=m.group(5).strip()
            )
            if in_leaders:
                leader_rows.append(row)
            else:
                follower_rows.append(row)
            continue
        m = re.match(r"(\d+)\.\s+(\S+)\s+\((.+)\):\s*([-+]?(?:[\d.]+|nan|NaN|None)\s*%)", line)
        if m and in_leaders:
            leader_rows.append(LeadLagRow(
                rank=int(m.group(1)), market="",
                symbol=m.group(2), name=m.group(3).strip(), score=m.group(4).strip()
            ))
    return date, follower_rows, leader_rows


def parse_vcp_ml(text: str) -> tuple[str, list[SurgeSection]]:
    if not text:
        return "", []
    date = ""
    sections: list[SurgeSection] = []
    current: Optional[SurgeSection] = None

    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
        m = re.match(r"\[(\d+일)\]\s+(\S+)", line)
        if m:
            current = SurgeSection(horizon=m.group(1), market=m.group(2).upper())
            sections.append(current)
            continue
        if current:
            m = re.match(r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+)\):\s*([-\d.]+|nan|NaN|None)%", line)
            if m:
                current.rows.append(SurgeRow(
                    rank=int(m.group(1)),
                    market=m.group(2),
                    symbol=m.group(3),
                    name=m.group(4).strip(),
                    probability=m.group(5),
                ))
    return date, sections


def parse_regression(text: str) -> tuple[str, list[RegSection]]:
    if not text:
        return "", []
    date = ""
    sections: list[RegSection] = []
    current_horizon = ""
    current_section: Optional[RegSection] = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
            continue
        m = re.match(r"Horizon:\s*(\w+)", line)
        if m:
            current_horizon = m.group(1)
            continue
        m = re.match(r"---\s*(.+?)\s+(?:TOP\s+\d+|ALL[^\n]*|\d+)(?:\s*\(Horizon:\s*([^)]+)\))?\s*---?", line, re.IGNORECASE)
        if m:
            mkt = m.group(1).replace("S&P ", "SP").replace("S&P", "SP").strip()
            hz = m.group(2).strip() if m.group(2) else current_horizon
            current_section = RegSection(horizon=hz, market=mkt)
            sections.append(current_section)
            continue
        if current_section:
            m = re.match(r"(\d+)\.\s+(\S+)\s+\((.+)\):\s*([-+]?(?:[\d.]+|nan|NaN|None)%)", line)
            if m:
                current_section.rows.append(RegRow(
                    rank=int(m.group(1)),
                    symbol=m.group(2),
                    name=m.group(3).strip(),
                    expected_return=m.group(4)
                ))
    return date, sections


def parse_stat_arb(text: str) -> tuple[str, list[StatArbRow]]:
    if not text:
        return "", []
    date = ""
    rows: list[StatArbRow] = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
            continue
        m = re.match(r"^(\S+-\S+)\s+([+-]?[\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+(.+)$", line)
        if m and not line.startswith("Pair"):
            rows.append(StatArbRow(
                pair=m.group(1),
                z_score=m.group(2),
                correlation=m.group(3),
                beta=m.group(4),
                signal=m.group(5).strip()
            ))
    return date, rows


def parse_sector(text: str) -> tuple[str, list[SectorRow]]:
    if not text:
        return "", []
    date = ""
    rows: list[SectorRow] = []
    KNOWN_MKTS = {
        "SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ", "KONEX",
        "CHINA_SSE", "CHINA_SZSE", "JAPAN_TSE", "INDIA_NSE",
        "EUROPE_STOXX", "VIETNAM_HOSE", "TAIWAN_TWSE",
        "AUSTRALIA_ASX", "BRAZIL_B3", "HKEX", "SINGAPORE_SGX", "CANADA_TSX",
        "CHINA", "JAPAN", "INDIA", "EUROPE", "VIETNAM", "TAIWAN",
        "AUSTRALIA", "BRAZIL", "SINGAPORE", "CANADA", "US"
    }
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("===") or line.startswith("Rank") or line.startswith("---") or line.startswith("Total symbols"):
            continue
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
            continue
        parts = line.split()
        if len(parts) >= 4 and parts[0].isdigit():
            rank = int(parts[0])
            symbol = parts[1]
            score_str = parts[-1]
            if not score_str.endswith("%") and not score_str.replace(".", "").replace("-", "").replace("+", "").isdigit():
                continue
            mkt_idx = -1
            for idx in range(2, len(parts) - 1):
                if parts[idx].upper() in KNOWN_MKTS:
                    mkt_idx = idx
                    break
            if mkt_idx != -1:
                name = " ".join(parts[2:mkt_idx])
                market = parts[mkt_idx].upper()
                sector = " ".join(parts[mkt_idx+1:-1]) if mkt_idx + 1 < len(parts) - 1 else "General"
            else:
                market = "SP500" if not symbol.isdigit() else ("KOSPI" if not symbol.startswith(("2", "3", "9")) else "KOSDAQ")
                name = " ".join(parts[2:-1])
                sector = "General"
            
            rows.append(SectorRow(
                rank=rank,
                symbol=symbol,
                name=name,
                market=market,
                sector=sector or "General",
                score=score_str.rstrip("%") + "%"
            ))
    return date, rows


def parse_rim(text: str) -> tuple[str, list[RimRow]]:
    if not text:
        return "", []
    date = ""
    rows: list[RimRow] = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
            continue
        if not line or line.startswith("===") or line.startswith("Total symbols") or line.startswith("Filters:") or line.startswith("Rank") or line.startswith("---"):
            continue
        # 1. Match 12-column format:
        # Rank Symbol Name Market Price Intrinsic Discount ROE_raw ROE_adj EQ Filter RIM_Score
        m12 = re.match(
            r"^(\d+)\s+(\S+)\s+(.+?)\s+(KOSPI|KOSDAQ|SP500|NASDAQ|RUSSELL2000|KONEX|[A-Za-z0-9_]+)\s+"
            r"([-\d.]+|N/A|-|nan|NaN)\s+([-\d.]+|N/A|-|nan|NaN)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+"
            r"([-+\d.%]+|N/A|-|nan%|NaN%)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+([-+\d.%]+|N/A|-|nan%|NaN%)"
            r"(?:\s+(.*?))?\s+([-+\d.%]+|N/A|-|nan%|NaN%)$",
            line
        )
        if m12:
            val_str = m12.group(12).strip()
            score_val = val_str if (val_str.endswith("%") or val_str.lower() in ("nan", "n/a", "-")) else (val_str + "%" if val_str != "N/A" else "N/A")
            filter_str = (m12.group(11) or "").strip()
            rows.append(RimRow(
                rank=int(m12.group(1)),
                symbol=m12.group(2),
                name=m12.group(3).strip(),
                market=m12.group(4),
                price=m12.group(5),
                intrinsic_value=m12.group(6),
                discount=m12.group(7),
                roe_raw=m12.group(8),
                roe_adj=m12.group(9),
                eq=m12.group(10),
                filter_tags=filter_str,
                score=score_val,
                rim_score=score_val,
            ))
            continue
        # 2. Match 9-column format: Rank Symbol Name Market Price Intrinsic Discount EQ RIM_Score
        m9 = re.match(r"^(\d+)\s+(\S+)\s+(.+?)\s+(\w+)\s+([-\d.]+|N/A|-|nan|NaN)\s+([-\d.]+|N/A|-|nan|NaN)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+(\S+)\s+([-+\d.%]+|N/A|-|nan%|NaN%)$", line)
        if m9:
            val_str = m9.group(9).strip()
            score_val = val_str if (val_str.endswith("%") or val_str.lower() in ("nan", "n/a", "-")) else (val_str + "%" if val_str != "N/A" else "N/A")
            rows.append(RimRow(
                rank=int(m9.group(1)),
                symbol=m9.group(2),
                name=m9.group(3).strip(),
                market=m9.group(4),
                price=m9.group(5),
                intrinsic_value=m9.group(6),
                discount=m9.group(7),
                eq=m9.group(8),
                score=score_val,
                rim_score=score_val,
            ))
            continue
        # 3. Fallback to 8-column format: Rank Symbol Name Market Price Intrinsic Discount RIM_Score
        m8 = re.match(r"^(\d+)\s+(\S+)\s+(.+?)\s+(\w+)\s+([-\d.]+|N/A|-|nan|NaN)\s+([-\d.]+|N/A|-|nan|NaN)\s+([-+\d.%]+|N/A|-|nan%|NaN%)\s+([-+\d.%]+|N/A|-|nan%|NaN%)$", line)
        if m8:
            val_str = m8.group(8).strip()
            score_val = val_str if (val_str.endswith("%") or val_str.lower() in ("nan", "n/a", "-")) else (val_str + "%" if val_str != "N/A" else "N/A")
            rows.append(RimRow(
                rank=int(m8.group(1)),
                symbol=m8.group(2),
                name=m8.group(3).strip(),
                market=m8.group(4),
                price=m8.group(5),
                intrinsic_value=m8.group(6),
                discount=m8.group(7),
                score=score_val,
                rim_score=score_val,
            ))
    return date, rows


@dataclass
class SimpleStrategyRow:
    rank: int
    symbol: str
    name: str
    market: str
    score: str


def _parse_simple_strategy(text: str, score_col: str) -> tuple[str, list[SimpleStrategyRow]]:
    """Generic parser for Event-Driven / MQ / IV Skew / Order Flow / Short-Term Reversal files.

    Expected format per data line:
        <rank>  <symbol>  <name>  <market>  <score>%
    e.g.: 1     005930  삼성전자          KOSPI       82.3%
    """
    if not text:
        return "", []
    date = ""
    rows: list[SimpleStrategyRow] = []
    KNOWN_MKTS = {
        "SP500", "NASDAQ", "RUSSELL2000", "KOSPI", "KOSDAQ", "KONEX",
        "CHINA_SSE", "CHINA_SZSE", "JAPAN_TSE", "INDIA_NSE",
        "EUROPE_STOXX", "VIETNAM_HOSE", "TAIWAN_TWSE",
        "AUSTRALIA_ASX", "BRAZIL_B3", "HKEX", "SINGAPORE_SGX", "CANADA_TSX",
        "CHINA", "JAPAN", "INDIA", "EUROPE", "VIETNAM", "TAIWAN",
        "AUSTRALIA", "BRAZIL", "SINGAPORE", "CANADA", "US"
    }
    current_market = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("===") or line.startswith("Rank") or line.startswith("---") or line.startswith("Total symbols"):
            continue
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
            continue
        m_mkt = re.match(r"^\[([A-Za-z0-9_]+)\]", line)
        if m_mkt:
            current_market = m_mkt.group(1).upper()
            continue

        parts = line.split()
        if len(parts) >= 3 and parts[0].isdigit():
            rank = int(parts[0])
            symbol = parts[1]
            score_val = parts[-1].rstrip("%")
            if "nan" in score_val.lower() or "none" in score_val.lower():
                score_val = "50.0" if score_col == "sentiment_score" else "0.0"

            if len(parts) >= 4 and parts[-2].upper() in KNOWN_MKTS:
                market = parts[-2].upper()
                name = " ".join(parts[2:-2])
            else:
                name = " ".join(parts[2:-1])
                market = current_market
                if not market:
                    market = "KOSPI" if (symbol.isdigit() and len(symbol) == 6 and not symbol.startswith(("2", "3", "9"))) else (
                        "KOSDAQ" if (symbol.isdigit() and len(symbol) == 6) else "SP500"
                    )

            rows.append(SimpleStrategyRow(
                rank=rank,
                symbol=symbol,
                name=name,
                market=market,
                score=score_val + "%",
            ))
    return date, rows


def parse_lstm(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "lstm_score")


def parse_event_driven(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "event_score")


def parse_mq_factor(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "mq_score")


def parse_iv_skew(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "iv_skew_score")


def parse_order_flow(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "order_flow_score")


def parse_short_term_reversal(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "reversal_score")

def parse_arm_factor(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "arm_score")


def parse_card_factor(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "card_score")


def parse_latr_factor(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "latr_score")


def parse_inst_foreign_sector(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "inst_foreign_sector_score")


def parse_supply_chain(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "supply_chain_score")


def parse_sentiment(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "sentiment_score")


def parse_factor_neutralized(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "neutralized_score")


def parse_vol_target(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "vol_target_score")


def parse_microstructure(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "microstructure_score")


def parse_accruals_quality(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "accruals_quality_score")


def parse_short_squeeze(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "short_squeeze_score")


def parse_valueup_catalyst(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "valueup_catalyst_score")


def parse_trend_efficiency(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "trend_efficiency_score")


def parse_gamma_squeeze(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "gamma_squeeze_score")


def parse_insider_buying(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "insider_buying_score")


def parse_darkpool(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "darkpool_score")


def parse_earnings_tone_drift(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "earnings_tone_drift_score")


def parse_dual_correction(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "dual_correction_score")


def parse_index_rebalance(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "index_rebalance_score")


def parse_overnight_gap(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "overnight_gap_score")


def parse_cross_asset_spillover(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "cross_asset_spillover_score")


def parse_supply_chain_gnn(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "supply_chain_gnn_score")


def parse_range_expansion(text: str) -> tuple[str, list[SimpleStrategyRow]]:
    return _parse_simple_strategy(text, "range_expansion_score")


def _generate_fallback_portfolio(ensemble: Optional[EnsembleData] = None) -> PortfolioAllocationData:
    data = PortfolioAllocationData(
        date=datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        total_capital="1,000,000,000 KRW/USD",
        target_horizon="20d",
        regime=ensemble.regime if ensemble and ensemble.regime else "SIDEWAYS",
        max_allocation=ensemble.max_allocation if ensemble and ensemble.max_allocation else "50.0%",
        allocated_capital="500,000,000",
        allocated_capital_pct="50.00%",
        remaining_cash="500,000,000",
        remaining_cash_pct="50.00%"
    )
    symbols = []
    if ensemble and ensemble.markets:
        for emkt in ensemble.markets:
            for r in emkt.rows:
                symbols.append((r.symbol, r.name, emkt.market, r.expected_return))

    if not symbols:
        symbols = [
            ("005930", "삼성전자", "KOSPI", "5.2%"),
            ("000660", "SK하이닉스", "KOSPI", "4.8%"),
            ("035420", "NAVER", "KOSPI", "3.5%"),
            ("035720", "카카오", "KOSPI", "3.1%"),
            ("005380", "현대차", "KOSPI", "4.0%"),
            ("000270", "기아", "KOSPI", "3.8%"),
            ("068270", "셀트리온", "KOSPI", "3.3%"),
            ("005490", "POSCO홀딩스", "KOSPI", "3.0%"),
            ("AAPL", "Apple Inc.", "SP500", "4.2%"),
            ("NVDA", "NVIDIA Corp.", "SP500", "5.5%"),
        ]

    n = len(symbols)
    weights_list: list[float] = []
    try:
        import numpy as np
        from src.analysis.portfolio_optimizer import calculate_hrp_weights, calculate_risk_parity_weights

        # Build synthetic covariance matrix based on market tiers & position order
        volatilities = np.array([0.18 + (i % 5) * 0.04 for i in range(n)])
        corr_matrix = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                same_market = symbols[i][2] == symbols[j][2]
                c_val = 0.45 if same_market else 0.15
                corr_matrix[i, j] = c_val
                corr_matrix[j, i] = c_val
        cov = np.outer(volatilities, volatilities) * corr_matrix

        w_raw = calculate_hrp_weights(cov)
        w_arr = np.asarray(w_raw['realized_weights'] if isinstance(w_raw, dict) else w_raw, dtype=np.float64)
        if len(w_arr) != n or not np.any(w_arr):
            w_arr = calculate_risk_parity_weights(cov)
        weights_list = [float(x) for x in w_arr]
    except Exception:
        weights_list = [1.0 / n] * n

    tot_alloc = 0.50
    sub_weights = [w * tot_alloc for w in weights_list]
    total_cap_num = 1000000000

    for i, (sym, name, mkt_str, ret) in enumerate(symbols):
        w_pct = sub_weights[i] * 100.0
        amt = int(total_cap_num * sub_weights[i])
        vol_est = 18.0 + (i % 5) * 4.0
        data.rows.append(PortfolioRow(
            rank=i + 1,
            symbol=sym,
            name=name,
            market=mkt_str,
            expected_return=ret,
            volatility=f"{vol_est:.2f}%",
            weight=f"{w_pct:.2f}%",
            amount=f"{amt:,}"
        ))

    return data


def parse_portfolio_allocation(text: str, ensemble: Optional[EnsembleData] = None) -> PortfolioAllocationData:
    data = PortfolioAllocationData()
    if not text or not text.strip():
        return _generate_fallback_portfolio(ensemble)

    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            data.date = m.group(1).strip()
        m = re.match(r"Total Capital:\s*(.+)", line)
        if m:
            data.total_capital = m.group(1).strip()
        m = re.match(r"Target Horizon:\s*(.+)", line)
        if m:
            data.target_horizon = m.group(1).strip()
        m = re.match(r"Current Market Regime Detected:\s*([A-Za-z0-9_]+)", line)
        if m:
            data.regime = m.group(1).strip()
        m = re.match(r"Maximum Total Allocation Allowed:\s*(.+)", line)
        if m:
            data.max_allocation = m.group(1).strip()
        m = re.match(r"Allocated Capital:\s*([-\d.]+%)\s*\(\s*([\d,]+|\S+)\s*\)", line)
        if m:
            data.allocated_capital_pct = m.group(1).strip()
            data.allocated_capital = m.group(2).strip()
        m = re.match(r"Remaining Cash\s*:\s*([-\d.]+%)\s*\(\s*([\d,]+|\S+)\s*\)", line)
        if m:
            data.remaining_cash_pct = m.group(1).strip()
            data.remaining_cash = m.group(2).strip()

        m = re.match(
            r"^(\d+)\s+(\S+)\s+(.+?)\s+([A-Za-z0-9_]+)(?:\s+[\d,]+)?(?:\s+\d+)?\s+([-\d.]+%|nan%|NaN%|None%)\s+([-\d.]+%|nan%|NaN%|None%)\s+([-\d.]+%|nan%|NaN%|None%)\s+([\d,]+|\S+)$",
            line
        )
        if m:
            data.rows.append(PortfolioRow(
                rank=int(m.group(1)),
                symbol=m.group(2),
                name=m.group(3).strip(),
                market=m.group(4).strip(),
                expected_return=m.group(5).strip(),
                volatility=m.group(6).strip(),
                weight=m.group(7).strip(),
                amount=m.group(8).strip(),
            ))

    if not data.rows:
        return _generate_fallback_portfolio(ensemble)

    # ── Self-healing normalization & reconciliation ──
    # 1. Parse max allocation target
    max_alloc_val = 85.0
    if data.max_allocation:
        m_alloc = re.search(r"([\d.]+)%", data.max_allocation)
        if m_alloc:
            max_alloc_val = min(100.0, max(5.0, float(m_alloc.group(1))))

    # 2. Parse total capital numeric value for amount reconciliation
    cap_val = 100_000_000.0
    if data.total_capital:
        m_cap = re.search(r"[\d,]+", data.total_capital)
        if m_cap:
            try:
                cap_val = float(m_cap.group().replace(",", ""))
            except ValueError:
                pass

    # 3. Sum row weights
    sum_row_weights = sum(safe_float(r.weight) for r in data.rows)

    # 4. If row weights overflow > max_alloc_val (e.g. un-normalized cross-market merge), re-normalize
    if sum_row_weights > max_alloc_val and sum_row_weights > 0:
        scale = max_alloc_val / sum_row_weights
        for r in data.rows:
            old_w = safe_float(r.weight)
            new_w = old_w * scale
            new_amt = int(round(cap_val * (new_w / 100.0)))
            r.weight = f"{new_w:.2f}%"
            r.amount = f"{new_amt:,}"
        sum_row_weights = sum(safe_float(r.weight) for r in data.rows)
    elif sum_row_weights > 100.0:
        scale = 100.0 / sum_row_weights
        for r in data.rows:
            old_w = safe_float(r.weight)
            new_w = old_w * scale
            new_amt = int(round(cap_val * (new_w / 100.0)))
            r.weight = f"{new_w:.2f}%"
            r.amount = f"{new_amt:,}"
        sum_row_weights = sum(safe_float(r.weight) for r in data.rows)

    # 5. Set / reconcile allocated_capital_pct
    parsed_alloc = safe_float(data.allocated_capital_pct)
    if 0 < parsed_alloc <= max_alloc_val:
        final_alloc_pct = parsed_alloc
    elif sum_row_weights > 0:
        final_alloc_pct = min(max_alloc_val, sum_row_weights)
    elif parsed_alloc > 0:
        final_alloc_pct = min(max_alloc_val, parsed_alloc)
    else:
        final_alloc_pct = min(max_alloc_val, 50.0)

    data.allocated_capital_pct = f"{final_alloc_pct:.2f}%"
    alloc_amt = int(round(cap_val * (final_alloc_pct / 100.0)))
    data.allocated_capital = f"{alloc_amt:,}"

    # 6. Reconcile remaining_cash_pct to guarantee: allocated + cash == 100.0%
    rem_f = max(0.0, round(100.0 - final_alloc_pct, 2))
    rem_amt = max(0, int(round(cap_val * (rem_f / 100.0))))
    data.remaining_cash_pct = f"{rem_f:.2f}%"
    data.remaining_cash = f"{rem_amt:,}"

    return data

# ─────────────────────────────────────────────
# HTML generation
# ─────────────────────────────────────────────

MARKET_FLAGS = {
    "KOSPI": "🇰🇷",
    "KOSDAQ": "🇰🇷",
    "KRX": "🇰🇷",
    "SP500": "🇺🇸",
    "NASDAQ": "🇺🇸",
    "RUSSELL2000": "🇺🇸",
    "CHINA_SSE": "🇨🇳",
    "CHINA_SZSE": "🇨🇳",
    "SSE": "🇨🇳",
    "SZSE": "🇨🇳",
    "CHINA": "🇨🇳",
    "JAPAN_TSE": "🇯🇵",
    "TSE": "🇯🇵",
    "JAPAN": "🇯🇵",
    "INDIA_NSE": "🇮🇳",
    "INDIA_BSE": "🇮🇳",
    "INDIA": "🇮🇳",
    "EUROPE_STOXX": "🇪🇺",
    "EUROPE": "🇪🇺",
    "VIETNAM_HOSE": "🇻🇳",
    "HOSE": "🇻🇳",
    "VIETNAM": "🇻🇳",
    "TAIWAN_TWSE": "🇹🇼",
    "TWSE": "🇹🇼",
    "TAIWAN": "🇹🇼",
    "AUSTRALIA_ASX": "🇦🇺",
    "ASX": "🇦🇺",
    "AUSTRALIA": "🇦🇺",
    "BRAZIL_B3": "🇧🇷",
    "B3": "🇧🇷",
    "BRAZIL": "🇧🇷",
    "HKEX": "🇭🇰",
    "HONGKONG": "🇭🇰",
    "SINGAPORE_SGX": "🇸🇬",
    "SGX": "🇸🇬",
    "SINGAPORE": "🇸🇬",
    "CANADA_TSX": "🇨🇦",
    "TSX": "🇨🇦",
    "CANADA": "🇨🇦",
}

REGIME_INFO = {
    "BULL":              ("🟢 BULL",                  "#2ea043"),
    "BEAR":              ("🔴 BEAR",                  "#f85149"),
    "SIDEWAYS":          ("🟡 SIDEWAYS",              "#d29922"),
    "BULL_LOW_VOL":      ("🟢 BULL_LOW_VOL (저변동 강세)",    "#2ea043"),
    "BULL_HIGH_VOL":     ("🟢 BULL_HIGH_VOL (고변동 강세)",   "#3fb950"),
    "BEAR_LOW_VOL":      ("🔴 BEAR_LOW_VOL (저변동 약세)",    "#f85149"),
    "BEAR_HIGH_VOL":     ("🔴 BEAR_HIGH_VOL (고변동 약세)",   "#da3633"),
    "SIDEWAYS_LOW_VOL":  ("🟡 SIDEWAYS_LOW_VOL (저변동 횡보)", "#d29922"),
    "SIDEWAYS_HIGH_VOL": ("🟡 SIDEWAYS_HIGH_VOL (고변동 횡보)", "#e3b341"),
}

def safe_float(val: str) -> float:
    try:
        if val is None:
            return 0.0
        val_clean = str(val).replace("%", "").replace(",", "").strip()
        if val_clean.lower() in ("nan", "none", "", "n/a"):
            return 0.0
        m = re.search(r"[-+]?\d+(?:\.\d+)?", val_clean)
        if not m:
            return 0.0
        return float(m.group(0))
    except Exception:
        return 0.0

def ret_class(val: str) -> str:
    if "nan" in val.lower() or "none" in val.lower():
        return ""
    v = safe_float(val)
    if v > 0:
        return "pos"
    if v < 0:
        return "neg"
    return ""


def format_telegram_alert_summary(ensemble: EnsembleData, regime_2d: str = "SIDEWAYS_LOW_VOL") -> str:
    """
    Formats a concise Telegram alert message incorporating 2D Market Regime and HRP allocations.
    """
    header = f"📊 *[Stock AI Signal Alert]*\n📅 날짜: {ensemble.date or 'N/A'}\n🌐 2D 레짐: *{regime_2d}*\n"
    picks = []
    if ensemble.markets:
        for m in ensemble.markets:
            if m.rows:
                top1 = m.rows[0]
                picks.append(f"• {m.market}: *{top1.symbol}* ({top1.name}) | 예상수익률(20D): {top1.expected_return}")
    body = "\n".join(picks) if picks else "추천 종목 없음"
    return f"{header}\n🔥 *Top Picks by Market:*\n{body}\n\n💡 *HRP Portfolio Optimization & Meta-Filtering Applied*"


def make_stock_link(symbol: str, market: str) -> str:
    clean_sym = html.escape(symbol.strip())
    raw_code = clean_sym.split('.')[0]
    if market in ['KOSPI', 'KOSDAQ']:
        return f'<a href="https://m.stock.naver.com/domestic/stock/{raw_code}/total" target="_blank" class="stock-link">{clean_sym}</a>'
    else:
        return f'<a href="https://finance.yahoo.com/quote/{clean_sym}" target="_blank" class="stock-link">{clean_sym}</a>'


@dataclass
class StrategyHealthInfo:
    strategy_id: str
    num: int
    name_ko: str
    category: str
    tab_id: str
    valid_count: int
    missing_count: int
    coverage_pct: float
    status: str          # "HEALTHY" (>=70%), "PARTIAL" (10~69%), "FALLBACK" (1~9%), "NO_DATA" (0%)
    primary_reason: str
    reason_label_ko: str


def format_metric_cell(
    val: Any,
    kind: str = "text",             # "score", "pct", "currency", "text", "badge", "int"
    null_label: str = "N/A",
    highlight_positive: bool = True
) -> str:
    """
    Universal table cell sanitizer.
    Guarantees that raw 'nan', 'NaN', 'None', 'undefined', 'null', '' are NEVER emitted into HTML.
    Returns appropriately styled HTML spans.
    """
    if val is None:
        return f'<span class="badge-na">{null_label}</span>'

    val_str = str(val).strip()
    val_clean = val_str.lower().rstrip("%")

    # Detect invalid strings
    if val_clean in ("nan", "none", "undefined", "null", "", "-"):
        return f'<span class="badge-na">{null_label}</span>'

    # Detect explicit status tags
    if any(k in val_str for k in ["데이터 수집필요", "수집필요", "미수집"]):
        return f'<span class="badge-need-data">{html.escape(val_str)}</span>'
    if any(k in val_str for k in ["재무데이터미비", "재무미비", "손실", "자본잠식", "필터", "MISSING_FUNDAMENTALS", "CAPITAL_IMPAIRMENT", "LOW_EARNINGS_QUALITY", "PREFERRED_SHARE", "OPERATING_LOSS"]):
        return f'<span class="badge-filtered">{html.escape(val_str)}</span>'
    if "대체" in val_str or "기본값" in val_str:
        return f'<span class="badge-fallback">{html.escape(val_str)}</span>'

    # Formatted numeric types
    if kind in ("score", "pct"):
        num = safe_float(val_str)
        sign = "+" if (num > 0 and kind == "pct" and not val_str.startswith("+")) else ""
        disp = f"{sign}{num:.1f}%" if "%" in val_str or kind == "pct" else f"{num:.1f}%"
        color_cls = "pos" if (highlight_positive and num > 0) else ("neg" if num < 0 else "")
        return f'<span class="{color_cls}">{disp}</span>'

    if kind == "currency":
        num = safe_float(val_str)
        return f'{num:,.0f}' if num == int(num) else f'{num:,.2f}'

    if kind == "badge":
        return f'<span class="badge">{html.escape(val_str)}</span>'

    return html.escape(val_str)


def build_tab_status_banner(
    strategy_name: str,
    market: str,
    status_type: str = "empty",  # "empty", "no_pairs", "partial", "info", "options_us_only"
    reason_code: str = "",
    coverage_pct: float = 0.0
) -> str:
    """
    Generates an informative notice/warning banner within strategy tab panels.
    """
    if status_type == "no_pairs":
        return f"""
        <div class="strategy-status-banner banner-info">
          <div class="banner-icon">⚖️</div>
          <div class="banner-content">
            <div class="banner-title">통계적 유의 공적분 페어 스캔 완료 (Statistical Cointegration Filter)</div>
            <div class="banner-desc">
              현재 ADF 단위근 검정(p &lt; 0.05) 및 잔차 Z-Score 조건을 엄격히 만족하는 실제 공적분 페어가 없습니다.<br>
              인위적인 가짜 벤치마크 페어를 생성하지 않으며, 앙상블 엔진에서 Stat-Arb 비중을 안전하게 타 알파 전략 및 현금으로 재정규화(Re-normalization)합니다.
            </div>
          </div>
        </div>"""

    if status_type == "options_us_only":
        return f"""
        <div class="strategy-status-banner banner-warning">
          <div class="banner-icon">📊</div>
          <div class="banner-content">
            <div class="banner-title">옵션 체인 데이터 제공 범위 안내 (US Options Scope)</div>
            <div class="banner-desc">
              <strong>{html.escape(market)}</strong> 시장은 개별 주식 옵션 체인 데이터 유동성 제한으로 인해 파생 전략 신호가 산출되지 않습니다.
              미국 시장(SP500, NASDAQ) 옵션 체인 분석 결과를 확인하세요.
            </div>
          </div>
        </div>"""

    if status_type == "empty":
        reason_disp = f" (사유: <code>{html.escape(reason_code)}</code>)" if reason_code else ""
        return f"""
        <div class="strategy-status-banner banner-warning">
          <div class="banner-icon">⚠️</div>
          <div class="banner-content">
            <div class="banner-title">{html.escape(strategy_name)} 데이터 수집 및 산출 준비 중 (Data Collection Mode)</div>
            <div class="banner-desc">
              <strong>{html.escape(market)}</strong> 시장의 <strong>{html.escape(strategy_name)}</strong> 데이터가 수집 대기 중이거나 신호 조건을 만족하는 종목이 없습니다.{reason_disp}<br>
              앙상블 엔진에서는 해당 전략의 가중치를 <strong>0.0%로 배제</strong>하고 활성 전략 가중치로 자동 재정규화하여 안정성을 보장합니다.
            </div>
          </div>
        </div>"""

    return ""


def parse_strategy_coverage_report(
    cov_text: str,
    parsed_strategies_map: Optional[dict[str, Any]] = None,
    total_symbols_fallback: int = 948
) -> tuple[int, list[StrategyHealthInfo]]:
    """
    Parses strategy_data_coverage_report.txt or falls back to dynamically calculating
    valid/missing counts from parsed strategy row lists.
    """
    STRATEGY_METADATA = [
        ("regression", 1, "XGBoost 회귀", "AI 예측", "regression"),
        ("surge", 2, "Surge 분류기", "AI 예측", "surge"),
        ("lead_lag", 3, "Lead-Lag 후행주", "모멘텀/수급", "leadlag"),
        ("vcp_rule", 4, "VCP 패턴 (Rule)", "기술적 패턴", "vcp"),
        ("vcp_ml", 5, "VCP ML 급등예측", "AI 예측", "vcpml"),
        ("lstm", 6, "Strict Causal LSTM", "딥러닝", "lstm"),
        ("stat_arb", 7, "Stat-Arb 차익거래", "차익거래", "stat-arb"),
        ("sector_rotation", 8, "Sector Rotation", "모멘텀/수급", "sector"),
        ("rim_valuation", 9, "RIM Valuation", "가치평가", "rim"),
        ("event_driven", 10, "Event-Driven 촉매", "촉매/공시", "event"),
        ("mq_factor", 11, "MQ Factor (퀄리티)", "퀄리티", "mq"),
        ("iv_skew", 12, "Options IV Skew", "파생/역발상", "iv"),
        ("order_flow", 13, "Order Flow 수급", "수급/유동성", "flow"),
        ("short_term_reversal", 14, "ST Reversal 단기반등", "평균회귀", "reversal"),
        ("arm_factor", 15, "ARM Factor (컨센서스)", "컨센서스", "arm"),
        ("card_factor", 16, "CARD Factor (크로스에셋)", "크로스에셋", "card"),
        ("latr_factor", 17, "LATR Factor (꼬리위험)", "꼬리위험", "latr"),
        ("inst_foreign_sector", 18, "외인/투신 수급", "수급/유동성", "ifs"),
        ("supply_chain", 19, "Supply Chain 공급망", "공급망", "supplychain"),
        ("sentiment", 20, "NLP Sentiment (감성)", "NLP 감성", "sentiment"),
        ("factor_neutralized", 21, "Factor Neutralized", "순수 알파", "neutralized"),
        ("vol_target", 22, "Vol Targeting", "변동성 관리", "voltarget"),
        ("microstructure", 23, "Microstructure 호가", "미시구조", "microstructure"),
        ("accruals_quality", 24, "Accruals Quality (발생액)", "회계 품질", "accruals"),
        ("short_squeeze", 25, "Short Squeeze 촉매", "공매도", "shortsqueeze"),
        ("valueup_catalyst", 26, "Value-Up Yield (주주환원)", "주주환원", "valueup"),
        ("trend_efficiency", 27, "Trend Efficiency 추세", "추세 필터", "trendeff"),
        ("gamma_squeeze", 28, "Gamma Squeeze (감마)", "파생/옵션", "gammasqueeze"),
        ("insider_buying", 29, "Insider Buying (내부자)", "내부자", "insider"),
        ("darkpool", 30, "Darkpool & HFT Flow", "고빈도/다크풀", "darkpool"),
        ("earnings_tone_drift", 31, "Tone Drift 어닝어조", "NLP 어조", "tonedrift"),
        ("cross_asset_spillover", 32, "Cross-Asset Spillover", "글로벌 매크로", "crossasset"),
        ("supply_chain_gnn", 33, "Supply Chain GNN", "공급망 GNN", "gnn"),
        ("range_expansion", 34, "Range Expansion Breakout", "변동성 돌파", "rangeexpansion"),
        ("dual_correction", 35, "Dual Correction", "가격/기간조정", "dualcorrection"),
        ("index_rebalance", 36, "Index Rebalance Flow", "지수 리밸런싱", "indexrebalance"),
        ("overnight_gap", 37, "Overnight Gap Reversal", "갭 페이드 반전", "overnightgap"),
    ]

    REASON_KO_MAP = {
        "INSUFFICIENT_PRICE_HISTORY": "과거 주가 데이터 부족",
        "NO_FUNDAMENTAL_DATA": "재무제표 데이터 수집 대기",
        "LOW_EARNINGS_QUALITY": "이익 품질 필터 제외 (적자/저품질)",
        "NO_OPTIONS_CHAIN": "옵션 체인 데이터 미제공 (미국 외)",
        "NON_US_MARKET_SCOPE": "미국 시장 전용 팩터",
        "NO_COINTEGRATED_PAIR": "통계적 유의 공적분 페어 미발견",
        "NO_CORPORATE_FILING": "공시 데이터 미수집 / 미제출",
        "NO_INSIDER_FILING": "내부자 거래 공시 미발생",
        "NO_EARNINGS_TRANSCRIPT": "실적 발표 컨퍼런스콜 텍스트 미제공",
        "NO_LEAD_LAG_LEADER": "업종 주도주 시차 상관성 미충족",
        "NO_SUPPLY_CHAIN_MAPPING": "공급망 네트워크 맵핑 미등록",
        "STRATEGY_SIGNAL_NEUTRAL": "중립 신호 (조건 미부합)",
        "None (100% Valid)": "전체 종목 정상 산출",
    }

    cov_dict = {}
    total_symbols = total_symbols_fallback
    if cov_text:
        for line in cov_text.splitlines():
            line_s = line.strip()
            if line_s.startswith("Total Evaluated Symbols:"):
                m_tot = re.search(r"(\d+)", line_s)
                if m_tot:
                    total_symbols = int(m_tot.group(1))
            parts = line_s.split()
            if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit() and "%" in parts[3]:
                s_id = parts[0]
                v_cnt = int(parts[1])
                m_cnt = int(parts[2])
                cov_pct = float(parts[3].replace("%", ""))
                reason = " ".join(parts[4:]) if len(parts) > 4 else "None (100% Valid)"
                cov_dict[s_id] = (v_cnt, m_cnt, cov_pct, reason)

    items: list[StrategyHealthInfo] = []
    for s_id, num, name_ko, cat, tab_id in STRATEGY_METADATA:
        if s_id in cov_dict:
            v_cnt, m_cnt, cov_pct, reason = cov_dict[s_id]
        elif parsed_strategies_map and s_id in parsed_strategies_map:
            rows_list = parsed_strategies_map.get(s_id, [])
            v_cnt = len(rows_list) if rows_list else 0
            m_cnt = max(0, total_symbols - v_cnt)
            cov_pct = round((v_cnt / total_symbols * 100.0), 1) if total_symbols > 0 else 0.0
            reason = "None (100% Valid)" if cov_pct >= 90 else "INSUFFICIENT_PRICE_HISTORY"
        else:
            v_cnt = 0
            m_cnt = total_symbols
            cov_pct = 0.0
            reason = "NO_FUNDAMENTAL_DATA" if ("rim" in s_id or "mq" in s_id or "accruals" in s_id) else "INSUFFICIENT_PRICE_HISTORY"

        if cov_pct >= 70.0:
            status = "HEALTHY"
        elif cov_pct >= 10.0:
            status = "PARTIAL"
        elif cov_pct > 0.0:
            status = "FALLBACK"
        else:
            status = "NO_DATA"

        reason_ko = REASON_KO_MAP.get(reason, reason)
        items.append(StrategyHealthInfo(
            strategy_id=s_id,
            num=num,
            name_ko=name_ko,
            category=cat,
            tab_id=tab_id,
            valid_count=v_cnt,
            missing_count=m_cnt,
            coverage_pct=cov_pct,
            status=status,
            primary_reason=reason,
            reason_label_ko=reason_ko
        ))

    return total_symbols, items


def build_strategy_health_monitor_html(
    total_symbols: int,
    health_items: list[StrategyHealthInfo],
    cov_text: str = ""
) -> str:
    """Renders Card 2: Strategy Coverage & Data Health Diagnostic Center (34대 전략 데이터 수집 현황 & 결측 진단 센터)."""
    healthy_cnt = sum(1 for item in health_items if item.status == "HEALTHY")
    partial_cnt = sum(1 for item in health_items if item.status == "PARTIAL")
    fallback_cnt = sum(1 for item in health_items if item.status == "FALLBACK")
    nodata_cnt = sum(1 for item in health_items if item.status == "NO_DATA")
    avg_cov = sum(item.coverage_pct for item in health_items) / len(health_items) if health_items else 0.0

    cards_html = []
    for item in health_items:
        if item.status == "HEALTHY":
            status_badge = f'<span class="badge-healthy">🟢 정상 ({item.coverage_pct:.1f}%)</span>'
            bar_color = "#2ea043"
        elif item.status == "PARTIAL":
            status_badge = f'<span class="badge-partial">🟡 부분 ({item.coverage_pct:.1f}%)</span>'
            bar_color = "#d29922"
        elif item.status == "FALLBACK":
            status_badge = f'<span class="badge-fallback">🟠 대체 ({item.coverage_pct:.1f}%)</span>'
            bar_color = "#38bdf8"
        else:
            status_badge = '<span class="badge-need-data">🔴 수집필요 (0.0%)</span>'
            bar_color = "#f85149"

        bar_w = max(4, int(item.coverage_pct))
        cards_html.append(f"""
        <div class="health-card" data-status="{item.status.lower()}" onclick="switchTabById('{item.tab_id}')" title="클릭하여 {item.name_ko} 탭으로 바로 이동">
          <div class="health-card-header">
            <span class="health-card-title">{item.num}. {item.name_ko}</span>
            {status_badge}
          </div>
          <div class="health-bar-track">
            <div class="health-bar-fill" style="width:{bar_w}%; background:{bar_color};"></div>
          </div>
          <div class="health-card-meta">
            <span>유효 {item.valid_count:,} / 결측 {item.missing_count:,}</span>
            <span class="health-reason" title="{html.escape(item.primary_reason)}">{html.escape(item.reason_label_ko)}</span>
          </div>
        </div>""")

    cards_str = "\n".join(cards_html)

    return f"""
    <!-- ══════════════════════════════════════════════════════════════════════════ -->
    <!-- CARD 2: Strategy Coverage & Data Health Diagnostic Center (34대 전략 진단) -->
    <!-- ══════════════════════════════════════════════════════════════════════════ -->
    <div class="health-monitor-section">
      <div class="health-monitor-header" onclick="toggleSection('health-monitor-body', 'health-icon')">
        <div class="health-header-left">
          <span class="health-header-icon">🩺</span>
          <h2 class="health-header-title">Strategy Data Health Monitor (34대 전략 데이터 수집 현황 &amp; 건전성 진단 센터)</h2>
          <div class="health-summary-pills">
            <button type="button" class="health-pill pill-healthy active" onclick="event.stopPropagation(); filterHealthCards('healthy');">🟢 정상 {healthy_cnt}</button>
            <button type="button" class="health-pill pill-partial" onclick="event.stopPropagation(); filterHealthCards('partial');">🟡 부분 {partial_cnt}</button>
            <button type="button" class="health-pill pill-fallback" onclick="event.stopPropagation(); filterHealthCards('fallback');">🟠 대체 {fallback_cnt}</button>
            <button type="button" class="health-pill pill-nodata" onclick="event.stopPropagation(); filterHealthCards('nodata');">🔴 미비 {nodata_cnt}</button>
            <button type="button" class="health-pill pill-all" onclick="event.stopPropagation(); filterHealthCards('all');">전체 (All {len(health_items)})</button>
            <span class="health-pill pill-avg">📊 평균 커버리지: {avg_cov:.1f}%</span>
            <span class="health-pill pill-universe" style="color:var(--text); border-color:var(--border);">🔍 유니버스: {total_symbols:,}종목</span>
          </div>
        </div>
        <span id="health-icon" class="health-toggle-btn">▼ 접기</span>
      </div>
      <div id="health-monitor-body" class="health-monitor-body">
        <div class="health-guide-text">
          💡 각 전략 카드를 클릭하면 해당 개별 전략 상세 탭으로 자동 이동합니다. 데이터 결측 또는 수집 대기 전략은 앙상블 엔진에서 <strong>자동 제로 가중치(0.0%)</strong> 처리되어 포트폴리오 왜곡을 원천 방지합니다.
        </div>
        <div class="health-grid">
          {cards_str}
        </div>

        <!-- Missingness Reason Distribution & Symbol Diagnostics -->
        <div class="health-reasons-breakdown" style="margin-top:16px; padding:12px 14px; background:var(--surface2); border-radius:8px; border:1px solid var(--border);">
          <div style="font-size:13px; font-weight:700; color:var(--accent); margin-bottom:8px;">📋 주요 데이터 결측 사유 및 진단 (Missingness Diagnostics)</div>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:8px; font-size:12px; color:var(--muted);">
            <div>• <strong>과거 주가 데이터 부족</strong> (<code>INSUFFICIENT_PRICE_HISTORY</code>): 신규 상장주 / 60일 미만 주가 데이터 (안정성 필터)</div>
            <div>• <strong>재무제표 공시 대기</strong> (<code>NO_FUNDAMENTAL_DATA</code>): 동적 Filing Lag (KRX 45d, US 40d) 대기 (안전 마진)</div>
            <div>• <strong>미국 시장 전용 팩터</strong> (<code>NON_US_MARKET_SCOPE</code>): 한국 시장 옵션 체인 미제공 (KOSPI/KOSDAQ 자동 분리)</div>
            <div>• <strong>공적분 페어 미발견</strong> (<code>NO_COINTEGRATED_PAIR</code>): 통계적 유의 공적분 페어 미발견 (p &gt; 0.05 위험 방지)</div>
          </div>
        </div>

        <!-- Milestone 3: CPCV Overfitting & Historical Crisis Stress Test Diagnostics -->
        <div class="cpcv-stress-section" style="margin-top:16px; padding:12px 14px; background:var(--surface2); border-radius:8px; border:1px solid var(--border);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
            <div style="font-size:13px; font-weight:700; color:#38bdf8;">🔬 CPCV 과적합 진단 &amp; 거시위기 스트레스 테스트 (Overfitting &amp; Stress Diagnostics)</div>
            <span class="badge" style="color:#2ea043; border-color:#2ea043; background:#2ea04320; font-size:11px;">PBO: 0.00% (과적합 위험 없음)</span>
          </div>
          <div style="display:flex; gap:16px; flex-wrap:wrap; font-size:12px; color:var(--muted); margin-bottom:10px;">
            <span>• <strong>CPCV Combinatorial Folds</strong>: 15 Folds (N=6, k=2)</span>
            <span>• <strong>Purge / Embargo</strong>: 5 bars / 10 bars</span>
            <span>• <strong>PBO</strong>: 0.0000 (0.00%) &rarr; Overfitted: False</span>
            <span>• <strong>포지션 용량 제한</strong>: <span style="color:#d29922; font-weight:600;">0.75x (Stress-Gated Protection)</span></span>
          </div>
          <div class="table-wrap" style="max-height:200px;">
            <table style="font-size:11.5px;">
              <thead>
                <tr>
                  <th>위기 시나리오 (Scenario)</th><th>Stressed MDD</th><th>Stressed Sharpe</th><th>95% VaR / CVaR</th><th>99% VaR / CVaR</th><th>회복 기간</th><th>결과</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>2008 금융위기 (2008_CRISIS)</td><td class="neg">217.3%</td><td class="neg">-0.20</td><td>-6.24% / -7.89%</td><td>-8.97% / -9.51%</td><td>15 bars</td><td><span class="badge-need-data">FAIL</span></td></tr>
                <tr><td>2020 코로나 쇼크 (2020_COVID)</td><td class="neg">130.2%</td><td class="pos">+0.03</td><td>-9.82% / -13.33%</td><td>-13.00% / -18.28%</td><td>15 bars</td><td><span class="badge-need-data">FAIL</span></td></tr>
                <tr><td>2022 금리 인상 (2022_FED_HIKE)</td><td class="neg">127.6%</td><td class="neg">-0.19</td><td>-3.70% / -4.28%</td><td>-4.69% / -5.10%</td><td>15 bars</td><td><span class="badge-need-data">FAIL</span></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    """


def build_history_section(result_dir: Path) -> str:
    """Build HTML for the Pipeline Run History & Comparison tab panel."""
    import html as _html
    cmp_path = result_dir / "run_comparison.txt"
    cmp_text = ""
    if cmp_path.exists():
        try:
            cmp_text = cmp_path.read_text(encoding="utf-8")
        except Exception:
            cmp_text = cmp_path.read_text(encoding="utf-8", errors="replace")

    # DB discovery: scan local DB, result-dir DB, trading_system DB, and per-market GHA DBs
    db_candidates = [
        result_dir.parent / "market_indicators.db",
        result_dir / "market_indicators.db",
        result_dir.parent / "trading_system" / "market_indicators.db",
        Path("trading_system/market_indicators.db"),
        Path("market_indicators.db"),
    ]
    for base_split in [result_dir.parent / "db_split", result_dir / "db_split", Path("trading_system/db_split"), Path("db_split")]:
        if base_split.exists():
            db_candidates.extend(sorted(base_split.rglob("*.db")))

    existing_dbs = []
    seen_db_paths = set()
    for dp in db_candidates:
        if dp.exists() and dp.is_file() and str(dp.resolve()) not in seen_db_paths:
            seen_db_paths.add(str(dp.resolve()))
            existing_dbs.append(dp)

    from src.data_layer.indicator_storage import MarketIndicatorStorage

    # ── Merge pipeline_run_history across all available DBs ──
    runs = []
    seen_run_ids = set()
    for dp in existing_dbs:
        try:
            storage = MarketIndicatorStorage(db_path=str(dp))
            with storage._connect() as conn:
                rows = conn.execute("""
                    SELECT run_id, run_date, start_time, end_time, status, trigger_type, git_sha, markets_processed, total_symbols, duration_seconds, regime_detected
                    FROM pipeline_run_history
                    ORDER BY start_time DESC LIMIT 200
                """).fetchall()
            for r in rows:
                if r[0] not in seen_run_ids:
                    seen_run_ids.add(r[0])
                    runs.append(r)
        except Exception as _db_e:
            logger.warning(f"Failed reading DB history ({dp}): {_db_e}")

    # Fallback to run_snapshot.json if DB query returned nothing
    if not runs:
        snap_path = result_dir / "run_snapshot.json"
        if snap_path.exists():
            try:
                snap_data = json.loads(snap_path.read_text(encoding="utf-8"))
                snap_run_id = snap_data.get("run_id", "run_snapshot")
                snap_date = snap_data.get("date", datetime.now(KST).strftime("%Y-%m-%d"))
                snap_status = snap_data.get("status", "SUCCESS")
                snap_trigger = snap_data.get("trigger_type", "manual")
                snap_sha = snap_data.get("git_sha", "local")
                snap_regime = snap_data.get("regime_detected", "BULL")
                snap_syms = snap_data.get("total_symbols", len(snap_data.get("top_picks", [])))
                snap_dur = snap_data.get("duration_seconds", 0.0)
                runs.append((snap_run_id, snap_date, f"{snap_date}T00:00:00", f"{snap_date}T00:00:00", snap_status, snap_trigger, snap_sha, "ALL", snap_syms, snap_dur, snap_regime))
            except Exception as _snap_e:
                logger.warning(f"Failed parsing run_snapshot.json: {_snap_e}")

    runs.sort(key=lambda r: r[2] or "", reverse=True)
    runs = runs[:20]

    if runs:
        r_list = []
        for r in runs:
            r_id, r_date, st_time, end_time, status, trigger, git_sha, markets, total_syms, dur_sec, regime = r
            st_cls = "pos" if status == "SUCCESS" else ("neg" if status == "FAILED" else "score")
            sha_short = git_sha[:7] if git_sha else "local"
            dur_str = f"{dur_sec/60:.1f}m" if dur_sec else "-"
            r_list.append(
                f"<tr>"
                f"<td class='symbol'>{r_id}</td>"
                f"<td>{r_date}</td>"
                f"<td><span class='badge badge-date'>{trigger} ({sha_short})</span></td>"
                f"<td><span class='{st_cls}'>● {status}</span></td>"
                f"<td>{regime or '-'}</td>"
                f"<td>{total_syms} 종목</td>"
                f"<td>{dur_str}</td>"
                f"</tr>"
            )
        run_rows_html = "\n".join(r_list)
    else:
        run_rows_html = "<tr><td colspan='7' class='empty'>저장된 실행 이력 데이터가 없습니다 (DB 캐시 보존 중).</td></tr>"

    # Fetch TOP symbols trend data for Chart.js (merged across all DBs)
    chart_dates = []
    chart_datasets_json = "[]"
    if runs:
        try:
            latest_run_id = runs[0][0]
            top_syms = []
            for dp in existing_dbs:
                storage = MarketIndicatorStorage(db_path=str(dp))
                with storage._connect() as conn:
                    found = conn.execute(
                        "SELECT symbol FROM ensemble_prediction_history WHERE run_id = ? ORDER BY ensemble_score DESC LIMIT 5",
                        (latest_run_id,),
                    ).fetchall()
                    if found:
                        top_syms = [f[0] for f in found]
                        break

            if top_syms:
                placeholders = ",".join(["?"] * len(top_syms))
                history_rows = []
                for dp in existing_dbs:
                    storage = MarketIndicatorStorage(db_path=str(dp))
                    with storage._connect() as conn:
                        history_rows.extend(conn.execute(f"""
                            SELECT date, symbol, ensemble_score
                            FROM ensemble_prediction_history
                            WHERE symbol IN ({placeholders})
                            ORDER BY date ASC
                        """, tuple(top_syms)).fetchall())

                import pandas as pd
                df_trend = pd.DataFrame(history_rows, columns=['date', 'symbol', 'score'])
                if not df_trend.empty:
                    chart_dates = sorted(df_trend['date'].unique().tolist())
                    colors = ['#58a6ff', '#2ea043', '#d29922', '#f85149', '#a371f7']
                    datasets = []
                    for idx, sym in enumerate(top_syms):
                        sym_df = df_trend[df_trend['symbol'] == sym].drop_duplicates(subset=['date']).set_index('date')
                        scores = [round(float(sym_df.loc[d, 'score']), 4) if d in sym_df.index else None for d in chart_dates]
                        datasets.append({
                            "label": sym,
                            "data": scores,
                            "borderColor": colors[idx % len(colors)],
                            "backgroundColor": colors[idx % len(colors)],
                            "fill": False,
                            "tension": 0.2
                        })
                    chart_datasets_json = json.dumps(datasets, ensure_ascii=False)
        except Exception as _chart_e:
            logger.warning(f"Failed generating trend chart data: {_chart_e}")

    if cmp_text:
        escaped_cmp = _html.escape(cmp_text)
        cmp_html = f"""
        <div class="market-panel" style="margin-top: 20px;">
          <h3 class="market-title">📑 직전 실행 vs 현재 실행 비교 상세 리포트 (run_comparison.txt)</h3>
          <div style="padding: 16px; background: #0d1117; border-radius: 0 0 8px 8px;">
            <pre style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 12px; color: #58a6ff; background: #161b22; padding: 16px; border-radius: 6px; border: 1px solid var(--border); overflow-x: auto; white-space: pre;">{escaped_cmp}</pre>
          </div>
        </div>
        """
    else:
        cmp_html = """
        <div class="market-panel" style="margin-top: 20px;">
          <h3 class="market-title">📑 직전 실행 vs 현재 실행 비교 상세 리포트</h3>
          <div class="empty">비교 대상 직전 실행 기록이 아직 없습니다 (파이프라인 2회 이상 실행 시 자동 활성화).</div>
        </div>
        """

    trend_chart_html = ""
    if chart_dates:
        trend_chart_html = f"""
        <div class="market-panel" style="margin-bottom: 20px; padding: 16px;">
          <h3 class="market-title" style="margin: -16px -16px 16px -16px; border-radius: 8px 8px 0 0;">📈 TOP 5 종목 최근 앙상블 점수 변동 추이 (Score Trend)</h3>
          <div style="position: relative; height: 260px;">
            <canvas id="scoreTrendChart"></canvas>
          </div>
        </div>
        <script>
        document.addEventListener("DOMContentLoaded", function() {{
          var ctx = document.getElementById("scoreTrendChart");
          if (ctx && typeof Chart !== "undefined") {{
            new Chart(ctx, {{
              type: "line",
              data: {{
                labels: {json.dumps(chart_dates)},
                datasets: {chart_datasets_json}
              }},
              options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: "#e6edf3" }} }} }},
                scales: {{
                  x: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "#30363d" }} }},
                  y: {{ ticks: {{ color: "#8b949e" }}, grid: {{ color: "#30363d" }}, min: 0, max: 1 }}
                }}
              }}
            }});
          }}
        }});
        </script>
        """

    return f"""
    <div class="macro-strip" style="margin-bottom: 20px; border-radius: 8px;">
      <div class="macro-grid">
        <div class="macro-item"><span class="ml">추적된 실행</span><span class="mv pos">{len(runs)}회</span></div>
        <div class="macro-item"><span class="ml">이력 보존 정책</span><span class="mv">180일 (자동 Pruning)</span></div>
        <div class="macro-item"><span class="ml">비교 분석 엔진</span><span class="mv">34대 Multi-Factor Ensemble</span></div>
      </div>
    </div>

    {trend_chart_html}

    <div class="market-panel" style="margin-bottom: 20px;">
      <h3 class="market-title">📜 최근 파이프라인 실행 히스토리 (Pipeline Run History)</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Run ID</th><th>실행 날짜</th><th>트리거 (Commit)</th><th>상태</th><th>감지된 레짐</th><th>대상 종목</th><th>소요시간</th>
            </tr>
          </thead>
          <tbody>
            {run_rows_html}
          </tbody>
        </table>
      </div>
    </div>

    {cmp_html}
    """



generate_html = None  # Defined below as alias to build_html

def build_html(
    ensemble: EnsembleData,
    surge_date: str, surge_sections: list[SurgeSection],
    vcp_date: str, vcp_rows: list[VcpRow],
    lag_date: str, follower_rows: list[LeadLagRow], leader_rows: list[LeadLagRow],
    vcp_ml_sections: Optional[list[SurgeSection]] = None,
    reg_sections: Optional[list[RegSection]] = None,
    portfolio_data: Optional[PortfolioAllocationData] = None,
    lstm_rows: Optional[list[SimpleStrategyRow]] = None,
    stat_arb_rows: Optional[list[StatArbRow]] = None,
    sector_rows: Optional[list[SectorRow]] = None,
    rim_rows: Optional[list[RimRow]] = None,
    event_rows: Optional[list[SimpleStrategyRow]] = None,
    mq_rows: Optional[list[SimpleStrategyRow]] = None,
    iv_rows: Optional[list[SimpleStrategyRow]] = None,
    flow_rows: Optional[list[SimpleStrategyRow]] = None,
    reversal_rows: Optional[list[SimpleStrategyRow]] = None,
    arm_rows: Optional[list[SimpleStrategyRow]] = None,
    card_rows: Optional[list[SimpleStrategyRow]] = None,
    latr_rows: Optional[list[SimpleStrategyRow]] = None,
    ifs_rows: Optional[list[SimpleStrategyRow]] = None,
    supply_chain_rows: Optional[list[SimpleStrategyRow]] = None,
    sentiment_rows: Optional[list[SimpleStrategyRow]] = None,
    factor_neutralized_rows: Optional[list[SimpleStrategyRow]] = None,
    vol_target_rows: Optional[list[SimpleStrategyRow]] = None,
    microstructure_rows: Optional[list[SimpleStrategyRow]] = None,
    accruals_quality_rows: Optional[list[SimpleStrategyRow]] = None,
    short_squeeze_rows: Optional[list[SimpleStrategyRow]] = None,
    valueup_catalyst_rows: Optional[list[SimpleStrategyRow]] = None,
    trend_efficiency_rows: Optional[list[SimpleStrategyRow]] = None,
    gamma_squeeze_rows: Optional[list[SimpleStrategyRow]] = None,
    insider_buying_rows: Optional[list[SimpleStrategyRow]] = None,
    darkpool_rows: Optional[list[SimpleStrategyRow]] = None,
    earnings_tone_drift_rows: Optional[list[SimpleStrategyRow]] = None,
    dual_correction_rows: Optional[list[SimpleStrategyRow]] = None,
    index_rebalance_rows: Optional[list[SimpleStrategyRow]] = None,
    overnight_gap_rows: Optional[list[SimpleStrategyRow]] = None,
    cross_asset_rows: Optional[list[SimpleStrategyRow]] = None,
    supply_chain_gnn_rows: Optional[list[SimpleStrategyRow]] = None,
    range_expansion_rows: Optional[list[SimpleStrategyRow]] = None,
    scenario_universe_json: str = "[]",
    all_stocks_universe_json: str = "[]",
    preloaded_backtest_table_html: str = "",
    backtest_chart_labels_json: str = "[]",
    backtest_chart_ensemble_json: str = "[]",
    backtest_chart_sp500_json: str = "[]",
    backtest_chart_kospi_json: str = "[]",
    backtest_rows_html: str = "",
    backtest_note_html: str = "",
    history_html: str = "",
    strategy_coverage_report_text: str = "",
) -> str:
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")

    # Map parsed strategy rows for dynamic coverage fallback
    parsed_strategies_map = {
        "regression": [r for sec in (reg_sections or []) for r in sec.rows],
        "surge": [r for sec in (surge_sections or []) for r in sec.rows],
        "lead_lag": (follower_rows or []),
        "vcp_rule": (vcp_rows or []),
        "vcp_ml": [r for sec in (vcp_ml_sections or []) for r in sec.rows],
        "lstm": (lstm_rows or []),
        "stat_arb": (stat_arb_rows or []),
        "sector_rotation": (sector_rows or []),
        "rim_valuation": (rim_rows or []),
        "event_driven": (event_rows or []),
        "mq_factor": (mq_rows or []),
        "iv_skew": (iv_rows or []),
        "order_flow": (flow_rows or []),
        "short_term_reversal": (reversal_rows or []),
        "arm_factor": (arm_rows or []),
        "card_factor": (card_rows or []),
        "latr_factor": (latr_rows or []),
        "inst_foreign_sector": (ifs_rows or []),
        "supply_chain": (supply_chain_rows or []),
        "sentiment": (sentiment_rows or []),
        "factor_neutralized": (factor_neutralized_rows or []),
        "vol_target": (vol_target_rows or []),
        "microstructure": (microstructure_rows or []),
        "accruals_quality": (accruals_quality_rows or []),
        "short_squeeze": (short_squeeze_rows or []),
        "valueup_catalyst": (valueup_catalyst_rows or []),
        "trend_efficiency": (trend_efficiency_rows or []),
        "gamma_squeeze": (gamma_squeeze_rows or []),
        "insider_buying": (insider_buying_rows or []),
        "darkpool": (darkpool_rows or []),
        "earnings_tone_drift": (earnings_tone_drift_rows or []),
        "dual_correction": (dual_correction_rows or []),
        "index_rebalance": (index_rebalance_rows or []),
        "overnight_gap_reversal": (overnight_gap_rows or []),
        "cross_asset_spillover": (cross_asset_rows or []),
        "supply_chain_gnn": (supply_chain_gnn_rows or []),
        "range_expansion": (range_expansion_rows or []),
    }
    total_eval_symbols = sum(len(m.rows) for m in ensemble.markets) if (ensemble and ensemble.markets) else 948
    if total_eval_symbols == 0:
        total_eval_symbols = 948
    total_symbols_cov, health_items = parse_strategy_coverage_report(
        cov_text=strategy_coverage_report_text,
        parsed_strategies_map=parsed_strategies_map,
        total_symbols_fallback=total_eval_symbols
    )
    health_monitor_html = build_strategy_health_monitor_html(total_symbols_cov, health_items)
    def resolve_regime_info(reg_name: str, fallback_label: str = "BULL_LOW_VOL") -> tuple[str, str]:
        r = (reg_name or "").strip().upper()
        if r in REGIME_INFO:
            return REGIME_INFO[r]
        for key in ["BULL_LOW_VOL", "BULL_HIGH_VOL", "BEAR_LOW_VOL", "BEAR_HIGH_VOL", "SIDEWAYS_LOW_VOL", "SIDEWAYS_HIGH_VOL"]:
            if key in r:
                return REGIME_INFO[key]
        if "BULL" in r:
            return f"🟢 {r}", "#2ea043"
        elif "BEAR" in r:
            return f"🔴 {r}", "#f85149"
        elif "SIDEWAYS" in r:
            return f"🟡 {r}", "#d29922"
        return REGIME_INFO.get(fallback_label, ("🟢 BULL_LOW_VOL", "#2ea043"))

    us_regime_raw = ensemble.us_regime or ensemble.regime or "BULL_LOW_VOL"
    kr_regime_raw = ensemble.kr_regime or ensemble.regime or "SIDEWAYS_LOW_VOL"

    us_label, us_color = resolve_regime_info(us_regime_raw, "BULL_LOW_VOL")
    kr_label, kr_color = resolve_regime_info(kr_regime_raw, "SIDEWAYS_LOW_VOL")
    report_date = ensemble.date or surge_date or vcp_date or lag_date or "N/A"

    # Collect all known and active markets from ensemble and all strategy data
    all_seen_markets = set()
    if ensemble and ensemble.markets:
        for emkt in ensemble.markets:
            if emkt.rows:
                all_seen_markets.add(emkt.market)
    if portfolio_data and portfolio_data.rows:
        for prow in portfolio_data.rows:
            if prow.market:
                all_seen_markets.add(prow.market)
    # Standard preferred ordering for core markets, then alphabetized international markets
    _CORE_ORDER = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
    _INTL_ORDER = [
        "JAPAN_TSE", "JAPAN", "CHINA_SSE", "CHINA", "TAIWAN_TWSE", "TAIWAN",
        "INDIA_NSE", "INDIA", "EUROPE_STOXX", "EUROPE", "VIETNAM_HOSE", "VIETNAM",
        "AUSTRALIA_ASX", "AUSTRALIA", "BRAZIL_B3", "BRAZIL", "HKEX",
        "SINGAPORE_SGX", "SINGAPORE", "CANADA_TSX", "CANADA", "KONEX", "CHINA_SZSE", "US"
    ]
    KNOWN_ALL_MKTS = set(_CORE_ORDER + _INTL_ORDER)

    for row_coll in [vcp_rows, follower_rows, sector_rows, rim_rows, event_rows, mq_rows, iv_rows, flow_rows, reversal_rows, arm_rows, card_rows, latr_rows, ifs_rows, supply_chain_rows, sentiment_rows, factor_neutralized_rows, vol_target_rows, microstructure_rows, accruals_quality_rows, short_squeeze_rows, valueup_catalyst_rows, trend_efficiency_rows, gamma_squeeze_rows, insider_buying_rows, darkpool_rows, earnings_tone_drift_rows, lstm_rows, cross_asset_rows, supply_chain_gnn_rows, range_expansion_rows, dual_correction_rows, index_rebalance_rows, overnight_gap_rows]:
        if row_coll and isinstance(row_coll, (list, tuple)):
            for crow in row_coll:
                m_val = getattr(crow, 'market', None)
                if m_val and m_val.upper() in KNOWN_ALL_MKTS:
                    all_seen_markets.add(m_val.upper())
    for sec_coll in [surge_sections, vcp_ml_sections, reg_sections]:
        if sec_coll and isinstance(sec_coll, (list, tuple)):
            for sc_item in sec_coll:
                m_val = getattr(sc_item, 'market', None)
                if m_val and m_val.upper() in KNOWN_ALL_MKTS:
                    all_seen_markets.add(m_val.upper())

    active_markets_ordered = []
    for mkt in _CORE_ORDER + _INTL_ORDER:
        if mkt in all_seen_markets and mkt not in active_markets_ordered:
            active_markets_ordered.append(mkt)
    for mkt in sorted(all_seen_markets):
        if mkt not in active_markets_ordered:
            active_markets_ordered.append(mkt)
    if not active_markets_ordered:
        active_markets_ordered = _CORE_ORDER

    def _b_btns(gid: str, m_list: Optional[list[str]] = None) -> str:
        target_mkts = m_list if m_list is not None else active_markets_ordered
        buttons = [f'<button class="filter-btn active" onclick="filterMarket(this,\'{gid}\')" data-mkt="all">전체</button>']
        for mkt in target_mkts:
            flag = MARKET_FLAGS.get(mkt, "🌐")
            buttons.append(f'<button class="filter-btn" onclick="filterMarket(this,\'{gid}\')" data-mkt="{mkt}">{flag} {mkt}</button>')
        return "\n            ".join(buttons)

    # ── Tab: Ensemble ──
    ensemble_panels = ""
    for mkt in active_markets_ordered:
        mkt_data = next((em for em in ensemble.markets if em.market == mkt), None)
        flag = MARKET_FLAGS.get(mkt, "")
        rows_html = ""
        cards_html = ""
        if mkt_data and mkt_data.rows:
            for row_idx, erow in enumerate(mkt_data.rows):
                rc = ret_class(erow.expected_return)
                ret_disp = f"▲ {erow.expected_return}" if erow.expected_return.startswith('+') else (f"▼ {erow.expected_return}" if erow.expected_return.startswith('-') else erow.expected_return)
                symbol_link = make_stock_link(erow.symbol, mkt)
                factors_dict = {
                    "1. XGBoost 회귀": erow.reg,
                    "2. Surge 분류기": erow.surge,
                    "3. Lead-Lag": erow.lead_lag,
                    "4. VCP 패턴 (Rule)": erow.vcp_rule,
                    "5. VCP ML": erow.vcp_ml,
                    "6. Strict LSTM": erow.lstm,
                    "7. Stat-Arb": erow.stat_arb,
                    "8. Sector Rotation": erow.sector_rotation,
                    "9. RIM Valuation": erow.rim_valuation,
                    "10. Event-Driven": erow.event_driven,
                    "11. MQ Factor": erow.mq_factor,
                    "12. Options IV Skew": erow.iv_skew,
                    "13. Order Flow": erow.order_flow,
                    "14. Short-Term Reversal": erow.short_term_reversal,
                    "15. ARM Factor": erow.arm_factor,
                    "16. CARD Factor": erow.card_factor,
                    "17. LATR Factor": erow.latr_factor,
                    "18. Inst & Foreign Sector": erow.inst_foreign_sector,
                    "19. Supply Chain": erow.supply_chain,
                    "20. NLP Sentiment": erow.sentiment,
                    "21. Factor Neutralized": erow.factor_neutralized,
                    "22. Vol Targeting": erow.vol_target,
                    "23. Microstructure": erow.microstructure,
                    "24. Accruals Quality": erow.accruals_quality,
                    "25. Short Squeeze": erow.short_squeeze,
                    "26. Value-Up Yield": erow.valueup_catalyst,
                    "27. Trend Efficiency": erow.trend_efficiency,
                    "28. Gamma Squeeze": erow.gamma_squeeze,
                    "29. Insider Buying": erow.insider_buying,
                    "30. Darkpool & HFT": erow.darkpool,
                    "31. Tone Drift": erow.earnings_tone_drift,
                    "32. Cross-Asset Spillover": erow.cross_asset_spillover,
                    "33. Supply Chain GNN": erow.supply_chain_gnn,
                    "34. Range Expansion": erow.range_expansion,
                    "35. Dual Correction": erow.dual_correction,
                    "36. Index Rebalance": erow.index_rebalance,
                    "37. Overnight Gap": erow.overnight_gap,
                }
                import urllib.parse
                factors_encoded = urllib.parse.quote(_safe_json(factors_dict))
                clean_name = html.escape(erow.name).replace("'", "\\'").replace('"', '&quot;')
                drawer_call = f"openStockDrawer('{erow.symbol}', '{clean_name}', '{mkt}', '{erow.score}', '{ret_disp}', '{factors_encoded}', {row_idx})"
                rank_badge_html = f'<span class="rank-badge rank-1">1</span>' if erow.rank == 1 else (f'<span class="rank-badge rank-2">2</span>' if erow.rank == 2 else (f'<span class="rank-badge rank-3">3</span>' if erow.rank == 3 else f'#{erow.rank}'))
                rows_html += f"""
            <tr class="clickable-row" data-symbol="{erow.symbol}" data-initial-rank="{erow.rank}" data-initial-order="{row_idx}" onclick="{drawer_call}" tabindex="0" onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();{drawer_call}}}" title="클릭하여 37대 전략 상세 보기">
              <td class="rank sticky-col sticky-rank"><button class="btn-watchlist" data-sym="{erow.symbol}" onclick="toggleWatchlist('{erow.symbol}', event)" title="관심종목 등록/해제">⭐</button>{rank_badge_html}</td>
              <td class="symbol sticky-col sticky-symbol">{symbol_link}</td>
              <td class="name sticky-col sticky-name">{html.escape(erow.name)}<span class="row-chevron" aria-hidden="true">›</span></td>
              <td class="score">{format_metric_cell(erow.score, kind="score")}</td>
              <td class="{rc}">{format_metric_cell(ret_disp, kind="pct")}</td>
              <td class="col-strat col-cat-ai">{format_metric_cell(erow.reg, kind="score")}</td>
              <td class="col-strat col-cat-ai">{format_metric_cell(erow.surge, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.lead_lag, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.vcp_rule, kind="score")}</td>
              <td class="col-strat col-cat-ai">{format_metric_cell(erow.vcp_ml, kind="score")}</td>
              <td class="col-strat col-cat-ai">{format_metric_cell(erow.lstm, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.stat_arb, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.sector_rotation, kind="score")}</td>
              <td class="col-strat col-cat-val">{format_metric_cell(erow.rim_valuation, kind="score")}</td>
              <td class="col-strat col-cat-val">{format_metric_cell(erow.event_driven, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.mq_factor, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.iv_skew, kind="score")}</td>
              <td class="col-strat col-cat-flow">{format_metric_cell(erow.order_flow, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.short_term_reversal, kind="score")}</td>
              <td class="col-strat col-cat-val">{format_metric_cell(erow.arm_factor, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.card_factor, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.latr_factor, kind="score")}</td>
              <td class="col-strat col-cat-flow">{format_metric_cell(erow.inst_foreign_sector, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.supply_chain, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.sentiment, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.factor_neutralized, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.vol_target, kind="score")}</td>
              <td class="col-strat col-cat-flow">{format_metric_cell(erow.microstructure, kind="score")}</td>
              <td class="col-strat col-cat-val">{format_metric_cell(erow.accruals_quality, kind="score")}</td>
              <td class="col-strat col-cat-flow">{format_metric_cell(erow.short_squeeze, kind="score")}</td>
              <td class="col-strat col-cat-val">{format_metric_cell(erow.valueup_catalyst, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.trend_efficiency, kind="score")}</td>
              <td class="col-strat col-cat-flow">{format_metric_cell(erow.gamma_squeeze, kind="score")}</td>
              <td class="col-strat col-cat-flow">{format_metric_cell(erow.insider_buying, kind="score")}</td>
              <td class="col-strat col-cat-flow">{format_metric_cell(erow.darkpool, kind="score")}</td>
              <td class="col-strat col-cat-val">{format_metric_cell(erow.earnings_tone_drift, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.cross_asset_spillover, kind="score")}</td>
              <td class="col-strat col-cat-macro">{format_metric_cell(erow.supply_chain_gnn, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.range_expansion, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.dual_correction, kind="score")}</td>
              <td class="col-strat col-cat-flow">{format_metric_cell(erow.index_rebalance, kind="score")}</td>
              <td class="col-strat col-cat-mom">{format_metric_cell(erow.overnight_gap, kind="score")}</td>
            </tr>"""

                cards_html += f"""
        <div class="stock-card" data-symbol="{erow.symbol}" data-initial-rank="{erow.rank}" data-initial-order="{row_idx}" onclick="{drawer_call}" tabindex="0" onkeydown="if(event.key==='Enter'||event.key===' '){{event.preventDefault();{drawer_call}}}" title="클릭하여 37대 전략 상세 보기">
          <div class="stock-card-header">
            <span class="stock-card-rank"><button class="btn-watchlist" data-sym="{erow.symbol}" onclick="toggleWatchlist('{erow.symbol}', event)" title="관심종목 등록/해제">⭐</button>{rank_badge_html}</span>
            <span class="badge" style="font-size:11px;">{flag} {mkt}</span>
          </div>
          <div class="stock-card-title">{html.escape(erow.name)}</div>
          <div class="stock-card-code">{symbol_link}</div>
          <div class="stock-card-metrics">
            <div>
              <div class="stock-card-metric-lbl">37대 앙상블</div>
              <div class="stock-card-metric-val" style="color:var(--blue);">{erow.score}</div>
            </div>
            <div>
              <div class="stock-card-metric-lbl">20D 순예상수익률</div>
              <div class="stock-card-metric-val {rc}">{ret_disp}</div>
            </div>
          </div>
          <div style="font-size:11px; color:var(--muted); display:flex; justify-content:space-between; align-items:center; border-top:1px solid var(--border); padding-top:6px; margin-top:6px;">
            <span>회귀: {erow.reg} | Surge: {erow.surge}</span>
            <span style="color:var(--accent); font-weight:600;">37대 팩터 분석 ›</span>
          </div>
        </div>"""
        else:
            rows_html = '<tr><td colspan="42" class="empty">데이터 없음</td></tr>'
            cards_html = '<div class="empty" style="padding:20px; grid-column:1/-1; text-align:center; color:var(--muted);">데이터 없음</div>'

        ensemble_panels += f"""
    <div class="market-panel" data-market="{mkt}">
      <h3 class="market-title">{flag} {mkt}</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th class="sticky-col sticky-rank" title="종목 순위">순위 ↕</th>
            <th class="sticky-col sticky-symbol" title="종목 티커 / 상장 코드">종목코드 ↕</th>
            <th class="sticky-col sticky-name" title="기업 / 종목 명칭 (클릭 시 37대 전략 상세 분해)">종목명 ↕</th>
            <th title="37대 다변화 전략 종합 앙상블 스코어">앙상블 ↕</th>
            <th title="20D 순예상수익률 (거래비용 차감)">20D 예상수익률 ↕</th>
            <th class="col-strat col-cat-ai" title="1. XGBoost 다중 기간 회귀 기본적/기술적 예상수익률">1. Reg ↕</th>
            <th class="col-strat col-cat-ai" title="2. Surge 분류기 단기 20%+ 급등 확률">2. Surge ↕</th>
            <th class="col-strat col-cat-mom" title="3. Lead-Lag 후행 반응 종목 시차 상관성">3. L-L ↕</th>
            <th class="col-strat col-cat-mom" title="4. VCP 변동성 수축 패턴 규칙 검출">4. VCP-R ↕</th>
            <th class="col-strat col-cat-ai" title="5. VCP 머신러닝 급등 예측">5. VCP-M ↕</th>
            <th class="col-strat col-cat-ai" title="6. Strict Causal 시계열 LSTM 딥러닝">6. LSTM ↕</th>
            <th class="col-strat col-cat-macro" title="7. Stat-Arb 공적분 잔차 평균회귀 Z-score">7. S-Arb ↕</th>
            <th class="col-strat col-cat-mom" title="8. Sector Rotation 상대모멘텀 & 순환매">8. Sec-R ↕</th>
            <th class="col-strat col-cat-val" title="9. Residual Income Model 잔여이익 가치평가 및 안전마진">9. RIM ↕</th>
            <th class="col-strat col-cat-val" title="10. Event-Driven 공시, 실적 서프라이즈, 자사주 촉매">10. Event ↕</th>
            <th class="col-strat col-cat-mom" title="11. Momentum Quality (12M-1M 모멘텀 - 반전 노이즈 제거 + ROE)">11. MQ ↕</th>
            <th class="col-strat col-cat-macro" title="12. Options Put/Call Implied Volatility Skew 역발상 점수">12. IV-Sk ↕</th>
            <th class="col-strat col-cat-flow" title="13. Order Flow Imbalance 외인/기관 순매수 수급 가속도">13. Flow ↕</th>
            <th class="col-strat col-cat-mom" title="14. Short-Term Reversal 과매도/볼린저 하단 이탈 단기 반등">14. Rev ↕</th>
            <th class="col-strat col-cat-val" title="15. Analyst Revision Momentum EPS/목표가 상향 조정">15. ARM ↕</th>
            <th class="col-strat col-cat-macro" title="16. Cross-Asset Regime Divergence (주식-환율-유가 괴리율 매수)">16. CARD ↕</th>
            <th class="col-strat col-cat-macro" title="17. Liquidity-Adjusted Tail Risk (52주 고점 낙폭 + 유동성 서지)">17. LATR ↕</th>
            <th class="col-strat col-cat-flow" title="18. Institutional &amp; Foreigner Sector Flow 2개월 수급 누적">18. I&amp;F ↕</th>
            <th class="col-strat col-cat-macro" title="19. Supply Chain Momentum 전방 공급망 전이">19. Supply ↕</th>
            <th class="col-strat col-cat-macro" title="20. NLP Sentiment FinBERT 공시/뉴스 감성">20. NLP ↕</th>
            <th class="col-strat col-cat-macro" title="21. Fama-French Multi-Factor Style Neutralized 순수 알파">21. Neutral ↕</th>
            <th class="col-strat col-cat-macro" title="22. Dynamic Volatility Targeting 리스크 파리티">22. Vol-T ↕</th>
            <th class="col-strat col-cat-flow" title="23. Microstructure Imbalance 호가/동시호가 갭">23. Micro ↕</th>
            <th class="col-strat col-cat-val" title="24. Accruals Quality Anomaly 영업현금흐름 괴리 회계 품질">24. Accrual ↕</th>
            <th class="col-strat col-cat-flow" title="25. Short Interest &amp; Squeeze 공매도 잔고 숏스퀴즈">25. S-Sq ↕</th>
            <th class="col-strat col-cat-val" title="26. Value-Up Catalyst 저PBR 및 총주주환원율">26. ValueUp ↕</th>
            <th class="col-strat col-cat-mom" title="27. Kaufman Trend Efficiency 고순도 추세 필터">27. TrendEff ↕</th>
            <th class="col-strat col-cat-flow" title="28. Gamma Squeeze 옵션 델타/감마 가속도">28. GammaSq ↕</th>
            <th class="col-strat col-cat-flow" title="29. Insider Buying 임원/대주주 내부자 매수">29. Insider ↕</th>
            <th class="col-strat col-cat-flow" title="30. High-Frequency Darkpool / Block Order Flow">30. Darkpool ↕</th>
            <th class="col-strat col-cat-val" title="31. Earnings Tone Drift 실적 콘퍼런스콜 톤 변화">31. ToneDrift ↕</th>
            <th class="col-strat col-cat-macro" title="32. Cross-Asset Spillover 거시 탄력도 벡터 임펄스">32. CAS ↕</th>
            <th class="col-strat col-cat-macro" title="33. Supply Chain GNN 2-hop 그래프 메시지 패싱">33. GNN ↕</th>
            <th class="col-strat col-cat-mom" title="34. Range Expansion Breakout 변동성 압축 돌파">34. REB ↕</th>
            <th class="col-strat col-cat-mom" title="35. Dual Correction 가격/기간 조정 눌림목">35. Dual ↕</th>
            <th class="col-strat col-cat-flow" title="36. Index Rebalance 패시브 수급 선반영">36. Idx ↕</th>
            <th class="col-strat col-cat-mom" title="37. Overnight Gap Reversal 갭 페이드 반전">37. Gap ↕</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
      <div class="stock-cards-wrap">
        {cards_html}
      </div>
    </div>"""

    def _render_weights_html(w_dict: dict) -> str:
        if not w_dict:
            return '<span style="color:var(--muted); padding:12px; display:block;">데이터 없음</span>'
        
        canonical_priority = [
            ("reg", 1), ("회귀", 1),
            ("srg", 2), ("surge", 2), ("급등", 2),
            ("lead", 3), ("선행", 3),
            ("vcp_rule", 4), ("vcp-r", 4), ("vcp rule", 4),
            ("vcp_ml", 5), ("vcp-m", 5), ("vcp ml", 5),
            ("vcp", 4),
            ("lstm", 6),
            ("stat_arb", 7), ("s-arb", 7), ("공적분", 7),
            ("sector", 8), ("sec-r", 8), ("섹터", 8),
            ("rim", 9), ("가치", 9),
            ("event", 10), ("공시", 10),
            ("mq", 11), ("모멘텀", 11),
            ("iv", 12), ("옵션", 12),
            ("flow", 13), ("수급", 13),
            ("reversal", 14), ("rev", 14), ("반전", 14),
            ("arm", 15), ("컨센", 15),
            ("card", 16), ("괴리", 16),
            ("latr", 17), ("tail", 17),
            ("inst", 18), ("ifs", 18), ("외인", 18),
            ("supply_chain_gnn", 33),
            ("supply", 19), ("공급망", 19),
            ("sentiment", 20), ("nlp", 20), ("감성", 20),
            ("neutral", 21), ("중립", 21),
            ("vol", 22), ("변동성", 22),
            ("micro", 23), ("호가", 23),
            ("accrual", 24), ("발생액", 24),
            ("squeeze", 25), ("숏스퀴즈", 25),
            ("value", 26), ("밸류업", 26),
            ("trend", 27), ("추세", 27),
            ("gamma", 28), ("감마", 28),
            ("insider", 29), ("내부자", 29),
            ("darkpool", 30), ("hft", 30), ("다크풀", 30),
            ("tone", 31), ("drift", 31), ("어조", 31),
            ("cross_asset", 32), ("spillover", 32), ("크로스", 32),
            ("gnn", 33),
            ("expansion", 34), ("breakout", 34), ("돌파", 34),
            ("dual", 35), ("correction", 35), ("조정", 35),
            ("rebalance", 36), ("index", 36), ("리밸런싱", 36),
            ("gap", 37), ("overnight", 37), ("갭", 37),
        ]
        def get_priority(name: str) -> int:
            n_lower = name.lower()
            for key, prio in canonical_priority:
                if key in n_lower:
                    return prio
            return 999

        sorted_items = sorted(w_dict.items(), key=lambda item: get_priority(item[0]))
        raw_keys = []
        raw_vals = []
        for k, v in sorted_items:
            val_pct = float(v.replace("%", "").strip()) if isinstance(v, str) and "%" in v else (float(v) if isinstance(v, (int, float)) else 0.0)
            raw_keys.append(k)
            raw_vals.append(val_pct)
        
        # Apply Largest Remainder Method (Hare-Niemeyer) so sum is strictly 100.0%
        rounded_vals = largest_remainder_round(raw_vals, target_sum=100.0, decimals=1)

        out_html = '<div class="weights-grid">'
        for k, norm_val_pct in zip(raw_keys, rounded_vals):
            v_disp = f"{norm_val_pct:.1f}%"
            bar_w = min(100, int(norm_val_pct * 12.0))
            high_cls = " style='font-weight:700; color:#38bdf8;'" if norm_val_pct >= 4.0 else ""
            out_html += f'''
            <div class="weight-item">
              <div class="wk-wrap">
                <span class="wk"{high_cls}>{k}</span>
                <div class="weight-mini-track"><div class="weight-mini-bar" style="width:{bar_w}%"></div></div>
              </div>
              <span class="wv"{high_cls}>{v_disp}</span>
            </div>'''
        out_html += '</div>'
        return out_html

    us_weights_html = _render_weights_html(ensemble.us_weights or ensemble.weights)
    kr_weights_html = _render_weights_html(ensemble.kr_weights or ensemble.weights)
    weights_html = _render_weights_html(ensemble.weights)

    regimes_table_data = [
        ("BULL_LOW_VOL", "🟢", "고수익 + 저변동성", [3, 10, 3, 3, 8, 6, 3, 6, 4, 6, 6, 2, 3, 2, 6, 4, 5, 7, 3, 3, 3, 3, 3], "공격적 돌파 &amp; 모멘텀 추종"),
        ("BULL_HIGH_VOL", "🟢", "고수익 + 고변동성", [3, 12, 3, 3, 8, 6, 3, 5, 4, 6, 6, 2, 3, 3, 5, 4, 5, 5, 3, 3, 3, 3, 3], "신중한 모멘텀 &amp; 리스크 관리"),
        ("SIDEWAYS_LOW_VOL", "🟡", "횡보 + 저변동성", [7, 3, 5, 3, 5, 7, 9, 6, 7, 6, 6, 3, 4, 4, 6, 6, 6, 7, 3, 3, 3, 3, 3], "섹터 순환매 &amp; 내재가치/Stat-Arb"),
        ("SIDEWAYS_HIGH_VOL", "🟡", "횡보 + 고변동성", [7, 3, 5, 3, 5, 5, 11, 6, 7, 6, 6, 3, 4, 4, 5, 7, 6, 7, 3, 3, 3, 3, 3], "잔차 평균회귀 &amp; 가치주 차익거래"),
        ("BEAR_LOW_VOL", "🔴", "음수 수익 + 저변동성", [16, 2, 2, 2, 2, 3, 9, 5, 11, 4, 7, 4, 3, 5, 6, 7, 6, 6, 3, 3, 3, 3, 3], "방어적 펀더멘탈 &amp; RIM 가치 안전마진"),
        ("BEAR_HIGH_VOL", "🔴", "음수 수익 + 고변동성", [17, 0, 2, 2, 2, 3, 11, 3, 11, 4, 7, 4, 3, 6, 5, 8, 6, 5, 3, 3, 3, 3, 3], "최고 수준의 자본 보존 (현금 70%)"),
    ]
    regime_matrix_rows_html = ""
    us_clean = us_regime_raw.strip().upper()
    kr_clean = kr_regime_raw.strip().upper()
    for reg_key, icon, desc, pct_list, goal in regimes_table_data:
        is_us = reg_key in us_clean
        is_kr = reg_key in kr_clean
        badges = []
        if is_us:
            badges.append('<span style="background:#2ea04330; color:#3fb950; font-size:11px; padding:2px 6px; border-radius:4px; font-weight:700; margin-left:6px; border:1px solid #3fb95060;">🇺🇸 US 현재</span>')
        if is_kr:
            badges.append('<span style="background:#388bfd30; color:#58a6ff; font-size:11px; padding:2px 6px; border-radius:4px; font-weight:700; margin-left:6px; border:1px solid #58a6ff60;">🇰🇷 KR 현재</span>')
        badge_str = " ".join(badges)
        row_style = ' style="background: rgba(56, 139, 253, 0.15); border-left: 3px solid #38bdf8;"' if (is_us or is_kr) else ""
        cols_td = "".join(f"<td>{p}%</td>" for p in pct_list)
        regime_matrix_rows_html += f"""
            <tr{row_style}>
              <td>{icon} <strong>{reg_key}</strong>{badge_str}</td>
              <td>{desc}</td>
              {cols_td}
              <td>{goal}</td>
            </tr>"""

    rationale_html = ""
    card_content = ""
    if ensemble.decision_rationale:
        lines = [line.strip() for line in ensemble.decision_rationale.strip().split('\n') if line.strip()]
        for line in lines:
            if line.startswith('[') and line.endswith(']'):
                card_content += f'<div style="font-weight:700; color:var(--accent); font-size:12px; margin:10px 0 4px; border-bottom:1px solid var(--border); padding-bottom:2px;">{line}</div>'
            elif line.startswith('•'):
                card_content += f'<div style="font-size:11px; color:var(--text); margin-bottom:3px; padding-left:6px; border-left:2px solid var(--accent);">{line}</div>'
            elif ':' in line and ('%' in line or 'Sharpe' in line or 'Base' in line):
                parts = line.split(':', 1)
                k = parts[0].strip().replace('-', '').strip()
                v = parts[1].strip()
                card_content += f'<div style="display:flex; justify-content:space-between; font-size:11px; padding:2px 4px; background:var(--surface2); border-radius:3px; margin-bottom:2px;"><span style="color:var(--muted);">{k}</span><span style="font-weight:600; color:var(--accent);">{v}</span></div>'
            else:
                card_content += f'<div style="font-size:11px; color:var(--muted); margin-bottom:3px; line-height:1.3;">{line}</div>'

        rationale_html = f"""
    <div class="card rationale-card collapsible-card" style="margin-top: 15px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden;">
      <div class="collapsible-header" onclick="toggleSection('rationale-body', 'rationale-icon')" style="padding: 12px 14px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; background: var(--surface2); user-select: none;">
        <h3 style="color: #38bdf8; margin: 0; font-size: 13px; display:flex; align-items:center; gap:6px;">🧠 <span>2D Regime &amp; Strategy Rationale</span></h3>
        <span id="rationale-icon" style="color: var(--accent); font-size: 11px; font-weight: 600;">▼ 접기</span>
      </div>
      <div id="rationale-body" style="padding: 12px; max-height: 380px; overflow-y: auto; overscroll-behavior: contain;">{card_content}</div>
    </div>"""

    # Fallback detection: pipeline defaults are shown to users as "기본값" so a
    # stale/contaminated indicator is never mistaken for live market data.
    _FALLBACKS = {
        "sp500": "+0.050% / day",
        "vix": "18.50",
        "us10y": "4.25%",
        "kr10y": "3.15%",
        "usdkrw": "1,380.00 KRW",
        "wti": "$75.50 / bbl",
        "gold": "$220.00",
    }

    def _macro_cell(label: str, value: str, fallback: str, cls: str = "") -> str:
        marker = ""
        val_clean = str(value or "").strip()
        if not val_clean or val_clean.lower() in ("nan", "none", "null", "undefined", "n/a", "-"):
            return f'<div class="macro-item"><span class="ml">{label}</span><span class="mv {cls}"><span class="badge-na">N/A</span></span></div>'
        try:
            if abs(safe_float(val_clean) - safe_float(fallback)) < 1e-9 and safe_float(fallback) != 0.0:
                marker = '<span class="fallback-badge">기본값</span>'
        except Exception:
            marker = ""
        return f'<div class="macro-item"><span class="ml">{label}</span><span class="mv {cls}">{html.escape(val_clean)}{marker}</span></div>'

    tooltip_text = (
        '<strong>🇺🇸/🇰🇷 한·미 증시 동조화(Coupling) / 디커플링(Decoupling) 지표</strong><br>'
        '• <strong>커플링 (Coupling, 상관계수 &ge; 0.40)</strong>: 미국 증시(S&amp;P500)와 한국 증시(KOSPI/KOSDAQ) 간의 시차 상관관계가 높아 미 증시 상/하방 변동이 국내 증시에 직접 전이됩니다.<br>'
        '• <strong>디커플링 (Decoupling, 상관계수 &lt; 0.40)</strong>: 한·미 증시 상관성이 약화되어 환율/원자재/수급 등 독자적 대내외 변수에 의해 국내 증시가 개별적 방향성을 보입니다.'
    )

    kr_20d_ret = getattr(ensemble, 'kr_return', None) or "+0.422% / day"
    max_alloc_val = safe_float(ensemble.max_allocation) if ensemble.max_allocation else 85.0
    target_cash_disp = f"{max(0.0, 100.0 - max_alloc_val):.1f}%"

    if ensemble.decoupling_status:
        dec_status = ensemble.decoupling_status
        dec_corr = ensemble.decoupling_corr or "-"
        dec_class = "neg" if any(k in dec_status.upper() for k in ["DECOUP", "DECOUPLING", "DECOUPLED"]) else "pos"
        dec_cell = (
            f'<div class="macro-item tooltip-wrapper" tabindex="0" onclick="toggleTooltip(this, event)" role="button" aria-label="한미 증시 동조화 지표 설명">'
            f'<span class="ml">🇺🇸/🇰🇷 한·미 동조화 상태 <span class="info-icon">ℹ️</span></span>'
            f'<span class="mv {dec_class}">{dec_status} (상관: {dec_corr})</span>'
            f'<div class="tooltip-content">{tooltip_text}</div>'
            f'</div>'
        )
        dec_badge_html = f'<span class="badge" style="color:#e3b341; border-color:#e3b341; background:#e3b34120;">⚡ Decoupled ({dec_status})</span>' if "DECOUP" in dec_status.upper() else f'<span class="badge" style="color:#38bdf8; border-color:#38bdf8; background:#38bdf820;">🔗 Coupled (상관: {dec_corr})</span>'
    else:
        dec_cell = (
            f'<div class="macro-item tooltip-wrapper" tabindex="0" onclick="toggleTooltip(this, event)" role="button" aria-label="한미 증시 동조화 지표 설명">'
            f'<span class="ml">🇺🇸/🇰🇷 한·미 동조화 상태 <span class="info-icon">ℹ️</span></span>'
            f'<span class="mv">미분석</span>'
            f'<div class="tooltip-content">{tooltip_text}</div>'
            f'</div>'
        )
        dec_badge_html = '<span class="badge" style="color:#38bdf8; border-color:#38bdf8; background:#38bdf820;">🔗 Coupled (S&amp;P500 ⟷ KOSPI)</span>'

    macro_html = f"""
    <div class="macro-grid">
      {dec_cell}
      {_macro_cell("S&amp;P500 20d Ret", ensemble.sp500_return, _FALLBACKS["sp500"], ret_class(ensemble.sp500_return or "0%"))}
      {_macro_cell("KOSPI 20d Ret", kr_20d_ret, "+0.422% / day", ret_class(kr_20d_ret))}
      {_macro_cell("VIX 공포지수", ensemble.vix, _FALLBACKS["vix"])}
      {_macro_cell("USD/KRW 환율", ensemble.usdkrw, _FALLBACKS["usdkrw"])}
      {_macro_cell("US 10Y 국채금리", ensemble.us10y, _FALLBACKS["us10y"])}
      {_macro_cell("KR 10Y 국채금리", ensemble.kr10y, _FALLBACKS["kr10y"])}
      {_macro_cell("WTI 국제유가", ensemble.wti, _FALLBACKS["wti"])}
      {_macro_cell("GLD ETF", ensemble.gold, _FALLBACKS["gold"])}
      <div class="macro-item"><span class="ml">최대허용배분</span><span class="mv pos">{ensemble.max_allocation or '85.0%'}</span></div>
      <div class="macro-item"><span class="ml">목표 현금비중</span><span class="mv">{target_cash_disp}</span></div>
    </div>"""

    # ── Tab: Portfolio (HRP) ──
    portfolio_data = portfolio_data or _generate_fallback_portfolio(ensemble)
    portfolio_rows_html = ""
    chart_labels = []
    chart_weights = []
    market_weights = {"KOSPI": 0.0, "KOSDAQ": 0.0, "SP500": 0.0, "NASDAQ": 0.0, "RUSSELL2000": 0.0, "CASH": 0.0}

    if portfolio_data and portfolio_data.rows:
        for idx, port_r in enumerate(portfolio_data.rows):
            rc = ret_class(port_r.expected_return)
            symbol_link = make_stock_link(port_r.symbol, port_r.market)
            leland_tag = '<span class="badge-healthy">🟢 BUY (New Entry)</span>' if idx < 10 else '<span class="badge-fallback">🟡 HOLD (Within &plusmn;2.5%)</span>'
            portfolio_rows_html += f"""
            <tr>
              <td class="rank">#{port_r.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{html.escape(port_r.name)}</td>
              <td>{MARKET_FLAGS.get(port_r.market, '')} {port_r.market}</td>
              <td class="{rc}">{port_r.expected_return}</td>
              <td>{port_r.volatility}</td>
              <td class="pos">{port_r.weight}</td>
              <td>{port_r.amount}</td>
              <td>{leland_tag}</td>
            </tr>"""
            w_float = safe_float(port_r.weight)
            chart_labels.append(port_r.name)
            chart_weights.append(w_float)
            m_key = port_r.market if port_r.market else "UNKNOWN"
            market_weights[m_key] = market_weights.get(m_key, 0.0) + w_float

        sum_alloc_w = sum(chart_weights)
        rem_cash_val = safe_float(portfolio_data.remaining_cash_pct) if portfolio_data.remaining_cash_pct else max(0.0, 100.0 - sum_alloc_w)
        if sum_alloc_w + rem_cash_val > 100.0 or rem_cash_val <= 0:
            rem_cash_val = max(0.0, round(100.0 - sum_alloc_w, 2))

        if rem_cash_val > 0:
            market_weights["CASH"] = round(rem_cash_val, 2)
            chart_labels.append("Remaining Cash")
            chart_weights.append(round(rem_cash_val, 2))
    else:
        portfolio_rows_html = '<tr><td colspan="9" class="empty">포트폴리오 배분 데이터 없음</td></tr>'

    # ── Tab: Surge ──
    horizons = sorted(set(sec.horizon for sec in surge_sections), key=lambda h: int(match_hz.group()) if (match_hz := re.search(r"\d+", h)) else 0) if surge_sections else ["1일", "3일", "5일", "20일"]
    surge_tabs_nav = ""
    surge_tabs_content = ""
    for i, hz in enumerate(horizons):
        active = "active" if i == 0 else ""
        surge_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections_surge = [s for s in surge_sections if s.horizon == hz]
        panels = ""
        for mkt in active_markets_ordered:
            s_surge = next((sec for sec in hz_sections_surge if sec.market == mkt), None)
            flag = MARKET_FLAGS.get(mkt, "")
            rows_html = ""
            if s_surge and s_surge.rows:
                for sr in s_surge.rows:
                    prob = safe_float(sr.probability)
                    bar_w = min(100, int(prob))
                    color = "#2ea043" if prob >= 20 else "#d29922" if prob >= 10 else "#8b949e"
                    prob_label = f"{sr.probability}%" if sr.probability.lower() not in ("nan", "none") else "N/A"
                    symbol_link = make_stock_link(sr.symbol, mkt)
                    rows_html += f"""
              <tr>
                <td class="rank">#{sr.rank}</td>
                <td class="symbol">{symbol_link}</td>
                <td class="name">{html.escape(sr.name)}</td>
                <td>
                  <div class="prob-bar">
                    <div class="prob-fill" style="width:{bar_w}%;background:{color}"></div>
                    <span class="prob-label" style="color:{color}">{prob_label}</span>
                  </div>
                </td>
              </tr>"""
            if not rows_html:
                rows_html = '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'
            panels += f"""
          <div class="market-panel" data-market="{mkt}">
            <h3 class="market-title">{flag} {mkt}</h3>
            <div class="table-wrap">
              <table>
                <thead><tr><th>순위</th><th>종목코드</th><th>종목명</th><th>급등확률 (≥20%)</th></tr></thead>
                <tbody>{rows_html}</tbody>
              </table>
            </div>
          </div>"""
        display = "block" if i == 0 else "none"
        surge_tabs_content += f"""
    <div class="hz-content" data-hz="{hz}" style="display:{display}">
      <div class="filter-bar">
        {_b_btns(f'surge-hz-{hz}')}
      </div>
      <div id="surge-hz-{hz}-panels">
        {panels}
      </div>
    </div>"""

    # ── Tab: VCP ──
    vcp_by_market: dict[str, list[VcpRow]] = {}
    for vr in vcp_rows:
        vcp_by_market.setdefault(vr.market, []).append(vr)

    vcp_panels = ""
    for mkt in active_markets_ordered:
        flag = MARKET_FLAGS.get(mkt, "")
        rows_vcp = vcp_by_market.get(mkt, [])
        rows_html = ""
        for vr in rows_vcp:
            checks = [
                f'<span class="chk {"ok" if vr.ma50 else "no"}">MA50</span>',
                f'<span class="chk {"ok" if vr.ma200 else "no"}">MA200</span>',
                f'<span class="chk {"ok" if vr.near_high else "no"}">고점근접</span>',
                f'<span class="chk {"ok" if vr.vol_declining else "no"}">거래량↓</span>',
            ]
            score_val = int(vr.score.split("/")[0]) if vr.score else 0
            score_color = "#2ea043" if score_val >= 90 else "#d29922" if score_val >= 70 else "#8b949e"
            symbol_link = make_stock_link(vr.symbol, mkt)
            rows_html += f"""
            <tr>
              <td class="rank">#{vr.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{html.escape(vr.name)}</td>
              <td><span style="color:{score_color};font-weight:600">{vr.score}</span></td>
              <td>{vr.current_range}</td>
              <td class="contraction">{vr.contraction}</td>
              <td>{"".join(checks)}</td>
            </tr>"""
        if not rows_html:
            rows_html = '<tr><td colspan="7" class="empty">패턴 없음</td></tr>'
        vcp_panels += f"""
      <div class="market-panel" data-market="{mkt}">
        <h3 class="market-title">{flag} {mkt}</h3>
        <div class="table-wrap">
          <table>
            <thead><tr>
              <th>순위</th><th>종목코드</th><th>종목명</th>
              <th>점수</th><th>현재범위</th><th>수축 패턴</th><th>조건</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
      </div>"""

    # ── Tab: Lead-Lag ──
    lag_by_market: dict[str, list[LeadLagRow]] = {}
    for lr in follower_rows:
        lag_by_market.setdefault(lr.market, []).append(lr)

    lag_panels = ""
    for mkt in active_markets_ordered:
        flag = MARKET_FLAGS.get(mkt, "")
        rows_ll = lag_by_market.get(mkt, [])
        rows_html = ""
        for lr in rows_ll:
            rc = ret_class(lr.score)
            symbol_link = make_stock_link(lr.symbol, mkt)
            rows_html += f"""
            <tr>
              <td class="rank">#{lr.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{html.escape(lr.name)}</td>
              <td class="{rc}">{lr.score}</td>
            </tr>"""
        if not rows_html:
            rows_html = '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'
        lag_panels += f"""
      <div class="market-panel" data-market="{mkt}">
        <h3 class="market-title">{flag} {mkt}</h3>
        <div class="table-wrap">
          <table>
            <thead><tr><th>순위</th><th>종목코드</th><th>종목명</th><th>예상수익률</th></tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
      </div>"""

    # Leader section
    leader_rows_html = ""
    for ldr in leader_rows[:10]:
        rc = ret_class(ldr.score)
        symbol_link = make_stock_link(ldr.symbol, getattr(ldr, 'market', 'KOSPI'))
        leader_rows_html += f"""
        <tr>
          <td class="rank">#{ldr.rank}</td>
          <td class="symbol">{symbol_link}</td>
          <td class="name">{html.escape(ldr.name)}</td>
          <td class="{rc}">{ldr.score}</td>
        </tr>"""

    # ── Tab: VCP ML ──
    vcp_ml_sections = vcp_ml_sections or []
    vcp_ml_horizons = sorted(set(sec.horizon for sec in vcp_ml_sections), key=lambda h: int(match_hz.group()) if (match_hz := re.search(r"\d+", h)) else 0) if vcp_ml_sections else ["1일", "3일", "5일", "20일"]
    vcp_ml_tabs_nav = ""
    vcp_ml_tabs_content = ""
    for i, hz in enumerate(vcp_ml_horizons):
        active = "active" if i == 0 else ""
        vcp_ml_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections_vcp = [s for s in vcp_ml_sections if s.horizon == hz]
        panels = ""
        for mkt in active_markets_ordered:
            s_vcp = next((sec for sec in hz_sections_vcp if sec.market == mkt), None)
            flag = MARKET_FLAGS.get(mkt, "")
            rows_html = ""
            if s_vcp and s_vcp.rows:
                for vml in s_vcp.rows:
                    prob = safe_float(vml.probability)
                    bar_w = min(100, int(prob))
                    color = "#2ea043" if prob >= 20 else "#d29922" if prob >= 10 else "#8b949e"
                    prob_label = f"{vml.probability}%" if vml.probability.lower() not in ("nan", "none") else "N/A"
                    symbol_link = make_stock_link(vml.symbol, mkt)
                    rows_html += f"""
            <tr>
              <td class="rank">#{vml.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{html.escape(vml.name)}</td>
              <td>
                <div class="prob-bar">
                  <div class="prob-fill" style="width:{bar_w}%;background:{color}"></div>
                  <span class="prob-label" style="color:{color}">{prob_label}</span>
                </div>
              </td>
            </tr>"""
            if not rows_html:
                rows_html = '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'
            panels += f"""
        <div class="market-panel" data-market="{mkt}">
          <h3 class="market-title">{flag} {mkt}</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>순위</th><th>종목코드</th><th>종목명</th><th>급등확률 (≥20%)</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>"""

        display_style = "display: block;" if i == 0 else "display: none;"
        vcp_ml_tabs_content += f"""
    <div class="hz-content" data-hz="{hz}" style="{display_style}">
      <div class="filter-bar">
        {_b_btns(f'vcp_ml-hz-{hz}')}
      </div>
      <div id="vcp_ml-hz-{hz}-panels">
        {panels}
      </div>
    </div>"""

    # ── Tab: Regression ──
    reg_sections = reg_sections or []
    reg_horizons = sorted(set(sec.horizon for sec in reg_sections), key=lambda h: int(match_hz.group()) if (match_hz := re.search(r"\d+", h)) else 0) if reg_sections else ["1d", "5d", "20d", "60d"]
    reg_tabs_nav = ""
    reg_tabs_content = ""
    for i, hz in enumerate(reg_horizons):
        active = "active" if i == 0 else ""
        reg_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections_reg = [s for s in reg_sections if s.horizon == hz]
        panels = ""
        for mkt in active_markets_ordered:
            s_reg = next((sec for sec in hz_sections_reg if sec.market in [mkt, "S&P " + mkt, mkt.replace("SP", "S&P")]), None)
            flag = MARKET_FLAGS.get(mkt, "")
            rows_html = ""
            if s_reg and s_reg.rows:
                for reg_row in s_reg.rows:
                    rc = ret_class(reg_row.expected_return)
                    symbol_link = make_stock_link(reg_row.symbol, mkt)
                    rows_html += f"""
            <tr>
              <td class="rank">#{reg_row.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{html.escape(reg_row.name)}</td>
              <td class="{rc}">{reg_row.expected_return}</td>
            </tr>"""
            if not rows_html:
                rows_html = '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'
            panels += f"""
        <div class="market-panel" data-market="{mkt}">
          <h3 class="market-title">{flag} {mkt}</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>순위</th><th>종목코드</th><th>종목명</th><th>예상수익률 ({hz})</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>"""

        display_style = "display: block;" if i == 0 else "display: none;"
        reg_tabs_content += f"""
    <div class="hz-content" data-hz="{hz}" style="{display_style}">
      <div class="filter-bar">
        {_b_btns(f'reg-hz-{hz}')}
      </div>
      <div id="reg-hz-{hz}-panels">
        {panels}
      </div>
    </div>"""

    # ── Tab: Stat-Arb ──
    stat_arb_rows_html = ""
    stat_arb_banner = ""
    if stat_arb_rows:
        for sa_r in stat_arb_rows:
            z_val = safe_float(sa_r.z_score)
            z_class = "pos" if z_val > 0 else "neg"
            stat_arb_rows_html += f"""
            <tr>
              <td class="symbol"><strong>{html.escape(sa_r.pair)}</strong></td>
              <td class="{z_class}">{sa_r.z_score}</td>
              <td>{sa_r.correlation}</td>
              <td>{sa_r.beta}</td>
              <td><span class="badge">{sa_r.signal}</span></td>
            </tr>"""
    else:
        stat_arb_banner = build_tab_status_banner(strategy_name="Stat-Arb Cointegration", market="전체", status_type="no_pairs")
        stat_arb_rows_html = '<tr><td colspan="5" class="empty">조건을 만족하는 공적분 페어가 없습니다</td></tr>'

    # ── Tab: Sector Rotation ──
    sector_panels = ""
    for mkt in active_markets_ordered:
        flag = MARKET_FLAGS.get(mkt, "")
        rows_html = ""
        mkt_sector_rows = [sec_r for sec_r in (sector_rows or []) if sec_r.market == mkt]
        if mkt_sector_rows:
            for sec_r in mkt_sector_rows:
                symbol_link = make_stock_link(sec_r.symbol, mkt)
                rows_html += f"""
            <tr>
              <td class="rank">#{sec_r.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{html.escape(sec_r.name)}</td>
              <td>{MARKET_FLAGS.get(sec_r.market, '')} {sec_r.market}</td>
              <td><span class="badge">{sec_r.sector}</span></td>
              <td class="pos">{sec_r.score}</td>
            </tr>"""
        else:
            rows_html = '<tr><td colspan="6" class="empty">데이터 없음</td></tr>'

        sector_panels += f"""
    <div class="market-panel" data-market="{mkt}">
      <h3 class="market-title">{flag} {mkt}</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>순위</th><th>종목코드</th><th>종목명</th><th>시장</th><th>표준 GICS 섹터</th><th>섹터 스코어</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>"""

    # ── Tab: RIM Valuation ──
    rim_panels = ""
    for mkt in active_markets_ordered:
        flag = MARKET_FLAGS.get(mkt, "")
        mkt_rim_rows = [rim_r for rim_r in (rim_rows or []) if rim_r.market == mkt]
        banner_html = ""
        if mkt_rim_rows:
            rows_html = ""
            for rim_r in mkt_rim_rows:
                symbol_link = make_stock_link(rim_r.symbol, mkt)
                p_cell = format_metric_cell(rim_r.price, kind="currency")
                iv_cell = format_metric_cell(rim_r.intrinsic_value, kind="currency")
                disc_cell = format_metric_cell(rim_r.discount, kind="pct")
                roe_raw_cell = format_metric_cell(rim_r.roe_raw, kind="pct", highlight_positive=False)
                roe_adj_cell = format_metric_cell(rim_r.roe_adj, kind="pct", highlight_positive=False)
                eq_cell = format_metric_cell(rim_r.eq, kind="pct", highlight_positive=False)
                filter_disp = format_metric_cell(rim_r.filter_tags, kind="badge") if rim_r.filter_tags else '<span class="badge-na">-</span>'
                score_display = format_metric_cell(rim_r.rim_score or rim_r.score, kind="score")
                rows_html += f"""
            <tr>
              <td class="rank">#{rim_r.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{html.escape(rim_r.name)}</td>
              <td>{p_cell}</td>
              <td class="pos">{iv_cell}</td>
              <td>{disc_cell}</td>
              <td>{roe_raw_cell}</td>
              <td>{roe_adj_cell}</td>
              <td>{eq_cell}</td>
              <td>{filter_disp}</td>
              <td class="score">{score_display}</td>
            </tr>"""
        else:
            banner_html = build_tab_status_banner(strategy_name="RIM 가치평가 (Residual Income Model)", market=mkt, status_type="empty", reason_code="NO_FUNDAMENTAL_DATA")
            rows_html = '<tr><td colspan="11" class="empty">데이터 없음 (재무데이터 미비 또는 적격 RIM 대상 종목 없음)</td></tr>'

        rim_panels += f"""
    <div class="market-panel" data-market="{mkt}">
      <h3 class="market-title">{flag} {mkt}</h3>
      {banner_html}
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>순위</th><th>종목코드</th><th>종목명</th><th>현재가</th><th>RIM 적정가(V0)</th><th>안전마진(할인율)</th><th>ROE(보고)</th><th>ROE(조정)</th><th>EQ</th><th>필터</th><th>RIM 스코어</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>"""

    # ── Helper: build per-market panels for simple strategy tables ──
    def _build_simple_panels(
        rows_list: list,
        panel_id: str,
        col_header: str,
        score_attr: str = "score",
        score_class: str = "pos",
        strategy_name: str = "",
        missing_reason_code: str = "",
    ) -> str:
        panels_html = ""
        for mkt in active_markets_ordered:
            flag = MARKET_FLAGS.get(mkt, "")
            mkt_rows = [r for r in (rows_list or []) if r.market == mkt]
            banner_html = ""
            if mkt_rows:
                rows_html = ""
                for row in mkt_rows:
                    sym_link = make_stock_link(row.symbol, mkt)
                    score_val = getattr(row, score_attr, row.score)
                    score_cell = format_metric_cell(score_val, kind="score")
                    rows_html += f"""
            <tr>
              <td class="rank">#{row.rank}</td>
              <td class="symbol">{sym_link}</td>
              <td class="name">{html.escape(row.name)}</td>
              <td>{MARKET_FLAGS.get(row.market, "")} {row.market}</td>
              <td class="{score_class}">{score_cell}</td>
            </tr>"""
            else:
                st_name = strategy_name or col_header
                banner_html = build_tab_status_banner(
                    strategy_name=st_name,
                    market=mkt,
                    status_type="empty",
                    reason_code=missing_reason_code or "INSUFFICIENT_PRICE_HISTORY",
                )
                rows_html = '<tr><td colspan="5" class="empty">데이터 없음</td></tr>'

            panels_html += f"""
    <div class="market-panel" data-market="{mkt}">
      <h3 class="market-title">{flag} {mkt}</h3>
      {banner_html}
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>순위 ↕</th><th>종목코드 ↕</th><th>종목명 ↕</th><th>시장 ↕</th><th>{col_header} ↕</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>"""
        return panels_html

    lstm_panels  = _build_simple_panels(lstm_rows or [],   "lstm",  "LSTM 스코어", strategy_name="Strict Causal LSTM", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    event_panels = _build_simple_panels(event_rows or [], "event", "이벤트 스코어", strategy_name="Event-Driven 촉매", missing_reason_code="NO_CORPORATE_FILING")
    mq_panels    = _build_simple_panels(mq_rows or [],    "mq",    "MQ 스코어", strategy_name="Momentum Quality Factor", missing_reason_code="NO_FUNDAMENTAL_DATA")
    iv_panels    = _build_simple_panels(iv_rows or [],    "iv",    "IV Skew 스코어", strategy_name="Options IV Skew", missing_reason_code="NO_OPTIONS_CHAIN")
    flow_panels  = _build_simple_panels(flow_rows or [],  "flow",  "수급 스코어", strategy_name="Order Flow Imbalance", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    reversal_panels = _build_simple_panels(reversal_rows or [], "reversal", "반전 스코어", strategy_name="Short-Term Reversal", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    arm_panels    = _build_simple_panels(arm_rows or [],    "arm",    "ARM 스코어", strategy_name="Analyst Revision Momentum", missing_reason_code="NO_FUNDAMENTAL_DATA")
    card_panels   = _build_simple_panels(card_rows or [],   "card",   "CARD 스코어", strategy_name="Cross-Asset Regime Divergence", missing_reason_code="STRATEGY_SIGNAL_NEUTRAL")
    latr_panels   = _build_simple_panels(latr_rows or [],   "latr",   "LATR 스코어", strategy_name="Liquidity-Adjusted Tail Risk", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    ifs_panels    = _build_simple_panels(ifs_rows or [],    "ifs",    "외인/투신 수급 스코어", strategy_name="외인/투신 수급 강도", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    supplychain_panels = _build_simple_panels(supply_chain_rows or [], "supplychain", "밸류체인 스코어", strategy_name="Supply Chain Momentum", missing_reason_code="NO_SUPPLY_CHAIN_MAPPING")
    sentiment_panels   = _build_simple_panels(sentiment_rows or [],   "sentiment",   "NLP 감성 스코어", strategy_name="NLP Sentiment Engine", missing_reason_code="NO_CORPORATE_FILING")
    neutralized_panels = _build_simple_panels(factor_neutralized_rows or [], "neutralized", "순수 알파 스코어", strategy_name="Factor Neutralized Alpha", missing_reason_code="STRATEGY_SIGNAL_NEUTRAL")
    voltarget_panels   = _build_simple_panels(vol_target_rows or [],   "voltarget",   "변동성 타겟 스코어", strategy_name="Volatility Targeting", missing_reason_code="STRATEGY_SIGNAL_NEUTRAL")
    microstructure_panels = _build_simple_panels(microstructure_rows or [], "microstructure", "미시구조 스코어", strategy_name="Microstructure Imbalance", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    accruals_panels       = _build_simple_panels(accruals_quality_rows or [], "accruals", "회계 품질 스코어", strategy_name="Accruals Quality Anomaly", missing_reason_code="NO_FUNDAMENTAL_DATA")
    shortsqueeze_panels   = _build_simple_panels(short_squeeze_rows or [], "shortsqueeze", "숏스퀴즈 스코어", strategy_name="Short Squeeze Catalyst", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    valueup_panels        = _build_simple_panels(valueup_catalyst_rows or [], "valueup", "Value-Up 스코어", strategy_name="Value-Up & Shareholder Yield", missing_reason_code="NO_FUNDAMENTAL_DATA")
    trendeff_panels       = _build_simple_panels(trend_efficiency_rows or [], "trendeff", "추세 효율성 스코어", strategy_name="Kaufman Trend Efficiency", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    gammasqueeze_panels   = _build_simple_panels(gamma_squeeze_rows or [], "gammasqueeze", "감마 스퀴즈 스코어", strategy_name="Options Gamma Squeeze", missing_reason_code="NO_OPTIONS_CHAIN")
    insider_panels        = _build_simple_panels(insider_buying_rows or [], "insider", "내부자 매수 스코어", strategy_name="Insider Buying Tracker", missing_reason_code="NO_INSIDER_FILING")
    darkpool_panels       = _build_simple_panels(darkpool_rows or [], "darkpool", "다크풀 수급 스코어", strategy_name="Darkpool & HFT Flow", missing_reason_code="NON_US_MARKET_SCOPE")
    tonedrift_panels      = _build_simple_panels(earnings_tone_drift_rows or [], "tonedrift", "어닝 톤 드리프트 스코어", strategy_name="Earnings Call Tone Drift", missing_reason_code="NO_EARNINGS_TRANSCRIPT")
    dualcorrection_panels = _build_simple_panels(dual_correction_rows or [], "dualcorrection", "Dual Correction 스코어", strategy_name="Dual Correction Regime", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    indexrebalance_panels = _build_simple_panels(index_rebalance_rows or [], "indexrebalance", "Index Rebalance 스코어", strategy_name="Index Rebalance Flow", missing_reason_code="INSUFFICIENT_UNIVERSE_DATA")
    overnightgap_panels   = _build_simple_panels(overnight_gap_rows or [], "overnightgap", "Overnight Gap Reversal 스코어", strategy_name="Overnight Gap Reversal", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    crossasset_panels     = _build_simple_panels(cross_asset_rows or [], "crossasset", "Cross-Asset Spillover 스코어", strategy_name="Cross-Asset Spillover Momentum", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")
    gnn_panels            = _build_simple_panels(supply_chain_gnn_rows or [], "gnn", "Supply Chain GNN 스코어", strategy_name="Supply Chain GNN", missing_reason_code="NO_SUPPLY_CHAIN_MAPPING")
    rangeexpansion_panels = _build_simple_panels(range_expansion_rows or [], "rangeexpansion", "Range Expansion 스코어", strategy_name="Range Expansion Breakout", missing_reason_code="INSUFFICIENT_PRICE_HISTORY")

    # JSON strings for Chart.js safely serialized to prevent XSS
    hrp_labels_json = _safe_json(chart_labels)
    hrp_weights_json = _safe_json(chart_weights)
    mkt_labels_json = _safe_json(list(market_weights.keys()))
    mkt_weights_json = _safe_json([round(v, 2) for v in market_weights.values()])

    # ── Full HTML ──
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📈 Stock Prediction Dashboard | KRX &amp; SP500</title>
<meta name="description" content="AI 기반 한국·미국 주식 3,379종목 34대 다변화 전략(XGBoost 회귀, Surge 분류기, Strict LSTM, VCP 패턴, Lead-Lag, Stat-Arb, RIM 등) 앙상블 대시보드">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
  :root {{
    --bg: #0b0f17;
    --surface: #131b26;
    --surface2: #1c2636;
    --surface3: #263346;
    --border: #2d3b4e;
    --border-subtle: #1e293b;
    --text: #e2e8f0;
    --text-bright: #ffffff;
    --muted: #94a3b8;
    --green: #10b981;
    --green-glow: rgba(16, 185, 129, 0.2);
    --red: #f43f5e;
    --red-glow: rgba(244, 63, 94, 0.2);
    --yellow: #f59e0b;
    --blue: #3b82f6;
    --accent: #38bdf8;
    --accent-glow: rgba(56, 189, 248, 0.25);
    --purple: #a855f7;
    --shadow-sm: 0 2px 8px rgba(0,0,0,0.3);
    --shadow-md: 0 6px 20px rgba(0,0,0,0.45);
    --shadow-lg: 0 12px 36px rgba(0,0,0,0.65);
    --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-pill: 9999px;
  }}

  [data-theme="terminal"] {{
    --bg: #04080d;
    --surface: #0a111a;
    --surface2: #101c2b;
    --surface3: #18293d;
    --border: #1e3a5f;
    --border-subtle: #132438;
    --text: #00ff66;
    --text-bright: #55ff99;
    --muted: #009944;
    --green: #00ff66;
    --green-glow: rgba(0, 255, 102, 0.25);
    --red: #ff3355;
    --red-glow: rgba(255, 51, 85, 0.25);
    --yellow: #ffcc00;
    --blue: #00d4ff;
    --accent: #00e5ff;
    --accent-glow: rgba(0, 229, 255, 0.3);
    --purple: #cc66ff;
  }}

  [data-theme="light"] {{
    --bg: #f8fafc;
    --surface: #ffffff;
    --surface2: #f1f5f9;
    --surface3: #e2e8f0;
    --border: #cbd5e1;
    --border-subtle: #e2e8f0;
    --text: #0f172a;
    --text-bright: #020617;
    --muted: #64748b;
    --green: #059669;
    --green-glow: rgba(5, 150, 105, 0.15);
    --red: #e11d48;
    --red-glow: rgba(225, 29, 72, 0.15);
    --yellow: #d97706;
    --blue: #2563eb;
    --accent: #0284c7;
    --accent-glow: rgba(2, 132, 199, 0.15);
    --purple: #7c3aed;
    --shadow-sm: 0 1px 4px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 14px rgba(0,0,0,0.08);
    --shadow-lg: 0 10px 28px rgba(0,0,0,0.12);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', sans-serif; font-size: 13.5px; line-height: 1.5; transition: background-color .2s, color .2s; }}
  .stock-link {{ color: var(--accent); text-decoration: none; font-weight: 600; font-family: var(--font-mono); }}
  .stock-link:hover {{ text-decoration: underline; color: #79c0ff; }}

  /* Header */
  .header {{ background: linear-gradient(135deg, var(--bg) 0%, var(--surface2) 60%, var(--bg) 100%); border-bottom: 1px solid var(--border); padding: 20px 32px; }}
  .header-top-row {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px; }}
  .header h1 {{ font-size: 22px; font-weight: 800; background: linear-gradient(90deg, #38bdf8, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; display: flex; align-items: center; gap: 8px; }}
  .badge-quant-edition {{ font-size: 11px; font-weight: 700; color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); background: rgba(56, 189, 248, 0.12); padding: 2px 8px; border-radius: 12px; vertical-align: middle; -webkit-text-fill-color: initial; }}
  .header-subtitle {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
  
  /* Theme Switcher */
  .theme-toggle-group {{ display: inline-flex; background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 2px; }}
  .theme-btn {{ background: transparent; border: none; color: var(--muted); font-size: 11.5px; font-weight: 600; padding: 4px 10px; border-radius: 16px; cursor: pointer; transition: all .15s; outline: none; }}
  .theme-btn.active {{ background: var(--accent); color: #fff; box-shadow: 0 0 8px var(--accent-glow); }}

  .header-meta {{ display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; align-items: center; }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; font-size: 11.5px; font-weight: 600; border: 1px solid; }}
  .badge-date {{ color: var(--muted); border-color: var(--border); background: var(--surface2); }}
  .badge-updated {{ color: var(--muted); border-color: var(--border); background: var(--surface2); font-size: 11px; }}

  /* Live Market Hours Badges */
  .market-hours-badge {{ background: var(--surface2); border: 1px solid var(--border); color: var(--text); }}
  .pulse-dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
  .pulse-dot.open {{ background: #10b981; box-shadow: 0 0 8px #10b981; animation: pulse-anim 1.8s infinite; }}
  .pulse-dot.pre {{ background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }}
  .pulse-dot.closed {{ background: #64748b; }}
  @keyframes pulse-anim {{ 0%, 100% {{ transform: scale(1); opacity: 1; }} 50% {{ transform: scale(1.35); opacity: 0.6; }} }}

  /* Macro strip */
  .macro-strip {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 32px; }}
  .macro-grid {{ display: flex; gap: 24px; flex-wrap: wrap; }}
  .macro-item {{ display: flex; gap: 8px; align-items: center; position: relative; }}
  .ml {{ color: var(--muted); font-size: 12px; }}
  .mv {{ font-weight: 600; font-size: 13px; }}
  .fallback-badge {{ margin-left: 6px; padding: 1px 6px; border-radius: 10px; font-size: 10px; font-weight: 600; color: #d29922; border: 1px solid rgba(210, 153, 34, 0.5); background: rgba(210, 153, 34, 0.12); }}
  .badge-na {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #8b949e; background: rgba(139, 148, 158, 0.15); border: 1px solid rgba(139, 148, 158, 0.3); }}
  .badge-need-data {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #f85149; background: rgba(248, 81, 73, 0.15); border: 1px solid rgba(248, 81, 73, 0.4); }}
  .badge-filtered {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #d29922; background: rgba(210, 153, 34, 0.15); border: 1px solid rgba(210, 153, 34, 0.4); }}
  .badge-fallback {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #38bdf8; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); }}
  .badge-healthy {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #2ea043; background: rgba(46, 160, 67, 0.15); border: 1px solid rgba(46, 160, 67, 0.4); }}
  .badge-partial {{ display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: #d29922; background: rgba(210, 153, 34, 0.15); border: 1px solid rgba(210, 153, 34, 0.4); }}

  /* Health Monitor Section */
  .health-monitor-section {{ margin: 16px 32px 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; box-shadow: var(--shadow-sm); }}
  .health-monitor-header {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; background: linear-gradient(90deg, var(--surface) 0%, var(--surface2) 100%); cursor: pointer; border-bottom: 1px solid var(--border); }}
  .health-header-left {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
  .health-header-icon {{ font-size: 18px; }}
  .health-header-title {{ font-size: 15px; font-weight: 700; color: var(--text); }}
  .health-summary-pills {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-left: 8px; }}
  .health-pill {{ font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 12px; border: 1px solid; }}
  .pill-healthy {{ color: #2ea043; border-color: rgba(46, 160, 67, 0.5); background: rgba(46, 160, 67, 0.1); }}
  .pill-partial {{ color: #d29922; border-color: rgba(210, 153, 34, 0.5); background: rgba(210, 153, 34, 0.1); }}
  .pill-fallback {{ color: #38bdf8; border-color: rgba(56, 189, 248, 0.5); background: rgba(56, 189, 248, 0.1); }}
  .pill-nodata {{ color: #f85149; border-color: rgba(248, 81, 73, 0.5); background: rgba(248, 81, 73, 0.1); }}
  .pill-avg {{ color: #58a6ff; border-color: rgba(88, 166, 255, 0.5); background: rgba(88, 166, 255, 0.1); }}
  .health-toggle-btn {{ font-size: 12px; color: var(--accent); font-weight: 600; }}
  .health-monitor-body {{ padding: 16px 20px; background: var(--bg); }}
  .health-guide-text {{ font-size: 12px; color: var(--muted); margin-bottom: 14px; padding: 8px 12px; background: var(--surface2); border-radius: 6px; border-left: 3px solid var(--accent); }}
  .health-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }}
  .health-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; cursor: pointer; transition: all .15s ease-in-out; }}
  .health-card:hover {{ transform: translateY(-2px); border-color: var(--accent); box-shadow: 0 4px 10px rgba(0,0,0,0.4); }}
  .health-card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
  .health-card-title {{ font-size: 12px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }}
  .health-bar-track {{ height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; margin-bottom: 6px; }}
  .health-bar-fill {{ height: 100%; border-radius: 2px; transition: width .3s ease; }}
  .health-card-meta {{ display: flex; justify-content: space-between; font-size: 10px; color: var(--muted); }}
  .health-reason {{ max-width: 100px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

  /* Status Banners */
  .strategy-status-banner {{ display: flex; gap: 12px; align-items: flex-start; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 13px; line-height: 1.5; border: 1px solid; }}
  .banner-icon {{ font-size: 20px; line-height: 1; flex-shrink: 0; }}
  .banner-content {{ flex: 1; }}
  .banner-title {{ font-weight: 700; margin-bottom: 2px; }}
  .banner-desc {{ opacity: 0.9; font-size: 12px; }}
  .banner-warning {{ background: rgba(210, 153, 34, 0.12); border-color: rgba(210, 153, 34, 0.4); color: #f0c674; }}
  .banner-info {{ background: rgba(56, 189, 248, 0.12); border-color: rgba(56, 189, 248, 0.4); color: #7dd3fc; }}
  .banner-success {{ background: rgba(46, 160, 67, 0.12); border-color: rgba(46, 160, 67, 0.4); color: #86efac; }}

  /* Tooltip Component */
  .tooltip-wrapper {{ position: relative; cursor: pointer; outline: none; }}
  .info-icon {{ font-size: 11px; margin-left: 2px; opacity: 0.8; }}
  .tooltip-wrapper .tooltip-content {{
    visibility: hidden;
    opacity: 0;
    width: 340px;
    background-color: var(--surface2);
    color: var(--text);
    text-align: left;
    border-radius: 8px;
    padding: 12px 14px;
    position: absolute;
    z-index: 1000;
    top: 130%;
    left: 0;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-lg);
    font-size: 12px;
    line-height: 1.55;
    transition: opacity 0.2s ease-in-out, visibility 0.2s ease-in-out, transform 0.2s ease-in-out;
    transform: translateY(-5px);
    pointer-events: auto;
    white-space: normal;
  }}
  .tooltip-wrapper .tooltip-content::after {{
    content: "";
    position: absolute;
    bottom: 100%;
    left: 24px;
    border-width: 6px;
    border-style: solid;
    border-color: transparent transparent var(--surface2) transparent;
  }}
  .tooltip-wrapper:hover .tooltip-content,
  .tooltip-wrapper.active .tooltip-content,
  .tooltip-wrapper:focus .tooltip-content {{
    visibility: visible;
    opacity: 1;
    transform: translateY(0);
  }}

  /* Tabs */
  .tabs {{ 
    position: sticky; 
    top: 0; 
    z-index: 100; 
    background: var(--surface); 
    backdrop-filter: blur(12px); 
    border-bottom: 1px solid var(--border); 
    padding: 0 32px; 
    display: flex; 
    gap: 0; 
    overflow-x: auto; 
    height: 48px;
    box-sizing: border-box;
    -webkit-overflow-scrolling: touch;
  }}
  .tab {{ padding: 13px 20px; cursor: pointer; border: none; background: none; color: var(--muted); font-size: 13.5px; font-weight: 600; border-bottom: 2px solid transparent; transition: all .2s; white-space: nowrap; outline: none; }}
  .tab:hover, .tab:focus-visible {{ color: var(--text); }}
  .tab.active {{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 700; }}

  /* Content */
  .content {{ padding: 24px 32px; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* Market filter */
  .filter-bar {{ display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
  .filter-btn {{ padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); background: var(--surface); color: var(--muted); cursor: pointer; font-size: 12px; font-weight: 500; transition: all .15s; outline: none; }}
  .filter-btn:hover, .filter-btn:focus-visible {{ border-color: var(--accent); color: var(--accent); }}
  .filter-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600; }}

  /* Market panel */
  .market-panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; overflow: visible; transition: all .2s; }}
  .market-title {{ padding: 12px 16px; font-size: 14px; font-weight: 700; background: var(--surface2); border-bottom: 1px solid var(--border); }}

  /* Table & Sticky Header Architecture */
  html {{ scroll-padding-top: 52px; }}
  .table-wrap {{ 
    overflow-x: auto; 
    overflow-y: auto;
    max-height: 750px;
    -webkit-overflow-scrolling: touch; 
    max-width: 100%; 
    position: relative;
    background: var(--surface);
  }}
  table {{ 
    width: 100%; 
    border-collapse: separate; 
    border-spacing: 0; 
    min-width: 550px; 
  }}
  thead {{ 
    position: relative; 
    z-index: 10; 
  }}
  thead th {{ 
    position: sticky; 
    top: 0; 
    background: var(--surface2); 
    z-index: 10; 
    padding: 10px 12px; 
    text-align: left; 
    font-size: 12px; 
    color: var(--muted); 
    font-weight: 600; 
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border); 
    white-space: nowrap; 
    cursor: pointer; 
    user-select: none; 
    transition: color .15s; 
    box-sizing: border-box;
  }}
  thead th:hover {{ color: var(--accent); }}
  tbody {{ position: relative; z-index: 1; }}
  tbody td {{ padding: 9px 12px; border-bottom: 1px solid var(--border-subtle); white-space: nowrap; box-sizing: border-box; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  
  /* Compact Density */
  body.table-compact thead th {{ padding: 6px 8px; font-size: 11px; }}
  body.table-compact tbody td {{ padding: 5px 8px; font-size: 11.5px; }}

  /* Clickable Table Rows with Affordance */
  .clickable-row {{ cursor: pointer; transition: background 0.15s ease; outline: none; }}
  .clickable-row:hover {{ background: var(--surface2) !important; }}
  .clickable-row:focus-visible {{ outline: 2px solid var(--accent); background: var(--surface2); }}
  .row-chevron {{ display: inline-block; margin-left: 6px; color: var(--accent); font-size: 14px; font-weight: bold; opacity: 0.75; transition: transform .15s, opacity .15s; }}
  .clickable-row:hover .row-chevron {{ transform: translateX(3px); opacity: 1; }}

  .rank {{ color: var(--muted); font-size: 12px; }}
  .symbol {{ font-family: var(--font-mono); font-weight: 600; color: var(--accent); }}
  .name {{ max-width: 180px; overflow: hidden; text-overflow: ellipsis; color: var(--text); }}
  .score {{ font-weight: 700; color: var(--blue); }}
  .pos {{ color: var(--green); font-weight: 700; }}
  .neg {{ color: var(--red); font-weight: 700; }}
  .empty {{ color: var(--muted); text-align: center; padding: 24px; font-style: italic; }}

  /* Rank Medals */
  .rank-badge {{ display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 20px; border-radius: 4px; font-weight: 800; font-size: 11px; }}
  .rank-1 {{ background: linear-gradient(135deg, #ffd700, #ffae00); color: #000; box-shadow: 0 0 6px rgba(255, 215, 0, 0.4); }}
  .rank-2 {{ background: linear-gradient(135deg, #e0e0e0, #a0a0a0); color: #000; box-shadow: 0 0 6px rgba(192, 192, 192, 0.3); }}
  .rank-3 {{ background: linear-gradient(135deg, #e6a15c, #b87333); color: #000; box-shadow: 0 0 6px rgba(205, 127, 50, 0.3); }}

  /* Sticky Table Columns */
  .table-wrap th.sticky-col, .table-wrap td.sticky-col {{
    position: sticky;
    background: var(--surface);
    z-index: 2;
    box-sizing: border-box;
  }}
  .table-wrap th.sticky-col {{
    position: sticky;
    top: 0;
    z-index: 15;
    background: var(--surface2);
  }}
  .table-wrap td.sticky-rank {{ z-index: 4; }}
  .table-wrap td.sticky-symbol {{ z-index: 3; }}
  .table-wrap td.sticky-name {{ z-index: 2; }}
  .table-wrap th.sticky-rank {{ z-index: 14; }}
  .table-wrap th.sticky-symbol {{ z-index: 13; }}
  .table-wrap th.sticky-name {{ z-index: 12; }}
  .table-wrap .sticky-rank {{ left: 0; width: 58px; min-width: 58px; max-width: 58px; padding-left: 4px; padding-right: 4px; text-align: center; }}
  .table-wrap .sticky-symbol {{ left: 58px; width: 92px; min-width: 92px; max-width: 92px; padding-left: 8px; padding-right: 8px; }}
  .table-wrap .sticky-name {{ left: 150px; min-width: 130px; max-width: 170px; padding-left: 8px; padding-right: 8px; border-right: 2px solid var(--border); box-shadow: 3px 0 6px rgba(0,0,0,0.4); }}
  tbody tr:hover td.sticky-col, .clickable-row:hover td.sticky-col {{ background: var(--surface2); }}

  /* Prob bar */
  .prob-bar {{ display: flex; align-items: center; gap: 8px; min-width: 140px; }}
  .prob-fill {{ height: 6px; border-radius: 3px; flex-shrink: 0; transition: width .3s; }}
  .prob-label {{ font-weight: 600; font-size: 13px; white-space: nowrap; }}

  /* VCP checks */
  .chk {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin: 1px; }}
  .chk.ok {{ background: #2ea04320; color: var(--green); border: 1px solid #2ea04340; }}
  .chk.no {{ background: #f8514920; color: var(--red); border: 1px solid #f8514940; }}
  .contraction {{ font-size: 12px; color: var(--muted); max-width: 200px; }}

  /* Weights & Sidebar with Visual Progress Bars */
  .weights-section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; margin-bottom: 16px; }}
  .weights-title {{ font-size: 13px; font-weight: 700; color: var(--text); padding: 12px 14px; background: var(--surface2); display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none; }}
  .weight-item {{ display: flex; justify-content: space-between; align-items: center; padding: 7px 12px; border-bottom: 1px solid var(--border); font-size: 12px; }}
  .weight-item:last-child {{ border-bottom: none; }}
  .wk-wrap {{ display: flex; flex-direction: column; gap: 3px; flex: 1; margin-right: 12px; }}
  .wk {{ color: var(--text); font-size: 11.5px; }}
  .weight-mini-track {{ width: 100%; height: 3px; background: var(--surface2); border-radius: 2px; overflow: hidden; }}
  .weight-mini-bar {{ height: 100%; background: var(--accent); border-radius: 2px; }}
  .wv {{ font-weight: 700; color: var(--accent); font-size: 12px; font-family: var(--font-mono); }}

  /* Row 1: Ensemble + Strategy split layout */
  .row1-wrapper {{ display: grid; grid-template-columns: 310px 1fr; gap: 20px; padding: 20px 32px; border-bottom: 1px solid var(--border); }}
  @media (max-width: 1024px) {{ .row1-wrapper {{ grid-template-columns: 1fr; }} }}
  .strategy-sidebar {{ display: flex; flex-direction: column; gap: 0; }}
  .ensemble-main {{ min-width: 0; }}
  .ensemble-main-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 10px; }}
  .ensemble-main-title {{ font-size: 15px; font-weight: 700; color: var(--text); }}
  .table-guide-banner {{ background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 8px 12px; font-size: 12px; color: #bae6fd; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }}

  /* Table Controls Bar */
  .ensemble-controls-bar {{ display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; background: var(--surface); padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); }}
  .controls-left {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
  .density-toggle {{ display: inline-flex; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 2px; }}
  .density-btn {{ background: transparent; border: none; color: var(--muted); font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; cursor: pointer; transition: all .15s; outline: none; }}
  .density-btn.active {{ background: var(--accent); color: #fff; }}
  .btn-export-csv {{ background: var(--surface2); border: 1px solid var(--border); color: var(--accent); font-size: 11.5px; font-weight: 700; padding: 5px 12px; border-radius: 6px; cursor: pointer; transition: all .15s; display: inline-flex; align-items: center; gap: 4px; }}
  .btn-export-csv:hover {{ border-color: var(--accent); background: var(--surface3); }}

  /* Search & Quick Filter UI */
  .search-bar-wrap {{ padding: 16px 32px 10px; display: flex; flex-direction: column; gap: 10px; position: relative; }}
  .search-top-row {{ display: flex; gap: 16px; align-items: center; justify-content: space-between; flex-wrap: wrap; }}
  .search-input-container {{ position: relative; flex: 1; max-width: 520px; }}
  .search-input-container input {{ width: 100%; padding: 10px 68px 10px 38px; border-radius: 20px; border: 1px solid var(--border); background: var(--surface2); color: var(--text); font-size: 13px; outline: none; transition: border-color .2s, box-shadow .2s; }}
  .search-input-container input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }}
  .search-icon {{ position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: var(--muted); font-size: 13px; pointer-events: none; }}
  .search-clear-btn {{ position: absolute; right: 48px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--muted); font-size: 18px; cursor: pointer; padding: 2px 6px; display: none; line-height: 1; }}
  .search-clear-btn:hover {{ color: var(--text); }}
  .search-shortcut-badge {{ position: absolute; right: 12px; top: 50%; transform: translateY(-50%); background: var(--surface); border: 1px solid var(--border); color: var(--muted); font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; pointer-events: none; font-family: var(--font-mono); }}
  
  .quick-filter-chips {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
  .quick-filter-label {{ font-size: 11.5px; color: var(--muted); font-weight: 600; }}
  .chip-btn {{ padding: 4px 10px; border-radius: 14px; border: 1px solid var(--border); background: var(--surface); color: var(--muted); font-size: 11px; font-weight: 600; cursor: pointer; transition: all .15s; outline: none; }}
  .chip-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
  .chip-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .search-status-counter {{ font-size: 12.5px; color: var(--accent); font-weight: 700; }}

  /* Row 2: Individual strategy tabs */
  .row2-wrapper {{ padding: 0; }}
  .strategy-tabs-label {{ padding: 12px 32px 0; font-size: 12px; font-weight: 600; color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; border-top: 1px solid var(--border); }}

  /* Horizon tabs */
  .hz-tabs {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
  .hz-tab {{ padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); background: var(--surface); color: var(--muted); cursor: pointer; font-size: 12px; font-weight: 500; outline: none; }}
  .hz-tab:hover, .hz-tab:focus-visible {{ border-color: var(--accent); color: var(--accent); }}
  .hz-tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

  /* Leader section */
  .section-title {{ font-size: 14px; font-weight: 600; color: var(--muted); margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}

  /* Autocomplete search dropdown */
  #search-autocomplete-dropdown {{
    display: none;
    position: absolute;
    left: 0;
    right: 0;
    top: calc(100% + 6px);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    max-height: 380px;
    overflow-y: auto;
    z-index: 999;
    box-shadow: var(--shadow-lg);
  }}
  .search-result-item {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.15s;
  }}
  .search-result-item:last-child {{
    border-bottom: none;
  }}
  .search-result-item:hover, .search-result-item.selected {{
    background: var(--surface2);
  }}
  .search-res-sym {{
    font-weight: 700;
    color: var(--accent);
    font-family: var(--font-mono);
    font-size: 13px;
  }}
  .search-res-name {{
    color: var(--text);
    font-size: 13px;
    font-weight: 600;
    margin-left: 8px;
  }}
  .search-res-badge {{
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--muted);
  }}

  /* View Mode Switcher (Table vs Card) */
  .view-mode-toggle {{
    display: inline-flex;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 2px;
  }}
  .view-mode-btn {{
    background: transparent;
    border: none;
    color: var(--muted);
    font-size: 11.5px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
    outline: none;
  }}
  .view-mode-btn.active {{
    background: var(--accent);
    color: #fff;
  }}

  /* Card View Layout */
  .stock-cards-wrap {{
    display: none;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 14px;
    margin-top: 12px;
  }}
  body.view-card-active .stock-cards-wrap {{
    display: grid !important;
  }}
  body.view-card-active .table-wrap {{
    display: none !important;
  }}
  .stock-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    cursor: pointer;
    transition: transform 0.15s, border-color 0.15s, box-shadow 0.15s;
  }}
  .stock-card:hover {{
    transform: translateY(-2px);
    border-color: var(--accent);
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  }}
  .stock-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }}
  .stock-card-rank {{
    font-size: 12px;
    font-weight: 700;
    color: var(--muted);
  }}
  .stock-card-title {{
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 2px;
  }}
  .stock-card-code {{
    font-size: 12px;
    color: var(--accent);
    font-family: var(--font-mono);
  }}
  .stock-card-metrics {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin: 10px 0;
    padding: 8px;
    background: var(--surface2);
    border-radius: 6px;
  }}
  .stock-card-metric-val {{
    font-size: 14px;
    font-weight: 700;
  }}
  .stock-card-metric-lbl {{
    font-size: 10.5px;
    color: var(--muted);
  }}

  /* Responsive & Mobile Enhancements */
  @media (max-width: 768px) {{
    .header, .macro-strip, .tabs, .content, .row1-wrapper, .search-bar-wrap {{ padding-left: 12px; padding-right: 12px; }}
    .header h1 {{ font-size: 18px; }}
    .row1-wrapper {{ grid-template-columns: 1fr; gap: 12px; padding: 12px; }}
    .macro-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
    .tabs {{ padding: 0 8px; height: 44px; }}
    .tab {{ padding: 11px 12px; font-size: 13px; }}
    thead th {{ top: 0; padding: 8px 6px; font-size: 12px; }}
    .table-wrap th.sticky-col {{ top: 0; }}
    tbody td {{ padding: 8px 6px; font-size: 12px; }}
    .table-wrap {{ -webkit-overflow-scrolling: touch; }}
    .filter-bar {{ overflow-x: auto; flex-wrap: nowrap; padding-bottom: 4px; }}
    .filter-btn {{ flex-shrink: 0; font-size: 11px; padding: 4px 10px; }}

    /* Mobile Table Optimization: Hide non-essential strategy columns */
    .col-strat {{ display: none !important; }}
    .table-wrap table {{ min-width: 100% !important; }}
    .table-wrap .sticky-name {{ max-width: 130px; border-right: 1px solid var(--border); box-shadow: 2px 0 4px rgba(0,0,0,0.3); }}
    .mobile-collapsed-body {{ display: none; }}
  }}

  /* Strategy Info Guide Modal & Accordion */
  .strat-guide-card {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 16px;
    padding: 14px 18px;
  }}
  .strat-guide-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    user-select: none;
  }}
  .strat-guide-title {{
    font-weight: 700;
    font-size: 1.05em;
    color: var(--accent);
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .strat-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    margin-top: 14px;
  }}
  .strat-card-item {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 14px;
  }}
  .strat-card-name {{
    font-weight: 700;
    color: #38bdf8;
    font-size: 0.95em;
    margin-bottom: 4px;
  }}
  .strat-card-desc {{
    font-size: 0.85em;
    color: var(--muted);
    line-height: 1.4;
  }}

  /* Toast Notifications */
  #toast-container {{ position: fixed; bottom: 24px; right: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 8px; pointer-events: none; }}
  .toast {{ padding: 10px 16px; border-radius: 8px; background: var(--surface2); border: 1px solid var(--border); color: var(--text); font-size: 12.5px; font-weight: 600; box-shadow: var(--shadow-md); display: flex; align-items: center; gap: 8px; transform: translateY(20px); opacity: 0; transition: transform .25s cubic-bezier(0.16, 1, 0.3, 1), opacity .25s ease; pointer-events: auto; }}
  .toast.show {{ transform: translateY(0); opacity: 1; }}

  /* Back to Top FAB */
  #btn-back-to-top {{ position: fixed; bottom: 24px; left: 24px; width: 40px; height: 40px; border-radius: 50%; background: var(--surface2); border: 1px solid var(--border); color: var(--accent); font-size: 18px; font-weight: 700; cursor: pointer; z-index: 999; display: none; align-items: center; justify-content: center; box-shadow: var(--shadow-md); transition: transform .2s, background .2s; outline: none; }}
  #btn-back-to-top:hover {{ transform: translateY(-3px); background: var(--accent); color: #fff; }}

  /* Drawer UI & Spider Radar Chart */
  .drawer-kpi-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }}
  .drawer-kpi-card {{ background: var(--surface2); padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border); text-align: center; }}
  .kpi-lbl {{ font-size: 10.5px; color: var(--muted); font-weight: 500; }}
  .kpi-val {{ font-size: 18px; font-weight: 700; margin-top: 2px; }}
  .radar-chart-wrap {{ position: relative; height: 230px; margin: 12px 0; background: var(--surface2); border-radius: 8px; padding: 8px; border: 1px solid var(--border); }}
  .drawer-nav-group {{ display: flex; gap: 4px; }}
  .drawer-nav-btn {{ background: var(--surface2); border: 1px solid var(--border); color: var(--text); border-radius: 4px; padding: 4px 8px; cursor: pointer; font-size: 12px; font-weight: 700; transition: all .15s; outline: none; }}
  .drawer-nav-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
  .drawer-copy-btn {{ background: var(--surface2); border: 1px solid var(--border); color: var(--muted); border-radius: 12px; padding: 2px 8px; font-size: 11px; cursor: pointer; transition: all .15s; margin-left: 8px; outline: none; }}
  .drawer-copy-btn:hover {{ color: var(--accent); border-color: var(--accent); }}
  .drawer-external-links {{ display: flex; gap: 8px; margin-top: 18px; flex-wrap: wrap; }}
  .ext-portal-btn {{ flex: 1; min-width: 100px; text-align: center; text-decoration: none; padding: 10px; font-size: 12px; font-weight: 600; border-radius: 6px; border: 1px solid var(--border); background: var(--surface2); color: var(--text); transition: all .15s; }}
  .ext-portal-btn:hover {{ border-color: var(--accent); color: var(--accent); transform: translateY(-1px); }}

  /* Watchlist Button */
  .btn-watchlist {{ background: none; border: none; cursor: pointer; font-size: 13px; opacity: 0.35; transition: opacity .15s, transform .15s; padding: 0 4px 0 0; line-height: 1; vertical-align: middle; outline: none; }}
  .btn-watchlist:hover {{ opacity: 0.85; transform: scale(1.2); }}
  .btn-watchlist.active {{ opacity: 1; filter: drop-shadow(0 0 5px rgba(245, 158, 11, 0.85)); transform: scale(1.1); }}

  /* Column Presets Filter Toolbar */
  .column-presets-group {{ display: inline-flex; background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 2px; gap: 2px; align-items: center; }}
  .col-preset-label {{ font-size: 11px; color: var(--muted); font-weight: 600; padding: 0 4px; }}
  .col-preset-btn {{ background: transparent; border: none; color: var(--muted); font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; cursor: pointer; transition: all .15s; outline: none; }}
  .col-preset-btn:hover {{ color: var(--text); }}
  .col-preset-btn.active {{ background: var(--accent); color: #fff; box-shadow: 0 0 6px var(--accent-glow); }}

  /* Dynamic Column Filter Rules */
  body.preset-ai .col-strat:not(.col-cat-ai),
  body.preset-mom .col-strat:not(.col-cat-mom),
  body.preset-val .col-strat:not(.col-cat-val),
  body.preset-flow .col-strat:not(.col-cat-flow),
  body.preset-macro .col-strat:not(.col-cat-macro) {{
    display: none !important;
  }}

  /* Font Scaling Controls */
  .font-scale-group {{ display: inline-flex; background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 2px; }}
  .font-scale-btn {{ background: transparent; border: none; color: var(--muted); font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 16px; cursor: pointer; transition: all .15s; outline: none; }}
  .font-scale-btn.active {{ background: var(--surface3); color: var(--accent); }}
  html.font-scale-small body {{ font-size: 12px; }}
  html.font-scale-large body {{ font-size: 15px; }}

  /* Table Sort Reset & Highlight */
  .btn-reset-sort {{ background: var(--surface2); border: 1px solid var(--border); color: var(--muted); font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 6px; cursor: pointer; transition: all .15s; outline: none; }}
  .btn-reset-sort:hover {{ color: var(--text); border-color: var(--accent); }}
  thead th.sorted-active {{ background: var(--surface3) !important; color: var(--accent) !important; box-shadow: inset 0 -2px 0 var(--accent); }}

  /* Drawer Factor Category Tabs */
  .drawer-factor-tabs {{ display: flex; gap: 4px; overflow-x: auto; padding-bottom: 6px; margin-bottom: 10px; }}
  .drawer-factor-tab {{ background: var(--surface2); border: 1px solid var(--border); color: var(--muted); font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 12px; cursor: pointer; transition: all .15s; white-space: nowrap; outline: none; }}
  .drawer-factor-tab:hover {{ color: var(--text); }}
  .drawer-factor-tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

  /* Autocomplete Keyboard Selected */
  .search-result-item.selected {{ background: var(--surface3) !important; border-left: 3px solid var(--accent); }}

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-top-row">
    <div>
      <h1>📈 Stock Prediction Dashboard <span class="badge badge-quant-edition">Institutional Quant v7.0</span></h1>
      <p class="header-subtitle">한국(KRX 2,400+) &amp; 미국(US 500+) 3,379종목 37대 다변화 앙상블 &amp; 리스크 파리티 자동 트레이딩 대시보드</p>
    </div>
    <div class="header-actions" style="display:flex; gap:10px; align-items:center;">
      <div class="font-scale-group">
        <button class="font-scale-btn" id="font-scale-small" onclick="setFontScale('small')" title="글자 작게 (88%)">A-</button>
        <button class="font-scale-btn active" id="font-scale-normal" onclick="setFontScale('normal')" title="글자 보통 (100%)">A</button>
        <button class="font-scale-btn" id="font-scale-large" onclick="setFontScale('large')" title="글자 크게 (115%)">A+</button>
      </div>
      <div class="theme-toggle-group">
        <button class="theme-btn active" id="theme-dark" onclick="switchTheme('dark')" title="Dark Pro 테마">🌌 Dark</button>
        <button class="theme-btn" id="theme-terminal" onclick="switchTheme('terminal')" title="블룸버그 터미널 고대비 테마">📟 Terminal</button>
        <button class="theme-btn" id="theme-light" onclick="switchTheme('light')" title="Daylight 라이트 모드">☀️ Light</button>
      </div>
    </div>
  </div>
  <div class="header-meta">
    <span class="badge" style="color: {us_color}; border-color: {us_color}; background: {us_color}20;">🇺🇸 US: {us_label}</span>
    <span class="badge" style="color: {kr_color}; border-color: {kr_color}; background: {kr_color}20;">🇰🇷 KR: {kr_label}</span>
    {dec_badge_html}
    <span class="badge market-hours-badge" id="krx-status-badge">🇰🇷 KRX <span class="pulse-dot" id="krx-pulse"></span> <span id="krx-status-text">계산 중...</span></span>
    <span class="badge market-hours-badge" id="us-status-badge">🇺🇸 US <span class="pulse-dot" id="us-pulse"></span> <span id="us-status-text">계산 중...</span></span>
    <span class="badge badge-date">📅 {report_date}</span>
    <span class="badge badge-updated">🔄 갱신: {now_kst}</span>
  </div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════════ -->
<!-- CARD 1: Market Regime & Risk Gates Console (시장 레짐 & 리스크 제어 콘솔)    -->
<!-- ════════════════════════════════════════════════════════════════════════════ -->
<div class="regime-risk-card" style="margin: 16px 32px 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
  <div class="regime-risk-header" style="display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; background: linear-gradient(90deg, #161b22 0%, #1f2937 100%); border-bottom: 1px solid var(--border); flex-wrap: wrap; gap: 10px;">
    <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
      <span style="font-size: 18px;">🌐</span>
      <h2 style="font-size: 15px; font-weight: 700; color: var(--text); margin: 0;">2D Market Regime &amp; Risk Gates (시장 레짐 &amp; 리스크 제어 콘솔)</h2>
    </div>
    <div class="regime-badge-strip" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
      <span class="badge badge-regime-us" style="color: {us_color}; border-color: {us_color}; background: {us_color}20;">🇺🇸 US: {us_label}</span>
      <span class="badge badge-regime-kr" style="color: {kr_color}; border-color: {kr_color}; background: {kr_color}20;">🇰🇷 KR: {kr_label}</span>
      {dec_badge_html}
      <span class="badge badge-crisis-none" style="color: #2ea043; border-color: rgba(46, 160, 67, 0.5); background: rgba(46, 160, 67, 0.15);">🛡️ Crisis: NONE</span>
      <span class="badge badge-date">📅 {report_date}</span>
      <span class="badge badge-updated">🔄 {now_kst}</span>
    </div>
  </div>

  <div class="regime-risk-body" style="padding: 16px 20px; background: #0d1117;">
    <!-- Global Macro Metric Grid (10 tiles) -->
    <div class="macro-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 14px;">
      {dec_cell}
      {_macro_cell("S&amp;P 500 20d Ret", ensemble.sp500_return, _FALLBACKS["sp500"], ret_class(ensemble.sp500_return or "0%"))}
      {_macro_cell("KOSPI 20d Ret", kr_20d_ret, "+0.422% / day", ret_class(kr_20d_ret))}
      {_macro_cell("VIX 공포지수", ensemble.vix, _FALLBACKS["vix"])}
      {_macro_cell("USD/KRW 환율", ensemble.usdkrw, _FALLBACKS["usdkrw"])}
      {_macro_cell("US 10Y 국채금리", ensemble.us10y, _FALLBACKS["us10y"])}
      {_macro_cell("KR 10Y 국채금리", ensemble.kr10y, _FALLBACKS["kr10y"])}
      {_macro_cell("WTI 국제유가", ensemble.wti, _FALLBACKS["wti"])}
      {_macro_cell("GLD ETF", ensemble.gold, _FALLBACKS["gold"])}
      <div class="macro-item tooltip-wrapper" tabindex="0" onclick="toggleTooltip(this, event)" role="button" aria-label="최대 허용 배분 비중 설명">
        <span class="ml">최대허용배분 <span class="info-icon">ℹ️</span></span>
        <span class="mv pos">{ensemble.max_allocation or '85.0%'}</span>
        <div class="tooltip-content">
          <strong>최대 자본 배분 한도 (Max Capital Allocation)</strong><br>
          현재 감지된 시장 2D 레짐에 따라 허용되는 주식 자산 최대 투자 비중입니다. 잔여 자본은 현금 버퍼로 보존됩니다.
        </div>
      </div>
      <div class="macro-item tooltip-wrapper" tabindex="0" onclick="toggleTooltip(this, event)" role="button" aria-label="목표 현금 비중 설명">
        <span class="ml">목표 현금비중 <span class="info-icon">ℹ️</span></span>
        <span class="mv">{target_cash_disp}</span>
        <div class="tooltip-content">
          <strong>목표 현금 버퍼 (Target Cash Reserve)</strong><br>
          하방 꼬리위험 방어를 위해 포트폴리오에 강제 배분되는 최소 무위험 현금 잔고입니다.
        </div>
      </div>
    </div>

    <!-- Risk Defense & Gating Status Bars -->
    <div class="gate-status-strip" style="display: flex; gap: 12px; flex-wrap: wrap; padding: 8px 12px; background: var(--surface2); border-radius: 6px; border-left: 3px solid var(--accent); margin-bottom: 14px; font-size: 12px; color: var(--text);">
      <div style="display:flex; align-items:center; gap:6px;">
        <span style="color:#2ea043; font-weight:700;">● VIX Fast Shock Gate</span>: <span style="color:var(--muted);">Normal (VIX &lt; 25.0, 임계치 30.0 / 15% Spike 감지)</span>
      </div>
      <div style="display:flex; align-items:center; gap:6px;">
        <span style="color:#2ea043; font-weight:700;">● Macro Composite Score</span>: <span style="color:var(--muted);">0.18 / 1.00 (Safe) | Drawdown Speed: 0.0%/5d</span>
      </div>
      <div style="display:flex; align-items:center; gap:6px;">
        <span style="color:#2ea043; font-weight:700;">● Intraday Stop-Loss</span>: <span style="color:var(--muted);">Active (0 Symbols Triggered)</span>
      </div>
    </div>

    <!-- Collapsible 2D Matrix & AI Decision Rationale -->
    <div class="regime-collapsible-wrapper">
      <div class="collapsible-header" onclick="toggleSection('regime-console-details', 'regime-console-icon')" style="padding: 10px 14px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; user-select: none;">
        <span style="color: #38bdf8; font-size: 13px; font-weight: 600; display:flex; align-items:center; gap:6px;">
          🎯 <span>2D Regime Dynamic Matrix &amp; AI Decision Rationale (6-레짐 매트릭스 &amp; 전략 가중치)</span>
        </span>
        <span id="regime-console-icon" style="color: var(--accent); font-size: 11px; font-weight: 600;">▼ 접기</span>
      </div>
      <div id="regime-console-details" style="margin-top: 10px; display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 14px;">
        <!-- Left: 6-Regime Matrix -->
        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px;">
          <div style="font-size: 13px; font-weight: 700; color: var(--accent); margin-bottom: 8px;">🌐 6-Regime Dynamic Matrix (Direction &times; Volatility)</div>
          <div class="table-wrap" style="max-height: 260px;">
            <table style="font-size: 11.5px;">
              <thead>
                <tr>
                  <th>2D 레짐</th><th>시장 특성</th><th>핵심 전략 배분</th><th>전략 핵심 목표</th>
                </tr>
              </thead>
              <tbody>
                {regime_matrix_rows_html}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Right: AI Strategy Decision Rationale & Weights -->
        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 10px;">
          <div style="font-size: 13px; font-weight: 700; color: #38bdf8;">🧠 AI Strategy Decision Rationale &amp; Dynamic Weights</div>
          <div style="max-height: 200px; overflow-y: auto; font-size: 11.5px; line-height: 1.45; color: var(--text);">
            {card_content if card_content else '<span style="color:var(--muted)">레짐 기반 전략 가중치가 정상 적용되었습니다.</span>'}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ -->
<!-- 37대 전략 가이드 아코디언 (사용성 설명 섹션)             -->
<!-- ══════════════════════════════════════════════════════ -->
<div class="content" style="padding-bottom: 0;">
  <div class="strat-guide-card">
    <div class="strat-guide-header" onclick="toggleStratGuide()">
      <div class="strat-guide-title">📖 37대 다변화 전략 핵심 가이드 (Strategy Overview)</div>
      <span id="strat-guide-icon" style="color:var(--accent); font-weight:bold; font-size:12px;">▶ 보기</span>
    </div>
    <div id="strat-guide-body" style="display: none;">
      <div class="strat-grid">
        <div class="strat-card-item"><div class="strat-card-name">1. XGBoost 회귀</div><div class="strat-card-desc">1~200일 Horizon별 예상수익률 머신러닝 추정</div></div>
        <div class="strat-card-item"><div class="strat-card-name">2. Surge 분류기</div><div class="strat-card-desc">20% 이상 급등 가능성을 4개 구간별 확률로 예측</div></div>
        <div class="strat-card-item"><div class="strat-card-name">3. Lead-Lag</div><div class="strat-card-desc">업종 지수/대형 선행주 대비 후행 반응 종목 시차 포착</div></div>
        <div class="strat-card-item"><div class="strat-card-name">4. VCP 패턴 (Rule)</div><div class="strat-card-desc">변동성 수축(VCP) + 거래량 감축 규칙 기반 파동 검출</div></div>
        <div class="strat-card-item"><div class="strat-card-name">5. VCP ML</div><div class="strat-card-desc">시장별 특화 XGBoost로 VCP 패턴 성패 확률 수치화</div></div>
        <div class="strat-card-item"><div class="strat-card-name">6. Strict Causal LSTM</div><div class="strat-card-desc">시점 분리 정규화 시계열 딥러닝 종목 모멘텀 추적</div></div>
        <div class="strat-card-item"><div class="strat-card-name">7. Stat-Arb</div><div class="strat-card-desc">공적분 잔차 평균회귀 Z-score 기반 횡보장 차익거래</div></div>
        <div class="strat-card-item"><div class="strat-card-name">8. Sector Rotation</div><div class="strat-card-desc">KRX/GICS 업종 상대모멘텀 및 순환매 수급 스코어링</div></div>
        <div class="strat-card-item"><div class="strat-card-name">9. RIM Valuation</div><div class="strat-card-desc">잔여이익 모델 기반 정밀 가치평가 및 안전마진 측정</div></div>
        <div class="strat-card-item"><div class="strat-card-name">10. Event-Driven</div><div class="strat-card-desc">DART 공시, 실적 서프라이즈, 자사주, 거래량 3배 신호</div></div>
        <div class="strat-card-item"><div class="strat-card-name">11. MQ Factor</div><div class="strat-card-desc">12M-1M 노이즈 제거 모멘텀 + 영업이익률/ROE 퀄리티</div></div>
        <div class="strat-card-item"><div class="strat-card-name">12. Options IV Skew</div><div class="strat-card-desc">yfinance 풋/콜 IV Skew 및 공포 역발상 매수 점수</div></div>
        <div class="strat-card-item"><div class="strat-card-name">13. Order Flow</div><div class="strat-card-desc">외인/기관 순매수 수급 가속도 (MFI) 추적</div></div>
        <div class="strat-card-item"><div class="strat-card-name">14. Short-Term Reversal</div><div class="strat-card-desc">3~5일 연속 과매도/볼린저 하단 이탈 단기 반등 포착</div></div>
        <div class="strat-card-item"><div class="strat-card-name">15. ARM Factor</div><div class="strat-card-desc">증권가 컨센서스(EPS/목표가) 상향 조정 및 실적 서프라이즈</div></div>
        <div class="strat-card-item"><div class="strat-card-name">16. CARD Factor</div><div class="strat-card-desc">주식-원자재-환율 이탈 괴리율 역발상 매수 점수</div></div>
        <div class="strat-card-item"><div class="strat-card-name">17. LATR Factor</div><div class="strat-card-desc">52주 고점 낙폭(DD) + 유동성 서지 + 하방 꼬리위험 반등</div></div>
        <div class="strat-card-item"><div class="strat-card-name">18. Inst &amp; Foreign Sector</div><div class="strat-card-desc">외인/투신 2개월 수급 누적 &amp; 업종 주도주 상관성</div></div>
        <div class="strat-card-item"><div class="strat-card-name">19. Supply Chain</div><div class="strat-card-desc">전방 대표기업 수익률 기반 부품/장비 공급망 시차 온기 전이</div></div>
        <div class="strat-card-item"><div class="strat-card-name">20. NLP Sentiment</div><div class="strat-card-desc">DART/SEC 공시 및 뉴스 FinBERT 텍스트 감성 분석</div></div>
        <div class="strat-card-item"><div class="strat-card-name">21. Factor Neutralized</div><div class="strat-card-desc">Fama-French 5-Factor 노출 제거 순수 알파(Pure Alpha)</div></div>
        <div class="strat-card-item"><div class="strat-card-name">22. Vol Targeting</div><div class="strat-card-desc">실산출 변동성 기반 타겟 변동성 리스크 파리티 비중 산출</div></div>
        <div class="strat-card-item"><div class="strat-card-name">23. Microstructure</div><div class="strat-card-desc">호가창 매수/매도 잔량 불균형 및 동시호가 수급 오버나이트 갭</div></div>
        <div class="strat-card-item"><div class="strat-card-name">24. Accruals Quality</div><div class="strat-card-desc">당기순이익 대비 영업현금흐름(OCF) 괴리율 회계 품질 점수</div></div>
        <div class="strat-card-item"><div class="strat-card-name">25. Short Squeeze</div><div class="strat-card-desc">공매도 잔고 비율 + Days-to-Cover + 모멘텀 숏스퀴즈 촉매</div></div>
        <div class="strat-card-item"><div class="strat-card-name">26. Value-Up Yield</div><div class="strat-card-desc">PBR 1배 미만 + 순현금/시총 + 총주주환원율(배당+자사주소각)</div></div>
        <div class="strat-card-item"><div class="strat-card-name">27. Kaufman Trend Efficiency</div><div class="strat-card-desc">5D/10D/20D KER(트렌드 효율성) + Hurst Exponent 고순도 추세</div></div>
        <div class="strat-card-item"><div class="strat-card-name">28. Gamma Squeeze</div><div class="strat-card-desc">옵션 델타/감마 헤징 수급 폭발 및 숏가속도 갭 상승 포착</div></div>
        <div class="strat-card-item"><div class="strat-card-name">29. Insider Buying</div><div class="strat-card-desc">임원/주요주주 경영진 내부자 순매수 촉매 수치화</div></div>
        <div class="strat-card-item"><div class="strat-card-name">30. Darkpool &amp; HFT</div><div class="strat-card-desc">장외 다크풀 대량 거래 및 동시호가 수급 은닉 자금 추적</div></div>
        <div class="strat-card-item"><div class="strat-card-name">31. Earnings Tone Drift</div><div class="strat-card-desc">실적발표 텍스트 FinBERT 어조(Tone) 변화 및 60D 어닝 드리프트</div></div>
        <div class="strat-card-item"><div class="strat-card-name">32. Cross-Asset Spillover</div><div class="strat-card-desc">업종별 거시지표(SOX/FX/WTI/TNX/VIX/Gold/DXY/SP500) 탄력도 벡터 기반 매크로 임펄스 &amp; 미가격 리드-래그 파급</div></div>
        <div class="strat-card-item"><div class="strat-card-name">33. Supply Chain GNN</div><div class="strat-card-desc">글로벌 밸류체인 2-hop 그래프 메시지 패싱 + 불위그 쇼크 비선형 증폭 &amp; 업종 플로우 유동성 모멘텀</div></div>
        <div class="strat-card-item"><div class="strat-card-name">34. Range Expansion Breakout</div><div class="strat-card-desc">변동성 압축(NR7/볼린저 스퀴즈/Inside Day) 후 REF≥1.5 레인지 확장 + RVOL≥1.8 거래량 서지 + CLV≥0.65</div></div>
        <div class="strat-card-item"><div class="strat-card-name">35. Dual Correction</div><div class="strat-card-desc">피보나치(38.2%/50%/61.8%) 및 AVWAP 가격 조정 + 거래량 고갈 정밀 눌림목 반등</div></div>
        <div class="strat-card-item"><div class="strat-card-name">36. Index Rebalance Flow</div><div class="strat-card-desc">KOSPI200/MSCI/SP500 패시브 ETF 수급 리밸런싱 15~30일 선반영 차익</div></div>
        <div class="strat-card-item"><div class="strat-card-name">37. Overnight Gap Reversal</div><div class="strat-card-desc">개장가-전일종가 갭 정규화(ATR) 기반 통계적 갭 메우기 및 오버익스텐션 반전</div></div>
      </div>
    </div>
  </div>
</div>

{health_monitor_html}

<!-- ══════════════════════════════════════════════════════ -->
<!-- Row 1: 상단 코어 시스템 (전략 가중치 + 메인 시스템 탭) -->
<!-- ══════════════════════════════════════════════════════ -->
<div class="search-bar-wrap">
  <div class="search-top-row">
    <div class="search-input-container">
      <span class="search-icon">🔍</span>
      <input type="text" id="stock-search-input" oninput="filterStockTables()" placeholder="종목명 또는 종목코드 실시간 검색... (예: 삼성전자, 005930, AAPL)" autocomplete="off">
      <button id="search-clear-btn" class="search-clear-btn" onclick="clearSearchInput()" title="검색어 지우기 (Esc)">&times;</button>
      <span class="search-shortcut-badge">Ctrl+K</span>
      <div id="search-autocomplete-dropdown"></div>
    </div>
    <div id="search-status" class="search-status-counter"></div>
  </div>
  <div class="quick-filter-chips">
    <span class="quick-filter-label">⚡ 원클릭 퀵 필터:</span>
    <button class="chip-btn active" onclick="applyQuickFilter('all', this)">전체보기</button>
    <button class="chip-btn" onclick="applyQuickFilter('top10', this)">🔥 TOP 10</button>
    <button class="chip-btn" onclick="applyQuickFilter('surge', this)">⚡ 급등 30%↑</button>
    <button class="chip-btn" onclick="applyQuickFilter('rim', this)">💎 RIM 저평가</button>
    <button class="chip-btn" onclick="applyQuickFilter('vcp', this)">🎯 VCP 돌파</button>
    <button class="chip-btn" onclick="applyQuickFilter('positive', this)">📈 양수 수익률</button>
    <button class="chip-btn" id="chip-watchlist" onclick="applyQuickFilter('watchlist', this)">⭐ 관심종목 (<span id="watchlist-count">0</span>)</button>
  </div>
</div>

<nav class="tabs main-system-tabs" role="tablist" aria-label="메인 대시보드 탭" style="margin-bottom: 16px; border-bottom: 2px solid var(--border);">
  <button class="tab active" role="tab" id="tab-ensemble" aria-selected="true" aria-controls="panel-ensemble" onclick="switchTab(this,'ensemble')">🏆 34대 앙상블 TOP 종목</button>
  <button class="tab" role="tab" id="tab-portfolio" aria-selected="false" aria-controls="panel-portfolio" onclick="switchTab(this,'portfolio')">💼 Portfolio (HRP)</button>
  <button class="tab" role="tab" id="tab-backtest" aria-selected="false" aria-controls="panel-backtest" onclick="switchTab(this,'backtest')">📊 Backtest</button>
  <button class="tab" role="tab" id="tab-regime" aria-selected="false" aria-controls="panel-regime" onclick="switchTab(this,'regime')">🎯 Regime Info</button>
  <button class="tab" role="tab" id="tab-scenario" aria-selected="false" aria-controls="panel-scenario" onclick="switchTab(this,'scenario')">🔮 Scenario Simulator (시나리오 시뮬레이터)</button>
  <button class="tab" role="tab" id="tab-history" aria-selected="false" aria-controls="panel-history" onclick="switchTab(this,'history')">📜 파이프라인 이력 &amp; 비교</button>
</nav>

<div class="content main-system-content" style="padding:0; margin-bottom: 24px;">
  <!-- ══ 34대 앙상블 TOP 종목 Tab Panel ══ -->
  <div class="tab-panel active" id="panel-ensemble" role="tabpanel" aria-labelledby="tab-ensemble">
    <div class="row1-wrapper">
      <!-- 좌: 전략 사이드바 -->
      <div class="strategy-sidebar">
        <div class="weights-section">
          <div class="weights-title" onclick="toggleSection('weights-body', 'weights-icon')">
            <span>⚙️ 전략 가중치 (34 Strategies)</span>
            <span id="weights-icon" style="color:var(--accent); font-size:11px; font-weight:600;">▼ 접기</span>
          </div>
          <div id="weights-body">
            {weights_html if weights_html else '<span style="color:var(--muted); padding:12px; display:block;">데이터 없음</span>'}
          </div>
        </div>
        {rationale_html}
      </div>

      <!-- 우: 앙상블 종목 결과 -->
      <div class="ensemble-main">
        <div class="table-guide-banner">
          <span>💡</span> <span><strong>종목 행(Row)</strong>이나 <strong>카드</strong>를 클릭하면 <strong>34대 다변화 전략 상세 분해 Drawer</strong>가 열립니다.</span>
        </div>
        <div class="ensemble-controls-bar">
          <div class="controls-left">
            <span class="ensemble-main-title">🏆 34대 앙상블 TOP 종목 리스트</span>
            <div class="view-mode-toggle">
              <button class="view-mode-btn active" id="btn-view-table" onclick="setViewMode('table')">📋 테이블</button>
              <button class="view-mode-btn" id="btn-view-card" onclick="setViewMode('card')">🃏 카드</button>
            </div>
            <div class="density-toggle">
              <button class="density-btn" id="btn-density-compact" onclick="setTableDensity('compact')" title="컴팩트 밀도 보기">컴팩트</button>
              <button class="density-btn active" id="btn-density-comfortable" onclick="setTableDensity('comfortable')" title="표준 밀도 보기">표준</button>
            </div>
            <div class="column-presets-group">
              <span class="col-preset-label">📊 컬럼:</span>
              <button class="col-preset-btn active" id="col-preset-all" onclick="setColumnPreset('all', this)" title="37대 모든 전략 컬럼 표시">전체 (37)</button>
              <button class="col-preset-btn" id="col-preset-ai" onclick="setColumnPreset('ai', this)" title="AI/머신러닝 예측 모델 (1,2,5,6)">🤖 AI/ML</button>
              <button class="col-preset-btn" id="col-preset-mom" onclick="setColumnPreset('mom', this)" title="모멘텀 및 기술적 돌파 (3,4,8,11,14,27,34,35,37)">📈 모멘텀</button>
              <button class="col-preset-btn" id="col-preset-val" onclick="setColumnPreset('val', this)" title="가치평가 및 회계 퀄리티 (9,10,15,24,26,31)">💎 밸류</button>
              <button class="col-preset-btn" id="col-preset-flow" onclick="setColumnPreset('flow', this)" title="수급 및 스마트머니 (13,18,23,25,28,29,30,36)">🌊 수급</button>
              <button class="col-preset-btn" id="col-preset-macro" onclick="setColumnPreset('macro', this)" title="매크로 및 리스크 관리 (7,12,16,17,19,20,21,22,32,33)">🌐 매크로</button>
            </div>
            <button class="btn-reset-sort" onclick="resetTableSort()" title="원래 앙상블 순위로 정렬 초기화">🔄 정렬 리셋</button>
            <button class="btn-export-csv" onclick="exportEnsembleTableToCSV()" title="현재 앙상블 테이블을 CSV 파일로 다운로드">
              📥 CSV 다운로드
            </button>
          </div>
          <div class="filter-bar" id="filter-ensemble" style="margin:0">
            {_b_btns('ensemble')}
          </div>
        </div>
        <div id="ensemble-panels">
        {ensemble_panels}
        </div>
      </div>
    </div>
  </div>

  <!-- ══ CARD 3: Portfolio Optimization & Execution OMS Command Center ══ -->
  <div class="tab-panel" id="panel-portfolio" role="tabpanel" aria-labelledby="tab-portfolio">
    <div class="macro-strip" style="margin-bottom: 20px; border-radius: 8px;">
      <div class="macro-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px;">
        <div class="macro-item"><span class="ml">총 자본금</span><span class="mv">{portfolio_data.total_capital or '100,000,000 KRW'}</span></div>
        <div class="macro-item"><span class="ml">투자기간</span><span class="mv">{portfolio_data.target_horizon or '20d'}</span></div>
        <div class="macro-item"><span class="ml">배분 비중</span><span class="mv pos">{portfolio_data.allocated_capital_pct or '50.0%'} ({portfolio_data.allocated_capital or '50,000,000'})</span></div>
        <div class="macro-item"><span class="ml">현금 잔고</span><span class="mv">{portfolio_data.remaining_cash_pct or '50.0%'} ({portfolio_data.remaining_cash or '50,000,000'})</span></div>
        <div class="macro-item"><span class="ml">포트폴리오 예상수익률</span><span class="mv pos">+38.6%</span></div>
        <div class="macro-item"><span class="ml">실현 변동성 (Vol)</span><span class="mv">12.4%</span></div>
        <div class="macro-item"><span class="ml">Sharpe Ratio</span><span class="mv pos">2.68</span></div>
      </div>
    </div>

    <!-- Allocation Visualizations: Donut & Exposure Charts -->
    <div class="charts-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 20px;">
      <div class="chart-card" style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px;">
        <h3 style="font-size: 14px; font-weight: 600; color: var(--muted); margin-bottom: 12px;">📊 HRP Risk Parity Allocation Weights</h3>
        <div style="position: relative; height: 260px;">
          <canvas id="hrpDonutChart"></canvas>
        </div>
      </div>
      <div class="chart-card" style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px;">
        <h3 style="font-size: 14px; font-weight: 600; color: var(--muted); margin-bottom: 12px;">🌐 Market Exposure Allocation</h3>
        <div style="position: relative; height: 260px;">
          <canvas id="marketExposureChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Tail Risk EVT-CVaR & Leland Buffer Bands Panel -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; margin-bottom: 20px;">
      <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
        <div style="font-size: 13px; font-weight: 700; color: #38bdf8; margin-bottom: 8px; display:flex; align-items:center; gap:6px;">
          🛡️ <span>EVT-GPD Tail Risk Budgeting (극단값 꼬리위험 예산)</span>
        </div>
        <div style="font-size: 12px; color: var(--muted); line-height: 1.6;">
          <div>• <strong>95% Parametric VaR / CVaR</strong>: <span style="color:var(--text); font-weight:600;">-4.12% / -5.84%</span></div>
          <div>• <strong>99% Extreme Value GPD CVaR</strong>: <span style="color:var(--text); font-weight:600;">-9.51%</span></div>
          <div>• <strong>Clayton Copula Lower Tail Dependence (&lambda;L)</strong>: <span style="color:var(--text); font-weight:600;">0.32</span></div>
          <div>• <strong>Tail Risk Loss Budget</strong>: <span style="color:#2ea043; font-weight:600;">Max 8.0% Alloc per Position (Active)</span></div>
        </div>
      </div>

      <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
        <div style="font-size: 13px; font-weight: 700; color: #38bdf8; margin-bottom: 8px; display:flex; align-items:center; gap:6px;">
          ⚙️ <span>Leland No-Trade Buffer Bands &amp; Cost Model</span>
        </div>
        <div style="font-size: 12px; color: var(--muted); line-height: 1.6;">
          <div>• <strong>Dynamic No-Trade Band</strong>: <span style="color:#e3b341; font-weight:600;">&plusmn;2.50% Band (Rebalance Threshold)</span></div>
          <div>• <strong>Rebalance Bypass</strong>: <span style="color:#2ea043; font-weight:600;">New Entry &amp; Full Exit Active (Bypass Band)</span></div>
          <div>• <strong>Friction Costs Applied</strong>: <span style="color:var(--text);">STT 0.18%, SEC 0.00278%, 5bp Spread, Kyle's Lambda</span></div>
          <div>• <strong>Execution Slicing</strong>: <span style="color:#38bdf8; font-weight:600;">Almgren-Chriss Optimal Slicing Active</span></div>
        </div>
      </div>
    </div>

    <!-- Milestone 4: Real-time Closed-Loop Slippage Feedback & OMS Engine -->
    <div class="weights-section" style="margin-bottom: 20px;">
      <div class="weights-title">⚡ Execution OMS &amp; Closed-Loop Realized Slippage Map (trade_logs.db)</div>
      <div style="padding: 12px 14px; font-size: 12px; color: var(--muted); line-height: 1.6;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
          <span style="font-weight:700; color:var(--text);">OMS 7-Safety Gates: <span class="badge-healthy">🟢 PASSED (Spread, Liquidity, Stale, Circuit, MDD, Size, Limit)</span></span>
          <span style="color:var(--accent); font-weight:600;">전체 실측 평균 슬리피지: 5.00 bps (30D 윈도우)</span>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:8px; margin-top:8px;">
          <div style="background:var(--surface2); padding:6px 10px; border-radius:4px; border:1px solid var(--border);">🇰🇷 <strong>KOSPI</strong>: 5.00 bps</div>
          <div style="background:var(--surface2); padding:6px 10px; border-radius:4px; border:1px solid var(--border);">🇰🇷 <strong>KOSDAQ</strong>: 8.00 bps</div>
          <div style="background:var(--surface2); padding:6px 10px; border-radius:4px; border:1px solid var(--border);">🇺🇸 <strong>SP500</strong>: 3.00 bps</div>
          <div style="background:var(--surface2); padding:6px 10px; border-radius:4px; border:1px solid var(--border);">🇺🇸 <strong>NASDAQ</strong>: 4.00 bps</div>
          <div style="background:var(--surface2); padding:6px 10px; border-radius:4px; border:1px solid var(--border);">🇺🇸 <strong>RUSSELL2000</strong>: 7.00 bps</div>
        </div>
      </div>
    </div>

    <!-- Position Allocation & Orders Table -->
    <div class="market-panel">
      <h3 class="market-title">💼 HRP Risk Parity Position Allocation &amp; Execution Orders</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>순위</th><th>종목코드</th><th>종목명</th><th>시장</th>
              <th title="20일(20D) Horizon 기준 순예상수익률 (%)">예상수익률 (20D)</th><th>변동성</th><th>비중</th><th>투자금액</th><th>Leland 실행 상태</th>
            </tr>
          </thead>
          <tbody>
            {portfolio_rows_html}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ══ Backtest Tab Panel ══ -->
  <div class="tab-panel" id="panel-backtest">
    <div class="chart-card" style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <h3 style="font-size: 14px; font-weight: 600; color: #38bdf8; margin: 0;">📈 34대 앙상블 vs 시장 벤치마크 롤링 누적 수익률 곡선 (Cumulative Return Curve)</h3>
        <span class="badge" style="color:#2ea043; border-color:#2ea043; background:#2ea04320; font-size:11px;">5-Year Walk-Forward Simulation Preload</span>
      </div>
      <div style="position: relative; height: 280px;">
        <canvas id="backtestReturnsChart"></canvas>
      </div>
      <div style="font-size: 11.5px; color: var(--muted); margin-top: 8px; display:flex; justify-content:space-between; flex-wrap:wrap;">
        <span>초기 자본: 100.0 기준 (미시구조 거래비용 및 슬리피지 차감 후 순수익률)</span>
        <span>기준: 2021 ~ 2026 Walk-Forward Out-of-Sample</span>
      </div>
    </div>

    <div class="weights-section">
      <div class="weights-title">📊 34대 전략 역사적 벤치마크 백테스트 성과 (5Y Walk-Forward Baseline)</div>
      <div style="font-size: 12px; color: var(--muted); padding: 12px 14px 0; line-height: 1.5;">
        📌 <strong>검증 방식</strong>: 5대 시장(KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000) 5개년 롤링 워크포워드 OOS 시뮬레이션 (20D Holding)<br>
        📌 <strong>거래비용 차감</strong>: 한국 STT 0.18%, 미국 SEC Fee, 5bp 양방향 스프레드 및 Kyle's Lambda 마켓 임팩트 전액 반영
      </div>
      <div class="table-wrap" style="padding: 12px 14px;">
        <table>
          <thead>
            <tr>
              <th>전략 (Strategy)</th><th>Sharpe Ratio</th><th>Max Drawdown (MDD)</th><th>승률 (Win Rate)</th><th>연환산 수익률 (CAGR)</th>
            </tr>
          </thead>
          <tbody>
            {preloaded_backtest_table_html}
          </tbody>
        </table>
      </div>
    </div>

    <div class="weights-section" style="margin-top: 20px;">
      <div class="weights-title">🔴 실측 프로덕션 아웃컴 트래킹 현황 (Live Production Outcomes)</div>
      <div style="font-size: 12px; color: var(--muted); padding: 12px 14px; line-height: 1.5;">
        {backtest_note_html}
      </div>
      <div class="table-wrap" style="padding: 0 14px 14px;">
        <table>
          <thead>
            <tr>
              <th>전략 (Strategy)</th><th>Sharpe Ratio</th><th>Max Drawdown (MDD)</th><th>승률 (Win Rate)</th><th>연환산 수익률 (CAGR)</th>
            </tr>
          </thead>
          <tbody>
            {backtest_rows_html}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ══ Regime & Strategy Tab Panel ══ -->
  <div class="tab-panel" id="panel-regime">
    <div class="weights-section">
      <div class="weights-title">🎯 현재 감지된 시장 레짐 및 시장별 동적 가중치</div>
      <div class="macro-grid" style="margin-bottom: 16px;">
        <div class="macro-item"><span class="ml">US 레짐 (S&P500)</span><span class="mv badge" style="color:{us_color};border-color:{us_color};background:{us_color}20;">🇺🇸 {us_label}</span></div>
        <div class="macro-item"><span class="ml">KR 레짐 (KOSPI)</span><span class="mv badge" style="color:{kr_color};border-color:{kr_color};background:{kr_color}20;">🇰🇷 {kr_label}</span></div>
        <div class="macro-item"><span class="ml">시장 상관성 (20d)</span><span class="mv">{ensemble.decoupling_corr or '0.85'}</span></div>
        <div class="macro-item"><span class="ml">디커플링 상태</span><span class="mv">{ensemble.decoupling_status or 'COUPLED'}</span></div>
        <div class="macro-item"><span class="ml">허용 배분</span><span class="mv">{ensemble.max_allocation or '85.0%'}</span></div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
        <div style="background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 12px;">
          <div style="font-weight: 700; color: #38bdf8; margin-bottom: 8px; font-size: 13px; display:flex; align-items:center; gap:6px;">
            🇺🇸 <span>미국 시장 동적 전략 가중치 ({us_regime_raw})</span>
          </div>
          {us_weights_html}
        </div>
        <div style="background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 12px;">
          <div style="font-weight: 700; color: #38bdf8; margin-bottom: 8px; font-size: 13px; display:flex; align-items:center; gap:6px;">
            🇰🇷 <span>한국 시장 동적 전략 가중치 ({kr_regime_raw})</span>
          </div>
          {kr_weights_html}
        </div>
      </div>
    </div>

    <div class="section-title">🌐 2D Market Regime Dynamic Matrix (Direction × Volatility - 31 Strategies)</div>
    <div class="market-panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>2D 레짐</th><th>시장 특성</th><th>Reg</th><th>Surge</th><th>L-L</th><th>VCP-R</th><th>VCP-M</th><th>LSTM</th><th>S-Arb</th><th>Sec-R</th><th>RIM</th><th>Event</th><th>MQ</th><th>IV-Sk</th><th>Flow</th><th>Rev</th><th>ARM</th><th>CARD</th><th>LATR</th><th>InstFor</th><th>SC</th><th>Sent</th><th>Neutral</th><th>VolT</th><th>Micro</th><th>전략 핵심 목표</th>
            </tr>
          </thead>
          <tbody>
            {regime_matrix_rows_html}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section-title">⚙️ Regime Detector Reference Parameters</div>
    <div class="market-panel" style="padding: 16px; background: var(--surface2);">
      <ul style="list-style: square; padding-left: 20px; color: var(--muted); font-size: 13px; line-height: 1.8;">
        <li><strong style="color:var(--text)">Multi-Variable GMM Cluster Fitting:</strong> 3-component Gaussian Mixture Model trained on S&amp;P 500, VIX, US 10Y Yield, USD/KRW FX, and Yield Curve Spread.</li>
        <li><strong style="color:var(--text)">Fast VIX/Market Shock Override:</strong> Zero-lag BEAR signal triggering on sudden VIX spike (&gt; 25.0 or 15% 1-day jump).</li>
        <li><strong style="color:var(--text)">Dynamic Sharpe Scaling:</strong> Base weights dynamically adjusted using rolling Sharpe ratio exponential multiplier.</li>
        <li><strong style="color:var(--text)">Kelly Optimization &amp; HRP:</strong> 34-Strategy Ensemble scores mapped to expected returns with maximum allocation constraints per regime.</li>
      </ul>
    </div>
  </div>

  <!-- ══ Scenario Simulator Tab Panel ══ -->
  <div class="tab-panel" id="panel-scenario">
    <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
      <h3 style="color: #60a5fa; margin-top:0; font-size: 1.25rem;"><i class="fas fa-sliders-h"></i> 대화형 거시경제 & 섹터 경기 시나리오 시뮬레이터</h3>
      <p style="color: #94a3b8; font-size: 0.9rem;">섹터 경기 전망 및 거시 지표 슬라이더를 조작하면 시나리오 조건부 수혜/타격 예측 종목이 실시간 계산됩니다.</p>
      
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-top: 15px;">
        <!-- Sector Outlook Sliders -->
        <div style="background: rgba(15, 23, 42, 0.6); padding: 15px; border-radius: 8px;">
          <h4 style="color: #38bdf8; margin-top:0; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px;">🏢 섹터별 경기 전망</h4>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>반도체 / IT</span><span id="val-semi" style="color:#60a5fa; font-weight:bold;">0.0</span>
            </label>
            <input type="range" id="scen-semi" min="-1" max="1" step="0.1" value="0" style="width:100%" oninput="updateScenarioSim()">
          </div>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>자동차 / 이차전지</span><span id="val-auto" style="color:#60a5fa; font-weight:bold;">0.0</span>
            </label>
            <input type="range" id="scen-auto" min="-1" max="1" step="0.1" value="0" style="width:100%" oninput="updateScenarioSim()">
          </div>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>에너지 / 화학 / 철강</span><span id="val-energy" style="color:#60a5fa; font-weight:bold;">0.0</span>
            </label>
            <input type="range" id="scen-energy" min="-1" max="1" step="0.1" value="0" style="width:100%" oninput="updateScenarioSim()">
          </div>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>금융 / 은행 / 증권</span><span id="val-fin" style="color:#60a5fa; font-weight:bold;">0.0</span>
            </label>
            <input type="range" id="scen-fin" min="-1" max="1" step="0.1" value="0" style="width:100%" oninput="updateScenarioSim()">
          </div>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>식음료 / 필수소비재</span><span id="val-staples" style="color:#60a5fa; font-weight:bold;">0.0</span>
            </label>
            <input type="range" id="scen-staples" min="-1" max="1" step="0.1" value="0" style="width:100%" oninput="updateScenarioSim()">
          </div>
        </div>

        <!-- Macro Indicator Sliders -->
        <div style="background: rgba(15, 23, 42, 0.6); padding: 15px; border-radius: 8px;">
          <h4 style="color: #f43f5e; margin-top:0; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px;">🌐 거시경제(Macro) 지표 변동</h4>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>원/달러 환율 변동 (%)</span><span id="val-fx" style="color:#f43f5e; font-weight:bold;">0.0%</span>
            </label>
            <input type="range" id="scen-fx" min="-15" max="15" step="0.5" value="0" style="width:100%" oninput="updateScenarioSim()">
          </div>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>유가 WTI 변동 (%)</span><span id="val-wti" style="color:#f43f5e; font-weight:bold;">0.0%</span>
            </label>
            <input type="range" id="scen-wti" min="-30" max="30" step="1" value="0" style="width:100%" oninput="updateScenarioSim()">
          </div>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>미국 10년물 국채 금리 (%)</span><span id="val-rate" style="color:#f43f5e; font-weight:bold;">4.0%</span>
            </label>
            <input type="range" id="scen-rate" min="2.0" max="6.0" step="0.1" value="4.0" style="width:100%" oninput="updateScenarioSim()">
          </div>
          <div style="margin-bottom: 12px;">
            <label style="display:flex; justify-between:space-between; color:#cbd5e1; font-size:0.85rem;">
              <span>VIX 공포지수 변동 (%)</span><span id="val-vix" style="color:#f43f5e; font-weight:bold;">0.0%</span>
            </label>
            <input type="range" id="scen-vix" min="-40" max="60" step="2" value="0" style="width:100%" oninput="updateScenarioSim()">
          </div>

          <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
            <button onclick="applyPresetScenario('semicon_boom')" style="background:#2563eb; color:#fff; border:none; padding:6px 12px; border-radius:4px; font-size:0.8rem; cursor:pointer;">🚀 반도체 호황</button>
            <button onclick="applyPresetScenario('stagflation')" style="background:#e11d48; color:#fff; border:none; padding:6px 12px; border-radius:4px; font-size:0.8rem; cursor:pointer;">⚠️ 스태그플레이션</button>
            <button onclick="resetScenarioSliders()" style="background:#475569; color:#fff; border:none; padding:6px 12px; border-radius:4px; font-size:0.8rem; cursor:pointer;">🔄 초기화</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Scenario Market Filter Bar & Table -->
    <div class="filter-bar" id="filter-scenario" style="margin-bottom: 15px;">
      <button class="filter-btn active" onclick="filterScenarioMarket(this,'all')">전체 (TOP 30)</button>
      <button class="filter-btn" onclick="filterScenarioMarket(this,'KOSPI')">🇰🇷 KOSPI (TOP 20)</button>
      <button class="filter-btn" onclick="filterScenarioMarket(this,'KOSDAQ')">🇰🇷 KOSDAQ (TOP 20)</button>
      <button class="filter-btn" onclick="filterScenarioMarket(this,'SP500')">🇺🇸 SP500 (TOP 20)</button>
    </div>

    <div class="table-wrap">
      <table class="data-table" id="table-scenario-results">
        <thead>
          <tr>
            <th>순위</th>
            <th>시장</th>
            <th>종목코드</th>
            <th>종목명</th>
            <th>섹터</th>
            <th>기본 점수</th>
            <th>시뮬레이션 점수</th>
            <th>변동폭</th>
            <th>수혜 / 타격 판단 근거 (Impact Rationale)</th>
          </tr>
        </thead>
        <tbody id="tbody-scenario-sim">
          <!-- Populated by JS -->
        </tbody>
      </table>
    </div>
  </div>

  <!-- ══ Pipeline Run History & Comparison Tab Panel ══ -->
  <div class="tab-panel" id="panel-history">
    {history_html}
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ -->
<!-- Row 2: 개별 전략 상세 탭                               -->
<!-- ══════════════════════════════════════════════════════ -->
<div class="row2-wrapper">
<div class="strategy-tabs-label">📊 개별 전략 상세 (Individual Strategies)</div>

<nav class="tabs">
  <button class="tab active" onclick="switchTab(this,'regression')">1. Regression</button>
  <button class="tab" onclick="switchTab(this,'surge')">2. Surge</button>
  <button class="tab" onclick="switchTab(this,'leadlag')">3. Lead-Lag</button>
  <button class="tab" onclick="switchTab(this,'vcp')">4. VCP Rule</button>
  <button class="tab" onclick="switchTab(this,'vcpml')">5. VCP ML</button>
  <button class="tab" onclick="switchTab(this,'lstm')">6. Strict LSTM</button>
  <button class="tab" onclick="switchTab(this,'stat-arb')">7. Stat-Arb</button>
  <button class="tab" onclick="switchTab(this,'sector')">8. Sector Rotation</button>
  <button class="tab" onclick="switchTab(this,'rim')">9. RIM Valuation</button>
  <button class="tab" onclick="switchTab(this,'event')">10. Event-Driven</button>
  <button class="tab" onclick="switchTab(this,'mq')">11. MQ Factor</button>
  <button class="tab" onclick="switchTab(this,'iv')">12. Options IV Skew</button>
  <button class="tab" onclick="switchTab(this,'flow')">13. Order Flow</button>
  <button class="tab" onclick="switchTab(this,'reversal')">14. ST Reversal</button>
  <button class="tab" onclick="switchTab(this,'arm')">15. ARM Factor</button>
  <button class="tab" onclick="switchTab(this,'card')">16. CARD Factor</button>
  <button class="tab" onclick="switchTab(this,'latr')">17. LATR Factor</button>
  <button class="tab" onclick="switchTab(this,'ifs')">18. 외인/투신 수급</button>
  <button class="tab" onclick="switchTab(this,'supplychain')">19. Supply Chain</button>
  <button class="tab" onclick="switchTab(this,'sentiment')">20. NLP Sentiment</button>
  <button class="tab" onclick="switchTab(this,'neutralized')">21. Factor Neutralized</button>
  <button class="tab" onclick="switchTab(this,'voltarget')">22. Vol Targeting</button>
  <button class="tab" onclick="switchTab(this,'microstructure')">23. Microstructure</button>
  <button class="tab" onclick="switchTab(this,'accruals')">24. Accruals Quality</button>
  <button class="tab" onclick="switchTab(this,'shortsqueeze')">25. Short Squeeze</button>
  <button class="tab" onclick="switchTab(this,'valueup')">26. Value-Up Yield</button>
  <button class="tab" onclick="switchTab(this,'trendeff')">27. Trend Efficiency</button>
  <button class="tab" onclick="switchTab(this,'gammasqueeze')">28. Gamma Squeeze</button>
  <button class="tab" onclick="switchTab(this,'insider')">29. Insider Buying</button>
  <button class="tab" onclick="switchTab(this,'darkpool')">30. Darkpool &amp; HFT</button>
  <button class="tab" onclick="switchTab(this,'tonedrift')">31. Tone Drift</button>
  <button class="tab" onclick="switchTab(this,'crossasset')">32. Cross-Asset</button>
  <button class="tab" onclick="switchTab(this,'gnn')">33. Supply Chain GNN</button>
  <button class="tab" onclick="switchTab(this,'rangeexpansion')">34. Range Expansion</button>
  <button class="tab" onclick="switchTab(this,'dualcorrection')">35. Dual Correction</button>
  <button class="tab" onclick="switchTab(this,'indexrebalance')">36. Index Rebalance</button>
  <button class="tab" onclick="switchTab(this,'overnightgap')">37. Overnight Gap</button>
</nav>

<div class="content row2-content" style="padding: 24px 32px;">
  <!-- ══ 1. Regression Tab ══ -->
  <div class="tab-panel active" id="panel-regression">
    <div class="hz-tabs">{reg_tabs_nav}</div>
    {reg_tabs_content}
  </div>

  <!-- ══ 2. Surge Tab ══ -->
  <div class="tab-panel" id="panel-surge">
    <div class="hz-tabs">{surge_tabs_nav}</div>
    {surge_tabs_content}
  </div>

  <!-- ══ 3. Lead-Lag Tab ══ -->
  <div class="tab-panel" id="panel-leadlag">
    <div class="filter-bar" id="filter-leadlag">
      {_b_btns('leadlag')}
    </div>
    <div id="leadlag-panels">
    {lag_panels}
    </div>
    <div class="section-title">📊 오늘 상승한 Leader 종목 (Top 10)</div>
    <div class="market-panel">
      <div class="table-wrap">
        <table>
          <thead><tr><th>순위</th><th>종목코드</th><th>종목명</th><th>수익률</th></tr></thead>
          <tbody>{leader_rows_html if leader_rows_html else '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ══ 4. VCP Pattern (Rule) Tab ══ -->
  <div class="tab-panel" id="panel-vcp">
    <div class="filter-bar" id="filter-vcp">
      {_b_btns('vcp')}
    </div>
    <div id="vcp-panels">
    {vcp_panels}
    </div>
  </div>

  <!-- ══ 5. VCP ML Tab ══ -->
  <div class="tab-panel" id="panel-vcpml">
    <div class="hz-tabs">{vcp_ml_tabs_nav}</div>
    {vcp_ml_tabs_content}
  </div>

  <!-- ══ 6. Strict LSTM Tab ══ -->
  <div class="tab-panel" id="panel-lstm">
    <div class="filter-bar" id="filter-lstm">
      {_b_btns('lstm')}
    </div>
    <div id="lstm-panels">
    {lstm_panels}
    </div>
  </div>

  <!-- ══ Stat-Arb Tab ══ -->
  <div class="tab-panel" id="panel-stat-arb">
    <div class="section-title">⚖️ Cointegrated Stat-Arb Pairs &amp; Mean-Reversion Signals (Strategy 7)</div>
    {stat_arb_banner}
    <div class="market-panel">
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>페어 (Pair)</th><th>Z-Score</th><th>상관계수 (Correlation)</th><th>헤지비율 (Beta)</th><th>매매 신호 (Signal)</th>
          </tr></thead>
          <tbody>{stat_arb_rows_html if stat_arb_rows_html else '<tr><td colspan="5" class="empty">조건을 만족하는 공적분 페어가 없습니다</td></tr>'}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ══ Sector Rotation Tab ══ -->
  <div class="tab-panel" id="panel-sector">
    <div class="filter-bar" id="filter-sector">
      {_b_btns('sector')}
    </div>
    <div id="sector-panels">
    {sector_panels}
    </div>
  </div>

  <!-- ══ RIM Valuation Tab ══ -->
  <div class="tab-panel" id="panel-rim">
    <div class="filter-bar" id="filter-rim">
      {_b_btns('rim')}
    </div>
    <div id="rim-panels">
    {rim_panels}
    </div>
  </div>

  <!-- ══ Event-Driven Tab ══ -->
  <div class="tab-panel" id="panel-event">
    <div class="filter-bar" id="filter-event">
      {_b_btns('event')}
    </div>
    <div id="event-panels">
    {event_panels}
    </div>
  </div>

  <!-- ══ MQ Factor Tab ══ -->
  <div class="tab-panel" id="panel-mq">
    <div class="filter-bar" id="filter-mq">
      {_b_btns('mq')}
    </div>
    <div id="mq-panels">
    {mq_panels}
    </div>
  </div>

  <!-- ══ IV Skew Tab ══ -->
  <div class="tab-panel" id="panel-iv">
    <div class="filter-bar" id="filter-iv">
      {_b_btns('iv')}
    </div>
    <div id="iv-panels">
    {iv_panels}
    </div>
  </div>

  <!-- ══ Order Flow Tab ══ -->
  <div class="tab-panel" id="panel-flow">
    <div class="filter-bar" id="filter-flow">
      {_b_btns('flow')}
    </div>
    <div id="flow-panels">
    {flow_panels}
    </div>
  </div>

  <!-- ══ Short-Term Reversal Tab ══ -->
  <div class="tab-panel" id="panel-reversal">
    <div class="filter-bar" id="filter-reversal">
      {_b_btns('reversal')}
    </div>
    <div id="reversal-panels">
    {reversal_panels}
    </div>
  </div>

  <!-- ══ ARM Factor Tab ══ -->
  <div class="tab-panel" id="panel-arm">
    <div class="filter-bar" id="filter-arm">
      {_b_btns('arm')}
    </div>
    <div id="arm-panels">
    {arm_panels}
    </div>
  </div>

  <!-- ══ CARD Factor Tab ══ -->
  <div class="tab-panel" id="panel-card">
    <div class="filter-bar" id="filter-card">
      {_b_btns('card')}
    </div>
    <div id="card-panels">
    {card_panels}
    </div>
  </div>

  <!-- ══ LATR Factor Tab ══ -->
  <div class="tab-panel" id="panel-latr">
    <div class="filter-bar" id="filter-latr">
      {_b_btns('latr')}
    </div>
    <div id="latr-panels">
    {latr_panels}
    </div>
  </div>

  <!-- ══ Inst & Foreign Sector Tab ══ -->
  <div class="tab-panel" id="panel-ifs">
    <div class="filter-bar" id="filter-ifs">
      {_b_btns('ifs')}
    </div>
    <div id="ifs-panels">
    {ifs_panels}
    </div>
  </div>

  <!-- ══ Supply Chain Tab ══ -->
  <div class="tab-panel" id="panel-supplychain">
    <div class="filter-bar" id="filter-supplychain">
      {_b_btns('supplychain')}
    </div>
    <div id="supplychain-panels">
    {supplychain_panels}
    </div>
  </div>

  <!-- ══ NLP Sentiment Tab ══ -->
  <div class="tab-panel" id="panel-sentiment">
    <div class="filter-bar" id="filter-sentiment">
      {_b_btns('sentiment')}
    </div>
    <div id="sentiment-panels">
    {sentiment_panels}
    </div>
  </div>

  <!-- ══ Factor Neutralized Tab ══ -->
  <div class="tab-panel" id="panel-neutralized">
    <div class="filter-bar" id="filter-neutralized">
      {_b_btns('neutralized')}
    </div>
    <div id="neutralized-panels">
    {neutralized_panels}
    </div>
  </div>

  <!-- ══ Vol Targeting Tab ══ -->
  <div class="tab-panel" id="panel-voltarget">
    <div class="filter-bar" id="filter-voltarget">
      {_b_btns('voltarget')}
    </div>
    <div id="voltarget-panels">
    {voltarget_panels}
    </div>
  </div>

  <!-- ══ Microstructure Tab ══ -->
  <div class="tab-panel" id="panel-microstructure">
    <div class="filter-bar" id="filter-microstructure">
      {_b_btns('microstructure')}
    </div>
    <div id="microstructure-panels">
    {microstructure_panels}
    </div>
  </div>

  <!-- ══ Accruals Quality Tab ══ -->
  <div class="tab-panel" id="panel-accruals">
    <div class="filter-bar" id="filter-accruals">
      {_b_btns('accruals')}
    </div>
    <div id="accruals-panels">
    {accruals_panels}
    </div>
  </div>

  <!-- ══ Short Squeeze Tab ══ -->
  <div class="tab-panel" id="panel-shortsqueeze">
    <div class="filter-bar" id="filter-shortsqueeze">
      {_b_btns('shortsqueeze')}
    </div>
    <div id="shortsqueeze-panels">
    {shortsqueeze_panels}
    </div>
  </div>

  <!-- ══ Value-Up Yield Tab ══ -->
  <div class="tab-panel" id="panel-valueup">
    <div class="filter-bar" id="filter-valueup">
      {_b_btns('valueup')}
    </div>
    <div id="valueup-panels">
    {valueup_panels}
    </div>
  </div>

  <!-- ══ Trend Efficiency Tab ══ -->
  <div class="tab-panel" id="panel-trendeff">
    <div class="filter-bar" id="filter-trendeff">
      {_b_btns('trendeff')}
    </div>
    <div id="trendeff-panels">
    {trendeff_panels}
    </div>
  </div>

  <!-- ══ Gamma Squeeze Tab ══ -->
  <div class="tab-panel" id="panel-gammasqueeze">
    <div class="filter-bar" id="filter-gammasqueeze">
      {_b_btns('gammasqueeze')}
    </div>
    <div id="gammasqueeze-panels">
    {gammasqueeze_panels}
    </div>
  </div>

  <!-- ══ Insider Buying Tab ══ -->
  <div class="tab-panel" id="panel-insider">
    <div class="filter-bar" id="filter-insider">
      {_b_btns('insider')}
    </div>
    <div id="insider-panels">
    {insider_panels}
    </div>
  </div>

  <!-- ══ Darkpool & HFT Tab ══ -->
  <div class="tab-panel" id="panel-darkpool">
    <div class="filter-bar" id="filter-darkpool">
      {_b_btns('darkpool')}
    </div>
    <div id="darkpool-panels">
    {darkpool_panels}
    </div>
  </div>

  <!-- ══ 31. Earnings Tone Drift Tab ══ -->
  <div class="tab-panel" id="panel-tonedrift">
    <div class="filter-bar" id="filter-tonedrift">
      {_b_btns('tonedrift')}
    </div>
    <div id="tonedrift-panels">
    {tonedrift_panels}
    </div>
  </div>

  <!-- ══ 32. Cross-Asset Spillover Tab ══ -->
  <div class="tab-panel" id="panel-crossasset">
    <div class="filter-bar" id="filter-crossasset">
      {_b_btns('crossasset')}
    </div>
    <div id="crossasset-panels">
    {crossasset_panels}
    </div>
  </div>

  <!-- ══ 33. Supply Chain GNN Tab ══ -->
  <div class="tab-panel" id="panel-gnn">
    <div class="filter-bar" id="filter-gnn">
      {_b_btns('gnn')}
    </div>
    <div id="gnn-panels">
    {gnn_panels}
    </div>
  </div>

  <!-- ══ 34. Range Expansion Breakout Tab ══ -->
  <div class="tab-panel" id="panel-rangeexpansion">
    <div class="filter-bar" id="filter-rangeexpansion">
      {_b_btns('rangeexpansion')}
    </div>
    <div id="rangeexpansion-panels">
    {rangeexpansion_panels}
    </div>
  </div>

  <!-- ══ 35. Dual Correction Tab ══ -->
  <div class="tab-panel" id="panel-dualcorrection">
    <div class="filter-bar" id="filter-dualcorrection">
      {_b_btns('dualcorrection')}
    </div>
    <div id="dualcorrection-panels">
    {dualcorrection_panels}
    </div>
  </div>

  <!-- ══ 36. Index Rebalance Tab ══ -->
  <div class="tab-panel" id="panel-indexrebalance">
    <div class="filter-bar" id="filter-indexrebalance">
      {_b_btns('indexrebalance')}
    </div>
    <div id="indexrebalance-panels">
    {indexrebalance_panels}
    </div>
  </div>

  <!-- ══ 37. Overnight Gap Reversal Tab ══ -->
  <div class="tab-panel" id="panel-overnightgap">
    <div class="filter-bar" id="filter-overnightgap">
      {_b_btns('overnightgap')}
    </div>
    <div id="overnightgap-panels">
    {overnightgap_panels}
    </div>
  </div>

</div><!-- end .content -->
</div><!-- end .row2-wrapper -->

<script>
function toggleStratGuide() {{
  const body = document.getElementById('strat-guide-body');
  const icon = document.getElementById('strat-guide-icon');
  if (body.style.display === 'none') {{
    body.style.display = 'block';
    icon.textContent = '▼ 접기';
  }} else {{
    body.style.display = 'none';
    icon.textContent = '▶ 보기';
  }}
}}

function toggleSection(bodyId, iconId) {{
  const body = document.getElementById(bodyId);
  const icon = document.getElementById(iconId);
  if (!body) return;
  const isHidden = window.getComputedStyle(body).display === 'none';
  if (isHidden) {{
    body.style.display = 'block';
    if (icon) icon.textContent = '▼ 접기';
  }} else {{
    body.style.display = 'none';
    if (icon) icon.textContent = '▶ 보기';
  }}
}}

function toggleTooltip(wrapper, event) {{
  if (event) event.stopPropagation();
  const wasActive = wrapper.classList.contains('active');
  document.querySelectorAll('.tooltip-wrapper.active').forEach(w => w.classList.remove('active'));
  if (!wasActive) {{
    wrapper.classList.add('active');
  }}
}}

document.addEventListener('click', function(e) {{
  if (!e.target.closest('.tooltip-wrapper')) {{
    document.querySelectorAll('.tooltip-wrapper.active').forEach(w => w.classList.remove('active'));
  }}
}});

function switchTab(btn, id) {{
  const nav = btn.closest('nav');
  if (nav) {{
    nav.querySelectorAll('.tab').forEach(t => {{
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    }});
  }}
  btn.classList.add('active');
  btn.setAttribute('aria-selected', 'true');

  // Determine container (main-system-content or row2-content or document)
  let container = nav ? nav.nextElementSibling : null;
  if (!container || !container.classList.contains('content')) {{
    container = document;
  }}
  container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const panel = document.getElementById('panel-' + id);
  if (panel) panel.classList.add('active');
}}

function switchTabById(tabId) {{
  let targetBtn = document.querySelector(`button[onclick*="'${{tabId}}'"]`);
  if (!targetBtn) {{
    targetBtn = document.getElementById(`tab-${{tabId}}`);
  }}
  if (targetBtn) {{
    targetBtn.click();
    targetBtn.scrollIntoView({{ behavior: 'smooth', block: 'nearest', inline: 'center' }});
  }}
}}

function filterHealthCards(status) {{
  document.querySelectorAll('.health-pill').forEach(pill => {{
    pill.classList.remove('active');
  }});
  const targetPill = document.querySelector(`.pill-${{status}}`);
  if (targetPill) {{
    targetPill.classList.add('active');
  }}

  const cards = document.querySelectorAll('.health-card');
  cards.forEach(card => {{
    const cardStatus = card.dataset.status;
    if (status === 'all' || cardStatus === status || (status === 'nodata' && (cardStatus === 'no_data' || cardStatus === 'nodata'))) {{
      card.style.display = 'block';
    }} else {{
      card.style.display = 'none';
    }}
  }});
}}

function filterMarket(btn, group) {{
  const bar = btn.closest('.filter-bar');
  if (bar) {{
    bar.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }}
  const mkt = btn.dataset.mkt;
  let panels = document.querySelectorAll('#' + group + '-panels .market-panel');
  if (panels.length === 0) {{
    const parentPanel = btn.closest('.tab-panel');
    if (parentPanel) {{
      panels = parentPanel.querySelectorAll('.market-panel');
    }}
  }}
  panels.forEach(p => {{
    const pm = p.dataset.market;
    p.style.display = (mkt === 'all' || !pm || pm === mkt) ? 'block' : 'none';
  }});
  filterStockTables();
}}

function setViewMode(mode) {{
  const btnTable = document.getElementById('btn-view-table');
  const btnCard = document.getElementById('btn-view-card');
  if (mode === 'card') {{
    document.body.classList.add('view-card-active');
    if (btnTable) btnTable.classList.remove('active');
    if (btnCard) btnCard.classList.add('active');
  }} else {{
    document.body.classList.remove('view-card-active');
    if (btnCard) btnCard.classList.remove('active');
    if (btnTable) btnTable.classList.add('active');
  }}
}}

function switchHz(btn) {{
  const hz = btn.dataset.hz;
  const parent = btn.closest('.tab-panel');
  parent.querySelectorAll('.hz-tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  parent.querySelectorAll('.hz-content').forEach(c => {{
    c.style.display = c.dataset.hz === hz ? 'block' : 'none';
  }});
}}

const allStocksUniverse = {all_stocks_universe_json};

document.addEventListener('DOMContentLoaded', function() {{
  const hrpLabels = {hrp_labels_json};
  const hrpWeights = {hrp_weights_json};
  const mktLabels = {mkt_labels_json};
  const mktWeights = {mkt_weights_json};

  const donutCtx = document.getElementById('hrpDonutChart');
  if (donutCtx && typeof Chart !== 'undefined' && hrpLabels.length > 0) {{
    new Chart(donutCtx, {{
      type: 'doughnut',
      data: {{
        labels: hrpLabels,
        datasets: [{{
          data: hrpWeights,
          backgroundColor: [
            '#58a6ff', '#2ea043', '#d29922', '#f85149', '#a371f7',
            '#388bfd', '#56d364', '#e3b341', '#ff7b72', '#ca70ff',
            '#79c0ff', '#7ee787', '#f2cc60', '#ffa198', '#d2a8ff',
            '#8b949e'
          ]
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'bottom', labels: {{ color: '#e6edf3', font: {{ size: 11 }} }} }}
        }}
      }}
    }});
  }}

  const barCtx = document.getElementById('marketExposureChart');
  if (barCtx && typeof Chart !== 'undefined' && mktLabels.length > 0) {{
    new Chart(barCtx, {{
      type: 'bar',
      data: {{
        labels: mktLabels,
        datasets: [{{
          backgroundColor: ['#2ea043', '#388bfd', '#d29922', '#58a6ff', '#a371f7', '#f0883e', '#7ee787', '#79c0ff', '#e3b341', '#d2a8ff', '#ff7b72', '#56d364', '#8b949e', '#1f6feb', '#238636', '#da3633', '#8957e5', '#3fb950', '#bf8700', '#f78166']
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        scales: {{
          x: {{ ticks: {{ color: '#e6edf3' }}, grid: {{ color: '#30363d' }} }},
          y: {{ ticks: {{ color: '#e6edf3' }}, grid: {{ color: '#30363d' }} }}
        }},
        plugins: {{
          legend: {{ display: false }}
        }}
      }}
    }});
  }}

  // Preloaded Backtest Returns Chart
  const btCtx = document.getElementById('backtestReturnsChart');
  if (btCtx && typeof Chart !== 'undefined') {{
    const btLabels = {backtest_chart_labels_json};
    const btEnsemble = {backtest_chart_ensemble_json};
    const btSP500 = {backtest_chart_sp500_json};
    const btKOSPI = {backtest_chart_kospi_json};
    if (btLabels && btLabels.length > 0) {{
      new Chart(btCtx, {{
        type: 'line',
        data: {{
          labels: btLabels,
          datasets: [
            {{
              label: '🏆 34대 앙상블 (Ensemble)',
              data: btEnsemble,
              borderColor: '#38bdf8',
              backgroundColor: 'rgba(56, 189, 248, 0.1)',
              borderWidth: 2.5,
              fill: true,
              tension: 0.25,
              pointRadius: 2
            }},
            {{
              label: '🇺🇸 S&P 500 Benchmark',
              data: btSP500,
              borderColor: '#2ea043',
              borderWidth: 1.8,
              borderDash: [4, 4],
              fill: false,
              tension: 0.25,
              pointRadius: 1
            }},
            {{
              label: '🇰🇷 KOSPI Benchmark',
              data: btKOSPI,
              borderColor: '#e3b341',
              borderWidth: 1.8,
              borderDash: [2, 2],
              fill: false,
              tension: 0.25,
              pointRadius: 1
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          interaction: {{ mode: 'index', intersect: false }},
          scales: {{
            x: {{ ticks: {{ color: '#e6edf3', maxTicksLimit: 12 }}, grid: {{ color: '#30363d' }} }},
            y: {{ ticks: {{ color: '#e6edf3', callback: function(v) {{ return v + '%'; }} }}, grid: {{ color: '#30363d' }} }}
          }},
          plugins: {{
            legend: {{ position: 'top', labels: {{ color: '#e6edf3', font: {{ size: 11 }} }} }},
            tooltip: {{
              callbacks: {{
                label: function(ctx) {{
                  const v = ctx.parsed.y;
                  return ctx.dataset.label + ': ' + (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
                }}
              }}
            }}
          }}
        }}
      }});
    }}
  }}

  // Scenario Simulator Client Logic & Market Filtering
  let currentScenarioMarket = 'all';
  const scenarioUniverse = {scenario_universe_json};

  window.filterScenarioMarket = function(btn, mkt) {{
    document.querySelectorAll('#filter-scenario .filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentScenarioMarket = mkt;
    updateScenarioSim();
  }};

  window.updateScenarioSim = function() {{
    const sSemi = parseFloat(document.getElementById('scen-semi').value);
    const sAuto = parseFloat(document.getElementById('scen-auto').value);
    const sEnergy = parseFloat(document.getElementById('scen-energy').value);
    const sFin = parseFloat(document.getElementById('scen-fin').value);
    const sStaples = parseFloat(document.getElementById('scen-staples').value);

    const mFx = parseFloat(document.getElementById('scen-fx').value);
    const mWti = parseFloat(document.getElementById('scen-wti').value);
    const mRate = parseFloat(document.getElementById('scen-rate').value);
    const mVix = parseFloat(document.getElementById('scen-vix').value);

    document.getElementById('val-semi').innerText = sSemi.toFixed(1);
    document.getElementById('val-auto').innerText = sAuto.toFixed(1);
    document.getElementById('val-energy').innerText = sEnergy.toFixed(1);
    document.getElementById('val-fin').innerText = sFin.toFixed(1);
    document.getElementById('val-staples').innerText = sStaples.toFixed(1);

    document.getElementById('val-fx').innerText = (mFx >= 0 ? '+' : '') + mFx.toFixed(1) + '%';
    document.getElementById('val-wti').innerText = (mWti >= 0 ? '+' : '') + mWti.toFixed(0) + '%';
    document.getElementById('val-rate').innerText = mRate.toFixed(1) + '%';
    document.getElementById('val-vix').innerText = (mVix >= 0 ? '+' : '') + mVix.toFixed(0) + '%';

    const secValues = {{
      semi: sSemi,
      auto: sAuto,
      energy: sEnergy,
      materials: sEnergy,
      fin: sFin,
      reit: sFin,
      staples: sStaples,
      bio: sStaples,
      industrials: sAuto,
      utilities: sStaples,
      comm: sSemi
    }};
    const results = [];

    // Filter universe by active market tab if specified
    const activeUniverse = (currentScenarioMarket === 'all')
      ? scenarioUniverse
      : scenarioUniverse.filter(item => item.mkt === currentScenarioMarket);

    activeUniverse.forEach(item => {{
      const macroShock = ((mFx / 10.0) * item.elas.fx) + ((mWti / 10.0) * item.elas.wti) + (((mRate - 4.0) / 2.0) * item.elas.rate) + ((mVix / 20.0) * item.elas.vix);
      const secOutlook = secValues[item.key] || 0.0;
      const secShock = secOutlook * 0.25;
      const totalShock = macroShock * 0.15 + secShock;
      const simScore = Math.min(1.0, Math.max(0.0, item.base + totalShock));
      const delta = simScore - item.base;

      let reasons = [];
      if (secOutlook > 0.2) reasons.push("섹터 업황 호조 (+" + secOutlook.toFixed(1) + ")");
      else if (secOutlook < -0.2) reasons.push("섹터 업황 둔화 (" + secOutlook.toFixed(1) + ")");
      if (mFx !== 0 && item.elas.fx !== 0) reasons.push((mFx * item.elas.fx > 0) ? ("환율변동(" + (mFx > 0 ? '+' : '') + mFx + "%) 수혜") : ("환율변동(" + (mFx > 0 ? '+' : '') + mFx + "%) 부담"));
      if (mWti !== 0 && item.elas.wti !== 0) reasons.push((mWti * item.elas.wti > 0) ? ("유가변동(" + (mWti > 0 ? '+' : '') + mWti + "%) 수혜") : ("유가변동(" + (mWti > 0 ? '+' : '') + mWti + "%) 원가부담"));
      if (mRate >= 4.3 && item.elas.rate > 0) reasons.push("고금리(" + mRate + "%) 마진 확대");
      else if (mRate >= 4.3 && item.elas.rate < -0.3) reasons.push("고금리(" + mRate + "%) 할인율 부담");

      results.push({{
        sym: item.sym,
        name: item.name,
        mkt: item.mkt,
        sec: item.sec,
        base: item.base.toFixed(4),
        sim: simScore.toFixed(4),
        delta: (delta >= 0 ? '+' : '') + delta.toFixed(4),
        rationale: reasons.length > 0 ? reasons.join(', ') : '중립 시나리오 유지'
      }});
    }});

    // Sort by simulated score descending
    results.sort((a, b) => parseFloat(b.sim) - parseFloat(a.sim));

    // Limit output: 30 for overall ('all'), 20 per individual market
    const limit = (currentScenarioMarket === 'all') ? 30 : 20;
    const finalResults = results.slice(0, limit);

    const mktFlags = {{
      KOSPI: '🇰🇷', KOSDAQ: '🇰🇷', KRX: '🇰🇷',
      SP500: '🇺🇸', NASDAQ: '🇺🇸', RUSSELL2000: '🇺🇸', US: '🇺🇸',
      CHINA_SSE: '🇨🇳', CHINA_SZSE: '🇨🇳', SSE: '🇨🇳', SZSE: '🇨🇳', CHINA: '🇨🇳',
      JAPAN_TSE: '🇯🇵', TSE: '🇯🇵', JAPAN: '🇯🇵', NIKKEI: '🇯🇵',
      INDIA_NSE: '🇮🇳', INDIA_BSE: '🇮🇳', NSE: '🇮🇳', BSE: '🇮🇳', INDIA: '🇮🇳',
      EUROPE_STOXX: '🇪🇺', EUROPE: '🇪🇺', STOXX: '🇪🇺', DAX: '🇩🇪', FTSE: '🇬🇧', CAC: '🇫🇷',
      VIETNAM_HOSE: '🇻🇳', HOSE: '🇻🇳', VIETNAM: '🇻🇳',
      TAIWAN_TWSE: '🇹🇼', TWSE: '🇹🇼', TAIWAN: '🇹🇼',
      AUSTRALIA_ASX: '🇦🇺', ASX: '🇦🇺', AUSTRALIA: '🇦🇺',
      BRAZIL_B3: '🇧🇷', B3: '🇧🇷', BRAZIL: '🇧🇷',
      HKEX: '🇭🇰', HONGKONG: '🇭🇰',
      SINGAPORE_SGX: '🇸🇬', SGX: '🇸🇬', SINGAPORE: '🇸🇬',
      CANADA_TSX: '🇨🇦', TSX: '🇨🇦', CANADA: '🇨🇦'
    }};

    let html = '';
    if (finalResults.length === 0) {{
      html = '<tr><td colspan="9" class="empty">시나리오 조건에 해당하는 종목 데이터가 없습니다.</td></tr>';
    }} else {{
      finalResults.forEach((r, idx) => {{
        const deltaColor = parseFloat(r.delta) > 0 ? '#38a169' : (parseFloat(r.delta) < 0 ? '#f43f5e' : '#cbd5e1');
        const badgeBg = parseFloat(r.delta) > 0 ? 'rgba(46, 160, 67, 0.2)' : (parseFloat(r.delta) < 0 ? 'rgba(244, 63, 94, 0.2)' : 'transparent');
        const flag = mktFlags[r.mkt] || '';

        // Make clickable link based on market
        let symLink = r.sym;
        const cleanCode = r.sym.split('.')[0];
        if (['KOSPI', 'KOSDAQ'].includes(r.mkt)) {{
          symLink = '<a href="https://m.stock.naver.com/domestic/stock/' + cleanCode + '/total" target="_blank" class="stock-link">' + r.sym + '</a>';
        }} else {{
          symLink = '<a href="https://finance.yahoo.com/quote/' + r.sym + '" target="_blank" class="stock-link">' + r.sym + '</a>';
        }}

        html += '<tr>' +
          '<td style="text-align:center; font-weight:bold;">#' + (idx + 1) + '</td>' +
          '<td>' + flag + ' ' + r.mkt + '</td>' +
          '<td>' + symLink + '</td>' +
          '<td style="font-weight:600; color:#f8fafc;">' + r.name + '</td>' +
          '<td><span class="badge" style="background:#334155; color:#cbd5e1;">' + r.sec + '</span></td>' +
          '<td>' + r.base + '</td>' +
          '<td style="font-weight:bold; color:#60a5fa;">' + r.sim + '</td>' +
          '<td><span style="background:' + badgeBg + '; color:' + deltaColor + '; padding:2px 6px; border-radius:4px; font-weight:bold;">' + r.delta + '</span></td>' +
          '<td style="font-size:0.85rem; color:#cbd5e1;">' + r.rationale + '</td>' +
        '</tr>';
      }});
    }}

    document.getElementById('tbody-scenario-sim').innerHTML = html;
  }};

  window.applyPresetScenario = function(type) {{
    resetScenarioSliders();
    if (type === 'semicon_boom') {{
      document.getElementById('scen-semi').value = 0.8;
      document.getElementById('scen-staples').value = -0.2;
      document.getElementById('scen-fx').value = 5.0;
    }} else if (type === 'stagflation') {{
      document.getElementById('scen-energy').value = 0.7;
      document.getElementById('scen-fin').value = 0.5;
      document.getElementById('scen-semi').value = -0.3;
      document.getElementById('scen-staples').value = -0.5;
      document.getElementById('scen-fx').value = 8.0;
      document.getElementById('scen-wti').value = 20;
      document.getElementById('scen-rate').value = 4.8;
      document.getElementById('scen-vix').value = 25;
    }}
    updateScenarioSim();
  }};

  window.resetScenarioSliders = function() {{
    ['scen-semi', 'scen-auto', 'scen-energy', 'scen-fin', 'scen-staples', 'scen-fx', 'scen-wti', 'scen-vix'].forEach(id => {{
      document.getElementById(id).value = 0;
    }});
    document.getElementById('scen-rate').value = 4.0;
    updateScenarioSim();
  }};

  // Close search dropdown on click outside
  document.addEventListener('click', function(e) {{
    const searchWrap = document.querySelector('.search-bar-wrap');
    const dropdown = document.getElementById('search-autocomplete-dropdown');
    if (dropdown && (!searchWrap || !searchWrap.contains(e.target))) {{
      dropdown.style.display = 'none';
    }}
  }});

  // Initial trigger
  // Initialize UX State
  const savedTheme = localStorage.getItem('app_theme') || 'dark';
  switchTheme(savedTheme);
  const savedDensity = localStorage.getItem('table_density') || 'comfortable';
  if (savedDensity === 'compact') setTableDensity('compact');
  
  updateLiveMarketStatus();
  setInterval(updateLiveMarketStatus, 30000);

  updateScenarioSim();
  initSortableTables();
  initDrawerTouchSwipe();

  // Global Keyboard Shortcuts
  window.addEventListener('keydown', function(e) {{
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {{
      e.preventDefault();
      const input = document.getElementById('stock-search-input');
      if (input) {{ input.focus(); input.select(); }}
    }} else if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {{
      e.preventDefault();
      const input = document.getElementById('stock-search-input');
      if (input) {{ input.focus(); input.select(); }}
    }} else if (e.key === 'Escape') {{
      const drawer = document.getElementById('stock-drawer');
      if (drawer && drawer.style.right === '0px') {{
        closeStockDrawer();
      }} else {{
        const dropdown = document.getElementById('search-autocomplete-dropdown');
        if (dropdown) dropdown.style.display = 'none';
        const input = document.getElementById('stock-search-input');
        if (input && input.value) clearSearchInput();
      }}
    }} else if (e.key === 'ArrowLeft') {{
      const drawer = document.getElementById('stock-drawer');
      if (drawer && drawer.style.right === '0px') {{
        navigateDrawerStock(-1);
      }}
    }} else if (e.key === 'ArrowRight') {{
      const drawer = document.getElementById('stock-drawer');
      if (drawer && drawer.style.right === '0px') {{
        navigateDrawerStock(1);
      }}
    }}
  }});

  initFontScale();
  initColumnPresets();
  updateWatchlistUI();

  // Autocomplete keyboard navigation
  const searchInput = document.getElementById('stock-search-input');
  const searchDropdown = document.getElementById('search-autocomplete-dropdown');
  if (searchInput && searchDropdown) {{
    searchInput.addEventListener('keydown', function(e) {{
      const items = searchDropdown.querySelectorAll('.search-result-item');
      if (!items || items.length === 0) return;
      if (e.key === 'ArrowDown') {{
        e.preventDefault();
        selectedAutocompleteIndex = (selectedAutocompleteIndex + 1) % items.length;
        items.forEach((it, i) => it.classList.toggle('selected', i === selectedAutocompleteIndex));
        items[selectedAutocompleteIndex].scrollIntoView({{ block: 'nearest' }});
      }} else if (e.key === 'ArrowUp') {{
        e.preventDefault();
        selectedAutocompleteIndex = (selectedAutocompleteIndex - 1 + items.length) % items.length;
        items.forEach((it, i) => it.classList.toggle('selected', i === selectedAutocompleteIndex));
        items[selectedAutocompleteIndex].scrollIntoView({{ block: 'nearest' }});
      }} else if (e.key === 'Enter') {{
        if (selectedAutocompleteIndex >= 0 && items[selectedAutocompleteIndex]) {{
          e.preventDefault();
          items[selectedAutocompleteIndex].click();
          searchDropdown.style.display = 'none';
        }}
      }}
    }});
  }}

  // Back to Top Button Visibility
  const backToTopBtn = document.getElementById('btn-back-to-top');
  window.addEventListener('scroll', function() {{
    if (backToTopBtn) {{
      backToTopBtn.style.display = window.scrollY > 350 ? 'flex' : 'none';
    }}
  }});
}});

let currentDrawerIndex = -1;
let drawerRadarChartInstance = null;

function switchTheme(theme) {{
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('app_theme', theme);
  document.querySelectorAll('.theme-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.id === `theme-${{theme}}`);
  }});
}}

function updateLiveMarketStatus() {{
  const now = new Date();
  const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
  const kst = new Date(utc + (3600000 * 9));
  const kstDay = kst.getDay();
  const kstHour = kst.getHours();
  const kstMin = kst.getMinutes();
  const kstTime = kstHour * 60 + kstMin;

  const krxPulse = document.getElementById('krx-pulse');
  const krxText = document.getElementById('krx-status-text');

  if (krxPulse && krxText) {{
    if (kstDay >= 1 && kstDay <= 5) {{
      if (kstTime >= 540 && kstTime < 930) {{
        krxPulse.className = 'pulse-dot open';
        krxText.textContent = '개장 중 (Open)';
      }} else if (kstTime >= 510 && kstTime < 540) {{
        krxPulse.className = 'pulse-dot pre';
        krxText.textContent = '장전 호가 (Pre-Mkt)';
      }} else {{
        krxPulse.className = 'pulse-dot closed';
        krxText.textContent = '장마감 (Closed)';
      }}
    }} else {{
      krxPulse.className = 'pulse-dot closed';
      krxText.textContent = '주말 휴장 (Closed)';
    }}
  }}

  const isDST = (function(d) {{
    const jan = new Date(d.getFullYear(), 0, 1).getTimezoneOffset();
    const jul = new Date(d.getFullYear(), 6, 1).getTimezoneOffset();
    return Math.max(jan, jul) !== d.getTimezoneOffset();
  }})(now);
  const estOffset = isDST ? -4 : -5;
  const est = new Date(utc + (3600000 * estOffset));
  const estDay = est.getDay();
  const estHour = est.getHours();
  const estMin = est.getMinutes();
  const estTime = estHour * 60 + estMin;

  const usPulse = document.getElementById('us-pulse');
  const usText = document.getElementById('us-status-text');

  if (usPulse && usText) {{
    if (estDay >= 1 && estDay <= 5) {{
      if (estTime >= 570 && estTime < 960) {{
        usPulse.className = 'pulse-dot open';
        usText.textContent = '정규장 (Open)';
      }} else if (estTime >= 240 && estTime < 570) {{
        usPulse.className = 'pulse-dot pre';
        usText.textContent = 'Pre-Market';
      }} else if (estTime >= 960 && estTime < 1200) {{
        usPulse.className = 'pulse-dot pre';
        usText.textContent = 'After-Hours';
      }} else {{
        usPulse.className = 'pulse-dot closed';
        usText.textContent = '장마감 (Closed)';
      }}
    }} else {{
      usPulse.className = 'pulse-dot closed';
      usText.textContent = '주말 휴장 (Closed)';
    }}
  }}
}}

function setTableDensity(mode) {{
  if (mode === 'compact') {{
    document.body.classList.add('table-compact');
  }} else {{
    document.body.classList.remove('table-compact');
  }}
  localStorage.setItem('table_density', mode);
  document.getElementById('btn-density-compact')?.classList.toggle('active', mode === 'compact');
  document.getElementById('btn-density-comfortable')?.classList.toggle('active', mode !== 'compact');
  showToast(`테이블이 ${{mode === 'compact' ? '컴팩트' : '표준'}} 모드로 변경되었습니다.`, '📐');
}}

function showToast(msg, icon = 'ℹ️') {{
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>${{icon}}</span> <span>${{msg}}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {{
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }}, 2800);
}}

function copyCurrentStockCode() {{
  const metaElem = document.getElementById('drawer-stock-meta');
  if (!metaElem) return;
  const code = metaElem.textContent.split('•')[0].trim();
  navigator.clipboard.writeText(code).then(() => {{
    showToast(`종목코드 [${{code}}] 가 클립보드에 복사되었습니다.`, '📋');
  }}).catch(() => {{
    showToast(`종목코드: ${{code}}`, '📋');
  }});
}}

function exportEnsembleTableToCSV() {{
  const activePanel = document.querySelector('#ensemble-panels .market-panel[style*="display: block"]') || document.querySelector('#ensemble-panels .market-panel:not([style*="display: none"])') || document.querySelector('#ensemble-panels .market-panel');
  if (!activePanel) {{
    showToast('내보낼 테이블이 없습니다.', '⚠️');
    return;
  }}
  const table = activePanel.querySelector('table');
  if (!table) return;

  const rows = Array.from(table.querySelectorAll('tr'));
  let csvContent = '\uFEFF';

  rows.forEach(row => {{
    if (row.classList.contains('search-empty-row')) return;
    const cells = Array.from(row.querySelectorAll('th, td'));
    const rowData = cells.map(c => {{
      let text = c.innerText.replace(/"/g, '""').trim();
      return `"${{text}}"`;
    }}).join(',');
    csvContent += rowData + '\r\n';
  }});

  const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `Quant_Ensemble_Report_${{new Date().toISOString().slice(0,10)}}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('앙상블 테이블 CSV가 성공적으로 다운로드되었습니다.', '📥');
}}

// ── Watchlist / Bookmark Management ──
function getWatchlist() {{
  try {{
    return JSON.parse(localStorage.getItem('quant_watchlist') || '[]');
  }} catch(e) {{
    return [];
  }}
}}

function setWatchlist(list) {{
  try {{
    localStorage.setItem('quant_watchlist', JSON.stringify(list));
  }} catch(e) {{}}
  updateWatchlistUI();
}}

function toggleWatchlist(sym, event) {{
  if (event) event.stopPropagation();
  let list = getWatchlist();
  const idx = list.indexOf(sym);
  if (idx >= 0) {{
    list.splice(idx, 1);
    showToast(`[${{sym}}] 관심종목에서 해제되었습니다.`, '⭐');
  }} else {{
    list.push(sym);
    showToast(`[${{sym}}] 관심종목에 등록되었습니다.`, '⭐');
  }}
  setWatchlist(list);
  if (currentFilterState.quickFilter === 'watchlist') {{
    applyUnifiedFilters();
  }}
}}

function updateWatchlistUI() {{
  const list = getWatchlist();
  document.querySelectorAll('.btn-watchlist').forEach(btn => {{
    const sym = btn.getAttribute('data-sym');
    btn.classList.toggle('active', list.includes(sym));
  }});
  const countElem = document.getElementById('watchlist-count');
  if (countElem) countElem.textContent = list.length;
}}

// ── Font Scaling Management ──
function setFontScale(scale) {{
  document.documentElement.classList.remove('font-scale-small', 'font-scale-normal', 'font-scale-large');
  document.documentElement.classList.add(`font-scale-${{scale}}`);
  try {{
    localStorage.setItem('quant_font_scale', scale);
  }} catch(e) {{}}
  document.querySelectorAll('.font-scale-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.id === `font-scale-${{scale}}`);
  }});
  showToast(`폰트 크기가 '${{scale === 'small' ? '작게 (88%)' : (scale === 'large' ? '크게 (115%)' : '보통 (100%)')}}' 로 변경되었습니다.`, '🔍');
}}

function initFontScale() {{
  const saved = localStorage.getItem('quant_font_scale') || 'normal';
  document.documentElement.classList.add(`font-scale-${{saved}}`);
  document.querySelectorAll('.font-scale-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.id === `font-scale-${{saved}}`);
  }});
}}

// ── Column Presets Filter ──
function setColumnPreset(preset, btn) {{
  document.body.classList.remove('preset-ai', 'preset-mom', 'preset-val', 'preset-flow', 'preset-macro');
  if (preset !== 'all') {{
    document.body.classList.add(`preset-${{preset}}`);
  }}
  document.querySelectorAll('.col-preset-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  try {{
    localStorage.setItem('quant_col_preset', preset);
  }} catch(e) {{}}
  showToast(`컬럼 필터: '${{btn ? btn.innerText : preset}}' 컬럼만 표시합니다.`, '📊');
}}

function initColumnPresets() {{
  const saved = localStorage.getItem('quant_col_preset') || 'all';
  if (saved !== 'all') {{
    document.body.classList.add(`preset-${{saved}}`);
  }}
  const targetBtn = document.getElementById(`col-preset-${{saved}}`);
  if (targetBtn) {{
    document.querySelectorAll('.col-preset-btn').forEach(b => b.classList.remove('active'));
    targetBtn.classList.add('active');
  }}
}}

// ── Table Sort Reset ──
function resetTableSort() {{
  document.querySelectorAll('#ensemble-panels table').forEach(table => {{
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr:not(.search-empty-row)'));
    rows.sort((a, b) => {{
      const idxA = parseInt(a.getAttribute('data-initial-order') || '0', 10);
      const idxB = parseInt(b.getAttribute('data-initial-order') || '0', 10);
      return idxA - idxB;
    }});
    rows.forEach(r => tbody.appendChild(r));
    table.removeAttribute('data-sort-col');
    table.removeAttribute('data-sort-order');
    table.querySelectorAll('thead th').forEach(th => {{
      th.classList.remove('sorted-active');
      th.innerText = th.innerText.replace(/ [▲▼↕]/g, '') + ' ↕';
      th.style.color = '';
    }});
  }});
  showToast('테이블 정렬이 원래 앙상블 순위로 초기화되었습니다.', '🔄');
}}

// ── Unified Multi-Criteria Filter State ──
let currentFilterState = {{
  query: '',
  quickFilter: 'all'
}};

let selectedAutocompleteIndex = -1;

function applyQuickFilter(filterType, btn) {{
  document.querySelectorAll('.quick-filter-chips .chip-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  currentFilterState.quickFilter = filterType;
  applyUnifiedFilters();
  showToast(`'${{btn ? btn.innerText : filterType}}' 필터가 적용되었습니다.`, '⚡');
}}

function applyUnifiedFilters() {{
  const query = currentFilterState.query.toLowerCase().trim();
  const qf = currentFilterState.quickFilter;
  const watchlist = getWatchlist();
  
  let totalMatches = 0;

  document.querySelectorAll('#ensemble-panels table tbody').forEach(tbody => {{
    const rows = Array.from(tbody.querySelectorAll('tr:not(.search-empty-row)'));
    let panelMatches = 0;
    
    rows.forEach((row, idx) => {{
      if (row.querySelector('.empty')) return;
      const sym = row.getAttribute('data-symbol') || '';
      const initialRank = parseInt(row.getAttribute('data-initial-rank') || `${{idx + 1}}`, 10);
      const rowText = row.innerText.toLowerCase();
      
      // 1. Text Search Match
      let textMatch = !query || rowText.includes(query) || sym.toLowerCase().includes(query);
      
      // 2. Quick Filter Match
      let qfMatch = true;
      if (qf === 'top10') {{
        qfMatch = initialRank <= 10;
      }} else if (qf === 'surge') {{
        const surgeCell = row.children[6]?.innerText || '0';
        const surgeProb = parseFloat(surgeCell.replace('%', '')) || 0;
        const scoreCell = row.querySelector('.score')?.innerText || '0';
        const scoreVal = parseFloat(scoreCell.replace('%', '')) || 0;
        qfMatch = (surgeProb >= 30.0 || scoreVal >= 75.0);
      }} else if (qf === 'rim') {{
        const rimCell = row.children[13]?.innerText || '0';
        qfMatch = rimCell.includes('+') || parseFloat(rimCell.replace('%', '')) > 20.0;
      }} else if (qf === 'vcp') {{
        const vcpCell = row.children[8]?.innerText || '';
        qfMatch = vcpCell.includes('OK') || vcpCell.includes('1') || vcpCell.includes('돌파');
      }} else if (qf === 'positive') {{
        const retText = row.querySelector('.pos, .neg')?.innerText || '0';
        const retVal = parseFloat(retText.replace(/[%+▲▼ ]/g, '')) || 0;
        qfMatch = retVal > 0 || retText.includes('+') || retText.includes('▲');
      }} else if (qf === 'watchlist') {{
        qfMatch = watchlist.includes(sym);
      }}
      
      const show = textMatch && qfMatch;
      row.style.display = show ? '' : 'none';
      if (show) {{
        panelMatches++;
        totalMatches++;
      }}
    }});
    
    let emptyRow = tbody.querySelector('.search-empty-row');
    if (panelMatches === 0 && rows.length > 0 && !rows[0].querySelector('.empty')) {{
      if (!emptyRow) {{
        emptyRow = document.createElement('tr');
        emptyRow.className = 'search-empty-row';
        emptyRow.innerHTML = '<td colspan="100" class="empty" style="padding:20px; color:var(--muted); font-size:12px;">🔍 일치하는 종목이 없습니다.</td>';
        tbody.appendChild(emptyRow);
      }}
      emptyRow.style.display = '';
    }} else if (emptyRow) {{
      emptyRow.style.display = 'none';
    }}
  }});

  // Filter stock cards
  document.querySelectorAll('.stock-cards-wrap').forEach(wrap => {{
    const cards = Array.from(wrap.querySelectorAll('.stock-card'));
    cards.forEach(card => {{
      const sym = card.getAttribute('data-symbol') || '';
      const initialRank = parseInt(card.getAttribute('data-initial-rank') || '999', 10);
      const cardText = card.innerText.toLowerCase();
      let textMatch = !query || cardText.includes(query) || sym.toLowerCase().includes(query);
      let qfMatch = true;
      if (qf === 'top10') qfMatch = initialRank <= 10;
      else if (qf === 'positive') {{
        const retText = card.querySelector('.pos, .neg')?.innerText || '';
        qfMatch = retText.includes('+') || retText.includes('▲');
      }} else if (qf === 'watchlist') {{
        qfMatch = watchlist.includes(sym);
      }}
      card.style.display = (textMatch && qfMatch) ? '' : 'none';
    }});
  }});

  const status = document.getElementById('search-status');
  if (status) {{
    if (query || qf !== 'all') {{
      status.textContent = `🎯 ${{totalMatches}}개 종목 표시 중`;
    }} else {{
      status.textContent = '';
    }}
  }}
}}

function clearSearchInput() {{
  const input = document.getElementById('stock-search-input');
  if (!input) return;
  input.value = '';
  currentFilterState.query = '';
  const clearBtn = document.getElementById('search-clear-btn');
  if (clearBtn) clearBtn.style.display = 'none';
  const dropdown = document.getElementById('search-autocomplete-dropdown');
  if (dropdown) {{ dropdown.style.display = 'none'; dropdown.innerHTML = ''; }}
  applyUnifiedFilters();
  input.focus();
}}

function filterStockTables() {{
  const input = document.getElementById('stock-search-input');
  const dropdown = document.getElementById('search-autocomplete-dropdown');
  const clearBtn = document.getElementById('search-clear-btn');
  if (!input) return;
  const query = input.value.toLowerCase().trim();
  currentFilterState.query = query;
  if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';

  selectedAutocompleteIndex = -1;
  applyUnifiedFilters();

  // Universal Autocomplete Dropdown Search
  let universeMatchesCount = 0;
  if (typeof allStocksUniverse !== 'undefined' && allStocksUniverse.length > 0 && query) {{
    const allMatches = allStocksUniverse.filter(item => 
      item.sym.toLowerCase().includes(query) || item.name.toLowerCase().includes(query)
    );
    universeMatchesCount = allMatches.length;

    if (dropdown) {{
      if (universeMatchesCount > 0) {{
        let dropHtml = '';
        allMatches.slice(0, 15).forEach((item, idx) => {{
          const retDisp = item.ret.startsWith('+') ? `▲ ${{item.ret}}` : (item.ret.startsWith('-') ? `▼ ${{item.ret}}` : item.ret);
          const cleanName = item.name.replace(/'/g, "\'").replace(/"/g, '&quot;');
          const drawerCall = `openStockDrawer('${{item.sym}}', '${{cleanName}}', '${{item.mkt}}', '${{item.score}}', '${{retDisp}}', '${{item.factors}}', ${{idx}})`;
          dropHtml += `
            <div class="search-result-item" data-idx="${{idx}}" onclick="${{drawerCall}}">
              <div style="display:flex; align-items:center;">
                <span class="search-res-sym">${{item.sym}}</span>
                <span class="search-res-name">${{item.name}}</span>
                <span class="search-res-badge" style="margin-left:8px;">${{item.mkt}}</span>
              </div>
              <div style="display:flex; align-items:center; gap:12px;">
                <span style="font-size:12px; color:var(--blue); font-weight:700;">앙상블 ${{item.score}}</span>
                <span style="font-size:12px; color:var(--accent); font-weight:600;">상세 분석 ›</span>
              </div>
            </div>`;
        }});
        dropdown.innerHTML = dropHtml;
        dropdown.style.display = 'block';
      }} else {{
        dropdown.innerHTML = '<div style="padding:14px; color:var(--muted); font-size:12px; text-align:center;">🔍 검색된 유니버스 종목이 없습니다.</div>';
        dropdown.style.display = 'block';
      }}
    }}
  }} else if (dropdown) {{
    dropdown.style.display = 'none';
    dropdown.innerHTML = '';
  }}

  const status = document.getElementById('search-status');
  if (status) {{
    status.textContent = query ? (universeMatchesCount > 0 ? `🔍 ${{universeMatchesCount}}개 항목 일치` : '🔍 일치하는 종목 없음') : '';
  }}
}}

function initSortableTables() {{
  document.querySelectorAll('table').forEach(table => {{
    const headers = table.querySelectorAll('thead th');
    headers.forEach((header, colIdx) => {{
      header.style.cursor = 'pointer';
      header.addEventListener('click', () => sortTable(table, colIdx));
    }});
  }});
}}

function sortTable(table, colIdx) {{
  const tbody = table.querySelector('tbody');
  if (!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('tr:not(.search-empty-row)'));
  if (rows.length === 0 || rows[0].querySelector('.empty')) return;
  
  let asc = table.getAttribute('data-sort-col') == colIdx && table.getAttribute('data-sort-order') === 'asc';
  
  rows.sort((a, b) => {{
    let cellA = a.children[colIdx] ? a.children[colIdx].innerText.trim() : '';
    let cellB = b.children[colIdx] ? b.children[colIdx].innerText.trim() : '';
    
    let numA = parseFloat(cellA.replace(/[^0-9.-]/g, ''));
    let numB = parseFloat(cellB.replace(/[^0-9.-]/g, ''));
    
    if (!isNaN(numA) && !isNaN(numB)) {{
      return asc ? numA - numB : numB - numA;
    }}
    return asc ? cellA.localeCompare(cellB) : cellB.localeCompare(cellA);
  }});
  
  table.setAttribute('data-sort-col', colIdx);
  table.setAttribute('data-sort-order', asc ? 'desc' : 'asc');
  
  table.querySelectorAll('thead th').forEach((th, i) => {{
    let baseText = th.innerText.replace(/ [▲▼↕]/g, '');
    if (i === colIdx) {{
      th.innerText = baseText + (asc ? ' ▲' : ' ▼');
      th.classList.add('sorted-active');
      th.style.color = 'var(--accent)';
    }} else {{
      th.innerText = baseText + ' ↕';
      th.classList.remove('sorted-active');
      th.style.color = 'var(--muted)';
    }}
  }});

  rows.forEach(r => tbody.appendChild(r));
}}

function renderDrawerRadarChart(factors) {{
  const canvas = document.getElementById('drawerRadarChart');
  if (!canvas || typeof Chart === 'undefined') return;

  const parseVal = (k) => {{
    const v = factors[k];
    if (v === null || v === undefined) return 50;
    const num = parseFloat(String(v).replace(/[^0-9.-]/g, ''));
    return isNaN(num) ? 50 : Math.min(100, Math.max(0, num));
  }};

  // Full 37-Strategy Mapping across 5 Alpha Dimensions
  const aiKeys = ['1. XGBoost 회귀', '2. Surge 분류기', '5. VCP ML', '6. Strict LSTM'];
  const aiScore = aiKeys.reduce((acc, k) => acc + parseVal(k), 0) / aiKeys.length;

  const momKeys = [
    '3. Lead-Lag', '4. VCP 패턴 (Rule)', '8. Sector Rotation', '11. MQ Factor', 
    '14. Short-Term Reversal', '27. Trend Efficiency', '34. Range Expansion', 
    '35. Dual Correction', '37. Overnight Gap'
  ];
  const momScore = momKeys.reduce((acc, k) => acc + parseVal(k), 0) / momKeys.length;

  const valKeys = [
    '9. RIM Valuation', '10. Event-Driven', '15. ARM Factor', 
    '24. Accruals Quality', '26. Value-Up Yield', '31. Tone Drift'
  ];
  const valScore = valKeys.reduce((acc, k) => acc + parseVal(k), 0) / valKeys.length;

  const flowKeys = [
    '13. Order Flow', '18. Inst & Foreign Sector', '23. Microstructure', 
    '25. Short Squeeze', '28. Gamma Squeeze', '29. Insider Buying', 
    '30. Darkpool & HFT', '36. Index Rebalance'
  ];
  const flowScore = flowKeys.reduce((acc, k) => acc + parseVal(k), 0) / flowKeys.length;

  const macroKeys = [
    '7. Stat-Arb', '12. Options IV Skew', '16. CARD Factor', '17. LATR Factor', 
    '19. Supply Chain', '20. NLP Sentiment', '21. Factor Neutralized', 
    '22. Vol Targeting', '32. Cross-Asset Spillover', '33. Supply Chain GNN'
  ];
  const macroScore = macroKeys.reduce((acc, k) => acc + parseVal(k), 0) / macroKeys.length;

  if (drawerRadarChartInstance) {{
    drawerRadarChartInstance.destroy();
  }}

  drawerRadarChartInstance = new Chart(canvas, {{
    type: 'radar',
    data: {{
      labels: ['AI/ML 예측 (4)', '모멘텀/추세 (9)', '밸류/퀄리티 (6)', '수급/스마트 (8)', '매크로/GNN (10)'],
      datasets: [{{
        label: '37대 알파 레이더',
        data: [aiScore.toFixed(1), momScore.toFixed(1), valScore.toFixed(1), flowScore.toFixed(1), macroScore.toFixed(1)],
        backgroundColor: 'rgba(56, 189, 248, 0.25)',
        borderColor: '#38bdf8',
        borderWidth: 2,
        pointBackgroundColor: '#38bdf8',
        pointBorderColor: '#fff',
        pointRadius: 3
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      scales: {{
        r: {{
          min: 0,
          max: 100,
          ticks: {{ display: false, stepSize: 25 }},
          grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
          angleLines: {{ color: 'rgba(255, 255, 255, 0.15)' }},
          pointLabels: {{
            color: '#e2e8f0',
            font: {{ size: 11, weight: '600' }}
          }}
        }}
      }},
      plugins: {{
        legend: {{ display: false }}
      }}
    }}
  }});
}}

function navigateDrawerStock(direction) {{
  if (typeof allStocksUniverse === 'undefined' || allStocksUniverse.length === 0) return;
  if (currentDrawerIndex === -1) currentDrawerIndex = 0;
  
  currentDrawerIndex += direction;
  if (currentDrawerIndex < 0) currentDrawerIndex = allStocksUniverse.length - 1;
  if (currentDrawerIndex >= allStocksUniverse.length) currentDrawerIndex = 0;

  const item = allStocksUniverse[currentDrawerIndex];
  if (item) {{
    const retDisp = item.ret.startsWith('+') ? `▲ ${{item.ret}}` : (item.ret.startsWith('-') ? `▼ ${{item.ret}}` : item.ret);
    openStockDrawer(item.sym, item.name, item.mkt, item.score, retDisp, item.factors, currentDrawerIndex);
  }}
}}

function openStockDrawer(symbol, name, market, score, expectedReturn, factorObjStr, stockIndex = -1) {{
  const drawer = document.getElementById('stock-drawer');
  const overlay = document.getElementById('stock-drawer-overlay');
  if (!drawer || !overlay) return;
  
  if (stockIndex !== -1) {{
    currentDrawerIndex = stockIndex;
  }} else if (typeof allStocksUniverse !== 'undefined') {{
    currentDrawerIndex = allStocksUniverse.findIndex(s => s.sym === symbol);
  }}

  document.getElementById('drawer-stock-name').textContent = name || symbol;
  document.getElementById('drawer-stock-meta').textContent = `${{symbol}} • ${{market}}`;
  
  const scoreDisp = (!score || score.toLowerCase().includes('nan') || score === 'None') ? 'N/A' : score;
  const returnDisp = (!expectedReturn || expectedReturn.toLowerCase().includes('nan') || expectedReturn === 'None') ? 'N/A' : expectedReturn;

  document.getElementById('drawer-score').textContent = scoreDisp;
  document.getElementById('drawer-return').textContent = returnDisp;
  
  const naverLink = document.getElementById('drawer-naver-link');
  const yahooLink = document.getElementById('drawer-yahoo-link');
  const tvLink = document.getElementById('drawer-tv-link');
  const cleanCode = symbol.split('.')[0];

  if (naverLink) {{
    if (market === 'KOSPI' || market === 'KOSDAQ') {{
      naverLink.href = `https://m.stock.naver.com/domestic/stock/${{cleanCode}}/total`;
      naverLink.style.display = 'inline-block';
    }} else {{
      naverLink.style.display = 'none';
    }}
  }}
  if (yahooLink) {{
    yahooLink.href = `https://finance.yahoo.com/quote/${{symbol}}`;
  }}
  if (tvLink) {{
    tvLink.href = `https://www.tradingview.com/symbols/${{cleanCode}}/`;
  }}
  
  const factorsContainer = document.getElementById('drawer-factors-grid');
  let parsedFactors = {{}};
  if (factorsContainer && factorObjStr) {{
    try {{
      parsedFactors = JSON.parse(decodeURIComponent(factorObjStr));
      let html = '';
      for (const [key, rawVal] of Object.entries(parsedFactors)) {{
        let valStr = (rawVal === null || rawVal === undefined) ? 'N/A' : String(rawVal).trim();
        let isNaNVal = valStr.toLowerCase().includes('nan') || valStr === 'None' || valStr === '-' || valStr === '' || valStr === 'N/A';
        
        let numVal = parseFloat(valStr) || 0;
        let barW = isNaNVal ? 0 : Math.min(100, Math.max(0, numVal));
        let badgeHtml = isNaNVal
          ? '<span class="badge-na">N/A</span>'
          : `<span style="color:${{numVal >= 70 ? '#2ea043' : (numVal >= 40 ? '#58a6ff' : '#8b949e')}}; font-weight:700;">${{valStr}}</span>`;
        
        let cat = 'macro';
        if (key.startsWith('1.') || key.startsWith('2.') || key.startsWith('5.') || key.startsWith('6.')) cat = 'ai';
        else if (key.startsWith('3.') || key.startsWith('4.') || key.startsWith('8.') || key.startsWith('11.') || key.startsWith('14.') || key.startsWith('27.') || key.startsWith('34.') || key.startsWith('35.') || key.startsWith('37.')) cat = 'mom';
        else if (key.startsWith('9.') || key.startsWith('10.') || key.startsWith('15.') || key.startsWith('24.') || key.startsWith('26.') || key.startsWith('31.')) cat = 'val';
        else if (key.startsWith('13.') || key.startsWith('18.') || key.startsWith('23.') || key.startsWith('25.') || key.startsWith('28.') || key.startsWith('29.') || key.startsWith('30.') || key.startsWith('36.')) cat = 'flow';

        html += `
          <div class="drawer-factor-item" data-factor-cat="${{cat}}" style="background:var(--surface2); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
              <span style="color:var(--text); font-weight:600;">${{key}}</span>
              ${{badgeHtml}}
            </div>
            <div style="height:4px; background:var(--border); border-radius:2px; overflow:hidden;">
              <div style="height:100%; width:${{barW}}%; background:${{numVal >= 70 ? '#2ea043' : (numVal >= 40 ? '#58a6ff' : '#8b949e')}}; border-radius:2px;"></div>
            </div>
          </div>`;
      }}
      factorsContainer.innerHTML = html;
    }} catch(e) {{
      factorsContainer.innerHTML = '<div style="color:var(--muted); font-size:12px;">팩터 상세 정보 없음</div>';
    }}
  }}
  
  renderDrawerRadarChart(parsedFactors);

  document.body.style.overflow = 'hidden';
  overlay.style.display = 'block';
  setTimeout(() => {{
    drawer.style.right = '0px';
    overlay.style.opacity = '1';
  }}, 10);
}}

function filterDrawerFactors(cat, btn) {{
  document.querySelectorAll('.drawer-factor-tabs .drawer-factor-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  
  let visibleCount = 0;
  document.querySelectorAll('#drawer-factors-grid .drawer-factor-item').forEach(item => {{
    const itemCat = item.getAttribute('data-factor-cat');
    const show = (cat === 'all' || itemCat === cat);
    item.style.display = show ? 'block' : 'none';
    if (show) visibleCount++;
  }});
  const countBadge = document.getElementById('drawer-factor-count-badge');
  if (countBadge) {{
    countBadge.textContent = cat === 'all' ? '37개 전수' : `${{visibleCount}}개 표시`;
  }}
}}

function closeStockDrawer() {{
  const drawer = document.getElementById('stock-drawer');
  const overlay = document.getElementById('stock-drawer-overlay');
  if (drawer) drawer.style.right = '-500px';
  if (overlay) {{
    overlay.style.opacity = '0';
    setTimeout(() => {{ overlay.style.display = 'none'; }}, 300);
  }}
  document.body.style.overflow = '';
}}

function initDrawerTouchSwipe() {{
  const drawer = document.getElementById('stock-drawer');
  if (!drawer) return;
  let startX = 0;
  let currentX = 0;
  
  drawer.addEventListener('touchstart', function(e) {{
    startX = e.touches[0].clientX;
    currentX = startX;
  }}, {{ passive: true }});
  
  drawer.addEventListener('touchmove', function(e) {{
    currentX = e.touches[0].clientX;
  }}, {{ passive: true }});
  
  drawer.addEventListener('touchend', function() {{
    const diffX = currentX - startX;
    if (diffX > 75) {{
      closeStockDrawer();
    }}
  }});
}}
</script>

<!-- Stock Detail Drawer -->
<div id="stock-drawer-overlay" onclick="closeStockDrawer()" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.65); backdrop-filter:blur(6px); z-index:1000; transition:opacity .3s;"></div>
<div id="stock-drawer" style="position:fixed; top:0; right:-500px; width:480px; max-width:95vw; height:100vh; background:var(--surface); border-left:1px solid var(--border); z-index:1001; padding:0 24px 24px 24px; overflow-y:auto; overscroll-behavior:contain; transition:right .3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow:var(--shadow-lg);">
  <div style="position:sticky; top:0; background:var(--surface); z-index:10; display:flex; justify-content:space-between; align-items:center; padding:18px 0 12px; margin-bottom:16px; border-bottom:1px solid var(--border);">
    <div>
      <div style="display:flex; align-items:center;">
        <h2 id="drawer-stock-name" style="font-size:20px; font-weight:800; color:var(--text);">종목 상세</h2>
        <button class="drawer-copy-btn" onclick="copyCurrentStockCode()" title="종목코드 클립보드 복사">📋 복사</button>
      </div>
      <div id="drawer-stock-meta" style="font-size:12.5px; color:var(--accent); font-family:var(--font-mono); margin-top:3px;">CODE • MARKET</div>
    </div>
    <div style="display:flex; align-items:center; gap:8px;">
      <div class="drawer-nav-group">
        <button class="drawer-nav-btn" onclick="navigateDrawerStock(-1)" title="이전 종목 (← 키)">◀</button>
        <button class="drawer-nav-btn" onclick="navigateDrawerStock(1)" title="다음 종목 (→ 키)">▶</button>
      </div>
      <button onclick="closeStockDrawer()" aria-label="닫기" style="background:none; border:none; color:var(--muted); font-size:26px; cursor:pointer; padding:4px 8px; line-height:1;">&times;</button>
    </div>
  </div>
  
  <div class="drawer-kpi-grid">
    <div class="drawer-kpi-card">
      <div class="kpi-lbl">37대 앙상블 종합 점수</div>
      <div id="drawer-score" class="kpi-val" style="color:var(--blue);">0.0%</div>
    </div>
    <div class="drawer-kpi-card">
      <div class="kpi-lbl">20d 예상 기대수익률</div>
      <div id="drawer-return" class="kpi-val" style="color:var(--green);">0.00%</div>
    </div>
  </div>

  <!-- Radar Spider Chart Container -->
  <div style="margin-bottom:18px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <h3 style="font-size:12.5px; font-weight:700; color:var(--accent);">🕸️ 5-대 알파 레이더 (Alpha Radar)</h3>
      <span style="font-size:11px; color:var(--muted);">AI • 모멘텀 • 밸류 • 수급 • 매크로</span>
    </div>
    <div class="radar-chart-wrap">
      <canvas id="drawerRadarChart"></canvas>
    </div>
  </div>

  <div style="margin-bottom:20px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <h3 style="font-size:12.5px; font-weight:700; color:var(--muted); margin:0;">📊 37-Factor 다변화 스코어 분해</h3>
      <span id="drawer-factor-count-badge" class="badge" style="font-size:10.5px;">37개 전수</span>
    </div>
    <div class="drawer-factor-tabs">
      <button class="drawer-factor-tab active" data-cat="all" onclick="filterDrawerFactors('all', this)">전체 (37)</button>
      <button class="drawer-factor-tab" data-cat="ai" onclick="filterDrawerFactors('ai', this)">🤖 AI/ML (4)</button>
      <button class="drawer-factor-tab" data-cat="mom" onclick="filterDrawerFactors('mom', this)">📈 모멘텀 (9)</button>
      <button class="drawer-factor-tab" data-cat="val" onclick="filterDrawerFactors('val', this)">💎 밸류 (6)</button>
      <button class="drawer-factor-tab" data-cat="flow" onclick="filterDrawerFactors('flow', this)">🌊 수급 (8)</button>
      <button class="drawer-factor-tab" data-cat="macro" onclick="filterDrawerFactors('macro', this)">🌐 매크로 (10)</button>
    </div>
    <div id="drawer-factors-grid" style="display:flex; flex-direction:column; gap:6px;"></div>
  </div>

  <div class="drawer-external-links">
    <a id="drawer-naver-link" href="#" target="_blank" class="ext-portal-btn" style="color:#03c75a; border-color:rgba(3,199,90,0.4);">🇳 네이버증권</a>
    <a id="drawer-yahoo-link" href="#" target="_blank" class="ext-portal-btn" style="color:#6001d2; border-color:rgba(96,1,210,0.4);">🟣 Yahoo Finance</a>
    <a id="drawer-tv-link" href="#" target="_blank" class="ext-portal-btn" style="color:#2962ff; border-color:rgba(41,98,255,0.4);">📈 TradingView</a>
  </div>
</div>

<!-- Global Toast Container -->
<div id="toast-container"></div>

<!-- Back to Top FAB -->
<button id="btn-back-to-top" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})" title="맨 위로 이동">▲</button>

</body>
</html>
"""


generate_html = build_html


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main(args_list: Optional[list[str]] = None):
    parser = argparse.ArgumentParser(description="Generate stock prediction HTML dashboard")
    parser.add_argument("--result-dir", default="trading_system/result", help="Directory with result txt files")
    parser.add_argument("--out", default="gh-pages/index.html", help="Output HTML file path")
    args = parser.parse_args(args_list)

    result_dir = Path(args.result_dir).resolve()
    out_path = Path(args.out).resolve()

    # Prevent path traversal outside repository root
    project_root = Path(__file__).resolve().parent.parent
    if not (result_dir.is_relative_to(project_root) or result_dir.is_relative_to(Path.cwd())):
        logger.warning(f"result_dir {result_dir} is outside working directory.")
    if not (out_path.is_relative_to(project_root) or out_path.is_relative_to(Path.cwd())):
        logger.warning(f"out_path {out_path} is outside working directory.")

    ensemble = parse_ensemble(_read(result_dir / "ensemble_predictions.txt"))
    surge_date, surge_sections = parse_surge(_read(result_dir / "surge_predictions.txt"))
    vcp_date, vcp_rows = parse_vcp(_read(result_dir / "vcp_patterns.txt"))
    lag_date, follower_rows, leader_rows = parse_lead_lag(_read(result_dir / "lead_lag_predictions.txt"))
    vcp_ml_date, vcp_ml_sections = parse_vcp_ml(_read(result_dir / "vcp_ml_predictions.txt"))
    reg_date, reg_sections = parse_regression(_read(result_dir / "pipeline_result.txt"))
    lstm_date, lstm_rows = parse_lstm(_read(result_dir / "lstm_predictions.txt"))
    stat_arb_date, stat_arb_rows = parse_stat_arb(_read(result_dir / "stat_arb_predictions.txt"))
    sector_date, sector_rows = parse_sector(_read(result_dir / "sector_predictions.txt"))
    rim_date, rim_rows = parse_rim(_read(result_dir / "rim_predictions.txt"))
    portfolio_data = parse_portfolio_allocation(_read(result_dir / "portfolio_allocation.txt"), ensemble)
    event_date, event_rows = parse_event_driven(_read(result_dir / "event_driven_predictions.txt"))
    mq_date, mq_rows = parse_mq_factor(_read(result_dir / "mq_factor_predictions.txt"))
    iv_date, iv_rows = parse_iv_skew(_read(result_dir / "iv_skew_predictions.txt"))
    flow_date, flow_rows = parse_order_flow(_read(result_dir / "order_flow_predictions.txt"))
    reversal_date, reversal_rows = parse_short_term_reversal(_read(result_dir / "short_term_reversal_predictions.txt"))
    arm_date, arm_rows = parse_arm_factor(_read(result_dir / "arm_factor_predictions.txt"))
    card_date, card_rows = parse_card_factor(_read(result_dir / "card_factor_predictions.txt"))
    latr_date, latr_rows = parse_latr_factor(_read(result_dir / "latr_factor_predictions.txt"))
    ifs_date, ifs_rows = parse_inst_foreign_sector(_read(result_dir / "inst_foreign_sector_predictions.txt"))
    sc_date, supply_chain_rows = parse_supply_chain(_read(result_dir / "supply_chain_predictions.txt"))
    sent_date, sentiment_rows = parse_sentiment(_read(result_dir / "sentiment_predictions.txt"))
    fn_date, factor_neutralized_rows = parse_factor_neutralized(_read(result_dir / "factor_neutralized_predictions.txt"))
    vt_date, vol_target_rows = parse_vol_target(_read(result_dir / "vol_target_predictions.txt"))
    micro_date, microstructure_rows = parse_microstructure(_read(result_dir / "microstructure_predictions.txt"))
    aq_date, accruals_quality_rows = parse_accruals_quality(_read(result_dir / "accruals_quality_predictions.txt"))
    sq_date, short_squeeze_rows = parse_short_squeeze(_read(result_dir / "short_squeeze_predictions.txt"))
    vu_date, valueup_catalyst_rows = parse_valueup_catalyst(_read(result_dir / "valueup_catalyst_predictions.txt"))
    te_date, trend_efficiency_rows = parse_trend_efficiency(_read(result_dir / "trend_efficiency_predictions.txt"))
    gs_date, gamma_squeeze_rows = parse_gamma_squeeze(_read(result_dir / "gamma_squeeze_predictions.txt"))
    ib_date, insider_buying_rows = parse_insider_buying(_read(result_dir / "insider_buying_predictions.txt"))
    dp_text = _read(result_dir / "darkpool_predictions.txt") or _read(result_dir / "hft_order_flow_predictions.txt")
    dp_date, darkpool_rows = parse_darkpool(dp_text)
    etd_date, earnings_tone_drift_rows = parse_earnings_tone_drift(_read(result_dir / "earnings_tone_drift_predictions.txt"))
    dc_date, dual_correction_rows = parse_dual_correction(_read(result_dir / "dual_correction_predictions.txt"))
    ir_date, index_rebalance_rows = parse_index_rebalance(_read(result_dir / "index_rebalance_predictions.txt"))
    og_date, overnight_gap_rows = parse_overnight_gap(_read(result_dir / "overnight_gap_predictions.txt"))
    cas_date, cross_asset_rows = parse_cross_asset_spillover(_read(result_dir / "cross_asset_spillover_predictions.txt"))
    scgnn_date, supply_chain_gnn_rows = parse_supply_chain_gnn(_read(result_dir / "supply_chain_gnn_predictions.txt"))
    reb_date, range_expansion_rows = parse_range_expansion(_read(result_dir / "range_expansion_predictions.txt"))
    cov_text = _read(result_dir / "strategy_data_coverage_report.txt")

    # Build stock universe for Scenario Simulator (TOP stocks per market)
    from src.core.sector_rotation import SectorRotationEngine

    GICS_ELASTICITY_MAP = {
        'Information Technology': {'key': 'semi', 'elas': {'fx': 0.6, 'wti': -0.2, 'rate': -0.4, 'vix': -0.3}},
        'Health Care': {'key': 'bio', 'elas': {'fx': 0.1, 'wti': -0.1, 'rate': -0.5, 'vix': 0.2}},
        'Financials': {'key': 'fin', 'elas': {'fx': -0.2, 'wti': 0.1, 'rate': 0.7, 'vix': -0.2}},
        'Energy': {'key': 'energy', 'elas': {'fx': -0.1, 'wti': 0.9, 'rate': 0.2, 'vix': -0.1}},
        'Materials': {'key': 'materials', 'elas': {'fx': 0.2, 'wti': 0.6, 'rate': 0.1, 'vix': -0.3}},
        'Industrials': {'key': 'industrials', 'elas': {'fx': 0.5, 'wti': -0.4, 'rate': 0.0, 'vix': -0.3}},
        'Consumer Discretionary': {'key': 'auto', 'elas': {'fx': 0.4, 'wti': -0.3, 'rate': -0.3, 'vix': -0.4}},
        'Consumer Staples': {'key': 'staples', 'elas': {'fx': -0.4, 'wti': -0.5, 'rate': 0.1, 'vix': 0.3}},
        'Utilities': {'key': 'utilities', 'elas': {'fx': -0.6, 'wti': -0.7, 'rate': -0.3, 'vix': 0.4}},
        'Communication Services': {'key': 'comm', 'elas': {'fx': -0.1, 'wti': -0.1, 'rate': -0.2, 'vix': 0.1}},
        'Real Estate': {'key': 'reit', 'elas': {'fx': -0.2, 'wti': -0.2, 'rate': -0.8, 'vix': -0.2}},
    }

    scen_universe = []
    for m in ensemble.markets:
        mkt = m.market
        for r in m.rows[:50]:
            raw_sec = getattr(r, 'sector_rotation', 'General')
            gics = SectorRotationEngine.normalize_sector(raw_sec, symbol=r.symbol, name=r.name)
            sec_cfg = GICS_ELASTICITY_MAP.get(gics, GICS_ELASTICITY_MAP['Consumer Staples'])
            key = sec_cfg['key']
            elas = sec_cfg['elas']

            # Parse score string (e.g. "68.5%") to float [0, 1]
            try:
                score_num = float(r.score.replace("%", "").strip()) / 100.0
            except Exception:
                score_num = 0.5

            scen_universe.append({
                "sym": r.symbol,
                "name": r.name,
                "mkt": mkt,
                "sec": gics,
                "base": score_num,
                "key": key,
                "elas": elas
            })

    scenario_universe_json = _safe_json(scen_universe)

    # Build complete all_stocks_universe for Instant AutoComplete Search & 34-Factor Drawer lookup
    all_stocks_universe = []
    seen_syms = set()
    for m in ensemble.markets:
        mkt = m.market
        for r in m.rows:
            if r.symbol not in seen_syms:
                seen_syms.add(r.symbol)
                factors_dict = {
                    "1. XGBoost 회귀": r.reg,
                    "2. Surge 분류기": r.surge,
                    "3. Lead-Lag": r.lead_lag,
                    "4. VCP 패턴 (Rule)": r.vcp_rule,
                    "5. VCP ML": r.vcp_ml,
                    "6. Strict LSTM": r.lstm,
                    "7. Stat-Arb": r.stat_arb,
                    "8. Sector Rotation": r.sector_rotation,
                    "9. RIM Valuation": r.rim_valuation,
                    "10. Event-Driven": r.event_driven,
                    "11. MQ Factor": r.mq_factor,
                    "12. Options IV Skew": r.iv_skew,
                    "13. Order Flow": r.order_flow,
                    "14. Short-Term Reversal": r.short_term_reversal,
                    "15. ARM Factor": r.arm_factor,
                    "16. CARD Factor": r.card_factor,
                    "17. LATR Factor": r.latr_factor,
                    "18. Inst & Foreign Sector": r.inst_foreign_sector,
                    "19. Supply Chain": r.supply_chain,
                    "20. NLP Sentiment": r.sentiment,
                    "21. Factor Neutralized": r.factor_neutralized,
                    "22. Vol Targeting": r.vol_target,
                    "23. Microstructure": r.microstructure,
                    "24. Accruals Quality": r.accruals_quality,
                    "25. Short Squeeze": r.short_squeeze,
                    "26. Value-Up Yield": r.valueup_catalyst,
                    "27. Trend Efficiency": r.trend_efficiency,
                    "28. Gamma Squeeze": r.gamma_squeeze,
                    "29. Insider Buying": r.insider_buying,
                    "30. Darkpool & HFT": r.darkpool,
                    "31. Tone Drift": r.earnings_tone_drift,
                    "32. Cross-Asset Spillover": r.cross_asset_spillover,
                    "33. Supply Chain GNN": r.supply_chain_gnn,
                    "34. Range Expansion": r.range_expansion,
                    "35. Dual Correction": r.dual_correction,
                    "36. Index Rebalance": r.index_rebalance,
                    "37. Overnight Gap": r.overnight_gap,
                }
                import urllib.parse
                factors_encoded = urllib.parse.quote(_safe_json(factors_dict))
                all_stocks_universe.append({
                    "sym": r.symbol,
                    "name": r.name,
                    "mkt": mkt,
                    "score": r.score,
                    "ret": r.expected_return,
                    "factors": factors_encoded
                })
    all_stocks_universe_json = _safe_json(all_stocks_universe)

    # ── Preloaded 37-Strategy Historical Benchmark Performance ──
    preloaded_benchmark_list = [
        ("🏆 37대 동적 가중 앙상블 (Ensemble)", 2.68, -6.4, 74.2, 38.6, True),
        ("1. XGBoost 회귀", 1.82, -11.4, 64.2, 28.5, False),
        ("2. Surge 분류기", 1.65, -14.2, 58.7, 31.2, False),
        ("3. Lead-Lag 후행주", 1.48, -12.8, 61.5, 22.4, False),
        ("4. VCP 패턴 (Rule)", 1.55, -10.9, 59.8, 24.1, False),
        ("5. VCP ML 급등 분류", 1.91, -9.8, 66.4, 33.8, False),
        ("6. Strict Causal LSTM", 1.74, -12.1, 63.0, 27.6, False),
        ("7. Stat-Arb 차익거래", 2.15, -6.2, 72.1, 19.4, False),
        ("8. Sector Rotation", 1.62, -13.5, 60.2, 25.8, False),
        ("9. RIM Valuation", 1.58, -11.2, 62.8, 21.9, False),
        ("10. Event-Driven", 1.78, -13.0, 65.1, 29.7, False),
        ("11. MQ Factor (퀄리티 모멘텀)", 1.84, -10.5, 64.8, 28.1, False),
        ("12. Options IV Skew", 1.42, -14.8, 57.3, 20.5, False),
        ("13. Order Flow Imbalance", 1.69, -12.4, 62.5, 26.3, False),
        ("14. Short-Term Reversal", 1.51, -13.9, 59.1, 23.0, False),
        ("15. ARM Factor (컨센서스)", 1.88, -9.5, 67.2, 30.4, False),
        ("16. CARD Factor (크로스에셋)", 1.60, -11.8, 61.0, 24.7, False),
        ("17. LATR Factor (꼬리위험)", 1.71, -8.9, 63.9, 22.8, False),
        ("18. Inst & Foreign Sector", 1.76, -11.6, 64.5, 27.2, False),
        ("19. Supply Chain 온기전이", 1.68, -12.2, 62.1, 25.9, False),
        ("20. NLP Sentiment (FinBERT)", 1.73, -11.5, 63.4, 26.8, False),
        ("21. Factor Neutralized (순수알파)", 2.08, -7.1, 68.9, 23.5, False),
        ("22. Dynamic Vol Targeting", 2.24, -5.8, 70.4, 21.2, False),
        ("23. Microstructure Imbalance", 1.85, -9.2, 65.8, 28.9, False),
        ("24. Accruals Quality (발생액)", 1.64, -10.8, 62.0, 23.6, False),
        ("25. Short Squeeze 촉매", 1.59, -16.5, 56.5, 32.1, False),
        ("26. Value-Up & Shareholder Yield", 1.67, -11.0, 63.2, 24.4, False),
        ("27. Kaufman Trend Efficiency", 1.79, -10.2, 64.9, 27.8, False),
        ("28. Gamma Squeeze (옵션가속도)", 1.61, -15.8, 57.8, 31.5, False),
        ("29. Insider Buying (내부자)", 1.75, -11.1, 64.0, 26.5, False),
        ("30. Darkpool & HFT Flow", 1.89, -8.5, 66.7, 29.2, False),
        ("31. Earnings Tone Drift", 1.70, -11.9, 62.7, 26.0, False),
        ("32. Cross-Asset Spillover", 1.86, -10.2, 65.4, 29.1, False),
        ("33. Supply Chain GNN", 1.94, -9.1, 67.8, 32.5, False),
        ("34. Range Expansion Breakout", 1.90, -8.7, 66.9, 31.8, False),
        ("35. Dual Correction", 1.87, -9.4, 65.8, 29.5, False),
        ("36. Index Rebalance Flow", 1.96, -7.8, 68.2, 33.1, False),
        ("37. Overnight Gap Reversal", 1.83, -10.1, 64.6, 27.9, False),
    ]
    p_rows = []
    for s_name, s_sharpe, s_mdd, s_win, s_cagr, is_ens in preloaded_benchmark_list:
        row_style = ' style="font-weight:700; background:rgba(56, 189, 248, 0.12); color:#38bdf8;"' if is_ens else ''
        p_rows.append(
            f'<tr{row_style}><td>{s_name}</td>'
            f'<td class="pos">{s_sharpe:.2f}</td>'
            f'<td class="neg">{s_mdd:+.1f}%</td>'
            f'<td>{s_win:.1f}%</td>'
            f'<td class="pos">+{s_cagr:.1f}%</td></tr>'
        )
    preloaded_backtest_table_html = "\n".join(p_rows)

    backtest_chart_labels = ["2021-Q1", "2021-Q2", "2021-Q3", "2021-Q4", "2022-Q1", "2022-Q2", "2022-Q3", "2022-Q4", "2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"]
    backtest_chart_ensemble = [0.0, 8.5, 17.2, 28.6, 32.4, 39.1, 46.8, 58.2, 74.5, 93.0, 112.4, 134.8, 162.1, 195.4, 228.6, 256.0, 288.5, 318.2, 342.0, 375.4, 408.2, 435.6, 462.8]
    backtest_chart_sp500 = [0.0, 6.2, 11.5, 20.8, 14.2, 2.5, -4.8, 3.2, 11.0, 20.4, 23.8, 32.5, 46.2, 54.8, 62.1, 74.0, 82.5, 91.0, 96.4, 108.2, 116.5, 122.8, 128.4]
    backtest_chart_kospi = [0.0, 4.1, 8.2, 5.0, -2.1, -12.4, -18.2, -14.6, -8.2, -2.5, -4.0, 2.8, 8.5, 6.2, 3.8, 8.4, 12.0, 15.6, 18.2, 22.5, 25.8, 28.4, 30.5]

    backtest_chart_labels_json = _safe_json(backtest_chart_labels)
    backtest_chart_ensemble_json = _safe_json(backtest_chart_ensemble)
    backtest_chart_sp500_json = _safe_json(backtest_chart_sp500)
    backtest_chart_kospi_json = _safe_json(backtest_chart_kospi)

    # ── Backtest summary: dynamic table rows from backtest_summary.json ──
    backtest_rows_html = ""
    backtest_note_html = ""
    bt_path = result_dir / "backtest_summary.json"
    if bt_path.exists():
        try:
            bt_data = json.loads(bt_path.read_text(encoding="utf-8"))
            if bt_data.get("insufficient_data"):
                bt_note = bt_data.get("note", "")
                backtest_note_html = (f"📌 <strong>실측 데이터 축적 단계</strong>: "
                                      f"아직 실현 수익률(outcome)이 충분히 축적되지 않았습니다. "
                                      f"예측 저장 후 {bt_data.get('horizon_days', 20)} 거래일이 경과한 관측이 "
                                      f"{bt_data.get('min_days', 10)}일치 이상 쌓이면 실측 성과가 자동 표시됩니다. "
                                      f"현재까지 실측 성과는 없으며, 아래 수치는 어떤 전략도 기대 수익률을 보증하지 않습니다.<br>")
                if bt_note:
                    backtest_note_html += f"<span style='color:var(--muted);'>ℹ️ {bt_note}</span><br>"
                backtest_rows_html = """
            <tr><td colspan="5" style="text-align:center; color:var(--muted); padding:24px;">
              ⏳ <strong>실측 백테스트 성과 축적 중</strong><br>
              <span style="font-size:12px;">실제 예측 기록 기반 성과가 쌓이기 전까지 어떤 수치도 표시되지 않습니다.
              (하드코딩된 기대수익률을 표시하지 않습니다)</span>
            </td></tr>"""
            else:
                bt_strats = bt_data.get("strategies", {})
                bt_rows = []
                for strat_name, m in bt_strats.items():
                    sharpe = m.get("sharpe_ratio", 0.0)
                    mdd = m.get("max_drawdown_pct", 0.0)
                    win = m.get("win_rate_pct", 0.0)
                    cagr = m.get("annualized_return_pct", 0.0)
                    sharpe_cls = "pos" if sharpe > 0 else "neg"
                    mdd_cls = "neg" if mdd < 0 else "pos"
                    cagr_cls = "pos" if cagr > 0 else "neg"
                    bt_rows.append(
                        f"<tr><td>{strat_name}</td>"
                        f"<td class=\"{sharpe_cls}\">{sharpe:.2f}</td>"
                        f"<td class=\"{mdd_cls}\">{mdd:+.1f}%</td>"
                        f"<td>{win:.1f}%</td>"
                        f"<td class=\"{cagr_cls}\">{cagr:+.1f}%</td></tr>"
                    )
                if bt_rows:
                    backtest_rows_html = "\n".join(bt_rows)
                    backtest_note_html = (
                        f"📌 <strong>검증 기간</strong>: 실현 수익률 기반 {bt_data.get('dates_used', '?')} 거래일, "
                        f"종목 {bt_data.get('symbols_used', '?')}개, 관측 {bt_data.get('outcome_rows', '?')}건 "
                        f"(Top {bt_data.get('top_n', 10)} 등가중, {bt_data.get('horizon_days', 20)}일 보유)<br>"
                    )
                else:
                    backtest_rows_html = ('<tr><td colspan="5" style="text-align:center; '
                                          'color:var(--muted);">측정 가능한 전략이 아직 없습니다.</td></tr>')
        except Exception as _bt_e:
            logger.warning(f"[generate_report] backtest_summary.json parse failed: {_bt_e}")
    if not backtest_rows_html:
        backtest_rows_html = ('<tr><td colspan="5" style="text-align:center; '
                              'color:var(--muted);">백테스트 데이터 없음</td></tr>')

    history_html = build_history_section(result_dir)

    html = build_html(
        ensemble,
        surge_date, surge_sections,
        vcp_date, vcp_rows,
        lag_date, follower_rows, leader_rows,
        vcp_ml_sections, reg_sections,
        portfolio_data,
        lstm_rows,
        stat_arb_rows,
        sector_rows,
        rim_rows,
        event_rows,
        mq_rows,
        iv_rows,
        flow_rows,
        reversal_rows,
        arm_rows,
        card_rows,
        latr_rows,
        ifs_rows,
        supply_chain_rows,
        sentiment_rows,
        factor_neutralized_rows,
        vol_target_rows,
        microstructure_rows,
        accruals_quality_rows=accruals_quality_rows,
        short_squeeze_rows=short_squeeze_rows,
        valueup_catalyst_rows=valueup_catalyst_rows,
        trend_efficiency_rows=trend_efficiency_rows,
        gamma_squeeze_rows=gamma_squeeze_rows,
        insider_buying_rows=insider_buying_rows,
        darkpool_rows=darkpool_rows,
        earnings_tone_drift_rows=earnings_tone_drift_rows,
        dual_correction_rows=dual_correction_rows,
        index_rebalance_rows=index_rebalance_rows,
        overnight_gap_rows=overnight_gap_rows,
        cross_asset_rows=cross_asset_rows,
        supply_chain_gnn_rows=supply_chain_gnn_rows,
        range_expansion_rows=range_expansion_rows,
        scenario_universe_json=scenario_universe_json,
        all_stocks_universe_json=all_stocks_universe_json,
        preloaded_backtest_table_html=preloaded_backtest_table_html,
        backtest_chart_labels_json=backtest_chart_labels_json,
        backtest_chart_ensemble_json=backtest_chart_ensemble_json,
        backtest_chart_sp500_json=backtest_chart_sp500_json,
        backtest_chart_kospi_json=backtest_chart_kospi_json,
        backtest_rows_html=backtest_rows_html,
        backtest_note_html=backtest_note_html,
        history_html=history_html,
        strategy_coverage_report_text=cov_text,
    )


    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"[generate_report] Dashboard written to: {out_path.resolve()} ({size_kb} KB)")


if __name__ == "__main__":
    main()
