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
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.data_layer.data_validator import DataValidator, clean_macro_value

logger = logging.getLogger(__name__)

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
    markets: list[EnsembleMarket] = field(default_factory=list)
    decision_rationale: str = ""
    coverage_report: str = ""
    decoupling_status: str = "COUPLED"
    decoupling_corr: str = "1.00"
    us_regime: str = "BULL_LOW_VOL"
    kr_regime: str = "BULL_LOW_VOL"

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
    score: str

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
            return DataValidator.clean_macro_value(val_str, fallback_str, kind)

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
            data.kr10y = _clean_macro(m.group(1), "3.35%", "kr10y")
        m = re.match(r"USD/KRW FX Rate.*:\s*(.+)", line)
        if m:
            data.usdkrw = _clean_macro(m.group(1), "1,380.00 KRW", "usdkrw")
        m = re.match(r"WTI Crude Oil.*:\s*(.+)", line)
        if m:
            data.wti = _clean_macro(m.group(1), "$75.50 / bbl", "wti")
        m = re.match(r"Gold \(GLD ETF\).*:\s*(.+)", line)
        if m:
            data.gold = _clean_macro(m.group(1), "$2,380.00", "gold")
    # Parse weights block
    in_weights_block = False
    for line in text.splitlines():
        line_s = line.strip()
        if "Applied Ensemble Strategy Weights" in line_s:
            in_weights_block = True
            continue
        if in_weights_block:
            if line_s.startswith("---"):
                in_weights_block = False
            elif ":" in line_s and line_s.endswith("%"):
                parts = line_s.split(":", 1)
                k_str = parts[0].strip()
                v_str = parts[1].strip()
                data.weights[k_str] = v_str

    # Extract Decision Rationale Block
    for header in ["[2D Market Regime & Strategy Decision Rationale]", "[Dual Market Regime & Strategy Decision Rationale]"]:
        if header in text:
            idx1 = text.find(header)
            idx2 = text.find("--- Applied Ensemble Strategy Weights", idx1)
            if idx2 != -1:
                data.decision_rationale = text[idx1:idx2].strip()
            else:
                data.decision_rationale = text[idx1:idx1+800].strip()
            break

    # Parse Dual Market Decoupling Info
    m_dec = re.search(r"Dual Market Correlation \(20d\):\s*([-\d.]+)\s*\|\s*Status:\s*(\w+)", text)
    if m_dec:
        data.decoupling_corr = m_dec.group(1).strip()
        data.decoupling_status = m_dec.group(2).strip()

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
        m = re.match(r"\[(\w+)\] Top \d+ Ensemble Picks", l_str)
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
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
        m = re.match(r"Horizon:\s*(\w+)", line)
        if m:
            current_horizon = m.group(1)
            continue
        m = re.match(r"---\s*(.+?)\s+TOP", line)
        if m:
            mkt = m.group(1).replace("S&P ", "SP")
            current_section = RegSection(horizon=current_horizon, market=mkt.strip())
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
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
            continue
        m = re.match(r"^(\d+)\s+(\S+)\s+(.+?)\s+(\w+)\s+(.+?)\s+([-\d.]+)%$", line)
        if m:
            rows.append(SectorRow(
                rank=int(m.group(1)),
                symbol=m.group(2),
                name=m.group(3).strip(),
                market=m.group(4),
                sector=m.group(5).strip(),
                score=m.group(6) + "%"
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
        m = re.match(r"^(\d+)\s+(\S+)\s+(.+?)\s+(\w+)\s+([-\d.nanNaN]+)\s+([-\d.nanNaN]+)\s+([-+\d.nanNaN%]+)\s+([-+\d.nanNaN%]+)$", line)
        if m:
            val_str = m.group(8).strip()
            score_val = val_str if val_str.endswith("%") else val_str + "%"
            rows.append(RimRow(
                rank=int(m.group(1)),
                symbol=m.group(2),
                name=m.group(3).strip(),
                market=m.group(4),
                price=m.group(5),
                intrinsic_value=m.group(6),
                discount=m.group(7),
                score=score_val
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
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
            continue
        # Matches: rank  symbol  name (anything)  market  score%
        m = re.match(r"^(\d+)\s+(\S+)\s+(.+?)\s+(KOSPI|KOSDAQ|SP500|NASDAQ|RUSSELL2000)\s+([-+]?[\d.]+)%$", line)
        if m:
            rows.append(SimpleStrategyRow(
                rank=int(m.group(1)),
                symbol=m.group(2),
                name=m.group(3).strip(),
                market=m.group(4),
                score=m.group(5) + "%",
            ))
    return date, rows


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


def _generate_fallback_portfolio(ensemble: Optional[EnsembleData] = None) -> PortfolioAllocationData:
    data = PortfolioAllocationData(
        date=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
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

        w_arr = calculate_hrp_weights(cov)
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
        m = re.match(r"Current Market Regime Detected:\s*(\w+)", line)
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
            r"^(\d+)\s+(\S+)\s+(.+?)\s+(KOSPI|KOSDAQ|KONEX|SP500|NASDAQ|RUSSELL2000)\s+([-\d.]+%|nan%|NaN%|None%)\s+([-\d.]+%|nan%|NaN%|None%)\s+([-\d.]+%|nan%|NaN%|None%)\s+([\d,]+|\S+)$",
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

    return data

# ─────────────────────────────────────────────
# HTML generation
# ─────────────────────────────────────────────

MARKET_FLAGS = {
    "KOSPI": "🇰🇷",
    "KOSDAQ": "🇰🇷",
    "SP500": "🇺🇸",
    "NASDAQ": "🇺🇸",
    "RUSSELL2000": "🇺🇸",
}

REGIME_INFO = {
    "BULL":              ("🟢 BULL",              "#2ea043"),
    "BEAR":              ("🔴 BEAR",              "#f85149"),
    "SIDEWAYS":          ("🟡 SIDEWAYS",          "#d29922"),
    "BULL_LOW_VOL":      ("🟢 BULL (Low Vol)",    "#2ea043"),
    "BULL_HIGH_VOL":     ("🟢 BULL (High Vol)",   "#3fb950"),
    "BEAR_LOW_VOL":      ("🔴 BEAR (Low Vol)",    "#f85149"),
    "BEAR_HIGH_VOL":     ("🔴 BEAR (High Vol)",   "#da3633"),
    "SIDEWAYS_LOW_VOL":  ("🟡 SIDEWAYS (Low Vol)", "#d29922"),
    "SIDEWAYS_HIGH_VOL": ("🟡 SIDEWAYS (High Vol)","#e3b341"),
}

def safe_float(val: str) -> float:
    try:
        val_clean = val.replace("%", "").strip()
        if val_clean.lower() in ("nan", "none", ""):
            return 0.0
        return float(val_clean)
    except Exception:
        return 0.0

def ret_class(val: str) -> str:
    if "nan" in val.lower() or "none" in val.lower():
        return ""
    try:
        if safe_float(val) >= 0:
            return "pos"
        return "neg"
    except Exception:
        return "neg"


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
                picks.append(f"• {m.market}: *{top1.symbol}* ({top1.name}) | 예상: {top1.expected_return}")
    body = "\n".join(picks) if picks else "추천 종목 없음"
    return f"{header}\n🔥 *Top Picks by Market:*\n{body}\n\n💡 *HRP Portfolio Optimization & Meta-Filtering Applied*"


def make_stock_link(symbol: str, market: str) -> str:
    clean_sym = symbol.strip()
    raw_code = clean_sym.split('.')[0]
    if market in ['KOSPI', 'KOSDAQ']:
        return f'<a href="https://m.stock.naver.com/domestic/stock/{raw_code}/total" target="_blank" class="stock-link">{clean_sym}</a>'
    else:
        return f'<a href="https://finance.yahoo.com/quote/{clean_sym}" target="_blank" class="stock-link">{clean_sym}</a>'


def build_html(
    ensemble: EnsembleData,
    surge_date: str, surge_sections: list[SurgeSection],
    vcp_date: str, vcp_rows: list[VcpRow],
    lag_date: str, follower_rows: list[LeadLagRow], leader_rows: list[LeadLagRow],
    vcp_ml_sections: Optional[list[SurgeSection]] = None,
    reg_sections: Optional[list[RegSection]] = None,
    portfolio_data: Optional[PortfolioAllocationData] = None,
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
    scenario_universe_json: str = "[]",
    backtest_rows_html: str = "",
    backtest_note_html: str = "",
) -> str:
    from datetime import timezone, timedelta
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    def resolve_regime_info(reg_name: str, fallback_label: str) -> tuple[str, str]:
        r = (reg_name or "").strip().upper()
        if r in REGIME_INFO:
            return REGIME_INFO[r]
        elif "BULL" in r:
            return f"🟢 {r}", "#2ea043"
        elif "BEAR" in r:
            return f"🔴 {r}", "#f85149"
        elif "SIDEWAYS" in r:
            return f"🟡 {r}", "#d29922"
        return REGIME_INFO.get(fallback_label, ("🟢 BULL", "#2ea043"))

    us_regime_raw = ensemble.us_regime or ensemble.regime or "BULL_LOW_VOL"
    kr_regime_raw = ensemble.kr_regime or ensemble.regime or "SIDEWAYS_LOW_VOL"

    us_label, us_color = resolve_regime_info(us_regime_raw, "BULL_LOW_VOL")
    kr_label, kr_color = resolve_regime_info(kr_regime_raw, "SIDEWAYS_LOW_VOL")
    report_date = ensemble.date or surge_date or vcp_date or lag_date or "N/A"

    # ── Tab: Ensemble ──
    ensemble_panels = ""
    for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
        mkt_data = next((m for m in ensemble.markets if m.market == mkt), None)
        flag = MARKET_FLAGS.get(mkt, "")
        rows_html = ""
        if mkt_data and mkt_data.rows:
            for r in mkt_data.rows[:20]:
                rc = ret_class(r.expected_return)
                symbol_link = make_stock_link(r.symbol, mkt)
                rows_html += f"""
            <tr>
              <td class="rank">#{r.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{r.name}</td>
              <td class="score">{r.score}</td>
              <td class="{rc}">{r.expected_return}</td>
              <td>{r.reg}</td>
              <td>{r.surge}</td>
              <td>{r.lead_lag}</td>
              <td>{r.vcp_rule}</td>
              <td>{r.vcp_ml}</td>
              <td>{r.lstm}</td>
              <td>{r.stat_arb}</td>
              <td>{r.sector_rotation}</td>
              <td>{r.rim_valuation}</td>
              <td>{r.event_driven}</td>
              <td>{r.mq_factor}</td>
              <td>{r.iv_skew}</td>
              <td>{r.order_flow}</td>
              <td>{r.short_term_reversal}</td>
              <td>{r.arm_factor}</td>
              <td>{r.card_factor}</td>
              <td>{r.latr_factor}</td>
            </tr>"""
        else:
            rows_html = '<tr><td colspan="22" class="empty">데이터 없음</td></tr>'

        ensemble_panels += f"""
    <div class="market-panel" data-market="{mkt}">
      <h3 class="market-title">{flag} {mkt}</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>순위</th><th>종목코드</th><th>종목명</th>
            <th>앙상블</th><th>기대수익</th>
            <th>회귀</th><th>Surge</th><th>L-L</th><th>VCP-R</th><th>VCP-M</th><th>LSTM</th><th>S-Arb</th><th>Sec-R</th><th>RIM</th><th>Event</th><th>MQ</th><th>IV-Sk</th><th>Flow</th><th>Rev</th><th>ARM</th><th>CARD</th><th>LATR</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>"""

    weights_html = ""
    for k, v in ensemble.weights.items():
        weights_html += f'<div class="weight-item"><span class="wk">{k}</span><span class="wv">{v}</span></div>'

    rationale_html = ""
    if ensemble.decision_rationale:
        rationale_html = f"""
    <div class="card rationale-card" style="margin-top: 15px; background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; padding: 15px; border-radius: 8px;">
      <h3 style="color: #38bdf8; margin-bottom: 8px; font-size: 1.1em;">🧠 [2D Regime &amp; Strategy Decision Rationale]</h3>
      <pre style="white-space: pre-wrap; font-family: monospace; font-size: 0.9em; color: #cbd5e1; margin: 0;">{ensemble.decision_rationale}</pre>
    </div>"""

    dec_status = ensemble.decoupling_status or "COUPLED"
    dec_corr = ensemble.decoupling_corr or "1.00"
    dec_class = "neg" if "DECOUPLING" in dec_status else "pos"

    macro_html = f"""
    <div class="macro-grid">
      <div class="macro-item"><span class="ml">🇺🇸/🇰🇷 한·미 동조화 상태</span><span class="mv {dec_class}">{dec_status} (상관: {dec_corr})</span></div>
      <div class="macro-item"><span class="ml">S&amp;P500 20d Ret</span><span class="mv {ret_class(ensemble.sp500_return or '0%')}">{ensemble.sp500_return or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">VIX 공포지수</span><span class="mv">{ensemble.vix or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">USD/KRW 환율</span><span class="mv">{ensemble.usdkrw or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">US 10Y 국채금리</span><span class="mv">{ensemble.us10y or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">KR 10Y 국채금리</span><span class="mv">{ensemble.kr10y or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">WTI 국제유가</span><span class="mv">{ensemble.wti or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">금 (GLD ETF)</span><span class="mv">{ensemble.gold or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">최대허용배분</span><span class="mv">{ensemble.max_allocation or 'N/A'}</span></div>
    </div>"""

    # ── Tab: Portfolio (HRP) ──
    portfolio_data = portfolio_data or _generate_fallback_portfolio(ensemble)
    portfolio_rows_html = ""
    chart_labels = []
    chart_weights = []
    market_weights = {"KOSPI": 0.0, "KOSDAQ": 0.0, "SP500": 0.0, "NASDAQ": 0.0, "RUSSELL2000": 0.0, "CASH": 0.0}

    if portfolio_data and portfolio_data.rows:
        for port_r in portfolio_data.rows:
            rc = ret_class(port_r.expected_return)
            symbol_link = make_stock_link(port_r.symbol, port_r.market)
            portfolio_rows_html += f"""
            <tr>
              <td class="rank">#{port_r.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{port_r.name}</td>
              <td>{MARKET_FLAGS.get(port_r.market, '')} {port_r.market}</td>
              <td class="{rc}">{port_r.expected_return}</td>
              <td>{port_r.volatility}</td>
              <td class="pos">{port_r.weight}</td>
              <td>{port_r.amount}</td>
            </tr>"""
            w_float = safe_float(port_r.weight)
            chart_labels.append(port_r.name)
            chart_weights.append(w_float)
            if port_r.market in market_weights:
                market_weights[port_r.market] += w_float
            else:
                market_weights["SP500"] += w_float

        rem_cash_val = safe_float(portfolio_data.remaining_cash_pct) if portfolio_data.remaining_cash_pct else max(0.0, 100.0 - sum(chart_weights))
        if rem_cash_val > 0:
            market_weights["CASH"] = round(rem_cash_val, 2)
            chart_labels.append("Remaining Cash")
            chart_weights.append(round(rem_cash_val, 2))
    else:
        portfolio_rows_html = '<tr><td colspan="8" class="empty">포트폴리오 배분 데이터 없음</td></tr>'

    # ── Tab: Surge ──
    horizons = sorted(set(s.horizon for s in surge_sections), key=lambda h: int(m.group()) if (m := re.search(r"\d+", h)) else 0) if surge_sections else ["1일", "3일", "5일", "20일"]
    surge_tabs_nav = ""
    surge_tabs_content = ""
    for i, hz in enumerate(horizons):
        active = "active" if i == 0 else ""
        surge_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections = [s for s in surge_sections if s.horizon == hz]
        panels = ""
        for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
            s = next((sec for sec in hz_sections if sec.market == mkt), None)
            flag = MARKET_FLAGS.get(mkt, "")
            rows_html = ""
            if s and s.rows:
                for sr in s.rows:
                    prob = safe_float(sr.probability)
                    bar_w = min(100, int(prob))
                    color = "#2ea043" if prob >= 20 else "#d29922" if prob >= 10 else "#8b949e"
                    symbol_link = make_stock_link(sr.symbol, mkt)
                    rows_html += f"""
              <tr>
                <td class="rank">#{sr.rank}</td>
                <td class="symbol">{symbol_link}</td>
                <td class="name">{sr.name}</td>
                <td>
                  <div class="prob-bar">
                    <div class="prob-fill" style="width:{bar_w}%;background:{color}"></div>
                    <span class="prob-label" style="color:{color}">{sr.probability}</span>
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
        surge_tabs_content += f'<div class="hz-content" data-hz="{hz}" style="display:{display}">{panels}</div>'

    # ── Tab: VCP ──
    vcp_by_market: dict[str, list[VcpRow]] = {}
    for vr in vcp_rows:
        vcp_by_market.setdefault(vr.market, []).append(vr)

    vcp_panels = ""
    for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
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
              <td class="name">{vr.name}</td>
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
    for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
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
              <td class="name">{lr.name}</td>
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
          <td class="name">{ldr.name}</td>
          <td class="{rc}">{ldr.score}</td>
        </tr>"""

    # ── Tab: VCP ML ──
    vcp_ml_sections = vcp_ml_sections or []
    vcp_ml_horizons = sorted(set(s.horizon for s in vcp_ml_sections), key=lambda h: int(m.group()) if (m := re.search(r"\d+", h)) else 0) if vcp_ml_sections else ["1일", "3일", "5일", "20일"]
    vcp_ml_tabs_nav = ""
    vcp_ml_tabs_content = ""
    for i, hz in enumerate(vcp_ml_horizons):
        active = "active" if i == 0 else ""
        vcp_ml_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections = [s for s in vcp_ml_sections if s.horizon == hz]
        panels = ""
        for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
            s = next((sec for sec in hz_sections if sec.market == mkt), None)
            flag = MARKET_FLAGS.get(mkt, "")
            rows_html = ""
            if s and s.rows:
                for vml in s.rows:
                    prob = safe_float(vml.probability)
                    bar_w = min(100, int(prob))
                    color = "#2ea043" if prob >= 20 else "#d29922" if prob >= 10 else "#8b949e"
                    symbol_link = make_stock_link(vml.symbol, mkt)
                    rows_html += f"""
            <tr>
              <td class="rank">#{vml.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{vml.name}</td>
              <td>
                <div class="prob-bar">
                  <div class="prob-fill" style="width:{bar_w}%;background:{color}"></div>
                  <span class="prob-label" style="color:{color}">{vml.probability}</span>
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
        <button class="filter-btn active" onclick="filterMarket(this,'vcp_ml-hz-{hz}')" data-mkt="all">전체</button>
        <button class="filter-btn" onclick="filterMarket(this,'vcp_ml-hz-{hz}')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
        <button class="filter-btn" onclick="filterMarket(this,'vcp_ml-hz-{hz}')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
        <button class="filter-btn" onclick="filterMarket(this,'vcp_ml-hz-{hz}')" data-mkt="SP500">🇺🇸 SP500</button>
        <button class="filter-btn" onclick="filterMarket(this,'vcp_ml-hz-{hz}')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
        <button class="filter-btn" onclick="filterMarket(this,'vcp_ml-hz-{hz}')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
      </div>
      <div id="vcp_ml-hz-{hz}-panels">
        {panels}
      </div>
    </div>"""

    # ── Tab: Regression ──
    reg_sections = reg_sections or []
    reg_horizons = sorted(set(s.horizon for s in reg_sections), key=lambda h: int(m.group()) if (m := re.search(r"\d+", h)) else 0) if reg_sections else ["1d", "5d", "20d", "60d"]
    reg_tabs_nav = ""
    reg_tabs_content = ""
    for i, hz in enumerate(reg_horizons):
        active = "active" if i == 0 else ""
        reg_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections_reg = [s for s in reg_sections if s.horizon == hz]
        panels = ""
        for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
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
              <td class="name">{reg_row.name}</td>
              <td class="{rc}">{reg_row.expected_return}</td>
            </tr>"""
            if not rows_html:
                rows_html = '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'
            panels += f"""
        <div class="market-panel" data-market="{mkt}">
          <h3 class="market-title">{flag} {mkt}</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>순위</th><th>종목코드</th><th>종목명</th><th>예상수익률</th></tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>"""

        display_style = "display: block;" if i == 0 else "display: none;"
        reg_tabs_content += f"""
    <div class="hz-content" data-hz="{hz}" style="{display_style}">
      <div class="filter-bar">
        <button class="filter-btn active" onclick="filterMarket(this,'reg-hz-{hz}')" data-mkt="all">전체</button>
        <button class="filter-btn" onclick="filterMarket(this,'reg-hz-{hz}')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
        <button class="filter-btn" onclick="filterMarket(this,'reg-hz-{hz}')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
        <button class="filter-btn" onclick="filterMarket(this,'reg-hz-{hz}')" data-mkt="SP500">🇺🇸 SP500</button>
        <button class="filter-btn" onclick="filterMarket(this,'reg-hz-{hz}')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
        <button class="filter-btn" onclick="filterMarket(this,'reg-hz-{hz}')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
      </div>
      <div id="reg-hz-{hz}-panels">
        {panels}
      </div>
    </div>"""

    # ── Tab: Stat-Arb ──
    stat_arb_rows_html = ""
    if stat_arb_rows:
        for sa_r in stat_arb_rows:
            z_val = safe_float(sa_r.z_score)
            z_class = "pos" if z_val > 0 else "neg"
            stat_arb_rows_html += f"""
            <tr>
              <td class="symbol"><strong>{sa_r.pair}</strong></td>
              <td class="{z_class}">{sa_r.z_score}</td>
              <td>{sa_r.correlation}</td>
              <td>{sa_r.beta}</td>
              <td><span class="badge">{sa_r.signal}</span></td>
            </tr>"""
    else:
        stat_arb_rows_html = '<tr><td colspan="5" class="empty">조건을 만족하는 공적분 페어가 없습니다</td></tr>'

    # ── Tab: Sector Rotation ──
    sector_panels = ""
    for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
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
              <td class="name">{sec_r.name}</td>
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
    for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
        flag = MARKET_FLAGS.get(mkt, "")
        rows_html = ""
        mkt_rim_rows = [rim_r for rim_r in (rim_rows or []) if rim_r.market == mkt]
        if mkt_rim_rows:
            for rim_r in mkt_rim_rows:
                symbol_link = make_stock_link(rim_r.symbol, mkt)
                disc_class = "pos" if safe_float(rim_r.discount) > 0 else "neg"
                rows_html += f"""
            <tr>
              <td class="rank">#{rim_r.rank}</td>
              <td class="symbol">{symbol_link}</td>
              <td class="name">{rim_r.name}</td>
              <td>{rim_r.price}</td>
              <td class="pos">{rim_r.intrinsic_value}</td>
              <td class="{disc_class}">{rim_r.discount}</td>
              <td class="score">{rim_r.score}</td>
            </tr>"""
        else:
            rows_html = '<tr><td colspan="7" class="empty">데이터 없음</td></tr>'

        rim_panels += f"""
    <div class="market-panel" data-market="{mkt}">
      <h3 class="market-title">{flag} {mkt}</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>순위</th><th>종목코드</th><th>종목명</th><th>현재가</th><th>RIM 적정가(V0)</th><th>안전마진(할인율)</th><th>RIM 스코어</th>
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
    ) -> str:
        panels_html = ""
        for mkt in ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]:
            flag = MARKET_FLAGS.get(mkt, "")
            mkt_rows = [r for r in (rows_list or []) if r.market == mkt]
            rows_html = ""
            if mkt_rows:
                for row in mkt_rows:
                    sym_link = make_stock_link(row.symbol, mkt)
                    score_val = getattr(row, score_attr, row.score)
                    rows_html += f"""
            <tr>
              <td class="rank">#{row.rank}</td>
              <td class="symbol">{sym_link}</td>
              <td class="name">{row.name}</td>
              <td>{MARKET_FLAGS.get(row.market, "")} {row.market}</td>
              <td class="{score_class}">{score_val}</td>
            </tr>"""
            else:
                rows_html = f'<tr><td colspan="5" class="empty">데이터 없음</td></tr>'

            panels_html += f"""
    <div class="market-panel" data-market="{mkt}">
      <h3 class="market-title">{flag} {mkt}</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>순위</th><th>종목코드</th><th>종목명</th><th>시장</th><th>{col_header}</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>"""
        return panels_html

    event_panels = _build_simple_panels(event_rows or [], "event", "이벤트 스코어")
    mq_panels    = _build_simple_panels(mq_rows or [],    "mq",    "MQ 스코어")
    iv_panels    = _build_simple_panels(iv_rows or [],    "iv",    "IV Skew 스코어")
    flow_panels  = _build_simple_panels(flow_rows or [],  "flow",  "수급 스코어")
    reversal_panels = _build_simple_panels(reversal_rows or [], "reversal", "반전 스코어")
    arm_panels    = _build_simple_panels(arm_rows or [],    "arm",    "ARM 스코어")
    card_panels   = _build_simple_panels(card_rows or [],   "card",   "CARD 스코어")
    latr_panels   = _build_simple_panels(latr_rows or [],   "latr",   "LATR 스코어")
    ifs_panels    = _build_simple_panels(ifs_rows or [],    "ifs",    "외인/투신 수급 스코어")

    # JSON strings for Chart.js
    hrp_labels_json = json.dumps(chart_labels, ensure_ascii=False)
    hrp_weights_json = json.dumps(chart_weights)
    mkt_labels_json = json.dumps(list(market_weights.keys()), ensure_ascii=False)
    mkt_weights_json = json.dumps([round(v, 2) for v in market_weights.values()])

    # ── Full HTML ──
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📈 Stock Prediction Dashboard | KRX &amp; SP500</title>
<meta name="description" content="AI 기반 한국·미국 주식 예측 대시보드 — XGBoost 앙상블, Surge 분류기, VCP 패턴, Lead-Lag 전략">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  :root {{
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #21262d;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --green: #2ea043;
    --red: #f85149;
    --yellow: #d29922;
    --blue: #388bfd;
    --accent: #58a6ff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.5; }}
  .stock-link {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
  .stock-link:hover {{ text-decoration: underline; color: #79c0ff; }}

  /* Header */
  .header {{ background: linear-gradient(135deg, #0d1117 0%, #1a2332 50%, #0d1117 100%); border-bottom: 1px solid var(--border); padding: 24px 32px; }}
  .header h1 {{ font-size: 24px; font-weight: 700; background: linear-gradient(90deg, #58a6ff, #3fb950); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
  .header-meta {{ display: flex; gap: 16px; margin-top: 8px; flex-wrap: wrap; align-items: center; }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid; }}
  .badge-date {{ color: var(--muted); border-color: var(--border); }}
  .badge-updated {{ color: var(--muted); border-color: var(--border); font-size: 11px; }}

  /* Macro strip */
  .macro-strip {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 12px 32px; }}
  .macro-grid {{ display: flex; gap: 24px; flex-wrap: wrap; }}
  .macro-item {{ display: flex; gap: 8px; align-items: center; }}
  .ml {{ color: var(--muted); font-size: 12px; }}
  .mv {{ font-weight: 600; font-size: 13px; }}

  /* Tabs */
  .tabs {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; display: flex; gap: 0; overflow-x: auto; }}
  .tab {{ padding: 14px 20px; cursor: pointer; border: none; background: none; color: var(--muted); font-size: 14px; font-weight: 500; border-bottom: 2px solid transparent; transition: all .2s; white-space: nowrap; }}
  .tab:hover {{ color: var(--text); }}
  .tab.active {{ color: var(--accent); border-bottom-color: var(--accent); }}

  /* Content */
  .content {{ padding: 24px 32px; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* Market filter */
  .filter-bar {{ display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
  .filter-btn {{ padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); background: var(--surface); color: var(--muted); cursor: pointer; font-size: 12px; font-weight: 500; transition: all .15s; }}
  .filter-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
  .filter-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

  /* Market panel */
  .market-panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 16px; overflow: hidden; transition: all .2s; }}
  .market-title {{ padding: 12px 16px; font-size: 14px; font-weight: 600; background: var(--surface2); border-bottom: 1px solid var(--border); }}

  /* Table */
  .table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100%; }}
  table {{ width: 100%; border-collapse: collapse; min-width: 550px; }}
  thead th {{ position: sticky; top: 44px; background: var(--surface2); z-index: 10; padding: 10px 12px; text-align: left; font-size: 12px; color: var(--muted); font-weight: 500; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  tbody td {{ padding: 10px 12px; border-bottom: 1px solid #21262d; white-space: nowrap; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover {{ background: #1c2128; }}
  .rank {{ color: var(--muted); font-size: 12px; }}
  .symbol {{ font-family: monospace; font-weight: 600; color: var(--accent); }}
  .name {{ max-width: 180px; overflow: hidden; text-overflow: ellipsis; color: var(--text); }}
  .score {{ font-weight: 600; color: var(--blue); }}
  .pos {{ color: var(--green); font-weight: 600; }}
  .neg {{ color: var(--red); font-weight: 600; }}
  .empty {{ color: var(--muted); text-align: center; padding: 24px; font-style: italic; }}

  /* Prob bar */
  .prob-bar {{ display: flex; align-items: center; gap: 8px; min-width: 140px; }}
  .prob-fill {{ height: 6px; border-radius: 3px; flex-shrink: 0; transition: width .3s; }}
  .prob-label {{ font-weight: 600; font-size: 13px; white-space: nowrap; }}

  /* VCP checks */
  .chk {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin: 1px; }}
  .chk.ok {{ background: #2ea04320; color: var(--green); border: 1px solid #2ea04340; }}
  .chk.no {{ background: #f8514920; color: var(--red); border: 1px solid #f8514940; }}
  .contraction {{ font-size: 12px; color: var(--muted); max-width: 200px; }}

  /* Weights */
  .weights-section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
  .weights-title {{ font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 12px; }}
  .weight-item {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: 12px; }}
  .weight-item:last-child {{ border-bottom: none; }}
  .wk {{ color: var(--text); }}
  .wv {{ font-weight: 700; color: var(--accent); }}

  /* Row 1: Ensemble + Strategy split layout */
  .row1-wrapper {{ display: grid; grid-template-columns: 280px 1fr; gap: 20px; padding: 20px 32px; border-bottom: 1px solid var(--border); }}
  @media (max-width: 1024px) {{ .row1-wrapper {{ grid-template-columns: 1fr; }} }}
  .strategy-sidebar {{ display: flex; flex-direction: column; gap: 0; }}
  .ensemble-main {{ min-width: 0; }}
  .ensemble-main-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }}
  .ensemble-main-title {{ font-size: 15px; font-weight: 700; color: var(--text); }}

  /* Row 2: Individual strategy tabs */
  .row2-wrapper {{ padding: 0; }}
  .strategy-tabs-label {{ padding: 12px 32px 0; font-size: 12px; font-weight: 600; color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; border-top: 1px solid var(--border); }}

  /* Horizon tabs */
  .hz-tabs {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
  .hz-tab {{ padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); background: var(--surface); color: var(--muted); cursor: pointer; font-size: 12px; font-weight: 500; }}
  .hz-tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

  /* Leader section */
  .section-title {{ font-size: 14px; font-weight: 600; color: var(--muted); margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}

  /* Responsive & Mobile Enhancements */
  @media (max-width: 768px) {{
    .header, .macro-strip, .tabs, .content, .row1-wrapper {{ padding-left: 12px; padding-right: 12px; }}
    .header h1 {{ font-size: 18px; }}
    .row1-wrapper {{ grid-template-columns: 1fr; gap: 12px; padding: 12px; }}
    .macro-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
    .tabs {{ position: sticky; top: 0; z-index: 100; background: #161b22ee; backdrop-filter: blur(8px); -webkit-overflow-scrolling: touch; padding: 0 8px; }}
    .tab {{ padding: 10px 14px; font-size: 13px; }}
    thead th, tbody td {{ padding: 8px 6px; font-size: 11px; }}
    .table-wrap {{ -webkit-overflow-scrolling: touch; }}
    .filter-bar {{ overflow-x: auto; flex-wrap: nowrap; padding-bottom: 4px; }}
    .filter-btn {{ flex-shrink: 0; font-size: 11px; padding: 4px 10px; }}
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

  /* Scrollbar */
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
</style>
</head>
<body>

<div class="header">
  <h1>📈 Stock Prediction Dashboard</h1>
  <div class="header-meta">
    <span class="badge" style="color: {us_color}; border-color: {us_color}; background: {us_color}20;">🇺🇸 US: {us_label}</span>
    <span class="badge" style="color: {kr_color}; border-color: {kr_color}; background: {kr_color}20;">🇰🇷 KR: {kr_label}</span>
    <span class="badge badge-date">📅 {report_date}</span>
    <span class="badge badge-updated">🔄 생성: {now_kst}</span>
  </div>
</div>

<div class="macro-strip">
  {macro_html}
</div>

<!-- ══════════════════════════════════════════════════════ -->
<!-- 18대 전략 가이드 아코디언 (사용성 설명 섹션)             -->
<!-- ══════════════════════════════════════════════════════ -->
<div class="content" style="padding-bottom: 0;">
  <div class="strat-guide-card">
    <div class="strat-guide-header" onclick="toggleStratGuide()">
      <div class="strat-guide-title">📖 18대 다변화 전략 핵심 가이드 (Strategy Overview)</div>
      <span id="strat-guide-icon" style="color:var(--accent); font-weight:bold;">▼ 보기</span>
    </div>
    <div id="strat-guide-body" style="display: none;">
      <div class="strat-grid">
        <div class="strat-card-item"><div class="strat-card-name">1. XGBoost 회귀</div><div class="strat-card-desc">1~200일 Horizon별 예상수익률 머신러닝 추정</div></div>
        <div class="strat-card-item"><div class="strat-card-name">2. Surge 분류기</div><div class="strat-card-desc">20% 이상 급등 가능성을 4개 구간별 확률로 예측</div></div>
        <div class="strat-card-item"><div class="strat-card-name">3. Lead-Lag</div><div class="strat-card-desc">업종 지수/대형 선행주 대비 후행 반응 종목 시차 포착</div></div>
        <div class="strat-card-item"><div class="strat-card-name">4. VCP 패턴 (Rule)</div><div class="strat-card-desc">변동성 수축(VCP) + 거래량 감축 규칙 기반 파동 검출</div></div>
        <div class="strat-card-item"><div class="strat-card-name">5. VCP ML</div><div class="strat-card-desc">시장별 특화 XGBoost로 VCP 패턴 성패 확률 수치화</div></div>
        <div class="strat-card-item"><div class="strat-card-name">6. Causal LSTM</div><div class="strat-card-desc">시점 분리 정규화 시계열 딥러닝 종목 모멘텀 추적</div></div>
        <div class="strat-card-item"><div class="strat-card-name">7. Stat-Arb</div><div class="strat-card-desc">공적분 잔차 평균회귀 Z-score 기반 횡보장 차익거래</div></div>
        <div class="strat-card-item"><div class="strat-card-name">8. Sector Rotation</div><div class="strat-card-desc">KRX/GICS 업종 상대모멘텀 및 순환매 수급 스코어링</div></div>
        <div class="strat-card-item"><div class="strat-card-name">9. RIM Valuation</div><div class="strat-card-desc">잔여이익 모델 기반 정밀 가치평가 및 안전마진 측정</div></div>
        <div class="strat-card-item"><div class="strat-card-name">10. Event-Driven</div><div class="strat-card-desc">DART 공시, 실적 서프라이즈, 자사주, 거래량 3배 신호</div></div>
        <div class="strat-card-item"><div class="strat-card-name">11. MQ Factor</div><div class="strat-card-desc">12M-1M 노이즈 제거 모멘텀 + 영업이익률/ROE 퀄리티</div></div>
        <div class="strat-card-item"><div class="strat-card-name">12. Options IV Skew</div><div class="strat-card-desc">yfinance 풋/콜 IV Skew 및 공포 역발상 매수 점수</div></div>
        <div class="strat-card-item"><div class="strat-card-name">13. Order Flow</div><div class="strat-card-desc">외인/기관 순매수 수급 가속도 (MFI) 추적</div></div>
        <div class="strat-card-item"><div class="strat-card-name">14. ST Reversal</div><div class="strat-card-desc">3~5일 연속 과매도/볼린저 하단 이탈 단기 반등 포착</div></div>
        <div class="strat-card-item"><div class="strat-card-name">15. ARM Factor</div><div class="strat-card-desc">증권가 컨센서스(EPS/목표가) 상향 조정 및 실적 서프라이즈</div></div>
        <div class="strat-card-item"><div class="strat-card-name">16. CARD Factor</div><div class="strat-card-desc">주식-원자재-환율 이탈 괴리율 역발상 매수 점수</div></div>
        <div class="strat-card-item"><div class="strat-card-name">17. LATR Factor</div><div class="strat-card-desc">52주 고점 낙폭(DD) + 유동성 서지 + 하방 꼬리위험 반등</div></div>
        <div class="strat-card-item"><div class="strat-card-name">18. Inst &amp; Foreign Sector</div><div class="strat-card-desc">외인/투신 2개월 수급 누적 &amp; 업종 주도주 상관성</div></div>
      </div>
    </div>
  </div>
</div>


<!-- ══════════════════════════════════════════════════════ -->
<!-- Row 1: 상단 코어 시스템 (전략 가중치 + 메인 시스템 탭) -->
<!-- ══════════════════════════════════════════════════════ -->
<nav class="tabs main-system-tabs" style="margin-bottom: 16px; border-bottom: 2px solid var(--border);">
  <button class="tab active" onclick="switchTab(this,'ensemble')">🏆 18대 앙상블 TOP 종목</button>
  <button class="tab" onclick="switchTab(this,'portfolio')">💼 Portfolio (HRP)</button>
  <button class="tab" onclick="switchTab(this,'backtest')">📊 Backtest</button>
  <button class="tab" onclick="switchTab(this,'regime')">🎯 Regime Info</button>
</nav>

<div class="content main-system-content" style="padding:0; margin-bottom: 24px;">
  <!-- ══ 18대 앙상블 TOP 종목 Tab Panel ══ -->
  <div class="tab-panel active" id="panel-ensemble">
    <div class="row1-wrapper">
      <!-- 좌: 전략 사이드바 -->
      <div class="strategy-sidebar">
        <div class="weights-section">
          <div class="weights-title">⚙️ 전략 가중치 (18 Strategies)</div>
          {weights_html if weights_html else '<span style="color:var(--muted)">데이터 없음</span>'}
        </div>
        {rationale_html}
      </div>

      <!-- 우: 앙상블 종목 결과 -->
      <div class="ensemble-main">
        <div class="ensemble-main-header">
          <span class="ensemble-main-title">🏆 18대 앙상블 TOP 종목 리스트</span>
          <div class="filter-bar" id="filter-ensemble" style="margin:0">
            <button class="filter-btn active" onclick="filterMarket(this,'ensemble')" data-mkt="all">전체</button>
            <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
            <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
            <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="SP500">🇺🇸 SP500</button>
            <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
            <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
          </div>
        </div>
        <div id="ensemble-panels">
        {ensemble_panels}
        </div>
      </div>
    </div>
  </div>

  <!-- ══ Portfolio (HRP) Tab Panel ══ -->
  <div class="tab-panel" id="panel-portfolio">
    <div class="macro-strip" style="margin-bottom: 20px; border-radius: 8px;">
      <div class="macro-grid">
        <div class="macro-item"><span class="ml">총 자본금</span><span class="mv">{portfolio_data.total_capital or '1,000,000,000 KRW/USD'}</span></div>
        <div class="macro-item"><span class="ml">투자기간</span><span class="mv">{portfolio_data.target_horizon or '20d'}</span></div>
        <div class="macro-item"><span class="ml">배분 비중</span><span class="mv pos">{portfolio_data.allocated_capital_pct or '50.0%'}</span></div>
        <div class="macro-item"><span class="ml">현금 잔고</span><span class="mv">{portfolio_data.remaining_cash_pct or '50.0%'}</span></div>
      </div>
    </div>

    <div class="charts-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 24px;">
      <div class="chart-card" style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px;">
        <h3 style="font-size: 14px; font-weight: 600; color: var(--muted); margin-bottom: 12px;">📊 HRP Allocation Weights</h3>
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

    <div class="market-panel">
      <h3 class="market-title">💼 HRP Risk Parity Position Allocation</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>순위</th><th>종목코드</th><th>종목명</th><th>시장</th>
              <th>기대수익</th><th>변동성</th><th>비중</th><th>투자금액</th>
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
    <div class="weights-section">
      <div class="weights-title">📊 18대 전략 롤링 백테스트 성과 (Sharpe &amp; MDD)</div>
      <div style="font-size: 12px; color: var(--muted); margin-bottom: 12px; line-height: 1.5;">
        📌 <strong>검증 방식</strong>: 매일 저장된 앙상블 예측의 실현 수익률(outcome) 기반 실적 측정 (20d Holding)<br>
        {backtest_note_html}
        📌 <strong>미시구조 거래비용 반영</strong>: 거래세 (STT 0.18%), SEC fee, 호가 슬리피지 및 마켓 임팩트 차감 후 순수익률 기준
      </div>
      <div class="table-wrap">
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
      <div class="weights-title">🎯 현재 감지된 시장 레짐 및 가중치</div>
      <div class="macro-grid" style="margin-bottom: 12px;">
        <div class="macro-item"><span class="ml">US 레짐</span><span class="mv badge" style="color:{us_color};border-color:{us_color};background:{us_color}20;">🇺🇸 {us_label}</span></div>
        <div class="macro-item"><span class="ml">KR 레짐</span><span class="mv badge" style="color:{kr_color};border-color:{kr_color};background:{kr_color}20;">🇰🇷 {kr_label}</span></div>
        <div class="macro-item"><span class="ml">허용 배분</span><span class="mv">{ensemble.max_allocation or '50.0%'}</span></div>
      </div>
      {weights_html}
    </div>

    <div class="section-title">🌐 2D Market Regime Dynamic Matrix (Direction × Volatility - 18 Strategies)</div>
    <div class="market-panel">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>2D 레짐</th><th>시장 특성</th><th>Reg</th><th>Surge</th><th>L-L</th><th>VCP-R</th><th>VCP-M</th><th>LSTM</th><th>S-Arb</th><th>Sec-R</th><th>RIM</th><th>Event</th><th>MQ</th><th>IV-Sk</th><th>Flow</th><th>Rev</th><th>ARM</th><th>CARD</th><th>LATR</th><th>InstFor</th><th>전략 핵심 목표</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>🟢 <strong>BULL_LOW_VOL</strong></td>
              <td>고수익 + 저변동성</td>
              <td>5%</td><td>15%</td><td>4%</td><td>4%</td><td>12%</td><td>10%</td><td>4%</td><td>10%</td><td>6%</td><td>10%</td><td>10%</td><td>3%</td><td>5%</td><td>2%</td><td>3%</td><td>3%</td><td>3%</td>
              <td>공격적 돌파 &amp; 모멘텀 추종</td>
            </tr>
            <tr>
              <td>🟢 <strong>BULL_HIGH_VOL</strong></td>
              <td>고수익 + 고변동성</td>
              <td>4%</td><td>17%</td><td>4%</td><td>4%</td><td>12%</td><td>10%</td><td>4%</td><td>7%</td><td>6%</td><td>10%</td><td>10%</td><td>3%</td><td>5%</td><td>4%</td><td>3%</td><td>3%</td><td>3%</td>
              <td>신중한 모멘텀 &amp; 리스크 관리</td>
            </tr>
            <tr style="background: #388bfd15;">
              <td>🟡 <strong>SIDEWAYS_LOW_VOL</strong></td>
              <td>횡보 + 저변동성 (현재)</td>
              <td>10%</td><td>4%</td><td>6%</td><td>4%</td><td>7%</td><td>10%</td><td>12%</td><td>8%</td><td>10%</td><td>7%</td><td>8%</td><td>4%</td><td>5%</td><td>5%</td><td>4%</td><td>4%</td><td>4%</td>
              <td>섹터 순환매 &amp; 내재가치/Stat-Arb</td>
            </tr>
            <tr>
              <td>🟡 <strong>SIDEWAYS_HIGH_VOL</strong></td>
              <td>횡보 + 고변동성</td>
              <td>10%</td><td>4%</td><td>6%</td><td>4%</td><td>7%</td><td>7%</td><td>15%</td><td>8%</td><td>10%</td><td>7%</td><td>8%</td><td>4%</td><td>5%</td><td>5%</td><td>4%</td><td>4%</td><td>4%</td>
              <td>잔차 평균회귀 &amp; 가치주 차익거래</td>
            </tr>
            <tr>
              <td>🔴 <strong>BEAR_LOW_VOL</strong></td>
              <td>음수 수익 + 저변동성</td>
              <td>20%</td><td>3%</td><td>3%</td><td>3%</td><td>3%</td><td>4%</td><td>12%</td><td>7%</td><td>15%</td><td>5%</td><td>10%</td><td>5%</td><td>4%</td><td>6%</td><td>2%</td><td>2%</td><td>2%</td>
              <td>방어적 펀더멘탈 &amp; RIM 가치 안전마진</td>
            </tr>
            <tr>
              <td>🔴 <strong>BEAR_HIGH_VOL</strong></td>
              <td>음수 수익 + 고변동성</td>
              <td>22%</td><td>0%</td><td>3%</td><td>3%</td><td>3%</td><td>4%</td><td>15%</td><td>4%</td><td>15%</td><td>5%</td><td>10%</td><td>5%</td><td>4%</td><td>7%</td><td>1%</td><td>1%</td><td>1%</td>
              <td>최고 수준의 자본 보존 (현금 70%)</td>
            </tr>
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
        <li><strong style="color:var(--text)">Kelly Optimization &amp; HRP:</strong> 18-Strategy Ensemble scores mapped to expected returns with maximum allocation constraints per regime.</li>
      </ul>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ -->
<!-- Row 2: 개별 전략 상세 탭                               -->
<!-- ══════════════════════════════════════════════════════ -->
<div class="row2-wrapper">
<div class="strategy-tabs-label">📊 개별 전략 상세 (Individual Strategies)</div>

<nav class="tabs">
  <button class="tab active" onclick="switchTab(this,'scenario')">🔮 Scenario Simulator (시나리오 시뮬레이터)</button>
  <button class="tab" onclick="switchTab(this,'sector')">🔄 Sector Rotation (섹터 로테이션)</button>
  <button class="tab" onclick="switchTab(this,'surge')">⚡ Surge</button>
  <button class="tab" onclick="switchTab(this,'vcpml')">🤖 VCP ML</button>
  <button class="tab" onclick="switchTab(this,'regression')">📈 Regression</button>
  <button class="tab" onclick="switchTab(this,'vcp')">📐 VCP Rule</button>
  <button class="tab" onclick="switchTab(this,'leadlag')">🔗 Lead-Lag</button>
  <button class="tab" onclick="switchTab(this,'stat-arb')">⚖️ Stat-Arb</button>
  <button class="tab" onclick="switchTab(this,'rim')">💎 RIM Valuation</button>
  <button class="tab" onclick="switchTab(this,'event')">📰 Event-Driven</button>
  <button class="tab" onclick="switchTab(this,'mq')">🔬 MQ Factor</button>
  <button class="tab" onclick="switchTab(this,'iv')">📊 IV Skew</button>
  <button class="tab" onclick="switchTab(this,'flow')">🌊 Order Flow</button>
  <button class="tab" onclick="switchTab(this,'reversal')">↩️ ST Reversal</button>
  <button class="tab" onclick="switchTab(this,'arm')">📈 ARM</button>
  <button class="tab" onclick="switchTab(this,'card')">🌐 CARD</button>
  <button class="tab" onclick="switchTab(this,'latr')">⚡ LATR</button>
  <button class="tab" onclick="switchTab(this,'ifs')">🏛️ 외인/투신 수급</button>
</nav>

<div class="content row2-content" style="padding: 24px 32px;">
  <!-- ══ Surge Tab ══ -->
  <div class="tab-panel" id="panel-surge">
    <div class="hz-tabs">{surge_tabs_nav}</div>
    {surge_tabs_content}
  </div>

  <!-- ══ VCP Tab ══ -->
  <div class="tab-panel" id="panel-vcp">
    <div class="filter-bar" id="filter-vcp">
      <button class="filter-btn active" onclick="filterMarket(this,'vcp')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'vcp')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'vcp')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'vcp')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'vcp')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'vcp')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="vcp-panels">
    {vcp_panels}
    </div>
  </div>

  <!-- ══ Lead-Lag Tab ══ -->
  <div class="tab-panel" id="panel-leadlag">
    <div class="filter-bar" id="filter-leadlag">
      <button class="filter-btn active" onclick="filterMarket(this,'leadlag')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'leadlag')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'leadlag')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'leadlag')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'leadlag')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'leadlag')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
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

  <!-- ══ Stat-Arb Tab ══ -->
  <div class="tab-panel" id="panel-stat-arb">
    <div class="section-title">⚖️ Cointegrated Stat-Arb Pairs &amp; Mean-Reversion Signals (Strategy 7)</div>
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
      <button class="filter-btn active" onclick="filterMarket(this,'sector')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'sector')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'sector')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'sector')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'sector')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'sector')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="sector-panels">
    {sector_panels}
    </div>
  </div>

  <!-- ══ RIM Valuation Tab ══ -->
  <div class="tab-panel" id="panel-rim">
    <div class="filter-bar" id="filter-rim">
      <button class="filter-btn active" onclick="filterMarket(this,'rim')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'rim')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'rim')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'rim')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'rim')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'rim')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="rim-panels">
    {rim_panels}
    </div>
  </div>

  <!-- ══ Event-Driven Tab ══ -->
  <div class="tab-panel" id="panel-event">
    <div class="filter-bar" id="filter-event">
      <button class="filter-btn active" onclick="filterMarket(this,'event')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'event')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'event')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'event')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'event')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'event')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="event-panels">
    {event_panels}
    </div>
  </div>

  <!-- ══ MQ Factor Tab ══ -->
  <div class="tab-panel" id="panel-mq">
    <div class="filter-bar" id="filter-mq">
      <button class="filter-btn active" onclick="filterMarket(this,'mq')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'mq')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'mq')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'mq')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'mq')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'mq')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="mq-panels">
    {mq_panels}
    </div>
  </div>

  <!-- ══ IV Skew Tab ══ -->
  <div class="tab-panel" id="panel-iv">
    <div class="filter-bar" id="filter-iv">
      <button class="filter-btn active" onclick="filterMarket(this,'iv')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'iv')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'iv')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'iv')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'iv')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'iv')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="iv-panels">
    {iv_panels}
    </div>
  </div>

  <!-- ══ Order Flow Tab ══ -->
  <div class="tab-panel" id="panel-flow">
    <div class="filter-bar" id="filter-flow">
      <button class="filter-btn active" onclick="filterMarket(this,'flow')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'flow')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'flow')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'flow')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'flow')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'flow')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="flow-panels">
    {flow_panels}
    </div>
  </div>

  <!-- ══ Short-Term Reversal Tab ══ -->
  <div class="tab-panel" id="panel-reversal">
    <div class="filter-bar" id="filter-reversal">
      <button class="filter-btn active" onclick="filterMarket(this,'reversal')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'reversal')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'reversal')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'reversal')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'reversal')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'reversal')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="reversal-panels">
    {reversal_panels}
    </div>
  </div>

  <!-- ══ ARM Factor Tab ══ -->
  <div class="tab-panel" id="panel-arm">
    <div class="filter-bar" id="filter-arm">
      <button class="filter-btn active" onclick="filterMarket(this,'arm')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'arm')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'arm')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'arm')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'arm')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'arm')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="arm-panels">
    {arm_panels}
    </div>
  </div>

  <!-- ══ CARD Factor Tab ══ -->
  <div class="tab-panel" id="panel-card">
    <div class="filter-bar" id="filter-card">
      <button class="filter-btn active" onclick="filterMarket(this,'card')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'card')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'card')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'card')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'card')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'card')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="card-panels">
    {card_panels}
    </div>
  </div>

  <!-- ══ LATR Factor Tab ══ -->
  <div class="tab-panel" id="panel-latr">
    <div class="filter-bar" id="filter-latr">
      <button class="filter-btn active" onclick="filterMarket(this,'latr')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'latr')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'latr')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'latr')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'latr')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'latr')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="latr-panels">
    {latr_panels}
    </div>
  </div>

  <!-- ══ Inst & Foreign Sector Tab ══ -->
  <div class="tab-panel" id="panel-ifs">
    <div class="filter-bar" id="filter-ifs">
      <button class="filter-btn active" onclick="filterMarket(this,'ifs')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'ifs')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'ifs')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'ifs')" data-mkt="SP500">🇺🇸 SP500</button>
      <button class="filter-btn" onclick="filterMarket(this,'ifs')" data-mkt="NASDAQ">🇺🇸 NASDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'ifs')" data-mkt="RUSSELL2000">🇺🇸 RUSSELL2000</button>
    </div>
    <div id="ifs-panels">
    {ifs_panels}
    </div>
  </div>

  <!-- ══ Scenario Simulator Tab ══ -->
  <div class="tab-panel active" id="panel-scenario">
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

  <!-- ══ VCP ML Tab ══ -->
  <div class="tab-panel" id="panel-vcpml">
    <div class="hz-tabs">{vcp_ml_tabs_nav}</div>
    {vcp_ml_tabs_content}
  </div>

  <!-- ══ Regression Tab ══ -->
  <div class="tab-panel" id="panel-regression">
    <div class="hz-tabs">{reg_tabs_nav}</div>
    {reg_tabs_content}
  </div>

</div><!-- end .content -->
</div><!-- end .row2-wrapper -->

<script>
function toggleStratGuide() {{
  const body = document.getElementById('strat-guide-body');
  const icon = document.getElementById('strat-guide-icon');
  if (body.style.display === 'none') {{
    body.style.display = 'block';
    icon.textContent = '▲ 접기';
  }} else {{
    body.style.display = 'none';
    icon.textContent = '▼ 보기';
  }}
}}

function switchTab(btn, id) {{
  const nav = btn.closest('nav');
  if (nav) nav.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');

  // Determine container (main-system-content or row2-content or document)
  let container = nav ? nav.nextElementSibling : null;
  if (!container || !container.classList.contains('content')) {{
    container = document;
  }}
  container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const panel = document.getElementById('panel-' + id);
  if (panel) panel.classList.add('active');
}}

function filterMarket(btn, group) {{
  const bar = btn.closest('.filter-bar');
  bar.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const mkt = btn.dataset.mkt;
  const panels = document.querySelectorAll('#' + group + '-panels .market-panel');
  panels.forEach(p => {{
    const pm = p.dataset.market;
    p.style.display = (mkt === 'all' || !pm || pm === mkt) ? 'block' : 'none';
  }});
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
          label: 'Market Weight (%)',
          data: mktWeights,
          backgroundColor: ['#2ea043', '#388bfd', '#d29922', '#58a6ff', '#8b949e']
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

    const secValues = {{ semi: sSemi, auto: sAuto, energy: sEnergy, fin: sFin, staples: sStaples }};
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

    const mktFlags = {{ KOSPI: '🇰🇷', KOSDAQ: '🇰🇷', SP500: '🇺🇸', NASDAQ: '🇺🇸', RUSSELL2000: '🇺🇸' }};

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

  // Initial trigger
  updateScenarioSim();
}});
</script>
</body>
</html>
"""


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

    # Build stock universe for Scenario Simulator (TOP stocks per market)
    scen_universe = []
    for m in ensemble.markets:
        mkt = m.market
        for r in m.rows[:50]:
            # Determine sector elasticity key and GICS normalized name
            raw_sec = getattr(r, 'sector_rotation', 'General')
            gics = "Consumer Staples"
            key = "staples"
            elas = {"fx": -0.4, "wti": -0.5, "rate": 0.1, "vix": 0.3}

            name_lower = r.name.lower()
            if any(k in name_lower for k in ["전자", "하이닉스", "반도체", "samsung", "sk", "nvda", "amd", "apple", "msft", "it"]):
                gics = "Information Technology"
                key = "semi"
                elas = {"fx": 0.6, "wti": -0.2, "rate": -0.4, "vix": -0.3}
            elif any(k in name_lower for k in ["자동차", "현대", "기아", "모비스", "이차전지", "에코프로", "lg에너지", "tsla"]):
                gics = "Consumer Discretionary"
                key = "auto"
                elas = {"fx": 0.4, "wti": -0.3, "rate": -0.3, "vix": -0.4}
            elif any(k in name_lower for k in ["화학", "s-oil", "oil", "에너지", "포스코", "posco", "철강", "xom", "cvx"]):
                gics = "Energy/Materials"
                key = "energy"
                elas = {"fx": 0.2, "wti": 0.7, "rate": 0.1, "vix": -0.2}
            elif any(k in name_lower for k in ["금융", "은행", "증권", "보험", "kb", "신한", "하나", "jpm", "bac"]):
                gics = "Financials"
                key = "fin"
                elas = {"fx": -0.2, "wti": 0.1, "rate": 0.7, "vix": -0.2}

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

    scenario_universe_json = json.dumps(scen_universe, ensure_ascii=False)

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

    html = build_html(
        ensemble,
        surge_date, surge_sections,
        vcp_date, vcp_rows,
        lag_date, follower_rows, leader_rows,
        vcp_ml_sections, reg_sections,
        portfolio_data,
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
        scenario_universe_json,
        backtest_rows_html,
        backtest_note_html,
    )


    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"[generate_report] Dashboard written to: {out_path.resolve()} ({size_kb} KB)")


if __name__ == "__main__":
    main()
