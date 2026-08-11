# 📈 주식 자동매매 및 예측 시스템 — 실행 가이드

본 가이드는 통합 예측 파이프라인(`run_pipeline.py`) 및 보조 도구의 설치, 설정, 실행, 트러블슈팅을 안내합니다.

---

## 📚 상세 설계 문서

| 문서 | 설명 |
|------|------|
| [ALGORITHMS_AND_STRATEGY.md](docs/ALGORITHMS_AND_STRATEGY.md) | 14대 전략(XGBoost 회귀, Surge, Lead-Lag, VCP 규칙, VCP ML, Strict Causal LSTM, Stat-Arb, Sector Rotation, RIM Valuation, Event-Driven, MQ Factor, Options IV Skew, Order Flow, Short-Term Reversal) 알고리즘 상세 |
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

---

## 💻 실행 방법

### 1. 통합 예측 파이프라인 (핵심)

14대 전략 모델을 기반으로 3,379개 종목의 예측 결과를 생성하고 2D 시장 레짐 기반 동적 앙상블을 수행합니다.

#### CLI 옵션 (P1)

```powershell
# 기본 실행 (전 시장, 모델 학습 포함)
.venv\Scripts\python run_pipeline.py

# 도움말
.venv\Scripts\python run_pipeline.py --help
```

| 옵션 | 설명 | 예시 |
|------|------|------|
| `--target {KOSPI,KOSDAQ,NASDAQ,RUSSELL2000,KRX,SP500}` | 특정 시장만 추론 (학습은 전 유니버스) | `--target KOSPI` |
| `--skip-training` | 기존 저장 모델 재사용 (학습 건너뛰기) | `--skip-training` |
| `--debug` | 시장별 3종목만 샘플 — 동작 빠른 검증 | `--debug` |

```powershell
# 예시 조합
.venv\Scripts\python run_pipeline.py --target SP500 --skip-training
.venv\Scripts\python run_pipeline.py --target KOSDAQ --debug
.venv\Scripts\python run_pipeline.py --target KRX --skip-training
```

> **`--target KRX`** = KOSPI + KOSDAQ 전체

### 2. 출력 파일 (`result/`)

| 파일 | 설명 |
|------|------|
| `ensemble_predictions.txt` | 14대 전략 동적 앙상블 TOP 20 및 Decision Rationale (KST) |
| `strategy_data_coverage_report.txt` | 14대 전략별 데이터 커버리지 및 결측 사유 비율 |
| `pipeline_result.txt` | 회귀 모델 horizon별 예상수익률 TOP10 |
| `surge_predictions.txt` | Surge 분류기 horizon별 급등 확률 TOP20 |
| `lead_lag_predictions.txt` | Leader-Follower 시차 상관 점수 |
| `vcp_patterns.txt` | VCP 패턴 검출 종목 |
| `vcp_ml_predictions.txt` | 시장별 VCP ML surge 확률 TOP10 |
| `stat_arb_predictions.txt` | Stat-Arb 차익거래 공적분 잔차 페어 |

| 파일 | 형식 | 설명 |
|------|------|------|
| `pipeline_result.txt` | 텍스트 요약 | TOP10/시장/4 horizon (사람이 읽는 요약) |
| `pipeline_result.csv` | CSV | 전체 종목 회귀 예측값 (기계 가독) |
| `pipeline_result.jsonl` | JSON Lines | 전체 종목 (REST API / 스트리밍용) |
| `surge_predictions.txt` | 텍스트 | horizon별 급등 확률 TOP20 |
| `surge_predictions.csv` | CSV | 서지 예측 원본 |
| `lead_lag_predictions.txt` | 텍스트 | Leader-Follower 상관 점수 (±30% 이상치 제외) |
| `vcp_patterns.txt` | 텍스트 | VCP 패턴 감지 종목 (Score 100/100 등) |
| `vcp_ml_predictions.txt` | 텍스트 | VCP ML surge 확률 TOP10 |

> `pipeline_result.txt`는 **요약본**입니다. 전체 원본 데이터는 `.csv` / `.jsonl` 파일을 사용하세요.

### 3. 대시보드 & REST API (P3)

```powershell
.venv\Scripts\python run_dashboard.py
# 브라우저에서 http://localhost:5000 접속
```

#### 대시보드 탭

| 탭 | 설명 |
|----|------|
| **📊 Overview** | 시스템 현황 카드 (마지막 실행일·종목 수, 60초 자동 갱신) |
| **📋 예측 결과** | 전략·시장·Horizon·TOP-N 필터 + 인터랙티브 테이블 |
| **Strategy Performance** | 전략별 백테스트 성과 차트 |

#### REST API

대시보드 서버 실행 중 아래 엔드포인트를 사용할 수 있습니다:

```bash
# 헬스 체크
curl http://localhost:5000/api/v1/health

# 회귀 예측 TOP 50 (KOSPI)
curl "http://localhost:5000/api/v1/predictions/latest?market=KOSPI&limit=50"

# 서지 예측
curl http://localhost:5000/api/v1/surge/latest

# VCP 패턴 (구조화 JSON)
curl http://localhost:5000/api/v1/vcp/latest

# Lead-Lag 점수
curl http://localhost:5000/api/v1/lead_lag/latest
```

**응답 형식**:
```json
{
  "status": "ok",
  "generated_at": "2026-07-04T09:00:12",
  "count": 50,
  "data": [{"symbol": "005930", "market": "KOSPI", ...}]
}
```

### 4. 오케스트레이터 데몬 (자동 스케줄러)

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

지원 스테이지: `indicators`, `universe`, `train`, `predict`, `score`, `ingest`, `trading`, `weekly_train_predict`, `all`

### 5. 텔레그램 봇 (P0/P2)

```powershell
.venv\Scripts\python telegram_bot_runner.py
```

주요 명령어: `/status`, `/portfolio`, `/buy <symbol> <qty>`, `/sell <symbol> <qty>`

**파이프라인 완료/실패 자동 알림**: `.env`에 아래 값을 설정하면 파이프라인 완료 시 Telegram 메시지가 전송됩니다.
GHA에서 실행 시 `[📊 GHA 결과 보기]` 인라인 버튼이 함께 첨부됩니다.

```ini
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

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