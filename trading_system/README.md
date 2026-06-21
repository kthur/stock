# 📈 주식 자동매매 및 예측 시스템 — 실행 가이드

본 가이드는 통합 예측 파이프라인(`run_pipeline.py`) 및 보조 도구의 설치, 설정, 실행, 트러블슈팅을 안내합니다.

---

## 📚 상세 설계 문서

| 문서 | 설명 |
|------|------|
| [ALGORITHMS_AND_STRATEGY.md](docs/ALGORITHMS_AND_STRATEGY.md) | 5대 전략(XGBoost 회귀, Surge, Lead-Lag, VCP 규칙, VCP ML) 알고리즘 상세 |
| [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | 시스템 아키텍처, 데이터 흐름, DB 스키마 |
| [CONFIGURATION_REFERENCE.md](docs/CONFIGURATION_REFERENCE.md) | `.env` 환경 변수 완전 참조 |
| [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | 해결된 이슈 목록 및 미해결 항목 |
| [IMPROVEMENT_PLAN.md](docs/IMPROVEMENT_PLAN.md) | 중장기 시스템 아키텍처 및 성능 개선 계획 |
| [TEST_GUIDE.md](docs/TEST_GUIDE.md) | 테스트 인프라 및 실행 가이드 |

---

## 🚀 빠른 시작 (Quick Start)

### 1. 가상환경 활성화 및 의존성 설치

```powershell
# 가상환경 생성 (최초 1회)
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# 의존성 라이브러리 설치
pip install -r requirements.txt
```

### 2. 환경 설정 파일(`.env`) 생성

```powershell
copy .env.example .env
```

`.env` 파일을 열어 필요한 설정값을 입력합니다. 전체 변수 목록은 [CONFIGURATION_REFERENCE.md](docs/CONFIGURATION_REFERENCE.md)를 참조하세요.

핵심 설정 예시:
```ini
# 학습 종목 수 (all = 전량 학습, 숫자 = 샘플 수)
TRAIN_SAMPLE_SP500=all
TRAIN_SAMPLE_KRX=all

# 오프라인 모드 (네트워크 없이 캐시만 사용)
STOCK_PRICE_FRESHNESS_DAYS=none

# 기존 모델 재사용 (학습 건너뛰기)
SKIP_TRAINING=False

# 학습 데이터 시작일
TRAIN_START_DATE=2006-01-01
```

---

## 💻 실행 방법

### 1. 통합 예측 파이프라인 (핵심)

5대 전략 모델을 학습하고 3,379개 종목의 예측 결과를 생성합니다:

```powershell
.venv\Scripts\python run_pipeline.py
```

**실행 흐름** (12단계):

| 단계 | 설명 | 소요 시간 |
|------|------|-----------|
| 1 | 설정 로드 (`TradingConfig`) | < 1초 |
| 2 | 글로벌 지표 수집 (VIX, TNX, USDKRW 등) | ~10초 |
| 3 | 지표 DB 저장 | < 1초 |
| 4 | 종목 유니버스 로드 (3,379 종목) | ~5초 |
| 5 | 글로벌 지표 히스토리 수집 | ~30초 |
| 6 | 학습 데이터 준비 (병렬 + 펀더멘탈) | ~5-15분 |
| 7a | 회귀 모델 학습 (시장별 XGB+LGB+Cat) | ~10-30분 |
| 7b | Surge 분류기 학습 | ~5-15분 |
| 7c | Lead-Lag 상관 행렬 계산 | ~2분 |
| 7d | VCP ML 분류기 학습 | ~5-10분 |
| 8-9 | 추론 데이터 수집 (전 종목) | ~10-30분 |
| 10-12 | 예측 실행 + 결과 저장 | ~5-10분 |

> **총 소요 시간**: 학습 포함 약 40-90분, `SKIP_TRAINING=True` 시 약 15-40분

### 2. 출력 파일

파이프라인 실행 후 `trading_system/` 하위에 5개 결과 파일이 생성됩니다:

| 파일 | 전략 | 내용 |
|------|------|------|
| `pipeline_result.txt` | XGBoost 회귀 | 종목별 horizon별 예상수익률 TOP 종목 |
| `surge_predictions.txt` | Surge 분류기 | Horizon별 20%↑ 급등 확률 TOP20 |
| `lead_lag_predictions.txt` | Lead-Lag | Leader 기반 follower 점수 |
| `vcp_patterns.txt` | VCP 규칙 | 변동성 수축 패턴 발견 종목 |
| `vcp_ml_predictions.txt` | VCP ML | 시장별 VCP 급등 확률 TOP10 |

### 3. 오케스트레이터 데몬 (자동 스케줄러)

매일 정해진 시각에 파이프라인을 자동 실행하는 백그라운드 데몬입니다:

```powershell
# 데몬 시작
.venv\Scripts\python run_orchestrator.py start

# 데몬 정지
.venv\Scripts\python run_orchestrator.py stop

# 상태 조회
.venv\Scripts\python run_orchestrator.py status

# 특정 스테이지 즉시 실행
.venv\Scripts\python run_orchestrator.py run-now <stage>
```

지원 스테이지: `indicators`, `universe`, `train`, `predict`, `score`, `ingest`, `weekly_train_predict`, `all`

### 4. 텔레그램 봇

```powershell
.venv\Scripts\python telegram_bot_runner.py
```

주요 명령어: `/status`, `/portfolio`, `/buy <symbol> <qty>`, `/sell <symbol> <qty>`

### 5. 대시보드

```powershell
.venv\Scripts\python run_dashboard.py
```

브라우저에서 `http://localhost:5000` 접속

---

## 📁 데이터베이스 파일

| 파일 | 크기 (약) | 설명 |
|------|-----------|------|
| `stock_prices.db` | ~1.7GB | 3,388 종목 OHLCV 캐시 |
| `market_indicators.db` | ~15MB | 글로벌 시장 지표 + 유니버스 + 펀더멘탈 |
| `ai_predictions.db` | ~12KB | AI 예측 결과 저장 |
| `asset_history.db` | ~80KB | 자산 히스토리 |
| `trade_logs.db` | ~20KB | 거래 로그 |

---

## 🛠️ 트러블슈팅

### Q1. "can't open file 'run'" 에러
**원인**: 실행 명령어 오타  
**해결**: 가상환경 활성화 후 파일명 단독 실행
```powershell
.venv\Scripts\activate
python run_pipeline.py
```

### Q2. PyTorch DLL 로딩 오류 (`WinError 1114`)
**원인**: CUDA/MKL DLL 충돌  
**해결**: phase3 테스트 제외하고 실행
```powershell
.venv\Scripts\python -m pytest tests/ --ignore=tests/phase3/
```

### Q3. "ModuleNotFoundError: No module named 'src'"
**원인**: `sys.path`에 프로젝트 디렉토리 미등록  
**해결**: `python -m pytest` 형태로 실행
```powershell
.venv\Scripts\python -m pytest tests/
```

### Q4. "database is locked" 에러
**원인**: 여러 프로세스가 동시에 SQLite에 쓰기 시도  
**해결**:
1. 다른 파이프라인 프로세스가 실행 중인지 확인
2. 오케스트레이터 데몬 중지 후 재시도
3. 지속 시 DB 파일 복사 후 재실행

### Q5. 파이프라인 실행 시간이 너무 오래 걸림
**해결**:
1. `DEBUG_MODE=True` 설정 (시장당 5개 종목만 학습)
2. `SKIP_TRAINING=True` 설정 (기존 모델 재사용)
3. `STOCK_PRICE_FRESHNESS_DAYS=none` 설정 (네트워크 미사용)

### Q6. 메모리 부족 (MemoryError)
**해결**:
1. `TRAIN_SAMPLE_SP500`, `TRAIN_SAMPLE_KRX` 줄이기 (예: `100`)
2. 다른 메모리 사용 프로그램 종료
3. 8GB 이상 RAM 권장