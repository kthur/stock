# Progress: Explorer M1-2 (Exponential Decay Filtering & Momentum Inertia)
Last visited: 2026-09-04T06:01:30+09:00

- [x] Initial setup & briefing initialized
- [x] Investigate F04: `apply_exponential_decay_filter` and `apply_rank_ic_decay_calibration` in `ensemble_scorer.py`
  - [x] Analyze current implementation of `apply_exponential_decay_filter` (lines 3362-3424)
  - [x] Analyze current implementation of `apply_rank_ic_decay_calibration` (lines 1215-1255)
  - [x] Inspect call sites and data flow in `combine_predictions`
  - [x] Design state caching `self._prev_filtered_scores[market]` and cold start handling
- [x] Investigate F05: Trend inertia boost vs crash protection & reversal calibration
  - [x] Analyze `compute_dynamic_weights_from_sharpe` (lines 1002-1205)
  - [x] Differentiate `BULL_LOW_VOL` vs `BULL_HIGH_VOL` for momentum strategies
  - [x] Calibrate reversal strategies in bear and crisis regimes
- [x] Formulate exact code replacement diffs & line numbers for Worker
- [x] Formulate unit test specifications & assertions
- [x] Write comprehensive handoff.md report
