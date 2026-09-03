# BRIEFING — 2026-09-03T15:49:30Z

## Mission
Recommend the exact fix strategy and code-level design for Milestone 1 Feature 2: Dual-Consensus Spectral Whitening (preserving PC1 & PC2 leading eigenvalues and Marchenko-Pastur spectral noise flooring).

## 🔒 My Identity
- Archetype: explorer
- Roles: Dual-Consensus Spectral Whitening Specialist
- Working directory: d:\Finance\code\stock\.agents\explorer_m1_2_opt2
- Original parent: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Milestone: Milestone 1 Feature 2 (Dual-Consensus Spectral Whitening)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement in source files (no edits to trading_system/)
- Recommend exact fix strategy and code-level design for Milestone 1 Feature 2
- Target file: `trading_system/src/ai/factor_orthogonalizer.py` (and test coverage in `tests/test_factor_orthogonalization.py`)
- Produce `plan_m1_2.md` and `handoff.md` in own directory
- Must preserve backward compatibility with existing callers/tests

## Current Parent
- Conversation ID: 31b60ad6-8c74-4119-a790-2b2e694a292d
- Updated: 2026-09-03T15:42:14Z

## Investigation State
- **Explored paths**:
  - `trading_system/src/ai/factor_orthogonalizer.py`
  - `trading_system/src/ai/ensemble_scorer.py`
  - `tests/test_factor_orthogonalization.py`
  - `tests/test_factor_ortho_empirical_stress.py`
  - `tests/test_v8_remediation.py`
- **Key findings**:
  - Unscaled Marchenko-Pastur floor $(1 - \sqrt{K/N})^2$ fails under high factor correlation (producing $0.7588 > 0.30$ correlation failure) because it treats the spiked correlation matrix as white noise.
  - Scaling the MP lower edge by noise-subspace variance $\sigma_{\text{noise}}^2$ aligns with RMT and passes 106/106 tests with zero regressions.
  - Dual-consensus preservation (`preserve_top_k=2`) maintains $f(\lambda_K) = 1.0$ (PC1 Trend) and $f(\lambda_{K-1}) = 1.0$ (PC2 Value/Quality) uncompressed, reducing mean correlation to $0.1890 < 0.30$.
- **Unexplored areas**: None within Feature 2 scope. Ready for Worker implementation.

## Key Decisions Made
- Formulated exact mathematical specification for noise-subspace variance $\sigma_{\text{noise}}^2 = \frac{1}{K - k} \sum_{i=1}^{K - k} \lambda_i$.
- Formulated MP floor: $\lambda_{\text{floor}} = \text{clip}(\max(\sigma_{\text{noise}}^2(1 - \sqrt{q})^2, 0.01 \cdot \sigma_{\text{noise}}^2), 10^{-4}, 1.0)$.
- Mapped `preserve_consensus_pc1=True` to `eff_top_k=1` for backward compatibility.
- Generated comprehensive technical plan `plan_m1_2.md` and self-contained handoff report `handoff.md`.

## Artifact Index
- `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\plan_m1_2.md` — Technical plan for M1 Feature 2
- `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\handoff.md` — 5-component handoff report
- `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\progress.md` — Liveness progress log
- `d:\Finance\code\stock\.agents\explorer_m1_2_opt2\DISPATCH.md` — Dispatch record
