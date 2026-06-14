## 2026-06-12T02:31:17Z
You are the Worker for Milestone 2 (Daily Post-Market Stock Scoring Backend).
Your tasks are:
1. Update `trading_system/src/data_layer/indicator_storage.py` to:
   - In `_init_db()`, add SQL to create table `post_market_rankings` if it does not exist:
     ```sql
     CREATE TABLE IF NOT EXISTS post_market_rankings (
         date TEXT,
         symbol TEXT,
         name TEXT,
         rank INTEGER,
         composite_score REAL,
         technical_score REAL,
         ai_score REAL,
         sentiment_score REAL,
         PRIMARY KEY (date, symbol)
     )
     ```
   - Implement `save_post_market_rankings(self, date_str: str, rankings: List[Dict])` which inserts or replaces rankings in the `post_market_rankings` table.
   - Implement `get_post_market_rankings(self, date_str: Optional[str] = None) -> pd.DataFrame` which retrieves the rankings as a pandas DataFrame. If `date_str` is None, retrieve the latest available date's rankings.

2. Create a new daily post-market scoring script at `trading_system/scripts/post_market_scoring.py`:
   - Initialize `TradingConfig`, `MarketIndicatorStorage`, `HybridStrategyEngine`, and `OnDevicePredictionModel`.
   - Retrieve all stocks in the universe from database.
   - For each stock, calculate:
     - **Technical Score**: Retrieve historical prices (60 days). Call `HybridStrategyEngine._compute_technical_indicators(price_bars)` and use `"score"`. Ensure robust offline/simulated fallback if yfinance or FDR data fetch fails.
     - **AI Prediction Score**: Retrieve prediction from `ai_predictions` table (e.g. horizon 20 expected return), or use `OnDevicePredictionModel` to predict. Normalise the expected return to a [0.0, 1.0] score.
     - **Sentiment Score**: Retrieve sentiment score for the stock. Call `NLPEngine` or `SentimentAnalyzer` to calculate it.
     - **Composite Score**: `0.40 * Technical + 0.40 * AI + 0.20 * Sentiment`.
   - Sort the stocks in the universe by composite score descending. Assign rank 1 to N.
   - Save the rankings to `post_market_rankings` table in `market_indicators.db`.
   - Print the top 10 ranked stocks to stdout.

3. Create a unit test `trading_system/tests/test_post_market_scoring.py` to verify:
   - The script initializes and runs correctly.
   - Ranks and composite scores are computed using the correct weights and saved to the database.
   - Verify using mocked/simulated yfinance/FDR data to ensure no network calls are made.

4. Run `pytest tests/test_post_market_scoring.py` and other test files to confirm correctness.
5. Write your handoff.md in your working folder detailing your changes and verification results.

⚠️ MANDATORY INTEGRITY WARNING — include this verbatim in your implementation:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## 2026-06-13T04:52:36Z
You are teamwork_preview_worker, a software engineer subagent.
Working directory: d:\Finance\code\stock\.agents\teamwork_preview_worker_m2
Your mission is to implement risk management and portfolio construction upgrades (Milestone 2).

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please modify the following files:

1. `trading_system/src/risk/risk_manager.py`:
   - Implement `check_trailing_stop_signal(self, symbol: str, current_price: float, highest_price: float, atr: float, regime: str = "weak_bull", adx: float = 20.0) -> bool`:
     - If `current_price <= 0.0`, return `True` (emergency exit).
     - If `atr <= 0.0`, return `False`.
     - Retrieve regime multipliers using `self.get_adaptive_atr_multipliers(regime, adx)`. Use the `"stop"` multiplier.
     - Calculate base stop distance = `atr * stop_multiplier`.
     - Scale by the crisis stop multiplier: `crisis_mult = self.crisis_detector.get_crisis_stop_multiplier()`. If `crisis_mult < 1.0`, multiply stop distance by it.
     - Apply portfolio drawdown-based stop tightening: if portfolio drawdown `self.calculate_drawdown() > 0.0` and `self.max_drawdown_allowed > 0.0`, scale the stop distance by `1.0 - (self.calculate_drawdown() / self.max_drawdown_allowed)`, clamped between `0.25` and `1.0`.
     - Return `True` if `highest_price - current_price >= stop_distance`, else `False`.
   - Update `calculate_position_sizing(self, symbol: str, entry_price: float, stop_loss_price: float, win_rate: float = 0.0, win_loss_ratio: float = 0.0, vix: float = 20.0, atr: float = 0.0) -> int`:
     - Update signature to accept `atr: float = 0.0`.
     - In the Kelly Criterion sizing path (when `win_rate > 0` and `win_loss_ratio > 0`): if `atr > 0.0`, compute annualized asset volatility `asset_vol_annual = (atr / entry_price) * (252**0.5)` if `entry_price > 0` else `0.0`. If `asset_vol_annual > 0.0`, scale the `kelly_pct` by `vol_scaler = self.target_annual_volatility / asset_vol_annual`. Clamp `vol_scaler` to `[0.25, 1.5]`. Scale `kelly_pct` by `vol_scaler` before calculating `max_value`.
     - In the Fixed Risk sizing path (where Kelly is not active or is disabled): scale the risk unit percentage `self.max_loss_per_trade_pct` by the active crisis level multiplier: `NONE: 1.0`, `WATCH: 0.75`, `ACTIVE: 0.50`, `SEVERE: 0.25` (based on `self.crisis_detector.crisis_level`) before computing `max_loss`.

2. `trading_system/trading_system.py`:
   - Update `_compute_position_size` signature to accept `atr: float = 0.0` (default 0.0).
   - In `_compute_position_size`, pass `atr` to `self.risk_manager.calculate_position_sizing(..., atr=atr)`.
   - Update the call to `_compute_position_size` around line 524 to pass the calculated local variable `atr` as argument.
   - Refactor `_check_trailing_stop` (around line 1897) to delegate the evaluation to `self.risk_manager.check_trailing_stop_signal`. Make sure it initializes `highest_price` watermark as before, and returns `TradeSignal.SELL` if `check_trailing_stop_signal` returns `True`, else `None`. If `price <= 0.0`, return `TradeSignal.SELL`, if `atr <= 0.0` return `None`, if `symbol not in self.portfolio.positions` return `None`. Pass `self._current_regime` and `self._current_adx` from the class instance to the method.

After completing the code modifications:
- Run the unit tests via `pytest tests/test_risk_manager.py` and ensure they pass.
- Write a report of changes made to `d:\Finance\code\stock\.agents\teamwork_preview_worker_m2\changes.md` and send a handoff message to the parent orchestrator (conv ID: 7635347b-53a9-4ba1-9cb3-cafe65efe2dc).

