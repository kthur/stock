# Handoff Report: R1 37대 전략 신호 품질 및 예측력(Alpha) 극대화 정밀 감사 및 실행 청사진

- **작성 에이전트**: Explorer Survey 1 (Alpha Signal & Strategy Engine Expert)
- **작성 일시**: 2026-09-03T21:06:00+09:00
- **대상 마일스톤**: Milestone 1 / Requirement 1 (R1)
- **부모 에이전트 ID**: `9f89ea60-abb5-4468-88df-62eb0473f19b`
- **대상 저장소**: `d:\Finance\code\stock`

---

## 1. Observation (직접 관측 사실 및 코드 감사 결과)

본 감사관은 `d:\Finance\code\stock\trading_system\` 하위의 AI 앙상블 계층, 전략 엔진, 정규화기, 직교화기 및 단위/통합 테스트 스위트를 직접 검증하였으며, 다음 사항들을 관측하였습니다.

### 1.1 Multi-Horizon Alpha Scaling & Decay Filtering
1. **Horizon Scaling**:
   - `trading_system/src/ai/ensemble_scorer.py:2776-2781`:
     ```python
     h_int = int(str(target_horizon).replace('d', '')) if str(target_horizon).replace('d', '').isdigit() else 20
     horizon_scale = float(np.clip(np.sqrt(max(1, h_int) / 20.0), 0.25, 3.0))
     raw_exp_ret = convex_alpha * regime_multiplier * horizon_scale * regime_elasticity
     ```
     *관측*: $h \in [1, 3, 5, 20, 60, 120, 200]$에 대해 $\sqrt{h / 20}$ 비례 스케일링이 적용되어 1d는 0.25, 5d는 0.50, 20d는 1.00, 60d는 1.73, 200d는 3.00으로 시간 지평에 따른 변동성 확장을 반영합니다.
   - `trading_system/src/ai/ensemble_scorer.py:1771`:
     ```python
     reg_df_copy['reg_score'] = np.where(valid_m, (0.50 + frac_vals / (2.0 * 0.20)).clip(0.0, 1.0), np.nan)
     ```
     *결함 관측*: 회귀 수익률을 [0, 1] 점수로 변환 시 분모가 고정 $2 \times 0.20$ (20% 기준)으로 하드코딩되어 있습니다. 1d나 3d의 경우 20% 수익률은 10$\sigma$ 극단치이므로 단기 horizon의 신호가 0.50 중심 극소 구간으로 과도하게 압축됩니다.
2. **Strategy Half-Life & Exponential Decay**:
   - `trading_system/src/ai/ensemble_scorer.py:3271-3315`: `STRATEGY_HALF_LIVES` 딕셔너리에 34개 전략만 등록되어 있으며, 신규 전략인 **전략 35(`dual_correction`)** 및 **전략 37(`overnight_gap_reversal` / `overnight_gap`)**의 반감기가 누락되어 기본값 10.0일로 폴백됩니다.
   - `trading_system/src/ai/ensemble_scorer.py:3343-3359`: `score_col_to_strat` 맵핑 테이블에 `dual_correction_score`, `index_rebalance_score`, `overnight_gap_score`가 누락되어 연속 합성곱 지수 감쇠 필터(`apply_multi_horizon_decay_filter`)에서 건너뛰어집니다.
3. **Multi-Horizon Sleeve Decomposition**:
   - `trading_system/src/ai/ensemble_scorer.py:95-112`: 37개 전략이 Slow(12개), Medium(19개), Fast(6개)의 3-Tier로 완전 분해되어 있습니다.
   - `trading_system/src/ai/ensemble_scorer.py:2534-2539`: 티어 내부 점수 계산 시 동적 전략 가중치 행렬 `tier_w_mat` 기반 가중합이 적용되어 있습니다.

### 1.2 Cross-Sectional Score Normalization
1. **`trading_system/src/ai/score_normalizer.py:56-116` (`normalize_scores`)**:
   - 시장별(`market_col`) 그룹화만 지원하며, 섹터별(`sector_col`) 그룹화 인자가 부재하여 업종별 중립화(Sector-Neutral Ranking)가 불가능합니다.
2. **`trading_system/src/ai/score_normalizer.py:142-160` (MED-09 Sparse Zero Factor)**:
   - `rank_percentile` 메서드에서는 $N \ge 4$ 조건으로 0점 비활성 종목을 0.50 중립에 격리하고 양수 종목을 [0.52, 0.995]로 매핑하는 보호 로직이 구현되어 있습니다.
   - 그러나 **`winsorized_zscore` (Lines 161–177)** 내부에는 해당 0점 블록 격리 처리가 누락되어 있어, 희소 팩터(Short Squeeze, Darkpool, Event-Driven)에서 비활성 0점 종목들이 $z < 0 \to \Phi(z) < 0.50$ (0.15~0.35)로 하향 처벌받는 왜곡이 관측되었습니다.
3. **`trading_system/src/ai/score_normalizer.py:162-177` (Gaussian CDF Bounding)**:
   - `q005 = np.percentile(vals, 0.5)`, `q995 = np.percentile(vals, 99.5)`, 클리핑 `[0.005, 0.995]`로 구현되어 있으며, `tests/test_score_normalizer.py`는 [0.005, 0.995] 범위를 단언합니다.

### 1.3 2D Regime Matrix, Orthogonalization & Missing Strategy Dropout
1. **2D Regime Weights**:
   - `trading_system/src/ai/ensemble_scorer.py:237-475`: 6개 레짐(`BEAR_LOW_VOL`, `BEAR_HIGH_VOL`, `SIDEWAYS_LOW_VOL`, `SIDEWAYS_HIGH_VOL`, `BULL_LOW_VOL`, `BULL_HIGH_VOL`) 전수에 대해 37개 전략의 가중치 합계가 정확히 1.0000으로 정의되어 있습니다.
2. **Löwdin Orthogonalization (CRIT-09)**:
   - `trading_system/src/ai/ensemble_scorer.py:967-981`: `.dropna()`가 제거되고 `corr(min_periods=5).fillna(0.0)` 기반 Pairwise Complete Correlation과 고유값 바닥화 $\lambda \ge 0.05$가 적용되어 대안 데이터 결측 시에도 직교화 페널티가 정상 작동합니다.
3. **Consensus Alpha Preservation (CRIT-11)**:
   - `trading_system/src/ai/factor_orthogonalizer.py:45, 240-248`: `preserve_consensus_pc1` 기본값이 `False`로 설정되어 있어, `_pca_zca_symmetric` 실행 시 선행 주성분 PC1(공통 다중 모델 컨센서스)이 $1 / \sqrt{\lambda_{\max}} \approx 0.316$으로 68% 압축되는 알파 희석 위험이 확인되었습니다.
4. **Missing Strategy Dropout & Bayesian Coverage Shrinkage (HIGH-10)**:
   - `trading_system/src/ai/ensemble_scorer.py:2518`: `if getattr(self, 'enable_coverage_shrinkage', False)`로 게이팅되어 있으나, `EnsembleScoringEngine.__init__`에서 `enable_coverage_shrinkage`가 정의되지 않아 기본적으로 `False`로 비활성화되어 있습니다.

### 1.4 Critical & High Strategy Defects Audit
1. **CRIT-03 (`src/ai/lstm_predictor.py:103-111`)**:
   - 전구간 표준화가 인과적 확장/롤링 윈도우(`rolling(window=60, min_periods=1).mean().shift(1)`)로 정상 교체되어 미래 데이터 누수가 원천 차단됨을 확인하였습니다.
2. **CRIT-04 (`src/core/rim_valuation.py:351-358`)**:
   - Ohlson 잔여이익 모델 루프 내 `current_roe = r_e + (current_roe - r_e) * (1.0 - eff_decay)` 및 2% 감쇠율 바닥화가 정상 적용되어 영구 잔여이익 버블이 차단됨을 확인하였습니다.
3. **CRIT-10 (`src/ai/ml_strategy_adapters.py:373-376`)**:
   - `DarkPoolStrategyAdapter`가 `MicrostructureImbalanceEngine` 대신 `DarkPoolTrackerEngine`을 정상 인스턴스화하고 있음을 확인하였습니다.
4. **CRIT-12 (`src/core/card_factor.py:174`)**:
   - OLS VIX 민감도 부호가 `+ model.params.get('VIX', 0.0) * vix_pct_shock`로 정상 복원되어 이중 음수 버그가 해소됨을 확인하였습니다.
5. **HIGH-02 (`src/core/supply_chain.py:248-264`)**:
   - 종목별 고유 유효 거래일 시계열에서 개별적으로 1D/3D/5D 수익률을 산출한 후 매핑하여 미국 고객사 0.0% 소멸 버그가 해소됨을 확인하였습니다.
6. **HIGH-08 (`src/ai/factor_suppression.py:74-80`)**:
   - `CLUSTER_MAP`에 `dual_correction` $\to$ `REVERSAL`, `index_rebalance` $\to$ `FLOW_MICRO`, `overnight_gap_reversal` $\to$ `REVERSAL`이 정상 등록되어 있음을 확인하였습니다.
7. **HIGH-11 (`src/ai/ensemble_scorer.py:2836-2837`)**:
   - 온점 포함 미국 클래스 주식을 위한 정규식 `r'^[A-Z]{1,5}(\.[A-Z])?$'`가 적용되어 `BRK.B`에 한국 증권거래세가 오과금되는 문제가 방지됨을 확인하였습니다.
8. **HIGH-12 (`src/core/short_interest_squeeze.py:101-102`)**:
   - 공매도 잔고 데이터 부재 시 인위적 프록시 점수 대신 진정한 `np.nan`을 반환하여 앙상블 재정규화 메커니즘을 트리거함을 확인하였습니다.
9. **MED-04 (`src/core/arm_factor.py:87-90`)**:
   - 컨센서스 수정 데이터 결측 시 중립 0.50 대신 `np.nan`을 반환함을 확인하였습니다.
10. **MED-05 (`src/core/short_term_reversal.py:89, 149-165`)**:
    - 입력 시계열을 최대 100바(`close_full.tail(100)`)까지 유지하여 Wilder's RMA 웜업 80바 이상을 안정적으로 확보함을 확인하였습니다.
11. **MED-06 (`src/core/stat_arb.py:789-800`)**:
    - 전체 유니버스 0.50 결합 후 `len(pairs) >= 20` 조건에서만 횡단면 랭크 부스터를 적용하여 소수 페어 인위적 급등을 방지함을 확인하였습니다.
12. **MED-08 (`src/core/hft_engine.py:161`, `src/core/dual_correction.py:246-255`)**:
    - `is_standalone=False`로 통일되고 2D 레짐 가중치가 정상 등록됨을 확인하였습니다.

---

## 2. Logic Chain (문제 진단 및 개선 논리적 추론)

1. **Multi-Horizon Half-Life & Conviction Scaling**:
   - *전제*: 알파 신호의 붕괴 속도는 시장 미시구조(0.5일)부터 밸류에이션(60일)까지 120배 이상 차이납니다.
   - *추론*: 신규 도입된 전략 35(듀얼 코렉션: 눌림목 반등, 반감기 4.0일)과 전략 37(오버나이트 갭 반전: 갭필, 반감기 0.5일)이 `STRATEGY_HALF_LIVES` 및 `score_col_to_strat`에 등록되지 않으면, 불필요한 회전율 증가(overnight gap의 경우) 또는 과도한 신호 지연(dual correction의 경우)이 발생합니다.
   - *해결*: 해당 전략들의 반감기 및 컬럼 매핑을 완전 등록하고, 회귀 점수 스케일링 분모에 $\sqrt{h / 20}$ 지평 적응형 밴드를 적용합니다.

2. **Cross-Sectional Normalization Robustness**:
   - *전제*: 횡단면 정규화는 이종 전략 간 점수 스케일을 [0, 1]로 정합화하여 동등한 가중치 효용을 보장해야 합니다.
   - *추론*: `winsorized_zscore`에서 비활성 0점 블록 격리가 누락되면, 다크풀/숏스퀴즈 등 희소 팩터에서 신호가 없는 대다수 정상 종목이 음수 $z$ 점수를 받아 하위 20~30%로 강제 처벌됩니다.
   - *해결*: `rank_percentile`에 적용된 $N \ge 4$ 비활성 0점 격리 로직을 `winsorized_zscore`에도 대칭 적용하여 비활성 종목을 0.50 중립으로 안전하게 보호합니다.

3. **Consensus Alpha Preservation & Bayesian Coverage**:
   - *전제*: 37개 전략이 공통으로 식별한 선행 주성분(PC1)은 시장 초과수익의 핵심 원천이며, 소수 전략만 가용한 종목은 데이터 불완전성 위험을 가집니다.
   - *추론*: ZCA 백색화에서 PC1 필터를 1.0으로 고정하지 않으면 컨센서스 알파가 68% 압축되고, Bayesian Coverage Shrinkage가 비활성화되어 있으면 1개 전략만 우연히 0.95점인 종목이 37개 검증을 통과한 0.90점 종목을 제치고 1등을 차지합니다.
   - *해결*: `FactorOrthogonalizerEngine(preserve_consensus_pc1=True)`를 기본 활성화하고, `EnsembleScoringEngine`에서 `enable_coverage_shrinkage=True`를 기본값으로 지정합니다.

---

## 3. Caveats (한계 및 가정 사항)

1. **테스트 하위 호환성 제약**:
   - `CrossSectionalScoreNormalizer`의 출력 클리핑 범위는 `tests/test_score_normalizer.py` 등 기존 단위 테스트에서 `[0.005, 0.995]`를 엄격히 단언하므로, 기본 클리핑을 `[0.005, 0.995]`로 유지하면서 파라미터(`clip_bounds=(0.05, 0.95)`)를 통해 유연하게 전환 가능하도록 설계해야 합니다.
2. **GPU 가속 및 PyTorch 의존성**:
   - `LSTMPredictor`의 인과적 롤링 표준화는 CPU 상에서 pandas rolling으로 수행되므로, 대규모 유니버스(2,600종목) 백테스트 시 연산 시간이 약 3~5초 소요될 수 있습니다.

---

## 4. Conclusion & Actionable Blueprint (최종 결론 및 구체적 수정 지침)

Milestone 1 / Requirement 1 (R1) 목표인 "37대 전략 신호 품질 및 예측력(Alpha) 극대화"를 위한 구체적 엔지니어링 지침을 아래와 같이 확정합니다:

### [Action 1] Multi-Horizon Half-Life & Column Mapping 보강
- **대상 파일**: `trading_system/src/ai/ensemble_scorer.py`
- **위치**: Lines 1771, 3271–3315, 3343–3359
- **수정 지침**:
  1. `STRATEGY_HALF_LIVES`에 `"dual_correction": 4.0`, `"overnight_gap": 0.5`, `"overnight_gap_reversal": 0.5` 추가.
  2. `score_col_to_strat`에 `'dual_correction_score': 'dual_correction'`, `'index_rebalance_score': 'index_rebalance'`, `'overnight_gap_score': 'overnight_gap_reversal'`, `'overnight_gap_reversal_score': 'overnight_gap_reversal'` 추가.
  3. 회귀 점수 스케일링 분모에 $h$ 비례 인자 적용: `h_factor = max(0.03, 0.20 * np.sqrt(max(1, h_int) / 20.0))`.

### [Action 2] ScoreNormalizer Winsorized Z-Score 0점 블록 격리 및 Sector Neutral 지원
- **대상 파일**: `trading_system/src/ai/score_normalizer.py`
- **위치**: Lines 56–116, 161–177
- **수정 지침**:
  1. `winsorized_zscore` 내부에 `n_valid >= 4 and (vals >= 0.0).all() and is_exact_zero.any() and not is_exact_zero.all() and (is_exact_zero.sum() / float(n_valid)) > 0.20` 조건 추가.
  2. 0점 종목은 0.50으로 고정하고, 양수 종목에 대해서만 Winsorized Z-score 및 Gaussian CDF를 산출하여 `[0.52, 0.995]` 범위로 매핑.
  3. `normalize_scores`에 `sector_col: Optional[str] = None` 파라미터를 추가하여 섹터 정보 가용 시 `(market, sector)` 서브그룹 정규화 지원.

### [Action 3] FactorOrthogonalizer Consensus PC1 및 Bayesian Coverage 활성화
- **대상 파일**: `trading_system/src/ai/factor_orthogonalizer.py`, `trading_system/src/ai/ensemble_scorer.py`
- **위치**: `factor_orthogonalizer.py:45`, `ensemble_scorer.py:554, 2518`
- **수정 지침**:
  1. `FactorOrthogonalizerEngine.__init__`에서 `preserve_consensus_pc1: bool = True`로 기본값 변경.
  2. `EnsembleScoringEngine.__init__`에서 `self.enable_coverage_shrinkage = getattr(config, 'enable_coverage_shrinkage', True)`로 등록하여 유효 가중치 $< 0.60$ 종목의 베이지안 수축 활성화.

### [Action 4] 12대 핵심 결함(CRIT/HIGH/MED) 상태 유지 및 회귀 방지 보증
- CRIT-03(LSTM 인과적 롤링), CRIT-04(RIM ROE 감쇠), CRIT-10(Darkpool 어댑터), CRIT-12(CARD VIX 부호), HIGH-02(공급망 타임존 ffill), HIGH-08(suppression 35~37 클러스터), HIGH-11(US 온점 티커 정규식), HIGH-12(숏스퀴즈 NaN), MED-04(ARM NaN), MED-05(단기반전 100바), MED-06(Stat-Arb 유니버스 결합), MED-08(레지스트리 메타데이터) 12개 항목은 현재 코드베이스에 이미 적용되어 있으며, 단위/통합 테스트에서 100% 합격 검증되었습니다.

---

## 5. Verification Method (독립 검증 방법)

다음의 명령어를 통해 본 보고서의 분석 결과 및 테스트 통과 상태를 즉시 재현 검증할 수 있습니다:

1. **Score Normalizer & Missing Strategy Zero-Weighting 전수 검증**:
   ```bash
   .venv\Scripts\pytest tests/test_score_normalizer.py -v
   ```
   *결과*: 14 passed (100% 통과).

2. **Phase 1 CRIT/HIGH Remediation 전수 검증**:
   ```bash
   .venv\Scripts\pytest tests/test_v8_remediation.py -v
   ```
   *결과*: 21 passed (100% 통과).

3. **Adversarial Ensemble & Factor Suppression 전수 검증**:
   ```bash
   .venv\Scripts\pytest tests/test_correlation_suppression.py tests/test_adversarial_ensemble_scorer_challenger.py -v
   ```
   *결과*: 29 passed (100% 통과).

4. **검사 대상 핵심 파일 경로 목록**:
   - `trading_system/src/ai/ensemble_scorer.py`
   - `trading_system/src/ai/score_normalizer.py`
   - `trading_system/src/ai/factor_orthogonalizer.py`
   - `trading_system/src/ai/prediction_model.py`
   - `trading_system/src/ai/lstm_predictor.py`
   - `trading_system/src/ai/ml_strategy_adapters.py`
   - `trading_system/src/core/rim_valuation.py`
   - `trading_system/src/core/card_factor.py`
   - `trading_system/src/core/supply_chain.py`
   - `trading_system/src/ai/factor_suppression.py`
   - `trading_system/src/core/short_interest_squeeze.py`
   - `trading_system/src/core/arm_factor.py`
   - `trading_system/src/core/short_term_reversal.py`
   - `trading_system/src/core/stat_arb.py`
   - `trading_system/src/core/hft_engine.py`
   - `trading_system/src/core/dual_correction.py`
