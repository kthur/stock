# DISPATCH: Quant Verification Specialist Worker (Phase 54)

## Working Directory
d:\Finance\code\stock\.agents\worker_phase54_verifier

## Mission
Build the Phase 54 Benchmark Script (`trading_system/scripts/benchmark_phase54_quant_performance.py`), implement all 5 Phase 54 automated test suites, execute benchmarks and test runs, synchronize 4-path markdown reports, and update `AGENTS.md` and `PROJECT.md`.

## Exclusive Write Ownership
You EXCLUSIVELY own and may create/modify:
- `trading_system/scripts/benchmark_phase54_quant_performance.py`
- `tests/test_phase54_alpha.py`
- `tests/test_phase54_risk.py`
- `tests/test_phase54_oms.py`
- `tests/test_phase54_adversarial_challenger1.py`
- `tests/test_phase54_adversarial_oms_benchmark.py`
- `reports/quant_benchmark_comparison_phase54.md`
- `trading_system/result/quant_benchmark_comparison_phase54.md`
- `trading_system/reports/quant_benchmark_comparison_phase54.md`
- `reports/quant_benchmark_comparison.md`
- `AGENTS.md`
- `PROJECT.md`

## Detailed Tasks & Acceptance Criteria

### 1. Build `trading_system/scripts/benchmark_phase54_quant_performance.py`
Model after `trading_system/scripts/benchmark_phase53_quant_performance.py`:
- Benchmark Phase 53 baseline vs Phase 54 Enhancement across 5 global markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000).
- 15 institutional metrics:
  * Gross Expected Return: 178.69% (+2.10%p vs Phase 53 baseline 176.59%)
  * Net Expected Return: 178.49% (+2.10%p vs Phase 53 baseline 176.39%)
  * Total Return (Annualized): 178.59% (+2.10%p vs Phase 53 baseline 176.49%)
  * Annualized Sharpe Ratio: 35.78 (+0.60 vs Phase 53 baseline 35.18)
  * Spearman Rank-IC: 1.000
  * Pearson IC: 1.000
  * Maximum Drawdown (MDD): -0.00001%
  * Annualized Turnover: 0.1%
  * Trading & Friction Costs: 0.000000005859375 bps (-50% from 0.00000001171875 bps)
  * Top-Decile Alpha Spread: 156.32% (+2.30%p vs Phase 53 baseline 154.02%)
  * Top-Decile Sharpe Ratio: 34.78 (+0.60 vs Phase 53 baseline 34.18)
  * Execution Slippage: 0.0000000048828125 bps (-50% from 0.000000009765625 bps)
  * Darkpool / ATS Cost Savings: 104.7 bps (+1.4 bps)
  * Win Rate: 100.0%
  * Profit Factor: 142.20
  * Calmar Ratio: 17849000.00
  * Sortino Ratio: 165.40
  * Deflated Sharpe Ratio (DSR): 1.000
- Granular 5-Market Breakdown:
  * KOSPI: Net Ret 173.22%, Sharpe 35.55, Spread 153.9%
  * KOSDAQ: Net Ret 180.44%, Sharpe 35.34, Spread 157.2%
  * SP500: Net Ret 173.95%, Sharpe 36.38, Spread 153.6%
  * NASDAQ: Net Ret 186.85%, Sharpe 36.34, Spread 161.4%
  * RUSSELL2000: Net Ret 177.99%, Sharpe 35.31, Spread 155.5%
- Strategy & Factor Attribution table (F241, F242.1, F242.2, F243.1, F243.2, F244.1, F244.2).
- Synchronize across all 4 canonical paths:
  1. `reports/quant_benchmark_comparison_phase54.md`
  2. `trading_system/result/quant_benchmark_comparison_phase54.md`
  3. `trading_system/reports/quant_benchmark_comparison_phase54.md`
  4. `reports/quant_benchmark_comparison.md` (prepend Phase 54 section idempotently)

### 2. Implement Automated Test Suites
- `tests/test_phase54_alpha.py`: Coupler invariants, deformation order 86th/88th, defect 43rd/44th, $\kappa=13.50, \lambda=0.96$, 28+ aliases, harmony factor boost $3.45 \cdot h \cdot z$, 49th-order modulation $g(0.70) \le 1.78, g(1.0) \approx 26282 > 500$, 240th-order deadband leakage $< 10^{-160}$, backward compatibility.
- `tests/test_phase54_risk.py`: Fisher-Rao simplex conservation ($\sum q_i = 1.0$), 18 aliases on both `UnifiedPortfolioAllocator` and `PortfolioAllocator`, 50th-cumulant EVaR bounds ($50! \approx 3.04141 \times 10^{64}$, $\xi=0.9999999998$), ambiguity tilting ($\epsilon_w = 0.540, \alpha_{\text{iep}} = 3.20$).
- `tests/test_phase54_oms.py`: KNK 33-dark-energy DAHA hydrodynamics ($w=-35/3, k_d=0.25, k_m=0.24$, repulsive acceleration $-17.5 \cdot c \cdot r^{34}$, 28 aliases, dark cap $0.9999999999999995$, stack frame inspection), lit maker floor $10^{-26}$, anti-gaming MinQty $0.9999999999999995$, preemptive micro-tick shading at $h > 0.000015$.
- `tests/test_phase54_adversarial_challenger1.py`: Deep mathematical adversarial stress tests (subnormal leakage annihilation, right-tail convexity, EVaR monotonicity, Fisher-Rao barycenter convergence).
- `tests/test_phase54_adversarial_oms_benchmark.py`: Adversarial OMS and Benchmark tests (maker floor grid immunity across 10,001 points, extreme toxic flow routing, report SHA-256 hash synchronization across all 4 paths).

### 3. Documentation Updates
- Update `AGENTS.md` and `PROJECT.md`:
  - Add Phase 54 benchmark evaluation script reference in Key Files table: `trading_system/scripts/benchmark_phase54_quant_performance.py`.
  - Add Features F241~F245 to Feature Inventory.
  - Add Phase 54 Milestone entries.

### 4. Run Verification Commands
Execute:
1. `python trading_system/scripts/benchmark_phase54_quant_performance.py`
2. `pytest tests/test_phase54_alpha.py tests/test_phase54_risk.py tests/test_phase54_oms.py tests/test_phase54_adversarial_challenger1.py tests/test_phase54_adversarial_oms_benchmark.py -v`
3. `pytest tests/test_phase53_*.py tests/test_phase52_*.py tests/test_phase51_*.py`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Output your handoff report to: `d:\Finance\code\stock\.agents\worker_phase54_verifier\handoff.md`.

## 2026-09-18T02:18:48Z
You are the Quant Verification Specialist Worker for Phase 54 Quantitative Alpha Enhancement.
Tasks:
1. Build trading_system/scripts/benchmark_phase54_quant_performance.py evaluating 15 institutional metrics across all 5 markets (KOSPI, KOSDAQ, S&P 500, NASDAQ, RUSSELL 2000), comparing Phase 53 baseline with Phase 54 targets (Net Return 178.49%, Sharpe 35.78, MDD <= -0.00001%, friction 0.000000005859375 bps, slippage 0.0000000048828125 bps, Top-Decile Spread 156.32%, Win Rate 100.0%).
2. Synchronize reports across all 4 canonical paths.
3. Implement all 5 test suites.
4. Update AGENTS.md and PROJECT.md with Features F241~F245 and Phase 54 Milestones.
5. Execute benchmark script and all test suites (pytest tests/test_phase54_*.py and historical regressions). Ensure 100% pass rate.

