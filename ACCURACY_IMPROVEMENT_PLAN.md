# 예측 정확성 향상 제안서

> 작성일: 2026-07-13  
> 대상 시스템: 통합 주식 자동매매 예측 파이프라인 (3,379 종목 / 5전략)  
> 분석 기준 파일: `trading_system/src/ai/prediction_model.py`, `vcp_ml_predictor.py`, `run_pipeline.py`

현재 파이프라인 코드를 면밀히 분석한 결과를 기반으로, 각 레이어별 개선 방안을 정리합니다.

---

## 🏆 개선 효과 기대 순위

| 순위 | 개선 항목 | 예상 개선 효과 | 구현 난이도 |
|------|-----------|----------------|-------------|
| 1 | 타겟 레이블 품질 개선 (위험조정 수익률) | ★★★★★ | 낮음 |
| 2 | Walk-Forward 검증 도입 | ★★★★★ | 중간 |
| 3 | Surge 분류 임계값 최적화 | ★★★★☆ | 낮음 |
| 4 | 거래량 품질 기반 데이터 필터링 | ★★★★☆ | 낮음 |
| 5 | 신규 피처 추가 (모멘텀 복합) | ★★★☆☆ | 중간 |
| 6 | 앙상블 스태킹 Blender 개선 | ★★★☆☆ | 중간 |
| 7 | 마켓 레짐 조건부 가중치 | ★★★☆☆ | 중간 |
| 8 | SMOTE 클래스 불균형 보정 | ★★☆☆☆ | 낮음 |

---

## 1. 타겟 레이블 품질 개선 ⚡ 최고 우선순위

### 현재 문제
`target_{h}d` = `Close(t+h) / Close(t) - 1`  
단순 raw return은 변동성 차이가 큰 종목(KONEX vs SP500)을 왜곡합니다.

### 개선안 A: 위험조정 수익률 (Sharpe-scaled Return)
```python
# 현재
target = close.shift(-h) / close - 1

# 개선: 20일 변동성으로 정규화
vol = close.pct_change().rolling(20).std()
raw_ret = close.shift(-h) / close - 1
target = raw_ret / (vol + 1e-8)  # Sharpe-scaled
```
**효과**: 시장 간(KOSPI vs SP500) 수익률 스케일 차이가 제거되어 크로스-마켓 학습 품질 향상.

### 개선안 B: 벤치마크 초과 수익률 (Excess Return)
```python
# 마켓 인덱스 수익률 대비 초과분만 학습
market_ret = kospi_index.shift(-h) / kospi_index - 1  # or sp500
target_excess = raw_ret - market_ret
```
**효과**: 알파(시장 초과 수익) 생성 종목을 정밀하게 식별.

**수정 위치**: `trading_system/src/ai/prediction_model.py` → `train()` 메서드 내 타겟 계산 부분

---

## 2. Walk-Forward 교차검증 도입 ⚡ 최고 우선순위

### 현재 문제
`prediction_model.py L1268-1279`: 현재는 **단일** 80/20 시분할 검증만 수행합니다.  
단일 검증은 특정 시기에 의존하는 과적합을 감지하지 못합니다.

### 개선안: Walk-Forward 검증 (Expanding Window)
```python
from sklearn.model_selection import TimeSeriesSplit

def train_with_walkforward(df_train, features, target_col, n_splits=5):
    dates = pd.to_datetime(df_train['date'])
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=20)  # 20일 누출 방지 gap

    fold_metrics = []
    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df_train)):
        X_train = df_train.iloc[train_idx][features]
        y_train = df_train.iloc[train_idx][target_col]
        X_val = df_train.iloc[val_idx][features]
        y_val = df_train.iloc[val_idx][target_col]

        model = xgb.XGBRegressor(...)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)])

        fold_metrics.append(compute_metrics(model, X_val, y_val))

    return np.mean(fold_metrics)  # 평균 성능을 신뢰도 지표로 활용
```
**효과**: 특정 시기 의존 과적합 탐지. 앙상블 가중치 계산의 신뢰도 대폭 향상.

**수정 위치**: `prediction_model.py` → `train()`, `train_surge()` 메서드

---

## 3. Surge 분류 임계값 최적화

### 현재 문제
`prediction_model.py L1511`: `surge_threshold=0.20` (20%)는 모든 시장/horizons에 동일하게 적용됩니다.

| 마켓 | 1일 20% 발생 빈도 | 20일 20% 발생 빈도 |
|------|-------------------|---------------------|
| SP500 | ~0.01% | ~8% |
| KOSPI | ~0.5% | ~15% |
| KONEX | ~5% | ~35% |

→ KONEX에서는 20%가 너무 낮아 라벨이 과다 생성되고, SP500에서는 너무 높아 라벨이 극도로 희소해집니다.

### 개선안: 시장/Horizon별 동적 임계값
```python
def compute_dynamic_threshold(returns_series, target_positive_rate=0.10):
    """라벨 비율이 target_positive_rate에 근접하도록 임계값 자동 계산"""
    return float(np.percentile(returns_series, (1 - target_positive_rate) * 100))

# 적용 예시
for h in surge_horizons:
    for mkt in markets:
        mkt_returns = df_train.loc[df_train['market'] == mkt, f'target_{h}d']
        threshold = compute_dynamic_threshold(mkt_returns, target_positive_rate=0.10)
        target = (mkt_returns >= threshold).astype(int)
```
**효과**: KONEX 소형주와 SP500 대형주가 동등하게 학습됨. `scale_pos_weight` 값이 안정화되어 과도한 가중치(500 cap) 문제 해결.

**수정 위치**: `prediction_model.py` → `train_surge()` 메서드 / `vcp_ml_predictor.py` → `train()` 메서드

---

## 4. 학습 데이터 품질 필터링

### 현재 문제
거래정지 종목(Volume=0), 관리종목, 극단적 이상치가 학습 데이터에 포함되어 노이즈를 발생시킵니다.

### 개선안: 훈련 데이터 품질 사전 필터
```python
def filter_training_data(df_train: pd.DataFrame) -> pd.DataFrame:
    """Low-quality rows 제거"""
    # 1. 거래정지 / 거래량 이상치 제거
    df = df_train[df_train['norm_volume'] > 0].copy()

    # 2. 가격 이상치 제거 (4 sigma rule)
    for col in ['ret_1d', 'ret_5d']:
        mu, sigma = df[col].mean(), df[col].std()
        df = df[(df[col] - mu).abs() < 4 * sigma]

    # 3. 최소 거래 기록 조건 (100일 미만 종목 제외)
    count_by_sym = df.groupby('symbol')['date'].count()
    valid_syms = count_by_sym[count_by_sym >= 100].index
    df = df[df['symbol'].isin(valid_syms)]

    logger.info(f"Data filtered: {len(df_train)} -> {len(df)} rows")
    return df
```
**효과**: KONEX 관리종목 노이즈가 KRX 모델 학습을 오염시키는 현상 방지.

**수정 위치**: `run_pipeline.py` → 학습 데이터 준비 단계 (`prepare_training_data()`)

---

## 5. 신규 피처 추가

### 현재 피처 갭 분석
현재 `ALL_FEATURES` (50개)는 기술적 지표 위주입니다. 다음 피처들이 누락되어 있습니다:

### 개선안 A: 상대 강도 피처 (Cross-Asset Momentum)
```python
def compute_sector_relative_strength(prices_df: pd.DataFrame) -> pd.Series:
    """종목 수익률 - 업종 평균 수익률"""
    sector_ret = prices_df.groupby('sector')['ret_20d'].transform('mean')
    return prices_df['ret_20d'] - sector_ret

# 추가할 피처 목록
features_to_add = [
    'sector_relative_strength',  # 업종 대비 상대 강도
    'market_relative_strength',  # 시장 전체 대비 상대 강도
    '52w_high_breakout',         # 52주 신고가 돌파 여부 (0/1)
    'vol_trend_slope',           # 거래량 추세 기울기 (20일 선형 회귀)
]
```

### 개선안 B: 마켓 레짐 피처
```python
def compute_regime_features(indicator_df):
    return {
        'vix_level': indicator_df['vix'],                          # 변동성 절대 수준
        'vix_regime': (indicator_df['vix'] > 25).astype(int),     # 고변동성 레짐 (0/1)
        'yield_curve': indicator_df['us10y'] - indicator_df.get('us2y', 0),  # 장단기 금리차
        'market_breadth': ...,                                     # 상승/하락 종목 비율
    }
```
**효과**: 고변동성 레짐에서의 모델 행동을 명시적으로 학습하여 시장 상황에 따른 예측 적응력 향상.

**수정 위치**: `trading_system/src/ai/feature_engineering.py` → 피처 계산 함수 추가

---

## 6. 앙상블 스태킹 Blender 개선

### 현재 방식
`prediction_model.py L1421-1430`: `1/MSE` 비례 가중치.  
단순하지만 모델 간 **상관관계(Correlation)를 무시**합니다. 두 모델이 동일한 오류를 범하는 경우에도 동등한 가중치를 부여합니다.

### 개선안: Stacking Blender (2단계 앙상블)
```python
from sklearn.linear_model import RidgeCV

def train_stacking_blender(X_val, y_val, model_xgb, model_lgb, model_cat):
    """1단계 모델 예측값을 피처로 사용해 2단계 블렌더 학습"""
    # 1단계 예측 스택
    pred_stack = np.column_stack([
        model_xgb.predict(X_val),
        model_lgb.predict(X_val),
        model_cat.predict(X_val),
    ])

    # 2단계: Ridge 블렌더 (L2 규제로 과적합 방지)
    blender = RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0])
    blender.fit(pred_stack, y_val)

    # 블렌더 계수를 가중치로 변환 (음수 방지)
    weights = np.maximum(blender.coef_, 0)
    weights /= weights.sum()
    return weights  # [w_xgb, w_lgb, w_cat]
```
**효과**: 성능이 낮은 모델에 음수 가중치 부여 방지 + 실제 검증 데이터 기반 최적 가중치 산출.

**수정 위치**: `prediction_model.py` → `train()`, `train_surge()` 끝단의 가중치 계산 블록

---

## 7. 마켓 레짐 조건부 가중치

### 개선안: VIX 수준에 따른 동적 앙상블 가중치
```python
def get_regime_adjusted_weights(vix_level: float, base_weights: dict) -> dict:
    """VIX 수준에 따라 보수적/공격적 모델 가중치 조정"""
    if vix_level > 30:      # 고변동성 레짐 (위험 회피)
        return {"xgb": 0.25, "lgb": 0.25, "cat": 0.50}
    elif vix_level < 15:    # 저변동성 레짐 (위험 선호)
        return {"xgb": 0.30, "lgb": 0.30, "cat": 0.20, "lstm": 0.20}
    else:                   # 중립 레짐
        return base_weights
```
**효과**: VIX 30 이상 급등 국면에서 CatBoost의 안정적인 트리 기반 예측을 우선함으로써 급락장 오예측 감소.

**수정 위치**: `prediction_model.py` → `_predict_regression()`, `_predict_surge()` 내부 가중치 조회 블록

---

## 8. SMOTE 클래스 불균형 보정

### 현재 문제
`prediction_model.py L1519`: `scale_pos_weight = min(neg_count/pos_count, 500)`.  
극단적인 클래스 불균형에서 scale weight 조정만으로는 한계가 있습니다.

### 개선안: SMOTE 합성 오버샘플링
```bash
pip install imbalanced-learn
```
```python
from imblearn.over_sampling import SMOTE

def apply_smote(X_train, y_train, max_ratio=5.0):
    """과소 클래스(Surge=1)를 합성하여 최대 5:1 비율까지 보정"""
    pos = y_train.sum()
    neg = len(y_train) - pos

    if neg / max(pos, 1) <= max_ratio:
        return X_train, y_train  # 비율이 적절하면 스킵

    target_ratio = {1: int(neg / max_ratio)}
    smote = SMOTE(sampling_strategy=target_ratio, random_state=42)
    return smote.fit_resample(X_train, y_train)
```
**효과**: KONEX 같은 데이터 희소 마켓에서 surge 클래스를 균형 있게 보강하여 recall 향상.

**수정 위치**: `prediction_model.py` → `train_surge()` / `vcp_ml_predictor.py` → `train()` 메서드

---

## 📋 구현 우선순위 로드맵

```
단기 (1~2주) — 낮은 구현 비용, 높은 효과:
├── ① Surge 임계값 동적 최적화 (market × horizon별)
├── ② 학습 데이터 품질 필터 (거래정지/이상치 제거)
└── ③ 위험조정 타겟 레이블 도입 (변동성 정규화)

중기 (3~4주) — 중간 구현 비용:
├── ④ Walk-Forward 검증 도입 (TimeSeriesSplit n=5)
├── ⑤ 섹터 상대 강도 피처 추가
└── ⑥ 스태킹 블렌더 교체

장기 (5~8주) — 높은 구현 비용, 구조 변경 포함:
├── ⑦ 마켓 레짐 조건부 가중치
└── ⑧ SMOTE 클래스 불균형 보정
```

> **가장 빠른 효과를 원한다면** ①(동적 임계값) → ②(데이터 필터링) → ③(위험조정 타겟) 순서로 적용하세요.  
> 코드 변경이 적고 파이프라인 재학습만으로 즉시 효과를 볼 수 있습니다.
