# DISPATCH: Worker M1 (Phase 8 Signal & Alpha Architecture)

## Working Directory
`d:\Finance\code\stock\.agents\worker_m1_signal`

## Master Reference Files
- `d:\Finance\code\stock\.agents\ORIGINAL_REQUEST.md` (Section ## 2026-09-05T02:15:24Z)
- `d:\Finance\code\stock\.agents\explorer_m1_survey\handoff.md` (Exact technical blueprint and equations)
- `d:\Finance\code\stock\AGENTS.md`

## File Ownership (Exclusive)
- `trading_system/src/ai/ensemble_scorer.py`
- `trading_system/src/ai/factor_suppression.py`
- `tests/test_phase8_signal_enhancement.py`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Tasks & Specifications
1. **Feature F51.1 (Riemannian Manifold Geodesic 5-Pillar Synergy)** in `src/ai/ensemble_scorer.py`:
   - In `compute_quint_pillar_tensor_synergy`: Add `version >= 8` branch.
   - Map 5-pillar vector $(\psi_{\text{val}}, \psi_{\text{mom}}, \psi_{\text{flow}}, \psi_{\text{cat}}, \psi_{\text{net}})$ onto probability simplex $\mathcal{S}^4$ and isometrically to $\mathbb{S}^4$ via $u_k = \sqrt{p_k}$.
   - Compute Bhattacharyya affinity $\text{BC}(p, p_0) = \sum_{k=1}^5 \sqrt{0.20 p_k}$ and Fisher-Rao geodesic arc distance $d_R(p, p_0) = \arccos(\text{clip}(\text{BC}, 0.0, 1.0))$.
   - Apply Riemannian harmony regularizer $H_{\text{Riemann}} = \exp(-2.40 d_R^2)$ and $\text{harmony\_factor} = 1.0 + 0.30 \cdot H_{\text{Riemann}} \cdot \mathbf{1}_{p_{\text{mean}} > 0.38}$.
   - Apply core triplet multiplier 1.50x for `val-mom-flow` and 1.25x for `flow-cat-net`.
   - In `BULL_LOW_VOL`, expand cap to 0.250 (max multiplier 1.250x); in `CRISIS`, maintain strict cap 0.040 (1.040x).
2. **Feature F51.2 (Hyperexponential Convex Rank Modulation)** in `src/ai/ensemble_scorer.py`:
   - Add class method `get_regime_adaptive_gamma_top(cls, regime='BULL_LOW_VOL', version=8) -> float` returning $\gamma_{\text{top}} \in [0.20, 0.85]$.
   - In `combine_predictions`: Under `version >= 8` for assets with $z_{\text{denoised}} \ge 0.0$, apply hyperexponential convex rank modulation:
     $\text{mult} = 0.50 + 0.65 \cdot r \cdot \exp(\gamma_{\text{top}} \cdot r^3)$ where $r \in [0, 1]$ is the cross-sectional percentile rank.
     For $z_{\text{denoised}} < 0.0$, maintain linear negative attenuation $\text{mult} = 1.40 - 0.80 \cdot r$.
3. **Feature F52.1 (Hurst Exponent Fractional Jump-Diffusion)** in `src/ai/ensemble_scorer.py`:
   - In `get_base_weights`: When `version >= 8`, scale the jump indicator by fractional persistence: $J_{\text{frac}} = \text{clip}(J_{\text{regime}} \cdot (2H)^{1.5}, 0.0, 1.0)$ where $H$ is the Hurst exponent (default 0.50).
   - Compute mixture: $\text{blend\_jump} = \min(0.85, 0.65 \cdot J_{\text{frac}})$, $w_{\text{sovereign}} = (1 - \text{blend\_jump}) \cdot w_{\text{diff}} + \text{blend\_jump} \cdot W_{2D}(R_{\text{jump}})$.
   - In `get_regime_adaptive_half_lives`: When `version >= 8`, adjust Markov departure penalty with Hurst exponent.
4. **Feature F52.2 (Asymmetric Septic Wavelet Noise Deadband)** in `src/ai/ensemble_scorer.py` and `src/ai/factor_suppression.py`:
   - Support $\alpha = 7.0$ septic wavelet thresholding in `apply_quintic_hyperbolic_deadband` and `apply_smooth_noise_deadband(..., version=8)` to achieve $< 0.003\%$ leakage ($99.997\%$ noise suppression) while transmitting $100.000\%$ of conviction signals $|z| \ge 0.150$.
5. **Unit Tests Creation & Verification**:
   - Create `tests/test_phase8_signal_enhancement.py` covering all 6 test functions specified in `explorer_m1_survey/handoff.md`.
   - Run tests using `.venv\Scripts\python.exe -m pytest tests/test_phase8_signal_enhancement.py tests/test_phase7_signal_enhancement.py tests/test_score_normalizer.py -v`.
   - Ensure 100% tests pass with 0 regressions.
6. Write completion report to `d:\Finance\code\stock\.agents\worker_m1_signal\handoff.md`.

## 2026-09-05T02:21:50Z
You are Worker M1 (Phase 8 Signal & Alpha Architecture).
Your working directory is: d:\Finance\code\stock\.agents\worker_m1_signal

File Ownership (Exclusive):
- trading_system/src/ai/ensemble_scorer.py
- trading_system/src/ai/factor_suppression.py
- tests/test_phase8_signal_enhancement.py

Execute the tasks in DISPATCH.md:
1. Implement F51.1 (Riemannian Manifold Geodesic 5-Pillar Synergy) in `ensemble_scorer.py`.
2. Implement F51.2 (Hyperexponential Convex Rank Modulation) in `ensemble_scorer.py`.
3. Implement F52.1 (Hurst Fractional Jump-Diffusion) in `ensemble_scorer.py`.
4. Implement F52.2 (Asymmetric Septic Wavelet Noise Deadband) in `ensemble_scorer.py` and `factor_suppression.py`.
5. Create comprehensive unit tests in `tests/test_phase8_signal_enhancement.py`.
6. Run tests via `.venv\Scripts\python.exe -m pytest tests/test_phase8_signal_enhancement.py tests/test_phase7_signal_enhancement.py tests/test_score_normalizer.py -v`.
7. Write your handoff report to `d:\Finance\code\stock\.agents\worker_m1_signal\handoff.md`.
8. Send a message to the orchestrator with your completion summary and handoff path.

