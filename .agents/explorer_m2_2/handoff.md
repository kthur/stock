# Handoff Report - Explorer 2 (Milestone 2)

## 1. Observation
1. **Technical indicators and scores calculation**: Defined in `trading_system/src/core/strategy_engine.py` lines 209–307 inside the `_compute_technical_indicators` method of `HybridStrategyEngine` class:
   ```python
   def _compute_technical_indicators(self, price_bars: list) -> Dict:
   ```
   It calculates `rsi_score`, `macd_score`, `ema_score`, `bb_score`, and `trend_bias` (utilizing RSI, MACD histogram, EMA20/50 relation, Bollinger Bands position, and EMA20 slope), and combines them using the formula:
   ```python
   combined = rsi_score * 0.25 + macd_score * 0.30 + ema_score * 0.25 + bb_score * 0.15
   combined = combined * 0.95 + trend_bias * 0.05
   ```
2. **AI Expected Returns Model**: Defined in `trading_system/src/ai/prediction_model.py` lines 14–157 inside class `OnDevicePredictionModel`. Batch inference is run using:
   ```python
   def process_and_predict_all(self, prices_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
   ```
   The model predicts expected returns over horizons: `[1, 5, 10, 20, 30, 60, 120, 200]` days.
3. **Sentiment Analysis**:
   - `NLPEngine` in `trading_system/src/data_layer/nlp_engine.py` performs simple keyword counting.
   - `SentimentAnalyzer` in `trading_system/src/ai/sentiment.py` (lines 436–558) performs advanced financial lexicon-based analysis with bigrams, intensifiers, and negations, returning a score dictionary containing a `"score"` in the range `[-1.0, 1.0]`.
4. **SQLite Databases & Schemas**:
   - Central database `trading_system/market_indicators.db` is handled by `MarketIndicatorStorage` in `trading_system/src/data_layer/indicator_storage.py` and defines tables: `global_indicators`, `stock_universe`, and `ai_predictions` (lines 14–45).
   - Additional databases are defined in `trading_system/src/persistence/database.py`: `trade_logs.db` (for orders and executions), `asset_history.db` (for cash and asset snapshots), and `ai_predictions.db` (for trade signals and prediction evaluation).
5. **Interface Contract**: `PROJECT.md` lines 27–29 defines the contract:
   - Output table: `daily_stock_rankings` (fields: `date`, `symbol`, `name`, `composite_score`, `technical_score`, `ai_score`, `sentiment_score`, `rank`) stored in the SQLite database.

---

## 2. Logic Chain
1. To calculate the daily composite score:
   $$Composite = 0.40 \times Technical + 0.40 \times AI + 0.20 \times Sentiment$$
   each component must be scaled to `[0.0, 1.0]` (from Observation 1).
2. The `Technical` score from `HybridStrategyEngine._compute_technical_indicators()` is already scaled to `[0.0, 1.0]` (Observation 1).
3. The raw predictions from the XGBoost model represent expected returns (Observation 2). To scale them to `[0.0, 1.0]`, we can apply percentile ranking (`df['expected_return'].rank(pct=True)`) across all stocks in the universe for that date, which maps them robustly to `[0.0, 1.0]`.
4. The sentiment score from `SentimentAnalyzer` is in the range `[-1.0, 1.0]` (Observation 3). We can map this to `[0.0, 1.0]` using the linear transformation $\frac{Score + 1.0}{2.0}$, falling back to $0.5$ (neutral) if no news exists for a stock.
5. The resulting rankings must be written to the `daily_stock_rankings` table in `market_indicators.db` as dictated by `PROJECT.md` contracts (Observation 5).

---

## 3. Caveats
- **News/Sentiment Fetching Scalability**: Fetching and analyzing news for the entire stock universe (3000+ KRX and S&P 500 stocks) daily could lead to performance bottlenecks and rate limits. A caching table `daily_news_sentiment` or an asynchronous fetching mechanism is recommended.
- **Model Horizon Selection**: We assume the 5-day horizon for expected returns prediction represents the ideal baseline for the AI component, but this parameter should be configurable.

---

## 4. Conclusion
The daily scoring engine can be implemented via a script (`daily_scoring.py`) that:
- Reads the universe from `stock_universe` in `market_indicators.db`.
- Computes technical scores using `HybridStrategyEngine` and FDataReader historical prices.
- Computes AI scores by fetching expected returns from the `ai_predictions` table (or generating them via `OnDevicePredictionModel`) and applying percentile ranking.
- Computes Sentiment scores using `SentimentAnalyzer` on recent news with a fallback to `0.5`.
- Combines the scores, computes ranks, and stores the results in the `daily_stock_rankings` table in `market_indicators.db` under the fields defined by `PROJECT.md`.

---

## 5. Verification Method
1. **Code Locations and Imports**: Verify that `daily_scoring.py` can import all required components without errors:
   ```powershell
   python -c "from src.data_layer.indicator_storage import MarketIndicatorStorage; from src.core.strategy_engine import HybridStrategyEngine; from src.ai.sentiment import SentimentAnalyzer; from src.ai.prediction_model import OnDevicePredictionModel; print('Imports successful')"
   ```
2. **Schema Integrity**: Verify the database schema after running the scoring engine:
   ```powershell
   sqlite3 market_indicators.db "PRAGMA table_info(daily_stock_rankings);"
   ```
   This should output the column details matching: `date`, `symbol`, `name`, `composite_score`, `technical_score`, `ai_score`, `sentiment_score`, `rank`.
