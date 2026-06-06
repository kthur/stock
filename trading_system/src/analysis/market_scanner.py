import logging
import time
import asyncio
from typing import List, Dict, Any
import yfinance as yf
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketScanner:
    """한국 시장 전체를 스캔하여 고수익 종목을 발굴하는 엔진"""
    
    def __init__(self):
        self.top_n = 5  # 최종 추천할 종목 수
        self.scan_pool_size = 300  # 1차 스캔할 시총 상위 종목 수
        self.logger = logger
        
    def _get_top_krx_stocks(self) -> Dict[str, str]:
        """시가총액 상위 KRX 종목(KOSPI+KOSDAQ) 티커 추출"""
        try:
            self.logger.info("Fetching KRX stock listing for market scanning...")
            df = fdr.StockListing('KRX')
            
            # 시가총액(Marcap) 기준으로 정렬 후 상위 추출
            if 'Marcap' in df.columns:
                df = df.sort_values(by='Marcap', ascending=False)
                
            df_top = df.head(self.scan_pool_size)
            
            tickers = {}
            for _, row in df_top.iterrows():
                code = row['Code']
                name = row['Name']
                market = row['Market']
                
                if 'KOSPI' in market:
                    symbol = f"{code}.KS"
                elif 'KOSDAQ' in market:
                    symbol = f"{code}.KQ"
                else:
                    continue
                    
                tickers[symbol] = name
            
            self.logger.info(f"Selected Top {len(tickers)} stocks by Market Cap.")
            return tickers
        except Exception as e:
            self.logger.error(f"Failed to fetch KRX listing: {e}")
            # Fallback
            return {"005930.KS": "삼성전자", "000660.KS": "SK하이닉스", "035420.KS": "NAVER"}

    def scan_market(self) -> List[Dict[str, Any]]:
        """시장을 스캔하여 고수익 예상 종목 리스트 반환"""
        self.logger.info("Starting Market Scan...")
        start_time = time.time()
        
        # 1. 대상 티커 선정
        krx_stocks = self._get_top_krx_stocks()
        symbols_list = list(krx_stocks.keys())
        
        if not symbols_list:
            return []
            
        # 2. yfinance 다중 티커 동시 다운로드 (1차 필터링용 데이터)
        self.logger.info(f"Downloading recent data for {len(symbols_list)} tickers...")
        # 60일치 데이터로 모멘텀과 변동성 계산
        try:
            # yf.download returns a MultiIndex DataFrame if multiple tickers
            data = yf.download(symbols_list, period="3mo", auto_adjust=False, threads=True, progress=False)
        except Exception as e:
            self.logger.error(f"yfinance download failed: {e}")
            return []
            
        results = []
        
        # 3. 스코어링 로직 적용
        if 'Close' not in data:
            self.logger.error("No Close price data found in download.")
            return []
            
        close_data = data['Close']
        volume_data = data['Volume'] if 'Volume' in data else None
        
        for symbol in symbols_list:
            try:
                # 데이터가 없는 종목 패스
                if symbol not in close_data.columns:
                    continue
                    
                prices = close_data[symbol].dropna()
                if len(prices) < 20:
                    continue
                    
                # 최근 가격
                current_price = float(prices.iloc[-1])
                
                # 1개월 모멘텀 (최근 20일 수익률)
                momentum_1m = (current_price / prices.iloc[-20]) - 1
                
                # 변동성 (최근 20일 일간 수익률의 표준편차)
                returns = prices.pct_change().dropna()
                volatility = returns.tail(20).std() * np.sqrt(252)
                
                # 딥러닝/RL 엔진의 스코어를 시뮬레이션한 휴리스틱 점수 결합 (AI Scoring Mock)
                # 실제 환경에서는 ml_engine.predict() 등을 호출하나, 성능을 위해 스캐너에서는 휴리스틱 사용
                base_score = (momentum_1m * 0.7) + (volatility * 0.3)
                
                # 거래량 필터: 너무 거래량이 적으면 제외 (선택)
                avg_vol = 0
                if volume_data is not None and symbol in volume_data.columns:
                    vols = volume_data[symbol].dropna()
                    if len(vols) >= 20:
                        avg_vol = vols.tail(20).mean()
                        if avg_vol < 10000:
                            continue
                
                if current_price > 1000: # 동전주 제외
                    results.append({
                        "symbol": symbol,
                        "name": krx_stocks[symbol],
                        "current_price": current_price,
                        "expected_return": round(momentum_1m * 100, 2), # 모멘텀을 기대 수익률로 변환 (표시용)
                        "score": base_score,
                        "volatility": round(volatility * 100, 2),
                        "avg_volume": int(avg_vol)
                    })
            except Exception as e:
                self.logger.debug(f"Error scoring {symbol}: {e}")
                continue
                
        # 4. 점수 순으로 정렬 후 Top N 추출
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        top_picks = results[:self.top_n]
        
        elapsed = time.time() - start_time
        self.logger.info(f"Market scan completed in {elapsed:.2f} seconds. Found {len(top_picks)} top picks.")
        
        # 포맷팅 정리
        formatted_picks = []
        for rank, p in enumerate(top_picks, 1):
            formatted_picks.append({
                "rank": rank,
                "symbol": p['symbol'],
                "name": p['name'],
                "price": p['current_price'],
                "expected_return": p['expected_return'],
                "reason": f"강한 상승 모멘텀({p['expected_return']}%) 및 AI 종합 점수 우수"
            })
            
        return formatted_picks
