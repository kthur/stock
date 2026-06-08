# Phase 5 / Benchmark Optimization — Exploration & Analysis Report

This report presents a read-only investigation, architectural analysis, and implementation blueprints for Phase 5 (Benchmark Optimization) of the 주식 트레이딩 시스템 (Stock Trading System).

---

## R1: Portfolio Risk Parity Weight Optimization

### 1. Existing Infrastructure Analysis
* **Files Investigated**: 
  - `src/strategy/asset_allocation.py`
  - `src/analysis/quantum_optimizer.py`
* **Observations**:
  - `AssetAllocator` currently implements a simple inverse-volatility weighting strategy under `self.strategy == "risk_parity"` (lines 119-134 of `src/strategy/asset_allocation.py`). This strategy divides 1.0 by the standard deviation of historical returns for each asset and normalizes the weights.
  - `QuantumPortfolioOptimizer` in `src/analysis/quantum_optimizer.py` also implements simple inverse-volatility in its `risk_parity_allocation` method (lines 65-90).
  - Simple inverse-volatility weightings are only mathematically equivalent to true **Equal Risk Contribution (ERC)** when all assets are completely uncorrelated. When asset correlations are present, covariance must be accounted for to ensure equal risk contribution across the portfolio.

### 2. Integration & Design Proposal
We will create a new dedicated optimizer file `src/analysis/portfolio_optimizer.py` containing the ERC solver. Then, we will integrate it into the existing `AssetAllocator` within `src/strategy/asset_allocation.py`.

#### Optimization Formulations (scipy.optimize)
To find the weights vector $w$ where risk contribution $\text{RC}_i = w_i \frac{(\Sigma w)_i}{\sqrt{w^T \Sigma w}}$ is equal for all assets, we can use two mathematical formulations:

##### Formulation A: Direct Risk Contribution Variance Minimization
We minimize the sum of squared differences of risk contributions between all asset pairs:
$$\min_w \sum_{i=1}^n \sum_{j=1}^n \left( w_i (\Sigma w)_i - w_j (\Sigma w)_j \right)^2 \quad \text{s.t.} \quad \sum w_i = 1, \quad 0 \le w_i \le 1$$
*Note: We multiply by $\Sigma w$ and omit the portfolio standard deviation in the denominator to avoid division by zero and create a smoother objective function.*

##### Formulation B: Log-Barrier Convex Optimization (Recommended)
An elegant, mathematically robust alternative is to solve the unconstrained convex log-barrier problem:
$$\min_x \frac{1}{2} x^T \Sigma x - \sum_{i=1}^n \ln(x_i) \quad \text{s.t.} \quad x_i > 0$$
Once the optimal vector $x^*$ is found, the weights are normalized:
$$w_i = \frac{x^*_i}{\sum_{j=1}^n x^*_j}$$
This formulation is numerically more stable, guarantees global convergence, and does not require complex constraints during optimization.

#### Implementation Blueprint (`src/analysis/portfolio_optimizer.py`)
```python
import numpy as np
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)

# Mandatory Integrity Warning
# DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, 
# create dummy/facade implementations, or circumvent the intended task. A Forensic 
# Auditor will independently verify your work. Integrity violations WILL be detected 
# and your work WILL be rejected.

def calculate_risk_parity_weights(cov_matrix: np.ndarray) -> np.ndarray:
    """
    Computes true Equal Risk Contribution (ERC) weights using a numerical solver.
    """
    n = cov_matrix.shape[0]
    if n == 0:
        return np.array([])
    if n == 1:
        return np.array([1.0])
        
    # Standardize/scale covariance to avoid numerical instability
    diag_vol = np.sqrt(np.diag(cov_matrix))
    # Avoid divide by zero
    diag_vol = np.where(diag_vol < 1e-8, 1e-8, diag_vol)
    
    # Formulation B: Log-barrier optimization
    def objective(x):
        x = np.asarray(x)
        # Avoid non-positive values inside log
        if np.any(x <= 1e-12):
            return 1e10
        return 0.5 * (x.T @ cov_matrix @ x) - np.sum(np.log(x))
        
    # Initial guess: equal weight scaled
    x0 = np.full(n, 1.0 / n)
    bounds = [(1e-8, None) for _ in range(n)]
    
    res = minimize(objective, x0, method='L-BFGS-B', bounds=bounds)
    
    if res.success:
        x_opt = res.x
        weights = x_opt / np.sum(x_opt)
    else:
        logger.warning(f"Log-barrier optimization failed: {res.message}. Falling back to Formulation A.")
        # Fallback to Formulation A: Direct RC Variance Minimization
        def obj_variance(w):
            rc = w * (cov_matrix @ w)
            rc_diff = rc[:, np.newaxis] - rc[np.newaxis, :]
            return np.sum(rc_diff ** 2)
            
        w0 = np.full(n, 1.0 / n)
        cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        bounds_a = [(0.0, 1.0) for _ in range(n)]
        
        res_a = minimize(obj_variance, w0, method='SLSQP', bounds=bounds_a, constraints=cons)
        if res_a.success:
            weights = res_a.x
        else:
            logger.error("All solvers failed. Falling back to simple inverse volatility.")
            inv_vol = 1.0 / diag_vol
            weights = inv_vol / np.sum(inv_vol)
            
    # Float precision correction (ensure exact sum to 1.0)
    weights = np.clip(weights, 0.0, 1.0)
    weights /= np.sum(weights)
    return weights
```

#### Integration Blueprint (`src/strategy/asset_allocation.py`)
Enhance `_risk_parity` method to align returns, construct the covariance matrix, and call the solver:
```python
    def _risk_parity(self, price_data: Dict[str, List[float]]) -> Dict[str, float]:
        import numpy as np
        from src.analysis.portfolio_optimizer import calculate_risk_parity_weights
        
        tickers = list(price_data.keys())
        n = len(tickers)
        if n == 0:
            return {}
        if n == 1:
            return {tickers[0]: 1.0}
            
        # 1. Compute return series for each ticker
        returns_dict = {}
        for ticker in tickers:
            returns_dict[ticker] = _compute_returns(price_data[ticker])
            
        # 2. Align series to minimum shared historical length
        min_len = min(len(r) for r in returns_dict.values())
        if min_len < 2:
            return self._equal_weight(tickers)
            
        returns_arr = np.array([returns_dict[t][:min_len] for t in tickers])
        
        # 3. Compute covariance matrix
        cov_matrix = np.cov(returns_arr)
        
        # 4. Solve for ERC weights
        weights = calculate_risk_parity_weights(cov_matrix)
        
        # 5. Format and normalize weights dict
        weights_dict = {tickers[i]: float(weights[i]) for i in range(n)}
        return _normalize(weights_dict)
```

---

## R2: VIX-Linked Dynamic Asset Allocation (Risk-Off Switch)

### 1. Existing Infrastructure Analysis
* **Files Investigated**: 
  - `src/risk/risk_manager.py`
  - `src/data_layer/alt_data.py`
  - `src/analysis/macro_analyzer.py`
* **Observations**:
  - `RiskManager` currently uses a `_volatility_scalar(vix)` helper to reduce position size multiplier values at VIX thresholds: $\text{VIX} \ge 25 \rightarrow 0.75\text{x}$, $\text{VIX} \ge 30 \rightarrow 0.50\text{x}$, $\text{VIX} \ge 40 \rightarrow 0.25\text{x}$.
  - The dynamic exposure restriction (e.g. clamping equity exposure to 30% and cash to 70% when $\text{VIX} \ge 25$) is **not** currently integrated into either the position sizing engine or the order manager.
  - VIX is fetched via yfinance (`^VIX`) in `AlternativeDataClient.fetch_vix()` (returns `20.0` as fallback).
  - In `src/analysis/macro_analyzer.py` (lines 195-198), US macro indicators (including VIX) are shifted forward by 1 day (`shifted(1)`) to align US/KR trading sessions and prevent look-ahead bias.

### 2. Integration & Design Proposal
We will implement the risk-off check in `src/risk/risk_manager.py` and enforce the clamp during the position sizing phase or order submission.

#### VIX Threshold Check
Add the `check_risk_off_signal` method to `RiskManager`:
```python
    def check_risk_off_signal(self, vix_value: float = None) -> bool:
        """
        Returns True if VIX index is equal to or exceeds 25, indicating Risk-Off mode.
        """
        if vix_value is None:
            try:
                import yfinance as yf
                vix_ticker = yf.Ticker("^VIX")
                hist = vix_ticker.history(period="1d")
                vix_value = float(hist['Close'].iloc[-1]) if not hist.empty else 20.0
            except Exception:
                vix_value = 20.0
        return vix_value >= 25.0
```

#### Exposure Clamping Mathematics
When the Risk-Off mode is active:
* **Equity Exposure Limit**: Total value of equity positions must not exceed $30\%$ of total portfolio value.
* **Safety Asset (Cash) Exposure Limit**: At least $70\%$ of total portfolio value must be held in cash.

To enforce this for a single stock trade:
1. Let $P$ be the current Total Portfolio Value.
2. Let $C$ be the current Cash balance.
3. Let $V_{E}$ be the current Total Equity Exposure ($P - C$).
4. Let $V_{E, \text{max}} = 0.3 \times P$ (Max allowed equity value).
5. The remaining equity room is:
   $$\Delta V_E = \max(0, V_{E, \text{max}} - V_E)$$
6. For a new trade with entry price $S$, the maximum quantity we can purchase under the risk-off constraint is:
   $$Q_{\text{max}} = \lfloor \frac{\Delta V_E}{S} \rfloor$$
7. The final calculated position size is clamped:
   $$Q_{\text{final}} = \min(Q_{\text{calculated}}, Q_{\text{max}})$$

This clamp can be injected directly inside `trading_system.py` in the order sizing logic or within `RiskManager.calculate_position_sizing`.

---

## R3: Machine Learning Model Upgrade

### 1. Existing Infrastructure Analysis
* **Files Investigated**: 
  - `src/analysis/macro_predictor.py`
  - `src/analysis/screener.py`
* **Observations**:
  - `MacroPredictor` currently trains a `RandomForestRegressor` from `scikit-learn`.
  - The model targets expected stock excess returns over a regional benchmark index (e.g. `^GSPC` for US, `^KS11` for KR).
  - Ticker-specific features include: 5 lags of macro variables (from `macro_analyzer`), and 5 lags of individual stock returns.
  - **Foreigner and institutional net purchase volumes** are not currently fetched, simulated, or used in the features.

### 2. Integration & Design Proposal

#### Machine Learning Upgrades (LightGBM/XGBoost)
We will replace `RandomForestRegressor` with `LGBMRegressor` from `lightgbm` (or `XGBRegressor` from `xgboost`).
* **Caveat**: LightGBM's default minimum samples in one leaf (`min_child_samples=20`) can cause empty trees and failures if the training set is very small (e.g. on small universes). We must configure `min_child_samples=2` or similar small value.
* We will use `verbose=-1` in LightGBM to keep logs clean.

Blueprint in `src/analysis/macro_predictor.py`:
```python
from lightgbm import LGBMRegressor
# or: from xgboost import XGBRegressor

class MacroPredictor:
    def __init__(self, max_depth: int = 5, n_estimators: int = 100):
        # Upgrade to LightGBM
        self.model = LGBMRegressor(
            max_depth=max_depth,
            n_estimators=n_estimators,
            random_state=42,
            min_child_samples=2,
            verbose=-1
        )
        self.is_trained = False
        self.feature_names = None
```

#### Supply & Demand Net Purchase Volume Simulator
Since yfinance does not provide foreign and institutional net purchase data directly, we will implement a simulation logic within the data layer/screener to produce realistic and correlated net purchase volumes.
* **Correlated simulation**: Foreign and institutional purchase activities are typically correlated with the stock return and total trading volume.
  $$\text{Foreign Net Purchase}_t = \text{Volume}_t \times (0.1 \times \text{Return}_t + \epsilon_{F,t})$$
  $$\text{Institution Net Purchase}_t = \text{Volume}_t \times (0.15 \times \text{Return}_t + \epsilon_{I,t})$$
  where $\epsilon \sim N(0, 0.05)$ represents market noise.

Add this simulator helper in `src/analysis/screener.py`:
```python
def simulate_net_purchase_volumes(ticker: str, dates: pd.DatetimeIndex, prices_series: pd.Series) -> pd.DataFrame:
    """
    Simulates realistic foreign and institutional net purchase volumes for a stock.
    """
    np.random.seed(hash(ticker) % 10000)
    returns = prices_series.pct_change().fillna(0.0)
    
    # Mock base volume
    base_volume = 1000000.0
    vols = np.random.lognormal(mean=np.log(base_volume), sigma=0.3, size=len(dates))
    
    # Generate net purchases correlated with return
    eps_f = np.random.normal(0.0, 0.05, size=len(dates))
    eps_i = np.random.normal(0.0, 0.04, size=len(dates))
    
    foreign_net = vols * (0.10 * returns.values + eps_f)
    inst_net = vols * (0.15 * returns.values + eps_i)
    
    return pd.DataFrame({
        "foreign_net_purchase": foreign_net,
        "institution_net_purchase": inst_net
    }, index=dates)
```

#### Incorporating Features into Training
In `src/analysis/screener.py` within `train_and_predict_region`, we construct the lag features for net purchases (e.g. 5 lags):
```python
            for ticker in tickers:
                if ticker not in stock_returns.columns:
                    continue
                excess = stock_returns[ticker] - bench_returns
                
                # Fetch/simulate net purchase volumes
                net_volumes = simulate_net_purchase_volumes(ticker, stock_returns.index, stock_returns[ticker])
                
                # Construct features
                ticker_features = macro_features_df.copy()
                for lag in range(1, 6):
                    ticker_features[f"stock_lag_{lag}"] = stock_returns[ticker].shift(lag)
                    ticker_features[f"foreign_net_purchase_lag_{lag}"] = net_volumes["foreign_net_purchase"].shift(lag)
                    ticker_features[f"institution_net_purchase_lag_{lag}"] = net_volumes["institution_net_purchase"].shift(lag)
                    
                ticker_features = ticker_features.dropna()
                idx = ticker_features.index.intersection(excess.index)
                if len(idx) < 5:
                    continue
                X_list.append(ticker_features.loc[idx])
                y_list.append(excess.loc[idx])
```

---

## R4: Dash Dashboard Components

### 1. Existing Infrastructure Analysis
* **Files Investigated**: 
  - `src/web/dashboard.py`
* **Observations**:
  - The dashboard uses `dash` with `dcc` and `dash_table`.
  - The `Global Macro` tab currently displays a dropdown for macro symbols, a correlation heatmap (`macro-correlation-heatmap`), and two data tables for expected outperformers in US/KR.
  - There is no pie chart or gauge chart to display portfolio weights or asset exposures.

### 2. Integration & Design Proposal
We will add two new visual elements to the 'Global Macro' tab and define the callbacks to update them.

#### Layout Modifications (`app.layout` update)
In the children list of `'global-macro-tab'`, we will insert a container holding the new graphs:
```python
                html.Div([
                    html.Div([
                        dcc.Graph(id='portfolio-weights-pie')
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        dcc.Graph(id='vix-exposure-gauge')
                    ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
                ], style={'margin-top': '20px'}),
```

#### Callback Implementations
We register two new callbacks in `src/web/dashboard.py`:

```python
# 1. Update Portfolio Weights Pie Chart
@app.callback(
    Output('portfolio-weights-pie', 'figure'),
    [Input('macro-timeframe-dropdown', 'value')]
)
def callback_update_portfolio_weights_pie(timeframe):
    from src.analysis.screener import StockScreener
    from src.analysis.portfolio_optimizer import calculate_risk_parity_weights
    from src.analysis.macro_analyzer import fetch_macro_indices_data
    import pandas as pd
    import numpy as np
    import yfinance as yf
    
    try:
        screener = StockScreener()
        outperformers = screener.screen_global_outperformers()
        
        tickers = [item['ticker'] for item in outperformers.get('US', [])[:5]] + \
                  [item['ticker'] for item in outperformers.get('KR', [])[:5]]
                  
        if not tickers:
            return {'data': [], 'layout': {'title': 'No Outperformers available'}}
            
        # Download price history
        df = yf.download(tickers, period=timeframe, progress=False, timeout=5)
        closes = {}
        for t in tickers:
            if t in df.columns.levels[0]:
                col = 'Close' if 'Close' in df[t].columns else ('Adj Close' if 'Adj Close' in df[t].columns else None)
                if col:
                    closes[t] = df[t][col]
                    
        # Fallback simulation if offline/failed
        if not closes:
            dates = pd.date_range(end=datetime.now(), periods=60, freq='B')
            for t in tickers:
                closes[t] = pd.Series(np.random.lognormal(mean=5.0, sigma=0.1, size=60), index=dates)
                
        price_df = pd.DataFrame(closes).ffill().bfill()
        returns_df = price_df.pct_change().dropna()
        
        cov_matrix = returns_df.cov().values
        weights = calculate_risk_parity_weights(cov_matrix)
        
        return {
            'data': [{
                'labels': list(price_df.columns),
                'values': weights.tolist(),
                'type': 'pie',
                'hole': 0.4,
                'textinfo': 'label+percent'
            }],
            'layout': {
                'title': 'Risk Parity Allocation (Top Outperformers)',
                'showlegend': True
            }
        }
    except Exception as e:
        logger.error(f"Error in portfolio weights pie callback: {e}")
        return {'data': [], 'layout': {'title': f"Error: {e}"}}

# 2. Update VIX-Linked Exposure Gauge (Horizontal Stacked Bar Chart)
@app.callback(
    Output('vix-exposure-gauge', 'figure'),
    [Input('macro-timeframe-dropdown', 'value')]
)
def callback_update_vix_exposure_gauge(timeframe):
    from src.data_layer.alt_data import AlternativeDataClient
    try:
        client = AlternativeDataClient()
        market_regime = client.get_market_regime()
        vix = market_regime.get("vix", 20.0)
        
        is_risk_off = vix >= 25.0
        equity_exposure = 30.0 if is_risk_off else 100.0
        cash_exposure = 70.0 if is_risk_off else 0.0
        
        return {
            'data': [
                {
                    'x': [equity_exposure],
                    'y': ['Exposure'],
                    'type': 'bar',
                    'orientation': 'h',
                    'name': 'Equity Limit',
                    'marker': {'color': '#E74C3C' if is_risk_off else '#3498DB'}
                },
                {
                    'x': [cash_exposure],
                    'y': ['Exposure'],
                    'type': 'bar',
                    'orientation': 'h',
                    'name': 'Cash Reservation',
                    'marker': {'color': '#2ECC71'}
                }
            ],
            'layout': {
                'title': f'Asset Exposure (VIX = {vix:.2f}, Risk-Off: {"ACTIVE" if is_risk_off else "INACTIVE"})',
                'barmode': 'stack',
                'xaxis': {'title': 'Exposure (%)', 'range': [0, 100]},
                'yaxis': {'showticklabels': False},
                'height': 250,
                'showlegend': True
            }
        }
    except Exception as e:
        logger.error(f"Error in VIX exposure callback: {e}")
        return {'data': [], 'layout': {'title': f"Error: {e}"}}
```

---

## Verification & Testing Methodologies

### 1. Verification Commands
To verify the modifications once implemented by the implementer, run the following:
* Run the project test suite:
  ```powershell
  python -m unittest tests/test_macro.py tests/test_macro_stress.py
  ```
* To test the Dash layout & dashboard server initialization:
  ```powershell
  python run_dashboard.py
  ```
  *(Verify that no import errors occur and the server successfully binds to the configured port).*

### 2. Specific Validation Criteria
* **R1 Verification**: 
  - Assert that `calculate_risk_parity_weights(cov)`.sum() equals 1.0 (with low tolerance e.g. `1e-7`).
  - Test with a mock covariance matrix where Asset A has high variance (0.1) and Asset B has low variance (0.01). Confirm that Asset B's calculated weight is larger than Asset A's weight.
* **R2 Verification**:
  - Call `check_risk_off_signal(vix_value=30.0)` and assert it returns `True`.
  - Check that under VIX >= 25, orders are successfully clamped to 30% of total portfolio value.
* **R3 Verification**:
  - Verify that `train_model()` executes without warnings and the saved file `data/macro_model_metrics.json` contains valid evaluation metrics (`mse`, `r2_score`).
  - Check that training feature list includes `foreign_net_purchase_lag_x` and `institution_net_purchase_lag_x`.
* **R4 Verification**:
  - Inspect the HTML layout of the dashboard and assert elements with IDs `portfolio-weights-pie` and `vix-exposure-gauge` (or `portfolio-exposure-gauge`) are present.
