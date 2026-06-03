"""AI/LLM 통합 엔진 - OpenAI 및 Google Gemini API 연동"""

import os
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class SentimentType(Enum):
    """감정 유형"""
    VERY_BULLISH = "매우 긍정적"
    BULLISH = "긍정적"
    NEUTRAL = "중립적"
    BEARISH = "부정적"
    VERY_BEARISH = "매우 부정적"


@dataclass
class InvestmentOpinion:
    """AI 투자 의견"""
    symbol: str
    recommendation: str  # BUY, HOLD, SELL
    sentiment: SentimentType
    confidence: float  # 0.0 ~ 1.0
    target_price: Optional[float] = None
    reasoning: str = ""
    risks: List[str] = None
    opportunities: List[str] = None
    timestamp: datetime = None
    is_simulated: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.risks is None:
            self.risks = []
        if self.opportunities is None:
            self.opportunities = []


class LLMEngine:
    """LLM 엔진 - OpenAI 및 Google Gemini API 통합"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, provider: str = "openai"):
        """
        LLM 엔진 초기화
        
        Args:
            api_key: API 키 (OpenAI 또는 Gemini)
            model: 사용할 모델
            provider: LLM 제공자 ("openai", "gemini")
        """
        self.provider = provider.lower()
        self.logger = logger
        self.query_history = []
        
        # API 클라이언트 및 상태 변수 초기화
        self.client = None
        self.is_v1 = False
        
        if self.provider == "openai":
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            self.model = model or "gpt-3.5-turbo"
            self._init_openai()
        elif self.provider == "gemini":
            self.api_key = api_key or os.getenv("GEMINI_API_KEY")
            self.model = model or "gemini-1.5-pro"
            self._init_gemini()
        else:
            self.logger.warning(f"Unknown provider: {self.provider}. Using simulation mode.")
            self.client = None
            self.api_key = None
            self.model = "unknown"
            
    def _init_openai(self):
        """OpenAI 초기화"""
        try:
            import openai
            if not self.api_key:
                raise ValueError("OpenAI API key is missing. Initializing in simulation mode.")
            if hasattr(openai, 'OpenAI'):
                self.client = openai.OpenAI(api_key=self.api_key)
                self.is_v1 = True
            else:
                openai.api_key = self.api_key
                self.client = openai
                self.is_v1 = False
            self.logger.info(f"OpenAI client initialized with model: {self.model}")
        except Exception as e:
            self.logger.warning(f"OpenAI library initialization failed or key missing ({e}). Using simulation mode.")
            self.client = None
            self.is_v1 = False

    def _init_gemini(self):
        """Gemini 초기화"""
        try:
            import google.generativeai as genai
            if not self.api_key:
                raise ValueError("Gemini API key is missing. Initializing in simulation mode.")
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            self.logger.info(f"Gemini client initialized with model: {self.model}")
        except Exception as e:
            self.logger.warning(f"Google Generative AI library initialization failed or key missing ({e}). Using simulation mode.")
            self.client = None
    
    def query_investment_opinion(self, stock_data: Dict) -> InvestmentOpinion:
        """
        주식에 대한 투자 의견 쿼리
        
        Args:
            stock_data: 주식 데이터
            
        Returns:
            InvestmentOpinion: AI 투자 의견
        """
        symbol = stock_data.get('symbol', 'UNKNOWN')
        
        # 쿼리 생성
        query = self._build_investment_query(stock_data)
        
        # API 호출
        is_sim = False
        if self.client:
            if self.provider == "openai":
                response = self._call_openai_api(query)
            elif self.provider == "gemini":
                response = self._call_gemini_api(query)
            else:
                response = None
                
            if not response:
                response = self._simulate_response(stock_data)
                is_sim = True
        else:
            response = self._simulate_response(stock_data)
            is_sim = True
        
        # 응답 파싱
        opinion = self._parse_opinion_response(response, symbol)
        opinion.is_simulated = is_sim
        
        # 히스토리 저장
        self.query_history.append({
            'symbol': symbol,
            'query': query,
            'response': response,
            'opinion': opinion,
            'timestamp': datetime.now()
        })
        
        self.logger.info(f"Investment opinion for {symbol}: {opinion.recommendation} "
                        f"({opinion.sentiment.value}, conf={opinion.confidence:.2f})")
        
        return opinion
    
    def _build_investment_query(self, stock_data: Dict) -> str:
        """투자 의견 쿼리 생성"""
        symbol = stock_data.get('symbol', 'UNKNOWN')
        price = stock_data.get('price', 0)
        pe_ratio = stock_data.get('pe_ratio', 0)
        pb_ratio = stock_data.get('pb_ratio', 0)
        earnings_growth = stock_data.get('earnings_growth', 0)
        revenue_growth = stock_data.get('revenue_growth', 0)
        dividend_yield = stock_data.get('dividend_yield', 0)
        roe = stock_data.get('roe', 0)
        industry = stock_data.get('industry', 'Unknown')
        market_cap = stock_data.get('market_cap', 0)
        
        # 한국 종목 여부에 따라 통화 포맷 분기
        is_kor = symbol.endswith('.KS') or symbol.endswith('.KQ')
        currency_unit = "원(KRW)" if is_kor else "달러(USD)"
        currency_sym = "₩" if is_kor else "$"
        price_str = f"{currency_sym}{price:,.0f}" if is_kor else f"{currency_sym}{price:,.2f}"
        market_cap_str = f"{currency_sym}{market_cap:,.0f}"
        
        query = f"""
주식 {symbol}에 대한 투자 의견을 분석해주세요.

기본 정보 (통화 단위: {currency_unit}):
- 현재 가격: {price_str}
- 산업: {industry}
- 시가총액: {market_cap_str}

재무 지표:
- PER (주가수익비): {pe_ratio:.2f}
- PBR (주가순자산비): {pb_ratio:.2f}
- ROE: {roe:.1f}%
- 배당율: {dividend_yield:.2f}%

성장률:
- 실적 성장: {earnings_growth:.1f}%
- 매출 성장: {revenue_growth:.1f}%

분석해야 할 항목:
1. 투자 추천 (BUY/HOLD/SELL)
2. 감정도 (매우 긍정적/긍정적/중립적/부정적/매우 부정적)
3. 확신도 (0-100%)
4. 목표 주가 (예상 수치만, 화폐 기호 없이 숫자값으로만 기입)
5. 투자 이유
6. 주요 리스크
7. 기회 요인

JSON 형식으로 답변해주세요.
"""
        return query
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _call_openai_api_with_retry(self, query: str) -> str:
        if self.is_v1:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 전문 투자 분석가입니다. 응답은 반드시 JSON 형식으로만 작성하세요."},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        else:
            response = self.client.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 전문 투자 분석가입니다. 응답은 반드시 JSON 형식으로만 작성하세요."},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response['choices'][0]['message']['content']

    def _call_openai_api(self, query: str) -> str:
        """OpenAI API 호출"""
        try:
            return self._call_openai_api_with_retry(query)
        except Exception as e:
            self.logger.error(f"OpenAI API error after retries: {str(e)}")
            return ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _call_gemini_api_with_retry(self, query: str) -> str:
        system_prompt = "당신은 전문 투자 분석가입니다. 응답은 반드시 JSON 형식으로만 작성하세요."
        full_query = f"{system_prompt}\n\n{query}"
        response = self.client.generate_content(full_query)
        
        # 마크다운 코드 블록 제거 처리
        text = response.text
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        return text.strip()

    def _call_gemini_api(self, query: str) -> str:
        """Gemini API 호출"""
        try:
            return self._call_gemini_api_with_retry(query)
        except Exception as e:
            self.logger.error(f"Gemini API error after retries: {str(e)}")
            return ""
    
    def _simulate_response(self, stock_data: Dict) -> str:
        """응답 시뮬레이션"""
        symbol = stock_data.get('symbol', 'UNKNOWN')
        pe_ratio = stock_data.get('pe_ratio', 20)
        earnings_growth = stock_data.get('earnings_growth', 10)
        
        # PER와 성장률을 바탕으로 의견 결정
        if pe_ratio < 15 and earnings_growth > 10:
            recommendation = "BUY"
            sentiment = "매우 긍정적"
            confidence = 85
        elif pe_ratio < 20 and earnings_growth > 5:
            recommendation = "BUY"
            sentiment = "긍정적"
            confidence = 70
        elif pe_ratio > 25 or earnings_growth < 0:
            recommendation = "SELL"
            sentiment = "부정적"
            confidence = 70
        else:
            recommendation = "HOLD"
            sentiment = "중립적"
            confidence = 60
        
        response = {
            'recommendation': recommendation,
            'sentiment': sentiment,
            'confidence': confidence,
            'target_price': stock_data.get('price', 100) * (1 + earnings_growth / 100),
            'reasoning': f"{symbol} 주식은 현재 {sentiment} 상태입니다.",
            'risks': [
                '시장 변동성',
                '경기 부양 여부',
                '경쟁사 동향'
            ],
            'opportunities': [
                '신제품 출시',
                '해외 시장 진출',
                '기술 혁신'
            ]
        }
        return json.dumps(response, ensure_ascii=False)
    
    def _parse_opinion_response(self, response: str, symbol: str) -> InvestmentOpinion:
        """AI 응답 파싱"""
        try:
            # JSON 형식의 응답 파싱
            data = json.loads(response) if isinstance(response, str) else response
        except (json.JSONDecodeError, TypeError, ValueError):
            # 파싱 실패 시 시도: 마크다운 파싱을 위함이거나 텍스트 내에서 JSON 추출
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    raise ValueError("No JSON found")
            except Exception:
                # 파싱 실패 시 기본값
                data = {
                    'recommendation': 'HOLD',
                    'sentiment': '중립적',
                    'confidence': 50,
                    'reasoning': '분석 불가',
                    'risks': [],
                    'opportunities': []
                }
        
        # 감정도를 Enum으로 변환
        sentiment_map = {
            '매우 긍정적': SentimentType.VERY_BULLISH,
            '긍정적': SentimentType.BULLISH,
            '중립적': SentimentType.NEUTRAL,
            '부정적': SentimentType.BEARISH,
            '매우 부정적': SentimentType.VERY_BEARISH,
        }
        
        sentiment_str = data.get('sentiment', '중립적')
        sentiment = sentiment_map.get(sentiment_str, SentimentType.NEUTRAL)
        
        confidence = data.get('confidence', 50)
        confidence = min(100, max(0, confidence)) / 100  # 0-1 범위로 정규화
        
        return InvestmentOpinion(
            symbol=symbol,
            recommendation=data.get('recommendation', 'HOLD'),
            sentiment=sentiment,
            confidence=confidence,
            target_price=data.get('target_price'),
            reasoning=data.get('reasoning', ''),
            risks=data.get('risks', []),
            opportunities=data.get('opportunities', [])
        )
    
    def batch_query_stocks(self, stocks_data: List[Dict]) -> Dict[str, InvestmentOpinion]:
        """여러 주식 배치 쿼리"""
        opinions = {}
        
        for stock in stocks_data:
            symbol = stock.get('symbol')
            try:
                opinion = self.query_investment_opinion(stock)
                opinions[symbol] = opinion
            except Exception as e:
                self.logger.error(f"Error querying {symbol}: {str(e)}")
        
        return opinions
    
    def get_consensus_with_ai(self, stock_data: Dict, 
                             investor_opinions: Dict) -> Dict:
        """AI와 투자자 의견의 합의 도출"""
        ai_opinion = self.query_investment_opinion(stock_data)
        
        # AI 의견 + 투자자 의견 통합
        buy_count = sum(1 for op in investor_opinions.values() 
                       if op.recommendation == "BUY")
        buy_count += 1 if ai_opinion.recommendation == "BUY" else 0
        
        total = len(investor_opinions) + 1
        ai_weight = 1.5  # AI 의견에 1.5배 가중치
        
        weighted_confidence = (
            (sum(op.confidence for op in investor_opinions.values()) + 
             ai_opinion.confidence * ai_weight) / (len(investor_opinions) + ai_weight)
        )
        
        if buy_count >= total * 0.6:
            consensus = "강한 매수"
        elif buy_count >= total * 0.4:
            consensus = "매수"
        elif buy_count >= total * 0.3:
            consensus = "보유"
        else:
            consensus = "매도"
        
        return {
            'consensus': consensus,
            'ai_opinion': ai_opinion,
            'investor_opinions': investor_opinions,
            'buy_ratio': buy_count / total,
            'weighted_confidence': weighted_confidence,
            'recommendation': ai_opinion.recommendation
        }
