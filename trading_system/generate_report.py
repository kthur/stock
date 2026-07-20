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
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

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
    reg: str
    surge: str
    lead_lag: str
    vcp: str

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
    weights: dict = field(default_factory=dict)
    markets: list[EnsembleMarket] = field(default_factory=list)

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
        m = re.match(r"Current Market Regime Detected:\s*(\w+)\s*\(Code:\s*(\d+)\)", line)
        if m:
            data.regime = m.group(1)
            data.regime_code = int(m.group(2))
        m = re.match(r"Maximum Total Allocation Allowed:\s*(.+)", line)
        if m:
            data.max_allocation = m.group(1).strip()
        m = re.match(r"S&P 500 \(20d Rolling Mean Return\)\s*:\s*(.+)", line)
        if m:
            data.sp500_return = m.group(1).strip()
        m = re.match(r"VIX Index.*:\s*(.+)", line)
        if m:
            data.vix = m.group(1).strip()
        m = re.match(r"US 10Y Bond Yield.*:\s*(.+)", line)
        if m:
            data.us10y = m.group(1).strip()
        m = re.match(r"(XGBoost Regression|Surge Classifier|Lead-Lag|VCP Machine)\w*.*:\s*([\d.]+%)", line)
        if m:
            data.weights[m.group(1)] = m.group(2)

    # Parse market sections
    current_market = None
    in_data = False

    for line in text.splitlines():
        m = re.match(r"\[(\w+)\] Top \d+ Ensemble Picks", line.strip())
        if m:
            current_market = EnsembleMarket(market=m.group(1))
            data.markets.append(current_market)
            in_data = False
            continue
        if current_market and re.match(r"^-{3,}", line.strip()):
            in_data = True
            continue
        if in_data and current_market:
            # Pattern: "1    005930    Samsung Electronic    56.9%    11.4%    80%    10%    0%    9%"
            m = re.match(
                r"(\d+)\s+(\S+)\s+(.+?)\s{2,}([\d.]+%)\s+([-+]?[\d.]+%)\s+([\d.]+%)\s+([\d.]+%)\s+([\d.]+%)\s+([\d.]+%)",
                line.strip()
            )
            if m:
                current_market.rows.append(EnsembleRow(
                    rank=int(m.group(1)),
                    symbol=m.group(2),
                    name=m.group(3).strip(),
                    score=m.group(4),
                    expected_return=m.group(5),
                    reg=m.group(6),
                    surge=m.group(7),
                    lead_lag=m.group(8),
                    vcp=m.group(9),
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
        # "[1일] KOSPI Top 20 Surge Candidates"
        m = re.match(r"\[(\d+일)\]\s+(\w+)\s+Top", line)
        if m:
            current = SurgeSection(horizon=m.group(1), market=m.group(2))
            sections.append(current)
            continue
        if current:
            # "  1. [KOSPI] 005930 (Samsung Electronics): 60.7%"
            m = re.match(r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+?)\):\s*([\d.]+%)", line)
            if m:
                current.rows.append(SurgeRow(
                    rank=int(m.group(1)),
                    market=m.group(2),
                    symbol=m.group(3),
                    name=m.group(4),
                    probability=m.group(5),
                ))
    return date, sections


def parse_vcp(text: str) -> tuple[str, list[VcpRow]]:
    if not text:
        return "", []
    date = ""
    rows: list[VcpRow] = []
    current_symbol = None
    current_market = None

    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"Date:\s*(.+)", line)
        if m:
            date = m.group(1).strip()
        # "  1. [KOSPI] 025890 (한국주강)"
        m = re.match(r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+?)\)", line)
        if m:
            rank = int(m.group(1))
            current_market = m.group(2)
            current_symbol = m.group(3)
            current_name = m.group(4)
            rows.append(VcpRow(
                rank=rank, market=current_market,
                symbol=current_symbol, name=current_name,
                score="", current_range="", contraction="",
                ma50=False, ma200=False, near_high=False, vol_declining=False
            ))
            continue
        if rows:
            # "Score: 100/100 | Current range: 2.5% | Contraction: 2.5% > ..."
            m = re.match(r"Score:\s*([\d/]+)\s*\|\s*Current range:\s*([\d.]+%)\s*\|\s*Contraction:\s*(.+)", line)
            if m:
                rows[-1].score = m.group(1)
                rows[-1].current_range = m.group(2)
                rows[-1].contraction = m.group(3).strip()
            # "Above MA50: ✓ | Above MA200: ✗ | Near high: ✓ | Volume declining: ✓"
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
        # "  1. [KOSPI] 448730 (삼성FN리츠): 1.60%" or "  1. [SP500] LHX (L3Harris): 0.78%"
        m = re.match(r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+?)\):\s*([-+]?[\d.]+\s*%)", line)
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
        # "  1. 042520 (한스바이오메드): +8.85%"  (no [MARKET] bracket for leaders)
        m = re.match(r"(\d+)\.\s+(\S+)\s+\((.+?)\):\s*([-+]?[\d.]+\s*%)", line)
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
        m = re.match(r"\[(\d+일)\]\s+(\w+)\s+(TOP|Top)", line)
        if m:
            current = SurgeSection(horizon=m.group(1), market=m.group(2))
            sections.append(current)
            continue
        if current:
            m = re.match(r"(\d+)\.\s+\[(\w+)\]\s+(\S+)\s+\((.+?)\):\s*([\d.]+%)", line)
            if m:
                current.rows.append(SurgeRow(
                    rank=int(m.group(1)),
                    market=m.group(2),
                    symbol=m.group(3),
                    name=m.group(4),
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
            m = re.match(r"(\d+)\.\s+(\S+)\s+\((.+?)\):\s*([-+]?[\d.]+%)", line)
            if m:
                current_section.rows.append(RegRow(
                    rank=int(m.group(1)),
                    symbol=m.group(2),
                    name=m.group(3),
                    expected_return=m.group(4)
                ))
    return date, sections

# ─────────────────────────────────────────────
# HTML generation
# ─────────────────────────────────────────────

MARKET_FLAGS = {
    "KOSPI": "🇰🇷",
    "KOSDAQ": "🇰🇷",
    "KONEX": "🇰🇷",
    "SP500": "🇺🇸",
}

REGIME_INFO = {
    "BULL":  ("🟢 BULL",  "#2ea043"),
    "BEAR":  ("🔴 BEAR",  "#f85149"),
    "SIDEWAYS": ("🟡 SIDEWAYS", "#d29922"),
}

def ret_class(val: str) -> str:
    val = val.strip().lstrip("+")
    try:
        if float(val.rstrip("%")) >= 0:
            return "pos"
    except ValueError:
        pass
    return "neg"


def build_html(
    ensemble: EnsembleData,
    surge_date: str, surge_sections: list[SurgeSection],
    vcp_date: str, vcp_rows: list[VcpRow],
    lag_date: str, follower_rows: list[LeadLagRow], leader_rows: list[LeadLagRow],
    vcp_ml_sections: list[SurgeSection] = None,
    reg_sections: list[RegSection] = None,
) -> str:
    now_kst = datetime.utcnow().strftime("%Y-%m-%d %H:%M") + " UTC"
    regime_label, regime_color = REGIME_INFO.get(ensemble.regime, (ensemble.regime, "#8b949e"))
    report_date = ensemble.date or surge_date or vcp_date or lag_date or "N/A"

    # ── Tab: Ensemble ──
    ensemble_panels = ""
    for mkt in ["KOSPI", "KOSDAQ", "KONEX", "SP500"]:
        mkt_data = next((m for m in ensemble.markets if m.market == mkt), None)
        flag = MARKET_FLAGS.get(mkt, "")
        rows_html = ""
        if mkt_data and mkt_data.rows:
            for r in mkt_data.rows:
                rc = ret_class(r.expected_return)
                rows_html += f"""
            <tr>
              <td class="rank">#{r.rank}</td>
              <td class="symbol">{r.symbol}</td>
              <td class="name">{r.name}</td>
              <td class="score">{r.score}</td>
              <td class="{rc}">{r.expected_return}</td>
              <td>{r.reg}</td>
              <td>{r.surge}</td>
              <td>{r.lead_lag}</td>
              <td>{r.vcp}</td>
            </tr>"""
        else:
            rows_html = '<tr><td colspan="9" class="empty">데이터 없음</td></tr>'

        ensemble_panels += f"""
    <div class="market-panel" data-market="{mkt}">
      <h3 class="market-title">{flag} {mkt}</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>순위</th><th>종목코드</th><th>종목명</th>
            <th>앙상블</th><th>기대수익</th>
            <th>회귀</th><th>Surge</th><th>L-L</th><th>VCP</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>"""

    weights_html = ""
    for k, v in ensemble.weights.items():
        weights_html += f'<div class="weight-item"><span class="wk">{k}</span><span class="wv">{v}</span></div>'

    macro_html = f"""
    <div class="macro-grid">
      <div class="macro-item"><span class="ml">S&amp;P500 20d Ret</span><span class="mv {ret_class(ensemble.sp500_return or '0%')}">{ensemble.sp500_return or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">VIX 변화</span><span class="mv">{ensemble.vix or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">US 10Y</span><span class="mv">{ensemble.us10y or 'N/A'}</span></div>
      <div class="macro-item"><span class="ml">최대허용배분</span><span class="mv">{ensemble.max_allocation or 'N/A'}</span></div>
    </div>"""

    # ── Tab: Surge ──
    # Group by horizon
    horizons = sorted(set(s.horizon for s in surge_sections), key=lambda h: int(re.search(r"\d+", h).group()))
    surge_tabs_nav = ""
    surge_tabs_content = ""
    for i, hz in enumerate(horizons):
        active = "active" if i == 0 else ""
        surge_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections = [s for s in surge_sections if s.horizon == hz]
        panels = ""
        for s in hz_sections:
            flag = MARKET_FLAGS.get(s.market, "")
            rows_html = ""
            for r in s.rows:
                prob = float(r.probability.rstrip("%"))
                bar_w = min(100, int(prob))
                color = "#2ea043" if prob >= 20 else "#d29922" if prob >= 10 else "#8b949e"
                rows_html += f"""
              <tr>
                <td class="rank">#{r.rank}</td>
                <td class="symbol">{r.symbol}</td>
                <td class="name">{r.name}</td>
                <td>
                  <div class="prob-bar">
                    <div class="prob-fill" style="width:{bar_w}%;background:{color}"></div>
                    <span class="prob-label" style="color:{color}">{r.probability}</span>
                  </div>
                </td>
              </tr>"""
            if not rows_html:
                rows_html = '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'
            panels += f"""
          <div class="market-panel">
            <h3 class="market-title">{flag} {s.market}</h3>
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
    for r in vcp_rows:
        vcp_by_market.setdefault(r.market, []).append(r)

    vcp_panels = ""
    for mkt in ["KOSPI", "KOSDAQ", "KONEX", "SP500"]:
        flag = MARKET_FLAGS.get(mkt, "")
        rows = vcp_by_market.get(mkt, [])
        rows_html = ""
        for r in rows:
            checks = [
                f'<span class="chk {"ok" if r.ma50 else "no"}">MA50</span>',
                f'<span class="chk {"ok" if r.ma200 else "no"}">MA200</span>',
                f'<span class="chk {"ok" if r.near_high else "no"}">고점근접</span>',
                f'<span class="chk {"ok" if r.vol_declining else "no"}">거래량↓</span>',
            ]
            score_val = int(r.score.split("/")[0]) if r.score else 0
            score_color = "#2ea043" if score_val >= 90 else "#d29922" if score_val >= 70 else "#8b949e"
            rows_html += f"""
            <tr>
              <td class="rank">#{r.rank}</td>
              <td class="symbol">{r.symbol}</td>
              <td class="name">{r.name}</td>
              <td><span style="color:{score_color};font-weight:600">{r.score}</span></td>
              <td>{r.current_range}</td>
              <td class="contraction">{r.contraction}</td>
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
    for r in follower_rows:
        lag_by_market.setdefault(r.market, []).append(r)

    lag_panels = ""
    for mkt in ["KOSPI", "KOSDAQ", "KONEX", "SP500"]:
        flag = MARKET_FLAGS.get(mkt, "")
        rows = lag_by_market.get(mkt, [])
        rows_html = ""
        for r in rows:
            rc = ret_class(r.score)
            rows_html += f"""
            <tr>
              <td class="rank">#{r.rank}</td>
              <td class="symbol">{r.symbol}</td>
              <td class="name">{r.name}</td>
              <td class="{rc}">{r.score}</td>
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
    for r in leader_rows[:10]:
        rc = ret_class(r.score)
        leader_rows_html += f"""
        <tr>
          <td class="rank">#{r.rank}</td>
          <td class="symbol">{r.symbol}</td>
          <td class="name">{r.name}</td>
          <td class="{rc}">{r.score}</td>
        </tr>"""

    # ── Tab: VCP ML ──
    vcp_ml_sections = vcp_ml_sections or []
    vcp_ml_horizons = sorted(set(s.horizon for s in vcp_ml_sections), key=lambda h: int(re.search(r"\d+", h).group())) if vcp_ml_sections else []
    vcp_ml_tabs_nav = ""
    vcp_ml_tabs_content = ""
    for i, hz in enumerate(vcp_ml_horizons):
        active = "active" if i == 0 else ""
        vcp_ml_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections = [s for s in vcp_ml_sections if s.horizon == hz]
        panels = ""
        for s in hz_sections:
            flag = MARKET_FLAGS.get(s.market, "")
            rows_html = ""
            for r in s.rows:
                prob = float(r.probability.rstrip("%"))
                bar_w = min(100, int(prob))
                color = "#2ea043" if prob >= 20 else "#d29922" if prob >= 10 else "#8b949e"
                rows_html += f"""
            <tr>
              <td class="rank">#{r.rank}</td>
              <td class="symbol">{r.symbol}</td>
              <td class="name">{r.name}</td>
              <td>
                <div class="prob-bar">
                  <div class="prob-fill" style="width:{bar_w}%;background:{color}"></div>
                  <span class="prob-label" style="color:{color}">{r.probability}</span>
                </div>
              </td>
            </tr>"""
            if not rows_html:
                rows_html = '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'
            panels += f"""
        <div class="market-panel" data-market="{s.market}">
          <h3 class="market-title">{flag} {s.market}</h3>
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
        <button class="filter-btn" onclick="filterMarket(this,'vcp_ml-hz-{hz}')" data-mkt="KONEX">🇰🇷 KONEX</button>
        <button class="filter-btn" onclick="filterMarket(this,'vcp_ml-hz-{hz}')" data-mkt="SP500">🇺🇸 SP500</button>
      </div>
      <div id="vcp_ml-hz-{hz}-panels">
        {panels}
      </div>
    </div>"""

    # ── Tab: Regression ──
    reg_sections = reg_sections or []
    reg_horizons = sorted(set(s.horizon for s in reg_sections), key=lambda h: int(re.search(r"\d+", h).group())) if reg_sections else []
    reg_tabs_nav = ""
    reg_tabs_content = ""
    for i, hz in enumerate(reg_horizons):
        active = "active" if i == 0 else ""
        reg_tabs_nav += f'<button class="hz-tab {active}" data-hz="{hz}" onclick="switchHz(this)">{hz}</button>'
        hz_sections = [s for s in reg_sections if s.horizon == hz]
        panels = ""
        for s in hz_sections:
            mkt_key = "SP500" if s.market == "SP500" else s.market
            flag = MARKET_FLAGS.get(mkt_key, "")
            rows_html = ""
            for r in s.rows:
                rc = ret_class(r.expected_return)
                rows_html += f"""
            <tr>
              <td class="rank">#{r.rank}</td>
              <td class="symbol">{r.symbol}</td>
              <td class="name">{r.name}</td>
              <td class="{rc}">{r.expected_return}</td>
            </tr>"""
            if not rows_html:
                rows_html = '<tr><td colspan="4" class="empty">데이터 없음</td></tr>'
            panels += f"""
        <div class="market-panel" data-market="{mkt_key}">
          <h3 class="market-title">{flag} {mkt_key}</h3>
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
        <button class="filter-btn" onclick="filterMarket(this,'reg-hz-{hz}')" data-mkt="KONEX">🇰🇷 KONEX</button>
        <button class="filter-btn" onclick="filterMarket(this,'reg-hz-{hz}')" data-mkt="SP500">🇺🇸 SP500</button>
      </div>
      <div id="reg-hz-{hz}-panels">
        {panels}
      </div>
    </div>"""

    # ── Full HTML ──
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📈 Stock Prediction Dashboard | KRX & SP500</title>
<meta name="description" content="AI 기반 한국·미국 주식 예측 대시보드 — XGBoost 앙상블, Surge 분류기, VCP 패턴, Lead-Lag 전략">
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

  /* Header */
  .header {{ background: linear-gradient(135deg, #0d1117 0%, #1a2332 50%, #0d1117 100%); border-bottom: 1px solid var(--border); padding: 24px 32px; }}
  .header h1 {{ font-size: 24px; font-weight: 700; background: linear-gradient(90deg, #58a6ff, #3fb950); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
  .header-meta {{ display: flex; gap: 16px; margin-top: 8px; flex-wrap: wrap; align-items: center; }}
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid; }}
  .badge-regime {{ color: {regime_color}; border-color: {regime_color}; background: {regime_color}20; }}
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
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead th {{ padding: 10px 12px; text-align: left; font-size: 12px; color: var(--muted); font-weight: 500; border-bottom: 1px solid var(--border); white-space: nowrap; }}
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
  .weights-section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 20px; }}
  .weights-title {{ font-size: 13px; font-weight: 600; color: var(--muted); margin-bottom: 12px; }}
  .weight-item {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid var(--border); }}
  .weight-item:last-child {{ border-bottom: none; }}
  .wk {{ color: var(--text); }}
  .wv {{ font-weight: 700; color: var(--accent); }}

  /* Horizon tabs */
  .hz-tabs {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
  .hz-tab {{ padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); background: var(--surface); color: var(--muted); cursor: pointer; font-size: 12px; font-weight: 500; }}
  .hz-tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

  /* Leader section */
  .section-title {{ font-size: 14px; font-weight: 600; color: var(--muted); margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}

  /* Responsive */
  @media (max-width: 768px) {{
    .header, .macro-strip, .tabs, .content {{ padding-left: 16px; padding-right: 16px; }}
    .header h1 {{ font-size: 18px; }}
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
    <span class="badge badge-regime">{regime_label}</span>
    <span class="badge badge-date">📅 {report_date}</span>
    <span class="badge badge-updated">🔄 생성: {now_kst}</span>
  </div>
</div>

<div class="macro-strip">
  {macro_html}
</div>

<nav class="tabs">
  <button class="tab active" onclick="switchTab(this,'ensemble')">🏆 Ensemble</button>
  <button class="tab" onclick="switchTab(this,'surge')">⚡ Surge</button>
  <button class="tab" onclick="switchTab(this,'vcpml')">🤖 VCP ML</button>
  <button class="tab" onclick="switchTab(this,'regression')">📈 Regression</button>
  <button class="tab" onclick="switchTab(this,'vcp')">📐 VCP</button>
  <button class="tab" onclick="switchTab(this,'leadlag')">🔗 Lead-Lag</button>
</nav>

<div class="content">

  <!-- ══ Ensemble Tab ══ -->
  <div class="tab-panel active" id="panel-ensemble">
    <div class="weights-section">
      <div class="weights-title">⚙️ 전략 가중치</div>
      {weights_html if weights_html else '<span style="color:var(--muted)">데이터 없음</span>'}
    </div>
    <div class="filter-bar" id="filter-ensemble">
      <button class="filter-btn active" onclick="filterMarket(this,'ensemble')" data-mkt="all">전체</button>
      <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="KOSPI">🇰🇷 KOSPI</button>
      <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="KOSDAQ">🇰🇷 KOSDAQ</button>
      <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="KONEX">🇰🇷 KONEX</button>
      <button class="filter-btn" onclick="filterMarket(this,'ensemble')" data-mkt="SP500">🇺🇸 SP500</button>
    </div>
    <div id="ensemble-panels">
    {ensemble_panels}
    </div>
  </div>

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
      <button class="filter-btn" onclick="filterMarket(this,'vcp')" data-mkt="KONEX">🇰🇷 KONEX</button>
      <button class="filter-btn" onclick="filterMarket(this,'vcp')" data-mkt="SP500">🇺🇸 SP500</button>
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
      <button class="filter-btn" onclick="filterMarket(this,'leadlag')" data-mkt="KONEX">🇰🇷 KONEX</button>
      <button class="filter-btn" onclick="filterMarket(this,'leadlag')" data-mkt="SP500">🇺🇸 SP500</button>
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

</div>

<script>
function switchTab(btn, id) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('panel-' + id).classList.add('active');
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
</script>
</body>
</html>
"""


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate stock prediction HTML dashboard")
    parser.add_argument("--result-dir", default="trading_system/result", help="Directory with result txt files")
    parser.add_argument("--out", default="gh-pages/index.html", help="Output HTML file path")
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    out_path = Path(args.out)

    print(f"[generate_report] Reading from: {result_dir.resolve()}")

    ensemble = parse_ensemble(_read(result_dir / "ensemble_predictions.txt"))
    surge_date, surge_sections = parse_surge(_read(result_dir / "surge_predictions.txt"))
    vcp_date, vcp_rows = parse_vcp(_read(result_dir / "vcp_patterns.txt"))
    lag_date, follower_rows, leader_rows = parse_lead_lag(_read(result_dir / "lead_lag_predictions.txt"))
    vcp_ml_date, vcp_ml_sections = parse_vcp_ml(_read(result_dir / "vcp_ml_predictions.txt"))
    reg_date, reg_sections = parse_regression(_read(result_dir / "pipeline_result.txt"))

    html = build_html(
        ensemble,
        surge_date, surge_sections,
        vcp_date, vcp_rows,
        lag_date, follower_rows, leader_rows,
        vcp_ml_sections, reg_sections
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"[generate_report] Dashboard written to: {out_path.resolve()} ({size_kb} KB)")


if __name__ == "__main__":
    main()
