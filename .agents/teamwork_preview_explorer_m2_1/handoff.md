# Handoff Report: Quantitative Alpha & Ensemble Factor Orthogonalization (Milestone 2 - R2)

**Agent:** Explorer M2-1  
**Working Directory:** `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_1`  
**Scope Document:** `PROJECT.md`  

---

## 1. Observation

1. **Target File Locations**:
   - `EnsembleScoringEngine` implementation: `trading_system/src/ai/ensemble_scorer.py` (lines 29-1154).
   - `StrategyCorrelationMonitor` implementation: `trading_system/src/ai/correlation_monitor.py` (lines 45-221).
   - `RegimeFactorSuppressionEngine` implementation: `trading_system/src/ai/factor_suppression.py` (lines 15-258).
   - Contract Specification: `PROJECT.md` (lines 30-32):
     ```
     ### Factor Orthogonalizer ↔ Ensemble Scorer
     - Input: matrix of 17 raw strategy signal scores per ticker X in R^{N x 17}.
     - Output: orthogonalized score matrix X_{ortho} in R^{N x 17} preserving relative variance explaining power.
     ```

2. **17 Strategy Mapping in `combine_predictions()`** (`ensemble_scorer.py` lines 863-881):
   - 17 strategy score columns: `reg_score`, `surge_score`, `ll_score`, `vcp_rule_score`, `vcp_ml_score`, `lstm_score`, `stat_arb_score`, `sector_score`, `rim_score`, `event_score`, `mq_score`, `iv_skew_score`, `order_flow_score`, `reversal_score`, `arm_score`, `card_score`, `latr_score`.

3. **Current Redundancy Handling** (`ensemble_scorer.py` lines 884-913):
   - Computes daily 17x17 Spearman rank correlation matrix $R$ and VIFs using `StrategyCorrelationMonitor`.
   - Dampens base strategy weights $w_i \to w_i^{supp}$ using `RegimeFactorSuppressionEngine`.
   - **Current Deficit**: Weight suppression modifies linear scalar weights $w_i$, but does **not decorrelate the underlying score feature space** $X \in \mathbb{R}^{N \times 17}$. High inter-strategy correlation ($\rho > 0.50$, $\text{VIF} > 4.0$) distorts ensemble scoring and downstream stacking (`MetaEnsembleLearner`).

4. **Cluster Redundancy Observed**:
   - **CORE_AI**: `regression`, `lstm` ($\rho \approx 0.65 - 0.80$)
   - **MOMENTUM**: `surge`, `vcp_ml`, `sector_rotation`, `arm_factor` ($\rho \approx 0.60 - 0.85$)
   - **VALUATION**: `rim_valuation`, `mq_factor` ($\rho \approx 0.50 - 0.70$)
   - **REVERSAL**: `stat_arb`, `vcp_rule`, `short_term_reversal`, `card_factor` ($\rho \approx 0.55 - 0.75$)
   - **FLOW_MICRO**: `lead_lag`, `event_driven`, `iv_skew`, `order_flow`, `latr_factor` ($\rho \approx 0.45 - 0.60$)

---

## 2. Logic Chain

1. **Step 1 (Problem Identification)**: The existing scalar weight dampening $P_i(R)$ in `RegimeFactorSuppressionEngine` penalizes strategy weights $w_i$ when correlation exceeds threshold $\theta(R)$. However, because $S_{linear} = \sum w_i^{supp} S_i$, any two collinear signals $S_i$ and $S_j$ still carry overlapping variance across tickers $N$.
2. **Step 2 (Interface Contract Alignment)**: `PROJECT.md` requires factor orthogonalization directly on the score matrix $X \in \mathbb{R}^{N \times 17} \to X_{ortho} \in \mathbb{R}^{N \times 17}$ before linear blending or meta-learning.
3. **Step 3 (Gram-Schmidt Design)**: For hierarchical regimes (where 1 strategy dominates, e.g. `surge` in BULL regimes), Gram-Schmidt orthogonalization orders vectors by regime weight $w_{(1)} \ge w_{(2)} \dots \ge w_{(17)}$, keeping the #1 strategy vector unmutated ($\boldsymbol{u}_{(1)} = \boldsymbol{x}_{(1)}$) and subtracting projections for subsequent vectors. Post-orthogonalization std dev rescaling preserves relative variance explaining power.
4. **Step 4 (PCA ZCA Symmetric Decorrelation Design)**: For non-hierarchical, multi-factor regimes, ZCA Symmetric Decorrelation computes $X_{decorr} = \bar{X} C^{-1/2} = \bar{X} V \tilde{\Lambda}^{-1/2} V^T$. This guarantees zero pairwise covariance ($\text{Cov}(X_{decorr}) = I$) while minimizing Frobenius distance $\| X_{decorr} - X \|_F$ to original signals.
5. **Step 5 (Integration Strategy)**: A unified `FactorOrthogonalizerEngine` class in `trading_system/src/ai/factor_orthogonalizer.py` will encapsulate both algorithms, allowing `EnsembleScoringEngine` to pass $X_{ortho}$ into linear combination and meta-ensemble stacking.

---

## 3. Caveats

1. **Read-only Investigation**: As an Explorer agent, no source code outside `.agents/teamwork_preview_explorer_m2_1` was edited. Implementation should be carried out by a designated Worker/Implementer agent.
2. **NaN / Missing Data Handling**: Tickers with missing strategy predictions (NaN values) must be filled (e.g. with cross-sectional mean) prior to eigen-decomposition/Gram-Schmidt, and restored after orthogonalization to ensure NaN propagation integrity.
3. **Extreme Low Volatility / Zero Variance**: If a strategy score has zero variance across tickers on a given day (e.g. all 0.0), ridge regularization ($\epsilon = 10^{-6}$) is required during matrix inversion to prevent division by zero or singular matrix errors.

---

## 4. Conclusion

1. **Multicollinearity Impact**: High correlation among the 17 strategies (especially in MOMENTUM and CORE_AI clusters) reduces Effective Strategy Count ($N_{eff}$) and inflates variance under scalar-weight-only suppression.
2. **Recommended Solution**: Implement `FactorOrthogonalizerEngine` (`trading_system/src/ai/factor_orthogonalizer.py`) supporting both Gram-Schmidt (order-dependent by regime weight) and PCA ZCA Symmetric Decorrelation (order-independent minimum Frobenius distance).
3. **Downstream Integration**: Plug `FactorOrthogonalizerEngine` into `EnsembleScoringEngine.combine_predictions()` prior to correlation reporting and linear/meta-ensemble blending.

---

## 5. Verification Method

1. **Inspect Analysis Artifacts**:
   - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_1\analysis.md`
   - `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m2_1\handoff.md`
2. **Execute Pytest Baseline Verification**:
   ```bash
   .venv/bin/pytest tests/test_correlation_suppression.py -v
   ```
3. **Verify Orthogonalization Mathematical Invariants (for future implementer unit test)**:
   - Check that $\text{Cov}(X_{ortho})$ off-diagonals are within $10^{-5}$ of 0.0.
   - Check that $X_{ortho}$ values remain clipped to $[0.0, 1.0]$.
   - Verify that $N_{eff} \approx 17.0$ when calculated on $X_{ortho}$.
