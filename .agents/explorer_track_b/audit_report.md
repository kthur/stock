# 37-전략 통합 트레이딩 시스템 심층 무결성 및 운용 감사 보고서 (Track B)
**Track B Scope**: Strategies 20–37, Score Normalization, ZCA Whitening, Suppression & Dynamic Ensemble  
**Auditor**: Explorer Track B  
**Date**: 2026-09-03  
**Target Repository**: `d:\Finance\code\stock`

---

## 1. Executive Summary

본 감사는 한국(KOSPI, KOSDAQ) 및 미국(SP500, NASDAQ, RUSSELL2000) 5대 시장을 대상으로 37대 다변화 전략을 병행 운영하는 퀀트 자동매매 시스템의 후반부 핵심 파이프라인(전략 20~37번, 횡단면 정규화, ZCA 백색화, 다중공선성 노이즈 억제, 동적 앙상블 가중치 및 미시구조 거래비용 모델)을 전수 정밀 점검하였습니다.

점검 결과, 1D 및 2D 레짐 가중치 행렬(각 37개 전략)은 수학적으로 정확히 합계 1.0000으로 정규화되어 있으나, 실제 런타임 신호 결합 및 정규화 과정에서 **신호 왜곡 및 심각한 런타임 바이패스를 초래하는 3건의 치명적 결함(Critical)**과 **가중치 희석 및 스케일 불연속을 야기하는 5건의 주요 결함(High)**, 그리고 **보고서/메타데이터 불일치에 해당하는 4건의 보통 결함(Medium)**을 식별하였습니다.

---

## 2. Comprehensive Issue Matrix (우선순위 요약)

| ID | 우선순위 | 영역 / 컴포넌트 | 대상 파일 및 위치 | 핵심 문제 요약 |
|---|---|---|---|---|
| **C-01** | **Critical** | Dynamic Ensemble / Correlation Penalty | `src/ai/ensemble_scorer.py` (L.967-969) | 37개 전략 전수 `.dropna()`로 인한 상관 직교화 페널티 전면 무력화 |
| **C-02** | **Critical** | Strategy Registry / Adapter | `src/ai/ml_strategy_adapters.py` (L.373-375) | Strategy 30(Darkpool) 호출 시 Strategy 23(Microstructure) 오인스턴스화 |
| **C-03** | **Critical** | ZCA Whitening / Numerical Stability | `src/ai/factor_orthogonalizer.py` (L.226-235) | 주성분 consensus preservation 미구현으로 인한 시장 알파 65% 압축 왜곡 |
| **H-01** | **High** | 2D Regime Noise Suppression | `src/ai/factor_suppression.py` (L.74-80) | `CLUSTER_MAP`에 전략 35, 36, 37 누락으로 레짐 노이즈 억제 탈루 |
| **H-02** | **High** | Multi-Horizon Alpha Decomposition | `src/ai/ensemble_scorer.py` (L.2504-2511, 2566) | 티어별 단순 산술평균 계산으로 동적 레짐 가중치 30% 무차별 희석 |
| **H-03** | **High** | Missingness & Weight Normalization | `src/ai/ensemble_scorer.py` (L.2485-2496) | 단일 전략 결측 시 신뢰도 수축(Bayesian Shrinkage) 부재로 순위 왜곡 |
| **H-04** | **High** | Microstructure Friction Model | `src/ai/ensemble_scorer.py` (L.2801-2803) | US 티커(`BRK.B` 등) 온점(.) 파싱 오류로 인한 국내 증권거래세 오과금 |
| **H-05** | **High** | Short Squeeze Strategy | `src/core/short_interest_squeeze.py` (L.116-160) | 데이터 결측 시 저조한 프록시 점수와 원천 점수 간 백분위 랭크 왜곡 |
| **M-01** | **Medium** | Coverage Analyzer | `src/analysis/coverage_analyzer.py` (L.196-214) | 신규 전략 32~37번 결측 사유 매핑 누락(`STRATEGY_SIGNAL_NEUTRAL` 일괄 처리) |
| **M-02** | **Medium** | Strategy Registry Metadata | `src/core/hft_engine.py`, `dual_correction.py`, `index_rebalance.py` | `is_standalone=True` 충돌 및 기본 레짐 가중치 불일치 |
| **M-03** | **Medium** | Cross-Sectional Score Normalizer | `src/ai/score_normalizer.py` (L.144-150) | 소형 유니버스($N < 10$)에서 비활성 0점 블록 격리 조건 미충족 |
| **M-04** | **Medium** | Microstructure Friction Model | `src/ai/ensemble_scorer.py` (L.2809-2811, 2985-2987) | 거래대금(`turnover`) 중복 계산 및 불필요한 연산 오버헤드 |

---

## 3. Detailed Forensic Audit Findings (상세 감사 내역)

---

### [Critical Issues]

#### 1. [CRITICAL-01] 37개 전략 전수 `.dropna()`로 인한 상관 직교화 페널티 전면 무력화

##### [현황 및 문제점]
`trading_system/src/ai/ensemble_scorer.py`의 `apply_correlation_orthogonalization_penalty()` 함수(967~969행):
```python
967: subset_df = scores_df[list(valid_cols.values())].apply(pd.to_numeric, errors='coerce').dropna()
968: if len(subset_df) < 10:
969:     return weights
```
- **원인 분석**: 37대 전략 체계에서는 대안 데이터(다크풀, 옵션 IV/Gamma, 어닝콜 텍스트 톤, 공시 감성 등)의 특성상 종목별로 일부 전략 데이터가 결측(`NaN`)되는 것이 자연스럽습니다. 그러나 위 코드는 유효한 37개 전략 점수 컬럼 전체에 대해 단 하나의 결측치라도 존재하면 해당 행(종목) 전체를 제거하는 `.dropna()`를 수행합니다.
- **결과**: 유니버스 내에서 37개 전략이 단 1개도 결측되지 않고 100% 채워진 종목 수가 10개 미만(`len(subset_df) < 10`)으로 떨어지게 되며, 이로 인해 Löwdin 대칭 직교화 상관 페널티 계산이 **조용히 중단(Silent Bypass)되어 원본 가중치 `weights`가 그대로 반환**됩니다. 전략 간 높은 상관성을 제어하기 위한 핵심 안정성 장치가 실전 파이프라인에서 완전히 비활성화되는 치명적 결함입니다.

##### [정량적/공학적 개선 방안]
전체 행 제거 방식 대신, 각 전략 간 유효 관측치를 보존하는 **Pairwise Complete Correlation** 방식을 적용하거나 결측치를 섹터/시장 중앙값으로 대치한 후 상관행렬을 산출합니다:
```python
# 개선안: Pairwise 완전 관측치 기반 상관계수 산출 및 최소 샘플 임계치 완화
corr_matrix = scores_df[list(valid_cols.values())].apply(pd.to_numeric, errors='coerce').corr(min_periods=5).abs().fillna(0.0)
np.fill_diagonal(corr_matrix.values, 1.0)
```

##### [수정 대상 파일]
- `trading_system/src/ai/ensemble_scorer.py`: `apply_correlation_orthogonalization_penalty()` (Line 967-972)

##### [검증 방안]
- **테스트 케이스**: `tests/test_ensemble_correlation_penalty.py` 신설. 50개 종목 중 각 전략별로 10~20%의 결측치가 분산되어 단 하나의 종목도 37개 전략 전수가 채워지지 않은 상태를 구성.
- **합격 기준**: `len(subset_df) < 10`에 걸리지 않고 `penalized_weights`가 정상 산출되어 고상관 전략(상관계수 > 0.65)에 대해 유의미한 가중치 감쇄가 발생하는지 검증.

---

#### 2. [CRITICAL-02] Strategy 30(Darkpool) 어댑터의 클래스 오인스턴스화

##### [현황 및 문제점]
`trading_system/src/ai/ml_strategy_adapters.py`의 `DarkPoolStrategyAdapter.compute_scores()` 함수(373~375행):
```python
371: if self.model_instance is not None and hasattr(self.model_instance, "compute_scores"):
372:     return self.model_instance.compute_scores(prices_dict=prices_dict, **kwargs)
373: from src.core.hft_engine import MicrostructureImbalanceEngine
374: engine = MicrostructureImbalanceEngine()
375: res = engine.compute_scores(prices_dict=prices_dict, **kwargs)
```
- **원인 분석**: 전략 30번(`darkpool`)은 다크풀 블록트레이드 및 장외 거래량 괴리를 추적하는 전략입니다. 실제 구현체는 `src.data_layer.darkpool_tracker.DarkPoolTrackerEngine`에 정의되어 있으며, `run_pipeline.py`(3232행)에서는 이 `DarkPoolTrackerEngine`을 직접 호출합니다. 그러나 `StrategyRegistry`에 등록된 공식 어댑터 `DarkPoolStrategyAdapter`는 내부에서 전략 23번인 `MicrostructureImbalanceEngine`(호가창 불균형 엔진)을 임포트하여 실행하고 컬럼명만 `darkpool_score`로 변경하고 있습니다.
- **결과**: `StrategyRegistry`나 백테스트 러너, 모듈형 전략 파이프라인에서 전략 30번을 실행할 경우, 다크풀 추적 대신 호가창 미시구조 점수(Strategy 23)가 이중으로 산출되어 전략 23번과 30번 간 상관계수가 1.0000이 되고 모델 다변화 효과가 원천 상실됩니다.

##### [정량적/공학적 개선 방안]
`DarkPoolStrategyAdapter`가 올바른 `DarkPoolTrackerEngine`을 인스턴스화하여 다크풀/블록트레이드 괴리 점수를 산출하도록 바인딩을 수정합니다:
```python
from src.data_layer.darkpool_tracker import DarkPoolTrackerEngine
engine = DarkPoolTrackerEngine(config=self.config)
res = engine.calculate_scores(symbols=list(prices_dict.keys()), prices_dict=prices_dict, **kwargs)
```

##### [수정 대상 파일]
- `trading_system/src/ai/ml_strategy_adapters.py`: `DarkPoolStrategyAdapter.compute_scores()` (Line 373-375)

##### [검증 방안]
- **테스트 케이스**: `registry.get("darkpool")[0]().compute_scores(prices_dict)` 실행 결과와 `DarkPoolTrackerEngine().calculate_scores()` 결과의 동등성을 검증.
- **합격 기준**: 반환된 DataFrame이 `MicrostructureImbalanceEngine`의 결과와 독립적이며, `darkpool_score`가 블록 거래량 및 ATS 비율에 반응함을 확인.

---

#### 3. [CRITICAL-03] ZCA 백색화의 주성분 Consensus Alpha 파괴 (코드 미구현)

##### [현황 및 문제점]
`trading_system/src/ai/factor_orthogonalizer.py`의 `_pca_zca_symmetric()` 함수(226~235행):
```python
226: # Smooth Spectral Tikhonov / ESRW Whitening Operator:
227: # Multi-model consensus preservation (V7-03):
228: # Do not compress the leading principal component (PC1 = shared multi-strategy consensus).
229: # For lambda_max (last eigen-pair in ascending eigh), keep whitening filter = 1.0.
230: # For residual eigenvalues, apply smooth spectral Tikhonov damping.
231: lambdas_clean = np.maximum(eigenvalues, 0.0)
232: ridge_eps = float(np.clip(self.ridge_epsilon, 1e-6, 1e-3))
233: whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)
```
- **원인 분석**: 주석(227~230행)에는 "선행 주성분(PC1)인 다중 전략 컨센서스를 압축하지 않기 위해 $\lambda_{\max}$에 대해 whitening filter = 1.0을 유지한다"고 명시되어 있습니다. 그러나 실제 구현 코드(233행)에서는 `whitening_filter`가 모든 고유값에 대해 무차별적으로 $1 / \sqrt{\lambda + \epsilon}$를 적용합니다.
- **결과**: 37개 전략이 공통으로 강력한 확신(Consensus)을 나타낼 때 PC1의 고유값은 $\lambda_{\max} \approx 8.0 \sim 15.0$ 수준으로 커집니다. 이때 필터값은 $1 / \sqrt{10} \approx 0.316$이 되어 **모든 모델이 일치하여 찾아낸 시장 초과수익(Shared Alpha)을 68% 이상 강제로 압축(Damping)**해 버립니다. 반대로 노이즈에 해당하는 극소 고유값($\lambda \approx 0$)에는 $1 / \sqrt{10^{-6}} = 1,000$배의 거대한 필터가 곱해져 공선성 널 공간(Collinear Null Space)의 수치 노이즈를 극단적으로 증폭시킵니다.

##### [정량적/공학적 개선 방안]
1. 주석의 의도대로 $\lambda_{\max}$에 대한 백색화 필터를 1.0으로 고정하거나 완만한 스펙트럼 보존 필터를 적용합니다.
2. 상태수(Condition Number) $\kappa = \lambda_{\max} / (\lambda_{\min} + \epsilon)$를 계산하여 최대 증폭비를 10.0 이내로 캡핑(Eigenvalue Floor Capping)합니다:
```python
lambdas_clean = np.maximum(eigenvalues, 0.0)
ridge_eps = float(np.clip(self.ridge_epsilon, 1e-6, 1e-3))
whitening_filter = 1.0 / np.sqrt(lambdas_clean + ridge_eps)

# Consensus Alpha 보존: PC1(최대 고유값) 필터는 1.0으로 고정하여 공유 신호 압축 방지
if len(whitening_filter) > 0:
    whitening_filter[-1] = 1.0

# 상태수 기반 수치 안정성 보장: 극소 고유값의 무한 증폭 방지 (최대 10배 제한)
whitening_filter = np.minimum(whitening_filter, 10.0)
```

##### [수정 대상 파일]
- `trading_system/src/ai/factor_orthogonalizer.py`: `_pca_zca_symmetric()` (Line 231-236)

##### [검증 방안]
- **테스트 케이스**: 고상관 전략 신호($\rho = 0.85$)를 합성하여 백색화 전후의 PC1 투영 분산 비율을 측정.
- **합격 기준**: 백색화 후 PC1의 분산이 원본 대비 90% 이상 보존되며, 잔차 직교 성분들의 상관계수는 0.15 미만으로 안정화됨을 확인.

---

### [High-Priority Issues]

#### 4. [HIGH-01] `factor_suppression.py`의 `CLUSTER_MAP` 내 전략 35, 36, 37번 누락

##### [현황 및 문제점]
`trading_system/src/ai/factor_suppression.py`의 `CLUSTER_MAP` 정의(74~80행):
```python
74: CLUSTER_MAP = {
75:     'CORE_AI': ['regression', 'lstm', 'vol_target'],
76:     'MOMENTUM': ['surge', 'vcp_ml', 'sector_rotation', 'arm_factor', 'supply_chain', 'short_squeeze', 'trend_efficiency', 'supply_chain_gnn', 'cross_asset_spillover', 'range_expansion_breakout', 'range_expansion', 'intraday_breakout'],
77:     'VALUATION': ['rim_valuation', 'rim', 'mq_factor', 'factor_neutralized', 'accruals_quality', 'valueup_catalyst', 'value_up'],
78:     'REVERSAL': ['stat_arb', 'vcp_rule', 'vcp', 'vcp_patterns', 'short_term_reversal', 'card_factor'],
79:     'FLOW_MICRO': ['lead_lag', 'event_driven', 'iv_skew', 'order_flow', 'latr_factor', 'inst_foreign_sector', 'sentiment', 'microstructure', 'gamma_squeeze', 'insider_buying', 'darkpool', 'darkpool_hft', 'earnings_tone_drift', 'tone_drift', 'hft']
80: }
```
- **원인 분석**: 전략 35번(`dual_correction`), 36번(`index_rebalance`), 37번(`overnight_gap_reversal`)이 `CLUSTER_MAP`에 등록되어 있지 않습니다.
- **결과**: `self.STRATEGY_TO_CLUSTER.get(strat_i, 'OTHER')` 로직에 의해 세 전략은 모두 클러스터 `'OTHER'`로 분류됩니다. 따라서:
  1. 클러스터 내부 중복 페널티(Intra-cluster multiplier $c_{ij} = 2.0$ 또는 $1.5$)가 전혀 적용되지 않고 기본값 $1.0$만 적용됩니다.
  2. 2D 레짐별 고위험 클러스터 억제 목록(`HIGH_RISK_CLUSTERS_PER_REGIME`)에 매칭되지 않아, 강세장에서 평균회귀 전략을 억제하거나 횡보장에서 모멘텀/수급 전략을 억제할 때 규제망을 완전히 벗어나게 됩니다.

##### [정량적/공학적 개선 방안]
`CLUSTER_MAP`에 신규 전략 35~37번을 금융 논리에 맞추어 명시적으로 등록합니다:
- `dual_correction` $\rightarrow$ `'REVERSAL'` (피보나치/AVWAP 눌림목 반등)
- `index_rebalance` $\rightarrow$ `'FLOW_MICRO'` (패시브 자금 리밸런싱 수급)
- `overnight_gap_reversal` $\rightarrow$ `'REVERSAL'` (시가 갭 페이드 및 평균회귀)

##### [수정 대상 파일]
- `trading_system/src/ai/factor_suppression.py`: `RegimeFactorSuppressionEngine.CLUSTER_MAP` (Line 78-79)

##### [검증 방안]
- **테스트 케이스**: `tests/test_factor_suppression.py`에서 `dual_correction`, `index_rebalance`, `overnight_gap_reversal`의 클러스터 매핑을 assert하고, 고상관 레짐에서 suppression multiplier $P_i$가 정상 감쇄되는지 검증.

---

#### 5. [HIGH-02] `ensemble_scorer.py`의 Multi-Horizon 티어 점수 단순 평균으로 인한 동적 가중치 30% 희석

##### [현황 및 문제점]
`trading_system/src/ai/ensemble_scorer.py`의 `combine_predictions()` (2504~2511행 및 2566행):
```python
2504: def _calc_tier_score(cols_list):
...
2511:     return np.where(v_counts > 0, sub_sums / np.maximum(v_counts, 1), np.nan)
...
2566: linear_score = pd.Series(0.70 * linear_score + 0.30 * hierarchical_score, index=merged.index).clip(0.0, 1.0)
```
- **원인 분석**: Slow(30~90d), Medium(5~20d), Fast(1~3d)의 3개 티어로 알파를 분해하는 과정에서, 각 티어 내부 점수(`_calc_tier_score`)를 계산할 때 해당 티어에 속한 전략 점수들을 **단순 산술평균(`sub_sums / v_counts`)**합니다.
- **결과**: 앞단에서 2D 레짐, 롤링 샤프, IC 모멘텀, 직교화 페널티를 거쳐 정밀하게 산출된 `eff_us_weights`와 `eff_kr_weights`가 티어 내부에서는 완전히 무시됩니다. 최종 `linear_score`의 30%를 차지하는 `hierarchical_score`가 동일 가중치(Equal-weight)로 계산됨으로써, **공들여 최적화한 동적 레짐 가중치의 30%가 단순 평균 잡음으로 희석**됩니다.

##### [정량적/공학적 개선 방안]
티어 내부 점수를 계산할 때도 유효 전략별 정규화된 동적 가중치를 곱하여 가중평균하도록 수정합니다:
```python
def _calc_weighted_tier_score(strat_names_and_cols, eff_weights_series):
    t_score_sum = pd.Series(0.0, index=merged.index)
    t_weight_sum = pd.Series(0.0, index=merged.index)
    for sn, sc in strat_names_and_cols:
        if sc in merged.columns:
            vm = merged[sc].notna() & np.isfinite(merged[sc])
            w = eff_weights_series[sn]
            t_score_sum += np.where(vm, merged[sc] * w, 0.0)
            t_weight_sum += np.where(vm, w, 0.0)
    return np.where(t_weight_sum > 0, t_score_sum / np.maximum(t_weight_sum, 1e-6), np.nan)
```

##### [수정 대상 파일]
- `trading_system/src/ai/ensemble_scorer.py`: `combine_predictions()` (Line 2504-2520)

##### [검증 방안]
- **테스트 케이스**: 특정 티어 내 전략 A의 가중치가 0.09, 전략 B의 가중치가 0.01일 때, B의 극단값 노이즈가 티어 점수를 왜곡시키지 않고 A의 신호에 90% 비례하는지 검증.

---

#### 6. [HIGH-03] 단일/소수 전략 유효 종목에 대한 Bayesian Coverage Shrinkage 부재

##### [현황 및 문제점]
`trading_system/src/ai/ensemble_scorer.py`의 가중치 재정규화 로직(2485~2496행):
```python
2490: safe_valid_weight = valid_weight_series.replace(0.0, 1.0)
2495: raw_linear_score = pd.Series(np.where(has_valid, (total_score_series / safe_valid_weight).clip(0.0, 1.0), 0.0), index=merged.index)
```
- **원인 분석**: 특정 종목이 37개 전략 중 36개가 결측되고 단 1개(예: `event_driven` 단독 호재 공시 0.95점, 공칭 가중치 0.03)만 유효할 경우, `safe_valid_weight`는 0.03이 됩니다. 이때 `total_score_series / safe_valid_weight = (0.95 * 0.03) / 0.03 = 0.95`가 됩니다.
- **결과**: 37개 전략 전수의 검증을 거쳐 0.90점을 받은 초우량 확신 종목보다, 단 1개의 전략만 우연히 터지고 나머지 36개 전략의 검증을 전혀 받지 못한 불완전 종목이 최상위(Rank 1)로 치고 올라가는 현상이 발생합니다.

##### [정량적/공학적 개선 방안]
유효 전략 가중치의 합(`valid_weight_series`)이 명목 가중치 총합(1.0)에 미달할 경우, 신뢰도를 중립 기준점(0.50)으로 베이지안 수축(Bayesian Shrinkage)시키는 보정식을 도입합니다:
$$S_{\text{final}} = \lambda_{\text{cov}} \cdot S_{\text{norm}} + (1 - \lambda_{\text{cov}}) \cdot 0.50, \quad \text{where } \lambda_{\text{cov}} = \min\left(1.0, \frac{\sum_{k \in \text{valid}} w_k}{W_{\text{target}}}\right)$$
(여기서 $W_{\text{target}} \approx 0.60$, 즉 최소 60% 이상의 가중치 커버리지를 확보해야 100% 신뢰도 부여)

##### [수정 대상 파일]
- `trading_system/src/ai/ensemble_scorer.py`: `combine_predictions()` (Line 2494-2497)

##### [검증 방안]
- **테스트 케이스**: 전략 1개만 0.95점을 받은 종목과 전략 30개가 0.85점을 받은 종목의 최종 순위를 비교하여 후자가 상위를 차지하도록 검증.

---

#### 7. [HIGH-04] 미시구조 거래비용 모델의 US 티커 온점(.) 파싱 오류 및 증권거래세 오과금

##### [현황 및 문제점]
`trading_system/src/ai/ensemble_scorer.py`의 미시구조 모델(2801~2803행, 2853~2854행):
```python
2802: is_us_stock = mkt_col.isin(['SP500', 'NASDAQ', 'RUSSELL2000']) | (sym_col.str.isalpha() & (sym_col.str.len() <= 5))
...
2853: m_kospi = ((mkt_col == 'KOSPI') | sym_col.str.endswith('.KS') | (sym_col.str.isdigit() & (sym_col.str.len() == 6))) & ~m_kosdaq
2854: stt_tax[m_kospi] = 0.0018
...
2863: m_other_us = is_us_stock & ~m_nasdaq & ~m_russell & ~m_kosdaq & ~m_kospi
```
- **원인 분석**: 입력 DataFrame의 `market` 컬럼이 누락되거나 비어 있는 경우, `is_us_stock`은 `sym_col.str.isalpha() & (sym_col.str.len() <= 5)` 조건으로 식별합니다. 그러나 버크셔 해서웨이(`BRK.B`), 브라운포먼(`BF.B`) 등 클래스 구분 온점(`.`)이 포함된 미국 주요 대형주는 `isalpha()`가 `False`가 됩니다.
- **결과**: `is_us_stock`이 `False`로 판정되고 기본 한국 시장 프로파일(KOSPI)로 분류되어, 미국 주식임에도 **한국 증권거래세(0.18%)가 부과되고 한국식 기준 주문금액(5,000만 원)이 적용**되어 예상 순수익률이 크게 훼손됩니다.

##### [정량적/공학적 개선 방안]
온점을 허용하는 정규표현식(`^[A-Z]{1,5}(\.[A-Z])?$`)으로 변경하여 미국 주식 식별을 완전무결하게 만듭니다:
```python
is_us_sym = sym_col.str.match(r'^[A-Z]{1,5}(\.[A-Z])?$') & ~sym_col.str.endswith(('.KS', '.KQ'))
is_us_stock = mkt_col.isin(['SP500', 'NASDAQ', 'RUSSELL2000']) | is_us_sym
```

##### [수정 대상 파일]
- `trading_system/src/ai/ensemble_scorer.py`: Line 2802

##### [검증 방안]
- **테스트 케이스**: `market` 컬럼 없이 `BRK.B`, `BF.B`를 입력하여 `stt_tax`가 0.00003(SEC 수수료)으로 적용되고 0.0018(STT)이 아님을 검증.

---

#### 8. [HIGH-05] 숏스퀴즈 전략의 데이터 결측 프록시 점수와 원천 점수 간 랭킹 왜곡

##### [현황 및 문제점]
`trading_system/src/core/short_interest_squeeze.py` (116~124행 및 149~160행):
```python
121: proxy_score = float(0.15 * max(-0.2, min(0.5, ret_5d)) + 0.10 * (min(3.0, vol_surge) / 3.0) + ...) # 통상 0.10 ~ 0.25
122: results[sym_str] = float(np.clip(proxy_score, 0.0, 1.0))
...
149: raw_squeeze = float(f_sr * f_dtc * mom_factor * ignite_mult * htb_squeeze_mult) # 통상 0.50 ~ 5.0+
150: results[sym_str] = raw_squeeze
...
160: ranks = df_out.loc[valid_mask, 'raw_score'].rank(pct=True, ascending=True).clip(0.02, 0.98)
```
- **원인 분석**: 공매도 잔고율(Short Interest) 및 DTC 데이터가 없는 종목에 대해 거래량 급증 기반의 프록시 점수(`proxy_score`, 0.05~0.30 범위)를 산출한 뒤, 실제 공매도 데이터가 존재하는 종목의 미정규화 원천 점수(`raw_squeeze`, 0.5~5.0 범위)와 **동일한 `raw_score` 컬럼에 병합한 후 일괄 백분위 랭크(`rank(pct=True)`)를 수행**합니다.
- **결과**: 수치 스케일 차이로 인해, 프록시 점수를 받은 정상 종목들은 공매도 데이터가 있는 종목들보다 무조건 하위 30% 랭크로 밀려납니다. 즉, 데이터 결측 종목이 구조적으로 숏스퀴즈 패널티를 받게 됩니다.

##### [정량적/공학적 개선 방안]
공매도 데이터가 없는 종목은 다른 전략들처럼 **진정한 결측치(`np.nan`)를 반환**하여 `ensemble_scorer.py`의 결측치 제로 가중치 재정규화 메커니즘을 타게 하거나, 프록시를 사용할 경우 원천 점수 분포와 스케일을 일치시킨 후 정규화해야 합니다:
```python
# 원칙 준수: 가짜 프록시 결합 대신 진정한 NaN 반환
if pd.isna(short_ratio) or pd.isna(dtc):
    results[sym_str] = np.nan
```

##### [수정 대상 파일]
- `trading_system/src/core/short_interest_squeeze.py`: `calculate_scores()` (Line 101-125)

##### [검증 방안]
- **테스트 케이스**: 공매도 데이터가 없는 종목들이 인위적인 하위 랭크 왜곡 없이 `NaN`으로 온전히 보존되는지 검증.

---

### [Medium-Priority Issues]

#### 9. [MEDIUM-01] `coverage_analyzer.py` 내 신규 전략 32~37번 결측 사유 매핑 누락
- **파일**: `trading_system/src/analysis/coverage_analyzer.py` (Line 196-214)
- **현황**: `options_strats`, `us_strats`, `pair_strats`, `sentiment_strats` 등의 분류 집합에 전략 32번(`cross_asset_spillover`), 33번(`supply_chain_gnn`), 36번(`index_rebalance`) 등이 포함되지 않아 결측 시 모두 `STRATEGY_SIGNAL_NEUTRAL`로 일괄 출력됨.
- **개선안**: 거시 지표 누락(`NO_MACRO_INDICATORS`), 공급망 그래프 누락(`NO_VALUE_CHAIN_EDGE`), 리밸런싱 비시즌(`OFF_SEASON_REBALANCE`) 사유를 추가 매핑.

#### 10. [MEDIUM-02] StrategyRegistry 메타데이터 불일치 및 `is_standalone` 속성 충돌
- **파일**: `trading_system/src/core/hft_engine.py` (Line 161), `dual_correction.py` (Line 246), `index_rebalance.py` (Line 23)
- **현황**:
  - `MicrostructureImbalanceEngine`에 `is_standalone=True`로 선언되어 앙상블 제외 대상으로 표기되어 있으나, `ensemble_scorer.py`에서는 가중치(0.02~0.03)를 할당하여 실집행 앙상블에 포함하고 있음.
  - `dual_correction.py`의 `default_regime_weights` 합계가 0.42로 규격(1.0)에 미달함.
  - `index_rebalance.py`의 `default_regime_weights`가 누락됨.
- **개선안**: `is_standalone=False`로 통일하고 메타데이터 기본 레짐 가중치를 `ensemble_scorer.py`의 규격과 일치시킴.

#### 11. [MEDIUM-03] `CrossSectionalScoreNormalizer` 비활성 0점 블록 격리 임계치 경직성
- **파일**: `trading_system/src/ai/score_normalizer.py` (Line 144-150)
- **현황**: 비음수 희소 팩터(Short Squeeze, Insider Buying 등)에서 대다수 종목이 0점인 경우를 중립 0.50으로 처리하는 보호 로직에 `n_valid >= 10` 조건이 걸려 있음. 섹터별 유니버스가 5~9개일 때 0점인 종목들이 0.05~0.20의 인위적 약세 랭크를 받게 됨.
- **개선안**: `n_valid >= 4`로 임계치를 완화하여 소형 유니버스에서도 비활성 종목의 중립성 보장.

#### 12. [MEDIUM-04] 미시구조 거래비용 모델 내 일평균 거래대금(`turnover`) 중복 산출
- **파일**: `trading_system/src/ai/ensemble_scorer.py` (Line 2809-2811, 2985-2987)
- **현황**: `turnover = vol_col * close_col` 계산이 약 170라인 간격으로 2회 중복 수행되며, 전자는 `close`만 보고 후자는 `close_price`까지 확인하는 사소한 로직 분기가 존재함.
- **개선안**: 상단에서 일원화하여 1회만 계산하고 불필요한 DataFrame 접근 제거.

---

## 4. Quantitative Engineering Improvement Plan (단계별 실행 계획)

### Phase 1: 치명적 런타임 결함 수정 (Critical Fixes, Day 1)
1. **C-01 수정**: `ensemble_scorer.py`에서 `scores_df.corr(min_periods=5)`를 사용하여 결측치가 있어도 상관 직교화 페널티가 정상 동작하도록 수정.
2. **C-02 수정**: `ml_strategy_adapters.py`에서 `DarkPoolStrategyAdapter`가 올바르게 `DarkPoolTrackerEngine`을 호출하도록 클래스 바인딩 교정.
3. **C-03 수정**: `factor_orthogonalizer.py`의 `_pca_zca_symmetric()`에서 $\lambda_{\max}$ 필터를 1.0으로 고정하고 상태수 상한(10.0)을 적용하여 컨센서스 알파 보존.

### Phase 2: 가중치 및 신호 정규화 무결성 강화 (High-Priority Fixes, Day 2)
1. **H-01 수정**: `factor_suppression.py`의 `CLUSTER_MAP`에 전략 35, 36, 37번 클러스터 등록.
2. **H-02 수정**: `ensemble_scorer.py`의 `_calc_tier_score`에 전략별 동적 가중치 반영.
3. **H-03 수정**: `ensemble_scorer.py`에 유효 가중치 커버리지 기반 Bayesian Shrinkage 도입.
4. **H-04 수정**: `ensemble_scorer.py`에서 미국 주식 식별 정규표현식 수정.
5. **H-05 수정**: `short_interest_squeeze.py`에서 데이터 부재 시 일관되게 `np.nan` 반환.

### Phase 3: 분석 리포팅 및 메타데이터 정합성 보정 (Medium Fixes, Day 3)
1. **M-01 수정**: `coverage_analyzer.py`에 전략 32~37번 결측 사유 매핑 추가.
2. **M-02 수정**: 전략 엔진들의 `StrategyMeta` 속성 및 기본 가중치 통일.
3. **M-03 수정**: `score_normalizer.py`의 제로 블록 격리 유니버스 최소 크기 완화($N \ge 4$).
4. **M-04 수정**: `ensemble_scorer.py`의 거래대금 중복 연산 정리.

---

## 5. Verification Method & Test Suite Design

- **단위 테스트**:
  - `tests/test_factor_orthogonalizer.py`: ZCA 백색화 시 PC1 컨센서스 보존율 $\ge 90\%$, 상태수 $\kappa \le 10$ 검증.
  - `tests/test_ensemble_scorer_coverage.py`: 전략 1개만 채워진 종목의 앙상블 점수가 중립(0.50)으로 적절히 수축되는지 검증.
  - `tests/test_strategy_darkpool_adapter.py`: 어댑터 호출 시 호가 불균형 엔진이 아닌 다크풀 엔진이 작동하는지 검증.
- **통합 테스트**:
  - `pytest tests/test_score_normalizer.py tests/test_factor_suppression.py -v`
  - 전체 파이프라인 시뮬레이션: 5대 시장 100종목 가상 데이터셋에서 37개 전략 점수 산출 $\rightarrow$ 횡단면 정규화 $\rightarrow$ 2D 레짐 앙상블 $\rightarrow$ 거래비용 차감의 전 과정 무결성 통과 확인.
