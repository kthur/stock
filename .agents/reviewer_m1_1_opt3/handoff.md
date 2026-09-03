# Milestone 1 Review & Adversarial Challenge Report (Features F01, F02, F03, F05)

**Reviewer**: Reviewer M1-1 (`reviewer`, `critic`)  
**Scope**: Features F01, F02, F03, F05 in `trading_system/src/ai/ensemble_scorer.py`  
**Verdict**: **APPROVE**  
**Date**: 2026-09-04T06:54:30+09:00  

---

## 1. Observation

### 1.1 Direct Code Inspection
Direct examination of `trading_system/src/ai/ensemble_scorer.py` confirms genuine and complete implementations:

1. **Feature F01: 7-State 2D Regime Matrix & Dedicated `CRISIS` Base Weights Dictionary**:
   - `REGIME_2D_WEIGHTS['CRISIS']` (lines 472–510) explicitly specifies base weights for all 37 strategies:
     ```python
     'CRISIS': {  # sum = 1.0000 across all 37 strategies, all >= 0.005
         'regression': 0.050,
         'surge': 0.005,
         'lead_lag': 0.015,
         'vcp_rule': 0.005,
         'vcp_ml': 0.005,
         'lstm': 0.015,
         'stat_arb': 0.070,
         'sector_rotation': 0.020,
         'rim_valuation': 0.065,
         'event_driven': 0.020,
         'mq_factor': 0.040,
         'iv_skew': 0.035,
         'order_flow': 0.025,
         'short_term_reversal': 0.055,
         'arm_factor': 0.015,
         'card_factor': 0.050,
         'latr_factor': 0.045,
         'inst_foreign_sector': 0.020,
         'supply_chain': 0.010,
         'sentiment': 0.025,
         'factor_neutralized': 0.050,
         'vol_target': 0.080,
         'microstructure': 0.015,
         'accruals_quality': 0.060,
         'short_squeeze': 0.005,
         'valueup_catalyst': 0.035,
         'trend_efficiency': 0.005,
         'gamma_squeeze': 0.005,
         'insider_buying': 0.025,
         'darkpool': 0.015,
         'earnings_tone_drift': 0.015,
         'cross_asset_spillover': 0.020,
         'supply_chain_gnn': 0.010,
         'range_expansion_breakout': 0.005,
         'dual_correction': 0.025,
         'index_rebalance': 0.015,
         'overnight_gap_reversal': 0.025,
     }
     ```
   - Strategy count: exactly 37 strategies.
   - Sum: $\sum w_i = 1.000000$.
   - Weight floor: $\min(w_i) = 0.0050$, so all $w_i \ge 0.0050$.
   - Defensive dominance: `vol_target` (0.080), `stat_arb` (0.070), `rim_valuation` (0.065), `accruals_quality` (0.060), `short_term_reversal` (0.055), `card_factor` (0.050).
   - High-beta throttling: `surge`, `vcp_rule`, `vcp_ml`, `short_squeeze`, `gamma_squeeze`, `trend_efficiency`, and `range_expansion_breakout` are capped at exactly 0.0050.
   - In `get_base_weights()` (lines 1156–1170), resolution logic explicitly matches `"CRISIS"` in upper case or substring:
     ```python
     regime_str = str(regime).strip().upper() if regime is not None else ""
     if isinstance(regime, str) and regime in self.REGIME_2D_WEIGHTS:
         w = dict(self.REGIME_2D_WEIGHTS[regime])
     elif regime_str in self.REGIME_2D_WEIGHTS:
         w = dict(self.REGIME_2D_WEIGHTS[regime_str])
     elif "CRISIS" in regime_str:
         w = dict(self.REGIME_2D_WEIGHTS["CRISIS"])
     ```
     This completely eliminates the previous defect where `'CRISIS'` fell through to `SIDEWAYS_LOW_VOL`.

2. **Feature F02: Markov Posterior Regime Soft-Blending**:
   - Lines 1091–1155 implement convex combination:
     $$\mathbf{w}_{\text{base}}(t) = \sum_m \pi_{t, m} \mathbf{w}^{(m)}$$
   - Handles 2D regime posterior probability dictionaries, 1D regime posterior probability dictionaries (mapping `bear` $\to 0$, `sideways` $\to 1$, `bull` $\to 2$), and unnormalized or dirty inputs (filtering out non-finite and negative values, with safe renormalization).
   - Falls back safely to `SIDEWAYS_LOW_VOL` if $\sum \pi_{t, m} \le 10^{-12}$.

3. **Feature F03: Continuous TV-Distance & VIX Entropy Weight Smoothing**:
   - Lines 1511–1552 compute continuous Total Variation distance:
     $$d_{\text{TV}} = \frac{1}{2} \sum_s |\pi_{t, s} - \pi_{t-1, s}|$$
   - Lines 1531–1539 compute continuous VIX stress $\sigma_{\text{vix}} = \text{clip}\left(\frac{\text{VIX} - 18}{22}, 0, 1\right)$ and ambiguity entropy:
     $$H_{\text{vix}} = -\frac{p \ln p + (1-p) \ln(1-p)}{\ln 2} \quad \text{where } p = \text{clip}\left(\frac{\text{VIX} - 12}{28}, 10^{-4}, 1 - 10^{-4}\right)$$
   - Lines 1547–1551 compute dynamic smoothing speed:
     $$\alpha_t = \text{clip}(\alpha_0 + \beta_{\text{trans}} d_{\text{TV}} + \beta_{\text{vix}} \sigma_{\text{vix}} + \beta_{\text{ent}} H_{\text{vix}} + \beta_{\text{tilt}}, 0.15, 0.85)$$
   - Lines 1558–1561 preserve backward compatibility for discrete 1-hot regime transitions when TV smoothing is inactive:
     ```python
     if is_regime_shift and not use_tv_smoothing:
         self._prev_weights[market] = dict(dynamic_weights)
         return dynamic_weights
     ```
     This triggers an exact instant weight reset with zero lag.

4. **Feature F05: Trend Inertia Boost vs Crash Protection**:
   - Lines 1420–1474 implement regime-adaptive momentum turbo multipliers:
     * `BULL_LOW_VOL`: Momentum turbo boosted to $1.40 + 0.20 \times \max(0, \text{autocorr}) \in [1.40, 1.60]\times$, reversal dampened to $0.50\times$, defensive $0.70\times$.
     * `BULL_HIGH_VOL`: Crash protection scales momentum back to $1.15\times$, reversal $1.10\times$, reducing momentum/reversal ratio by $65\%$ ($8.14 \to 2.79$).
     * `CRISIS` / `BEAR_HIGH_VOL`: Momentum slashed to $0.50\times$, reversal boosted to $1.40 \times (1.0 + 0.20 \times \text{vix\_stress}) \in [1.40, 1.68]\times$, defensive $1.30\times$.
     * `BEAR_LOW_VOL`: Momentum $0.70\times$, reversal $1.30\times$, defensive $1.20\times$.
     * `SIDEWAYS_HIGH_VOL`: Momentum $0.85\times$, reversal $1.30\times$, defensive $1.10\times$.

### 1.2 Integrity Violation Check
- **Hardcoded test fixtures in source code**: None found. Grep for test symbols ("AAPL", "005930") returned zero matches in `ensemble_scorer.py`.
- **Facade implementations**: None. All logic computes genuine mathematical transformations.
- **Shortcuts / Task Bypasses**: None. All 37 strategies are actively utilized in all 7 2D regimes.
- **Verification integrity**: Tested via independent adversarial test suite without mocks.

---

## 2. Logic Chain

1. **F01 (CRISIS Base Weights & Resolution)**:
   - *Observation*: `REGIME_2D_WEIGHTS['CRISIS']` contains 37 strategies summing to 1.0000 with min weight 0.0050. `get_base_weights("CRISIS")` and variants return `vol_target = 0.080` while `get_base_weights("SIDEWAYS_LOW_VOL")` returns `0.020`.
   - *Deduction*: Extreme stress environments will now route capital into defensive strategies (`vol_target`, `stat_arb`, `rim_valuation`, `accruals_quality`) rather than defaulting to calm sideways trading.

2. **F02 (Markov Posterior Soft-Blending)**:
   - *Observation*: Blending `{"BULL_LOW_VOL": 0.50, "SIDEWAYS_LOW_VOL": 0.30, "CRISIS": 0.20}` produces an exact convex combination matching theoretical weights to within $10^{-6}$, and dirty inputs are sanitized and normalized.
   - *Deduction*: Continuous Markov regime probabilities eliminate artificial portfolio turnover caused by knife-edge regime boundaries.

3. **F03 (TV-Distance & VIX Entropy Smoothing)**:
   - *Observation*: $\alpha_t$ is strictly clamped within $[0.15, 0.85]$. Under severe regime shifts with high VIX, $\alpha_t$ accelerates toward 0.85 for rapid adaptation. In absence of TV smoothing, legacy 1-hot switches trigger instant reset (`eff_alpha = 1.0`).
   - *Deduction*: System dynamically balances responsiveness during crises with turnover preservation during tranquil regimes, without breaking existing regression tests.

4. **F05 (Trend Inertia vs Crash Protection)**:
   - *Observation*: In `BULL_LOW_VOL`, factor rank autocorrelation scales momentum turbo from $1.40\times$ up to $1.60\times$. In `BULL_HIGH_VOL`, momentum is curtailed to $1.15\times$. In `CRISIS`, momentum is halved ($0.50\times$) while reversal factors receive up to $1.68\times$ allocation.
   - *Deduction*: The system captures momentum persistence in steady bulls while mitigating momentum crash risk (Barroso & Santa-Clara 2015) in volatile and crisis regimes.

---

## 3. Caveats

1. In environments where `StrategyRegistry` discovers standalone strategies (such as `opening_auction_arbitrage`), they receive 0.0 weight by design, resulting in 37 active strategies (sum = 1.0000) and 1 standalone signal.
2. In `CRISIS` with very high VIX ($\ge 40$), the combined effect of `apply_vix_override` (+0.08 base weight boost to 5 defensive strategies) and dynamic scoring boosts defensive strategies (`vol_target` to 11.12%, `stat_arb` to 13.37%). While `short_term_reversal`'s multiplier is boosted ($1.68\times$), its final normalized weight (5.49%) is heavily dominant over momentum (`surge` at 0.96%), though defensive factors absorb the largest share of capital. This is financially desirable in severe crises.

---

## 4. Conclusion

**Verdict**: **APPROVE**

Milestone 1 features F01, F02, F03, and F05 are implemented with high mathematical rigor, zero integrity shortcuts, full backward compatibility, and 100% test pass rates across all 48 test targets and adversarial stress benchmarks.

---

## 5. Verification Method

### Test Suite Execution
```bash
# Full Milestone 1 regression test suites (48 passed in 110s, 100%)
.venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py tests/test_hpo_and_2d_ensemble.py tests/test_system_wide_world_class_improvements.py tests/test_adversarial_regime_sharpe_m2.py -v

# Independent adversarial stress test suite (100% passed)
.venv\Scripts\python.exe .agents/reviewer_m1_1_opt3/verify_m1_adversarial.py
```

### Verified Claims Matrix
| Claim | Target Location | Verification Method | Result |
|---|---|---|---|
| F01: 37 strategies in CRISIS, sum = 1.0000 | `ensemble_scorer.py:472–510` | Exact count, sum, and floor check | **PASS** |
| F01: No fallback to SIDEWAYS_LOW_VOL | `ensemble_scorer.py:1156–1170` | Tested multiple crisis strings/substrs | **PASS** |
| F02: Markov posterior convex combination | `ensemble_scorer.py:1091–1155` | Evaluated 2D and 1D probability dicts | **PASS** |
| F03: Continuous TV & VIX smoothing | `ensemble_scorer.py:1511–1552` | Simulated TV distance & entropy bounds | **PASS** |
| F03: Backward compatibility instant reset | `ensemble_scorer.py:1558–1561` | Tested legacy 1-hot discrete switch | **PASS** |
| F05: Trend inertia boost in BULL_LOW_VOL | `ensemble_scorer.py:1432–1437` | Autocorr 0.80 vs 0.00 comparison | **PASS** |
| F05: Crash protection in BULL_HIGH_VOL | `ensemble_scorer.py:1441–1448` | Momentum/reversal ratio comparison | **PASS** |
| F05: Reversal boost in CRISIS / BEAR | `ensemble_scorer.py:1449–1458` | Multiplier check across VIX spectrum | **PASS** |
| Zero Integrity Violations | Entire file | AST & keyword grep inspection | **PASS** |
