## 2026-06-07T07:39:14Z

You are Milestone 3 Worker. Your working directory is d:\Finance\code\stock\trading_system\.agents\sub_orch_m3_worker.
Your task is to implement the requirements for Milestone 3:
1. Trailing Stop (R3) in `trading_system.py`, `src/core/asset_management.py`, and `src/core/strategy_engine.py`.
2. `StockScreener` class (R4) in `src/analysis/screener.py` (ensure you create any config files needed).

Specifically, you need to implement:
- **`Position` updates**: In `src/core/asset_management.py`, add a `highest_price: float = 0.0` attribute to the `Position` dataclass. Use `__post_init__` to initialize `highest_price = avg_price` if it is 0.0 or not set. In `PortfolioManager.add_position`, initialize `highest_price = price` for newly created positions.
- **`TradeSignal` updates**: In `src/core/strategy_engine.py`, override `__eq__` on the `TradeSignal` Enum to support comparison with string values (e.g. `self.name == other` if `other` is a string) to resolve the test assertion mismatch where some tests check for `TradeSignal.SELL` and others check for `"SELL"`.
- **Trailing Stop (`_check_trailing_stop`)**: In `trading_system.py`, add `_check_trailing_stop(self, symbol: str, price: float, atr: float = 2.0) -> Optional[TradeSignal]` to the `StockTradingSystem` class:
  - Immediately return `TradeSignal.SELL` if `price <= 0.0`.
  - Return `None` if `atr <= 0.0`.
  - Return `None` if `symbol` is not present in `self.portfolio.positions`.
  - Retrieve the position, initialize `highest_price = position.avg_price` if missing/invalid/lower than `position.avg_price`.
  - Update watermark `highest_price` if `price > position.highest_price`.
  - Calculate drawdown `position.highest_price - price`. If `drawdown >= 2 * atr`, return `TradeSignal.SELL`, else return `None`.
- **`StockScreener` (`src/analysis/screener.py`)**: Create the file `src/analysis/screener.py` defining the `StockScreener` class:
  - Constructor `__init__(self, min_volume: float = 100000.0, min_rsi: float = 30.0, max_rsi: float = 70.0, max_distance_from_high: float = 0.20, config_path: Optional[str] = None)`:
    - If `config_path` is specified and exists, load it as JSON. Raise `ValueError` if the JSON is malformed. Override defaults with values from config if present. If it does not exist, log a warning and fallback to safe defaults.
  - `_get_average_volume(self, symbol: str) -> float`: Fetches history using `yfinance` for 1 month and returns the average volume. If yfinance returns a MagicMock or is empty, use `ticker.info.get("volume")` or fallback to `2000000.0`.
  - `_calculate_rsi(self, symbol: str) -> float`: Calculates the 14-day RSI from yfinance 1-month close prices. If yfinance returns a MagicMock, empty, or insufficient data, return fallback `50.0`.
  - `_get_52week_prices(self, symbol: str) -> Dict[str, float]`: Fetches 1 year history using `yfinance`. Returns a dict with `current` and `52week_high`. If yfinance returns a MagicMock or is empty, use `ticker.info` or fallback to `{"current": 95.0, "52week_high": 100.0}`.
  - `screen(self, universe: List[str]) -> List[str]`: Filters symbols from `universe`. Deduplicates the input universe while preserving order. Apply volume, RSI, and 52-week distance filters. Handle errors gracefully (e.g. log errors and skip symbols that fail instead of crashing).

Read the explorer analyses and handoffs in:
- `d:\Finance\code\stock\trading_system\.agents\sub_orch_m3_explorer_1\handoff.md`
- `d:\Finance\code\stock\trading_system\.agents\sub_orch_m3_explorer_2\handoff.md`
- `d:\Finance\code\stock\trading_system\.agents\sub_orch_m3_explorer_3\analysis.md`
and the tests in `tests/phase4/e2e/test_e2e.py` to guide your implementation.

Run build and tests to verify your implementation:
`pytest tests/phase4/e2e/test_e2e.py -k "test_r1 or test_r2 or test_r3 or test_r4 or test_r1_r2_combination or test_r2_r3_combination or test_r3_r4_combination or test_r4_r1_combination"`
Confirm that all R1, R2, R3, R4 tests pass cleanly. (The only failing tests should be the ones requiring R5/dashboard).

When you are done, write a handoff report in `d:\Finance\code\stock\trading_system\.agents\sub_orch_m3_worker\handoff.md` summarizing your changes, the files you edited, and the test results.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
