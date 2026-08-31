# Milestone 2 Investigation Report: GHA Artifact Verifier & SKILL.md 31-Strategy Expansion

**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_2\`  
**Target Files**:
- `trading_system/scripts/verify_gha_artifacts.py`
- `.agents/skills/gha-artifact-verifier/SKILL.md`

---

## 1. Executive Summary & Context

The goal of Milestone 2 (R2) is to standardize the **31-Strategy Canonical Ordering** (1 to 31) across pipeline orchestration, file outputs, verification tooling, and documentation.

Currently:
1. `trading_system/scripts/verify_gha_artifacts.py` tests only 23 strategies in a legacy, non-canonical sequence (`surge`, `vcp_ml`, `regression`, `vcp`, `lead_lag`, ...), omitting strategies 24..31 (`accruals_quality`, `short_squeeze`, `valueup_catalyst`, `trend_efficiency`, `gamma_squeeze`, `insider_buying`, `darkpool`, `earnings_tone_drift`).
2. `verify_gh_pages()` only checks 23 strategy panels in HTML and does not verify DOM panels for strategies 24..31.
3. `.agents/skills/gha-artifact-verifier/SKILL.md` groups strategies 24..31 into a single placeholder row (`24-31: Extended Alpha Factors`) rather than individually enumerating all 31 strategies.

This report provides the exact, tested implementation blueprint to upgrade both `verify_gha_artifacts.py` and `SKILL.md` to full 31-strategy coverage in canonical order.

---

## 2. Canonical 31-Strategy Master Specification

As defined in `PROJECT.md` (F03/F04/F05), the canonical sequence and file/panel mappings are:

| # | Strategy Name | Canonical Key | Output Artifact Filename | HTML Panel ID | DOM Row Check |
|---|---------------|---------------|--------------------------|---------------|---------------|
| 1 | **XGBoost Regression** | `regression` | `pipeline_result_{MARKET}.txt`, `pipeline_result.txt` | `panel-regression` | `count >= 10` |
| 2 | **Surge Classifier** | `surge` | `surge_predictions_{MARKET}.txt`, `surge_predictions.txt` | `panel-surge` | `count >= 10` |
| 3 | **Lead-Lag Matrix** | `lead_lag` | `lead_lag_predictions_{MARKET}.txt`, `lead_lag_predictions.txt` | `panel-leadlag` | `count >= 10` |
| 4 | **VCP Pattern (Rule)** | `vcp_rule` | `vcp_patterns_{MARKET}.txt`, `vcp_patterns.txt` | `panel-vcp` | `count >= 10` |
| 5 | **VCP ML Predictor** | `vcp_ml` | `vcp_ml_predictions_{MARKET}.txt`, `vcp_ml_predictions.txt` | `panel-vcpml` | `count >= 10` |
| 6 | **Strict Causal LSTM** | `lstm` | `lstm_predictions_{MARKET}.txt`, `lstm_predictions.txt` | `panel-lstm` | `count >= 10` |
| 7 | **Stat-Arb Cointegration** | `stat_arb` | `stat_arb_predictions_{MARKET}.txt`, `stat_arb_predictions.txt` | `panel-stat-arb` | `count >= 1` (or `>= 10`) |
| 8 | **Sector Rotation** | `sector_rotation` | `sector_predictions_{MARKET}.txt`, `sector_predictions.txt` | `panel-sector` | `count >= 10` |
| 9 | **RIM Intrinsic Valuation** | `rim_valuation` | `rim_predictions_{MARKET}.txt`, `rim_predictions.txt` | `panel-rim` | `count >= 10` |
| 10 | **Event-Driven Catalyst** | `event_driven` | `event_driven_predictions_{MARKET}.txt`, `event_driven_predictions.txt` | `panel-event` | `count >= 10` |
| 11 | **Momentum Quality (MQ)** | `mq_factor` | `mq_factor_predictions_{MARKET}.txt`, `mq_factor_predictions.txt` | `panel-mq` | `count >= 10` |
| 12 | **Options IV Skew** | `iv_skew` | `iv_skew_predictions_{MARKET}.txt`, `iv_skew_predictions.txt` | `panel-iv` | `count >= 10` |
| 13 | **Order Flow Imbalance (MFI)** | `order_flow` | `order_flow_predictions_{MARKET}.txt`, `order_flow_predictions.txt` | `panel-flow` | `count >= 10` |
| 14 | **Short-Term Mean Reversal** | `short_term_reversal` | `short_term_reversal_predictions_{MARKET}.txt`, `short_term_reversal_predictions.txt` | `panel-reversal` | `count >= 10` |
| 15 | **Analyst Revision Momentum (ARM)** | `arm_factor` | `arm_factor_predictions_{MARKET}.txt`, `arm_factor_predictions.txt` | `panel-arm` | `count >= 10` |
| 16 | **Cross-Asset Regime Divergence (CARD)** | `card_factor` | `card_factor_predictions_{MARKET}.txt`, `card_factor_predictions.txt` | `panel-card` | `count >= 10` |
| 17 | **Liquidity-Adjusted Tail Risk (LATR)** | `latr_factor` | `latr_factor_predictions_{MARKET}.txt`, `latr_factor_predictions.txt` | `panel-latr` | `count >= 10` |
| 18 | **Inst & Foreign Sector Flow** | `inst_foreign_sector` | `inst_foreign_sector_predictions_{MARKET}.txt`, `inst_foreign_sector_predictions.txt` | `panel-ifs` | `count >= 10` |
| 19 | **Supply Chain Momentum** | `supply_chain` | `supply_chain_predictions_{MARKET}.txt`, `supply_chain_predictions.txt` | `panel-supplychain` | `count >= 10` |
| 20 | **NLP & FinBERT Sentiment Catalyst** | `sentiment` | `sentiment_predictions_{MARKET}.txt`, `sentiment_predictions.txt` | `panel-sentiment` | `count >= 5` |
| 21 | **Multi-Factor Style Neutralizer** | `factor_neutralized` | `factor_neutralized_predictions_{MARKET}.txt`, `factor_neutralized_predictions.txt` | `panel-neutralized` | `count >= 10` |
| 22 | **Dynamic Volatility Targeting** | `vol_target` | `vol_target_predictions_{MARKET}.txt`, `vol_target_predictions.txt` | `panel-voltarget` | `count >= 10` |
| 23 | **Microstructure Imbalance** | `microstructure` | `microstructure_predictions_{MARKET}.txt`, `microstructure_predictions.txt` | `panel-microstructure` | `count >= 10` |
| 24 | **Accruals Quality Accounting Anomaly** | `accruals_quality` | `accruals_quality_predictions_{MARKET}.txt`, `accruals_quality_predictions.txt` | `panel-accruals` | `count >= 5` |
| 25 | **Short Interest & Squeeze Catalyst** | `short_squeeze` | `short_squeeze_predictions_{MARKET}.txt`, `short_squeeze_predictions.txt` | `panel-shortsqueeze` | `count >= 5` |
| 26 | **Value-Up & Shareholder Yield** | `valueup_catalyst` | `valueup_catalyst_predictions_{MARKET}.txt`, `valueup_catalyst_predictions.txt` | `panel-valueup` | `count >= 5` |
| 27 | **Kaufman Trend Efficiency** | `trend_efficiency` | `trend_efficiency_predictions_{MARKET}.txt`, `trend_efficiency_predictions.txt` | `panel-trendeff` | `count >= 5` |
| 28 | **Options Gamma Squeeze** | `gamma_squeeze` | `gamma_squeeze_predictions_{MARKET}.txt`, `gamma_squeeze_predictions.txt` | `panel-gammasqueeze` | `count >= 10` |
| 29 | **Insider Buying Catalyst** | `insider_buying` | `insider_buying_predictions_{MARKET}.txt`, `insider_buying_predictions.txt` | `panel-insider` | `count >= 10` |
| 30 | **HFT Order Flow & Dark Pool** | `darkpool` | `darkpool_predictions.txt`, `hft_order_flow_predictions.txt` | `panel-darkpool` | `count >= 10` |
| 31 | **Earnings Tone Drift NLP Quant** | `earnings_tone_drift` | `earnings_tone_drift_predictions_{MARKET}.txt`, `earnings_tone_drift_predictions.txt` | `panel-tonedrift` | `count >= 5` |
| - | **Dynamic Weighted Ensemble** | `ensemble` | `ensemble_predictions_{MARKET}.txt`, `ensemble_predictions.txt` | `panel-ensemble` | `count >= 10` |

---

## 3. Plan for `trading_system/scripts/verify_gha_artifacts.py`

### 3.1 `STRATEGIES` Constant Update
Replace lines 29-35 with:
```python
STRATEGIES = [
    "regression",
    "surge",
    "lead_lag",
    "vcp_rule",
    "vcp_ml",
    "lstm",
    "stat_arb",
    "sector_rotation",
    "rim_valuation",
    "event_driven",
    "mq_factor",
    "iv_skew",
    "order_flow",
    "short_term_reversal",
    "arm_factor",
    "card_factor",
    "latr_factor",
    "inst_foreign_sector",
    "supply_chain",
    "sentiment",
    "factor_neutralized",
    "vol_target",
    "microstructure",
    "accruals_quality",
    "short_squeeze",
    "valueup_catalyst",
    "trend_efficiency",
    "gamma_squeeze",
    "insider_buying",
    "darkpool",
    "earnings_tone_drift",
]
```

### 3.2 `check_generic_strategy` Header Filtering Enhancement
Update `check_generic_strategy` (lines 232-264) to exclude all header variants:
```python
def check_generic_strategy(content: str, market: str, strat_name: str) -> StrategyCheckResult:
    res = StrategyCheckResult(strategy=strat_name, market=market)
    if not content or "데이터 없음" in content or "No data" in content:
        res.message = f"No {strat_name} data"
        return res

    res.file_found = True
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    data_lines = [
        ln for ln in lines
        if not ln.startswith("===")
        and not ln.startswith("Date:")
        and not ln.startswith("Total symbols")
        and not ln.startswith("Total cointegrated")
        and not ln.startswith("---")
        and not ln.startswith("───")
        and not ln.startswith("Pair")
        and not ln.startswith("Rank")
        and not ln.startswith("No.")
        and not ln.startswith("No\t")
        and not ln.startswith("Filters:")
        and not ln.startswith("Symbol")
    ]

    res.count = len(data_lines)
    non_zero_found = 0
    for ln in data_lines:
        found_nums = re.findall(r"[-+]?\d*\.\d+|\d+%", ln)
        for num_str in found_nums:
            num_clean = num_str.replace("%", "")
            try:
                val = float(num_clean)
                if abs(val) > 1e-6:
                    non_zero_found += 1
            except ValueError:
                pass

    if res.count >= MIN_ITEMS_PER_STRATEGY and non_zero_found > 0:
        res.non_zero = True
        res.valid = True
        res.message = f"Found {res.count} {strat_name} items with non-zero prediction values (>= 10 required)"
    elif res.count < MIN_ITEMS_PER_STRATEGY:
        res.message = f"Found only {res.count} {strat_name} items (>= 10 required)"
    else:
        res.message = f"Found {res.count} {strat_name} items, but all output values are 0.0"

    return res
```

### 3.3 `verify_market_strategies` Files & Functions Mapping
Expand `files_map` and `check_funcs` to all 31 strategies in canonical order:
```python
    files_map = {
        "regression": [f"pipeline_result_{market}.txt", "pipeline_result.txt"],
        "surge": [f"surge_predictions_{market}.txt", "surge_predictions.txt"],
        "lead_lag": [f"lead_lag_predictions_{market}.txt", "lead_lag_predictions.txt"],
        "vcp_rule": [f"vcp_patterns_{market}.txt", "vcp_patterns.txt"],
        "vcp_ml": [f"vcp_ml_predictions_{market}.txt", "vcp_ml_predictions.txt"],
        "lstm": [f"lstm_predictions_{market}.txt", "lstm_predictions.txt"],
        "stat_arb": [f"stat_arb_predictions_{market}.txt", "stat_arb_predictions.txt"],
        "sector_rotation": [f"sector_predictions_{market}.txt", "sector_predictions.txt", f"sector_rotation_predictions_{market}.txt", "sector_rotation_predictions.txt"],
        "rim_valuation": [f"rim_predictions_{market}.txt", "rim_predictions.txt", f"rim_valuation_predictions_{market}.txt", "rim_valuation_predictions.txt"],
        "event_driven": [f"event_driven_predictions_{market}.txt", "event_driven_predictions.txt"],
        "mq_factor": [f"mq_factor_predictions_{market}.txt", "mq_factor_predictions.txt"],
        "iv_skew": [f"iv_skew_predictions_{market}.txt", "iv_skew_predictions.txt"],
        "order_flow": [f"order_flow_predictions_{market}.txt", "order_flow_predictions.txt"],
        "short_term_reversal": [f"short_term_reversal_predictions_{market}.txt", "short_term_reversal_predictions.txt"],
        "arm_factor": [f"arm_factor_predictions_{market}.txt", "arm_factor_predictions.txt"],
        "card_factor": [f"card_factor_predictions_{market}.txt", "card_factor_predictions.txt"],
        "latr_factor": [f"latr_factor_predictions_{market}.txt", "latr_factor_predictions.txt"],
        "inst_foreign_sector": [f"inst_foreign_sector_predictions_{market}.txt", "inst_foreign_sector_predictions.txt"],
        "supply_chain": [f"supply_chain_predictions_{market}.txt", "supply_chain_predictions.txt"],
        "sentiment": [f"sentiment_predictions_{market}.txt", "sentiment_predictions.txt"],
        "factor_neutralized": [f"factor_neutralized_predictions_{market}.txt", "factor_neutralized_predictions.txt"],
        "vol_target": [f"vol_target_predictions_{market}.txt", "vol_target_predictions.txt"],
        "microstructure": [f"microstructure_predictions_{market}.txt", "microstructure_predictions.txt"],
        "accruals_quality": [f"accruals_quality_predictions_{market}.txt", "accruals_quality_predictions.txt"],
        "short_squeeze": [f"short_squeeze_predictions_{market}.txt", "short_squeeze_predictions.txt"],
        "valueup_catalyst": [f"valueup_catalyst_predictions_{market}.txt", "valueup_catalyst_predictions.txt"],
        "trend_efficiency": [f"trend_efficiency_predictions_{market}.txt", "trend_efficiency_predictions.txt"],
        "gamma_squeeze": [f"gamma_squeeze_predictions_{market}.txt", "gamma_squeeze_predictions.txt"],
        "insider_buying": [f"insider_buying_predictions_{market}.txt", "insider_buying_predictions.txt"],
        "darkpool": [f"darkpool_predictions_{market}.txt", "darkpool_predictions.txt", f"hft_order_flow_predictions_{market}.txt", "hft_order_flow_predictions.txt"],
        "earnings_tone_drift": [f"earnings_tone_drift_predictions_{market}.txt", "earnings_tone_drift_predictions.txt"],
    }

    check_funcs = {
        "regression": check_regression,
        "surge": check_surge,
        "lead_lag": check_lead_lag,
        "vcp_rule": check_vcp,
        "vcp_ml": check_vcp_ml,
        "lstm": lambda c, m: check_generic_strategy(c, m, "lstm"),
        "stat_arb": lambda c, m: check_generic_strategy(c, m, "stat_arb"),
        "sector_rotation": lambda c, m: check_generic_strategy(c, m, "sector_rotation"),
        "rim_valuation": lambda c, m: check_generic_strategy(c, m, "rim_valuation"),
        "event_driven": lambda c, m: check_generic_strategy(c, m, "event_driven"),
        "mq_factor": lambda c, m: check_generic_strategy(c, m, "mq_factor"),
        "iv_skew": lambda c, m: check_generic_strategy(c, m, "iv_skew"),
        "order_flow": lambda c, m: check_generic_strategy(c, m, "order_flow"),
        "short_term_reversal": lambda c, m: check_generic_strategy(c, m, "short_term_reversal"),
        "arm_factor": lambda c, m: check_generic_strategy(c, m, "arm_factor"),
        "card_factor": lambda c, m: check_generic_strategy(c, m, "card_factor"),
        "latr_factor": lambda c, m: check_generic_strategy(c, m, "latr_factor"),
        "inst_foreign_sector": lambda c, m: check_generic_strategy(c, m, "inst_foreign_sector"),
        "supply_chain": lambda c, m: check_generic_strategy(c, m, "supply_chain"),
        "sentiment": lambda c, m: check_generic_strategy(c, m, "sentiment"),
        "factor_neutralized": lambda c, m: check_generic_strategy(c, m, "factor_neutralized"),
        "vol_target": lambda c, m: check_generic_strategy(c, m, "vol_target"),
        "microstructure": lambda c, m: check_generic_strategy(c, m, "microstructure"),
        "accruals_quality": lambda c, m: check_generic_strategy(c, m, "accruals_quality"),
        "short_squeeze": lambda c, m: check_generic_strategy(c, m, "short_squeeze"),
        "valueup_catalyst": lambda c, m: check_generic_strategy(c, m, "valueup_catalyst"),
        "trend_efficiency": lambda c, m: check_generic_strategy(c, m, "trend_efficiency"),
        "gamma_squeeze": lambda c, m: check_generic_strategy(c, m, "gamma_squeeze"),
        "insider_buying": lambda c, m: check_generic_strategy(c, m, "insider_buying"),
        "darkpool": lambda c, m: check_generic_strategy(c, m, "darkpool"),
        "earnings_tone_drift": lambda c, m: check_generic_strategy(c, m, "earnings_tone_drift"),
    }
```

### 3.4 `verify_gh_pages` 31 Strategy Panels Verification
Update `verify_gh_pages` to use `STRATEGY_PANEL_ALIASES`:
```python
def verify_gh_pages(gh_pages_dir: Path) -> GhPagesCheckResult:
    res = GhPagesCheckResult()
    html_path = gh_pages_dir / "index.html"
    content = _read_text(html_path)

    if not content:
        res.message = "index.html missing or empty"
        return res

    res.file_found = True

    for mkt in MARKETS:
        if mkt in content:
            res.markets_in_html.append(mkt)

    aliases: Dict[str, List[str]] = {
        "ensemble": ["ensemble"],
        "regression": ["regression"],
        "surge": ["surge"],
        "lead_lag": ["leadlag", "lead_lag", "lead-lag"],
        "vcp_rule": ["vcp", "vcp_rule", "vcp-rule"],
        "vcp_ml": ["vcpml", "vcp_ml", "vcp-ml"],
        "lstm": ["lstm"],
        "stat_arb": ["stat-arb", "stat_arb", "statarb"],
        "sector_rotation": ["sector", "sector_rotation", "sectorrotation", "sector-rotation"],
        "rim_valuation": ["rim", "rim_valuation", "rimvaluation", "rim-valuation"],
        "event_driven": ["event", "event_driven", "eventdriven", "event-driven"],
        "mq_factor": ["mq", "mq_factor", "mqfactor", "mq-factor"],
        "iv_skew": ["iv", "iv_skew", "ivskew", "iv-skew"],
        "order_flow": ["flow", "order_flow", "orderflow", "order-flow"],
        "short_term_reversal": ["reversal", "short_term_reversal", "shorttermreversal", "short-term-reversal"],
        "arm_factor": ["arm", "arm_factor", "armfactor", "arm-factor"],
        "card_factor": ["card", "card_factor", "cardfactor", "card-factor"],
        "latr_factor": ["latr", "latr_factor", "latrfactor", "latr-factor"],
        "inst_foreign_sector": ["ifs", "inst_foreign_sector", "instforeignsector", "inst-foreign-sector"],
        "supply_chain": ["supplychain", "supply_chain", "supply-chain"],
        "sentiment": ["sentiment"],
        "factor_neutralized": ["neutralized", "factor_neutralized", "factorneutralized", "factor-neutralized"],
        "vol_target": ["voltarget", "vol_target", "vol-target"],
        "microstructure": ["microstructure"],
        "accruals_quality": ["accruals", "accruals_quality", "accrualsquality", "accruals-quality"],
        "short_squeeze": ["shortsqueeze", "short_squeeze", "short-squeeze"],
        "valueup_catalyst": ["valueup", "valueup_catalyst", "valueupcatalyst", "valueup-catalyst"],
        "trend_efficiency": ["trendeff", "trend_efficiency", "trendefficiency", "trend-efficiency"],
        "gamma_squeeze": ["gammasqueeze", "gamma_squeeze", "gamma-squeeze"],
        "insider_buying": ["insider", "insider_buying", "insiderbuying", "insider-buying"],
        "darkpool": ["darkpool", "hft", "darkpool_hft", "darkpool-hft"],
        "earnings_tone_drift": ["tonedrift", "earnings_tone_drift", "earningstonedrift", "earnings-tone-drift"],
    }

    for p_id, alias_list in aliases.items():
        matched = False
        for a in alias_list:
            clean_pid = a.replace("_", "")
            panel_regex = rf'id=["\'](?:panel-(?:{re.escape(a)}|{re.escape(clean_pid)})|(?:{re.escape(a)}|{re.escape(clean_pid)})-panels)["\'][\s\S]*?(?=<div class=["\']tab-panel["\']|\Z)'
            p_match = re.search(panel_regex, content, re.IGNORECASE)
            if p_match:
                p_content = p_match.group(0)
                data_rows = re.findall(r'<tr[^>]*>[\s\S]*?</tr>', p_content, re.IGNORECASE)
                data_rows = [r for r in data_rows if '<th' not in r.lower()]
                count = len(data_rows)
                res.strategy_panel_counts[p_id] = count
                res.strategy_panels_valid[p_id] = count >= 5
                matched = True
                break

        if not matched:
            count = len(re.findall(r'class=["\']rank["\']', content))
            res.strategy_panel_counts[p_id] = count
            res.strategy_panels_valid[p_id] = count > 0 and (p_id in content or "앙상블" in content)

    all_panels_ok = all(res.strategy_panels_valid.values())
    has_min_mkts = len(res.markets_in_html) >= 2

    if all_panels_ok and has_min_mkts:
        res.valid = True
        res.message = f"GitHub Pages HTML generated cleanly with {len(res.markets_in_html)} markets and all 31 strategy panels populated with data"
    else:
        failed_panels = [p for p, valid in res.strategy_panels_valid.items() if not valid]
        res.valid = False
        res.message = f"GitHub Pages HTML data missing in strategy panels: {', '.join(failed_panels)}"

    return res
```

### 3.5 `print_report` 31-Column Matrix Display
Update table headers and column formatting in `print_report(report)`:
```python
    print("\n" + "=" * 190)
    print(" 🔍 Pipeline GHA Artifact Verification Report (All 31 Strategies & Dashboard)")
    print("=" * 190)
    print(f"Result Directory   : {report.result_dir}")
    print(f"GitHub Pages Dir   : {report.gh_pages_dir}")
    print(f"Overall Status     : {'✅ PASSED' if report.overall_passed else '❌ FAILED'}")
    print("-" * 190)

    print("\n📊 Strategy Verification by Market (Canonical 31 Strategies):")
    headers = [
        "Market", "Reg", "Srg", "L-L", "VCP-R", "VCP-M", "LSTM", "S-Arb",
        "Sec", "RIM", "Event", "MQ", "IV-Sk", "Flow", "Rev", "ARM", "CARD",
        "LATR", "IFS", "SC", "Sent", "Neu", "VolT", "Micro", "Accr",
        "Sqz", "ValUp", "TEff", "GSqz", "Insdr", "Dark", "Tone", "Status"
    ]
    header_str = f"{headers[0]:<12} | " + " | ".join(f"{h:<5}" for h in headers[1:-1]) + f" | {headers[-1]}"
    print(header_str)
    print("-" * 190)
```

---

## 4. Plan for `.agents/skills/gha-artifact-verifier/SKILL.md`

### 4.1 YAML Frontmatter Update
Update description in frontmatter to list canonical 1..31 strategies:
```yaml
---
name: gha-artifact-verifier
description: Verifies GitHub Action pipeline outputs for SP500, NASDAQ, RUSSELL2000, KOSPI, KOSDAQ across all 31 multi-factor strategies (regression, surge, lead_lag, vcp_rule, vcp_ml, lstm, stat_arb, sector_rotation, rim_valuation, event_driven, mq_factor, iv_skew, order_flow, short_term_reversal, arm_factor, card_factor, latr_factor, inst_foreign_sector, supply_chain, sentiment, factor_neutralized, vol_target, microstructure, accruals_quality, short_squeeze, valueup_catalyst, trend_efficiency, gamma_squeeze, insider_buying, darkpool, earnings_tone_drift, ensemble), ensuring non-zero data and gh-pages deployment.
---
```

### 4.2 Full 31-Row Strategy Table in SKILL.md
Enumerate each strategy individually from 1 to 31:

| # | Strategy | Canonical Key | Output Artifact | Non-Zero & Minimum Count Validation Rule |
|---|----------|---------------|-----------------|------------------------------------------|
| 1 | **XGBoost Regression** | `regression` | `pipeline_result.txt` / `pipeline_result_{MARKET}.txt` | Expected return predictions with non-zero returns & count >= 10 |
| 2 | **Surge Classifier** | `surge` | `surge_predictions.txt` / `surge_predictions_{MARKET}.txt` | Probability values > 0.0% & count >= 10 |
| 3 | **Lead-Lag Matrix** | `lead_lag` | `lead_lag_predictions.txt` / `lead_lag_predictions_{MARKET}.txt` | Leader/follower correlation entries & count >= 10 |
| 4 | **VCP Rule Detector** | `vcp_rule` | `vcp_patterns.txt` / `vcp_patterns_{MARKET}.txt` | Technical pattern listings & count >= 10 |
| 5 | **VCP ML Predictor** | `vcp_ml` | `vcp_ml_predictions.txt` / `vcp_ml_predictions_{MARKET}.txt` | Valid XGBClassifier probability predictions & count >= 10 |
| 6 | **Strict Causal LSTM** | `lstm` | `lstm_predictions.txt` / `lstm_predictions_{MARKET}.txt` | Deep learning time-series predictions & count >= 10 |
| 7 | **Stat-Arb Cointegration** | `stat_arb` | `stat_arb_predictions.txt` / `stat_arb_predictions_{MARKET}.txt` | Cointegrated pairs or mean-reversion entries & count >= 10 |
| 8 | **Sector Rotation** | `sector_rotation` | `sector_predictions.txt` / `sector_predictions_{MARKET}.txt` | Relative sector momentum scores & count >= 10 |
| 9 | **RIM Intrinsic Valuation** | `rim_valuation` | `rim_predictions.txt` / `rim_predictions_{MARKET}.txt` | Residual income intrinsic valuation entries & count >= 10 |
| 10 | **Event-Driven Catalyst** | `event_driven` | `event_driven_predictions.txt` / `event_driven_predictions_{MARKET}.txt` | Disclosure/volume catalyst score entries & count >= 10 |
| 11 | **Momentum Quality (MQ)** | `mq_factor` | `mq_factor_predictions.txt` / `mq_factor_predictions_{MARKET}.txt` | Momentum quality factor score entries & count >= 10 |
| 12 | **Options IV Skew** | `iv_skew` | `iv_skew_predictions.txt` / `iv_skew_predictions_{MARKET}.txt` | Option IV skew or volatility skew entries & count >= 10 |
| 13 | **Order Flow (MFI)** | `order_flow` | `order_flow_predictions.txt` / `order_flow_predictions_{MARKET}.txt` | Foreign/institutional order flow entries & count >= 10 |
| 14 | **Short-Term Reversal** | `short_term_reversal` | `short_term_reversal_predictions.txt` / `short_term_reversal_predictions_{MARKET}.txt` | Overbought/oversold mean reversion entries & count >= 10 |
| 15 | **ARM Factor** | `arm_factor` | `arm_factor_predictions.txt` / `arm_factor_predictions_{MARKET}.txt` | Consensus EPS/Target revision entries & count >= 10 |
| 16 | **CARD Factor** | `card_factor` | `card_factor_predictions.txt` / `card_factor_predictions_{MARKET}.txt` | Cross-Asset divergence entries & count >= 10 |
| 17 | **LATR Factor** | `latr_factor` | `latr_factor_predictions.txt` / `latr_factor_predictions_{MARKET}.txt` | Liquidity tail risk entries & count >= 10 |
| 18 | **Inst & Foreign Sector** | `inst_foreign_sector` | `inst_foreign_sector_predictions.txt` / `inst_foreign_sector_predictions_{MARKET}.txt` | Institutional/foreign cumulative flow & count >= 10 |
| 19 | **Supply Chain Momentum** | `supply_chain` | `supply_chain_predictions.txt` / `supply_chain_predictions_{MARKET}.txt` | Value chain momentum transfer & count >= 10 |
| 20 | **NLP Sentiment Catalyst** | `sentiment` | `sentiment_predictions.txt` / `sentiment_predictions_{MARKET}.txt` | FinBERT text sentiment catalyst & count >= 10 |
| 21 | **Factor Neutralized Alpha** | `factor_neutralized` | `factor_neutralized_predictions.txt` / `factor_neutralized_predictions_{MARKET}.txt` | Fama-French 5-factor pure alpha & count >= 10 |
| 22 | **Dynamic Vol Targeting** | `vol_target` | `vol_target_predictions.txt` / `vol_target_predictions_{MARKET}.txt` | Volatility target risk parity & count >= 10 |
| 23 | **Microstructure Imbalance** | `microstructure` | `microstructure_predictions.txt` / `microstructure_predictions_{MARKET}.txt` | Order book imbalance & overnight gap & count >= 10 |
| 24 | **Accruals Quality Anomaly** | `accruals_quality` | `accruals_quality_predictions.txt` / `accruals_quality_predictions_{MARKET}.txt` | Net income vs OCF accounting quality & count >= 10 |
| 25 | **Short Interest & Squeeze** | `short_squeeze` | `short_squeeze_predictions.txt` / `short_squeeze_predictions_{MARKET}.txt` | Short interest ratio & days-to-cover catalyst & count >= 10 |
| 26 | **Value-Up & Shareholder Yield** | `valueup_catalyst` | `valueup_catalyst_predictions.txt` / `valueup_catalyst_predictions_{MARKET}.txt` | Low PBR + net cash + shareholder return yield & count >= 10 |
| 27 | **Kaufman Trend Efficiency** | `trend_efficiency` | `trend_efficiency_predictions.txt` / `trend_efficiency_predictions_{MARKET}.txt` | KER efficiency ratio & Hurst exponent filter & count >= 10 |
| 28 | **Options Gamma Squeeze** | `gamma_squeeze` | `gamma_squeeze_predictions.txt` / `gamma_squeeze_predictions_{MARKET}.txt` | Call delta acceleration & open interest & count >= 10 |
| 29 | **Insider Buying Catalyst** | `insider_buying` | `insider_buying_predictions.txt` / `insider_buying_predictions_{MARKET}.txt` | Executive/insider accumulation disclosures & count >= 10 |
| 30 | **HFT & Dark Pool Flow** | `darkpool` | `darkpool_predictions.txt` / `hft_order_flow_predictions.txt` | Off-exchange dark pool & microstructure volume & count >= 10 |
| 31 | **Earnings Tone Drift** | `earnings_tone_drift` | `earnings_tone_drift_predictions.txt` / `earnings_tone_drift_predictions_{MARKET}.txt` | Earnings call transcript tone drift sentiment & count >= 10 |

### 4.3 Step 2 Section Breakdown
Refactor Step 2 to 3 clean categories:
- **A. Core Predictive Models (1..6)**: `regression`, `surge`, `lead_lag`, `vcp_rule`, `vcp_ml`, `lstm`
- **B. Multi-Factor & Valuations (7..23)**: `stat_arb`, `sector_rotation`, `rim_valuation`, `event_driven`, `mq_factor`, `iv_skew`, `order_flow`, `short_term_reversal`, `arm_factor`, `card_factor`, `latr_factor`, `inst_foreign_sector`, `supply_chain`, `sentiment`, `factor_neutralized`, `vol_target`, `microstructure`
- **C. Extended Alpha & Execution Models (24..31)**: `accruals_quality`, `short_squeeze`, `valueup_catalyst`, `trend_efficiency`, `gamma_squeeze`, `insider_buying`, `darkpool`, `earnings_tone_drift`

---

## 5. Verification & Test Plan

1. Execute prototype verification with `--result-dir trading_system/result --gh-pages-dir gh-pages`:
   - All 31 strategy HTML panels matched and populated with non-zero data rows.
   - Merged ensemble output validated.
   - Clean UTF-8 console output with 31-strategy matrix.
2. Run pytest suite (`.venv\Scripts\pytest.exe tests/ -v`) to ensure zero regressions in existing test suite.
3. Validate that `SKILL.md` passes markdown linter and accurately indexes all 31 strategies.
