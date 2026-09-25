# Scope: Core Trading System Integrity & Remediation (116 Failing Tests)

## Architecture & Subsystem Boundaries
- **Track 1: Ensemble & Factor Numerical Stability (R1 & R2)**
  - `src/ai/score_normalizer.py`: CrossSectionalScoreNormalizer (percentile rank, monotonic top-decile spread scaling, Gaussian CDF, NaN/zero/outlier handling, small universe 5-8 symbols)
  - `src/ai/ensemble_scorer.py`: EnsembleScoringEngine (extreme edge cases, hyper-exponential rank modulation, gamma_top reachability, regime branch ordering and backward compatibility)
  - `src/ai/factor_suppression.py`: FactorSuppressionEngine (VIF & regime noise suppression)
- **Track 2: ML Predictors & Alpha Returns Maximization (R4)**
  - `src/ai/transformer_predictor.py` (or transformer predictor module): Forward tensor shape, sequence dimension, train/inference pipeline, save/load integrity
  - `src/ai/prediction_model.py` / Sprint 3 multivariate LSTM: Sequence rolling normalization and multi-horizon inference
  - `v7` Returns Maximization: P90 hurdle rate calculation, unscaled trading transaction cost adjustment
- **Track 3: Benchmark Report & SHA256 Synchronization (R3)**
  - Phase 60 to Phase 65 benchmark report markdown files in canonical paths:
    - Root / benchmarks directories (e.g. `docs/reports/` or `trading_system/reports/` or `gh-pages/`)
    - Exact SHA256 hash assertions in `tests/test_phase60_adversarial_oms_benchmark.py` through `test_phase65_adversarial_oms_benchmark.py`
- **Track 4: Full Pipeline & Regression Verification (R5)**
  - `trading_system/run_pipeline.py`: Syntax, imports, executable integrity
  - Full pytest regression suite: `trading_system\.venv\Scripts\python.exe -m pytest tests -k "not benchmark_phase"` verifying 5,624+ passing tests with 0 regressions

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | R1: Numerical Stability Edge Cases | All zeros/ones, 90-100% NaNs, extreme outliers, small universes (5-8 assets), ZeroDivision/NaN prevention | M1 | ORIGINAL_REQUEST R1 |
| 2 | R1: Monotonic Top-Decile Spread | Top-decile spread scaling and monotonicity preservation | M1 | ORIGINAL_REQUEST R1 |
| 3 | R2: Hyper-Exponential Rank & Gamma Top | Hyper-exponential rank modulation and gamma_top reachability in Phase 8/9 | M1 | ORIGINAL_REQUEST R2 |
| 4 | R2: Multi-Market Regime Branch Ordering | Random stress regime branch ordering and backward compatibility | M1 | ORIGINAL_REQUEST R2 |
| 5 | R4: TransformerPredictor Forward & State | Fix forward shape mismatch, sequence length, train/inference/save/load | M2 | ORIGINAL_REQUEST R4 |
| 6 | R4: Sprint3 LSTM & v7 Alpha Returns | Fix Sprint 3 multivariate LSTM inference and v7 P90 hurdle rate / unscaled costs | M2 | ORIGINAL_REQUEST R4 |
| 7 | R3: Phase 60-65 Benchmark Reports | Reconcile markdown report contents and generate canonical outputs | M3 | ORIGINAL_REQUEST R3 |
| 8 | R3: Phase 60-65 SHA256 Sync | Update SHA256 hash assertions in test files to match canonical reports | M3 | ORIGINAL_REQUEST R3 |
| 9 | R5: Pipeline Executability Check | Verify `run_pipeline.py` loads and parses without error | M4 | ORIGINAL_REQUEST R5 |
| 10 | R5: Full Regression Audit | Ensure 0 regressions across 5,624+ existing passing tests | M4 | ORIGINAL_REQUEST R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Failure Diagnostics | Parallel exploration across Tracks 1, 2, 3 to pinpoint exact failing tests, line numbers, error traces, and remediation strategy | none | IN_PROGRESS |
| M1 | Track 1 Remediation | Fix R1 & R2 numerical stability, edge cases, top-decile spread, hyper-exponential rank, gamma_top in `ensemble_scorer.py`, `score_normalizer.py` | M0 | PLANNED |
| M2 | Track 2 Remediation | Fix R4 TransformerPredictor forward tensor shape, Sprint 3 LSTM, v7 P90 hurdle rate in ML modules | M0 | PLANNED |
| M3 | Track 3 Remediation | Fix R3 Phase 60-65 benchmark markdown reports and SHA256 synchronization | M0 | PLANNED |
| M4 | System Integration & Regression Audit | Run full test suite, verify 100% pass on 116 failing tests, 0 regressions on 5624+ tests, verify `run_pipeline.py` | M1, M2, M3 | PLANNED |

## Interface Contracts & Constraints
- `CrossSectionalScoreNormalizer`: must return float32 numpy arrays matching input shape, no NaNs/Infs even when input is all NaN or all zero.
- `EnsembleScoringEngine`: must cleanly handle small universes (5-8 items), NaN proportions up to 100%, and preserve monotonic ordering in top deciles.
- `TransformerPredictor`: forward pass must accept batch tensors of shape `(batch_size, seq_len, num_features)` or expected input format and output predictions matching target horizons.
- Report sync: Canonical report files must be updated consistently across all mirrored paths, then SHA256 calculated via standard hashlib sha256 hex digest.
