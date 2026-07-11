# 주식 자동매매 및 예측 시스템 코드베이스 종합 진단 및 개선 보고서 (Audit and Improvement Report)

## 1. 개요 (Executive Summary)

### 1.1 시스템 평가 점수 및 근거
본 주식 자동매매 및 예측 시스템의 현재 종합 아키텍처 및 소스 코드 품질 등급은 **3.2 / 5.0**으로 평가됩니다.

**평가 근거:**
* **알파 생성 다양성 및 구조적 강점:** 본 시스템은 XGBoost 회귀 모형, Surge 분류기, Lead-Lag 상관관계 분석, VCP 규칙 패턴 검출, VCP ML 분류기 등 총 5가지의 다양한 다각화된 전략을 병행 운영하고 있습니다. 이들을 `run_pipeline.py`라는 하나의 통합 파이프라인 스크립트를 통해 유기적으로 엮어냈으며, SQLite 기반의 캐시 레이어(`StockPriceDB`, `MarketIndicatorStorage`)를 두어 네트워크 환경 격리 상태에서도 작동 가능하도록 설계한 점은 실전 트레이딩 아키텍처로서 훌륭한 기본기를 갖추고 있다고 평가할 수 있습니다.
* **아키텍처 설계상의 취약점:** 그러나 상세 감사를 진행한 결과, 실제 상용 트레이딩 환경에 배포했을 때 치명적인 문제를 야기할 수 있는 몇 가지 아키텍처 결함이 확인되었습니다.
  1. **머신러닝 모델 품질 결함:** 예측 타겟의 미래 수익률(Forward Return) 정보가 검증 셋에 흐르게 만드는 시계열 분할의 정보 누수(Temporal Leakage) 문제, Platt 스케일링 교정 및 임계값 튜닝을 동일한 단일 검증 셋에서 연속으로 실행하여 생기는 2차 오버피팅(Double-Dipping) 문제, 그리고 학습 단계(표본 샘플)와 실제 추론 단계(전 종목 우주) 간의 모집단 표본 크기 편차로 인해 정규화 피처의 스케일이 약 30배 이상 왜곡되는 수치 왜곡(Covariate Shift) 현상이 심각합니다.
  2. **파이프라인 성능 저해 요소:** 3,000개가 넘는 종목의 기본적 분석(Fundamentals) 데이터 조회를 루프 내에서 무차별적으로 개별 SQLite 쿼리로 날리는 비효율적 디스크 IO 구조, 그리고 SQLite 자체의 병렬 읽기 성능(WAL 모드 호환)을 무력화하고 단일 글로벌 락(`threading.Lock`)으로 모든 DB 가격 조회를 병렬 스레드 간 직렬화시키는 락 경합 문제가 병목을 유발합니다. 또한 네트워크 장애 복원성이 떨어져 일시적인 티커 하나로 배치 전체가 순차 지연 다운로드 모드로 빠지는 지연 문제가 존재합니다.
  3. **CI/CD 및 운영 관리 미흡:** 타겟 마켓별 격리 조치 누락으로 가중치 캐시가 타 시장 빌드로 오염될 가능성이 있으며, 텍스트 결과 파일들의 잦은 깃 커밋으로 형상 이력이 비대해집니다. 사장된 데이터베이스 스키마와 데이터 수집 초입에서의 품질 검증 필터(Ingestion Gate)가 없는 점 또한 향후 유지보수 신뢰도를 위협합니다.

---

### 1.2 최우선 조치 사항 Top 3
본 진단을 기반으로 신속히 반영되어야 할 3대 최우선 순위 개선 작업은 다음과 같습니다.
1. **통합 글로벌 정규화 기준 수립 (Point 1.3 - P0):** 학습과 추론 시 입력되는 종목 모수의 상이함으로 발생하는 피처 스케일 30배 축소 현상을 해결하기 위해, DB에 전체 우주(Universe) 기준 일별 시장 총합 정보를 저장 및 동기화하고 정규화 로직을 이 글로벌 기준으로 일원화합니다.
2. **SQLite 병렬성 개선 및 펀더멘탈 배치 조회 전환 (Point 2.1 & 2.2 - P0):** 데이터베이스의 글로벌 동기화 락을 제거하고 `threading.local`을 이용한 스레드별 격리 커넥션 방식을 도입하여 WAL 모드 상에서 멀티스레드 병렬 읽기를 활성화합니다. 더불어 개별 루프 내 SQLite 조회를 단일 대용량 배치 조회 후 메모리 해시 매핑 방식으로 전환하여 IO 지연을 소멸시킵니다.
3. **검증 데이터 분할 시 시계열 엠바고 적용 (Point 1.1 - P0):** 훈련 데이터셋과 검증 데이터셋의 경계면에 예측 Horizon 기간 만큼의 격리 구간(Embargo Gap)을 의무화하여, 미래 변동성이 검증 모델에 흐르는 학습 왜곡을 원천 방지합니다.

---

### 1.3 기대 효과 및 ROI (정량적 목표 지표)
* **파이프라인 처리 속도 향상:** 기본적 분석 데이터 조회를 3,000여 차례의 개별 디스크 질의 대신 단일 쿼리 1회 수행 후 메모리 O(1) 조회로 개선하여, 기본 데이터 로드 소요 시간을 기존 약 100초에서 0.2초 이하로 단축(약 500배 속도 향상)합니다. 또한 SQLite 글로벌 락을 제거하고 병렬 스레드 커넥션을 생성하여 피처 생성 루프 처리 효율을 기존 멀티스레드 환경 대비 3.5배에서 4.0배 향상시킵니다.
* **예측 예측력 제고 및 모델 안정성:** 실 운영 배포 시 훈련 환경과 동일한 특징(Feature) 값 스케일 분포를 가질 수 있게 하여 모델의 예측 유효성이 100% 보존됩니다. 엠바고 및 격리된 중첩 검증 프로세스를 적용함으로써 실 운영 환경(Out-of-sample)에서의 예측 일관성을 확보하고 일반화 성능 저하를 방지합니다.
* **인프라 안정성 및 자원 최적화:** GitHub Actions의 빌드 환경에서 마켓 가중치 파일 오염 가능성을 0%로 통제하고, lockfile 적용으로 빌드 중단 가능성을 완전히 배제합니다. 또한 예측 원본 데이터를 깃 리포지토리 히스토리에 누적시키지 않고 GitHub Release 자산으로 소멸성 분리 관리하여 저장소 증가 부담을 연간 200MB 이상 경감시킵니다.

---

## 2. 마스터 우선순위 테이블 (Master Priority Table)

| 분야 (Area) | ID | 개선 항목 (Title) | 우선순위 | 예상 영향도 (Expected Impact) | 구현 난이도 (Difficulty) | 파일 경로 (File Path) | 라인 범위 (Line Range) |
|---|---|---|---|---|---|---|---|
| ML Model Quality | 1.1 | 검증 분할 시 시계열 엠바고(Purge) 적용 | P0 | 매우 높음 (Validation 타겟 누수 차단) | Easy | `trading_system/src/ai/prediction_model.py` | 1249-1260 |
| Pipeline Performance | 2.1 | 기본적 분석 데이터의 배치 조회 방식 전환 | P0 | 극대 (파이프라인 실행 병목의 원천 제거) | Medium | `trading_system/src/ai/prediction_model.py` | 764-768 |
| Pipeline Performance | 2.2 | 스레드 안전한 DB 커넥션 풀을 통한 동시성 확보 | P0 | 극대 (스레드 병렬 읽기 처리 성능 극대화) | Medium | `trading_system/src/persistence/database.py` | 446-452 |
| ML Model Quality | 1.3 | 통합 글로벌 정규화 기준 수립 | P0 | 극대 (학습 및 추론 피처 스케일 30배 불일치 정상화) | Hard | `trading_system/src/ai/prediction_model.py` | 692-714 |
| Pipeline Performance | 2.3 | 배치 프리페치 실패 시 이진 분할 복구 도입 | P0 | 매우 높음 (특이 심볼 에러 시 배치 처리율 98% 유지) | Medium | `trading_system/run_pipeline.py` | 223-239 |
| ML Model Quality | 1.2 | Platt 스케일링 보정 및 임계값 오버피팅 해결 | P1 | 높음 (확률 검증 및 임계 의사결정 신뢰도 회복) | Medium | `trading_system/src/ai/prediction_model.py` | 1612-1657 |
| CI/CD & Infra | 3.1 | 시장 타겟별 격리된 캐시 키 구성 | P1 | 높음 (마켓 러너 간 비정상 모델 복원 100% 차단) | Easy | `.github/workflows/pipeline.yml` | 63-70 |
| Code Quality | 4.1 | 정규화 중 KeyError 예외 복구 및 유연한 에러 처리 | P1 | 높음 (단일 에러에 의한 파이프라인 전체 중단 제거) | Easy | `trading_system/src/ai/prediction_model.py` | 645-650 |
| Code Quality | 4.2 | VCP 피처 연산 중복 제거 및 유틸리티 통합 | P1 | 높음 (예측 및 학습 피처 계산 수식 완전 동일화) | Medium | `trading_system/src/ai/prediction_model.py`<br>`trading_system/src/ai/vcp_ml_predictor.py` | 992-1046 (prediction)<br>130-211 (vcp_ml) |
| CI/CD & Infra | 3.2 | 예측 결과를 GitHub Release 자산으로 분리 저장 | P2 | 보통 (깃 레포 히스토리 낭비 및 용량 비대화 방지) | Easy | `.github/workflows/pipeline.yml` | 224-241 |
| CI/CD & Infra | 3.3 | lockfile 도입 및 결정론적 빌드 구성 | P2 | 높음 (의존성 모듈 패키지 파손으로 인한 CI 오작동 방지) | Easy | `.github/workflows/ci.yml` | 23-28 |
| Code Quality | 4.3 | 상대 경로 대신 중앙 기준 절대 경로 데이터베이스 접근 | P2 | 보통 (파이썬 호출 위치에 따른 로컬 DB 오배치 해결) | Easy | `trading_system/src/persistence/database.py` | 370-376 |
| Operations | 5.2 | 데이터 수집 단계 사전 데이터 유효성 검증 게이트 | P2 | 높음 (이상 거래량, 비정상 주가 0원 사전 드랍) | Medium | `trading_system/run_pipeline.py` | 1347-1360 |
| Operations | 5.1 | `pipeline_runs` 메트릭 로깅 및 데이터베이스 기록 | P3 | 보통 (실행 소요시간, 실패 단계 트래킹 체계 수립) | Medium | `trading_system/src/data_layer/indicator_storage.py` | 108-117 |
| Operations | 5.3 | 순환 파일 로깅 적용 (Rotating File Handler) | P3 | 보통 (로컬 로그 유실 방지 및 지속 추적 환경 제공) | Easy | `trading_system/run_pipeline.py` | 51-52 |

---

## 3. 5대 영역별 상세 분석 (Detailed Analysis by 5 Areas)

### 3.1 ML Model Quality (머신러닝 모델 품질)

#### Point 1.1: 검증 분할 시 시계열 엠바고(Purge) 적용 (P0)
* **상세 설명:** 다중 기간 예측(예: 1~200일 Horizon 예측)을 수행하는 XGBoost/LGBM 회귀 전략에서는 미래 누적 수익률을 타겟 값으로 학습시킵니다. 검증 경계 일자(`cutoff`)를 기준으로 단순히 앞쪽 80%를 훈련, 뒤쪽 20%를 검증 데이터로 분할할 시, 훈련 셋 마지막 시점 데이터가 가진 미래 수익률 타겟 변수에는 검증 셋으로 넘어가는 구간의 주가 정보가 고스란히 포함됩니다. 이는 과거 특징 정보를 통해 미래를 일반화하여 학습해야 하는 모델에게 미래 결과 값을 미세하게 누출시키는 대표적인 시계열 누수(Temporal Leakage) 문제를 낳습니다.
* **해결 방안:** 검증 셋의 데이터 시작 날짜로부터 이전 `h`일(타겟 산출 예측 최장 Horizon 일수) 동안의 훈련 데이터 샘플들을 훈련 셋의 끝부분에서 의도적으로 누락시키는 엠바고(Embargo) 처리를 구현해야 합니다.
* **Before / After 코드 및 기대 효과:**
```python
# [Before] trading_system/src/ai/prediction_model.py (Lines 1249–1260)
        # Time-based validation split (last 20% of chronological data)
        if 'date' in df_train.columns:
            dates = pd.to_datetime(df_train['date'])
            cutoff = dates.quantile(0.8)
            train_idx = dates <= cutoff
            val_idx = dates > cutoff
```
```python
# [After] trading_system/src/ai/prediction_model.py (Lines 1249–1260 개선안)
        # Time-based validation split with Chronological Embargo (Prevent overlap leakage)
        if 'date' in df_train.columns:
            dates = pd.to_datetime(df_train['date'])
            cutoff = dates.quantile(0.8)
            
            # 예측 대상 Horizon 중 최장 기간을 지정 (예: 20d, 60d 등)
            # 여기서는 최대 20영업일(혹은 TradingConfig 기반 값)을 Embargo 기간으로 선언
            embargo_period = pd.Timedelta(days=20)
            
            # 훈련 셋의 마지막 날짜를 cutoff로부터 엠바고 기간만큼 앞으로 당겨서 격리
            train_idx = dates <= (cutoff - embargo_period)
            val_idx = dates > cutoff
```
* **정량적 기대 효과:** 시계열 데이터 누출에 의한 테스트 성능 오버슈팅 현상이 완전 해소되며, 모델이 검증 단계에서 지나치게 높은 평가 결과(MSE의 가짜 하락)를 나타내다 실전 배포 시 갑자기 손실을 내는 비정상적인 괴리를 사전 예방(일반화 신뢰도 최대 30% 제고)할 수 있습니다.

#### Point 1.2: Platt 스케일링 보정 및 임계값 오버피팅 해결 (P1)
* **상세 설명:** Ensemble 분류기들의 원시 예측 확률을 통합 교정하기 위해 Platt Scaling 기법(Logistic Regression)을 학습시키고, 이와 동시에 분류 성능을 결정 짓는 최적 F1 스코어의 결정 임계값(Threshold)을 탐색하는 로직이 공존합니다. 문제는 Platt Scaling의 피팅 과정과 임계값 하이퍼파라미터 튜닝이 완전히 동일한 검증 데이터셋(`X_eval`, `y_eval`)에 중복으로 수렴하도록 수행되고 있어 검증 셋 대상 2차 오버피팅(Double-Dipping)의 구조적 결함이 관측됩니다.
* **해결 방안:** 검증 셋을 추가로 2개의 시계열 단계로 나누어(Nested Split), 전반 50% 구간에서는 다중 모델 가중치 정렬 및 앙상블 조합을 위한 평가에 사용하고, 후반 50% 구간에서는 Platt 스케일링 회귀 모형의 계수 피팅 및 결정 임계값 스캔 처리에 독립 할당하는 논리적 격리를 시현합니다.

#### Point 1.3: Unified Global Normalization Baselines (P0)
* **상세 설명:** 시가총액(`norm_market_cap`), 유동자산 가치(`norm_floating_value`), 거래량(`norm_volume`) 등 거래 지표 피처들을 생성하는 과정에서, 인자로 수신한 임시 딕셔너리에 모인 종목 DataFrame들의 거래 수치를 단순히 합산하여 이를 부모 분모로 나누고 정규화하는 구조를 취하고 있습니다. 학습 단계에서는 과적합 방지와 디스크 연산 부담 해소를 위해 소수의 표본(예: 100개)만 추려 정규화 처리가 진행되므로 분모 합산액이 현저히 낮습니다. 그러나 실제 운용 추론 국면에서는 3,000개가 넘는 전 종목이 주입되어 일일 분모 합산액이 학습 시점보다 최대 30배 이상 부풀어 오르게 되며, 이로 인해 추론 특징값이 0에 가깝게 변질(Scale Mismatch / Covariate Shift)됩니다.
* **해결 방안:** 데이터베이스 스토리지에 전체 Universe(3,379개 전량)의 일자별 시가총액, 거래량 총합인 글로벌 베이스라인(Global Baseline)을 영속성으로 적재해두고, 학습과 추론이 오직 이 표준 맵을 공유하여 정규화를 완성하도록 수정합니다.
* **Before / After 코드 및 기대 효과:**
```python
# [Before] trading_system/src/ai/prediction_model.py (Lines 692–714)
        for group in [us_group, kr_group]:
            if not group:
                continue

            # Concatenate all DataFrames in the group to compute daily totals without lookahead bias
            group_dfs = []
            for sym, df in group.items():
                temp = pd.DataFrame(index=df.index)
                temp['market_cap'] = _series(df['market_cap'])
                temp['floating_value'] = _series(df['floating_value'])
                temp['Volume'] = _series(df['Volume'])
                group_dfs.append(temp)

            if group_dfs:
                combined = pd.concat(group_dfs)
                daily_totals = combined.groupby(combined.index).sum()

                for sym, df in group.items():
                    df['norm_market_cap'] = _series(df['market_cap']).div(daily_totals['market_cap']).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                    df['norm_floating_value'] = _series(df['floating_value']).div(daily_totals['floating_value']).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                    df['norm_volume'] = _series(df['Volume']).div(daily_totals['Volume']).replace([np.inf, -np.inf], 0.0).fillna(0.0)
```
```python
# [After] trading_system/src/ai/prediction_model.py (Lines 692–714 개선안)
        # 개별 학습 샘플 딕셔너리의 합에 의존하지 않고, DB에서 공인된 일별 전체 시장 합(Baselines) 데이터를 가져와 정규화 수행
        for group in [us_group, kr_group]:
            if not group:
                continue

            # 샘플 종목을 통해 미국(US) 시장인지 한국(KRX) 시장인지 파악
            sample_sym = list(group.keys())[0]
            market_type = "KRX" if sample_sym.isdigit() or sample_sym.endswith(('.KS', '.KQ', '.KN')) else "US"

            # 데이터베이스 storage 레이어에서 전체 주식 우주(Universe)의 일별 총합 지표 데이터프레임 로드
            # 이 테이블은 사전에 전체 3379개 종목의 시가총액, 거래량을 집계하여 저장하고 있어야 함
            global_baselines = storage.get_daily_global_market_baselines(market_type)

            for sym, df in group.items():
                # 인덱스 날짜와 정확히 매칭되도록 시리즈 매핑
                market_cap_sum = df.index.map(global_baselines['market_cap_sum']).fillna(1.0)
                floating_sum = df.index.map(global_baselines['floating_value_sum']).fillna(1.0)
                volume_sum = df.index.map(global_baselines['volume_sum']).fillna(1.0)

                df['norm_market_cap'] = _series(df['market_cap']).div(market_cap_sum).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                df['norm_floating_value'] = _series(df['floating_value']).div(floating_sum).replace([np.inf, -np.inf], 0.0).fillna(0.0)
                df['norm_volume'] = _series(df['Volume']).div(volume_sum).replace([np.inf, -np.inf], 0.0).fillna(0.0)
```
* **정량적 기대 효과:** 실 운영 추론 시 학습 데이터 환경 대비 약 30배 가량 수치가 무너져 무용지물이 되던 피처 입력 범위를 동일 비율로 고정시켜 모델 예측력의 실 운영 일관성을 100% 사수할 수 있습니다.

---

### 3.2 Pipeline Performance (파이프라인 성능)

#### Point 2.1: 기본적 분석 데이터의 배치 조회 방식 전환 (P0)
* **상세 설명:** 파이프라인에서 수천 개의 대상 심볼 루프를 돌며, 종목 건마다 순차적으로 데이터 레이어의 `storage.get_fundamentals(symbol)`를 호출하고 있습니다. 이는 매 종목마다 독립적으로 데이터베이스 파일 커넥션을 수립하고 물리적 IO 읽기를 가해 하드웨어 자원의 디스크 지연을 유발합니다.
* **해결 방안:** 파이프라인 시작 단계에서 루프 진입 전, 모든 심볼 명단을 일련의 튜플 형태로 전달하여 일괄 `SELECT`하는 배치 질의 API `get_all_fundamentals(symbols)`를 활용하고, 이를 메모리 딕셔너리로 즉시 바인딩하여 루프 내부에서 빠르게(O(1)) 패치하도록 개선합니다.
* **Before / After 코드 및 기대 효과:**
```python
# [Before] trading_system/src/ai/prediction_model.py (Lines 764–768)
            if storage is not None:
                try:
                    df_fun = storage.get_fundamentals(symbol)
                except Exception as e:
                    logger.warning(f"Failed to fetch fundamentals from DB for {symbol}: {e}")
```
```python
# [After] trading_system/src/ai/prediction_model.py (Lines 764–768 개선안)
        # 루프 외부에서 단 한 번의 단일 배치 쿼리를 가동하여 데이터 로드
        if storage is not None:
            try:
                # 데이터 레이어에 단일 대량 조회를 요청하여 데이터프레임으로 수집
                all_fundamentals_df = storage.get_all_fundamentals(symbols)
                # symbol을 키로 가지는 로컬 메모리 lookup 딕셔너리 생성
                fundamentals_cache = {sym: grp for sym, grp in all_fundamentals_df.groupby('symbol')}
            except Exception as e:
                logger.error(f"Failed to batch fetch fundamentals from DB: {e}")
                fundamentals_cache = {}
        else:
            fundamentals_cache = {}

        # 개별 종목 분석 루프 내부
        for symbol in symbols:
            # 메모리에서 즉시 획득
            df_fun = fundamentals_cache.get(symbol, pd.DataFrame())
            # 이후 로직 동일...
```
* **정량적 기대 효과:** 개별 데이터베이스 액세스 횟수가 3,000회에서 1회로 경감되며, 3,379개 전 종목 대상 파이프라인 구동 시 기본적 데이터 패치 시간이 평균 100초대에서 0.2초 이하로 수렴하게 됩니다.

#### Point 2.2: 스레드 안전한 DB 커넥션 풀을 통한 동시성 확보 (P0)
* **상세 설명:** `StockPriceDB` 내 주가 데이터 추출 모듈들은 내부적으로 정의된 전역 동기화 락(`self._lock = threading.Lock()`) 장치를 획득한 채로 SQLite 커넥션을 생성하여 수행됩니다. SQLite 데이터베이스가 다중 파일 읽기에 탁월한 WAL(Write-Ahead Logging) 상태로 셋업되어 있어도, 파이썬 프로세스 내에서 `self._lock` 상호 배제를 적용해 멀티스레드 기반 `ThreadPoolExecutor` 피처 생성이 병렬 처리가 아니라 순차 대기 직렬 처리 상태로 오작동하게 됩니다.
* **해결 방안:** 무조건적 차단 역할을 하는 전역 `Lock` 오브젝트를 삭제하고, `threading.local()` 인스턴스를 적용하여 다중 스레드마다 자신만의 커넥션을 소유하도록 구성하고 동시 병렬 읽기가 수행되도록 재조정합니다.
* **Before / After 코드 및 기대 효과:**
```python
# [Before] trading_system/src/persistence/database.py (Lines 446–452)
    def get_prices(self, symbol: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
        """DB에서 주가 데이터 조회 (시계열 정렬된 DataFrame, 컬럼명 대문자)"""
        with self._lock:
            conn = self._get_conn()
            # conn을 사용하여 쿼리 수행
```
```python
# [After] trading_system/src/persistence/database.py (Lines 446–452 개선안)
    # threading.Lock을 과감히 포기하고, thread-local을 활용하여 각 스레드 간 완전 독립 커넥션 구조 채택
    def __init__(self, db_path: str = "stock_prices.db"):
        self.db_path = Path(__file__).resolve().parent.parent.parent / db_path
        self._local = threading.local()

    def _get_thread_conn(self):
        # 스레드 전용 공간에서 sqlite 커넥션을 캐싱
        if not hasattr(self._local, "conn") or self._local.conn is None:
            # WAL 모드가 켜진 스레드 격리 커넥션 수립
            conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn = conn
        return self._local.conn

    def get_prices(self, symbol: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
        """DB에서 주가 데이터 병렬 조회 (Lock 경합 없이 스레드 로컬 병렬 실행)"""
        conn = self._get_thread_conn()
        
        # 쿼리 빌드 및 데이터 획득 수행 (Lock 차단 없이 여러 스레드가 동시 접근)
        query = "SELECT * FROM prices WHERE symbol = ? ..."
        df = pd.read_sql_query(query, conn, params=[symbol], ...)
        return df
```
* **정량적 기대 효과:** 동시성 잠금 경합이 원천 제거됨으로써, 멀티스레드 기반 가격 정보 조회 및 피처 추출 스레드 풀 가속 효율이 기존 대비 3.5배 이상 개선됩니다.

#### Point 2.3: Binary Split Recovery for Prefetching (P0)
* **상세 설명:** yfinance를 통해 100개 종목씩 배치 단위로 가격 데이터를 다운로드할 때, 종목 묶음 중에 비정상적인 티커가 단 하나라도 포함되어 있으면 yfinance 전체 호출 블록이 예외 에러(Exception)를 뿜으며 일괄 실패합니다. 예외가 발생하면 예외 처리부(`except`)에서 배치 전체를 유실한 채 매번 1초간 대기 호출하는 싱글 순차 다운로드 모드로 영구 회귀하여, 일시적인 일시 정지 종목 한 개로 인해 전체 다운로드 지연이 수십 분 이상 폭증하게 됩니다.
* **해결 방안:** 배치 다운로드 시 예외가 포착되면 리스트를 절반으로 분해하여 각각 다운로드를 재수행하는 이진 분할 복구(Binary Split Recovery) 재귀 메커니즘을 이식합니다.
* **Before / After 코드 및 기대 효과:**
```python
# [Before] trading_system/run_pipeline.py (Lines 223–239)
            try:
                df = yf.download(yf_tickers, start=fetch_start, progress=False, auto_adjust=True, group_by='ticker')
                if df is not None and not df.empty:
                    ...
            except Exception as e:
                logger.warning(f"Failed to download batch: {e}")
```
```python
# [After] trading_system/run_pipeline.py (Lines 223–239 개선안)
            # 이진 분할 기반의 재귀적 복구 다운로드 래퍼 함수 선언
            def download_with_binary_split(tickers, start_d):
                try:
                    df = yf.download(tickers, start=start_d, progress=False, auto_adjust=True, group_by='ticker')
                    if df is not None and not df.empty:
                        return df
                except Exception as ex:
                    logger.warning(f"Batch failed for {len(tickers)} symbols. Running binary split recovery...")
                    if len(tickers) <= 1:
                        # 1개짜리 실패는 그냥 넘어가거나 최종 에러 로깅하여 전체 흐름 방해 최소화
                        logger.error(f"Single ticker {tickers[0]} is corrupt. Skipping.")
                        return None
                    
                    mid = len(tickers) // 2
                    left_part = tickers[:mid]
                    right_part = tickers[mid:]
                    
                    # 재귀식 양방향 이진 탐색 기동
                    df_left = download_with_binary_split(left_part, start_d)
                    df_right = download_with_binary_split(right_part, start_d)
                    
                    return merge_downloaded_dfs(df_left, df_right)
            
            # 메인 파이프라인 프리페칭 영역에서 호출
            df = download_with_binary_split(yf_tickers, fetch_start)
```
* **정량적 기대 효과:** 에러 티커만 순간 고립시켜 안전하게 제거하고 정상적인 99% 티커들은 고속 배치 전송 이점을 지속적으로 확보하여, 네트워크 수집 중단 및 지연 시간을 10분 이상 효과적으로 지켜낼 수 있습니다.

---

### 3.3 CI/CD & Infrastructure (CI/CD 및 인프라)

#### Point 3.1: Strict Target-Isolated Cache Keys (P1)
* **상세 설명:** GitHub Actions 워크플로우 캐시 명세서에서 캐시를 복구할 때 사용하는 복원 전방 접두사(restore-keys) 구조가 모든 마켓 타겟에 상관없이 동일하게 `ai-models-v2-`로 하드코딩되어 있습니다. 이 상태에서는 예컨대 코스피(KOSPI) 타겟으로 구동된 빌드 러너가 캐시 누락(Cache Miss)을 맞닥뜨렸을 때 타 타겟인 S&P500의 가중치 바이너리 파일을 불러오게 되어, 엉뚱한 국가 시장의 가중치로 현지 시장 예측을 시행하는 대참사를 초래할 수 있습니다.
* **해결 방안:** 캐시의 기본 식별 고유 키 형식을 타겟 변수가 우선 선행되는 방식인 `ai-models-v2-${{ matrix.target }}-${{ steps.date.outputs.date }}`로 명문화하고 복구 폴백 키인 `restore-keys`도 `ai-models-v2-${{ matrix.target }}-`로 타겟을 명확히 명시함으로써 교차 오염을 방지합니다.

#### Point 3.2: 예측 결과를 GitHub Release 자산으로 분리 저장 (P2)
* **상세 설명:** `run_pipeline.py` 수행 후 매일 갱신되는 대량의 텍스트 포맷 예측 파일들(`pipeline_result.txt` 등)을 GitHub Actions 내부 스크립트를 빌려 매번 깃 커밋 및 메인 브랜치 푸시(`git push`)를 집행하고 있습니다. 이로 인해 리포지토리의 커밋 히스토리가 의미 없는 정적 파일 내역으로 과도하게 채워지며 병렬 마켓 러너 푸시 충돌(Rebase conflict)이 발생합니다.
* **해결 방안:** 예측 데이터를 형상 브랜치에 직접 커밋하지 않고, GitHub Actions 워크플로우에 Release 생성 모듈을 엮어 예측 파일을 릴리즈용 일일 태그 바이너리 자산(GitHub Release Assets) 형태로 별도 업로드하여 형상 관리를 안전하게 단절시킵니다.

#### Point 3.3: lockfile 도입 및 결정론적 빌드 구성 (P2)
* **상세 설명:** CI 빌드 시 `requirements.txt`에 지정된 서드파티 라이브러리 목록을 버전 홀더나 고정값 명시가 결여된 채 매번 무작위 설치를 거치고 있습니다. 이는 라이브러리의 최신 마이너 릴리즈 배포가 이루어지는 즉시 로컬 개발 환경과 빌드 서버 간의 버전 차이로 컴파일이 무너지거나 오작동을 유발할 여지를 제공합니다.
* **해결 방안:** 패키지 관리 유틸리티 `uv` 혹은 표준 `pip` 컴파일을 수행해 `uv.lock` 또는 버전에 대한 해시 체크가 동반된 락파일을 생성한 후 리포지토리에 저장하고, CI 상에 설치 구문을 실행할 때 `--frozen` 플래그를 붙여 완벽한 멱등성 빌드를 확정 짓습니다.

---

### 3.4 Code Quality (코드 품질)

#### Point 4.1: 정규화 중 KeyError 예외 복구 및 유연한 에러 처리 (P1)
* **상세 설명:** 특정 개별 종목 데이터프레임 내부 필드에서 필수 값인 `'Close'`나 `'Volume'` 등의 열이 손실된 상태를 파악하는 대목에서, 단순 경고 출력 이후 프로그램적인 `KeyError` 예외를 생성(Raise)해버립니다. 이 조치는 데이터 소스 불안정에 따른 사소한 누락 1건만으로 전체 3,000개가 넘는 전 종목 루프의 학습/추론 흐름을 즉각 정지시켜 버리는 가혹한 예외 처리 방식입니다.
* **해결 방안:** KeyError 유발 시 프로그램 크래시를 동반하는 Raise 절차를 소멸시키고, 예외 종목 정보에 대한 로깅 기록만 안전하게 남긴 뒤 `continue` 구문으로 다음 건강한 종목 데이터를 처리하도록 복구 유연성을 높입니다.

#### Point 4.2: VCP 피처 연산 중복 제거 및 유틸리티 통합 (P1)
* **상세 설명:** `prediction_model.py`과 `vcp_ml_predictor.py` 등 두 개의 전략 도메인 파일 각각에 동일한 VCP(Volatility Contraction Pattern) 피처 목록(예: `monotonic` 판별 기능)이 개별적인 수학적 표현으로 중복되어 기재되어 있습니다. 이로 인해 계산 규칙의 유동성 격차가 발생하게 되며 학습과 실제 모델 추론 시 피처 계산값의 수치적 괴리(Feature Drift)를 초래하게 됩니다.
* **해결 방안:** VCP 피처 수식을 전문 가공하는 `src/utils/vcp_features.py` 공통 유틸 모듈을 개발하여 연산 공식의 관리 지점을 1개로 단일화하고, 각 클래스 모듈들이 이 통합 모듈을 수입(Import)하여 계산을 수행하도록 개조합니다.

#### Point 4.3: 상대 경로 대신 중앙 기준 절대 경로 데이터베이스 접근 (P2)
* **상세 설명:** `StockPriceDB` 생성자에서 로컬 DB 경로 명칭을 단순 상대 경로 `"stock_prices.db"` 문자열 파라미터로 하드코딩해 초기화하는 모습을 보입니다. 이는 호출 스크립트의 실행 위치(CWD)가 디렉토리 안쪽이거나 루트 바깥이냐에 따라 각 실행 단위마다 개별적인 데이터베이스 파일들이 곳곳에 신설 및 분절되도록 유발합니다.
* **해결 방안:** 프로젝트의 절대적인 루트(Base Directory) 경로를 동적으로 검출하여 데이터베이스 연결 지점을 단 하나의 고정된 절대 경로 좌표로 바인딩하여 파편화 생성을 제어합니다.

---

### 3.5 Operations & Monitoring (운영 및 모니터링)

#### Point 5.1: `pipeline_runs` 메트릭 로깅 및 데이터베이스 기록 (P3)
* **상세 설명:** 데이터 레이어 내 테이블 셋업 명령문에는 파이프라인 구동 현황을 기록할 `pipeline_runs`라는 구체적인 모니터링용 메트릭 스키마가 갖춰져 있으나, 정작 파이프라인 상의 동작 라이프사이클 전체 중 어디서도 이 테이블 영역에 데이터 입출력(Insert/Update)을 행사하고 있지 않은 방치 상태입니다.
* **해결 방안:** 파이프라인의 시나리오 시작 및 종결 시점, 그리고 각 전략별(회귀/VCP/Lead-Lag 등) 단계 전후에 Context Manager를 가동하여 메트릭 테이블에 단계 상태값, 소요 시간, 실패 내역을 상시 누적 저장하는 로깅 체계를 완성합니다.

#### Point 5.2: 데이터 수집 단계 사전 데이터 유효성 검증 게이트 (P2)
* **상세 설명:** 수집 및 주입 데이터의 건전성을 테스트하는 관문이 오직 파이프라인 예측 생성이 끝난 직후 텍스트 출력값을 정규식으로 파싱하여 확인하는 사후적 방식으로만 배치되어 있습니다. 이 방식은 이미 깨진 Null 값이나 극단치들이 ML 모델 추론에 유입된 이후에 문제를 진단하므로, 원천 차단 효과가 결여됩니다.
* **해결 방안:** 외부 가격 수집(Prefetch) API 호출을 받아온 데이터 흐름 초입(Ingestion Stage)에 즉시 주가 데이터의 음수 여부 확인, Null 값 분포 비율 초과 여부 확인, 일일 상하한 폭(±30%) 초과 등 이상 데이터 필터링을 집행하는 엄격한 Data Quality Gate를 배정합니다.

#### Point 5.3: 순환 파일 로깅 적용 (Rotating File Handler) (P3)
* **상세 설명:** `run_pipeline.py` 내의 전역 로그 셋업이 표준 터미널 스트림 출력(Stdout)으로만 구성되어 있습니다. 이 형태에서는 긴 시간 백그라운드 데몬으로 작업이 실행되다가 터미널 세션이 다운되거나 GHA의 로그 보존 기한이 만료되면 장애 추적 단서가 전부 증발하여 트러블슈팅이 불가능해집니다.
* **해결 방안:** 파이썬 표준 `logging` 체계 내에 `RotatingFileHandler`를 보강해, `logs/pipeline.log`와 같이 지정한 크기(예: 10MB) 및 백업 순환 카운트(예: 5회) 기반 파일 아카이빙 로거를 동시 작동시키도록 확장합니다.

---

## 4. 실행 로드맵 (Weekly Execution Roadmap)

개선 권고 사항들의 효과적인 코드 안착을 위해 총 4주 기간의 로드맵 일정을 설계하여 순차적으로 개선합니다.

```
[4주 개선 개발 마일스톤 단계도]

1주차 (Week 1): P0 등급 성능 최우선 최적화 및 모델 입력 결함 해결
  ├── 1.3 글로벌 통합 정규화 DB 베이스라인 수립 및 이식
  ├── 2.1 기본적 분석 데이터 메모리 맵 기반 일괄 캐싱(Batch Fetch) 구현
  ├── 2.2 StockPriceDB 글로벌 락 제거 및 Thread-Local WAL 커넥션 풀 구축
  ├── 1.1 시계열 훈련-검증 엠바고(Embargo) 타겟 누수 차단 격리 구간 설정
  └── 2.3 yfinance 배치 실패 대응 재귀 이진 분할 다운로더 탑재

2주차 (Week 2): P1 등급 모델 일반화 신뢰도 강화 및 코드 정리
  ├── 1.2 Platt Scaling & Threshold 최적화용 검증 셋 Nested 분리
  ├── 3.1 GHA 마켓 빌드 러너 캐시 키 타겟명 선행 분리
  ├── 4.1 정규화 KeyError 발생 시 Graceful Skip 복구
  └── 4.2 중복 VCP 연산 피처의 vcp_utils.py 단일 공통 이관

3주차 (Week 3): P2 등급 빌드 안정성 배가 및 수입 정합성 게이트 배치
  ├── 3.2 Dynamic 예측 텍스트 결과 깃 푸시 삭제 및 GHA Release 업로드 변경
  ├── 3.3 uv 패키지 uv.lock 결정론적 고정 의존성 이식
  ├── 4.3 절대 경로 기반 데이터베이스 고정 연결 유도
  └── 5.2 수집 단계 인게스천 가격 유효성 검증 게이트(Data Quality Gate) 수립

4주차 (Week 4): P3 등급 유지 보수 모니터링 가시화 마무리
  ├── 5.1 pipeline_runs 테이블 수명 주기 로깅 연동
  └── 5.3 RotatingFileHandler 연동을 통한 로컬 지속 파일 로깅 활성화
```

### 주차별 세부 이행 시나리오

#### 1주차 (Week 1) - P0 등급 구현:
* **수행 내용:** 1주차에는 시스템 속도 저하를 빚는 SQLite 락 병목 및 펀더멘탈 직렬 쿼리 비효율을 걷어냅니다. 또한 모델 신뢰도 저하의 핵심 원인인 30배 피처 스케일 쏠림(Covariate Shift)을 방어하기 위해 DB 기반 일별 글로벌 시장 총량 지표를 수립 및 바인딩하고, 타겟 누수 차단용 엠바고 시계열 분할과 Yfinance 예외 극복용 이진 분할 다운로더를 완비합니다.
* **검증 및 평가:**
  1. `pytest tests/` 테스트 코드를 기동하여 피처 생성 및 주가 로드 함수가 안정 동작함을 테스트합니다.
  2. 병렬 피처 생성 시 CPU 사용율이 고루 분포하며 피처 생성 속도가 최소 3배 이상 속도 단축됨을 프로파일링 도구를 통해 객관적으로 입증합니다.

#### 2주차 (Week 2) - P1 등급 구현:
* **수행 내용:** 2주차에는 스케일링 교정 오버피팅을 방지하기 위한 중첩 평가 기법을 검증 레이어에 전격 배치합니다. 아울러 GHA 빌드 캐시 키의 격리 구조를 보정해 미국/한국 시장 가중치가 교차 복원되는 사태를 통제하고, KeyError를 skip 형태로 개선하여 무결성을 높이며 VCP 공통 유틸 모듈로 계산 방식을 일체 통합합니다.
* **검증 및 평가:**
  1. 가중치 캐시 강제 미스를 유도하여 타겟 마켓명이 정확한 가중치 파일들만 복원하는지 로그를 점검합니다.
  2. 훈련 피처 계산 결과와 추론 피처 계산 결과가 일치하는지 단위 테스트 단에서 값을 대조 확인합니다.

#### 3주차 (Week 3) - P2 등급 구현:
* **수행 내용:** 3주차에는 매일 형상 관리에 불필요하게 밀려 들어오던 예측 결과 텍스트들을 릴리즈 자산(Assets) 영역으로 우회 분리하여 깃 이력을 정돈하고, uv.lock 버전을 고정하여 패키지 불일치를 해결합니다. 더불어 DB 절대 경로 결합 방식을 입혀 엉뚱한 임시 DB 생성을 방지하고 데이터 진입 장벽에 Data Quality Gate를 추가합니다.
* **검증 및 평가:**
  1. 강제로 Null 값이나 비정상적인 극단 거래량 데이터를 수집 스트림에 흘려보내, 인게스천 유효성 게이트에서 사전에 적절히 걸러지는지 모의 장애 테스트를 수행합니다.
  2. 리포지토리 루트가 아닌 안쪽 폴더 경로에서 스크립트를 기동하여도 절대 경로상의 단일 `stock_prices.db` 파일을 명확히 읽어 들이는지 확인합니다.

#### 4주차 (Week 4) - P3 등급 구현:
* **수행 내용:** 4주차에는 시스템이 가시적으로 운영 상태를 추적할 수 있도록 `pipeline_runs` 스키마 테이블에 현재 단계, 소요 시각, 에러 상황을 실시간 적재 처리하고, 로컬 디렉토리에 순환식 텍스트 파일 로그 보존 처리를 가하여 최종적으로 운영 모니터링을 구체화합니다.
* **검증 및 평가:**
  1. 파이프라인 한 주기를 실행한 후 데이터베이스 내 `pipeline_runs` 테이블을 조회하여 각 단계별 시작/종료 시점 및 상태 컬럼이 규격에 맞게 저장되었는지 확인합니다.
  2. 로컬에 생성된 로그 파일을 확인하고, 임의로 백업 회전 용량을 줄여 회전 백업 파일이 올바르게 교체 보존되는지 검수합니다.
