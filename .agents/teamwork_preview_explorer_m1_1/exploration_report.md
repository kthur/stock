# Deep Quantitative Architectural Exploration & Implementation Strategy Report
## Feature F47: 5-Pillar Economically-Weighted Trilinear Tensors, Pillar Harmony & Convexity (Milestone 1, Phase 7 Zenith v14)

**Document**: `exploration_report.md`  
**Author**: M1 Explorer 1 (Tensor Synergy & Convexity)  
**Target Module**: `trading_system/src/ai/ensemble_scorer.py` (`compute_quint_pillar_tensor_synergy`, `combine_predictions`)  
**Project Root**: `d:\Finance\code\stock`  
**Date**: 2026-09-05  

---

## 1. Executive Summary & Problem Boundary

### 1.1 Objective
This investigation delivers a forensic code-level analysis, exact mathematical formulations, and a turnkey implementation blueprint for **Feature F47** in **Milestone 1 (Dynamic Alpha Signal Synergy & Right-Tail Confidence 7th Deepening)** of the **Phase 7 Zenith Quantitative Enhancements (v14)**:
1. **Trilinear Contraction Economic Weighting ($\Omega_{\text{tri}}$)**:
   - Transition from Phase 6 uniform scalar triplet weighting ($w_{\text{tri}} \sum \psi_i \psi_j \psi_k$) to economically motivated triplet contractions.
   - High-conviction structural factor sweet-spot `('val', 'mom', 'flow')` boosted by **1.40x** ($1.40 \cdot w_{\text{tri}}(R)$).
   - High-conviction tactical/network factor sweet-spot `('flow', 'cat', 'net')` boosted by **1.20x** ($1.20 \cdot w_{\text{tri}}(R)$).
   - Remaining 8 triplets preserved at $1.00 \cdot w_{\text{tri}}(R)$.
2. **Pillar Harmony Regularizer ($\mathcal{H}_{\text{pillar}}$)**:
   - Quantifies conviction dispersion across the 5 orthogonal pillars using the coefficient of variation $\text{CV}_\psi = \frac{\sigma_\psi}{\mu_\psi + 10^{-4}}$.
   - Regularizer formula: $\mathcal{H}_{\text{pillar}} = \exp\left(-1.20 \cdot (\text{clip}(\text{CV}_\psi, 0.0, 2.0))^2\right) \in (0, 1]$.
   - Amplifies confluence when multiple pillars exhibit mutually confirming strength ($\mu_\psi > 0.40$):
     $$\text{harmony\_factor} = 1.0 + 0.25 \cdot \mathcal{H}_{\text{pillar}} \cdot \mathbf{1}_{\{\mu_\psi > 0.40\}}$$
3. **Regime Cap Expansion & Safety Boundary**:
   - `BULL_LOW_VOL`: synergy cap expands from **0.180** to **0.220** ($1.220\times$ multiplier), expanding the Top-Decile alpha spread by $+18\%\sim+22\%$.
   - `CRISIS`: synergy cap is strictly maintained at **0.040** ($1.040\times$ multiplier), with $w_{\text{tri}} = 0.000$ guaranteeing zero trilinear leakage during macro panic.
   - Strict hierarchical ordering: $\text{5-Pillar} > \text{4-Pillar} > \text{3-Pillar} > \text{2-Pillar} > \text{1-Pillar} == \text{Baseline } (1.0000\times)$.
4. **Strict Backward Compatibility (Zero-Regression Invariant)**:
   - For `version <= 6`, exact Phase 6 behavior (cap 0.180 in Bull Low Vol, uniform $w_{\text{tri}}$ triplets, unity harmony factor) is 100% bit-exact preserved, guaranteeing zero regressions across all 2,536+ repository tests.

---

## 2. Mathematical Architecture of Feature F47

### 2.1 Disjoint 5-Pillar Canonical Mapping
The 37 canonical strategies are partitioned into 5 disjoint orthogonal pillars ($\bigcup_{p=1}^5 \mathcal{S}_p = 37$, $\mathcal{S}_i \cap \mathcal{S}_j = \emptyset$ for $i \ne j$):
- **`val` (Val_Qual, 6 strategies)**: `rim_score`, `valueup_catalyst_score`, `accruals_quality_score`, `arm_score`, `factor_neutralized_score`, `reg_score`.
- **`mom` (Mom_Trend, 9 strategies)**: `surge_score`, `vcp_ml_score`, `trend_efficiency_score`, `sector_score`, `range_expansion_score`, `mq_score`, `ll_score`, `vcp_rule_score`, `lstm_score`.
- **`flow` (Micro_Flow, 9 strategies)**: `order_flow_score`, `inst_foreign_sector_score`, `darkpool_score`, `microstructure_score`, `overnight_gap_score`, `stat_arb_score`, `iv_skew_score`, `reversal_score`, `vol_target_score`.
- **`cat` (Corp_Cat, 6 strategies)**: `event_score`, `sentiment_score`, `short_squeeze_score`, `gamma_squeeze_score`, `insider_buying_score`, `earnings_tone_drift_score`.
- **`net` (Network_Macro, 7 strategies)**: `supply_chain_score`, `supply_chain_gnn_score`, `cross_asset_spillover_score`, `dual_correction_score`, `index_rebalance_score`, `card_score`, `latr_score`.

### 2.2 Pillar Conviction Softplus Activation
For each pillar $p \in \{\text{val}, \text{mom}, \text{flow}, \text{cat}, \text{net}\}$, scores are aggregated using convex combination of max and mean:
$$\bar{s}_p = \left(0.70 \cdot \max_{j \in \mathcal{S}_p}(s_j) + 0.30 \cdot \frac{1}{|\mathcal{S}_p|}\sum_{j \in \mathcal{S}_p} s_j\right) \in [0, 1]$$
Normalized excess conviction above neutral baseline ($0.50$):
$$\psi_p = \begin{cases} \text{clip}\left(\frac{\ln(1 + \exp(\kappa(\bar{s}_p - 0.50))) - \ln(2)}{\ln(1 + \exp(0.50\kappa)) - \ln(2)}, 0.0, 1.0\right) & \text{if } \bar{s}_p > 0.50 \\ 0.0 & \text{otherwise} \end{cases}$$
where $\kappa = 8.0$.

### 2.3 Multi-Linear Contraction Tensors
Contraction terms:
1. **2nd-Order Bilinear (10 pairs)**:
   $$\Xi_{(2)} = \sum_{1 \le i < j \le 5} \omega_{(p_i, p_j)}(R) \cdot (\psi_{p_i} \cdot \psi_{p_j})$$
2. **3rd-Order Trilinear (10 triplets)**:
   $$\Xi_{(3)} = \sum_{1 \le i < j < k \le 5} \Omega_{(p_i, p_j, p_k)}(R) \cdot (\psi_{p_i} \cdot \psi_{p_j} \cdot \psi_{p_k})$$
   where:
   $$\Omega_{(p_i, p_j, p_k)}(R) = \begin{cases} 1.40 \cdot w_{\text{tri}}(R) & \text{if } \{p_i, p_j, p_k\} = \{\text{val}, \text{mom}, \text{flow}\} \\ 1.20 \cdot w_{\text{tri}}(R) & \text{if } \{p_i, p_j, p_k\} = \{\text{flow}, \text{cat}, \text{net}\} \\ 1.00 \cdot w_{\text{tri}}(R) & \text{otherwise (8 remaining triplets)} \end{cases}$$
3. **4th-Order Quadruplets (5 quads)**:
   $$\Xi_{(4)} = w_{\text{quad}}(R) \sum_{1 \le i < j < k < l \le 5} (\psi_{p_i} \cdot \psi_{p_j} \cdot \psi_{p_k} \cdot \psi_{p_l})$$
4. **5th-Order Quintuplet (1 hyper-contraction)**:
   $$\Xi_{(5)} = w_{\text{quint}}(R) \cdot (\psi_1 \cdot \psi_2 \cdot \psi_3 \cdot \psi_4 \cdot \psi_5)$$

Raw confluence:
$$\Xi_{\text{raw}} = \Xi_{(2)} + \Xi_{(3)} + \Xi_{(4)} + \Xi_{(5)}$$

### 2.4 Pillar Harmony Regularizer ($\mathcal{H}_{\text{pillar}}$)
Given cross-sectional pillar convictions $\boldsymbol{\psi} = (\psi_1, \dots, \psi_5)^T$:
- Mean: $\mu_\psi = \frac{1}{5}\sum_{p=1}^5 \psi_p$
- Standard deviation: $\sigma_\psi = \sqrt{\frac{1}{5}\sum_{p=1}^5 (\psi_p - \mu_\psi)^2}$
- Coefficient of variation: $\text{CV}_\psi = \frac{\sigma_\psi}{\mu_\psi + 10^{-4}}$
- Harmony Regularizer:
  $$\mathcal{H}_{\text{pillar}} = \exp\left(-1.20 \cdot (\text{clip}(\text{CV}_\psi, 0.0, 2.0))^2\right)$$
- Harmony Factor:
  $$\text{harmony\_factor} = 1.0 + 0.25 \cdot \mathcal{H}_{\text{pillar}} \cdot \mathbf{1}_{\{\mu_\psi > 0.40\}}$$
- Total Confluence:
  $$\Xi_{\text{total}} = \Xi_{\text{raw}} \cdot \text{harmony\_factor}$$

### 2.5 Final Synergy Multiplier & Regime Capping
$$M_{\text{synergy}} = 1.0 + \text{clip}\left(\Xi_{\text{total}}, 0.0, C_{\text{regime}}(R)\right)$$
Regime cap $C_{\text{regime}}(R)$ table:
| Regime | Phase 6 Cap ($v \le 6$) | Phase 7 Cap ($v \ge 7$) | Multiplier Max ($v \ge 7$) |
| :--- | :---: | :---: | :---: |
| **`BULL_LOW_VOL`** | **0.180** | **0.220** | **1.2200x** |
| `BULL_HIGH_VOL` | 0.145 | 0.145 | 1.1450x |
| `SIDEWAYS_LOW_VOL` | 0.115 | 0.115 | 1.1150x |
| `SIDEWAYS_HIGH_VOL` | 0.070 | 0.070 | 1.0700x |
| `BEAR_HIGH_VOL` | 0.045 | 0.045 | 1.0450x |
| `BEAR_LOW_VOL` | 0.085 | 0.085 | 1.0850x |
| **`CRISIS`** | **0.040** | **0.040** | **1.0400x** |
| `BULL` (fallback) | 0.160 | 0.160 | 1.1600x |
| Others (fallback) | 0.100 | 0.100 | 1.1000x |

---

## 3. Forensic Code Investigation & Architectural Trade-off

### 3.1 Existing Callers & Hardcoded Test Assertions
Our investigation detected that the existing test suite contains hardcoded cap assertions that were written specifically for Phase 6 ($v \le 6$):
1. `tests/test_phase6_signal_enhancement.py:116-117`:
   ```python
   mult_bull = engine.compute_quint_pillar_tensor_synergy(scores_df=df, regime='BULL_LOW_VOL', kappa=8.0, regime_adaptive_cap=True)
   assert mult_bull.loc['ASSET_0'] <= 1.18001
   ```
2. `tests/test_phase6_m1_challenger1_adversarial.py:378`:
   ```python
   mult = engine.compute_quint_pillar_tensor_synergy(scores_df=df, regime=reg, regime_adaptive_cap=True)
   assert mult.loc['ASSET_0'] <= expected_cap  # expected_cap['BULL_LOW_VOL'] = 1.18001
   ```
3. `tests/test_phase6_m1_challenger2_adversarial.py:271`:
   ```python
   mult_bull = engine.compute_quint_pillar_tensor_synergy(df_super, regime='BULL_LOW_VOL', regime_adaptive_cap=True)
   assert mult_bull.iloc[0] <= 1.180001
   ```

**Key Finding**:
None of these 3 legacy test files pass the `version` parameter because when they were written in Phase 6, `compute_quint_pillar_tensor_synergy` did not accept `version`.
If `compute_quint_pillar_tensor_synergy` had `version: int = 7` as its default value, all three existing test suites would immediately fail because `mult_bull.loc['ASSET_0']` produces `1.22000`, exceeding the hardcoded `1.18001` assertion!

### 3.2 Resolution & Design Options
We evaluate two implementation patterns:

| Aspect | Design Option A (Recommended) | Design Option B |
| :--- | :--- | :--- |
| **Signature** | `compute_quint_pillar_tensor_synergy(..., version: int = 6, **kwargs)` | `compute_quint_pillar_tensor_synergy(..., version: int = 7, **kwargs)` |
| **Legacy Tests** | **100% PASS** without modifying a single line of existing tests. | Fails 3 test suites unless legacy tests are modified to pass `version=6`. |
| **Pipeline Integration** | `combine_predictions` passes `version=version` (e.g. `version=7`), smoothly activating Phase 7. | `combine_predictions` passes `version=version` or relies on default. |
| **Zero-Regression Risk** | **0% Risk** (Full binary backward compatibility). | Non-zero risk of modifying historical test suites. |

**Recommended Architecture**:
Implement **Design Option A** with `version: int = 6` default (or `kwargs.get('version', version)`), while `combine_predictions` explicitly passes `version=version` at line 3266. Phase 7 tests in `tests/test_phase7_signal_enhancement.py` explicitly pass `version=7`.

---

## 4. Exact Implementation Blueprint

### 4.1 Target File: `trading_system/src/ai/ensemble_scorer.py`

#### Modification 1: `compute_quint_pillar_tensor_synergy` Signature & Cap Update
**Location**: Lines 4457–4684

```python
    @classmethod
    def compute_quint_pillar_tensor_synergy(
        cls,
        scores_df: pd.DataFrame,
        regime: Union[int, str] = 'SIDEWAYS_LOW_VOL',
        kappa: float = 8.0,
        regime_adaptive_cap: bool = True,
        max_cap: Optional[float] = None,
        version: int = 6,
        **kwargs
    ) -> pd.Series:
        """
        Phase 6 (F41.1) & Phase 7 Zenith (F47.1): Quint-Pillar Economic Decomposition & 
        High-Order Multi-Linear Tensor Synergy.
        Partitions all 37 strategies into 5 disjoint canonical pillars without omission or overlap:
        1. Val_Qual (6):      {rim_score, valueup_catalyst_score, accruals_quality_score, arm_score, factor_neutralized_score, reg_score}
        2. Mom_Trend (9):     {surge_score, vcp_ml_score, trend_efficiency_score, sector_score, range_expansion_score, mq_score, ll_score, vcp_rule_score, lstm_score}
        3. Micro_Flow (9):    {order_flow_score, inst_foreign_sector_score, darkpool_score, microstructure_score, overnight_gap_score, stat_arb_score, iv_skew_score, reversal_score, vol_target_score}
        4. Corp_Cat (6):      {event_score, sentiment_score, short_squeeze_score, gamma_squeeze_score, insider_buying_score, earnings_tone_drift_score}
        5. Network_Macro (7): {supply_chain_score, supply_chain_gnn_score, cross_asset_spillover_score, dual_correction_score, index_rebalance_score, card_score, latr_score}

        Computes 2nd-order (10 pairs), 3rd-order (10 triplets), 4th-order (5 quads), and 5th-order (1 quint) contractions.
        - For version >= 7:
            * Economically-weighted triplets: ('val', 'mom', 'flow') boosted by 1.40x, ('flow', 'cat', 'net') boosted by 1.20x.
            * Pillar Harmony Regularizer: H_pillar = exp(-1.20 * CV_psi^2), boosting harmonious 5-pillar conviction by up to 1.25x.
            * Bull Low Vol regime cap expands to 0.220 (1.220x multiplier).
            * Crisis cap strictly preserved <= 0.040.
            * Strict hierarchy 5 > 4 > 3 > 2 > 1 > Baseline strictly maintained.
        - For version <= 6:
            * Exact Phase 6 baseline (cap 0.180 in Bull Low Vol, uniform w_tri triplets, unity harmony factor).
        """
        version = int(kwargs.get('version', version))

        if scores_df is None or scores_df.empty:
            return pd.Series(1.0, index=scores_df.index if scores_df is not None else [0])

        n_rows = len(scores_df)
        if n_rows < 5:
            return pd.Series(1.0, index=scores_df.index)

        clusters = {
            'val': [
                'rim_score', 'valueup_catalyst_score', 'accruals_quality_score', 'arm_score',
                'factor_neutralized_score', 'reg_score'
            ],
            'mom': [
                'surge_score', 'vcp_ml_score', 'trend_efficiency_score', 'sector_score',
                'range_expansion_score', 'mq_score', 'll_score', 'vcp_rule_score',
                'lstm_score'
            ],
            'flow': [
                'order_flow_score', 'inst_foreign_sector_score', 'darkpool_score',
                'microstructure_score', 'overnight_gap_score', 'stat_arb_score',
                'iv_skew_score', 'reversal_score', 'vol_target_score'
            ],
            'cat': [
                'event_score', 'sentiment_score', 'short_squeeze_score', 'gamma_squeeze_score',
                'insider_buying_score', 'earnings_tone_drift_score'
            ],
            'net': [
                'supply_chain_score', 'supply_chain_gnn_score', 'cross_asset_spillover_score',
                'dual_correction_score', 'index_rebalance_score', 'card_score', 'latr_score'
            ]
        }

        # Pillar Convictions
        denom = float(np.log(1.0 + np.exp(kappa * 0.50)) - np.log(2.0))
        denom = max(1e-4, denom)
        pillar_convictions = {}

        for pillar_name, cols in clusters.items():
            valid_cols = [c for c in cols if c in scores_df.columns]
            if not valid_cols:
                pillar_convictions[pillar_name] = pd.Series(0.0, index=scores_df.index)
                continue

            sub = scores_df[valid_cols].apply(pd.to_numeric, errors='coerce')
            sub_max = sub.max(axis=1).fillna(0.50)
            sub_mean = sub.mean(axis=1).fillna(0.50)
            agg_s = (0.70 * sub_max + 0.30 * sub_mean).clip(0.0, 1.0)

            excess_arg = kappa * (agg_s - 0.50)
            raw_softplus = np.log1p(np.exp(np.clip(excess_arg, -20.0, 20.0))) - np.log(2.0)
            psi = np.where(agg_s > 0.50, raw_softplus / denom, 0.0)
            pillar_convictions[pillar_name] = pd.Series(np.clip(psi, 0.0, 1.0), index=scores_df.index)

        reg_str = str(regime).upper()
        if 'BULL_LOW_VOL' in reg_str:
            omega_pairs = {
                ('val', 'mom'): 0.025, ('val', 'flow'): 0.020, ('val', 'cat'): 0.015, ('val', 'net'): 0.015,
                ('mom', 'flow'): 0.035, ('mom', 'cat'): 0.040, ('mom', 'net'): 0.030,
                ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020,
                ('cat', 'net'): 0.025
            }
            w_tri = 0.025
            w_quad = 0.035
            w_quint = 0.060
            reg_cap = 0.220 if version >= 7 else 0.180
        elif 'BULL_HIGH_VOL' in reg_str:
            omega_pairs = {
                ('val', 'mom'): 0.020, ('val', 'flow'): 0.025, ('val', 'cat'): 0.015, ('val', 'net'): 0.015,
                ('mom', 'flow'): 0.040, ('mom', 'cat'): 0.025, ('mom', 'net'): 0.025,
                ('flow', 'cat'): 0.030, ('flow', 'net'): 0.020,
                ('cat', 'net'): 0.020
            }
            w_tri = 0.020
            w_quad = 0.025
            w_quint = 0.045
            reg_cap = 0.145
        elif 'SIDEWAYS_LOW_VOL' in reg_str:
            omega_pairs = {
                ('val', 'mom'): 0.020, ('val', 'flow'): 0.035, ('val', 'cat'): 0.025, ('val', 'net'): 0.020,
                ('mom', 'flow'): 0.015, ('mom', 'cat'): 0.015, ('mom', 'net'): 0.015,
                ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020,
                ('cat', 'net'): 0.020
            }
            w_tri = 0.015
            w_quad = 0.015
            w_quint = 0.030
            reg_cap = 0.115
        elif 'SIDEWAYS_HIGH_VOL' in reg_str:
            omega_pairs = {
                ('val', 'mom'): 0.015, ('val', 'flow'): 0.040, ('val', 'cat'): 0.025, ('val', 'net'): 0.020,
                ('mom', 'flow'): 0.008, ('mom', 'cat'): 0.008, ('mom', 'net'): 0.008,
                ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020,
                ('cat', 'net'): 0.015
            }
            w_tri = 0.008
            w_quad = 0.005
            w_quint = 0.015
            reg_cap = 0.070
        elif 'BEAR_HIGH_VOL' in reg_str:
            omega_pairs = {
                ('val', 'mom'): 0.010, ('val', 'flow'): 0.045, ('val', 'cat'): 0.030, ('val', 'net'): 0.020,
                ('mom', 'flow'): 0.005, ('mom', 'cat'): 0.005, ('mom', 'net'): 0.005,
                ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020,
                ('cat', 'net'): 0.010
            }
            w_tri = 0.002
            w_quad = 0.000
            w_quint = 0.000
            reg_cap = 0.045
        elif 'BEAR_LOW_VOL' in reg_str or 'BEAR' in reg_str:
            omega_pairs = {
                ('val', 'mom'): 0.018, ('val', 'flow'): 0.035, ('val', 'cat'): 0.030, ('val', 'net'): 0.020,
                ('mom', 'flow'): 0.010, ('mom', 'cat'): 0.010, ('mom', 'net'): 0.010,
                ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020,
                ('cat', 'net'): 0.015
            }
            w_tri = 0.010
            w_quad = 0.008
            w_quint = 0.020
            reg_cap = 0.085
        elif 'CRISIS' in reg_str:
            omega_pairs = {
                ('val', 'mom'): 0.010, ('val', 'flow'): 0.040, ('val', 'cat'): 0.020, ('val', 'net'): 0.015,
                ('mom', 'flow'): 0.005, ('mom', 'cat'): 0.005, ('mom', 'net'): 0.005,
                ('flow', 'cat'): 0.020, ('flow', 'net'): 0.015,
                ('cat', 'net'): 0.010
            }
            w_tri = 0.000
            w_quad = 0.000
            w_quint = 0.000
            reg_cap = 0.040
        elif 'BULL' in reg_str:
            omega_pairs = {
                ('val', 'mom'): 0.025, ('val', 'flow'): 0.020, ('val', 'cat'): 0.015, ('val', 'net'): 0.015,
                ('mom', 'flow'): 0.035, ('mom', 'cat'): 0.035, ('mom', 'net'): 0.025,
                ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020,
                ('cat', 'net'): 0.025
            }
            w_tri = 0.022
            w_quad = 0.030
            w_quint = 0.050
            reg_cap = 0.160
        else:
            omega_pairs = {
                ('val', 'mom'): 0.022, ('val', 'flow'): 0.030, ('val', 'cat'): 0.025, ('val', 'net'): 0.020,
                ('mom', 'flow'): 0.015, ('mom', 'cat'): 0.015, ('mom', 'net'): 0.015,
                ('flow', 'cat'): 0.025, ('flow', 'net'): 0.020,
                ('cat', 'net'): 0.020
            }
            w_tri = 0.012
            w_quad = 0.012
            w_quint = 0.025
            reg_cap = 0.100

        # 1. 2nd-order Bilinear pairs (10 terms)
        p_val = pillar_convictions['val']
        p_mom = pillar_convictions['mom']
        p_flow = pillar_convictions['flow']
        p_cat = pillar_convictions['cat']
        p_net = pillar_convictions['net']

        synergy_sum = pd.Series(0.0, index=scores_df.index)
        for (p1, p2), w_omega in omega_pairs.items():
            synergy_sum += w_omega * (pillar_convictions[p1] * pillar_convictions[p2])

        # 2. 3rd-order Trilinear triplets (10 terms)
        named_triplets = [
            (('val', 'mom', 'flow'), (p_val, p_mom, p_flow)),
            (('val', 'mom', 'cat'), (p_val, p_mom, p_cat)),
            (('val', 'mom', 'net'), (p_val, p_mom, p_net)),
            (('val', 'flow', 'cat'), (p_val, p_flow, p_cat)),
            (('val', 'flow', 'net'), (p_val, p_flow, p_net)),
            (('val', 'cat', 'net'), (p_val, p_cat, p_net)),
            (('mom', 'flow', 'cat'), (p_mom, p_flow, p_cat)),
            (('mom', 'flow', 'net'), (p_mom, p_flow, p_net)),
            (('mom', 'cat', 'net'), (p_mom, p_cat, p_net)),
            (('flow', 'cat', 'net'), (p_flow, p_cat, p_net)),
        ]
        tri_multipliers = {
            ('val', 'mom', 'flow'): 1.40,
            ('flow', 'cat', 'net'): 1.20,
        }
        tri_confluence = pd.Series(0.0, index=scores_df.index)
        if w_tri > 0:
            if version >= 7:
                for trip_key, (t1, t2, t3) in named_triplets:
                    mult_factor = tri_multipliers.get(trip_key, 1.00)
                    tri_confluence += (w_tri * mult_factor) * (t1 * t2 * t3)
            else:
                for _, (t1, t2, t3) in named_triplets:
                    tri_confluence += w_tri * (t1 * t2 * t3)

        # 3. 4th-order Quadruplets (5 terms)
        quads = [
            (p_val, p_mom, p_flow, p_cat),
            (p_val, p_mom, p_flow, p_net),
            (p_val, p_mom, p_cat, p_net),
            (p_val, p_flow, p_cat, p_net),
            (p_mom, p_flow, p_cat, p_net)
        ]
        quad_confluence = pd.Series(0.0, index=scores_df.index)
        if w_quad > 0:
            for q1, q2, q3, q4 in quads:
                quad_confluence += w_quad * (q1 * q2 * q3 * q4)

        # 4. 5th-order Quintuplet Hyper-Confluence (1 term)
        quint_confluence = pd.Series(0.0, index=scores_df.index)
        if w_quint > 0:
            quint_confluence = w_quint * (p_val * p_mom * p_flow * p_cat * p_net)

        raw_confluence = synergy_sum + tri_confluence + quad_confluence + quint_confluence

        # 5. Pillar Harmony Regularizer H_pillar (Phase 7 Zenith F47.1)
        if version >= 7:
            p_vals = np.array([p_val.values, p_mom.values, p_flow.values, p_cat.values, p_net.values])
            p_mean = np.mean(p_vals, axis=0)
            p_std = np.std(p_vals, axis=0)
            cv_p = p_std / (p_mean + 1e-4)
            cv_clipped = np.clip(cv_p, 0.0, 2.0)
            h_pillar = np.exp(-1.20 * np.square(cv_clipped))
            harmony_factor = pd.Series(
                1.0 + 0.25 * h_pillar * (p_mean > 0.40).astype(float),
                index=scores_df.index
            )
            total_confluence = raw_confluence * harmony_factor
        else:
            total_confluence = raw_confluence

        if max_cap is not None:
            eff_cap = float(max_cap)
        elif regime_adaptive_cap:
            eff_cap = float(reg_cap)
        else:
            eff_cap = 0.100

        synergy_multiplier = 1.0 + total_confluence.clip(0.0, eff_cap)
        return synergy_multiplier
```

#### Modification 2: Call-site Wiring in `combine_predictions`
**Location**: Lines 3264–3272 in `trading_system/src/ai/ensemble_scorer.py`

```python
                # Phase 2-B: Quint-Pillar High-Order Tensor Synergy Kernel (F41.1 & F47.1) vs Quad-Pillar Baseline
                if int(version) >= 6:
                    synergy_mult = self.compute_quint_pillar_tensor_synergy(
                        scores_df=merged,
                        regime=regime,
                        kappa=8.0,
                        regime_adaptive_cap=True,
                        version=version
                    )
```

---

## 5. Invariant Test Verification Specification

To ensure rigorous validation of Feature F47, the following test cases are formulated for `tests/test_phase7_signal_enhancement.py`:

### Test Case 1: `test_f47_strict_synergy_hierarchy_preserved_v7`
- **Objective**: Verify strict inequality chain:
  $$\text{ASSET\_0 (5-Pillar)} > \text{ASSET\_1 (4-Pillar)} > \text{ASSET\_2 (3-Pillar)} > \text{ASSET\_3 (2-Pillar)} > \text{ASSET\_4 (1-Pillar)} == 1.0000 == \text{ASSET\_5 (Neutral)}$$
- **Setup**: Synthetic 10-asset universe with strong conviction (0.92) populated across 5, 4, 3, 2, 1, and 0 pillars.
- **Assertions**:
  - `mult_v7['ASSET_0'] > mult_v7['ASSET_1']`
  - `mult_v7['ASSET_1'] > mult_v7['ASSET_2']`
  - `mult_v7['ASSET_2'] > mult_v7['ASSET_3']`
  - `mult_v7['ASSET_3'] > mult_v7['ASSET_4']`
  - `math.isclose(mult_v7['ASSET_4'], 1.0000, abs_tol=1e-4)`
  - `math.isclose(mult_v7['ASSET_5'], 1.0000, abs_tol=1e-4)`

### Test Case 2: `test_f47_economically_weighted_triplet_boost`
- **Objective**: Verify that `('val', 'mom', 'flow')` receives a 1.40x boost over unboosted triplets, and `('flow', 'cat', 'net')` receives a 1.20x boost.
- **Setup**: 
  - Asset A: strong in `val`, `mom`, `flow` (conviction 0.85).
  - Asset B: strong in `val`, `mom`, `cat` (conviction 0.85).
  - Asset C: strong in `flow`, `cat`, `net` (conviction 0.85).
- **Assertions**:
  - In `version=6`: `math.isclose(mult_v6['ASSET_A'], mult_v6['ASSET_B'], abs_tol=1e-4)`
  - In `version=7`: `mult_v7['ASSET_A'] > mult_v7['ASSET_B']`
  - In `version=7`: `mult_v7['ASSET_C'] > mult_v7['ASSET_B']`
  - Ratio test: $(mult_{v7, A} - 1.0 - \Xi_{(2), A}) / (mult_{v7, B} - 1.0 - \Xi_{(2), B}) \approx 1.40$.

### Test Case 3: `test_f47_pillar_harmony_regularizer_precision`
- **Objective**: Verify that $\mathcal{H}_{\text{pillar}} = \exp(-1.20 \cdot \text{CV}_\psi^2)$ correctly rewards balanced multi-pillar assets over lopsided assets.
- **Setup**:
  - Asset Balanced: all 5 pillars have equal conviction $\psi = 0.80$ ($\text{CV}_\psi = 0$).
  - Asset Lopsided: 2 pillars at $\psi = 0.95$, 3 pillars at $\psi = 0.00$ ($\text{CV}_\psi \approx 1.22$).
- **Assertions**:
  - For Balanced: $\mathcal{H}_{\text{pillar}} = 1.0000$, $\text{harmony\_factor} = 1.2500$.
  - For Lopsided: $\mathcal{H}_{\text{pillar}} = \exp(-1.20 \times 1.22^2) \approx 0.167$, $\text{harmony\_factor} \le 1.05$.
  - Confluence of Balanced is boosted by full 1.25x factor.

### Test Case 4: `test_f47_bull_low_vol_cap_expansion_to_0220`
- **Objective**: Verify that `BULL_LOW_VOL` cap expands from 0.180 to 0.220 for super-confluent assets.
- **Setup**: Super-confluent asset with all 37 strategies at 0.95 conviction.
- **Assertions**:
  - In `version=7`: `math.isclose(mult_v7['ASSET_0'], 1.2200, abs_tol=1e-4)`
  - In `version=6`: `math.isclose(mult_v6['ASSET_0'], 1.1800, abs_tol=1e-4)`
  - Ratio expansion: $mult_{v7} > mult_{v6}$ by exactly $+0.040$ ($+22.2\%$ additional synergy headroom).

### Test Case 5: `test_f47_crisis_cap_safety_boundedness`
- **Objective**: Verify that `CRISIS` cap is strictly bounded at $\le 1.04001$ in both $v=6$ and $v=7$.
- **Setup**: Super-confluent asset evaluated in `CRISIS` regime.
- **Assertions**:
  - `mult_crisis_v7['ASSET_0'] <= 1.04001`
  - `mult_crisis_v7['ASSET_0'] >= 1.00000`
  - All 10 assets stay strictly in $[1.0000, 1.04001]$ under `CRISIS`.

### Test Case 6: `test_f47_zero_regression_phase6_parity`
- **Objective**: Verify bit-exact parity between Phase 6 baseline and new implementation with `version=6`.
- **Setup**: 100 randomized multi-asset portfolios across all 7 market regimes.
- **Assertions**:
  - `np.max(np.abs(res_legacy.values - res_v6.values)) < 1e-12` across all 7 regimes.
  - Legacy `tests/test_phase6_signal_enhancement.py` passes 6/6 tests (100%).

---

## 6. Implementation Checklist for Worker & Reviewer

1. [ ] Apply modifications to `compute_quint_pillar_tensor_synergy` in `trading_system/src/ai/ensemble_scorer.py`:
   - Add `version: int = 6` parameter with `version = int(kwargs.get('version', version))`.
   - Update `BULL_LOW_VOL` regime cap: `reg_cap = 0.220 if version >= 7 else 0.180`.
   - Add named triplet economic weighting: `('val', 'mom', 'flow'): 1.40`, `('flow', 'cat', 'net'): 1.20`.
   - Add Pillar Harmony Regularizer $\mathcal{H}_{\text{pillar}} = \exp(-1.20 \cdot \text{CV}_\psi^2)$ and `harmony_factor = 1.0 + 0.25 * h_pillar * (p_mean > 0.40)`.
2. [ ] Update call site in `combine_predictions` line 3266 to pass `version=version`.
3. [ ] Verify `tests/test_phase6_signal_enhancement.py` passes 100% (6/6).
4. [ ] Verify `tests/test_phase6_m1_challenger1_adversarial.py` passes 100% (27/27).
5. [ ] Verify `tests/test_phase6_m1_challenger2_adversarial.py` passes 100% (23/23).
6. [ ] Implement `tests/test_phase7_signal_enhancement.py` with the 6 invariant test cases.
