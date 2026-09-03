# Handoff Report: Explorer M1-2 — Live Alpha Decay Filtering & Momentum Inertia vs Crash Protection
**Author**: Explorer M1-2 (`explorer_m1_2_opt3`)  
**Target Milestone**: Milestone 1 (Features F04 & F05)  
**Target Component**: `trading_system/src/ai/ensemble_scorer.py` (`EnsembleScoringEngine`)  
**Date**: 2026-09-04T06:02:00+09:00  
**Status**: Exploration & Engineering Specification Complete  

---

## 1. Observation

### 1.1 Observation on Orphaned Multi-Horizon Decay Methods (`ensemble_scorer.py:3362-3424`, `1215-1256`)
1. **`apply_exponential_decay_filter` (`ensemble_scorer.py:3362-3424`)**:
   - Signature:
     ```python
     @classmethod
     def apply_exponential_decay_filter(
         cls,
         current_scores: pd.DataFrame,
         previous_scores: Optional[pd.DataFrame] = None,
         custom_half_lives: Optional[Dict[str, float]] = None,
         regime: Optional[Union[int, str]] = None
     ) -> pd.DataFrame:
     ```
   - Mathematical formula implemented:
     $$\alpha_k(R_t) = 1 - \exp\left( - \frac{\ln 2}{\tau_k(R_t)} \right)$$
     $$\tilde{s}_{i, k}(t) = \alpha_k(R_t) s_{i, k}(t) + (1 - \alpha_k(R_t)) \tilde{s}_{i, k}(t-1)$$
   - **Critical Observation**: Grep search across the entire repository reveals that `apply_exponential_decay_filter` is **never called anywhere in `combine_predictions` or the live pipeline**. It is entirely orphaned.
   - **Defects in existing implementation**:
     * Line 3395 maps `'lstm_score': 'regression'` instead of `'lstm_score': 'lstm'`.
     * Line 3421 performs: `curr_indexed[col] = alpha * curr_indexed[col] + (1.0 - alpha) * prev_s` without `.clip(0.0, 1.0)`. While input scores are usually $[0, 1]$, numerical precision noise could drift outside $[0, 1]$.
     * If `previous_scores` contains duplicate symbol rows or duplicate columns, `prev_indexed[col].reindex(...)` raises a pandas `ValueError`.

2. **`apply_rank_ic_decay_calibration` (`ensemble_scorer.py:1215-1256`)**:
   - Signature:
     ```python
     @classmethod
     def apply_rank_ic_decay_calibration(
         cls,
         base_weights: Dict[str, float],
         strategy_rank_ic_dict: Optional[Dict[str, float]] = None,
         strategy_half_lives: Optional[Dict[str, float]] = None,
         latency_days: float = 0.0,
         gamma: float = 1.0,
         regime: Optional[Union[int, str]] = None
     ) -> Dict[str, float]:
     ```
   - Mathematical formula:
     $$w_k^{\text{calibrated}} = w_k \cdot \exp(\gamma \cdot \text{Rank\_IC}_k) \cdot \exp\left( - \frac{\ln 2 \cdot \text{latency}}{\tau_k(R_t)} \right)$$
   - **Critical Observation**: This method is also completely disconnected from `combine_predictions` and `calculate_ensemble_score`.

### 1.2 Observation on Current Momentum Multiplier in `compute_dynamic_weights_from_sharpe` (`ensemble_scorer.py:1112-1128`)
```python
1115: turbo_mult = 1.0
1116: is_bull_regime = 'BULL' in str(regime).upper() or str(regime) == '2'
1117: if is_bull_regime:
1118:     MOMENTUM_TURBO_STRATEGIES = {
1119:         'surge', 'vcp_ml', 'mq_factor', 'order_flow', 'short_squeeze',
1120:         'gamma_squeeze', 'trend_efficiency', 'supply_chain', 'event_driven'
1121:     }
1122:     DEFENSIVE_STRATEGIES = {'stat_arb', 'short_term_reversal', 'vol_target'}
1123:     if strategy in MOMENTUM_TURBO_STRATEGIES:
1124:         turbo_mult = 1.40
1125:     elif strategy in DEFENSIVE_STRATEGIES:
1126:         turbo_mult = 0.70
```
- **Defects Observed**:
  1. **No Volatility Differentiation in Bull Regimes**: Treats `BULL_LOW_VOL` (calm persistent trend with high SNR) and `BULL_HIGH_VOL` (turbulent market with high momentum crash risk) identically with `turbo_mult = 1.40`.
  2. **No Trend Inertia Tracking**: Does not reward factors displaying positive rank autocorrelation ($\rho_k^{\text{autocorr}} > 0$).
  3. **Zero Crash Protection in High-Vol Bull**: When volatility spikes in bull markets, continuing to push momentum at $1.40\times$ causes catastrophic momentum crashes (Barroso & Santa-Clara 2015).
  4. **Zero Reversal Calibration in Bear / Crisis**: When `regime` is `BEAR_HIGH_VOL`, `BEAR_LOW_VOL`, or `CRISIS`, `is_bull_regime` evaluates to `False`. Thus `turbo_mult = 1.0` unconditionally for all strategies:
     - Mean-reverting reversal strategies (`short_term_reversal`, `overnight_gap_reversal`, `dual_correction`, `stat_arb`) receive **zero boost**, despite being the highest-alpha sources during market sell-offs.
     - Momentum strategies receive **zero crash discount**, dragging down returns during freefalls.

### 1.3 Baseline Verification
Execution of 36 unit tests across `test_hpo_and_2d_ensemble.py`, `test_factor_momentum_and_available_normalization.py`, `test_adversarial_regime_sharpe_m2.py`, and `test_sector_and_ensemble_audit_fixes.py` plus 16 tests in `test_regime_ensemble.py` and `test_r1_ensemble_regime_fixes.py` yielded **52 / 52 tests PASSING (100%)** in Python 3.11.

---

## 2. Logic Chain

### Logic Chain Step 1: Market-Segregated State Caching for Live Alpha Decay
- *Premise*: `apply_exponential_decay_filter` requires $\tilde{s}_{i, k}(t-1)$ to perform convolutional decay. Without state caching, the filter cannot run across pipeline invocations or trading days.
- *Inference*:
  1. Add `self._prev_filtered_scores: Dict[str, pd.DataFrame] = {}` to `EnsembleScoringEngine.__init__`.
  2. Cache prior scores segregated by lowercase market key (`'sp500'`, `'nasdaq'`, `'russell2000'`, `'kospi'`, `'kosdaq'`, `'us'`, `'kr'`, and `'global'`).
  3. Only store `['symbol'] + strategy_score_cols` to minimize memory footprint.
  4. On cold start (`prev_scores is None`), `apply_exponential_decay_filter` immediately returns `current_scores.copy()` (lines 3377-3378), ensuring 100% test compatibility and zero cold-start distortion.

### Logic Chain Step 2: Hooking Decay Filtering into `combine_predictions`
- *Premise*: Score normalization (Phase 3-A) puts all active strategy scores onto the standardized $[0.0, 1.0]$ scale. If decay filtering runs after Phase 3-A:
  $$\tilde{s}_{i, k}(t) = \alpha_k s_{i, k}(t) + (1 - \alpha_k) \tilde{s}_{i, k}(t-1)$$
  Because $s_{i, k}(t) \in [0, 1]$ and $\tilde{s}_{i, k}(t-1) \in [0, 1]$ and $\alpha_k \in (0, 1)$, their convex combination strictly remains in $[0, 1]$.
- *Inference*: Hook decay filtering at **Phase 3-A.2** (immediately following `self.score_normalizer.normalize_scores`, before Phase 3-B correlation monitoring and Phase 3-C orthogonalization). This ensures downstream factor suppression and PCA-ZCA whitening operate on the denoised, time-stabilized factor signals.

### Logic Chain Step 3: Hooking Rank IC and Latency Decay Calibration
- *Premise*: Fast execution signals lose predictive power if stale, while slow valuation factors persist.
- *Inference*: Hook `apply_rank_ic_decay_calibration` at **Phase 3-B.2** in `combine_predictions`. When `strategy_rank_ic_dict` or `latency_days > 0` is supplied (via `kwargs` or `self.strategy_rank_ic_dict`), calibrate `eff_us_weights` and `eff_kr_weights`. If None, cleanly preserve uncalibrated base weights.

### Logic Chain Step 4: Trend Inertia vs Crash Protection in `compute_dynamic_weights_from_sharpe`
- *Premise*: Market regimes dictate distinct factor dynamics:
  1. **`BULL_LOW_VOL`**: Low volatility, persistent trend. Reward factor rank autocorrelation $\rho_k^{\text{autocorr}}$ with trend inertia boost:
     $$\text{turbo\_mult} = 1.40 + 0.20 \cdot \max(0, \rho_k^{\text{autocorr}}) \quad \in [1.40, 1.60]$$
     Dampen counter-trend reversal strategies to $0.50\times$.
  2. **`BULL_HIGH_VOL`**: High volatility bull. High probability of momentum crashes. Curtail momentum to $1.15\times$ to protect against sharp reversals, while elevating reversal strategies to $1.10\times$.
  3. **`BEAR_HIGH_VOL` & `CRISIS`**: Panic selling. Momentum strategies crash. Slash momentum to $0.50\times$. Boost reversal strategies via VIX stress:
     $$\text{turbo\_mult} = 1.40 \cdot (1.0 + 0.20 \cdot \text{vix\_stress}) \quad \in [1.40, 1.68]$$
     where $\text{vix\_stress} = \text{clip}((\text{VIX} - 20) / 20, 0, 1)$. Boost defensive strategies to $1.30\times$.
  4. **`BEAR_LOW_VOL`**: Grinding bear drift. Momentum = $0.70\times$, Reversal = $1.30\times$, Defensive = $1.20\times$.
  5. **`SIDEWAYS_HIGH_VOL`**: Range-bound chop. Reversal = $1.30\times$, Momentum = $0.85\times$.

---

## 3. Caveats & Edge Cases

1. **Cold Start Identity**:
   When no previous scores are cached (`self._prev_filtered_scores` empty), `apply_exponential_decay_filter` returns the current scores DataFrame unmodified. No synthetic initial values are invented.
2. **Universe Drift & IPOs**:
   When a stock appears today that was not in yesterday's universe, `reindex().fillna(curr_indexed[col])` sets $\tilde{s}(t-1) = s(t)$, yielding $\alpha s(t) + (1 - \alpha) s(t) = s(t)$. Clean identity fallback.
3. **Strict Bounds Guarantee**:
   All outputs from decay filtering are explicitly capped with `.clip(0.0, 1.0)` to eliminate floating-point arithmetic overflow.
4. **Dynamic Weight Normalization**:
   After applying `turbo_mult`, dynamic weights are clipped to the maximum ratio bound of $20.0$, enforced at $\ge 1\%$ floor per active strategy, and strictly normalized to sum to $1.0000$.

---

## 4. Conclusion & Concrete Code Specification for Worker

### 4.1 Exact Code Replacement Blocks for `trading_system/src/ai/ensemble_scorer.py`

#### [Block 1] Add State Caching & Helper Methods to `EnsembleScoringEngine`
**Location**: In `__init__` around line 558, and insert helper methods after line 650:

```python
# --- IN __init__ (after line 558) ---
        self.score_normalizer = CrossSectionalScoreNormalizer(method='winsorized_zscore')
        self._dsr_validator = DeflatedSharpeRatioValidator(n_strategies=34, n_horizons=8) if DeflatedSharpeRatioValidator is not None else None

        # Feature F04: Multi-horizon exponential decay filtering prior scores state cache per market
        self._prev_filtered_scores: Dict[str, pd.DataFrame] = {}
        self.enable_decay_filter: bool = getattr(config, 'enable_decay_filter', True) if config is not None else True
        self.strategy_rank_ic_dict: Optional[Dict[str, float]] = None
```

```python
# --- HELPER METHODS (add after line 650) ---
    def reset_decay_filter_state(self, market: Optional[str] = None) -> None:
        """Reset cached previous filtered scores for a given market or all markets."""
        if market is not None:
            self._prev_filtered_scores.pop(str(market).lower(), None)
        else:
            self._prev_filtered_scores.clear()

    def compute_factor_rank_autocorrelation(
        self,
        current_scores: pd.DataFrame,
        market: str = "global"
    ) -> Dict[str, float]:
        """
        Computes 1-day lag factor rank autocorrelation between current scores and cached previous scores:
        rho_k = SpearmanRankCorr(s_k(t), s_tilde_k(t-1))
        """
        mkt_key = str(market).lower()
        prev_scores = self._prev_filtered_scores.get(mkt_key)
        if prev_scores is None or prev_scores.empty or current_scores is None or current_scores.empty:
            return {}
        if 'symbol' not in current_scores.columns or 'symbol' not in prev_scores.columns:
            return {}

        curr_idx = current_scores.drop_duplicates(subset=['symbol']).set_index('symbol')
        prev_idx = prev_scores.drop_duplicates(subset=['symbol']).set_index('symbol')

        common_syms = curr_idx.index.intersection(prev_idx.index)
        if len(common_syms) < 5:
            return {}

        autocorr_map = {}
        score_col_to_strat = {
            'reg_score': 'regression', 'surge_score': 'surge', 'll_score': 'lead_lag',
            'vcp_rule_score': 'vcp_rule', 'vcp_ml_score': 'vcp_ml', 'lstm_score': 'lstm',
            'stat_arb_score': 'stat_arb', 'sector_score': 'sector_rotation', 'rim_score': 'rim_valuation',
            'event_score': 'event_driven', 'mq_score': 'mq_factor', 'iv_skew_score': 'iv_skew',
            'order_flow_score': 'order_flow', 'reversal_score': 'short_term_reversal', 'arm_score': 'arm_factor',
            'card_score': 'card_factor', 'latr_score': 'latr_factor', 'inst_foreign_sector_score': 'inst_foreign_sector',
            'supply_chain_score': 'supply_chain', 'sentiment_score': 'sentiment', 'factor_neutralized_score': 'factor_neutralized',
            'vol_target_score': 'vol_target', 'microstructure_score': 'microstructure', 'accruals_quality_score': 'accruals_quality',
            'short_squeeze_score': 'short_squeeze', 'valueup_catalyst_score': 'valueup_catalyst', 'trend_efficiency_score': 'trend_efficiency',
            'gamma_squeeze_score': 'gamma_squeeze', 'insider_buying_score': 'insider_buying', 'darkpool_score': 'darkpool',
            'earnings_tone_drift_score': 'earnings_tone_drift', 'cross_asset_spillover_score': 'cross_asset_spillover',
            'supply_chain_gnn_score': 'supply_chain_gnn', 'range_expansion_score': 'range_expansion_breakout',
            'dual_correction_score': 'dual_correction', 'index_rebalance_score': 'index_rebalance',
            'overnight_gap_score': 'overnight_gap_reversal'
        }

        for col, strat in score_col_to_strat.items():
            if col in curr_idx.columns and col in prev_idx.columns:
                s_curr = pd.to_numeric(curr_idx.loc[common_syms, col], errors='coerce')
                s_prev = pd.to_numeric(prev_idx.loc[common_syms, col], errors='coerce')
                valid = s_curr.notna() & s_prev.notna()
                if valid.sum() >= 5:
                    corr = s_curr[valid].corr(s_prev[valid], method='spearman')
                    if pd.notna(corr):
                        autocorr_map[strat] = float(np.clip(corr, -1.0, 1.0))

        return autocorr_map

    def _apply_decay_filtering_with_cache(
        self,
        merged: pd.DataFrame,
        strategy_cols: List[Tuple[str, str]],
        regime: Union[int, str] = 'BULL_LOW_VOL',
        us_regime: Optional[Union[int, str]] = None,
        kr_regime: Optional[Union[int, str]] = None,
        **kwargs: Any
    ) -> pd.DataFrame:
        """
        Executes market-segregated multi-horizon exponential decay filtering
        with prior score state caching in self._prev_filtered_scores.
        Provides clean fallback on cold start (None prior scores) and ensures
        all strategy scores are strictly clipped in [0.0, 1.0].
        """
        if merged.empty or 'symbol' not in merged.columns:
            return merged

        active_score_cols = [col for _, col in strategy_cols if col in merged.columns]
        if not active_score_cols:
            return merged

        df_out = merged.copy()
        has_market_col = 'market' in df_out.columns and df_out['market'].notna().any()

        if has_market_col:
            unique_markets = df_out['market'].dropna().unique()
            filtered_chunks = []
            for mkt in unique_markets:
                mkt_key = str(mkt).lower()
                mkt_mask = (df_out['market'] == mkt)
                sub_df = df_out.loc[mkt_mask].copy()

                is_us = mkt_key in ['sp500', 'nasdaq', 'russell2000', 'us']
                is_kr = mkt_key in ['kospi', 'kosdaq', 'kr']
                mkt_regime = us_regime if (is_us and us_regime) else (kr_regime if (is_kr and kr_regime) else regime)

                prev_scores = self._prev_filtered_scores.get(mkt_key)
                sub_filtered = self.apply_exponential_decay_filter(
                    current_scores=sub_df,
                    previous_scores=prev_scores,
                    regime=mkt_regime
                )

                for col in active_score_cols:
                    if col in sub_filtered.columns and pd.api.types.is_numeric_dtype(sub_filtered[col]):
                        sub_filtered[col] = sub_filtered[col].clip(0.0, 1.0)

                cache_cols = ['symbol'] + [c for c in active_score_cols if c in sub_filtered.columns]
                self._prev_filtered_scores[mkt_key] = sub_filtered[cache_cols].copy()
                filtered_chunks.append(sub_filtered)

            no_mkt_mask = df_out['market'].isna()
            if no_mkt_mask.any():
                filtered_chunks.append(df_out.loc[no_mkt_mask])

            df_out = pd.concat(filtered_chunks, axis=0).reindex(df_out.index)
        else:
            mkt_key = str(kwargs.get('market', 'global')).lower()
            prev_scores = self._prev_filtered_scores.get(mkt_key)

            df_out = self.apply_exponential_decay_filter(
                current_scores=df_out,
                previous_scores=prev_scores,
                regime=regime
            )
            for col in active_score_cols:
                if col in df_out.columns and pd.api.types.is_numeric_dtype(df_out[col]):
                    df_out[col] = df_out[col].clip(0.0, 1.0)

            cache_cols = ['symbol'] + [c for c in active_score_cols if c in df_out.columns]
            self._prev_filtered_scores[mkt_key] = df_out[cache_cols].copy()

        cache_cols_all = ['symbol'] + [c for c in active_score_cols if c in df_out.columns]
        self._prev_filtered_scores['global'] = df_out[cache_cols_all].copy()

        return df_out
```

---

#### [Block 2] Update `compute_dynamic_weights_from_sharpe` for Feature F05
**Location**: `ensemble_scorer.py:1002-1014` and `1112-1128`:

```python
# Signature (line 1002):
    def compute_dynamic_weights_from_sharpe(
        self,
        rolling_sharpes: Dict[str, float],
        regime: Union[int, str],
        gamma: float = 1.0,
        vix_val: Optional[float] = None,
        factor_ic_dict: Optional[Dict[str, float]] = None,
        factor_crowding_penalties: Optional[Dict[str, float]] = None,
        pruning_threshold: Optional[float] = -0.50,
        smooth_downside_mode: bool = False,
        market: str = "global",
        factor_autocorr_dict: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
```

```python
# Replace lines 1112-1128 with:
            # Regime-Adaptive Momentum Turbo & Trend Inertia vs Crash Protection (Feature F05):
            # In calm Bull regimes (BULL_LOW_VOL), reward factor rank autocorrelation and persist momentum alpha (1.4x ~ 1.6x).
            # In volatile Bull regimes (BULL_HIGH_VOL), scale back momentum to 1.15x to prevent crash risk (Barroso & Santa-Clara 2015).
            # In Bear & Crisis regimes, slash momentum to 0.50x and calibrate/boost reversal strategies to 1.40x ~ 1.68x.
            turbo_mult = 1.0
            regime_str = str(regime).upper()
            is_bull_low_vol = ('BULL_LOW_VOL' in regime_str) or (
                ('BULL' in regime_str or str(regime) == '2') and 'HIGH_VOL' not in regime_str
            )
            is_bull_high_vol = ('BULL_HIGH_VOL' in regime_str) or (
                ('BULL' in regime_str) and ('HIGH_VOL' in regime_str)
            )
            is_crisis_or_bear_high_vol = (
                'CRISIS' in regime_str or
                'BEAR_HIGH_VOL' in regime_str or
                ('BEAR' in regime_str and 'HIGH_VOL' in regime_str) or
                (vix_val is not None and float(vix_val) >= 30.0)
            )
            is_bear_low_vol = ('BEAR_LOW_VOL' in regime_str) or (
                ('BEAR' in regime_str or str(regime) == '0') and not is_crisis_or_bear_high_vol
            )
            is_sideways_high_vol = ('SIDEWAYS_HIGH_VOL' in regime_str)

            MOMENTUM_TURBO_STRATEGIES = {
                'surge', 'vcp_ml', 'mq_factor', 'order_flow', 'short_squeeze',
                'gamma_squeeze', 'trend_efficiency', 'supply_chain', 'event_driven',
                'range_expansion_breakout'
            }
            REVERSAL_STRATEGIES = {
                'short_term_reversal', 'overnight_gap_reversal', 'dual_correction', 'stat_arb'
            }
            DEFENSIVE_STRATEGIES = {
                'vol_target', 'factor_neutralized', 'rim_valuation', 'accruals_quality'
            }

            if is_bull_low_vol:
                if strategy in MOMENTUM_TURBO_STRATEGIES:
                    # Reward factor rank autocorrelation / persistence in calm bull
                    autocorr = float(np.clip(factor_autocorr_dict.get(strategy, 0.0), -1.0, 1.0)) if factor_autocorr_dict else 0.0
                    turbo_mult = 1.40 + 0.20 * max(0.0, autocorr)
                elif strategy in REVERSAL_STRATEGIES:
                    turbo_mult = 0.50
                elif strategy in DEFENSIVE_STRATEGIES:
                    turbo_mult = 0.70
            elif is_bull_high_vol:
                if strategy in MOMENTUM_TURBO_STRATEGIES:
                    # Crash protection: scale back momentum turbo to prevent crash risk
                    turbo_mult = 1.15
                elif strategy in REVERSAL_STRATEGIES:
                    turbo_mult = 1.10
                elif strategy in DEFENSIVE_STRATEGIES:
                    turbo_mult = 0.90
            elif is_crisis_or_bear_high_vol:
                if strategy in MOMENTUM_TURBO_STRATEGIES:
                    # Crash protection: curtail momentum in market crashes
                    turbo_mult = 0.50
                elif strategy in REVERSAL_STRATEGIES:
                    # Calibrate reversal strategies in crisis / bear regimes
                    vix_stress = float(np.clip(((float(vix_val) if vix_val is not None else 25.0) - 20.0) / 20.0, 0.0, 1.0))
                    turbo_mult = 1.40 * (1.0 + 0.20 * vix_stress)
                elif strategy in DEFENSIVE_STRATEGIES:
                    turbo_mult = 1.30
            elif is_bear_low_vol:
                if strategy in MOMENTUM_TURBO_STRATEGIES:
                    turbo_mult = 0.70
                elif strategy in REVERSAL_STRATEGIES:
                    turbo_mult = 1.30
                elif strategy in DEFENSIVE_STRATEGIES:
                    turbo_mult = 1.20
            elif is_sideways_high_vol:
                if strategy in MOMENTUM_TURBO_STRATEGIES:
                    turbo_mult = 0.85
                elif strategy in REVERSAL_STRATEGIES:
                    turbo_mult = 1.30
                elif strategy in DEFENSIVE_STRATEGIES:
                    turbo_mult = 1.10

            scores[strategy] = base_w * multiplier * ic_mult * dsr_mult * turbo_mult * (1.0 - crowd_penalty)
```

---

#### [Block 3] Hook Phase 3-A.2 & Phase 3-B.2 in `combine_predictions`
**Location**: `ensemble_scorer.py:2395` and `ensemble_scorer.py:2499`:

```python
# Hook 1: Decay Filtering at Phase 3-A.2 (after line 2395)
        # Phase 3-A.2: Multi-Horizon Exponential Convolutional Decay Filtering (Feature F04)
        if getattr(self, 'enable_decay_filter', True) and not merged.empty and 'symbol' in merged.columns:
            try:
                merged = self._apply_decay_filtering_with_cache(
                    merged=merged,
                    strategy_cols=strategy_cols,
                    regime=regime,
                    us_regime=us_regime,
                    kr_regime=kr_regime,
                    **kwargs
                )
            except Exception as _dfe:
                logger.warning(f"Decay filter application warning (clean fallback to unfiltered): {_dfe}")
```

```python
# Hook 2: Rank IC and Latency Decay Calibration at Phase 3-B.2 (after line 2499)
        # Phase 3-B.2: Apply Rank IC and Latency Decay Calibration to Strategy Weights (Feature F04)
        rank_ic_map = kwargs.get('strategy_rank_ic_dict') or kwargs.get('factor_ic_dict') or getattr(self, 'strategy_rank_ic_dict', None)
        latency_days = float(kwargs.get('latency_days', 0.0))
        gamma_rank_ic = float(kwargs.get('gamma_rank_ic', 1.0))
        if rank_ic_map or latency_days > 0.0:
            try:
                eff_us_weights = self.apply_rank_ic_decay_calibration(
                    base_weights=eff_us_weights,
                    strategy_rank_ic_dict=rank_ic_map,
                    latency_days=latency_days,
                    gamma=gamma_rank_ic,
                    regime=us_regime or regime
                )
                eff_kr_weights = self.apply_rank_ic_decay_calibration(
                    base_weights=eff_kr_weights,
                    strategy_rank_ic_dict=rank_ic_map,
                    latency_days=latency_days,
                    gamma=gamma_rank_ic,
                    regime=kr_regime or regime
                )
            except Exception as _ice:
                logger.warning(f"Rank IC decay calibration warning (fallback to uncalibrated): {_ice}")
```

---

#### [Block 4] Clean Defenses & Fixed LSTM Mapping in `apply_exponential_decay_filter`
**Location**: `ensemble_scorer.py:3388-3424`:

```python
        sym_col = 'symbol' if 'symbol' in df_filtered.columns else None
        if sym_col and sym_col in previous_scores.columns:
            prev_clean = previous_scores.drop_duplicates(subset=[sym_col])
            if prev_clean.columns.has_duplicates:
                prev_clean = prev_clean.loc[:, ~prev_clean.columns.duplicated(keep='first')]
            prev_indexed = prev_clean.set_index(sym_col)
            curr_indexed = df_filtered.set_index(sym_col)

            score_col_to_strat = {
                'reg_score': 'regression', 'surge_score': 'surge', 'll_score': 'lead_lag',
                'vcp_rule_score': 'vcp_pattern', 'vcp_ml_score': 'vcp_ml', 'lstm_score': 'lstm',
                'stat_arb_score': 'stat_arb', 'sector_score': 'sector_rotation', 'rim_score': 'rim_valuation',
                'event_score': 'event_driven', 'mq_score': 'mq_factor', 'iv_skew_score': 'iv_skew',
                'order_flow_score': 'order_flow', 'reversal_score': 'short_term_reversal', 'arm_score': 'arm_factor',
                'card_score': 'card_factor', 'latr_score': 'latr_factor', 'inst_foreign_sector_score': 'inst_foreign_sector',
                'supply_chain_score': 'supply_chain', 'sentiment_score': 'sentiment', 'factor_neutralized_score': 'factor_neutralized',
                'vol_target_score': 'vol_target', 'microstructure_score': 'microstructure', 'accruals_quality_score': 'accruals_quality',
                'short_squeeze_score': 'short_squeeze', 'valueup_catalyst_score': 'value_up', 'trend_efficiency_score': 'trend_efficiency',
                'gamma_squeeze_score': 'gamma_squeeze', 'insider_buying_score': 'insider_buying', 'darkpool_score': 'darkpool_hft',
                'earnings_tone_drift_score': 'tone_drift',
                'cross_asset_spillover_score': 'cross_asset_spillover', 'cross_asset_score': 'cross_asset_spillover',
                'supply_chain_gnn_score': 'supply_chain_gnn',
                'range_expansion_score': 'range_expansion_breakout', 'range_expansion_breakout_score': 'range_expansion_breakout',
                'breakout_score': 'range_expansion_breakout',
                'dual_correction_score': 'dual_correction',
                'index_rebalance_score': 'index_rebalance',
                'overnight_gap_score': 'overnight_gap_reversal',
                'overnight_gap_reversal_score': 'overnight_gap_reversal',
            }

            for col in curr_indexed.columns:
                strat_key = score_col_to_strat.get(col, col)
                if strat_key in half_lives and col in prev_indexed.columns and pd.api.types.is_numeric_dtype(curr_indexed[col]):
                    tau = half_lives.get(strat_key, 10.0)
                    alpha = 1.0 - float(np.exp(-np.log(2.0) / max(tau, 0.1)))
                    prev_s = prev_indexed[col].reindex(curr_indexed.index).fillna(curr_indexed[col])
                    curr_indexed[col] = (alpha * curr_indexed[col] + (1.0 - alpha) * prev_s).clip(0.0, 1.0)

            df_filtered = curr_indexed.reset_index()
        return df_filtered
```

---

## 5. Verification Method

### 5.1 Concrete Unit Test Suite for the Worker (`tests/test_m1_quant_enhancements.py`)

The Worker must create `tests/test_m1_quant_enhancements.py` with these unit tests:

```python
import pytest
import numpy as np
import pandas as pd
from src.ai.ensemble_scorer import EnsembleScoringEngine

class TestMilestone1FeaturesF04F05:
    def test_f04_exponential_decay_cold_start_identity(self):
        """F04: Cold start without cached prior scores returns identical scores."""
        engine = EnsembleScoringEngine()
        engine.reset_decay_filter_state()
        
        symbols = ['AAPL', 'MSFT', 'NVDA']
        reg_df = pd.DataFrame({'symbol': symbols, 'expected_return': [0.10, 0.20, 0.15]})
        surge_df = pd.DataFrame({'symbol': symbols, 'surge_probability': [0.70, 0.80, 0.60]})
        
        res = engine.combine_predictions(reg_df=reg_df, s_df=surge_df, regime='BULL_LOW_VOL')
        assert 'ensemble_score' in res.columns
        assert len(res) == 3
        # State must be cached after first execution
        assert 'global' in engine._prev_filtered_scores
        assert not engine._prev_filtered_scores['global'].empty

    def test_f04_exponential_decay_warm_start_smoothing_and_clipping(self):
        """F04: Consecutive runs apply convolutional exponential smoothing and clip [0, 1]."""
        engine = EnsembleScoringEngine()
        engine.reset_decay_filter_state()
        
        symbols = ['AAPL']
        # Day 1: High valuation score (0.90) and high microstructure score (0.90)
        rim_df1 = pd.DataFrame({'symbol': symbols, 'rim_score': [0.90]})
        micro_df1 = pd.DataFrame({'symbol': symbols, 'microstructure_score': [0.90]})
        res1 = engine.combine_predictions(rim_df=rim_df1, microstructure_df=micro_df1, regime='BULL_LOW_VOL')
        
        # Day 2: Sudden drop to 0.50 for both
        rim_df2 = pd.DataFrame({'symbol': symbols, 'rim_score': [0.50]})
        micro_df2 = pd.DataFrame({'symbol': symbols, 'microstructure_score': [0.50]})
        res2 = engine.combine_predictions(rim_df=rim_df2, microstructure_df=micro_df2, regime='BULL_LOW_VOL')
        
        # Slow factor (tau=45 in normal, 58.5 in Bull) should persist high (> 0.85)
        # Fast factor (tau=0.5 in normal, 0.65 in Bull) should adjust quickly (< 0.65)
        assert res2['rim_score'].iloc[0] > 0.85
        assert res2['microstructure_score'].iloc[0] < 0.65
        assert 0.0 <= res2['rim_score'].iloc[0] <= 1.0
        assert 0.0 <= res2['microstructure_score'].iloc[0] <= 1.0

    def test_f04_rank_ic_decay_calibration_in_combine_predictions(self):
        """F04: Rank IC decay calibration updates effective weights and favors high-IC factor."""
        engine = EnsembleScoringEngine()
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
        reg_df = pd.DataFrame({'symbol': symbols, 'expected_return': [0.10, 0.12, 0.08, 0.15, 0.05]})
        surge_df = pd.DataFrame({'symbol': symbols, 'surge_probability': [0.80, 0.85, 0.70, 0.90, 0.60]})
        
        # Test without IC calibration
        res_base = engine.combine_predictions(reg_df=reg_df, s_df=surge_df, regime='BULL_LOW_VOL')
        
        # Test with high positive Rank IC on surge (+0.20) and negative on regression (-0.15)
        rank_ics = {'surge': 0.20, 'regression': -0.15}
        res_cal = engine.combine_predictions(
            reg_df=reg_df, s_df=surge_df, regime='BULL_LOW_VOL',
            strategy_rank_ic_dict=rank_ics, latency_days=1.0
        )
        # Top surge asset AAPL should have higher score under surge-favoring calibration
        assert res_cal['ensemble_score'].max() >= res_base['ensemble_score'].max()

    def test_f05_bull_low_vol_momentum_inertia_boost(self):
        """F05: BULL_LOW_VOL rewards positive factor rank autocorrelation."""
        engine = EnsembleScoringEngine()
        sharpes = {'surge': 1.0, 'vcp_ml': 1.0, 'regression': 0.5}
        
        w_base = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
        # Feed high positive autocorrelation (0.80)
        w_autocorr = engine.compute_dynamic_weights_from_sharpe(
            sharpes, regime='BULL_LOW_VOL',
            factor_autocorr_dict={'surge': 0.80, 'vcp_ml': 0.80}
        )
        assert w_autocorr['surge'] > w_base['surge']
        assert w_autocorr['vcp_ml'] > w_base['vcp_ml']
        assert pytest.approx(sum(w_autocorr.values()), abs=1e-5) == 1.0

    def test_f05_bull_high_vol_crash_protection(self):
        """F05: BULL_HIGH_VOL scales back momentum multiplier to prevent crash risk."""
        engine = EnsembleScoringEngine()
        sharpes = {'surge': 1.5, 'regression': 0.5}
        
        w_low = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_LOW_VOL')
        w_high = engine.compute_dynamic_weights_from_sharpe(sharpes, regime='BULL_HIGH_VOL')
        
        base_low = engine.get_base_weights('BULL_LOW_VOL')
        base_high = engine.get_base_weights('BULL_HIGH_VOL')
        
        # Relative boost (dynamic / base) for surge must be larger in low vol than in high vol
        boost_low = w_low['surge'] / base_low['surge']
        boost_high = w_high['surge'] / base_high['surge']
        assert boost_low > boost_high

    def test_f05_crisis_and_bear_reversal_calibration(self):
        """F05: CRISIS and BEAR_HIGH_VOL boost reversal strategies and slash momentum."""
        engine = EnsembleScoringEngine()
        sharpes = {'short_term_reversal': 0.5, 'surge': 0.5, 'regression': 0.5}
        
        w_crisis = engine.compute_dynamic_weights_from_sharpe(
            sharpes, regime='CRISIS', vix_val=35.0
        )
        base_crisis = engine.get_base_weights('CRISIS')
        
        # Reversal must be boosted relative to base
        assert w_crisis['short_term_reversal'] / base_crisis['short_term_reversal'] > 1.10
        # Momentum must be discounted relative to base
        assert w_crisis['surge'] / base_crisis['surge'] < 0.90
        assert pytest.approx(sum(w_crisis.values()), abs=1e-5) == 1.0
```

### 5.2 Verification Commands to Execute
```bash
# Run Milestone 1 dedicated tests
.venv\Scripts\pytest.exe tests/test_m1_quant_enhancements.py -v

# Run existing baseline tests to verify zero regressions
.venv\Scripts\pytest.exe tests/test_hpo_and_2d_ensemble.py tests/test_factor_momentum_and_available_normalization.py tests/test_adversarial_regime_sharpe_m2.py tests/test_sector_and_ensemble_audit_fixes.py tests/test_regime_ensemble.py tests/test_r1_ensemble_regime_fixes.py -v
```

### 5.3 Invalidation Conditions
1. If running `combine_predictions` on a cold start without previous scores produces different scores than baseline, or raises `AttributeError` / `KeyError`.
2. If `apply_exponential_decay_filter` yields any score $< 0.0$ or $> 1.0$, or generates `NaN` when input is valid.
3. If `compute_dynamic_weights_from_sharpe` in any regime outputs a weight dictionary whose sum deviates from $1.0000$ by more than $10^{-5}$.
4. If in `BULL_HIGH_VOL`, momentum strategies receive a multiplier equal to or higher than `BULL_LOW_VOL` (violating crash protection).
5. If in `CRISIS` or `BEAR_HIGH_VOL`, reversal strategies are not boosted relative to base weights.
