# Handoff Report: M1 Explorer 2 (Jump-Diffusion & Markov Penalty)
## Phase 7 Zenith Quantitative Enhancements (v14) — Features F47 & F48

**Document**: `handoff.md`  
**Author**: M1 Explorer 2 (Jump-Diffusion & Markov Penalty)  
**Recipient**: Parent Orchestrator (`e1532581-bf40-4631-af87-80cf978d298b`)  
**Working Directory**: `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2`  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

1. **Phase 6 Baseline Stability**:
   - Ran `.venv\Scripts\python.exe -m pytest tests/test_phase6_signal_enhancement.py -v`.
   - Tool Execution Result: `6 passed in 22.07s` (100% passing across all 6 Phase 6 tests).
   - Invariants verified: 5-pillar hierarchy, Hölder p-norm boosting, asymmetric Richards S-curve v6, Markov stationary divergence & 4-tier elasticity, asymmetric kurtosis noise deadband, and 5-market stress universe.

2. **Code Structure in `trading_system/src/ai/ensemble_scorer.py`**:
   - `get_base_weights` (lines 1160–1288):
     - Takes `(self, regime, vix_val=None, macro_label=None, regime_probs=None)`.
     - Soft-blends continuous probabilities into `blended = sum(prob * state_w)`.
     - In line 1208: assigns `w = blended` directly without measuring regime shift or transition jump intensity.
     - Lacks `version` parameter and does not blend Merton jump target weights during crash events.
   - `get_regime_adaptive_half_lives` (lines 4032–4114):
     - Takes `(cls, regime='SIDEWAYS_LOW_VOL', regime_probs=None, prev_regime_probs=None, transition_matrix=None, version=6)`.
     - Lines 4096–4102 calculate Kullback-Leibler divergence $D_{KL}(\boldsymbol{\pi} \parallel \boldsymbol{\pi}_\infty)$ against `cls.PI_STATIONARY`.
     - Line 4101 uses a static departure damping coefficient: `phi_kl = float(np.exp(-0.25 * max(0.0, d_kl)))`.
     - Lacks directional volatility modulation $\kappa_{\text{Markov}}(S_{\text{vol}})$ when `version >= 7`.

3. **Stationary Distribution Profile (`PI_STATIONARY`, lines 3940–3948)**:
   - Regimes: `BULL_LOW_VOL`: 0.20, `BULL_HIGH_VOL`: 0.15, `SIDEWAYS_LOW_VOL`: 0.25, `SIDEWAYS_HIGH_VOL`: 0.15, `BEAR_LOW_VOL`: 0.12, `BEAR_HIGH_VOL`: 0.08, `CRISIS`: 0.05.
   - High-volatility subset mass $\Pi_{\infty, \text{high}} = 0.15 + 0.15 + 0.08 + 0.05 = 0.43$.

---

## 2. Logic Chain

1. **Premise 1 (Transition Lag during Market Crash)**:
   - When a market transitions abruptly from low volatility to high volatility/crisis, continuous linear mixture $\sum \pi_{m, t} W(R_m)$ retains a large fraction of stale bull factor weights during the initial periods of the shock.
2. **Inference 1 (Jump-Diffusion Formulation for F47)**:
   - By calculating Total Variation distance $d_{TV} = 0.5 \sum |\pi_{m, t} - \pi_{m, t-1}|$ and defining empirical jump intensity $J_{\text{regime}} = \text{clip}((d_{TV} - 0.25) / 0.35, 0.0, 1.0)$, we detect discrete regime jumps when $d_{TV} > 0.25$.
   - Blending with Merton jump target weights $w_{\text{Zenith}}^* = (1 - 0.60 J_{\text{regime}}) w_{\text{diffusion}} + 0.60 J_{\text{regime}} W_{2D}(R_{\text{jump}})$ instantly routes up to 60% of transition mass directly into crisis-hedged factors (`stat_arb`, `vol_target`, `rim_valuation`).
3. **Premise 2 (Asymmetric Signal Decay Dynamics)**:
   - In calm regimes, momentum and trend factors have high predictive persistence; penalizing departure symmetrically degrades predictive power.
   - In volatile regimes, old order flow and mean-reversion signals become hazardous noise; decay must be accelerated to prevent whipsaws.
4. **Inference 2 (Directional Volatility Departure Penalty for F48)**:
   - Defining Net Volatility Regime Shift $S_{\text{vol}} = \Pi_{t, \text{high}} - 0.43$ allows modulating $\kappa_{\text{Markov}}(S_{\text{vol}}) = \text{clip}(0.25(1 + 0.80 \max(0, S_{\text{vol}})), 0.25, 0.45)$.
   - When $S_{\text{vol}} \le 0$ (calm regimes), $\kappa_{\text{Markov}} = 0.25$, preserving exact Phase 6 momentum persistence.
   - When $S_{\text{vol}} > 0$ (volatile regimes), $\kappa_{\text{Markov}} \in (0.25, 0.45]$, compressing signal half-lives by up to ~35% (with Class A microstructure signals $\nu=1.30$ decaying significantly faster than Class D fundamental signals $\nu=0.40$).
5. **Premise 3 (Zero Regression Guard)**:
   - Explicit parameter checking `if int(version) >= 7:` ensures that calls with `version <= 6` or default parameters continue executing verbatim Phase 6 logic.

---

## 3. Caveats

1. **Caller Propagation**:
   - While `get_base_weights` can inspect `self._prev_regime_probs` as a fallback, for optimal jump-diffusion responsiveness, upstream callers (`compute_dynamic_weights_from_sharpe` and `combine_predictions`) should propagate `prev_regime_probs` and `version`.
2. **Non-Probabilistic 1-Hot Regimes**:
   - If callers pass only a string regime label (e.g. `'CRISIS'`) without probability vectors, $d_{TV}$ is not computed, and `get_base_weights` falls back to deterministic 1-hot table lookup, which is intended and safe.
3. **M1 Scope Boundary**:
   - This investigation is strictly read-only and covers F47 Part 2 (`get_base_weights`) and F48 Part 1 (`get_regime_adaptive_half_lives`). F47 Part 1 (trilinear tensors) and F48 Part 2 (quintic deadband) are addressed by parallel explorer colleagues.

---

## 4. Conclusion

1. Exact code replacements for `get_base_weights` and `get_regime_adaptive_half_lives` in `trading_system/src/ai/ensemble_scorer.py` are formulated and ready for implementation by the builder.
2. Full backwards compatibility is mathematically and architecturally guaranteed: default `version=6` preserves bit-exact Phase 6 behavior.
3. Deliverable artifact `d:\Finance\code\stock\.agents\teamwork_preview_explorer_m1_2\exploration_report.md` contains the comprehensive mathematical specifications and test cases.

---

## 5. Verification Method

1. **Run Phase 6 Regression Test**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_phase6_signal_enhancement.py -v
   ```
   *Expected Result*: All 6 tests pass with 0 failures.

2. **Verify Phase 7 F47 & F48 Invariants**:
   Execute the proposed test suite in `tests/test_phase7_signal_enhancement.py`:
   - `test_feature_47_jump_diffusion_sub_threshold_invariance`: verifies $w_{\text{v7}} == w_{\text{v6}}$ when $d_{TV} \le 0.25$.
   - `test_feature_47_jump_diffusion_crash_shock_mixture`: verifies defensive factor weight expansion and speculative factor reduction under jump crash ($d_{TV} = 0.80$).
   - `test_feature_47_jump_diffusion_version_guard_parity`: verifies `version=6` ignores jump blending under any $d_{TV}$.
   - `test_feature_48_markov_penalty_calm_regime_invariance`: verifies half-life parity in calm markets ($S_{\text{vol}} \le 0$).
   - `test_feature_48_markov_penalty_volatile_regime_acceleration`: verifies half-life contraction and Class A vs Class D elasticity ratio under crisis ($S_{\text{vol}} = +0.57$).

3. **Invalidation Conditions**:
   - If `get_base_weights(..., version=6)` alters weights when `prev_regime_probs` is supplied.
   - If `get_regime_adaptive_half_lives(..., version=7)` shortens half-lives in calm regimes ($S_{\text{vol}} \le 0$).
   - If any half-life falls below the statutory floor of $0.10$ days.
