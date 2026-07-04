# 📈 Stock Trading System — 통합 주식 자동매매 및 예측 파이프라인

한국(KOSPI/KOSDAQ/KONEX) 및 미국(S&P 500) 시장의 **3,379개 종목**을 대상으로
5개 ML/규칙 기반 전략을 병행 운영하는 통합 예측 파이프라인입니다.

---

## 🎯 5대 전략 개요

| # | 전략 | 방식 | 출력 파일 |
|---|------|------|-----------|
| **1** | XGBoost 회귀 | 8개 horizon(1~200일) 예상수익률 예측 | `pipeline_result.txt` / `.csv` |
| **2** | Surge 분류기 | 4개 horizon(1/3/5/20일) 20%↑ 급등 확률 | `surge_predictions.txt` / `.csv` |
| **3** | Lead-Lag 분석 | 시총 TOP50 leader 상관관계 기반 후행 종목 발굴 | `lead_lag_predictions.txt` |
| **4** | VCP 패턴 (규칙) | 변동성 수축 + 거래량 감소 + 고점 근접 규칙 | `vcp_patterns.txt` |
| **5** | VCP ML | 시장별 XGBClassifier 기반 VCP 급등 확률 | `vcp_ml_predictions.txt` |

---

## 🚀 빠른 시작 (Quick Start)

### 1. 환경 구성

```powershell
# 프로젝트 루트에서
python -m venv .venv
.venv\Scripts\activate
pip install -r trading_system/requirements.txt

# .env 설정
copy trading_system\.env.example trading_system\.env
# .env 파일 편집 후 저장
```

### 2. 파이프라인 실행 (CLI)

```powershell
# 기본 실행 (전 시장, 전략 학습 포함)
.venv\Scripts\python trading_system/run_pipeline.py

# 특정 시장만 추론 (학습은 전체 유니버스 유지)
.venv\Scripts\python trading_system/run_pipeline.py --target KOSPI
.venv\Scripts\python trading_system/run_pipeline.py --target SP500
.venv\Scripts\python trading_system/run_pipeline.py --target KRX   # KOSPI+KOSDAQ+KONEX

# 기존 모델 재사용 (학습 건너뛰기 — 빠른 재예측)
.venv\Scripts\python trading_system/run_pipeline.py --skip-training

# 디버그 모드 (시장별 3종목만 샘플 — 빠른 동작 검증)
.venv\Scripts\python trading_system/run_pipeline.py --debug

# 조합 예시
.venv\Scripts\python trading_system/run_pipeline.py --target KOSDAQ --skip-training --debug
```

> **참고**: 첫 실행 시 3,379개 종목의 주가 데이터를 다운로드하므로 수십 분이 소요됩니다.
> 이후 실행에서는 로컬 SQLite 캐시(`stock_prices.db`)를 활용합니다.

### 3. 대시보드 실행

```powershell
.venv\Scripts\python trading_system/run_dashboard.py
# 브라우저에서 http://localhost:5000 접속
```

---

## 📊 CLI 진행률 표시 (tqdm)

파이프라인 실행 중 터미널에 실시간 진행 상황이 표시됩니다:

```
📥 Training data:  45%|████████▌          | 1521/3379 [02:14<02:43, 11.3sym/s] loaded=1488
📡 Inference data: 78%|███████████████▌   | 2636/3379 [01:47<00:30, 24.1sym/s] loaded=2589
```

---

## 📂 출력 파일 구조

파이프라인 완료 후 `trading_system/result/` 에 생성됩니다:

| 파일 | 형식 | 크기 | 설명 |
|------|------|------|------|
| `pipeline_result.txt` | 텍스트 요약 | ~5KB | TOP10/시장/horizon (1d/5d/20d/60d) |
| `pipeline_result.csv` | CSV | ~2MB | 전체 종목 원본 데이터 (기계 가독) |
| `pipeline_result.jsonl` | JSON Lines | ~3MB | JSON 스트리밍 형식 |
| `surge_predictions.txt` | 텍스트 | ~17KB | horizon별 급등 확률 TOP20 |
| `surge_predictions.csv` | CSV | ~300KB | 서지 예측 전체 원본 |
| `lead_lag_predictions.txt` | 텍스트 | ~3.5KB | Leader-Follower 상관 점수 |
| `vcp_patterns.txt` | 텍스트 | ~2.4KB | VCP 패턴 감지 종목 |
| `vcp_ml_predictions.txt` | 텍스트 | ~7.5KB | VCP ML surge 확률 TOP10 |

> `pipeline_result.txt`는 요약본입니다. 전체 데이터는 `.csv` / `.jsonl` 파일을 사용하세요.

### 출력 파일 예시 (`pipeline_result.txt`)

```
=== Pipeline Inference Summary (TOP10 per Market) ===
Date: 2026-07-04 09:00
Total symbols analyzed: 3,379
Showing: Top 10 per market | Horizons: 1d, 5d, 20d, 60d
Full data: pipeline_result.csv / pipeline_result.jsonl

============================================================
Horizon: 1d

--- KOSPI TOP 10 ---
  1. 308170 (씨티알모빌리티): +0.54%
  2. 064400 (LG씨엔에스): +0.54%
  ...
--- S&P 500 TOP 10 ---
  1. SMCI (Super Micro): +2.31%
  ...
```

---

## 🔔 Telegram 알림 설정

파이프라인 완료/실패 시 Telegram으로 알림을 받으려면 `.env`에 설정합니다:

```ini
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Telegram 알림 예시

```
──────────────────────────────
✅ [SUCCESS] Pipeline Alert
──────────────────────────────
✅ 파이프라인 완료
⏱ 소요시간: 42.3분
📅 실행시각: 2026-07-04 09:47
[📊 GHA 결과 보기]  ← 인라인 버튼 (GHA 실행 시)
```

```
──────────────────────────────
🚨 [CRITICAL] Pipeline Alert
──────────────────────────────
🚨 파이프라인 실패
⏱ 소요시각: 5.2분
❌ 오류: ConnectionError: ...
[📋 에러 로그 보기]  ← 인라인 버튼 (GHA 실행 시)
```

> **Bot 생성**: [@BotFather](https://t.me/botfather) → `/newbot` → 토큰 복사  
> **Chat ID 확인**: `https://api.telegram.org/bot<TOKEN>/getUpdates`

---

## 🌐 웹 대시보드 & REST API

### 대시보드 탭 구성

| 탭 | 설명 |
|----|------|
| **📊 Overview** | 시스템 현황 카드 (마지막 실행일, 분석 종목 수, 60초 자동 갱신) |
| **📋 예측 결과** | 전략·시장·Horizon·TOP-N 동적 필터 + 인터랙티브 테이블 |
| **Strategy Performance** | 전략별 백테스트 성과 차트 |
| *(기타 탭)* | Macro, Screener, Portfolio, Risk 등 |

### REST API 엔드포인트

대시보드 서버가 실행 중일 때 `http://localhost:5000` 에서 사용 가능합니다:

```bash
# 헬스 체크 (마지막 파이프라인 실행 시각 등)
curl http://localhost:5000/api/v1/health

# 회귀 예측 전체 (선택: ?market=KOSPI&limit=50)
curl "http://localhost:5000/api/v1/predictions/latest?market=KOSPI&limit=50"

# 서지 예측 (선택: ?market=SP500&limit=20)
curl "http://localhost:5000/api/v1/surge/latest"

# VCP 패턴 (구조화 JSON)
curl http://localhost:5000/api/v1/vcp/latest

# Lead-Lag 점수
curl http://localhost:5000/api/v1/lead_lag/latest
```

### API 응답 형식

```json
{
  "status": "ok",
  "generated_at": "2026-07-04T09:00:12",
  "count": 50,
  "data": [
    {"symbol": "005930", "market": "KOSPI", "name": "삼성전자", "1": 0.0021, ...},
    ...
  ]
}
```

---

## ⚙️ 주요 환경 변수 (.env)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `TRAIN_SAMPLE_SP500` | `50` | SP500 학습 종목 수 (`all` = 전량) |
| `TRAIN_SAMPLE_KRX` | `50` | KRX 학습 종목 수 (`all` = 전량) |
| `SKIP_TRAINING` | `False` | `True` 시 기존 모델 재사용 |
| `STOCK_PRICE_FRESHNESS_DAYS` | `7` | 캐시 유효일 (`none` = 오프라인) |
| `TRAIN_START_DATE` | `2006-01-01` | 학습 데이터 시작일 |
| `INFERENCE_TARGET` | `SP500,KRX` | 추론 대상 시장 |
| `DEBUG_MODE` | `False` | `True` 시 시장별 3종목만 샘플 |
| `TELEGRAM_BOT_TOKEN` | *(없음)* | Telegram 알림용 봇 토큰 |
| `TELEGRAM_CHAT_ID` | *(없음)* | Telegram 수신 Chat ID |

전체 목록: [CONFIGURATION_REFERENCE.md](trading_system/docs/CONFIGURATION_REFERENCE.md)

---

## 🤖 GitHub Actions 자동화

`.github/workflows/pipeline.yml` 에 의해 매일 자동 실행됩니다.

### 시크릿 설정 (Repository → Settings → Secrets)

| 시크릿 이름 | 용도 |
|------------|------|
| `TELEGRAM_BOT_TOKEN` | 파이프라인 완료/실패 Telegram 알림 |
| `TELEGRAM_CHAT_ID` | Telegram 수신 대상 Chat ID |

### GHA Step Summary 예시

Actions 탭에서 로그를 열지 않고 결과를 한눈에 확인합니다:

```
## ✅ Pipeline: KOSPI

### ⚙️ 실행 정보
| 항목 | 값 |
|------|----|
| 상태 | success |
| 실행 일시 | 2026-07-04 09:47 KST |

### 📁 출력 파일 현황
| 파일 | 크기 | 줄 수 |
|------|------|-------|
| pipeline_result.txt | 4.2K | 98 |
| surge_predictions.txt | 18K | 390 |
| pipeline_result.csv | 2.1M | 3380 |
```

---

## 🤖 자율 주식 거래 에이전트

예측 파이프라인 신호를 수신하여 실제 계좌 거래를 실행하는 자동화 모듈 (`src/ai/trading_agent.py`):

- **Rule 1** (위험 관리): 단일 거래당 총 자본금 최대 2% 리스크 제한
- **Rule 2** (감성 & VIX 필터): 뉴스 감성 < -0.2 또는 VIX > 30.0 시 진입 차단
- **Rule 3** (통계적 우위): 승률 55%↑ 및 기댓값 > 0 검증 후 진입
- **Rule 4** (보고 의무): 매매 전 근거 보고서 Telegram 자동 알림
- **Rule 5** (비상 프로토콜): 지수 일일 변동성 5%↑ 시 전량 현금화

---

## 📂 프로젝트 구조

```
stock/
├── trading_system/
│   ├── run_pipeline.py          ← 통합 파이프라인 (CLI: --target/--skip-training/--debug)
│   ├── run_dashboard.py         ← 대시보드 서버 실행
│   ├── orchestrator.py          ← 자동 스케줄러 데몬
│   ├── requirements.txt         ← 의존성 (tqdm 포함)
│   ├── result/                  ← 파이프라인 출력 파일 (.txt/.csv/.jsonl)
│   ├── src/
│   │   ├── ai/                  ← ML 모델 (prediction_model, vcp_detector, vcp_ml_predictor)
│   │   ├── data_layer/          ← 데이터 수집·저장 (indicator_storage, earnings_data)
│   │   ├── web/
│   │   │   ├── dashboard.py     ← Plotly Dash 대시보드
│   │   │   ├── api.py           ← REST API 엔드포인트 (P3)
│   │   │   └── assets/
│   │   │       └── responsive.css  ← 반응형 CSS (P2)
│   │   ├── persistence/         ← DB 영속 계층 (SQLite)
│   │   ├── telegram_bot/        ← Telegram 봇 엔진
│   │   └── config.py            ← TradingConfig (.env 기반)
│   ├── models/                  ← XGBoost 모델 파일 (.json, Git 미추적)
│   ├── tests/                   ← pytest 테스트 스위트
│   └── docs/                    ← 상세 설계 문서
├── .github/workflows/
│   └── pipeline.yml             ← GHA 자동 실행 워크플로우
├── AGENTS.md                    ← AI 에이전트 참조 문서
├── OPTIMIZATION_REPORT.md       ← 성능 최적화 보고서
└── README.md                    ← 이 문서
```

---

## 📚 상세 문서

| 문서 | 설명 |
|------|------|
| [trading_system/README.md](trading_system/README.md) | 설치 가이드, CLI 상세, 트러블슈팅 |
| [ALGORITHMS_AND_STRATEGY.md](trading_system/docs/ALGORITHMS_AND_STRATEGY.md) | 5대 전략 알고리즘 상세 |
| [SYSTEM_ARCHITECTURE.md](trading_system/docs/SYSTEM_ARCHITECTURE.md) | 시스템 아키텍처 및 데이터 흐름 |
| [CONFIGURATION_REFERENCE.md](trading_system/docs/CONFIGURATION_REFERENCE.md) | `.env` 환경 변수 완전 참조 |
| [KNOWN_ISSUES.md](trading_system/docs/KNOWN_ISSUES.md) | 알려진 이슈 및 개선 로드맵 |
| [TEST_GUIDE.md](trading_system/docs/TEST_GUIDE.md) | 테스트 인프라 및 실행 가이드 |
| [OPTIMIZATION_REPORT.md](OPTIMIZATION_REPORT.md) | 성능 최적화 분석 보고서 |

---

## 🧪 테스트 실행

```powershell
# 전체 테스트 (240+ 케이스)
.venv\Scripts\pytest trading_system/tests/ -v

# 빠른 검증 (실패 즉시 중단)
.venv\Scripts\pytest trading_system/tests/ -x -q

# 특정 테스트만
.venv\Scripts\pytest trading_system/tests/test_e2e_consolidated.py -v
```
