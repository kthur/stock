# Handoff Report: Milestone 5 (R5: LLM/NLP DART & SEC Filing Sentiment Engine Design)

## 1. Observation

1. **System & Pipeline Structure**:
   - `trading_system/run_pipeline.py` orchestrates an 18-strategy quantitative trading system for 3,379 symbols across KOSPI, KOSDAQ, KONEX, and SP500 markets.
   - Strategy 10 (`EventDrivenEngine` in `trading_system/src/core/event_driven.py`) currently scores OpenDART disclosures based on string keyword matching (`'유상증자' in report_nm`, `'자기주식' in report_nm`) and static category weights (`EVENT_WEIGHTS`).
2. **Project Requirements**:
   - `d:\Finance\code\stock\.agents\orchestrator\PROJECT.md` line 10 & line 56-58:
     - `src/core/llm_sentiment_engine.py`: Extract sentiment/tone scores from DART/SEC filings using LLM/FinBERT tone analysis.
     - Interface contract: `LLMSentimentEngine.analyze_filing_sentiment(filing_text, Market='KOSPI'|'SP500')` -> `SentimentScore(positive, negative, tone_score, confidence)`.
     - Integration with `EventDrivenEngine`: `EventDrivenEngine.calculate_event_score(filing_data, sentiment_score)` -> modified catalyst score.
3. **Configuration & Environment Capabilities**:
   - `trading_system/src/config.py` contains `TradingConfig` with `openai_api_key`, `dart_api_key`, and sentiment filter threshold `sentiment_risk_threshold: float = 0.70`.
   - Python environment runs via `.venv/bin/python` (`.venv/Scripts/python.exe`). Pytest configuration uses `conftest.py` setting `sys.path` with `trading_system` prioritized.

---

## 2. Logic Chain

1. **Need for Dual-Mode Architecture**:
   - **Observation Ref**: Observation 1 & 3.
   - **Reasoning**: In production / cloud environments, HuggingFace transformers (`ProsusAI/finbert`, `snunlp/KR-FinBERT-SC`) provide state-of-the-art filing tone analysis. However, in offline, zero-network, or CPU-constrained environments (e.g. CODE_ONLY execution mode), model downloading may fail. Therefore, `LLMSentimentEngine` must implement a robust dual-mode architecture:
     a) Primary Mode: FinBERT / HuggingFace Transformers.
     b) Fallback Mode: Loughran-McDonald (LM) Financial Dictionary for US filings and Korean Financial Lexicon & regex scoring for KRX filings.
2. **Key Section Extraction**:
   - **Observation Ref**: Observation 2.
   - **Reasoning**: Unstructured SEC 10-K/10-Q and DART filings contain thousands of boilerplate lines. Extracting high-signal narrative sections (SEC Item 1A Risk Factors, Item 7 MD&A, and DART "이사회의 경영진단" / "사업의 내용") focuses NLP tone analysis on the narrative sections that contain management signal, while avoiding transformer token truncation.
3. **Event Catalyst Multiplier Integration**:
   - **Observation Ref**: Observation 1 & 2.
   - **Reasoning**: `EventDrivenEngine` assigns disclosure base weights $W_{base} \in [0.0, 1.0]$. By introducing a sentiment multiplier $M_{sent} = 1.0 + \gamma \cdot \text{tone\_score} \cdot \text{confidence}$ (with $\gamma = 0.35$), positive disclosure narrative tone boosts catalyst weight up to $1.35\times$, while negative/litigious narrative tone penalizes weight down to $0.65\times$.
4. **Clean Integration & Test Harness**:
   - **Observation Ref**: Observation 1 & 3.
   - **Reasoning**: Placing the primary implementation in `trading_system/src/core/llm_sentiment_engine.py` and a forwarder in `src/core/llm_sentiment_engine.py` maintains consistency with previous milestones (M1–M4) and ensures seamless import resolution in pytest and `run_pipeline.py`.

---

## 3. Caveats

- **Network Availability**: Primary transformer mode requires downloading model weights (`ProsusAI/finbert`, `snunlp/KR-FinBERT-SC`). In offline or restricted network environments, the system seamlessly falls back to Loughran-McDonald & Korean dictionary mode without raising exceptions.
- **Large Document Processing**: Extremely large filings (e.g., 50MB+ raw HTML) should be pre-truncated during section extraction to prevent high RAM usage.

---

## 4. Conclusion

The technical design for Milestone 5 (R5: LLM/NLP DART & SEC Filing Sentiment Engine) is fully specified and documented in `d:\Finance\code\stock\.agents\explorer_m5_2\design.md`.

Key deliverables designed:
1. Dataclass `SentimentScore` in `src/core/llm_sentiment_engine.py`.
2. Class `LLMSentimentEngine` with `analyze_filing_sentiment(filing_text, market)` supporting dual-mode execution (FinBERT primary vs Loughran-McDonald & Korean Lexicon fallback).
3. Text preprocessor and regex key section extractor (Item 1A, Item 7 MD&A, DART MD&A/Business).
4. `EventDrivenEngine` enhancement incorporating filing sentiment metrics into catalyst scores via multiplier $M_{sent} \in [0.65, 1.35]$.
5. Unit test specification in `tests/test_llm_sentiment_engine.py` covering transformer primary mode, dictionary fallback mode, section extraction, normalization bounds, and `EventDrivenEngine` integration.

---

## 5. Verification Method

1. **Design Document Verification**:
   - Inspect `d:\Finance\code\stock\.agents\explorer_m5_2\design.md`.
2. **Implementation Verification (for Worker agent upon implementation)**:
   - Run unit test suite for Milestone 5:
     ```bash
     .venv/bin/pytest tests/test_llm_sentiment_engine.py -v
     ```
   - Run complete repository test suite to ensure zero regression across all 18 strategies:
     ```bash
     .venv/bin/pytest tests/ -v
     ```
3. **Invalidation Conditions**:
   - `LLMSentimentEngine` fails to return `tone_score` normalized in $[-1.0, +1.0]$.
   - Fallback mode throws uncaught exceptions when `transformers` or GPU is missing.
   - `EventDrivenEngine` catalyst scores overflow the $[0.0, 1.0]$ bounds.
