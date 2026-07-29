# 📈 Stock Trading System — 통합 주식 자동매매 및 예측 파이프라인

한국(KOSPI/KOSDAQ/KONEX) 및 미국(S&P 500) 시장의 **3,379개 종목**을 대상으로 **17대 다변화 전략(Multi-Factor & Multi-Model)**을 병행 운영하고 2D 시장 레짐 기반 동적 앙상블 및 리스크 관리 시스템을 구동하는 통합 예측 파이프라인입니다.

자동 업데이트되는 라이브 웹 대시보드: **[https://kthur.github.io/stock/](https://kthur.github.io/stock/)**

---

## 🎯 17대 다변화 전략 개요

| # | 전략 | 방식 | 주요 특징 및 출력 파일 |
|---|------|------|------------------------|
| **1** | XGBoost 회귀 | 8개 horizon(1~200d) 예상수익률 예측 | 펀더멘탈 + 매크로 23개 피처 (`pipeline_result.txt`) |
| **2** | Surge 분류기 | 4개 horizon(1/3/5/20d) 20%↑ 급등 확률 | Class Weight 캡 ≤20.0 (`surge_predictions.txt`) |
| **3** | Lead-Lag 분석 | 2-Tier 업종 지수/대형주 시차 상관성 | US ETF 1일 Lag Shift 시차 추종 (`lead_lag_predictions.txt`) |
| **4** | VCP 패턴 (규칙) | 변동성 수축 + 거래량 감소 + 고점 근접 | Mark Minervini 4단계 변동성 수축 (`vcp_patterns.txt`) |
| **5** | VCP ML | 시장별 XGBClassifier 기반 VCP 급등 | 11개 VCP 정밀 패턴 피처 (`vcp_ml_predictions.txt`) |
| **6** | Strict Causal LSTM | 시점 분리 롤링 정규화 기반 시계열 DL | 미소 시점 데이터 누수 방지 딥러닝 앙상블 |
| **7** | Stat-Arb Cointegration | 잔차 평균회귀 Log 가격 Z-score 차익거래 | 공적분 페어 스캐닝 (`stat_arb_predictions.txt`) |
| **8** | Sector Rotation | KRX/GICS 업종 1M/3M 상대모멘텀 | 순환매 수급 및 상대모멘텀 스코어링 |
| **9** | RIM Valuation | 잔여이익 모델 기반 정밀 가치평가 | 적정주가 대비 할인율/괴리율 평가 (터미널 Value 보정) |
| **10** | Event-Driven | 공시/실적 깜짝실적/자사주 취득 촉매 | DART 공시 감지 및 거래량 3배 수치화 |
| **11** | Momentum Quality (MQ) | 12M-1M 모멘텀 - 1M 단기 반전 노이즈 제거 | 영업이익률/ROE 퀄리티 결합 모멘텀 |
| **12** | Options IV Skew | yfinance 풋/콜 풋옵션 IV Skew 및 비율 | 공포 지수 반대 매수 스코어링 |
| **13** | Order Flow Imbalance | 외인/기관 순매수 수급 가속도 (MFI) | 자금 유입 가속도 및 수급 불균형 |
| **14** | Short-Term Reversal | 3~5일 연속 과매도/볼린저 하단 이탈 | 펀더멘탈 안전장치 결합 평균회귀 |
| **15** | Analyst Revision (ARM) | 컨센서스 EPS/목표주가 수정 모멘텀 | 실적 컨센서스 상향 조정 속도 측정 |
| **16** | Cross-Asset Divergence (CARD)| 주식-환율-유가-금리 크로스에셋 괴리율 | 이탈 괴리율 역발상 스코어링 |
| **17** | Liquidity Tail Risk (LATR) | 52주 낙폭 + 유동성 서지 - 꼬리위험 | 위험 자산 페널티 차감 유동성 팩터 |

---

## 🛡️ 시스템 정밀 감사 및 개선 내역 (Phase 1 ~ Phase 4)

본 시스템은 금융공학 및 퀀트 시스템 감사(Phase 1~4)를 거쳐 다음과 같은 정밀 보정이 적용되어 있습니다:

- **Phase 1 (긴급 시스템 정비)**:
  - 17대 전체 전략 앙상블(`ensemble_scorer.py`) 통합 및 구문 안정화.
  - SQLite WAL 매니저 및 `StockPriceDB` 쓰기 뮤텍스(`_write_lock`) 적용으로 DB Lock 예외 방지.
  - `RiskManager` 및 `CrisisDetector` 파이프라인 연동 (거시 위기 시 점수 자동 제어).
  - Config 최소 거래대금(50억 원) 및 거래량(100만 주) 유동성 게이트 적용.
- **Phase 2 (데이터 무결성 & 시점이탈 제거)**:
  - 재무 데이터 공시일 기준 60일 시차(`+60 days`) 적용으로 Lookahead Bias 제거.
  - Lead-Lag 미국 지수 1일 Lag Shift 적용.
  - Stat-Arb Log 주가 공적분 회귀 변환.
- **Phase 3 (퀀트 수식 & HPO 최적화)**:
  - RIM 가치평가 모델 Terminal Value 중복 할인 보정.
  - LATR 팩터 꼬리위험/낙폭 부호 및 페널티 정상화.
  - Optuna VCP HPO 목적함수를 5일 전방 수익률(Forward Return) 기반으로 재설계.
- **Phase 4 (거래 미시구조 & 실전 실행 비용)**:
  - 증권거래세(STT), 미국 SEC 수수료, 호가 갭(Spread), ADV 거래대금 시장 충격 비용(Market Impact) 모델링.
  - 포트폴리오 추천순위를 순예상수익률(`ensemble_expected_return`) 기준으로 내림차순 정렬.
  - Intermediate GC 도입으로 메모리 힙 최적화.

---

## 🕒 타임존 및 결측 분석 (KST & Strategy Coverage)

- **KST (Asia/Seoul, UTC+9) 표준화**:
  - GHA Workflow (`pipeline.yml`), 파이프라인 및 HTML 리포트 타임스탬프가 **KST** 기준으로 통일 표기됩니다.
- **2D Market Regime & Decision Rationale**:
  - 6가지 2D 레짐(`BULL_LOW_VOL`, `BEAR_HIGH_VOL` 등) 판정 사유 및 17대 전략 동적 가중치 산출 근거를 텍스트 및 대시보드로 수록.
- **Strategy Data Coverage & Missingness Analyzer**:
  - `StrategyCoverageAnalyzer` 모듈이 17대 전략별 정상 스코어 산출 종목 수 및 결측 사유(`NO_PRICE_DATA`, `NO_FUNDAMENTAL`, `NO_OPTIONS_DATA` 등)를 추적하여 `strategy_data_coverage_report.txt`로 생성합니다.

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
```

### 3. 대시보드 리포트 생성 및 확인

```powershell
# HTML 대시보드 리포트 생성
.venv\Scripts\python trading_system/generate_report.py --out gh-pages/index.html

# 브라우저에서 https://kthur.github.io/stock/ 또는 로컬 index.html 열기
```

---

## 📂 출력 파일 구조

파이프라인 완료 후 `trading_system/result/` 에 생성됩니다:

| 파일 | 형식 | 설명 |
|------|------|------|
| `ensemble_predictions.txt` | 텍스트 요약 | **17대 전략 동적 앙상블 TOP 20** 및 Decision Rationale |
| `strategy_data_coverage_report.txt` | 텍스트 보고서 | **17대 전략 데이터 커버리지 & 결측 사유 분석** |
| `pipeline_result.txt` | 텍스트 요약 | TOP10/시장/horizon (1d/5d/20d/60d) 예상수익률 |
| `pipeline_result.csv` | CSV | 전체 종목 원본 데이터 (기계 가독) |
| `surge_predictions.txt` | 텍스트 | horizon별 급등 확률 TOP20 |
| `lead_lag_predictions.txt` | 텍스트 | Leader-Follower 상관 점수 |
| `vcp_patterns.txt` | 텍스트 | VCP 패턴 감지 종목 |
| `vcp_ml_predictions.txt` | 텍스트 | VCP ML surge 확률 TOP10 |
| `stat_arb_predictions.txt` | 텍스트 | 공적분 잔차 Z-score 차익거래 페어 |

---

## 🧪 테스트 스위트 실행

```powershell
# 17대 전략 및 결측 분석 / KST 타임존 전체 pytest
.venv\Scripts\python -m pytest tests/ -v
```

---

## 🔔 Telegram 알림 설정

`.env` 설정:
```ini
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```
