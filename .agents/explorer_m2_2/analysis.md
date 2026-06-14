# Post-Market Stock Scoring Backend Analysis

## Executive Summary
This report analyzes the existing codebase to design a post-market stock scoring engine for **Milestone 2**. We examine:
1. `HybridStrategyEngine` for technical indicator calculations.
2. `OnDevicePredictionModel` (XGBoost) for expected returns prediction.
3. `NLPEngine` and `SentimentAnalyzer` for financial sentiment scoring.
4. Existing SQLite databases (`market_indicators.db`, `trade_logs.db`, `asset_history.db`, and `ai_predictions.db`) and their schemas.
5. A proposed design for a daily scoring script (`daily_scoring.py`) that computes the composite score:
   $$Composite = 0.40 \times Technical + 0.40 \times AI + 0.20 \times Sentiment$$
   and stores rankings in the `daily_stock_rankings` table in `market_indicators.db`.

---

## 1. Technical Indicators & Scoring (`HybridStrategyEngine`)
- **File Path**: `trading_system/src/core/strategy_engine.py` (Lines 86–880)
- **Method for Technical Scores**: `_compute_technical_indicators(self, price_bars: list) -> Dict` (Lines 209–307)

### Mechanism of Technical Scoring
The method extracts close prices from `price_bars` (requiring a minimum of 20 bars) and calculates a weighted blend of indicators:
1. **RSI (14)**: Calculated via `_calc_rsi(closes)`. It maps values to `rsi_score` (0.9 if RSI < 25, 0.6 if RSI < 35, 0.1 if RSI > 75, 0.3 if RSI > 65, else 0.5).
2. **MACD Histogram**: Calculated via `_calc_macd_histogram(closes)`. It compares current vs. previous histogram values to identify golden/dead crosses (0.9 for Golden Cross, 0.1 for Dead Cross, 0.65 if positive, 0.35 if negative, else 0.5).
3. **EMA Alignment**: Compares EMA20 and EMA50. If EMA20[-1] > EMA50[-1], score is 0.7; if EMA20[-1] < EMA50[-1], score is 0.3; else 0.5.
4. **Bollinger Bands Position**: BB position `bb_pos` is calculated via `_calc_bollinger_position(closes)` mapping current close relative to upper/lower band limits (0 to 1). BB score is 0.85 if `bb_pos < 0.15` (oversold), 0.15 if `bb_pos > 0.85` (overbought), else 0.5.
5. **Trend Bias**: EMA20 slope and cross position. If EMA20 > EMA50 and EMA20 slope > 0.001, trend bias is 0.8; if EMA20 < EMA50 and EMA20 slope < -0.001, trend bias is 0.2; else 0.5.

The indicators are combined as follows:
```python
combined = rsi_score * 0.25 + macd_score * 0.30 + ema_score * 0.25 + bb_score * 0.15
combined = combined * 0.95 + trend_bias * 0.05
```
This combined score is a float in the range `[0.0, 1.0]`.

### Exposes API
- **Public Entry Point**: `analyze(self, symbol: str, market_data: Dict, news_sentiment: float, price_bars: Optional[List[Any]] = None, cash_ratio: float = 0.5) -> StrategyResult` (Lines 309–624).
- **Extraction for Daily Scoring**: The daily script can either invoke `_compute_technical_indicators(price_bars)` directly (requiring price bars) or wrap it in a clean public method. Since the daily script only requires the technical score, direct access to `_compute_technical_indicators` is most suitable.

---

## 2. XGBoost Expected Returns Model (`OnDevicePredictionModel`)
- **File Path**: `trading_system/src/ai/prediction_model.py` (Lines 14–157)
- **Class**: `OnDevicePredictionModel`

### How It Works
- The model trains individual `xgb.XGBRegressor` instances for various horizons: `[1, 5, 10, 20, 30, 60, 120, 200]` days.
- **Features Used**: `['ret_1d', 'ret_5d', 'ret_20d', 'ret_60d', 'dist_sma_20', 'vol_20d']`. These are computed by `_create_features(df)` using a historical Close price DataFrame.
- **Targets**: `df[f'target_{h}d'] = df['Close'].shift(-h) / df['Close'] - 1` (forward return over horizon `h`).

### Generating & Retrieving Predictions
1. **Generating predictions in batch**:
   Call `process_and_predict_all(self, prices_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame`.
   - Input: A dictionary mapping `symbol` to yfinance/FDR OHLCV DataFrame (must have >= 65 rows).
   - Output: A pandas DataFrame containing `symbol` and expected return values for each horizon `[1, 5, 10, 20, 30, 60, 120, 200]` as column headers.
2. **Retrieving predictions from Database**:
   - `MarketIndicatorStorage` in `trading_system/src/data_layer/indicator_storage.py` saves these predictions via `save_predictions(df_preds, date_str)` to the `ai_predictions` table.
   - Predictions are retrieved by calling `get_predictions(date_str)` on `MarketIndicatorStorage`. If `date_str` is None, it returns the latest predictions.

---

## 3. NLP & Sentiment Scoring (`NLPEngine` / `SentimentAnalyzer`)
The codebase contains two sentiment analysis implementations:

### A. `NLPEngine`
- **File Path**: `trading_system/src/data_layer/nlp_engine.py` (Lines 36–137)
- **Method**: `analyze_sentiment(self, text: str) -> tuple[Sentiment, float]`
- **Mechanism**: Simple keyword matching. Counts predefined positive/negative keywords in lowercase text.
- **Score Range**: Returns a tuple of `(Sentiment, score)` where the score is a float in the range `[-1.0, 1.0]`.

### B. `SentimentAnalyzer`
- **File Path**: `trading_system/src/ai/sentiment.py` (Lines 436–559)
- **Method**: `analyze(self, text: str) -> dict`
- **Mechanism**: A domain-specific financial sentiment analyzer using positive/negative financial lexicons with weights, handling n-grams (bigrams), intensifiers, negation window, and compound normalization with tanh-like scaling.
- **Score Range**: Returns a dictionary:
  ```python
  {
      "score": float,     # Compound score in [-1.0, 1.0]
      "label": str,       # 'positive' | 'negative' | 'neutral'
      "positive": float,  # Normalised positive score in [0.0, 1.0]
      "negative": float   # Normalised negative score in [0.0, 1.0]
  }
  ```
- **Usage Recommendation**: For the daily scoring engine, `SentimentAnalyzer` from `src.ai.sentiment` is highly recommended because it utilizes domain-specific vocabulary and advanced linguistic adjustments (intensifiers/negations). The score can be scaled to `[0.0, 1.0]` via:
  $$Scaled\_Sentiment = \frac{Score + 1.0}{2.0}$$
  If no news is found for a stock, it should default to `0.5` (neutral).

---

## 4. SQLite Database Architecture & Schemas
The codebase interacts with four SQLite databases, each with dedicated schema definitions and access code:

### 1. `market_indicators.db`
- **Access File**: `trading_system/src/data_layer/indicator_storage.py` (Class `MarketIndicatorStorage`)
- **Tables**:
  - `stock_universe`:
    ```sql
    CREATE TABLE IF NOT EXISTS stock_universe (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        market TEXT
    )
    ```
  - `ai_predictions`:
    ```sql
    CREATE TABLE IF NOT EXISTS ai_predictions (
        date TEXT,
        symbol TEXT,
        horizon INTEGER,
        expected_return REAL,
        PRIMARY KEY (date, symbol, horizon)
    )
    ```
  - `global_indicators`:
    ```sql
    CREATE TABLE IF NOT EXISTS global_indicators (
        date TEXT, symbol TEXT, name TEXT, price REAL, change_pct REAL, PRIMARY KEY (date, symbol)
    )
    ```

### 2. `trade_logs.db`
- **Access File**: `trading_system/src/persistence/database.py` (Class `TradeLogger` - asynchronous via `aiosqlite`)
- **Tables**: `orders` and `executions` for trade execution tracking.

### 3. `asset_history.db`
- **Access File**: `trading_system/src/persistence/database.py` (Class `AssetHistoryDB` - asynchronous via `aiosqlite`)
- **Tables**: `asset_snapshots` for tracking portfolio value.

### 4. `ai_predictions.db`
- **Access File**: `trading_system/src/persistence/database.py` (Class `AIPredictionDB` - asynchronous via `aiosqlite`)
- **Tables**: `predictions` for tracking trade decisions and evaluating historical AI accuracy.

---

## 5. Daily Scoring Engine Design Proposal
We propose a daily post-market scoring script `trading_system/scripts/daily_scoring.py` that runs daily to compute composite scores and rankings.

### Table Schema Definition
To comply with the contract specified in `PROJECT.md` (under "Daily Scoring Engine ↔ Database"), we will create the `daily_stock_rankings` table in the existing `market_indicators.db` database:
```sql
CREATE TABLE IF NOT EXISTS daily_stock_rankings (
    date TEXT,                  -- 'YYYY-MM-DD'
    symbol TEXT,                -- e.g., 'AAPL', '005930'
    name TEXT,                  -- stock name
    composite_score REAL,       -- 0.0 to 1.0
    technical_score REAL,       -- 0.0 to 1.0
    ai_score REAL,              -- 0.0 to 1.0 (percentile normalised expected return)
    sentiment_score REAL,       -- 0.0 to 1.0 (mapped from sentiment analyzer)
    rank INTEGER,               -- 1 to N (sorted by composite_score desc)
    PRIMARY KEY (date, symbol)
);
```

### Normalization Logic for AI & Sentiment
To compute the composite score, all three components must be on the same `[0.0, 1.0]` scale:
1. **Technical Score**: Calculated directly from `HybridStrategyEngine._compute_technical_indicators()`, which naturally outputs a score in `[0.0, 1.0]`.
2. **AI Score**: The raw predicted expected returns (e.g., `-0.05` to `0.10`) must be scaled. We use **Percentile Rank** across the universe for that date:
   $$AI\_Score = \text{Percentile Rank}(Expected\_Return)$$
   *Rationale*: Percentile ranking is robust, eliminates outliers, and is scale-invariant, mapping the highest return to 1.0 and lowest to 0.0.
3. **Sentiment Score**: The compound score from `SentimentAnalyzer` in `[-1.0, 1.0]` is scaled via:
   $$Sentiment\_Score = \frac{Score + 1.0}{2.0}$$
   If no news is processed for the symbol, the score falls back to a neutral `0.5`.

### Pseudo-code Implementation Design
Below is the python execution model proposed for `daily_scoring.py`:

```python
import sys
import os
import sqlite3
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Import project modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.data_layer.market_data_handler import MarketDataHandler
from src.core.strategy_engine import HybridStrategyEngine
from src.ai.sentiment import SentimentAnalyzer

def get_db_connection(db_path="market_indicators.db"):
    return sqlite3.connect(db_path)

def create_rankings_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_stock_rankings (
            date TEXT,
            symbol TEXT,
            name TEXT,
            composite_score REAL,
            technical_score REAL,
            ai_score REAL,
            sentiment_score REAL,
            rank INTEGER,
            PRIMARY KEY (date, symbol)
        )
    """)
    conn.commit()

def calculate_technical_score(symbol, market_handler, engine):
    try:
        # Fetch 60 bars for indicators
        bars = market_handler.fetch_historical_data(symbol, period="3mo")
        if not bars or len(bars) < 20:
            return 0.5
        result = engine._compute_technical_indicators(bars)
        return float(result["score"])
    except Exception:
        return 0.5

def fetch_sentiment_score(symbol, analyzer):
    # Propose integration with RSS feeds or News API
    # Here, we average the scores of collected articles or return 0.5 fallback
    articles = [] # Fetch news title + contents for 'symbol'
    if not articles:
        return 0.5
    
    scores = []
    for art in articles:
        res = analyzer.analyze(art)
        # Scale score from [-1, 1] to [0, 1]
        scores.append((res["score"] + 1.0) / 2.0)
    return sum(scores) / len(scores)

def run_daily_scoring(target_date: str = None):
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")
        
    storage = MarketIndicatorStorage()
    market_handler = MarketDataHandler()
    tech_engine = HybridStrategyEngine()
    sent_analyzer = SentimentAnalyzer()
    
    # 1. Fetch Universe
    universe_df = storage.get_universe() # columns: symbol, name, market
    if universe_df.empty:
        print("Universe is empty. Exiting.")
        return
        
    # 2. Get AI Expected Returns (horizon = 5d or 20d)
    # Fetch from market_indicators.db ai_predictions table
    with get_db_connection(storage.db_path) as conn:
        ai_df = pd.read_sql(
            "SELECT symbol, expected_return FROM ai_predictions WHERE date = ? AND horizon = 5",
            conn, params=(target_date,)
        )
    
    # Fallback if AI predictions for target_date are not run yet
    if ai_df.empty:
        print(f"Warning: No AI predictions for date {target_date}. Falling back to last available.")
        with get_db_connection(storage.db_path) as conn:
            ai_df = pd.read_sql(
                "SELECT symbol, expected_return FROM ai_predictions WHERE date = (SELECT MAX(date) FROM ai_predictions) AND horizon = 5",
                conn
            )
            
    # Calculate AI percentile scores
    if not ai_df.empty:
        ai_df["ai_score"] = ai_df["expected_return"].rank(pct=True)
    else:
        ai_df = pd.DataFrame(columns=["symbol", "expected_return", "ai_score"])
    
    # 3. Compute Technical and Sentiment scores in parallel
    results = []
    
    def process_stock(row):
        sym = row["symbol"]
        name = row["name"]
        
        # Technical Score
        tech = calculate_technical_score(sym, market_handler, tech_engine)
        
        # Sentiment Score
        sent = fetch_sentiment_score(sym, sent_analyzer)
        
        # AI Expected return match
        ai_row = ai_df[ai_df["symbol"] == sym]
        ai_score = float(ai_row["ai_score"].values[0]) if not ai_row.empty else 0.5
        
        return {
            "symbol": sym,
            "name": name,
            "technical_score": tech,
            "ai_score": ai_score,
            "sentiment_score": sent
        }

    # Parallel execution to process KRX + SP500 efficiently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_stock, row) for _, row in universe_df.iterrows()]
        for fut in futures:
            try:
                results.append(fut.result())
            except Exception as e:
                print(f"Error processing stock: {e}")

    df_rankings = pd.DataFrame(results)
    if df_rankings.empty:
        return

    # 4. Compute Composite Score
    # Composite = 0.40 * Technical + 0.40 * AI + 0.20 * Sentiment
    df_rankings["composite_score"] = (
        0.40 * df_rankings["technical_score"] +
        0.40 * df_rankings["ai_score"] +
        0.20 * df_rankings["sentiment_score"]
    )
    
    # 5. Compute Ranks (1 to N, sorted descending by composite_score)
    df_rankings["rank"] = df_rankings["composite_score"].rank(ascending=False, method="min").astype(int)
    df_rankings["date"] = target_date
    
    # 6. Save to SQLite DB
    with get_db_connection(storage.db_path) as conn:
        create_rankings_table(conn)
        
        # Bulk Insert
        insert_sql = """
            INSERT OR REPLACE INTO daily_stock_rankings
            (date, symbol, name, composite_score, technical_score, ai_score, sentiment_score, rank)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        records = df_rankings[[
            "date", "symbol", "name", "composite_score", "technical_score", "ai_score", "sentiment_score", "rank"
        ]].values.tolist()
        
        conn.executemany(insert_sql, records)
        conn.commit()
        
    print(f"Scored {len(df_rankings)} stocks successfully for {target_date}.")

if __name__ == "__main__":
    run_daily_scoring()
```

---

## 6. Recommendations & Design Decisions
1. **Database Selection**: centralize `daily_stock_rankings` in `market_indicators.db` since it already stores `stock_universe` and `ai_predictions`.
2. **Horizon Selection**: Use the **5-day expected return** horizon from the XGBoost model as it strikes a good balance between short-term momentum and medium-term trend forecasts.
3. **Sentiment Fallback**: Always ensure that stocks without news default to `0.5` (neutral sentiment) so their composite scores are not unfairly penalized.
4. **Percentile Normalization**: Rather than raw expected returns, utilize percentile normalization to bring expected returns into the `[0, 1]` range.
