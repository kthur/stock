# Technical Architecture & Handoff Report: Milestone 3 (R3: CPCV & Historical Stress Testing Engine)

**Agent ID**: `explorer_m3_1`  
**Role**: Technical Architecture Explorer for Milestone 3  
**Date**: 2026-07-31  

---

## 1. Observation

### 1.1 Directory & Import Architecture
- **Root vs `trading_system` structure**:
  - Root directory `d:\Finance\code\stock\src\` currently contains `execution/`, `risk/`, and `strategy/`.
  - `d:\Finance\code\stock\trading_system\src\` contains `ai/`, `risk/`, `core/`, `strategy/`, `data_layer/`, `persistence/`, `broker/`, `analysis/`, `telegram_bot/`, `utils/`, `web/`.
  - Root `conftest.py` (lines 5-11) and `trading_system/conftest.py` (lines 4-10) configure `sys.path` by prepending `trading_system/` and `root_dir`. Thus `from src.ai...` resolves to `trading_system/src/ai/`.
  - To support both path entry conventions seamlessly, the implementation must reside in `trading_system/src/ai/cpcv_stress_tester.py` with an import forwarder or mirrored module in `src/ai/cpcv_stress_tester.py`.

### 1.2 Existing Validation & Risk Codebase
- **`trading_system/src/ai/purged_cv.py`** (lines 8–63):
  - Defines `PurgedKFold(n_splits=5, pct_embargo=0.01)`.
  - Implements sequential $K$-fold purged cross-validation.
  - **Gap identified**: Lacks combinatorial fold generation $C(N, k)$ (CPCV), multi-path OOS backtest evaluation, and Probability of Backtest Overfitting (PBO) computation based on Marcos Lopez de Prado's methodology.
- **`trading_system/src/risk/risk_manager.py`** (lines 972–998):
  - Implements basic single-period `calculate_var(returns, confidence=0.95)` and `calculate_cvar(returns, confidence=0.95)`.
  - **Gap identified**: Lacks multi-scenario historical stress testing (`'2008_CRISIS'`, `'2020_COVID'`, `'2022_FED_HIKE'`), stress recovery time calculation, 99% VaR/CVaR, and structured `StressTestReport` dataclasses.

---

## 2. Logic Chain

### 2.1 Theoretical Framework for CPCV & PBO
Standard $K$-Fold cross-validation yields a single path of out-of-sample (OOS) statistics. In quantitative finance, strategies tuned across hyperparameters are vulnerable to backtest overfitting. Combinatorial Purged Cross-Validation (CPCV) solves this by:
1. Partitioning $N$ contiguous time blocks (default $N=6$).
2. Taking all combinations of $k$ test splits (default $k=2$), generating $S = \binom{N}{k} = \binom{6}{2} = 15$ distinct train/test combinations.
3. For each combination $s \in \{1, \dots, S\}$:
   - **Purging**: Training samples within `purge_window` (e.g. 5 bars) prior to any test group start are purged to prevent overlap from multi-period forward labels.
   - **Embargoing**: Training samples within `embargo_window` (e.g. 10 bars) following any test group end are purged to eliminate autoregressive / serial correlation leakage.
4. **PBO Calculation**:
   - For a matrix of candidate strategy returns (columns = $M$ model variants, rows = time bars):
   - For each split $s$: calculate In-Sample (IS) Sharpe ratio $S^{\text{IS}}_{s, m}$ and OOS Sharpe ratio $S^{\text{OOS}}_{s, m}$ for each strategy $m \in \{1, \dots, M\}$.
   - Identify IS-best strategy $m^*(s) = \arg\max_{m} S^{\text{IS}}_{s, m}$.
   - Find relative rank percentile $q_s \in (0, 1)$ of $S^{\text{OOS}}_{s, m^*(s)}$ among all OOS strategy performances.
   - Compute logit: $\lambda_s = \ln\left(\frac{q_s}{1 - q_s}\right)$.
   - $\text{PBO} = \frac{1}{S} \sum_{s=1}^S \mathbf{1}(q_s \le 0.5)$. If $\text{PBO} > 0.50$, the strategy set suffers from backtest overfitting.

### 2.2 Historical Stress Testing Engine Architecture
To validate robustness under market regimes not present in recent training data, the engine applies historical crisis shock vectors to strategy return series:
1. **`2008_CRISIS`**: Severe drawdown & high volatility regimes ($\mu \to \mu - 0.0025$/day, $\sigma \times 3.0$, crash window severity multiplier).
2. **`2020_COVID`**: Hyper-compressed liquidity shock ($\mu \to \mu - 0.0080$/day for 25 days, $\sigma \times 3.5$, followed by sharp V-rebound).
3. **`2022_FED_HIKE`**: Prolonged stagflation / rate hike grinding bear market ($\mu \to \mu - 0.0012$/day for 180 days, $\sigma \times 1.8$).

For each scenario, the engine computes:
- Max Drawdown (MDD)
- 95% and 99% Value at Risk ($\text{VaR}_{95}, \text{VaR}_{99}$)
- 95% and 99% Conditional VaR / Expected Shortfall ($\text{CVaR}_{95}, \text{CVaR}_{99}$)
- Stress Recovery Time (trading days to reach previous peak)
- Stress Sharpe Ratio
- `pass_flag` (True if $\text{MDD} \le \text{threshold}$ and $\text{Stress Sharpe} \ge 0.0$)

---

## 3. Caveats

1. **Synthetic vs Empirical Historical Shock Vectors**:
   - Ticker return histories may not span back to 2008. The engine utilizes shock vector scaling (modifying drift $\mu$ and volatility $\sigma$) applied to strategy returns to simulate empirical crisis dynamics deterministically.
2. **CPCV Sample Size Requirements**:
   - $N=6$ splits require sufficient time series length (minimum 120-200 bars). For shorter series, `n_splits` should automatically scale down or throw a descriptive error.
3. **Logit Boundary Protection**:
   - When relative rank percentile $q_s = 0$ or $1$, logit $\ln(q_s / (1-q_s))$ evaluates to $\pm \infty$. The calculation clips $q_s$ to $[\epsilon, 1-\epsilon]$ (where $\epsilon = 10^{-5}$) to maintain numerical stability.

---

## 4. Technical Specifications & Conclusion

### 4.1 Class Specification: `CPCVStressTester`
Location: `trading_system/src/ai/cpcv_stress_tester.py` (mirrored in `src/ai/cpcv_stress_tester.py`)

```python
import numpy as np
import pandas as pd
import scipy.stats as stats
from dataclasses import dataclass, asdict
from itertools import combinations
from typing import Dict, List, Tuple, Optional, Union, Any
import logging

logger = logging.getLogger(__name__)

@dataclass
class StressTestReport:
    scenario: str
    mdd: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float
    stress_sharpe: float
    stress_recovery_time: int
    pass_flag: bool
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CPCVStressTester:
    """
    Combinatorial Purged Cross-Validation (CPCV) & Historical Stress Testing Engine.
    Implements Marcos Lopez de Prado's CPCV/PBO methodology and macro crisis scenario stress testing.
    """

    def __init__(
        self,
        n_splits: int = 6,
        n_test_splits: int = 2,
        purge_window: int = 5,
        embargo_window: int = 10,
        mdd_threshold: float = 0.30,
    ):
        self.n_splits = n_splits
        self.n_test_splits = n_test_splits
        self.purge_window = purge_window
        self.embargo_window = embargo_window
        self.mdd_threshold = mdd_threshold

    def generate_purged_folds(
        self,
        X: Union[pd.DataFrame, pd.Series, np.ndarray],
        y: Optional[Union[pd.Series, np.ndarray]] = None,
    ) -> List[Tuple[np.ndarray, np.ndarray, Tuple[int, ...]]]:
        """
        Generates combinatorial purged & embargoed train/test fold indices C(N, k).
        """
        n_samples = len(X)
        indices = np.arange(n_samples)
        block_bounds = np.linspace(0, n_samples, self.n_splits + 1, dtype=int)
        blocks = [indices[block_bounds[i]:block_bounds[i+1]] for i in range(self.n_splits)]

        folds = []
        for test_blocks_idx in combinations(range(self.n_splits), self.n_test_splits):
            test_idx_list = [blocks[b] for b in test_blocks_idx]
            test_indices = np.concatenate(test_idx_list)

            # Purge and embargo ranges for each test block
            purge_embargo_mask = np.zeros(n_samples, dtype=bool)
            for b in test_blocks_idx:
                start_b = block_bounds[b]
                end_b = block_bounds[b+1]

                # Purge window BEFORE test block
                purge_start = max(0, start_b - self.purge_window)
                purge_embargo_mask[purge_start:start_b] = True

                # Embargo window AFTER test block
                embargo_end = min(n_samples, end_b + self.embargo_window)
                purge_embargo_mask[end_b:embargo_end] = True

            # Mark test blocks as excluded from training
            for b in test_blocks_idx:
                purge_embargo_mask[block_bounds[b]:block_bounds[b+1]] = True

            train_indices = indices[~purge_embargo_mask]
            folds.append((train_indices, test_indices, test_blocks_idx))

        return folds

    def compute_pbo(
        self,
        strategy_matrix: Union[pd.DataFrame, np.ndarray],
        annualization_factor: float = 252.0,
    ) -> Dict[str, Any]:
        """
        Computes Probability of Backtest Overfitting (PBO) across combinatorial folds.
        strategy_matrix: (N_bars, M_models) dataframe/array of returns.
        """
        if isinstance(strategy_matrix, pd.DataFrame):
            data = strategy_matrix.values
            col_names = list(strategy_matrix.columns)
        else:
            data = strategy_matrix
            col_names = [f"model_{i}" for i in range(data.shape[1])]

        n_samples, n_models = data.shape
        folds = self.generate_purged_folds(data)

        logits = []
        ranks = []
        best_models = []

        for train_idx, test_idx, _ in folds:
            train_data = data[train_idx]
            test_data = data[test_idx]

            # In-Sample Sharpe
            is_mean = np.mean(train_data, axis=0)
            is_std = np.std(train_data, axis=0, ddof=1) + 1e-8
            is_sharpe = (is_mean / is_std) * np.sqrt(annualization_factor)

            # Out-Of-Sample Sharpe
            oos_mean = np.mean(test_data, axis=0)
            oos_std = np.std(test_data, axis=0, ddof=1) + 1e-8
            oos_sharpe = (oos_mean / oos_std) * np.sqrt(annualization_factor)

            # Best IS model
            best_model_idx = np.argmax(is_sharpe)
            best_models.append(col_names[best_model_idx])

            # Rank of best IS model in OOS
            oos_best_perf = oos_sharpe[best_model_idx]
            rank_in_oos = np.sum(oos_sharpe <= oos_best_perf) / n_models
            rank_clipped = np.clip(rank_in_oos, 1e-5, 1.0 - 1e-5)
            logit = np.log(rank_clipped / (1.0 - rank_clipped))

            ranks.append(rank_in_oos)
            logits.append(logit)

        pbo = float(np.mean(np.array(ranks) <= 0.5))
        is_overfitted = pbo > 0.50

        return {
            "pbo": pbo,
            "logits": logits,
            "ranks": ranks,
            "is_overfitted": is_overfitted,
            "n_combinations": len(folds),
            "best_model_distribution": pd.Series(best_models).value_counts().to_dict(),
        }

    def run_historical_stress_test(
        self,
        strategy_returns: Union[pd.Series, pd.DataFrame, np.ndarray],
        scenario: str = "2008_CRISIS",
        mdd_threshold: Optional[float] = None,
    ) -> Union[StressTestReport, Dict[str, StressTestReport]]:
        """
        Runs historical crisis scenario stress test on strategy returns.
        Scenarios: '2008_CRISIS', '2020_COVID', '2022_FED_HIKE'
        """
        threshold = mdd_threshold if mdd_threshold is not None else self.mdd_threshold

        if isinstance(strategy_returns, pd.DataFrame):
            return {
                col: self._stress_test_single_series(strategy_returns[col], scenario, threshold)
                for col in strategy_returns.columns
            }
        elif isinstance(strategy_returns, (pd.Series, np.ndarray)):
            return self._stress_test_single_series(strategy_returns, scenario, threshold)
        else:
            raise TypeError("strategy_returns must be Series, DataFrame, or ndarray")

    def _stress_test_single_series(
        self,
        returns: Union[pd.Series, np.ndarray],
        scenario: str,
        mdd_threshold: float,
    ) -> StressTestReport:
        ret_arr = np.asarray(returns, dtype=float)
        ret_arr = ret_arr[~np.isnan(ret_arr)]
        if len(ret_arr) == 0:
            ret_arr = np.zeros(100)

        # Generate stressed returns based on scenario shock vectors
        stressed_ret = self._apply_scenario_shock(ret_arr, scenario)

        # Calculate metrics
        cum_ret = np.cumprod(1.0 + stressed_ret)
        peak = np.maximum.accumulate(cum_ret)
        drawdowns = (peak - cum_ret) / peak
        mdd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Stress Recovery Time
        max_dd_idx = np.argmax(drawdowns)
        recovery_time = -1
        if max_dd_idx < len(cum_ret) - 1:
            peak_val_at_max_dd = peak[max_dd_idx]
            recovery_indices = np.where(cum_ret[max_dd_idx:] >= peak_val_at_max_dd)[0]
            if len(recovery_indices) > 0:
                recovery_time = int(recovery_indices[0])
            else:
                recovery_time = len(cum_ret) - max_dd_idx

        # VaR & CVaR
        var_95 = float(np.percentile(stressed_ret, 5))
        var_99 = float(np.percentile(stressed_ret, 1))

        tail_95 = stressed_ret[stressed_ret <= var_95]
        cvar_95 = float(np.mean(tail_95)) if len(tail_95) > 0 else var_95

        tail_99 = stressed_ret[stressed_ret <= var_99]
        cvar_99 = float(np.mean(tail_99)) if len(tail_99) > 0 else var_99

        # Stress Sharpe Ratio
        ann_mean = np.mean(stressed_ret) * 252.0
        ann_std = np.std(stressed_ret, ddof=1) * np.sqrt(252.0) + 1e-8
        stress_sharpe = float(ann_mean / ann_std)

        pass_flag = bool(mdd <= mdd_threshold and stress_sharpe >= 0.0)

        return StressTestReport(
            scenario=scenario,
            mdd=mdd,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            stress_sharpe=stress_sharpe,
            stress_recovery_time=recovery_time,
            pass_flag=pass_flag,
            details={
                "n_bars": len(stressed_ret),
                "mdd_threshold": mdd_threshold,
                "annualized_return": float(ann_mean),
                "annualized_volatility": float(ann_std),
            },
        )

    def _apply_scenario_shock(self, ret_arr: np.ndarray, scenario: str) -> np.ndarray:
        n = len(ret_arr)
        shocked = ret_arr.copy()

        if scenario == "2008_CRISIS":
            # Drift penalty -0.25%/day, 3.0x volatility jump, severe shock block in middle
            drift_shift = -0.0025
            vol_mult = 3.0
            shocked = (shocked + drift_shift) * vol_mult
            # Inject acute panic crash block
            mid_start = n // 4
            mid_end = min(n, mid_start + max(10, n // 3))
            shocked[mid_start:mid_end] -= 0.015
        elif scenario == "2020_COVID":
            # Hyper-compressed 25-day crash (-0.8%/day, 3.5x vol), followed by V-rebound
            crash_len = min(25, n // 2)
            shocked[:crash_len] = (shocked[:crash_len] - 0.008) * 3.5
            rebound_len = min(40, n - crash_len)
            if rebound_len > 0:
                shocked[crash_len:crash_len+rebound_len] = (shocked[crash_len:crash_len+rebound_len] + 0.004) * 2.0
        elif scenario == "2022_FED_HIKE":
            # Grinding 180-day bear market (-0.12%/day drift, 1.8x vol)
            shocked = (shocked - 0.0012) * 1.8
        else:
            logger.warning(f"Unknown scenario '{scenario}'. Applying default 1.5x volatility shock.")
            shocked = shocked * 1.5

        return shocked


def run_historical_stress_test(
    strategy_returns: Union[pd.Series, pd.DataFrame, np.ndarray],
    scenario: str = "2008_CRISIS",
    mdd_threshold: float = 0.30,
) -> Union[StressTestReport, Dict[str, StressTestReport]]:
    tester = CPCVStressTester(mdd_threshold=mdd_threshold)
    return tester.run_historical_stress_test(strategy_returns, scenario=scenario)
```

---

### 4.2 Integration Specifications (`run_pipeline.py` & `RiskManager`)

1. **`run_pipeline.py` Pipeline Integration**:
   - In Step 11 (`Save predictions to DB & 18-Strategy Ensemble Output`), `CPCVStressTester` is invoked on the 18 strategy prediction score vectors.
   - PBO is evaluated across the 18 strategies to ensure non-overfitted factor weighting ($\text{PBO} < 0.50$).
   - Historical stress test reports for `'2008_CRISIS'`, `'2020_COVID'`, `'2022_FED_HIKE'` are computed for the top ensemble portfolio return stream.
   - Stressed MDD and pass flags are saved into `strategy_data_coverage_report.txt` under a dedicated `[MILESTONE 3: CPCV & HISTORICAL STRESS TEST REPORT]` section.

2. **`RiskManager` Dynamic Exposure Gating**:
   - When `pass_flag == False` in `'2008_CRISIS'` or `'2020_COVID'` scenarios, `RiskManager` applies a stress adjustment factor $\kappa_{\text{stress}} = 0.75$ to max position sizes and cash reserves to prevent catastrophic drawdowns.

---

### 4.3 Test Suite Specifications (`tests/test_cpcv_stress_tester.py`)

Test file location: `tests/test_cpcv_stress_tester.py` and `trading_system/tests/test_cpcv_stress_tester.py`.

```python
import pytest
import numpy as np
import pandas as pd
from src.ai.cpcv_stress_tester import CPCVStressTester, StressTestReport, run_historical_stress_test

def test_generate_purged_folds_combinatorics():
    tester = CPCVStressTester(n_splits=6, n_test_splits=2, purge_window=5, embargo_window=10)
    data = pd.DataFrame(np.random.randn(300, 4))
    folds = tester.generate_purged_folds(data)
    # C(6, 2) = 15 splits
    assert len(folds) == 15
    for train_idx, test_idx, test_blocks in folds:
        assert len(train_idx) > 0
        assert len(test_idx) > 0
        assert len(np.intersect1d(train_idx, test_idx)) == 0

def test_pbo_calculation():
    tester = CPCVStressTester(n_splits=6, n_test_splits=2)
    # Synthetic random returns matrix (10 models, 300 bars)
    np.random.seed(42)
    matrix = np.random.randn(300, 10) * 0.01
    res = tester.compute_pbo(matrix)
    assert "pbo" in res
    assert "logits" in res
    assert 0.0 <= res["pbo"] <= 1.0
    assert len(res["logits"]) == 15

def test_historical_stress_test_scenarios():
    returns = pd.Series(np.random.randn(250) * 0.01 + 0.0005)
    for scenario in ["2008_CRISIS", "2020_COVID", "2022_FED_HIKE"]:
        report = run_historical_stress_test(returns, scenario=scenario, mdd_threshold=0.35)
        assert isinstance(report, StressTestReport)
        assert report.scenario == scenario
        assert 0.0 <= report.mdd <= 1.0
        assert report.var_95 <= 0.0
        assert report.cvar_95 <= report.var_95
        assert isinstance(report.pass_flag, bool)

def test_stress_test_dataframe():
    df = pd.DataFrame({
        "strat1": np.random.randn(200) * 0.01,
        "strat2": np.random.randn(200) * 0.01 + 0.001
    })
    reports = run_historical_stress_test(df, scenario="2008_CRISIS")
    assert isinstance(reports, dict)
    assert "strat1" in reports
    assert "strat2" in reports
    assert isinstance(reports["strat1"], StressTestReport)
```

---

## 5. Verification Method

To independently verify the architecture and unit tests once implemented:

1. **Run Unit Tests**:
   ```bash
   .venv/bin/pytest tests/test_cpcv_stress_tester.py -v
   .venv/bin/pytest trading_system/tests/test_cpcv_stress_tester.py -v
   ```
2. **Verify Split Count**:
   - For $N=6, k=2$, assert `len(folds) == 15`.
3. **Verify Purging & Embargo Boundaries**:
   - Assert zero overlap between train and test indices across all 15 splits.
4. **Verify Stress Metrics Calculations**:
   - Confirm $\text{CVaR}_{95} \le \text{VaR}_{95}$ and $\text{CVaR}_{99} \le \text{VaR}_{99}$.
   - Confirm $0.0 \le \text{MDD} \le 1.0$.
