# Investigation Report: Macro Financial Analysis and ML Modeling (R1 & R2)

## 1. Requirements and Project Configurations
We investigated the configuration files `requirements.txt` and `pyproject.toml` in the `d:\Finance\code\stock\trading_system` directory.

### Key Observations
* **`requirements.txt`** contains 22 packages, covering core web framework components, numerical computation libraries, AI models, and deep learning frameworks:
  * Web & API: `fastapi`, `uvicorn`, `websockets`
  * Core ML & Data: `numpy`, `scipy`, `pandas`, `pyarrow`, `scikit-learn`
  * Optimization & Reinforcement Learning: `stable-baselines3`, `gymnasium`
  * Deep Learning & NLP: `torch`, `transformers`
  * Alternative Data & APIs: `yfinance`, `finance-datareader`, `openai`, `google-generativeai`, `python-telegram-bot`
  * System Utilities: `python-dotenv`, `tenacity`, `aiosqlite`, `pyzmq`, `reportlab`
* **`pyproject.toml`** defines the project metadata and contains a list of dependencies under the `[project]` section. Only 11 packages are listed as dependencies:
  * Listed: `fastapi`, `uvicorn`, `websockets`, `numpy`, `scipy`, `aiosqlite`, `python-dotenv`, `tenacity`, `yfinance`, `python-telegram-bot`, `pyzmq`.
  * **Missing in `pyproject.toml`**: `pandas`, `pyarrow`, `scikit-learn`, `stable-baselines3`, `gymnasium`, `reportlab`, `transformers`, `torch`, `finance-datareader`, `openai`, `google-generativeai`.

### Implications & Recommendations
* **Implications**: If the package is built or installed using `pyproject.toml` (e.g., via `pip install .` or `pip install -e .`), key scientific, machine learning, and data packages (such as `pandas` and `scikit-learn`) will **not** be installed. This will lead to runtime `ImportError` exceptions across most trading system modules (e.g., `ml_engine.py` which depends heavily on `scikit-learn` and `pandas`).
* **Recommendations**: Synchronize the `dependencies` list in `pyproject.toml` with `requirements.txt` to guarantee that any package-based installation automatically pulls in all required packages.

---

## 2. Environment Package Availability
We verified the environment package availability by querying the system's python environment and inspecting `out_pip_list.txt`.

### Package Status & Active Versions
The workspace's python environment has the key required packages installed with the following versions:
* **Python**: `3.11.9`
* **numpy**: `1.26.4`
* **pandas**: `3.0.3`
* **scikit-learn (sklearn)**: `1.9.0`
* **yfinance**: `1.4.1`

In addition, other analytical libraries are available:
* **scipy**: `1.17.1`
* **xgboost**: `3.2.0`
* **lightgbm**: `4.6.0`
* **optuna**: `4.9.0`
* **torch**: `2.12.0`
* **stable-baselines3**: `2.8.0`

### Conclusion on Environment
The environment is fully configured and contains all packages required for macro index correlation analysis (R1) and Random Forest prediction model training/evaluation (R2).

---

## 3. Yahoo Finance Ticker Investigation
We analyzed the ticker symbols for the macro indices and exchange rates, and evaluated potential rate limits or download issues.

### Ticker Symbols in Yahoo Finance (`yfinance`)
* **S&P 500**: `^GSPC` (Alternatively `SPY` for the ETF)
* **Nasdaq Composite**: `^IXIC` (Alternatively `QQQ` for the ETF)
* **KOSPI**: `^KS11`
* **KOSDAQ**: `^KQ11`
* **USD/KRW Exchange Rate**: `USDKRW=X`
* **10-Year US Treasury Yield**: `^TNX`
* **CBOE Volatility Index (VIX)**: `^VIX`

### Download Mechanisms
Individual tickers can be instantiated and downloaded via `yf.Ticker(symbol).history()`. For bulk downloads, it is highly recommended to use `yf.download` to batch requests:
```python
import yfinance as yf
tickers = ["^GSPC", "^IXIC", "^KS11", "^KQ11", "USDKRW=X", "^TNX", "^VIX"]
df = yf.download(tickers, start="2020-01-01", end="2026-06-01")
```
This downloads a multi-index DataFrame containing columns such as `('Close', '^GSPC')`, which is far more efficient than querying each ticker sequentially.

### Download Constraints, Rate Limits, & Mitigations
1. **Undocumented Rate Limits & HTTP 429**:
   * Yahoo Finance rate limits are undocumented but typically block client IPs after ~2000 requests per hour or excessive rapid sequential queries.
   * *Mitigations in code*: The existing implementation in `src/data_layer/market_data_handler.py` implements a token-bucket `RateLimiter` (max 5 requests per second), a `CircuitBreaker` (opens after 5 consecutive failures for 60 seconds), and a `tenacity.retry` decorator with exponential backoff.
2. **Local Caching Layer**:
   * To prevent hitting rate limits during repeated runs or backtests, `market_data_handler.py` implements a Parquet-based cache. Historical data is saved to `data/cache/{symbol}_{period}.parquet`. The cache is valid for 24 hours. This layer must be utilized for both R1 and R2.
3. **Timezone & Trading Day Misalignment**:
   * **Timezone Offset**: KOSPI/KOSDAQ trade in KST (UTC+9), closing at 15:30 KST (02:30 EST). US markets open at 09:30 EST (22:30 KST) and close at 16:00 EST (05:00 KST next day). 
   * **Lead-Lag Implication**: Because the US market on calendar date $T$ trades *after* the KR market has already closed on date $T$, US returns on day $T$ can only influence KR indices on day $T+1$.
   * **Holidays**: Simple inner merges will drop days when one market is closed (e.g., Thanksgiving in the US, Chuseok in Korea).
   * *Mitigations*: Forward-fill (`ffill()`) daily closing prices before calculating returns to preserve index levels on local market holidays, ensuring matching shapes.
4. **Data Normalization & Scaling**:
   * Prices (S&P 500, KOSPI, USD/KRW) are levels. We should compute daily percentage returns: $R_t = \frac{P_t - P_{t-1}}{P_{t-1}}$.
   * Treasury Yield (`^TNX`) and Volatility (`^VIX`) are rates. Computing percentage returns on interest rates/volatility can be volatile (e.g., VIX spikes from 15 to 30 is 100% return, while S&P 500 return is ~-2%). It is common to either calculate percentage returns of the rate, or use first differences in levels: $\Delta Y_t = Y_t - Y_{t-1}$.

---

## 4. Feature and Target Construction (R1 & R2)

### R1: Cross-Correlation with Lags
* **Objective**: Measure the lead-lag relationship between global indices and KR indices.
* **Mathematical Formula**:
  $$\rho_{XY}(k) = \text{Corr}(X_{t-k}, Y_t) = \frac{\text{Cov}(X_{t-k}, Y_t)}{\sigma_{X_{t-k}} \sigma_{Y_t}}$$
  where:
  * $Y_t$ is the target index return on business day $t$ (e.g., KOSPI `^KS11`).
  * $X_{t-k}$ is the predictor index return (e.g., S&P 500 `^GSPC`) shifted by $k$ business days.
  * $k \in [0, 1, 2, 3, 4, 5]$ is the lag. A positive lag ($k > 0$) implies past predictor values are correlated with the current target value.
* **Pandas Implementation**:
  Assuming `returns` is a pandas DataFrame of daily returns (with forward-filled price data and dropped NaNs):
  ```python
  import pandas as pd
  
  # Forward-fill prices first, then compute returns
  returns = prices.ffill().pct_change().dropna()
  
  # Calculate correlation for specific lags (e.g., target: KOSPI, predictor: S&P 500)
  lag_correlations = {}
  for k in range(0, 6):
      lag_correlations[k] = returns['^KS11'].corr(returns['^GSPC'].shift(k))
  
  # Or build a cross-correlation matrix between all indices at lag k
  corr_matrix_lag_k = returns.corrwith(returns.shift(k))
  ```

### R2: ML Feature Engineering & Target Design

#### 1. Target Construction ($y_t$)
The target variable is the **excess return** of an individual stock over its local benchmark index.
* **Formula**:
  $$y_{i,t} = R_{i,t} - R_{b,t}$$
  where:
  * $R_{i,t}$ is the individual stock $i$'s return on day $t$: $R_{i,t} = \frac{P_{i,t} - P_{i,t-1}}{P_{i,t-1}}$
  * $R_{b,t}$ is the local benchmark index return on day $t$:
    * For KR stocks: $R_{b,t}$ is the KOSPI (`^KS11`) or KOSDAQ (`^KQ11`) return.
    * For US stocks: $R_{b,t}$ is the S&P 500 (`^GSPC`) return.
  * *Note*: Excess return represents the stock-specific alpha, filtering out market-wide systematic risk.

#### 2. Input Feature Construction ($X_t$)
Features must only include information available *before* the start of the trading session on day $t$.
* **Lagged Index Returns**:
  * $R_{\text{GSPC}, t-k}$, $R_{\text{IXIC}, t-k}$, $R_{\text{KS11}, t-k}$, $R_{\text{KQ11}, t-k}$ for $k \in [1, 2, 3, 4, 5]$.
* **Lagged Exchange Rates & Macro Variables**:
  * USDKRW exchange rate percentage changes: $R_{\text{USDKRW}, t-k}$ for $k \in [1, 2, 3, 4, 5]$.
  * Treasury Yield differences or returns: $\Delta \text{TNX}_{t-k}$ for $k \in [1, 2, 3, 4, 5]$.
  * VIX differences or returns: $\Delta \text{VIX}_{t-k}$ for $k \in [1, 2, 3, 4, 5]$.
* **Stock-Specific Lagged Returns**:
  * $R_{i, t-k}$ for $k \in [1, 2, 3, 4, 5]$.
* **Technical Indicators**:
  * Distances from Simple/Exponential Moving Averages: e.g., $\frac{\text{Close} - \text{SMA}_{10}}{\text{SMA}_{10}}$.
  * Relative Strength Index (RSI), MACD, Bollinger Bands width/distance, normalized ATR.

#### 3. Timezone Asymmetry Handling
* **For KR Stocks (traded in KST)**:
  At the market open of day $T$ in Korea (09:00 KST), the US market has just closed its day $T-1$ trading session (16:00 EST on day $T-1$). Thus, US index returns $R_{\text{GSPC}, T-1}$ are fully known and must be included in the $t-1$ lag features.
* **For US Stocks (traded in EST)**:
  At the market open of day $T$ in the US (09:30 EST), the KR market has already completed and closed its day $T$ session (15:30 KST on day $T$). Therefore, Korean index returns $R_{\text{KS11}, T}$ are known and can be used as contemporaneous features (lag $0$) to predict US stock returns $R_{i, T}$ on that same day.

---

## 5. Random Forest Model Architecture, Training, and Evaluation

### Model Structure
* **Class**: `sklearn.ensemble.RandomForestRegressor` (for predicting continuous excess return) or `RandomForestClassifier` (for predicting binary outperform/underperform direction).
* **Hyperparameters**:
  * `n_estimators`: `100` to `300` trees.
  * `max_depth`: `5` to `10`. Financial returns have a low signal-to-noise ratio; deep trees will overfit to noise.
  * `min_samples_split`: `20` to `50` to force splits to contain a significant number of trading days.
  * `min_samples_leaf`: `10` to `25` to smooth leaf node predictions.
  * `max_features`: `'sqrt'` or `0.3` to ensure feature diversity across trees.
  * `random_state`: `42` (for reproducibility).

### Training & Cross-Validation Protocol
* **TimeSeriesSplit**: Do **not** use standard randomized K-Fold cross-validation, as it leaks future price information into past training splits. Instead, use `sklearn.model_selection.TimeSeriesSplit` (anchored or rolling walk-forward).
* **Purging and Embargoing**:
  * *Purging*: If target labels are overlapping (e.g., 5-day forward returns), delete training data points whose labels overlap with the validation set.
  * *Embargoing*: Since time-series data has autoregressive effects, delete a small window of training data immediately following the validation set.

### Evaluation Metrics
1. **Statistical Metrics**:
   * Regression: Mean Squared Error (MSE), Mean Absolute Error (MAE), and Out-of-Sample $R^2$ ($R^2_{\text{OOS}}$). *Note*: A positive $R^2_{\text{OOS}}$ in finance (even 0.5% - 2%) is considered highly predictive due to market noise.
   * Classification: Accuracy, Precision (highly critical for long-only models to minimize false positive buys), Recall, F1-Score, and AUC-ROC.
   * Rank Correlation / Information Coefficient (IC): Pearson/Spearman correlation between predicted excess returns and actual excess returns.
2. **Backtesting & Portfolio Metrics**:
   * Information Ratio (IR): Annualized active return divided by tracking error.
   * Sharpe Ratio: Performance metric adjusted for risk.
   * Maximum Drawdown (MDD): Peak-to-trough drop in simulated equity.
