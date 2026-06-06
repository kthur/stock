# Original User Request

## 2026-06-06T10:39:26Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

주식 트레이딩 시스템(Phase 3)의 수익률과 사용성을 극대화하기 위해, 감성 분석, 강화학습(RL), 자산 배분 알고리즘을 추가하고, PDF 리포트 자동 생성 및 실제 증권사 API 연동 뼈대를 구축합니다.

Working directory: d:/Finance/code/stock/trading_system
Integrity mode: development

## Requirements

### R1. 고급 수익률 개선 모듈 구현
- 뉴스/커뮤니티 데이터를 기반으로 한 LLM 감성 분석(Sentiment Analysis) 파이프라인 구축
- DQN 또는 PPO 기반의 강화학습(RL) 트레이딩 모델 뼈대 작성
- 포트폴리오 비중을 동적으로 재분배하는 자산 배분(Asset Allocation) 로직 구현

### R2. 사용성 및 시스템 고도화
- 백테스트 결과 및 매매 일지를 바탕으로 성과를 시각화한 PDF 레포트 자동 생성 기능 추가
- 한국투자증권 또는 키움증권 등 실제 브로커리지 API 연동을 위한 추상화된 Broker 클래스 및 연결 뼈대 작성

## Acceptance Criteria

### 수익률 개선 모듈 검증
- [ ] 감성 분석: 더미 텍스트를 입력했을 때 긍정/부정 점수(Score)를 반환하는 스크립트가 오류 없이 실행되어야 합니다.
- [ ] 강화학습: `stable-baselines3` 또는 PyTorch를 사용하여 임의의 가격 데이터를 통해 RL 모델이 학습(train) 사이클을 1회 이상 정상 통과해야 합니다.
- [ ] 자산 배분: 3개 무의 종목과 가격 데이터가 주어졌을 때, 각 종목의 투자 비중(%) 합이 100%가 되도록 분배하는 함수가 정상 동작해야 합니다.

### 사용성 고도화 검증
- [ ] PDF 레포트: 모의 매매 결과 데이터를 입력받아 로컬 시스템에 `.pdf` 파일을 성공적으로 생성하고 저장해야 합니다.
- [ ] 브로커 API: `RealBroker` 클래스의 인스턴스를 생성하고, 가상의 API 연결 메서드(`connect()`)와 주문 메서드(`submit_order()`)가 예외(Exception) 없이 호출되어야 합니다.
