# Analysis: Strategy Parameter Optimization (Requirement R1)

## Executive Summary
This report analyzes the requirements, current implementation, and necessary adjustments for **Requirement R1 (Strategy Parameter Optimization)** in `src/analysis/backtest.py`. 
To ensure a robust, crash-free parameter optimization process, we propose safe-guarding all mathematical and technical indicators against negative/zero windows, adding robust cache key matching (symbol + strategy + key set validation) to prevent cache cross-talk, resolving parameter name aliases, and avoiding division-by-zero errors in performance metrics.

---

## 1. Problem Boundary & Evidence Chain

### 1.1 Investigated Files and Locations
- **Interface Contract**: `PROJECT.md` contract:
  - `BacktestEngine.optimize_parameters(symbol: str, price_bars: List[PriceBar], param_ranges: Dict, strategy_name: str = "MA") -> Dict` runs parameter search, updates `data/optimized_params.json` and returns results.
- **E2E Test File**: `tests/phase4/e2e/test_e2e.py`
  - Defines 10 tests specific to R1/F1 (lines 72-154, 400-456, 674-693, 737-752, 797-821):
    - `test_r1_optimize_parameters_happy_path` (correct return structure)
    - `test_r1_json_saving_happy_path` (saves to cache file with exact keys)
    - `test_r1_best_params_structure` (saves strategy's optimized parameters)
    - `test_r1_caching_happy_path` (manual overwrite check of flat json format)
    - `test_r1_different_strategy_happy_path` (RSI strategy with aliases `rsi_period`, `rsi_oversold`)
    - `test_r1_empty_price_bars` (ValueError on empty input)
    - `test_r1_single_price_bar` (handles 1 bar gracefully)
    - `test_r1_invalid_param_ranges` (defaults to standard configurations on empty dict)
    - `test_r1_missing_json_directory` (creates target parent directory dynamically)
    - `test_r1_extreme_parameters` (handles negative or massive window inputs without crashes)

### 1.2 Identified Risks & Edge Cases
1. **Indicator Parameter Boundary Violations**: If `window` or `period` <= 0 is passed to indicators like SMA, EMA, RSI, MACD, or Bollinger Bands, index slicing (e.g. `closes[:-5]`) and index errors/zero division error occur.
2. **Global Cache Collision (Cache Cross-talk)**: The cache file `optimized_params.json` stores flat data representing the single latest run. When a test overwrites the cache or when multiple strategies are optimized back-to-back, a different symbol or strategy will read invalid cached parameters, causing validation assertions to fail.
3. **Parameter Name Mapping**: RSI strategy expects parameters `window`, `buy_threshold`, and `sell_threshold`, but tests pass `rsi_period` and `rsi_oversold`. These must be mapped appropriately.
4. **Bankruptcy/Zero Capital division**: In `_calculate_sharpe_ratio` and `_calculate_max_drawdown`, if portfolio equity drops to 0, division-by-zero errors occur.

---

## 2. Proposed Code Modification Plan

The proposed changes are safe, read-only proposals to be applied by the implementer in `src/analysis/backtest.py`.

### 2.1 Robust Indicator Calculations (Preventing Crashes)

We modify all technical indicator methods to enforce `window >= 1` or `period >= 1` internally.

```python
# Segment 1: _get_sma
def _get_sma(self, window: int) -> List[float]:
    if window <= 0:
        window = 1
    cache_key = ("SMA", window)
    # ...

# Segment 2: _calc_ema
@staticmethod
def _calc_ema(data: List[float], period: int) -> List[float]:
    if not data:
        return []
    if period <= 0:
        period = 1
    if len(data) < period:
        return [sum(data) / len(data)] * len(data)
    # ...

# Segment 3: _calc_rsi
@staticmethod
def _calc_rsi(closes: List[float], window: int = 14) -> List[float]:
    if window <= 0:
        window = 1
    if len(closes) <= window:
        return [50.0] * len(closes)
    # ...

# Segment 4: _get_macd_hist
def _get_macd_hist(self, fast: int, slow: int, signal: int) -> List[float]:
    if fast <= 0:
        fast = 1
    if slow <= 0:
        slow = 1
    if signal <= 0:
        signal = 1
    cache_key = ("MACD_HIST", fast, slow, signal)
    # ...

# Segment 5: _get_bollinger_bands
def _get_bollinger_bands(self, period: int, std_mult: float) -> Tuple[List[float], List[float]]:
    if period <= 0:
        period = 1
    cache_key = ("BOLLINGER_BANDS", period, std_mult)
    # ...

# Segment 6: _get_rolling_max, _get_rolling_mean_volume, _get_rolling_volatility
def _get_rolling_max(self, window: int) -> List[float]:
    if window <= 0:
        window = 1
    cache_key = ("ROLLING_MAX", window)
    # ...

def _get_rolling_mean_volume(self, window: int) -> List[float]:
    if window <= 0:
        window = 1
    cache_key = ("ROLLING_MEAN_VOL", window)
    # ...

def _get_rolling_volatility(self, window: int) -> List[float]:
    if window <= 0:
        window = 1
    cache_key = ("ROLLING_VOLATILITY", window)
    # ...
```

---

### 2.2 Performance Metrics Safe-guards

```python
# Segment 7: _calculate_sharpe_ratio (Bankruptcy protection)
def _calculate_sharpe_ratio(self, equity_curve: List[float], risk_free_rate: float = 0.02) -> float:
    if len(equity_curve) < 2:
        return 0
    
    returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i-1]
        if prev != 0:
            returns.append((equity_curve[i] - prev) / prev)
        else:
            returns.append(0.0)
            
    if not returns:
        return 0
    # ...

# Segment 8: _calculate_max_drawdown (Bankruptcy protection)
def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
    if not equity_curve:
        return 0
    
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        
        dd = (peak - value) / peak if peak != 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            
    return max_dd
```

---

### 2.3 Parameter Mapping in `_rsi_strategy`

```python
# Segment 9: _rsi_strategy parameter mapping
def _rsi_strategy(self, bars: List[PriceBar], params: Optional[Dict] = None) -> str:
    if params is None:
        params = {}
    # Handles both generic and RSI-specific naming conventions from tests
    window = params.get('window', params.get('rsi_period', params.get('period', 14)))
    buy_threshold = params.get('buy_threshold', params.get('rsi_oversold', 30))
    sell_threshold = params.get('sell_threshold', params.get('rsi_overbought', 70))
    # ...
```

---

### 2.4 Caching validation and safe-guards in `optimize_parameters`

```python
# Segment 10: optimize_parameters method re-implementation
def optimize_parameters(self, symbol: str, price_bars: List[PriceBar],
                       param_ranges: Dict, strategy_name: str = "MA") -> Dict:
    """파라미터 최적화 (캐싱 포함)"""
    if not price_bars:
        raise ValueError("price_bars cannot be empty")
        
    if not param_ranges:
        param_ranges = {"short_window": [10, 20], "long_window": [30, 40]}
        
    best_result = None
    best_params = None
    best_return = -float('inf')
    
    self.logger.info(f"Starting parameter optimization for {strategy_name}...")
    
    import json
    import os
    
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, 'optimized_params.json')
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            if "best_params" in cache_data:
                cached_params = cache_data["best_params"]
                keys_match = True
                if param_ranges:
                    for k in param_ranges.keys():
                        if k not in cached_params:
                            keys_match = False
                            break
                
                symbol_match = True
                if "symbol" in cache_data and cache_data["symbol"] != symbol:
                    symbol_match = False
                    
                strat_match = True
                if "strategy_name" in cache_data and cache_data["strategy_name"] != strategy_name:
                    strat_match = False
                    
                if keys_match and symbol_match and strat_match:
                    return {
                        'best_params': cached_params,
                        'best_result': None,
                        'best_return': cache_data.get('best_return', 0.0)
                    }
        except Exception:
            pass

    strategy_methods = {
        "MA": self._simple_ma_strategy,
        "이동평균선": self._simple_ma_strategy,
        "RSI": self._rsi_strategy,
        "MACD": self._macd_strategy,
        "TREND": self._trend_following_strategy,
        "추세": self._trend_following_strategy,
        "BOLLINGER": self._bollinger_band_strategy,
    }
    name_upper = strategy_name.upper()
    strategy_func_unbound = strategy_methods.get(name_upper, self._simple_ma_strategy)
    
    # 간단한 그리드 서치
    for param_combo in self._generate_param_combos(param_ranges):
        def strategy(bars):
            return strategy_func_unbound(bars, param_combo)
        
        result = self.run_backtest(symbol, price_bars, strategy)
        
        if result.total_return_pct > best_return:
            best_return = result.total_return_pct
            best_result = result
            best_params = param_combo
            
    # Default strategy configurations if no combos executed or best_params is None
    strategy_defaults = {
        "MA": {"short_window": 20, "long_window": 50},
        "이동평균선": {"short_window": 20, "long_window": 50},
        "RSI": {"window": 14, "buy_threshold": 30, "sell_threshold": 70},
        "MACD": {"fast": 12, "slow": 26, "signal": 9},
        "BOLLINGER": {"bb_period": 20, "bb_std_mult": 2.0, "rsi_window": 14},
        "TREND": {},
        "추세": {}
    }
    if best_params is None:
        best_params = strategy_defaults.get(name_upper, {})
        best_return = 0.0
    
    self.logger.info(f"Optimization complete: best params={best_params}, "
                    f"best return={best_return:.2f}%")
    
    # Save to cache including key metadata
    cache_data = {
        'symbol': symbol,
        'strategy_name': strategy_name,
        'best_params': best_params,
        'best_return': best_return,
        'sharpe_ratio': best_result.sharpe_ratio if best_result else 0.0
    }
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=4)
    
    return {
        'best_params': best_params,
        'best_result': best_result,
        'best_return': best_return
    }
```

---

## 3. Verification Method

Once implemented, the code can be verified by running the R1 E2E tests:

```powershell
pytest tests/phase4/e2e/test_e2e.py -k "test_r1"
```

All 10 test cases under `test_r1_*` should pass cleanly.
