# ⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

"""
Unit tests for LLM/NLP Filing Sentiment Engine (Milestone 5).
"""

import os
import tempfile
import pytest

from trading_system.src.core.llm_sentiment_engine import (
    FilingSentimentMetrics,
    LLMSentimentEngine
)
from trading_system.src.data_layer.indicator_storage import MarketIndicatorStorage
from trading_system.src.core.event_driven import EventDrivenEngine
from trading_system.src.analysis.coverage_analyzer import StrategyCoverageAnalyzer


def test_filing_sentiment_metrics_dataclass():
    """Test FilingSentimentMetrics dataclass fields and to_dict method."""
    metrics = FilingSentimentMetrics(
        symbol="005930",
        filing_date="2026-07-31",
        filing_tone_score=0.85,
        catalyst_surprise_score=0.90,
        composite_sentiment_score=0.87,
        confidence_score=0.70,
        source_type="OFFLINE_LEXICON"
    )
    d = metrics.to_dict()
    assert d['symbol'] == "005930"
    assert d['filing_tone_score'] == 0.85
    assert d['catalyst_surprise_score'] == 0.90
    assert d['composite_sentiment_score'] == 0.87
    assert d['confidence_score'] == 0.70
    assert d['source_type'] == "OFFLINE_LEXICON"


def test_offline_lexicon_korean_dart():
    """Test offline lexicon parser for Korean DART disclosures."""
    engine = LLMSentimentEngine()
    
    # Positive Korean text
    text_pos = "당사는 영업이익증가 및 실적개선으로 흑자전환에 성공하였으며 자기주식소각 및 무상증자를 결정하였습니다."
    metrics_pos = engine.analyze_filing("005930", text_pos, filing_date="2026-07-31", market="KOSPI")
    assert metrics_pos.filing_tone_score > 0.5
    assert metrics_pos.composite_sentiment_score > 0.5
    assert metrics_pos.source_type == "OFFLINE_LEXICON"
    assert metrics_pos.confidence_score == 0.7

    # Negative Korean text
    text_neg = "당사는 실적 감소로 적자전환되었으며 유상증자 및 감자를 진행하고 경영진 배임 소송이 발생하였습니다."
    metrics_neg = engine.analyze_filing("003550", text_neg, filing_date="2026-07-31", market="KOSPI")
    assert metrics_neg.filing_tone_score < 0.5
    assert metrics_neg.composite_sentiment_score < 0.5


def test_offline_lexicon_english_sec():
    """Test offline lexicon parser for English SEC 10-K/10-Q disclosures."""
    engine = LLMSentimentEngine()

    # Positive English text
    text_pos = "The company reported strong revenue growth, earnings beat expectations, and approved a major share buyback program."
    metrics_pos = engine.analyze_filing("AAPL", text_pos, filing_date="2026-07-31", market="SP500")
    assert metrics_pos.filing_tone_score > 0.5
    assert metrics_pos.composite_sentiment_score > 0.5

    # Negative English text
    text_neg = "The company faces severe dilution, ongoing litigation, asset impairment, and doubts about going concern status."
    metrics_neg = engine.analyze_filing("TSLA", text_neg, filing_date="2026-07-31", market="SP500")
    assert metrics_neg.filing_tone_score < 0.5
    assert metrics_neg.composite_sentiment_score < 0.5


def test_sentiment_formula_exactness():
    """Test exact mathematical formula S_tone = clip(0.5 + (N_pos - N_neg)/(2*(N_pos + N_neg + 1)), 0, 1)."""
    engine = LLMSentimentEngine()
    
    # 3 positive terms, 0 negative terms -> N_pos=3, N_neg=0
    # S_tone = 0.5 + 3 / (2 * (3 + 0 + 1)) = 0.5 + 3/8 = 0.875
    text_3pos = "실적개선 흑자전환 무상증자"
    m = engine._score_offline_lexicon(text_3pos, symbol="TEST", market="KOSPI")
    assert pytest.approx(m.filing_tone_score, abs=1e-3) == 0.875

    # Composite formula: 0.6 * tone + 0.4 * surprise
    expected_composite = 0.6 * m.filing_tone_score + 0.4 * m.catalyst_surprise_score
    assert pytest.approx(m.composite_sentiment_score, abs=1e-3) == expected_composite


def test_sqlite_cache_integration():
    """Test SQLite storage get_filing_sentiment and save_filing_sentiment."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        storage = MarketIndicatorStorage(db_path=db_path)
        metrics = FilingSentimentMetrics(
            symbol="005930",
            filing_date="2026-07-31",
            filing_tone_score=0.88,
            catalyst_surprise_score=0.92,
            composite_sentiment_score=0.896,
            confidence_score=1.0,
            source_type="LLM_FINBERT"
        )

        storage.save_filing_sentiment(metrics, filing_id="FILING_001")
        cached = storage.get_filing_sentiment("005930", filing_date="2026-07-31", filing_id="FILING_001")

        assert cached is not None
        assert cached['symbol'] == "005930"
        assert cached['filing_tone_score'] == 0.88
        assert cached['composite_sentiment_score'] == 0.896
        assert cached['source_type'] == "LLM_FINBERT"

        # Verify engine uses cache hit
        engine = LLMSentimentEngine(db_storage=storage)
        m_cached = engine.analyze_filing("005930", text="New text ignored due to cache", filing_date="2026-07-31", filing_id="FILING_001")
        assert m_cached.source_type == "CACHE"
        assert m_cached.composite_sentiment_score == 0.896
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_event_driven_sentiment_multiplier():
    """Test EventDrivenEngine.incorporate_filing_sentiment multiplier scaling and bounds [0.5x, 1.5x]."""
    event_engine = EventDrivenEngine()

    base_score = 0.60

    # High positive composite score (0.95) -> Multiplier = 1.0 + (0.95 - 0.5)*2.0*1.0 * 0.5 = 1.45x
    pos_metrics = FilingSentimentMetrics(
        symbol="005930",
        filing_date="2026-07-31",
        filing_tone_score=0.95,
        catalyst_surprise_score=0.95,
        composite_sentiment_score=0.95,
        confidence_score=1.0,
        source_type="LLM_FINBERT"
    )
    adjusted_pos = event_engine.incorporate_filing_sentiment("005930", base_score, pos_metrics)
    assert pytest.approx(adjusted_pos, abs=1e-3) == min(1.0, base_score * 1.45)

    # Low negative composite score (0.10) -> Multiplier = 1.0 + (0.10 - 0.5)*2.0*1.0 * 0.5 = 0.60x
    neg_metrics = FilingSentimentMetrics(
        symbol="003550",
        filing_date="2026-07-31",
        filing_tone_score=0.10,
        catalyst_surprise_score=0.10,
        composite_sentiment_score=0.10,
        confidence_score=1.0,
        source_type="OFFLINE_LEXICON"
    )
    adjusted_neg = event_engine.incorporate_filing_sentiment("003550", base_score, neg_metrics)
    assert pytest.approx(adjusted_neg, abs=1e-3) == base_score * 0.60

    # Extreme bounds check: multiplier clamped within [0.5, 1.5] and adjusted score clamped within [0.0, 1.0]
    extreme_pos = FilingSentimentMetrics("SYM", "2026", 1.0, 1.0, 1.0, 1.0, "LLM_FINBERT")
    adj_ext = event_engine.incorporate_filing_sentiment("SYM", 0.90, extreme_pos)
    assert adj_ext <= 1.0

    extreme_neg = FilingSentimentMetrics("SYM", "2026", 0.0, 0.0, 0.0, 1.0, "OFFLINE_LEXICON")
    adj_ext_neg = event_engine.incorporate_filing_sentiment("SYM", 0.10, extreme_neg)
    assert adj_ext_neg >= 0.0


def test_m5_sentiment_coverage_report():
    """Test generate_m5_sentiment_report formatting."""
    analyzer = StrategyCoverageAnalyzer()

    metrics_list = [
        FilingSentimentMetrics("005930", "2026-07-31", 0.90, 0.95, 0.92, 1.0, "LLM_FINBERT"),
        FilingSentimentMetrics("003550", "2026-07-31", 0.15, 0.20, 0.17, 0.7, "OFFLINE_LEXICON"),
        FilingSentimentMetrics("AAPL.US", "2026-07-31", 0.80, 0.85, 0.82, 0.7, "CACHE")
    ]

    report = analyzer.generate_m5_sentiment_report(metrics_list, kst_now_str="2026-07-31 21:30 KST")
    assert "[MILESTONE 5: LLM/NLP DART & SEC FILING SENTIMENT REPORT]" in report
    assert "Total Corporate Filings Analyzed: 3" in report
    assert "Primary LLM / FinBERT Pipeline: 1 (33.3%)" in report
    assert "Offline Lexicon Fallback      : 1 (33.3%)" in report
    assert "SQLite Cache Hits             : 1 (33.3%)" in report


def test_korean_dart_with_english_headers():
    """Test that Korean DART filings with leading English headers evaluate correctly with Korean lexicon mode."""
    engine = LLMSentimentEngine()

    # Case 1: Short English header prepended to positive Korean disclosure
    text1 = "DART Filing 005930: 당사는 흑자전환 및 영업이익증가로 인한 실적개선이 시뮬레이션되었습니다."
    metrics1 = engine.analyze_filing("005930", text1, filing_date="2026-07-31", market="KOSPI")
    assert metrics1.filing_tone_score > 0.50
    assert metrics1.composite_sentiment_score > 0.50
    assert metrics1.source_type == "OFFLINE_LEXICON"

    # Case 2: Long English header (>1000 characters) prepended to Korean DART text
    header = "DART Official Filing Metadata Header Report for Stock Symbol 005930. " * 20  # ~1400 chars
    text2 = header + "당사는 영업이익증가 및 실적개선으로 흑자전환에 성공하였습니다."
    metrics2 = engine.analyze_filing("005930", text2, filing_date="2026-07-31", market="KOSPI")
    assert metrics2.filing_tone_score > 0.50
    assert metrics2.composite_sentiment_score > 0.50
    assert metrics2.source_type == "OFFLINE_LEXICON"

    # Case 3: Market specified as SP500 but containing Hangul text
    text3 = "DART Report for Dual-Listed Symbol 005930. 당사는 흑자전환 및 영업이익증가"
    metrics3 = engine.analyze_filing("005930", text3, filing_date="2026-07-31", market="SP500")
    assert metrics3.filing_tone_score > 0.50
    assert metrics3.composite_sentiment_score > 0.50
    assert metrics3.source_type == "OFFLINE_LEXICON"


