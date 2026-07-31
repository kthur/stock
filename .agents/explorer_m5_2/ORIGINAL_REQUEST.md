## 2026-07-31T12:30:12Z
<USER_REQUEST>
You are explorer_m5_2, the Technical Architecture Explorer for Milestone 5 (R5: LLM/NLP DART & SEC Filing Sentiment Engine).

Your working directory is `d:\Finance\code\stock\.agents\explorer_m5_2`. Please create your working directory first if it does not exist.

Mission:
Investigate the codebase and design the technical specifications and implementation plan for Milestone 5 (R5: LLM/NLP DART & SEC Filing Sentiment Engine).

Scope & Specifications:
1. Module location: `trading_system/src/core/llm_sentiment_engine.py` (and root forwarder `src/core/llm_sentiment_engine.py`).
2. Feature Details:
   - `LLMSentimentEngine(storage=None, cache_db_path="indicator_storage.db")`:
     - Structured dataclass `FilingSentimentMetrics(symbol, filing_date, filing_tone_score, catalyst_surprise_score, composite_sentiment_score, confidence_score, source_type)`.
     - Dual Sentiment Architecture:
       a. Primary LLM / FinBERT sentiment scoring interface for DART (KOSPI/KOSDAQ) disclosures and SEC (SP500) 10-K/10-Q filings.
       b. Robust offline NLP lexicon fallback parser (financial sentiment dictionary for Korean and English corporate disclosures) when API/models are offline or unconfigured.
     - Local SQLite Caching: Cache sentiment results by `(symbol, filing_date, filing_id)` in `MarketIndicatorStorage` (`indicator_storage.db`) to avoid redundant processing.
3. Integration with `EventDrivenEngine` (`trading_system/src/core/event_driven.py`):
   - Inspect `EventDrivenEngine` (catalyst scoring, surprise detection, filing flags).
   - Design integration method `incorporate_filing_sentiment(symbol, base_catalyst_score)` adjusting event scores with sentiment intensity multipliers ($0.5\times$ to $1.5\times$).
4. Integration with `EnsembleScoringEngine` (`trading_system/src/ai/ensemble_scorer.py`) & `run_pipeline.py`:
   - Inspect `run_pipeline.py` Step 10/11: instantiate `LLMSentimentEngine`, process active symbols, pass sentiment signals to `EventDrivenEngine` and `EnsembleScoringEngine`.
   - Design section `[MILESTONE 5: LLM/NLP DART & SEC FILING SENTIMENT REPORT]` for `strategy_data_coverage_report.txt`.
5. Unit Tests Plan:
   - Design comprehensive unit test suite in `trading_system/tests/test_llm_sentiment_engine.py` and `tests/test_llm_sentiment_engine.py`.

Please inspect `trading_system/src/core/event_driven.py`, `trading_system/src/data_layer/indicator_storage.py`, `trading_system/src/ai/ensemble_scorer.py`, and `trading_system/run_pipeline.py`.
Write your full technical design report to `d:\Finance\code\stock\.agents\explorer_m5_2\handoff.md` and `progress.md`.
Notify orchestrator when done via `send_message`.
</USER_REQUEST>
