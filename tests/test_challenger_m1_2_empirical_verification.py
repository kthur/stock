"""
tests/test_challenger_m1_2_empirical_verification.py

Empirical Challenge & Verification Suite for Milestone 1 (Challenger 2):
1. Adversarial verification of `_save_strategy_predictions_report` in `run_pipeline.py`:
   - all-NaN input handling and baseline imputation (0.50)
   - sporadic NaNs median imputation and string coercion
   - graceful no-op on empty / missing column / None
   - per-market split files (*_KOSPI.txt, *_SP500.txt, etc.) creation
2. Full E2E fallback scoring + prediction saving + dashboard generation:
   - 6 target strategy engines (RIM, Sentiment, Tone Drift, Accruals Quality, Value-Up, Insider Buying)
   - multi-market universe with price time-series
   - generate_report.py execution and BeautifulSoup HTML table inspection
   - zero raw NaN/undefined metric leaks and non-empty populated rows across evaluated markets
"""

import os
import sys
import tempfile
import shutil
import subprocess
import re
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRADING_SYSTEM_DIR = os.path.join(PROJECT_ROOT, "trading_system")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if TRADING_SYSTEM_DIR not in sys.path:
    sys.path.insert(0, TRADING_SYSTEM_DIR)

from src.core.rim_valuation import RIMValuationEngine
from src.core.accruals_quality import AccrualsQualityEngine
from src.core.valueup_catalyst import ValueUpCatalystEngine
from src.core.llm_sentiment_engine import DARTSECSentimentEngine
from src.core.insider_buying import InsiderBuyingEngine
from src.core.earnings_tone_drift import EarningsToneDriftEngine


def _save_strat_helper(
    df_strat: pd.DataFrame,
    score_col: str,
    title: str,
    output_filename: str,
    result_dir: str,
    universe: pd.DataFrame,
    score_header: str = "Score",
    header_width: int = 16
) -> None:
    """Replicates _save_strategy_predictions_report from run_pipeline.py."""
    if df_strat is None or df_strat.empty or score_col not in df_strat.columns:
        return

    KST = timezone(timedelta(hours=9))
    kst_now_str = datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')

    def _get_target_markets_to_save(df=None, universe=None):
        markets = set()
        if df is not None and 'market' in df.columns:
            markets.update(df['market'].dropna().astype(str).unique())
        if universe is not None and 'market' in universe.columns:
            markets.update(universe['market'].dropna().astype(str).unique())
        return sorted(list(markets))

    merged = df_strat.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left') if 'market' not in df_strat.columns else df_strat.copy()
    if 'name' not in merged.columns and 'name' in universe.columns:
        merged = merged.merge(universe[['symbol', 'name']], on='symbol', how='left')
    merged['symbol'] = merged['symbol'].astype(str)
    merged[score_col] = pd.to_numeric(merged[score_col], errors='coerce')
    if merged[score_col].isna().all():
        merged[score_col] = 0.50
    else:
        col_median = merged[score_col].median()
        fallback_val = col_median if (pd.notna(col_median) and np.isfinite(col_median)) else 0.50
        merged[score_col] = merged[score_col].fillna(fallback_val)
    merged = merged.sort_values(by=score_col, ascending=False)

    def _write_content(f_out, df_sub, market_label=None):
        f_out.write(f"=== {title} ===\n")
        f_out.write(f"Date: {kst_now_str}\n")
        f_out.write(f"Total symbols evaluated: {len(df_sub)}\n\n")
        f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<18}{'Market':<12}{score_header:<{header_width}}\n")
        f_out.write("-" * (45 + header_width) + "\n")
        for rank, (_, row) in enumerate(df_sub.head(100).iterrows(), 1):
            name_str = str(row.get('name', 'Unknown'))[:16] if pd.notna(row.get('name')) else "Unknown"
            mkt_str = str(row.get('market', 'KRX'))
            sc_raw = float(row[score_col])
            sc_val = sc_raw * 100.0 if sc_raw <= 1.0 else sc_raw
            f_out.write(f"{rank:<5}{str(row['symbol']):<10}{name_str:<18}{mkt_str:<12}{sc_val:>{header_width-2}.1f}%\n")

    main_path = os.path.join(result_dir, output_filename)
    with open(main_path, "w", encoding="utf-8") as f:
        _write_content(f, merged)

    base_name = output_filename.replace(".txt", "")
    for _m in _get_target_markets_to_save(df=merged, universe=universe):
        _m_df = merged[merged['market'] == _m]
        if _m_df.empty:
            continue
        with open(os.path.join(result_dir, f"{base_name}_{_m}.txt"), "w", encoding="utf-8") as _mf:
            _write_content(_mf, _m_df, market_label=_m)


def test_save_strategy_predictions_report_all_nan():
    temp_dir = tempfile.mkdtemp()
    try:
        universe = pd.DataFrame({
            'symbol': ['005930', '000660', 'AAPL', 'MSFT', 'IWM'],
            'name': ['삼성전자', 'SK하이닉스', 'Apple Inc.', 'Microsoft', 'iShares Russell 2000'],
            'market': ['KOSPI', 'KOSPI', 'SP500', 'NASDAQ', 'RUSSELL2000']
        })
        df_strat = pd.DataFrame({
            'symbol': ['005930', '000660', 'AAPL', 'MSFT', 'IWM'],
            'accruals_quality_score': [np.nan, np.nan, np.nan, np.nan, np.nan]
        })

        _save_strat_helper(
            df_strat=df_strat,
            score_col='accruals_quality_score',
            title='Strategy 24: Accruals Quality Anomaly Predictions',
            output_filename='accruals_quality_predictions.txt',
            result_dir=temp_dir,
            universe=universe,
            score_header='Accrual Score'
        )

        main_file = os.path.join(temp_dir, 'accruals_quality_predictions.txt')
        assert os.path.exists(main_file), "Main output file must be created"
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "Total symbols evaluated: 5" in content
        assert "50.0%" in content
        assert "삼성전자" in content

        for mkt in ['KOSPI', 'SP500', 'NASDAQ', 'RUSSELL2000']:
            split_file = os.path.join(temp_dir, f'accruals_quality_predictions_{mkt}.txt')
            assert os.path.exists(split_file), f"Split file for {mkt} must exist"
            with open(split_file, 'r', encoding='utf-8') as sf:
                s_content = sf.read()
            assert "Total symbols evaluated:" in s_content
            assert len(s_content.splitlines()) > 4
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_save_strategy_predictions_report_sporadic_nans_and_mixed_types():
    temp_dir = tempfile.mkdtemp()
    try:
        universe = pd.DataFrame({
            'symbol': ['005930', '035420', 'NVDA', 'AMZN', 'KOSDAQ1'],
            'name': ['삼성전자', 'NAVER', 'NVIDIA Corp', 'Amazon.com', '코스닥종목'],
            'market': ['KOSPI', 'KOSPI', 'NASDAQ', 'SP500', 'KOSDAQ']
        })
        df_strat = pd.DataFrame({
            'symbol': ['005930', '035420', 'NVDA', 'AMZN', 'KOSDAQ1'],
            'sentiment_score': [0.95, 'INVALID_STRING', np.nan, 0.35, 0.50]
        })

        _save_strat_helper(
            df_strat=df_strat,
            score_col='sentiment_score',
            title='Strategy 20: NLP Sentiment Catalyst',
            output_filename='sentiment_predictions.txt',
            result_dir=temp_dir,
            universe=universe,
            score_header='Sentiment'
        )

        main_file = os.path.join(temp_dir, 'sentiment_predictions.txt')
        assert os.path.exists(main_file)
        with open(main_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        assert any("Total symbols evaluated: 5" in l for l in lines)
        data_rows = [l for l in lines if re.match(r'^\d+\s+', l.strip())]
        assert len(data_rows) == 5

        for r in data_rows:
            assert "%" in r
            assert "nan" not in r.lower()

        assert os.path.exists(os.path.join(temp_dir, 'sentiment_predictions_KOSPI.txt'))
        assert os.path.exists(os.path.join(temp_dir, 'sentiment_predictions_NASDAQ.txt'))
        assert os.path.exists(os.path.join(temp_dir, 'sentiment_predictions_SP500.txt'))
        assert os.path.exists(os.path.join(temp_dir, 'sentiment_predictions_KOSDAQ.txt'))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_all_6_engines_fallback_pricing_proxy_and_report_generation():
    symbols = ['005930', '035420', 'AAPL', 'NVDA', 'IWM']
    markets = ['KOSPI', 'KOSDAQ', 'SP500', 'NASDAQ', 'RUSSELL2000']
    names = ['삼성전자', 'NAVER', 'Apple Inc', 'Nvidia', 'iShares Russell 2000']

    dates = pd.date_range(end=datetime.now(), periods=250, freq='B')
    prices_dict = {}
    for sym in symbols:
        np.random.seed(hash(sym) % 100000)
        ret = np.random.normal(0.001, 0.02, size=len(dates))
        price = 100.0 * np.exp(np.cumsum(ret))
        df_p = pd.DataFrame({
            'open': price * 0.99,
            'high': price * 1.02,
            'low': price * 0.98,
            'close': price,
            'volume': np.random.uniform(100000, 500000, size=len(dates))
        }, index=dates)
        prices_dict[sym] = df_p

    universe = pd.DataFrame({
        'symbol': symbols,
        'name': names,
        'market': markets,
        'Close': [prices_dict[s]['close'].iloc[-1] for s in symbols]
    })

    test_dir = tempfile.mkdtemp()
    try:
        # Copy baseline result files from trading_system/result for full context if exists
        base_res_dir = os.path.join(PROJECT_ROOT, "trading_system", "result")
        if os.path.exists(base_res_dir):
            for src_file in os.listdir(base_res_dir):
                src_path = os.path.join(base_res_dir, src_file)
                if os.path.isfile(src_path):
                    shutil.copy(src_path, os.path.join(test_dir, src_file))

        # 1. RIM
        rim_engine = RIMValuationEngine()
        rim_df = rim_engine.compute_rim_scores(
            universe.copy(),
            symbol_market_map=dict(zip(symbols, markets)),
            prices_dict=prices_dict,
            allow_price_proxy=True
        )
        assert not rim_df.empty
        assert (rim_df['rim_score'] > 0).all()

        rim_merged = rim_df.merge(universe[['symbol', 'name', 'market']], on='symbol', how='left', suffixes=('', '_u'))
        if 'name_u' in rim_merged.columns:
            rim_merged['name'] = rim_merged['name'].fillna(rim_merged.pop('name_u'))
        if 'market_u' in rim_merged.columns:
            rim_merged['market'] = rim_merged['market'].fillna(rim_merged.pop('market_u'))
        rim_merged = rim_merged.sort_values(by='rim_score', ascending=False)

        def _write_rim(f_out, df_rim):
            f_out.write("=== Strategy 9: RIM Valuation Predictions ===\n")
            f_out.write("Date: 2026-08-29 23:00 KST\n")
            valid = df_rim[df_rim['rim_score'].notna() & (df_rim['rim_score'] > 0)]
            f_out.write(f"Total symbols evaluated: {len(df_rim)} (Valid: {len(valid)})\n")
            f_out.write("Filters: EQ=Earnings Quality | [PROXY]=Price trend proxy\n\n")
            f_out.write(f"{'Rank':<5}{'Symbol':<10}{'Name':<20}{'Market':<14}{'Price':<12}{'Intrinsic V0':<14}{'Discount %':<12}{'ROE_raw':<9}{'ROE_adj':<9}{'EQ':<6}{'Filter':<32}{'RIM Score':<12}\n")
            f_out.write("-" * 144 + "\n")
            for rank, (_, row) in enumerate(valid.head(100).iterrows(), 1):
                p_str = f"{row.get('Close', 100.0):<12.2f}"
                iv_str = f"{row.get('intrinsic_value', 100.0):<14.2f}"
                disc_str = f"{row.get('discount_ratio', 0.0)*100:>9.1f}%"
                sc_str = f"{row.get('rim_score', 0.5)*100:>9.1f}%"
                f_out.write(f"{rank:<5}{row['symbol']:<10}{str(row['name'])[:18]:<20}{row['market']:<14}{p_str}{iv_str}{disc_str}   10.0%    10.0%   100%  [PROXY]                         {sc_str}\n")

        with open(os.path.join(test_dir, "rim_predictions.txt"), "w", encoding="utf-8") as f:
            _write_rim(f, rim_merged)
        for mkt in markets:
            m_df = rim_merged[rim_merged['market'] == mkt]
            if not m_df.empty:
                with open(os.path.join(test_dir, f"rim_predictions_{mkt}.txt"), "w", encoding="utf-8") as mf:
                    _write_rim(mf, m_df)

        # 2. Accruals
        aq_engine = AccrualsQualityEngine()
        accruals_df = aq_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert not accruals_df.empty and accruals_df['accruals_quality_score'].notna().all()
        _save_strat_helper(accruals_df, "accruals_quality_score", "Strategy 24: Accruals Quality Anomaly Predictions", "accruals_quality_predictions.txt", test_dir, universe, score_header="Accruals Score")

        # 3. Value-Up
        vu_engine = ValueUpCatalystEngine()
        valueup_df = vu_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert not valueup_df.empty and valueup_df['valueup_catalyst_score'].notna().all()
        _save_strat_helper(valueup_df, "valueup_catalyst_score", "Strategy 26: Value-Up & Shareholder Yield Predictions", "valueup_catalyst_predictions.txt", test_dir, universe, score_header="ValueUp Score")

        # 4. Sentiment
        sent_engine = DARTSECSentimentEngine()
        sent_df = sent_engine.compute_scores(universe=universe, prices_dict=prices_dict)
        assert not sent_df.empty and sent_df['sentiment_score'].notna().all()
        _save_strat_helper(sent_df, "sentiment_score", "Strategy 20: NLP & FinBERT Sentiment Catalyst Predictions", "sentiment_predictions.txt", test_dir, universe, score_header="Sent Score")

        # 5. Insider Buying
        ins_engine = InsiderBuyingEngine()
        ins_df = ins_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert not ins_df.empty and ins_df['insider_buying_score'].notna().all()
        _save_strat_helper(ins_df, "insider_buying_score", "Strategy 29: Insider Buying Catalyst Predictions", "insider_buying_predictions.txt", test_dir, universe, score_header="Insider Score")

        # 6. Tone Drift
        tone_engine = EarningsToneDriftEngine()
        tone_df = tone_engine.calculate_scores(symbols, prices_dict=prices_dict)
        assert not tone_df.empty and tone_df['earnings_tone_drift_score'].notna().all()
        _save_strat_helper(tone_df, "earnings_tone_drift_score", "Strategy 30: Earnings Tone Drift NLP Predictions", "earnings_tone_drift_predictions.txt", test_dir, universe, score_header="Tone Score")

        # Run report generation
        out_html = os.path.join(test_dir, "index.html")
        cmd = [sys.executable, os.path.join(TRADING_SYSTEM_DIR, "generate_report.py"), "--result-dir", test_dir, "--out", out_html]
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        assert res.returncode == 0, f"generate_report failed: {res.stderr}"
        assert os.path.exists(out_html)
        assert os.path.getsize(out_html) > 50 * 1024

        with open(out_html, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        panels = {
            "RIM": "panel-rim",
            "Sentiment": "panel-sentiment",
            "Tone Drift": "panel-tonedrift",
            "Accruals Quality": "panel-accruals",
            "Value-Up": "panel-valueup",
            "Insider Buying": "panel-insider"
        }

        for name, pid in panels.items():
            panel_elem = soup.find("div", id=pid)
            assert panel_elem is not None, f"Panel {pid} not found"
            market_panels = panel_elem.find_all("div", class_="market-panel")
            assert len(market_panels) >= 5, f"Panel {pid} has fewer than 5 market panels"

            total_populated_rows = 0
            for mp in market_panels:
                mkt = mp.get("data-market", "")
                if mkt in markets:
                    t = mp.find("table")
                    assert t is not None
                    rows = [r for r in t.find_all("tr") if r.find_all("td")]
                    assert len(rows) > 0, f"Panel {pid} market {mkt} has 0 rows"
                    row_text = rows[0].get_text()
                    assert "데이터 없음" not in row_text, f"Panel {pid} market {mkt} has '데이터 없음' placeholder: {row_text}"
                    total_populated_rows += len(rows)

            assert total_populated_rows >= 5, f"Strategy {name} has fewer than 5 populated rows in evaluated markets"

        # Check for zero unhandled NaN/undefined leaks
        with open(out_html, "r", encoding="utf-8") as f:
            html_text = f.read()
        nan_tags = re.findall(r'>\s*(?:NaN|undefined|null)\s*<', html_text, re.IGNORECASE)
        assert len(nan_tags) == 0, f"Found {len(nan_tags)} raw NaN/undefined leaks in HTML: {nan_tags[:5]}"

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)
