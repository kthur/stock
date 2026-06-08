# Handoff Report: Sentiment Analysis Implementation

**Observation**
The implementation of Sentiment Analysis spans several files in the `trading_system/src/` directory. The `grep_search` and `view_file` results revealed the following exact files, classes, and methods:

1. `src/ai/sentiment.py`: 
   - Uses a lexicon-based approach for financial/trading text.
   - Has global lexicons: `POSITIVE_WORDS`, `NEGATIVE_WORDS`, `INTENSIFIERS`, `NEGATIONS`, and a `NEGATION_WINDOW` constant.
   - `analyze_sentiment(text: str) -> float`: Returns a score from -1.0 to +1.0. Checks for bigrams and unigrams, multiplies intensity by preceding intensifiers, and flips/halves scores if negations are found within the `NEGATION_WINDOW`. Uses a tanh-like normalisation method to calculate the compound score.
   - `SentimentAnalyzer` class: Includes an `analyze(self, text: str) -> dict` method returning detailed breakdowns `{'score': float, 'label': str, 'positive': float, 'negative': float}`.

2. `src/ai/llm_integration.py`:
   - Contains a `SentimentType` Enum (e.g., `VERY_BULLISH` = "매우 긍정적").
   - `LLMEngine._parse_opinion_response()` parses LLM JSON outputs and maps text sentiment like "매우 긍정적" to the `SentimentType` Enum for `InvestmentOpinion` generation.

3. `src/ai/llm_earnings_agent.py`:
   - `LLMEarningsAgent.analyze_earnings_call(symbol, transcript)`: Parses earning call transcripts. Currently uses a simulated ruleset based on keywords ("성장", "초과" vs "하향", "위축") to return a dictionary containing `sentiment_score` (e.g. 0.8, -0.6) and `guidance`.

4. `src/core/strategy_engine.py`:
   - `HybridStrategyEngine.analyze(...)` takes `news_sentiment: float` as a parameter.
   - Converts `news_sentiment > 0.5` to a `TradeSignal.BUY`, and `< -0.5` to `TradeSignal.SELL`.
   - Incorporates the sentiment score into a `combined_score` via `self.sentiment_weight` (default 0.3), along with signals like technical, ML, and darkpool.

**Logic Chain**
1. Based on searching the codebase for "sentiment", `src/ai/sentiment.py` emerged as the primary text-analysis module, confirming a lexicon-based approach.
2. Checking references to sentiment across the application led to `llm_integration.py` and `llm_earnings_agent.py`, which showed that sentiment is also derived as structured outputs from LLM evaluations of financial data and transcripts.
3. The strategy integration point is `src/core/strategy_engine.py`, which validates how sentiment directly dictates `TradeSignal` outputs via thresholding (>0.5 or <-0.5) and weighted combination.

**Caveats**
- Broker files (e.g., `src/broker/real_broker.py`, `KoreaInvestmentBroker`, `KiwoomBroker`) were examined but they do not process sentiment directly; they only receive the final TradeSignal.
- The `LLMEarningsAgent` currently relies on hardcoded keyword matching to simulate LLM sentiment scoring, meaning actual semantic LLM calls for this specific module are mocked.

**Conclusion**
Sentiment Analysis is primarily implemented via a domain-specific lexicon engine (`src/ai/sentiment.py`), supplemented by LLM-driven structured opinion parsers (`src/ai/llm_integration.py`, `src/ai/llm_earnings_agent.py`). These sentiment scores (scaled -1.0 to 1.0) are consumed by the `HybridStrategyEngine` (`src/core/strategy_engine.py`), weighted at 0.3 by default, and thresholded at +/- 0.5 to trigger explicit BUY/SELL signals.

**Verification Method**
1. Inspect `trading_system/src/ai/sentiment.py` to view the lexicon rules and scoring logic.
2. Run `pytest trading_system/tests/test_system.py` or execute `python trading_system/demo_full_integration.py` to see sentiment weights applied during strategy evaluation.
