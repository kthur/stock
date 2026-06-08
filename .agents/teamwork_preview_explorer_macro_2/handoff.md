# Handoff Report - Stock Screener & Macro Correlation Investigation

## 1. Observation
- **Screener Structure**: The `StockScreener` class is defined in `trading_system/src/analysis/screener.py` (lines 10-128) and implements technical indicators (Volume, RSI, and 52-week High Distance) filtering.
- **Ticker List Storage**: Dynamic and static search on the codebase (using `find_by_name` and `grep_search` tools) confirmed that the repository does not contain S&P 500 or KOSPI 200 ticker lists. `trading_system/src/utils/stock_list.py` uses `FinanceDataReader.StockListing('KRX')` to retrieve KOSPI and KOSDAQ tickers online.
- **Correlation Contract**: `.agents/orchestrator/SCOPE.md` defines the interface contracts for the outperformer screener under section `### R3. Outperformer Screener` (lines 29-37):
  ```python
  {
      "US": [{"ticker": str, "expected_excess_return": float, "correlation_to_exchange_rate": float}, ...],
      "KR": [{"ticker": str, "expected_excess_return": float, "correlation_to_exchange_rate": float}, ...]
  }
  ```
- **Correlation Mathematics**: Stock prices and the `USDKRW=X` exchange rate have different trading calendars and holiday schedules, requiring time-series alignment before correlation computation.

## 2. Logic Chain
- Since the repository lacks the S&P 500 and KOSPI 200 ticker lists, we must either fetch them online (e.g., scraping Wikipedia for S&P 500 and querying Naver/KRX for KOSPI 200) or store them as static JSON files in the local repository directory `trading_system/data/`. Local storage is recommended to prevent runtime network latency and API rate-limiting or scraping failures during screener execution.
- Since asset price series are non-stationary, directly calculating Pearson correlation on raw prices yields spurious correlation. Thus, stock prices and `USDKRW=X` prices must be outer-joined, forward-filled (`ffill().bfill()`) to align dates, and converted to daily percentage returns before computing correlation.
- The `screen_global_outperformers()` method must integrate these steps: fetch/load the ticker lists, batch download histories for all stocks and `USDKRW=X` to avoid yfinance rate limits, calculate daily return-based correlations, run `MacroPredictor.predict_outperformers()` to obtain `expected_excess_return`, sort each market descending by expected excess return, and return the top 10 tickers for both the US and KR markets in the required JSON/dictionary structure.

## 3. Caveats
- Wikipedia and Naver Finance page scrapers are prone to break if the page HTML structure changes. Cached JSON files are much more robust, but require a periodic/manual update mechanism to stay accurate when index constituents change.
- In `CODE_ONLY` network mode, the dynamic scraping logic cannot run; hence mock fallbacks must be specified and utilized in the tests or off-line runs.

## 4. Conclusion
- A comprehensive investigation has been completed, and recommendations have been written to `d:\Finance\code\stock\.agents\teamwork_preview_explorer_macro_2\analysis.md`. The proposed design is robust, complies with the contracts in `SCOPE.md`, and uses mathematically sound daily returns for correlation calculation.

## 5. Verification Method
- **File Inspection**: Check `d:\Finance\code\stock\.agents\teamwork_preview_explorer_macro_2\analysis.md` to confirm all 5 questions from the prompt are answered in detail.
- **Contract Verification**: Verify that the proposed return format matches the specification in `d:\Finance\code\stock\.agents\orchestrator\SCOPE.md`.
- **Integrity Check**: Confirm that no repository files were written or edited outside the `.agents/teamwork_preview_explorer_macro_2/` metadata directory.
