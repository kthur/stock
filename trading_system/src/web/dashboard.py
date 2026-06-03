"""Web Dashboard - FastAPI 기반 웹 대시보드"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import logging
import json
import urllib.parse
import uuid
import math
import concurrent.futures
import urllib.request
import os

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import HTMLResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = None
    WebSocket = None

logger = logging.getLogger(__name__)

from src.utils.stock_list import get_tickers, get_tickers_rev
from src.core.order_management import OrderType

class WebDashboard:
    """웹 대시보드"""
    
    def __init__(self, trading_system, event_bus=None, host: str = '127.0.0.1', port: int = 5000):
        """
        초기화
        
        Args:
            trading_system: 트레이딩 시스템 인스턴스
            event_bus: 이벤트 버스
            host: 호스트
            port: 포트
        """
        self.trading_system = trading_system
        self.event_bus = event_bus
        self.host = host
        self.port = port
        self.logger = logger
        self._enabled = HAS_FASTAPI
        self.active_connections = []
        self.scan_tasks = {}
        
        if HAS_FASTAPI:
            self.app = FastAPI(title="Stock Trading Dashboard")
            self._setup_routes()
            
            # 이벤트 버스 구독 등록 (비동기 처리 - 이벤트 루프 안전)
            if self.event_bus:
                def _safe_schedule(coro_func, *args):
                    """이벤트 루프가 존재할 때만 안전하게 태스크를 스케줄링"""
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(coro_func(*args))
                    except RuntimeError:
                        pass  # 이벤트 루프가 없으면 무시 (서버 시작 전)
                
                self.event_bus.subscribe("market_data", lambda data: _safe_schedule(self.broadcast_market_data, data))
                self.event_bus.subscribe("account_sync", lambda data: _safe_schedule(self.broadcast_portfolio_update))
                self.event_bus.subscribe("order_status", lambda data: _safe_schedule(self.broadcast_order_update, data))
            
            self.logger.info("FastAPI Web Dashboard initialized with Native WebSockets.")
        else:
            self.app = None
            self.logger.warning("FastAPI is not installed. Web dashboard will be disabled. To enable, run: pip install fastapi uvicorn")
    
    def _setup_routes(self):
        """라우트 설정"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            """메인 대시보드"""
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            return HTMLResponse(content=self.get_dashboard_html(), headers=headers)
        
        @self.app.get("/api/portfolio")
        async def api_portfolio():
            """포트폴리오 정보"""
            status = self.trading_system.get_trading_status()
            return {
                'status': 'success',
                'data': {
                    'cash': status['cash'],
                    'positions': status['positions'],
                    'timestamp': status['timestamp']
                }
            }

        @self.app.get("/api/portfolio/history")
        async def api_portfolio_history():
            """포트폴리오 자산 이력 (Chart.js 용도)"""
            if hasattr(self.trading_system, 'comp') and 'db' in self.trading_system.comp:
                try:
                    history = await self.trading_system.comp['db'].get_history(limit=100)
                    # 역순 정렬 (과거 -> 현재)
                    history.reverse()
                    
                    labels = []
                    values = []
                    
                    for row in history:
                        # 날짜 포맷 정리 (YYYY-MM-DD HH:MM)
                        dt = datetime.fromisoformat(row['timestamp'])
                        labels.append(dt.strftime("%Y-%m-%d %H:%M"))
                        values.append(row['total_value'])
                        
                    return {
                        'status': 'success',
                        'data': {
                            'labels': labels,
                            'values': values
                        }
                    }
                except Exception as e:
                    self.logger.error(f"Failed to fetch portfolio history: {e}")
                    return {'status': 'error', 'message': str(e)}
            return {'status': 'error', 'message': 'Database component not available'}
        
        @self.app.get("/api/performance")
        async def api_performance():
            """성과 정보"""
            perf = {
                'win_rate': self.trading_system.optimization_engine.get_win_rate(),
                'avg_slippage': self.trading_system.optimization_engine.get_avg_slippage(),
                'total_trades': self.trading_system.optimization_engine.total_trades,
                'timestamp': datetime.now().isoformat()
            }
            return {
                'status': 'success',
                'data': perf
            }
        
        @self.app.get("/api/orders")
        async def api_orders():
            """주문 목록"""
            unfilled = self.trading_system.order_management.get_unfilled_orders()
            orders = [{
                'order_id': o.order_id,
                'symbol': o.symbol,
                'type': o.order_type.value,
                'quantity': o.quantity,
                'price': o.price,
                'status': o.status.value,
                'filled': o.filled_quantity
            } for o in unfilled]
            
            return {
                'status': 'success',
                'data': orders,
                'count': len(orders)
            }
        
        @self.app.get("/api/trades")
        async def api_trades():
            """거래 이력"""
            # FastAPI는 네이티브 비동기이므로 래퍼 없이 직접 await 가능
            trades = await self.trading_system.trade_logger.get_trade_history(limit=20)
            return {
                'status': 'success',
                'data': trades,
                'count': len(trades)
            }
        
        @self.app.get("/api/risk")
        async def api_risk():
            """위험 정보"""
            if hasattr(self.trading_system, 'risk_manager'):
                risk = self.trading_system.risk_manager
                positions_qty = {s: p.quantity for s, p in self.trading_system.portfolio.positions.items()}
                metrics = risk.generate_risk_report(
                    positions_qty,
                    self.trading_system.market_data_cache
                )
                return {
                    'status': 'success',
                    'data': {
                        'current_value': metrics.current_value,
                        'drawdown': f"{metrics.current_drawdown:.2%}",
                        'max_loss_limit': metrics.max_loss_limit,
                        'risk_level': metrics.risk_level.value,
                        'volatility': f"{metrics.portfolio_volatility:.2%}",
                        'stop_loss_pct': risk.default_stop_loss_pct * 100.0,
                        'max_portfolio_loss_pct': risk.max_portfolio_loss_pct * 100.0,
                        'max_position_size_pct': risk.max_position_size_pct * 100.0,
                        'active_strategy': getattr(risk, 'active_strategy', 'HYBRID')
                    }
                }
            return {'status': 'error', 'message': 'Risk manager not available'}

        @self.app.post("/api/ai/opinion")
        async def api_ai_opinion(request: Request):
            """AI 투자 의견 분석 API"""
            try:
                body = await request.json()
                raw_symbol = body.get('symbol', 'AAPL').strip()
                if not raw_symbol:
                    return {'status': 'error', 'message': '종목명이 필요합니다.'}
                
                symbol = get_tickers().get(raw_symbol, raw_symbol)
                
                # 가짜/진짜 시세 데이터를 조회하여 llm_engine에 주입할 정보 생성
                quote = self.trading_system.get_stock_quote_from_broker(symbol)
                price = quote.get('price') or self.trading_system.market_data_cache.get(symbol, {}).get('price')
                
                if not price:
                    # 폴백 조회
                    market_data = self.trading_system.market_data_handler.fetch_live_data(symbol)
                    price = market_data.price if market_data else 150.0
                
                stock_data = {
                    'symbol': symbol,
                    'price': price,
                    'volume': quote.get('volume') or 1000000,
                    'timestamp': datetime.now().isoformat()
                }
                
                # AI 의견 도출
                opinion = self.trading_system.get_ai_investment_opinion(stock_data)
                return {'status': 'success', 'data': opinion}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        @self.app.post("/api/risk/settings")
        async def api_risk_settings(request: Request):
            """위험 정책 및 손절 설정 업데이트 API"""
            try:
                body = await request.json()
                if not hasattr(self.trading_system, 'risk_manager'):
                    return {'status': 'error', 'message': 'Risk manager not available'}
                    
                risk = self.trading_system.risk_manager
                
                # 각 설정 항목 파싱 및 반영
                if 'stop_loss_pct' in body:
                    risk.default_stop_loss_pct = float(body['stop_loss_pct']) / 100.0
                if 'max_portfolio_loss_pct' in body:
                    risk.max_portfolio_loss_pct = float(body['max_portfolio_loss_pct']) / 100.0
                if 'max_position_size_pct' in body:
                    risk.max_position_size_pct = float(body['max_position_size_pct']) / 100.0
                if 'active_strategy' in body:
                    risk.active_strategy = str(body['active_strategy']).upper()
                
                # 디스크에 지속화
                if hasattr(risk, 'save_config'):
                    risk.save_config()
                    
                self.logger.info(f"Risk settings dynamically updated & saved: StopLoss={risk.default_stop_loss_pct:.2%}, MaxPortfolioLoss={risk.max_portfolio_loss_pct:.2%}, MaxPositionSize={risk.max_position_size_pct:.2%}, ActiveStrategy={risk.active_strategy}")
                return {'status': 'success', 'message': '리스크 관리 설정이 성공적으로 갱신되었습니다.'}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        @self.app.post("/api/portfolio/reset")
        async def api_portfolio_reset():
            """포트폴리오 자산 및 시뮬레이션 상태 초기화 API"""
            try:
                self.trading_system.reset_system_portfolio()
                return {'status': 'success', 'message': '포트폴리오와 모든 기록이 초기화되었습니다.'}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        @self.app.post("/api/backtest")
        async def api_backtest(request: Request):
            """백테스트 실행 API"""
            
            try:
                body = await request.json()
                raw_symbol = body.get('symbol', 'AAPL').strip()
                symbol = get_tickers().get(raw_symbol, raw_symbol)
                strategy_name = body.get('strategy', 'MA')
                period = body.get('period', '10y')
                allow_short = bool(body.get('allow_short', False))
                trailing_stop_pct = float(body.get('trailing_stop_pct', 0))
                scale_in = bool(body.get('scale_in', False))
                stop_loss_pct = float(body.get('stop_loss_pct', 0))
                take_profit_pct = float(body.get('take_profit_pct', 0))
                
                # target period 및 warm-up 기간 계산
                download_period = period
                target_period_bars = None
                
                if period == '1mo':
                    download_period = '1y'
                    target_period_bars = 21
                elif period == '3mo':
                    download_period = '1y'
                    target_period_bars = 63
                elif period == '6mo':
                    download_period = '2y'
                    target_period_bars = 126
                elif period == '1y':
                    download_period = '2y'
                    target_period_bars = 252
                
                self.logger.info(f"Running backtest for {symbol} with strategy {strategy_name} for period {period} (download: {download_period}, target_bars: {target_period_bars}, allow_short: {allow_short}, trailing_stop: {trailing_stop_pct}, scale_in: {scale_in}, stop_loss: {stop_loss_pct}, take_profit: {take_profit_pct})")
                
                # 1. 과거 데이터 수집
                handler = self.trading_system.market_data_handler
                if hasattr(handler, 'fetch_historical_data'):
                    price_bars = handler.fetch_historical_data(symbol, period=download_period)
                else:
                    return {'status': 'error', 'message': 'Historical data fetching not supported.'}
                    
                if not price_bars:
                    return {'status': 'error', 'message': f'Failed to fetch data for {symbol}'}
                    
                # 2. 전략 객체 가져오기
                engine = self.trading_system.backtest_engine
                if hasattr(engine, 'get_strategy_func'):
                    strategy_func = engine.get_strategy_func(strategy_name)
                else:
                    strategy_func = engine._simple_ma_strategy
                    
                # 3. 백테스트 실행
                result = engine.run_backtest(symbol, price_bars, strategy_func, target_period_bars=target_period_bars, allow_short=allow_short, trailing_stop_pct=trailing_stop_pct, scale_in=scale_in, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct)
                
                # 차트 데이터 가공 (100 기준 Rebase)
                dates_str = [d.strftime("%Y-%m-%d") for d in getattr(result, 'dates', [])]
                price_curve = getattr(result, 'price_curve', [])
                equity_curve = getattr(result, 'equity_curve', [])
                
                if price_curve and price_curve[0] > 0:
                    base_p = price_curve[0]
                    price_rebased = [round((p / base_p) * 100, 2) for p in price_curve]
                else:
                    price_rebased = []
                    
                if equity_curve and equity_curve[0] > 0:
                    base_e = equity_curve[0]
                    equity_rebased = [round((e / base_e) * 100, 2) for e in equity_curve]
                else:
                    equity_rebased = []
                    
                buy_points = [None] * len(dates_str)
                sell_points = [None] * len(dates_str)
                
                date_to_idx = {d: i for i, d in enumerate(dates_str)}
                for t in result.trades:
                    entry_d = t.entry_date.strftime("%Y-%m-%d")
                    exit_d = t.exit_date.strftime("%Y-%m-%d")
                    is_short = getattr(t, 'direction', 'LONG') == 'SHORT'
                    
                    if entry_d in date_to_idx and price_rebased:
                        idx = date_to_idx[entry_d]
                        if is_short:
                            sell_points[idx] = price_rebased[idx]
                        else:
                            buy_points[idx] = price_rebased[idx]
                    if exit_d in date_to_idx and price_rebased:
                        idx = date_to_idx[exit_d]
                        if is_short:
                            buy_points[idx] = price_rebased[idx]
                        else:
                            sell_points[idx] = price_rebased[idx]
                
                return {
                    'status': 'success',
                    'data': {
                        'symbol': get_tickers_rev().get(result.symbol, result.symbol),
                        'total_return_pct': f"{result.total_return_pct:.2f}%",
                        'win_rate': f"{result.win_rate:.2%}",
                        'max_drawdown': f"{result.max_drawdown:.2%}",
                        'trades_count': len(result.trades),
                        'trailing_stop_count': getattr(result, 'trailing_stop_count', 0),
                        'profit_factor': f"{result.profit_factor:.2f}" if result.profit_factor != float('inf') else "\u221e",
                        'sharpe_ratio': f"{result.sharpe_ratio:.2f}",
                        'start_date': result.start_date.strftime("%Y-%m-%d"),
                        'end_date': result.end_date.strftime("%Y-%m-%d"),
                        'chart_data': {
                            'labels': dates_str,
                            'price': price_rebased,
                            'equity': equity_rebased,
                            'buy_points': buy_points,
                            'sell_points': sell_points
                        }
                    }
                }
            except Exception as e:
                self.logger.error(f"Backtest API error: {e}")
                return {'status': 'error', 'message': str(e)}

        @self.app.get("/api/search")
        async def api_search(q: str):
            """종목명 검색 API (Yahoo Finance 연동 + 로컬 한국 주식 매핑)"""
            if not q or len(q) < 2:
                return {'status': 'success', 'results': []}
            
            local_results = []
            for name, code in get_tickers().items():
                if q.lower() in name.lower() or q.upper() in code:
                    local_results.append({"symbol": code, "name": name})
                    
            # 영어 기반이나 다른 티커는 Yahoo 검색으로 처리 (한국어는 야후가 차단할 수 있음)
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(q)}&quotesCount=8&newsCount=0"
            headers = {'User-Agent': 'Mozilla/5.0'}
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=headers, timeout=10)
                    data = response.json()
            except ImportError:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers) as response:
                            data = await response.json()
                except ImportError:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req) as response:
                        data = json.loads(response.read().decode())
            
            quotes = data.get('quotes', [])
            results = local_results + [
                {
                    "symbol": quote.get('symbol'), 
                    "name": quote.get('shortname', quote.get('longname', '알 수 없음'))
                } 
                for quote in quotes if quote.get('quoteType') in ['EQUITY', 'ETF']
            ]
            
            # 중복 제거 (로컬 매핑과 야후 매핑 중복)
            seen = set()
            unique_results = []
            for r in results:
                if r['symbol'] not in seen:
                    seen.add(r['symbol'])
                    unique_results.append(r)
                    
            return {'status': 'success', 'results': unique_results}

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            try:
                while True:
                    # Keep connection alive
                    data = await websocket.receive_text()
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                    
        @self.app.post("/api/scanner/start")
        async def api_scanner_start(request: Request):
            try:
                body = await request.json()
                strategy_name = body.get('strategy', 'MA')
                period = body.get('period', '1y')
                allow_short = bool(body.get('allow_short', False))
                trailing_stop_pct = float(body.get('trailing_stop_pct', 0))
                scale_in = bool(body.get('scale_in', False))
                stop_loss_pct = float(body.get('stop_loss_pct', 0))
                take_profit_pct = float(body.get('take_profit_pct', 0))
                stop_loss_pct = float(body.get('stop_loss_pct', 0))
                take_profit_pct = float(body.get('take_profit_pct', 0))
                
                # target period 및 warm-up 기간 계산
                download_period = period
                target_period_bars = None
                
                if period == '1mo':
                    download_period = '1y'
                    target_period_bars = 21
                elif period == '3mo':
                    download_period = '1y'
                    target_period_bars = 63
                elif period == '6mo':
                    download_period = '2y'
                    target_period_bars = 126
                elif period == '1y':
                    download_period = '2y'
                    target_period_bars = 252
                
                # 한국 전체 종목 + 미국 대형주 샘플
                UNIVERSE = list(get_tickers_rev().keys()) + [
                    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "JNJ"
                ]
                
                task_id = str(uuid.uuid4())
                self.scan_tasks[task_id] = {
                    'status': 'running',
                    'progress': 0,
                    'total': len(UNIVERSE),
                    'results': [],
                    'error': None
                }
                
                async def run_scan_task(tid: str, univ: list, strat: str, dl_per: str, target_bars: int, allow_short: bool, trailing_stop_pct: float = 0.0, scale_in: bool = False, stop_loss_pct: float = 0.0, take_profit_pct: float = 0.0):
                    engine = self.trading_system.backtest_engine
                    handler = self.trading_system.market_data_handler
                    
                    if hasattr(engine, 'get_strategy_func'):
                        strategy_func = engine.get_strategy_func(strat)
                    else:
                        strategy_func = engine._simple_ma_strategy
                        
                    def sanitize_float(val, default=0.0):
                        if val is None or math.isnan(val) or math.isinf(val):
                            return default
                        return val
                        
                    def process_symbol(symbol):
                        try:
                            price_bars = handler.fetch_historical_data(symbol, period=dl_per)
                            if not price_bars:
                                return None
                            res = engine.run_backtest(symbol, price_bars, strategy_func, target_period_bars=target_bars, allow_short=allow_short, trailing_stop_pct=trailing_stop_pct, scale_in=scale_in, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct)
                            
                            display_symbol = get_tickers_rev().get(symbol, symbol)
                            if symbol.endswith('.KS'):
                                exchange, market = 'KOSPI', 'KR'
                            elif symbol.endswith('.KQ'):
                                exchange, market = 'KOSDAQ', 'KR'
                            else:
                                exchange, market = 'NASDAQ/NYSE', 'US'
                                
                            return {
                                'symbol': display_symbol,
                                'ticker': symbol,
                                'return_pct': sanitize_float(res.total_return_pct / 100.0),
                                'win_rate': sanitize_float(res.win_rate),
                                'sharpe': sanitize_float(getattr(res, 'sharpe_ratio', 0.0)),
                                'trades': len(res.trades),
                                'mdd': sanitize_float(getattr(res, 'max_drawdown', 0.0)),
                                'market': market,
                                'exchange': exchange,
                            }
                        except Exception as e:
                            self.logger.warning(f"Scan failed for {symbol}: {e}")
                            return None

                    results = []
                    completed = 0
                    
                    # Use ThreadPoolExecutor to run tasks in parallel
                    loop = asyncio.get_running_loop()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                        # Submit all tasks
                        futures = [loop.run_in_executor(executor, process_symbol, s) for s in univ]
                        
                        # Process results as they complete (batch processing to avoid event loop blocking)
                        for chunk_idx in range(0, len(futures), 50):
                            chunk = futures[chunk_idx:chunk_idx+50]
                            chunk_results = await asyncio.gather(*chunk)
                            for res in chunk_results:
                                if res:
                                    results.append(res)
                            completed += len(chunk)
                            self.scan_tasks[tid]['progress'] = completed
                        
                    # 최종 정리 (수익률 내림차순 정렬)
                    results.sort(key=lambda x: x['return_pct'], reverse=True)
                    self.scan_tasks[tid]['results'] = results
                    self.scan_tasks[tid]['status'] = 'completed'

                # 비동기 백그라운드 태스크로 실행
                asyncio.create_task(run_scan_task(task_id, UNIVERSE, strategy_name, download_period, target_period_bars, allow_short, trailing_stop_pct, scale_in, stop_loss_pct, take_profit_pct))
                
                return {'status': 'success', 'task_id': task_id}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        @self.app.get("/api/scanner/status/{task_id}")
        async def api_scanner_status(task_id: str):
            task = self.scan_tasks.get(task_id)
            if not task:
                return {'status': 'error', 'message': 'Task not found'}
            return {'status': 'success', 'data': task}

        @self.app.post("/api/orders/place")
        async def api_orders_place(request: Request):
            """수동 주문 생성 및 즉시 집행(지정가/시장가) API"""
            try:
                body = await request.json()
                raw_symbol = body.get('symbol', '').strip()
                if not raw_symbol:
                    return {'status': 'error', 'message': '종목명이 필요합니다.'}
                
                symbol = get_tickers().get(raw_symbol, raw_symbol) # 한글 이름 치환
                order_type_str = body.get('order_type', 'BUY') # BUY or SELL
                qty = int(body.get('quantity', 0))
                price_type = body.get('price_type', 'LIMIT') # LIMIT or MARKET
                price = float(body.get('price', 0))
                
                if qty <= 0:
                    return {'status': 'error', 'message': '수량은 1주 이상이어야 합니다.'}
                
                o_type = OrderType.BUY if order_type_str.upper() == 'BUY' else OrderType.SELL
                
                # 시장가(MARKET) 처리: 가격이 0이거나 미지정일 때, 현재 시세를 조회해와서 주문 가격을 결정
                if price_type == 'MARKET':
                    quote = self.trading_system.get_stock_quote_from_broker(symbol)
                    current_price = quote.get('price') or self.trading_system.market_data_cache.get(symbol, {}).get('price')
                    
                    if not current_price:
                        # yfinance에서 실시간 시세를 직접 한번 찔러옴
                        market_data = self.trading_system.market_data_handler.fetch_live_data(symbol)
                        if market_data:
                            current_price = market_data.price
                        else:
                            current_price = 150.0
                            
                    price = current_price
                
                # 주문 생성
                order = self.trading_system.order_management.create_order(symbol, o_type, qty, price)
                # 주문 제출
                await self.trading_system.order_management.submit_order(order)
                
                # 시장가(MARKET)이거나 지정가가 현재 시세와 맞아 즉시 체결이 가능한 시나리오 시뮬레이션
                # (수동 매매의 즉시 반응성을 위해, 제출된 주문을 즉시 가상 매칭 체결 처리)
                await self.trading_system.order_management.execute_order(order.order_id)
                await self.trading_system.trade_logger.log_execution(order.order_id, symbol, qty, price)
                
                # 포트폴리오 실제 갱신 처리
                if o_type == OrderType.BUY:
                    self.trading_system.portfolio.add_position(symbol, qty, price)
                else:
                    self.trading_system.portfolio.reduce_position(symbol, qty)
                
                # 대시보드 화면 및 포트폴리오 데이터 갱신 브로드캐스트
                await self.broadcast_portfolio_update()
                
                price_label = "시장가" if price_type == 'MARKET' else f"{price:,.2f}원"
                return {
                    'status': 'success',
                    'message': f"{raw_symbol}({symbol}) {order_type_str} {qty}주가 {price_label}(체결가: {price:,.2f}원)로 즉시 체결되었습니다."
                }
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        @self.app.post("/api/orders/cancel")
        async def api_orders_cancel(request: Request):
            """수동 주문 취소 API"""
            try:
                body = await request.json()
                order_id = body.get('order_id')
                if not order_id:
                    return {'status': 'error', 'message': 'order_id is required'}
                
                success = await self.trading_system.order_management.cancel_order(order_id)
                if success:
                    # 취소 시 포트폴리오 갱신 브로드캐스트
                    await self.broadcast_portfolio_update()
                    return {'status': 'success', 'message': f'주문 {order_id}가 취소되었습니다.'}
                else:
                    return {'status': 'error', 'message': '주문을 취소할 수 없습니다. (이미 체결되었거나 존재하지 않음)'}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        @self.app.on_event("startup")
        async def startup_event():
            # 1. 백그라운드 매매 시뮬레이션 루프 실행
            self._trading_loop_task = asyncio.create_task(self._run_periodic_simulation())
            self.logger.info("Background periodic trading simulator task started.")

            # 2. 텔레그램 봇 기동
            self._telegram_bot_task = asyncio.create_task(self._run_telegram_bot())
            self.logger.info("Background Telegram bot task started.")

            # 3. AI 평가 루프 실행
            self._ai_eval_task = asyncio.create_task(self._run_ai_evaluation_loop())
            self.logger.info("Background AI evaluation task started.")

        @self.app.on_event("shutdown")
        async def shutdown_event():
            # 백그라운드 태스크 취소
            if hasattr(self, '_trading_loop_task'):
                self._trading_loop_task.cancel()
                self.logger.info("Background periodic trading simulator task stopped.")

            if hasattr(self, '_telegram_bot_task'):
                self._telegram_bot_task.cancel()
                self.logger.info("Background Telegram bot task stopped.")

            if hasattr(self, '_ai_eval_task'):
                self._ai_eval_task.cancel()

            if hasattr(self, 'telegram_app') and self.telegram_app:
                try:
                    await self.telegram_app.updater.stop()
                    await self.telegram_app.stop()
                    await self.telegram_app.shutdown()
                    self.logger.info("Telegram Bot API polling stopped.")
                except Exception as e:
                    self.logger.error(f"Error shutting down telegram application: {e}")

    async def _run_ai_evaluation_loop(self):
        """저장된 AI 예측들의 성과를 주기적으로 자체 평가"""
        await asyncio.sleep(60)  # 초기 딜레이

        while True:
            try:
                if hasattr(self.trading_system, 'comp') and 'ai_db' in self.trading_system.comp:
                    def get_price(symbol):
                        market_data = self.trading_system.market_data_handler.fetch_live_data(symbol)
                        return market_data.price if market_data else None

                    await self.trading_system.comp['ai_db'].evaluate_pending_predictions(get_price)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in AI evaluation loop: {e}")

            # 1시간마다 평가 실행
            await asyncio.sleep(3600)                    
    async def _run_periodic_simulation(self):
        """백그라운드에서 주기적으로 거래 시뮬레이션을 실행하여 데이터를 실시간으로 업데이트 (개장 시간 스케줄 최적화)"""
        default_symbols = ["AAPL", "MSFT", "GOOGL", "005930.KS", "000660.KS", "005380.KS"]
        await asyncio.sleep(5)  # 서버 시작 후 잠시 안정화 대기
        
        while True:
            try:
                # 1. 보유 중인 포지션 종목도 감시 리스트에 동적으로 합류
                active_positions = list(self.trading_system.portfolio.positions.keys())
                symbols = list(set(default_symbols + active_positions))
                
                # 2. 시장 개장 상태 체크 (KST 기준)
                now = datetime.now()
                weekday = now.weekday()
                time_str = now.strftime("%H:%M")
                
                # 한국 개장: 월~금 09:00 ~ 15:30
                is_kr_open = (weekday < 5) and ("09:00" <= time_str <= "15:30")
                # 미국 개장: 월~금 23:30 ~ 06:00 KST (서머타임은 러프하게 퉁침)
                is_us_open = (weekday < 5) and (("23:30" <= time_str <= "23:59") or ("00:00" <= time_str <= "06:00"))
                
                # 주말 및 모든 장 폐쇄 시 yfinance API 할당량과 백오프 보호를 위해 10분 대기
                if not is_kr_open and not is_us_open:
                    self.logger.info("모든 주식 시장이 닫혀 있습니다. 부하 방지를 위해 주기적 스케줄 감시 주기를 10분으로 전환합니다.")
                    await asyncio.sleep(600)
                    continue

                self.logger.info(f"지능형 스케줄러 점검 - KR 개장: {is_kr_open}, US 개장: {is_us_open}")
                
                for symbol in symbols:
                    is_kr_stock = symbol.endswith('.KS') or symbol.endswith('.KQ')
                    
                    # 닫힌 시장 주식은 시뮬레이션을 돌리지 않고 건너뜀
                    if is_kr_stock and not is_kr_open:
                        continue
                    if not is_kr_stock and not is_us_open:
                        continue
                        
                    self.logger.info(f"Intelligent schedule run for {symbol} (Live simulation)")
                    await self.trading_system.simulate_trading_day(symbol)
                    # WebSocket을 통해 브라우저 화면의 포트폴리오를 실시간 갱신
                    await self.broadcast_portfolio_update()
                    # 종목 API 호출 시 부하 분산을 위해 10초 휴식
                    await asyncio.sleep(10)
                    
                # 일회성 전수 검사가 끝나면 1분 대기
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in intelligent market simulation: {e}")
                await asyncio.sleep(10)

    async def _run_telegram_bot(self):
        """백그라운드에서 텔레그램 봇 인스턴스를 초기화하고 폴링 기동"""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            self.logger.warning("TELEGRAM_BOT_TOKEN이 없어서 텔레그램 봇을 기동하지 않습니다.")
            return
            
        try:
            from telegram.ext import Application, MessageHandler, filters
            from telegram import Update
            
            self.logger.info("Starting Telegram Bot application context within Dashboard event loop...")
            
            # python-telegram-bot 빌드
            app = Application.builder().token(token).build()
            
            # 메시지 핸들러 등록
            async def handle_message(update: Update, context):
                if not update.message or not update.message.text:
                    return
                user_id = update.effective_user.id
                text = update.message.text
                
                # 메인 트레이딩 시스템 메시지 프로세서 호출
                response = self.trading_system.process_telegram_message(user_id, text)
                await update.message.reply_text(response, parse_mode="Markdown")
                
            app.add_handler(MessageHandler(filters.TEXT, handle_message))
            
            # 봇 상태 연결
            self.trading_system.start_telegram_bot()
            
            # 주문 상태 변경 이벤트를 구독하여 실시간 푸시 발송
            async def on_order_status_event(order):
                stats = self.trading_system.get_telegram_bot_stats()
                users = stats.get('users', {})
                
                for user_id in users:
                    try:
                        event_type = "order_placed"
                        if order.status.value == "EXECUTED":
                            event_type = "order_filled"
                        elif order.status.value == "CANCELLED":
                            event_type = "order_cancelled"
                            
                        msg = self.trading_system.send_telegram_notification(user_id, event_type, {
                            'symbol': order.symbol,
                            'quantity': order.quantity,
                            'price': order.price
                        })
                        await app.bot.send_message(chat_id=user_id, text=msg)
                    except Exception as ex:
                        self.logger.error(f"Failed to push telegram alert: {ex}")
            
            self.event_bus.subscribe("order_status", on_order_status_event)
            
            # 폴링 기동
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            
            self.telegram_app = app
            self.logger.info("Telegram Bot API polling started successfully.")
            
            # 태스크 유지
            while True:
                await asyncio.sleep(3600)
                
        except ImportError:
            self.logger.warning("python-telegram-bot 라이브러리가 설치되지 않아 텔레그램 봇 기동을 생략합니다.")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to start telegram bot: {e}")

    async def broadcast_json(self, message: dict):
        """활성화된 모든 소켓에 메시지 전송"""
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.error(f"Failed to send WS message: {e}")
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

    async def broadcast_order_update(self, order):
        """실시간 주문 업데이트 브로드캐스트"""
        if not self._enabled or not self.active_connections:
            return
        
        await self.broadcast_json({
            'type': 'order_update',
            'data': {
                'order_id': order.order_id,
                'symbol': order.symbol,
                'type': order.order_type.value,
                'quantity': order.quantity,
                'price': order.price,
                'status': order.status.value,
                'filled': order.filled_quantity,
                'timestamp': datetime.now().isoformat()
            }
        })
        self.logger.debug(f"Broadcasted order update: {order.order_id}")

    async def broadcast_portfolio_update(self):
        """실시간 포트폴리오 업데이트 브로드캐스트"""
        if not self._enabled or not self.active_connections:
            return
        
        status = self.trading_system.get_trading_status()
        await self.broadcast_json({
            'type': 'portfolio_update',
            'data': {
                'cash': status['cash'],
                'positions_count': len(status['positions']),
                'open_orders_count': status['open_orders'],
                'timestamp': status['timestamp']
            }
        })
        self.logger.debug("Broadcasted portfolio update")

    async def broadcast_market_data(self, market_data):
        """실시간 시세 업데이트 브로드캐스트"""
        if not self._enabled or not self.active_connections:
            return
        
        await self.broadcast_json({
            'type': 'market_data_update',
            'data': {
                'symbol': market_data.symbol,
                'price': market_data.price,
                'bid': market_data.bid,
                'ask': market_data.ask,
                'volume': market_data.volume,
                'timestamp': datetime.now().isoformat()
            }
        })
        self.logger.debug(f"Broadcasted market data: {market_data.symbol}")
        
    def get_dashboard_html(self) -> str:
        """대시보드 HTML"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>주식 트레이딩 시스템 대시보드</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: #f5f5f5;
                    color: #333;
                }
                .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
                header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }
                header h1 { font-size: 28px; margin-bottom: 5px; }
                header .timestamp { font-size: 12px; opacity: 0.9; }
                
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 20px;
                }
                
                .card {
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    border-left: 4px solid #667eea;
                }
                
                .card h2 {
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 10px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                
                .card .value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 5px;
                }
                
                .card .subtitle { font-size: 12px; color: #999; }
                
                .card.positive { border-left-color: #4caf50; }
                .card.negative { border-left-color: #f44336; }
                .card.warning { border-left-color: #ff9800; }
                
                .value.positive { color: #4caf50; }
                .value.negative { color: #f44336; }
                
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }
                
                th, td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #eee;
                }
                
                th {
                    background: #f9f9f9;
                    font-weight: 600;
                    font-size: 12px;
                    color: #666;
                    text-transform: uppercase;
                }
                
                tr:hover { background: #f9f9f9; }
                
                .status-badge {
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
                
                .status-executed { background: #c8e6c9; color: #2e7d32; }
                .status-pending { background: #fff9c4; color: #f57f17; }
                .status-cancelled { background: #ffccbc; color: #d84315; }
                
                .loading { color: #999; text-align: center; padding: 20px; }
                
                .form-control { width: 100%; padding: 8px; margin-bottom: 10px; border-radius: 4px; border: 1px solid #ccc; font-family: inherit; }
                .btn { padding: 10px 16px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
                .btn:hover { background: #5a6cd6; }
                .btn:disabled { background: #ccc; cursor: not-allowed; }
                
                footer {
                    text-align: center;
                    color: #999;
                    font-size: 12px;
                    margin-top: 40px;
                    padding: 20px;
                }
                
                .tabs {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 20px;
                    border-bottom: 2px solid #ddd;
                }
                .tab-btn {
                    padding: 10px 20px;
                    background: none;
                    border: none;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: bold;
                    color: #666;
                    border-bottom: 3px solid transparent;
                    margin-bottom: -2px;
                }
                .tab-btn:hover {
                    color: #667eea;
                }
                .tab-btn.active {
                    color: #667eea;
                    border-bottom: 3px solid #667eea;
                }
                .tab-content {
                    display: none;
                }
                .tab-content.active {
                    display: block;
                }
                .progress-bar {
                    width: 100%;
                    background-color: #eee;
                    border-radius: 4px;
                    overflow: hidden;
                    margin-top: 10px;
                }
                .progress-bar-fill {
                    height: 20px;
                    background-color: #4caf50;
                    width: 0%;
                    transition: width 0.3s;
                }
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
        </head>
        <body>
            <div class="container">
                <header style="display:flex; justify-content:space-between; align-items:center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <div>
                        <h1 style="font-size: 28px; margin-bottom: 5px; margin-top: 0;">📊 주식 트레이딩 시스템</h1>
                        <div class="timestamp" style="font-size: 12px; opacity: 0.9;">최근 업데이트: <span id="update-time">-</span></div>
                    </div>
                    <button class="btn" onclick="resetPortfolio()" style="background:#e53935; border:none; padding:10px 16px; border-radius:6px; font-weight:bold; font-size:12.5px; color:white; cursor:pointer; box-shadow:0 2px 5px rgba(0,0,0,0.2);">🔄 가상 자산 초기화</button>
                </header>
                
                <div class="tabs">
                    <button class="tab-btn active" id="tabbtn-dashboard" onclick="switchTab('dashboard')">대시보드</button>
                    <button class="tab-btn" id="tabbtn-scanner" onclick="switchTab('scanner')">백테스트 스캐너</button>
                </div>
                
                <div id="tab-dashboard" class="tab-content active">
                    <!-- 포트폴리오 개요 -->
                    <div class="grid" id="portfolio-grid">
                        <div class="card">
                            <h2>현금</h2>
                            <div class="value" id="cash">-</div>
                            <div class="subtitle">USD</div>
                        </div>
                        <div class="card">
                            <h2>포지션</h2>
                            <div class="value" id="positions">-</div>
                            <div class="subtitle">개수</div>
                        </div>
                        <div class="card">
                            <h2>미체결 주문</h2>
                            <div class="value" id="open-orders">-</div>
                            <div class="subtitle">개</div>
                        </div>
                    </div>

                    <!-- 📈 포트폴리오 차트 -->
                    <div class="grid" id="portfolio-charts-grid" style="display: none; grid-template-columns: 2fr 1fr;">
                        <div class="card">
                            <h2>자산 성장 곡선 (Equity Curve)</h2>
                            <div style="position: relative; height: 250px; width: 100%;">
                                <canvas id="equity-chart"></canvas>
                            </div>
                        </div>
                        <div class="card">
                            <h2>포지션 비중</h2>
                            <div style="position: relative; height: 250px; width: 100%;">
                                <canvas id="allocation-pie-chart"></canvas>
                            </div>
                        </div>
                    </div>
                
                <!-- 💸 실시간 수동 주문 실행 패널 -->
                <div class="card" style="margin-bottom: 20px; border-left: 4px solid #2196f3;">
                    <h2>💸 실시간 수동 주문 실행</h2>
                    <div style="display: flex; gap: 12px; align-items: flex-end; margin-bottom: 5px; margin-top: 15px; flex-wrap: wrap;">
                        <div>
                            <label style="font-size: 11px; color: #aaa; display: block; margin-bottom: 4px;">종목명 또는 티커</label>
                            <input type="text" id="trade-symbol" list="symbol-list" class="form-control" autocomplete="off" placeholder="예: 삼성전자" style="margin-bottom: 0; width: 160px;" oninput="searchSymbol(this.value)">
                        </div>
                        <div>
                            <label style="font-size: 11px; color: #aaa; display: block; margin-bottom: 4px;">구분</label>
                            <select id="trade-side" class="form-control" style="margin-bottom: 0; width: 90px; font-weight:bold;">
                                <option value="BUY" style="color:#4caf50;">매수 (BUY)</option>
                                <option value="SELL" style="color:#f44336;">매도 (SELL)</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size: 11px; color: #aaa; display: block; margin-bottom: 4px;">유형</label>
                            <select id="trade-price-type" class="form-control" onchange="togglePriceInput(this.value)" style="margin-bottom: 0; width: 100px;">
                                <option value="LIMIT">지정가</option>
                                <option value="MARKET">시장가</option>
                            </select>
                        </div>
                        <div id="trade-price-container">
                            <label style="font-size: 11px; color: #aaa; display: block; margin-bottom: 4px;">가격</label>
                            <input type="number" id="trade-price" class="form-control" placeholder="가격" style="margin-bottom: 0; width: 120px;" step="any">
                        </div>
                        <div>
                            <label style="font-size: 11px; color: #aaa; display: block; margin-bottom: 4px;">수량</label>
                            <input type="number" id="trade-qty" class="form-control" placeholder="수량" style="margin-bottom: 0; width: 90px;" min="1" value="10">
                        </div>
                        <div>
                            <button class="btn" id="btn-place-order" onclick="placeOrder()" style="background:#2196f3; font-weight:bold; padding: 10px 20px;">주문 제출</button>
                        </div>
                    </div>
                    <div id="trade-feedback" style="display:none; font-size:12px; margin-top:12px; padding:10px; border-radius:6px;"></div>
                </div>
                
                <!-- 성과 지표 -->
                <div class="grid" id="performance-grid">
                    <div class="card positive">
                        <h2>승률</h2>
                        <div class="value" id="win-rate">-</div>
                        <div class="subtitle">%</div>
                    </div>
                    <div class="card">
                        <h2>평균 슬리피지</h2>
                        <div class="value" id="avg-slippage">-</div>
                        <div class="subtitle">%</div>
                    </div>
                    <div class="card">
                        <h2>총 거래수</h2>
                        <div class="value" id="total-trades">-</div>
                        <div class="subtitle">건</div>
                    </div>
                </div>
                
                <!-- 위험 정보 -->
                <div class="grid" id="risk-grid" style="display: none;">
                    <div class="card warning">
                        <h2>현재 낙폭</h2>
                        <div class="value" id="drawdown">-</div>
                        <div class="subtitle">%</div>
                    </div>
                    <div class="card">
                        <h2>위험 수준</h2>
                        <div class="value" id="risk-level">-</div>
                        <div class="subtitle">레벨</div>
                    </div>
                </div>

                <!-- 🛡️ 실시간 리스크 관리 설정 -->
                <div class="card" style="margin-bottom: 20px; border-left: 4px solid #f44336;">
                    <h2>🛡️ 시스템 제어 및 리스크 관리 설정</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px;">
                        <div>
                            <label style="font-size: 12px; color: #aaa; display: block; margin-bottom: 6px;">기본 손절선 (Stop Loss %)</label>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <input type="range" id="risk-input-sl" min="1" max="30" value="5" oninput="document.getElementById('lbl-sl').textContent = this.value + '%'" style="flex-grow:1;">
                                <span id="lbl-sl" style="font-size:14px; font-weight:bold; color:#f44336; width:35px;">5%</span>
                            </div>
                        </div>
                        <div>
                            <label style="font-size: 12px; color: #aaa; display: block; margin-bottom: 6px;">최대 포트폴리오 허용 낙폭 (%)</label>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <input type="range" id="risk-input-mdd" min="3" max="50" value="10" oninput="document.getElementById('lbl-mdd').textContent = this.value + '%'" style="flex-grow:1;">
                                <span id="lbl-mdd" style="font-size:14px; font-weight:bold; color:#f44336; width:35px;">10%</span>
                            </div>
                        </div>
                        <div>
                            <label style="font-size: 12px; color: #aaa; display: block; margin-bottom: 6px;">단일 종목 최대 투자 비중 (%)</label>
                            <div style="display:flex; align-items:center; gap:8px;">
                                <input type="range" id="risk-input-pos" min="5" max="100" value="20" oninput="document.getElementById('lbl-pos').textContent = this.value + '%'" style="flex-grow:1;">
                                <span id="lbl-pos" style="font-size:14px; font-weight:bold; color:#ff9800; width:40px;">20%</span>
                            </div>
                        </div>
                        <div>
                            <label style="font-size: 12px; color: #aaa; display: block; margin-bottom: 6px;">활성 자동 매매 전략</label>
                            <select id="system-active-strategy" style="width: 100%; height: 28px; background: rgba(255,255,255,0.05); color: white; border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; padding: 0 4px; font-size:12px;">
                                <option value="HYBRID" style="background:#222; color:#fff;">하이브리드 (감성+스프레드)</option>
                                <option value="MA" style="background:#222; color:#fff;">이동평균 크로스 (MA)</option>
                                <option value="RSI" style="background:#222; color:#fff;">RSI 과매도 반등</option>
                                <option value="MACD" style="background:#222; color:#fff;">MACD 돌파</option>
                                <option value="TREND" style="background:#222; color:#fff;">추세 추종 (Trend)</option>
                                <option value="BUFFETT" style="background:#222; color:#fff;">워렌 버핏 가치 Proxy</option>
                                <option value="LYNCH" style="background:#222; color:#fff;">피터 린치 성장 Proxy</option>
                                <option value="DALIO" style="background:#222; color:#fff;">레이 달리오 안정 Proxy</option>
                            </select>
                        </div>
                    </div>
                    <div style="margin-top: 15px; text-align: right;">
                        <button class="btn" onclick="saveRiskSettings()" style="background:#f44336; font-weight:bold; padding: 8px 18px;">설정값 반영</button>
                    </div>
                    <div id="risk-settings-feedback" style="display:none; font-size:12px; margin-top:10px; padding:8px; border-radius:4px;"></div>
                </div>
                
                <!-- 백테스트 시뮬레이터 -->
                <div class="card" style="margin-bottom: 20px;">
                    <h2>📊 백테스트 시뮬레이터</h2>
                    <div style="display: flex; gap: 10px; align-items: flex-end; margin-bottom: 15px; margin-top: 15px; flex-wrap: wrap;">
                        <div>
                            <label style="font-size: 12px; color: #666; display: block; margin-bottom: 4px;">종목 (티커 또는 기업명)</label>
                            <input type="text" id="bt-symbol" list="symbol-list" class="form-control" autocomplete="off" placeholder="예: Apple" value="AAPL" oninput="searchSymbol(this.value)" onkeydown="if(event.key==='Enter') runBacktest()" style="margin-bottom: 0; width: 150px;">
                            <datalist id="symbol-list"></datalist>
                        </div>
                        <div>
                            <label style="font-size: 12px; color: #666; display: block; margin-bottom: 4px;">기간</label>
                            <select id="bt-period" class="form-control" style="margin-bottom: 0; width: 100px;">
                                <option value="1y">1년</option>
                                <option value="3y">3년</option>
                                <option value="5y">5년</option>
                                <option value="10y" selected>10년</option>
                                <option value="15y">15년</option>
                                <option value="20y">20년</option>
                                <option value="30y">30년</option>
                            </select>
                        </div>
                        <div style="flex-grow: 1;">
                            <label style="font-size: 12px; color: #666; display: block; margin-bottom: 4px;">투자 전략 (마우스를 올려 설명 확인)</label>
                            <select id="bt-strategy" class="form-control" style="margin-bottom: 0;">
                                <option value="MA" title="단순 이동평균선 돌파: 단기 이평선이 장기 이평선을 상향 돌파 시 매수">이동평균(MA)</option>
                                <option value="MACD" title="EMA 기반 MACD 히스토그램 전환점 감지 (골든/데드크로스)">MACD(EMA)</option>
                                <option value="RSI" title="RSI가 30 이하로 침체 시 매수 (과매도 반등 포착)">RSI</option>
                                <option value="BOLLINGER" title="볼린저밴드+RSI 복합: 하단밴드 터치+과매도 시 매수, 상단밴드+과매수 시 매도 (횡보장 수익)">볼린저밴드(Bollinger)</option>
                                <option value="ENSEMBLE" title="MA+RSI+MACD 3개 지표 투표: 2개 이상 동의 시에만 매매 (거짓신호 필터링)">복합 전략(Ensemble)</option>
                                <option value="TREND" title="추세 추종: 가격이 200일선 위에 있고 단기 이평(20일)이 중기 이평(50일) 위에 있을 때 매수">추세 추종(Trend Following)</option>
                                <option value="BUFFETT" title="워렌 버핏(가치/역발상): 200일선 아래 크게 하락하고 단기 과매도 시 매수">워렌 버핏(Value Proxy)</option>
                                <option value="LYNCH" title="피터 린치(성장/모멘텀): 50일 신고가 및 평균 거래량 크게 상회 시 강한 모멘텀 매수">피터 린치(Growth Proxy)</option>
                                <option value="DALIO" title="레이 달리오(안정/올웨더): 200일선 위 안정적 상승추세에서 매수">레이 달리오(Safe Proxy)</option>
                            </select>
                        </div>
                        <div style="display: flex; align-items: center; height: 38px; padding-bottom: 2px;">
                            <label style="font-size: 12px; color: #aaa; display: flex; align-items: center; cursor: pointer; user-select: none;">
                                <input type="checkbox" id="bt-allow-short" style="margin-right: 6px; width: 15px; height: 15px; cursor: pointer;">
                                공매도(Short) 허용
                            </label>
                        </div>
                        <div style="display: flex; align-items: center; height: 38px; padding-bottom: 2px;">
                            <label style="font-size: 12px; color: #aaa; display: flex; align-items: center; cursor: pointer; user-select: none;">
                                <input type="checkbox" id="bt-scale-in" style="margin-right: 6px; width: 15px; height: 15px; cursor: pointer;">
                                분할 진입(Scale-In)
                            </label>
                        </div>
                        <div style="flex-grow: 1;">
                            <label style="font-size: 12px; color: #666; display: block; margin-bottom: 4px;">트레일링 스톱 (%)</label>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <input type="range" id="bt-trailing-stop" min="0" max="15" step="1" value="0" style="flex-grow: 1; cursor: pointer;" oninput="document.getElementById('bt-ts-val').textContent = this.value + '%';">
                                <span id="bt-ts-val" style="font-size: 12px; color: #888; min-width: 30px;">0%</span>
                            </div>
                        </div>
                        <div style="flex-grow: 1;">
                            <label style="font-size: 12px; color: #666; display: block; margin-bottom: 4px;">고정 손절 (%)</label>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <input type="range" id="bt-stop-loss" min="0" max="20" step="1" value="0" style="flex-grow: 1; cursor: pointer;" oninput="document.getElementById('bt-sl-val').textContent = this.value === '0' ? '비활성' : this.value + '%';">
                                <span id="bt-sl-val" style="font-size: 12px; color: #888; min-width: 45px;">비활성</span>
                            </div>
                        </div>
                        <div style="flex-grow: 1;">
                            <label style="font-size: 12px; color: #666; display: block; margin-bottom: 4px;">부분 익절 (%)</label>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <input type="range" id="bt-take-profit" min="0" max="50" step="2" value="0" style="flex-grow: 1; cursor: pointer;" oninput="document.getElementById('bt-tp-val').textContent = this.value === '0' ? '비활성' : this.value + '%';">
                                <span id="bt-tp-val" style="font-size: 12px; color: #888; min-width: 45px;">비활성</span>
                            </div>
                        </div>
                        <button class="btn" onclick="runBacktest()">백테스트 실행</button>
                    </div>
                    <div id="bt-result" style="display: none; background: #f9f9f9; padding: 20px; border-radius: 8px; border: 1px solid #eee;">
                        <!-- 결과 영역 -->
                    </div>
                    <div id="bt-chart-container" style="position: relative; height: 400px; width: 100%; margin-top: 20px; display: none;">
                        <canvas id="bt-chart"></canvas>
                    </div>
                </div>

                <!-- 🤖 AI 주식 진단 리포트 -->
                <div class="card" style="margin-bottom: 20px; border-left: 4px solid #ce93d8;">
                    <h2 style="display:flex; justify-content:space-between; align-items:center;">
                        <span>🤖 AI 주식 진단 리포트</span>
                        <span id="ai-mode-badge" style="font-size:11px; font-weight:bold; padding:4px 8px; border-radius:12px; display:none;"></span>
                    </h2>
                    <p style="font-size: 13px; color:#888; margin-bottom: 15px;">원하는 종목을 입력하고 진단하기 버튼을 클릭하면, 실시간 수집된 시장 지표와 뉴스를 바탕으로 AI 리포트를 생성합니다.</p>
                    <div style="display:flex; gap:10px; align-items:center; margin-bottom:12px;">
                        <input type="text" id="ai-symbol" list="symbol-list" class="form-control" placeholder="예: 삼성전자" style="margin-bottom:0; width:180px;" oninput="searchSymbol(this.value)">
                        <button class="btn" id="btn-ai-query" onclick="queryAiOpinion()" style="background:#9c27b0; font-weight:bold; padding: 10px 20px;">🤖 AI 진단 개시</button>
                    </div>
                    
                    <div id="ai-loading" style="display:none; text-align:center; padding:20px;">
                        <div class="loading">AI가 시장 지표와 감성 코퍼스를 연산하여 의견서를 작성 중입니다...</div>
                    </div>
                    
                    <div id="ai-report-box" style="display:none; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); padding:18px; border-radius:10px; margin-top:12px;">
                        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px,1fr)); gap:10px; margin-bottom:15px;">
                            <div style="background:rgba(255,255,255,0.04); padding:10px; border-radius:8px; text-align:center;">
                                <div style="font-size:11px; color:#888;">추천 의견</div>
                                <div id="ai-rec" style="font-size:16px; font-weight:bold; margin-top:4px;">-</div>
                            </div>
                            <div style="background:rgba(255,255,255,0.04); padding:10px; border-radius:8px; text-align:center;">
                                <div style="font-size:11px; color:#888;">감성 등급</div>
                                <div id="ai-sent" style="font-size:16px; font-weight:bold; margin-top:4px;">-</div>
                            </div>
                            <div style="background:rgba(255,255,255,0.04); padding:10px; border-radius:8px; text-align:center;">
                                <div style="font-size:11px; color:#888;">추천 신뢰도</div>
                                <div id="ai-conf" style="font-size:16px; font-weight:bold; margin-top:4px;">-</div>
                            </div>
                            <div style="background:rgba(255,255,255,0.04); padding:10px; border-radius:8px; text-align:center;">
                                <div style="font-size:11px; color:#888;">목표 주가</div>
                                <div id="ai-target" style="font-size:16px; font-weight:bold; margin-top:4px;">-</div>
                            </div>
                        </div>
                        <div style="margin-bottom:12px;">
                            <h4 style="margin-bottom:4px; color:#ce93d8; font-size:13px;">💡 판단 근거 (Reasoning)</h4>
                            <p id="ai-reason" style="font-size:12px; color:#ccc; line-height:1.6; margin:0; white-space:pre-wrap;"></p>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                            <div>
                                <h4 style="margin-bottom:4px; color:#90caf9; font-size:13px;">💡 기회 요인 (Opportunities)</h4>
                                <p id="ai-opps" style="font-size:11px; color:#bbb; line-height:1.5; margin:0; white-space:pre-wrap;"></p>
                            </div>
                            <div>
                                <h4 style="margin-bottom:4px; color:#ef9a9a; font-size:13px;">⚠️ 위험 요인 (Risks)</h4>
                                <p id="ai-risks" style="font-size:11px; color:#bbb; line-height:1.5; margin:0; white-space:pre-wrap;"></p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- 미체결 주문 -->
                <div class="card">
                    <h2>미체결 주문</h2>
                    <div id="orders-table">
                        <div class="loading">데이터 로드 중...</div>
                    </div>
                </div>
                
                <!-- 최근 거래 -->
                <div class="card">
                    <h2>최근 거래 이력</h2>
                    <div id="trades-table">
                        <div class="loading">데이터 로드 중...</div>
                    </div>
                </div>
                
                </div>
                
                <!-- 종목 차트 팝업 모달 -->
                <div id="scan-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:9999; align-items:center; justify-content:center;">
                    <div style="background:#1e1e2e; border-radius:16px; padding:28px; width:90%; max-width:900px; max-height:90vh; overflow-y:auto; position:relative; box-shadow: 0 24px 64px rgba(0,0,0,0.5);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                            <div>
                                <h2 id="modal-title" style="margin:0; font-size:20px;">종목 백테스트 결과</h2>
                                <p id="modal-subtitle" style="margin:4px 0 0; font-size:13px; color:#888;"></p>
                            </div>
                            <button onclick="closeScanModal()" style="background:rgba(255,255,255,0.1); border:none; color:#fff; font-size:20px; width:36px; height:36px; border-radius:50%; cursor:pointer; line-height:36px;">✕</button>
                        </div>
                        <div id="modal-stats" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-bottom:18px;"></div>
                        <div id="modal-chart-container" style="height:320px; position:relative;">
                            <canvas id="modal-chart"></canvas>
                        </div>
                        <div id="modal-loading" style="text-align:center; padding:40px; display:none;">
                            <div class="loading">백테스트 차트를 불러오는 중입니다...</div>
                        </div>
                    </div>
                </div>

                <div id="tab-scanner" class="tab-content">
                    <div class="card" style="margin-bottom: 20px;">
                        <h2>📊 전체 종목 백테스트 스캐너</h2>
                        <p style="font-size: 13px; color: #888; margin-bottom: 15px;">한국 시장 전 종목(KOSPI/KOSDAQ) 및 주요 미국 주식을 대상으로 백그라운드 스캔을 수행합니다. 종목을 클릭하면 수익률 차트를 확인할 수 있습니다.</p>
                        
                        <details style="margin-bottom: 18px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.07); padding: 12px; border-radius: 8px;">
                            <summary style="font-size: 13px; font-weight: bold; color: #ccc; cursor: pointer; user-select: none;">🔍 스캔 대상 유니버스 종목 보기 (한국 전 종목 + 미국 대형주 10개)</summary>
                            <div style="margin-top: 10px; font-size: 12px; line-height: 1.7; color: #aaa;">
                                <div style="margin-bottom: 8px;">
                                    <strong style="color: #90caf9;">🇺🇸 미국 주식 (10개):</strong><br>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">AAPL</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">MSFT</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">GOOGL</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">AMZN</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">NVDA</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">META</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">TSLA</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">BRK-B</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">JPM</span>
                                    <span style="display: inline-block; background: rgba(255,255,255,0.05); padding: 1px 6px; border-radius: 4px; margin: 2px;">JNJ</span>
                                </div>
                                <div>
                                    <strong style="color: #ffcc80;">🇰🇷 한국 주식:</strong><br>
                                    KOSPI / KOSDAQ 전체 종목 (약 2000+개 종목 자동 동기화)
                                </div>
                            </div>
                        </details>
                        
                        <div style="display: flex; gap: 12px; align-items: flex-end; margin-bottom: 18px; flex-wrap: wrap;">
                            <div>
                                <label style="font-size: 12px; color: #888; display: block; margin-bottom: 5px;">전략 (마우스를 올려 설명 확인)</label>
                                <select id="scan-strategy" class="form-control" style="margin-bottom: 0; width: 180px;">
                                    <option value="MA" title="단순 이동평균선 돌파">이동평균(MA)</option>
                                    <option value="MACD" title="EMA 기반 MACD 골든/데드크로스">MACD(EMA)</option>
                                    <option value="RSI" title="RSI 과매도 반등 포착">RSI</option>
                                    <option value="BOLLINGER" title="볼린저밴드+RSI 복합 (횡보장 수익)">볼린저밴드(Bollinger)</option>
                                    <option value="ENSEMBLE" title="MA+RSI+MACD 투표 (거짓신호 필터링)">복합 전략(Ensemble)</option>
                                    <option value="TREND" title="추세 추종">추세 추종(Trend)</option>
                                    <option value="BUFFETT" title="워렌 버핏 가치/역발상">워렌 버핏(Value)</option>
                                    <option value="LYNCH" title="피터 린치 성장/모멘텀">피터 린치(Growth)</option>
                                    <option value="DALIO" title="레이 달리오 안정 투자">레이 달리오(Safe)</option>
                                </select>
                            </div>
                            <div>
                                <label style="font-size: 12px; color: #888; display: block; margin-bottom: 5px;">기간</label>
                                <select id="scan-period" class="form-control" style="margin-bottom: 0; width: 110px;">
                                    <option value="1mo">1개월</option>
                                    <option value="3mo">3개월</option>
                                    <option value="6mo">6개월</option>
                                    <option value="1y">1년</option>
                                    <option value="3y">3년</option>
                                    <option value="5y">5년</option>
                                    <option value="10y" selected>10년</option>
                                </select>
                            </div>
                            <div>
                                <label style="font-size: 12px; color: #888; display: block; margin-bottom: 5px;">최소 거래 횟수</label>
                                <select id="scan-min-trades" class="form-control" style="margin-bottom: 0; width: 110px;">
                                    <option value="0">전체</option>
                                    <option value="1" selected>1회 이상</option>
                                    <option value="3">3회 이상</option>
                                    <option value="5">5회 이상</option>
                                    <option value="10">10회 이상</option>
                                </select>
                            </div>
                            <div style="display: flex; align-items: center; height: 38px; padding-bottom: 2px;">
                                <label style="font-size: 12px; color: #aaa; display: flex; align-items: center; cursor: pointer; user-select: none;">
                                    <input type="checkbox" id="scan-allow-short" style="margin-right: 6px; width: 15px; height: 15px; cursor: pointer;">
                                    공매도(Short) 허용
                                </label>
                            </div>
                            <div>
                                <button class="btn" onclick="startScanner()" id="btn-scan" style="padding: 10px 24px;">▶ 스캔 시작</button>
                            </div>
                        </div>
                        
                        <div id="scan-progress-container" style="display: none; margin-bottom: 20px;">
                            <div style="font-size: 13px; color: #aaa; display: flex; justify-content: space-between; margin-bottom: 6px;">
                                <span>⏳ 스캔 진행 중...</span>
                                <span id="scan-progress-text">0 / 0</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-bar-fill" id="scan-progress-bar" style="transition: width 0.4s ease;"></div>
                            </div>
                        </div>

                        <!-- 요약 통계 -->
                        <div id="scan-summary" style="display:none; margin-bottom:18px;">
                            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:10px;">
                                <div style="background:rgba(76,175,80,0.12); border:1px solid rgba(76,175,80,0.3); border-radius:10px; padding:12px; text-align:center;">
                                    <div style="font-size:11px; color:#888; margin-bottom:4px;">스캔 종목 수</div>
                                    <div id="sum-total" style="font-size:20px; font-weight:700; color:#4caf50;">-</div>
                                </div>
                                <div style="background:rgba(33,150,243,0.12); border:1px solid rgba(33,150,243,0.3); border-radius:10px; padding:12px; text-align:center;">
                                    <div style="font-size:11px; color:#888; margin-bottom:4px;">평균 수익률</div>
                                    <div id="sum-avg-ret" style="font-size:20px; font-weight:700; color:#2196f3;">-</div>
                                </div>
                                <div style="background:rgba(255,193,7,0.12); border:1px solid rgba(255,193,7,0.3); border-radius:10px; padding:12px; text-align:center;">
                                    <div style="font-size:11px; color:#888; margin-bottom:4px;">수익 종목 수</div>
                                    <div id="sum-positive" style="font-size:20px; font-weight:700; color:#ffc107;">-</div>
                                </div>
                                <div style="background:rgba(156,39,176,0.12); border:1px solid rgba(156,39,176,0.3); border-radius:10px; padding:12px; text-align:center;">
                                    <div style="font-size:11px; color:#888; margin-bottom:4px;">최고 수익률 종목</div>
                                    <div id="sum-best" style="font-size:14px; font-weight:700; color:#ce93d8;">-</div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="scan-results" style="display: none;">
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 24px; margin-top: 10px;">
                                <div>
                                    <h3 style="margin-bottom: 12px; border-bottom: 2px solid #4caf50; padding-bottom: 6px; color: #4caf50; font-size:15px;">🇰🇷 한국 시장 수익률 순위</h3>
                                    <div id="scan-results-kr"></div>
                                </div>
                                <div>
                                    <h3 style="margin-bottom: 12px; border-bottom: 2px solid #2196f3; padding-bottom: 6px; color: #64b5f6; font-size:15px;">🇺🇸 미국 시장 수익률 순위</h3>
                                    <div id="scan-results-us"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <footer>
                    <p>주식 트레이딩 시스템 v1.0.0 | 실시간 모니터링</p>
                </footer>
            </div>
            
            <script>
                let equityChart = null;
                let pieChart = null;

                // 데이터 갱신
                async function updateData() {
                    try {
                        const portfolio = await fetch('/api/portfolio').then(r => r.json());
                        if (portfolio.status === 'success') {
                            document.getElementById('cash').textContent = 
                                '$' + portfolio.data.cash.toLocaleString('en-US', {maximumFractionDigits: 0});
                            document.getElementById('positions').textContent = 
                                Object.keys(portfolio.data.positions).length;
                                
                            updateAllocationChart(portfolio.data.cash, portfolio.data.positions);
                        }
                        
                        const history = await fetch('/api/portfolio/history').then(r => r.json());
                        if (history.status === 'success' && history.data.labels.length > 0) {
                            document.getElementById('portfolio-charts-grid').style.display = 'grid';
                            updateEquityChart(history.data.labels, history.data.values);
                        }
                        
                        const perf = await fetch('/api/performance').then(r => r.json());
                        if (perf.status === 'success') {
                            document.getElementById('win-rate').textContent = 
                                (perf.data.win_rate * 100).toFixed(1);
                            document.getElementById('avg-slippage').textContent = 
                                (perf.data.avg_slippage * 100).toFixed(4);
                            document.getElementById('total-trades').textContent = 
                                perf.data.total_trades;
                        }
                        
                        const orders = await fetch('/api/orders').then(r => r.json());
                        if (orders.status === 'success') {
                            document.getElementById('open-orders').textContent = orders.count;
                            updateOrdersTable(orders.data);
                        }
                        
                        const trades = await fetch('/api/trades').then(r => r.json());
                        if (trades.status === 'success') {
                            updateTradesTable(trades.data);
                        }
                        
                        const risk = await fetch('/api/risk').then(r => r.json());
                        if (risk.status === 'success') {
                            document.getElementById('risk-grid').style.display = 'grid';
                            document.getElementById('drawdown').textContent = risk.data.drawdown;
                            document.getElementById('risk-level').textContent = risk.data.risk_level;
                        }
                        
                        document.getElementById('update-time').textContent = 
                            new Date().toLocaleTimeString('ko-KR');
                    } catch (error) {
                        console.error('Update error:', error);
                    }
                }
                
                function updateOrdersTable(orders) {
                    let html = '<table>';
                    html += '<tr><th>주문 ID</th><th>종목</th><th>구분</th><th>수량</th><th>가격</th><th>상태</th><th>액션</th></tr>';
                    
                    if (orders.length === 0) {
                        html += '<tr><td colspan="7" style="text-align: center; color: #999;">미체결 주문 없음</td></tr>';
                    } else {
                        orders.forEach(o => {
                            html += '<tr>';
                            html += '<td>' + o.order_id.substring(0, 12) + '</td>';
                            html += '<td>' + o.symbol + '</td>';
                            html += '<td>' + o.type + '</td>';
                            html += '<td>' + o.quantity + '</td>';
                            html += '<td>$' + o.price.toFixed(2) + '</td>';
                            html += '<td><span class="status-badge status-' + o.status.toLowerCase() + '">' + o.status + '</span></td>';
                            html += `<td><button class="btn btn-sm" onclick="cancelOrder('${o.order_id}')" style="background:#f44336; padding:4px 10px; font-size:11px; margin:0; border-radius:4px; font-weight:bold;">취소</button></td>`;
                            html += '</tr>';
                        });
                    }
                    
                    html += '</table>';
                    document.getElementById('orders-table').innerHTML = html;
                }

                // ── 수동 주문 관련 자바스크립트 핸들러 ──────────────────────
                function togglePriceInput(val) {
                    const priceContainer = document.getElementById('trade-price-container');
                    if (val === 'MARKET') {
                        priceContainer.style.display = 'none';
                    } else {
                        priceContainer.style.display = 'block';
                    }
                }

                async function placeOrder() {
                    const symbol = document.getElementById('trade-symbol').value.trim();
                    const side = document.getElementById('trade-side').value;
                    const priceType = document.getElementById('trade-price-type').value;
                    const price = parseFloat(document.getElementById('trade-price').value) || 0;
                    const qty = parseInt(document.getElementById('trade-qty').value) || 0;
                    const feedback = document.getElementById('trade-feedback');
                    const btn = document.getElementById('btn-place-order');

                    if (!symbol) {
                        alert('종목명을 입력하세요.');
                        return;
                    }
                    if (qty <= 0) {
                        alert('수량은 1주 이상이어야 합니다.');
                        return;
                    }
                    if (priceType === 'LIMIT' && price <= 0) {
                        alert('지정가 주문 시 가격을 입력하셔야 합니다.');
                        return;
                    }

                    btn.disabled = true;
                    btn.textContent = '제출 중...';
                    feedback.style.display = 'none';

                    try {
                        const resp = await fetch('/api/orders/place', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                symbol: symbol,
                                order_type: side,
                                quantity: qty,
                                price_type: priceType,
                                price: price
                            })
                        });
                        const res = await resp.json();
                        btn.disabled = false;
                        btn.textContent = '주문 제출';

                        feedback.style.display = 'block';
                        if (res.status === 'success') {
                            feedback.style.background = 'rgba(76,175,80,0.15)';
                            feedback.style.border = '1px solid rgba(76,175,80,0.4)';
                            feedback.style.color = '#81c784';
                            feedback.textContent = res.message;
                            
                            // 주문 성공 후 인풋 값 부분 클리어
                            document.getElementById('trade-symbol').value = '';
                            document.getElementById('trade-price').value = '';
                            
                            // 전역 데이터 새로고침
                            updateData();
                        } else {
                            feedback.style.background = 'rgba(244,67,54,0.15)';
                            feedback.style.border = '1px solid rgba(244,67,54,0.4)';
                            feedback.style.color = '#e57373';
                            feedback.textContent = '오류: ' + res.message;
                        }
                    } catch (e) {
                        btn.disabled = false;
                        btn.textContent = '주문 제출';
                        feedback.style.display = 'block';
                        feedback.style.background = 'rgba(244,67,54,0.15)';
                        feedback.style.border = '1px solid rgba(244,67,54,0.4)';
                        feedback.style.color = '#e57373';
                        feedback.textContent = '네트워크 오류가 발생했습니다: ' + e.message;
                    }
                }

                async function cancelOrder(orderId) {
                    if (!confirm('정말로 이 주문을 취소하시겠습니까?')) return;

                    try {
                        const resp = await fetch('/api/orders/cancel', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ order_id: orderId })
                        });
                        const res = await resp.json();

                        if (res.status === 'success') {
                            alert(res.message);
                            updateData();
                        } else {
                            alert('취소 실패: ' + res.message);
                        }
                    } catch (e) {
                        alert('네트워크 오류가 발생했습니다: ' + e.message);
                    }
                }

                // ── 실시간 리스크 관리 설정 반영 ──────────────────────────
                async function saveRiskSettings() {
                    const sl = parseFloat(document.getElementById('risk-input-sl').value);
                    const mdd = parseFloat(document.getElementById('risk-input-mdd').value);
                    const pos = parseFloat(document.getElementById('risk-input-pos').value);
                    const activeStrat = document.getElementById('system-active-strategy').value;
                    const feedback = document.getElementById('risk-settings-feedback');

                    feedback.style.display = 'none';

                    try {
                        const resp = await fetch('/api/risk/settings', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                stop_loss_pct: sl,
                                max_portfolio_loss_pct: mdd,
                                max_position_size_pct: pos,
                                active_strategy: activeStrat
                            })
                        });
                        const res = await resp.json();
                        feedback.style.display = 'block';

                        if (res.status === 'success') {
                            feedback.style.background = 'rgba(76,175,80,0.15)';
                            feedback.style.border = '1px solid rgba(76,175,80,0.4)';
                            feedback.style.color = '#81c784';
                            feedback.textContent = res.message;
                            setTimeout(() => { feedback.style.display = 'none'; }, 3000);
                        } else {
                            feedback.style.background = 'rgba(244,67,54,0.15)';
                            feedback.style.border = '1px solid rgba(244,67,54,0.4)';
                            feedback.style.color = '#e57373';
                            feedback.textContent = '설정 반영 실패: ' + res.message;
                        }
                    } catch (e) {
                        feedback.style.display = 'block';
                        feedback.style.background = 'rgba(244,67,54,0.15)';
                        feedback.style.border = '1px solid rgba(244,67,54,0.4)';
                        feedback.style.color = '#e57373';
                        feedback.textContent = '네트워크 에러: ' + e.message;
                    }
                }

                // ── 자산 및 시뮬레이션 상태 초기화 ─────────────────────────
                async function resetPortfolio() {
                    if (!confirm('경고: 정말로 가상 자산을 초기화하시겠습니까?\n모든 보유 포지션이 청산되며 주문 기록과 자산 이력이 삭제됩니다.')) return;
                    
                    try {
                        const resp = await fetch('/api/portfolio/reset', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'}
                        });
                        const res = await resp.json();
                        if (res.status === 'success') {
                            alert(res.message);
                            updateData();
                            window.location.reload();
                        } else {
                            alert('초기화 실패: ' + res.message);
                        }
                    } catch (e) {
                        alert('네트워크 오류가 발생했습니다: ' + e.message);
                    }
                }

                // ── 리스크 및 전략 설정 초기 세팅 로드 ─────────────────────
                async function initSettings() {
                    try {
                        const risk = await fetch('/api/risk').then(r => r.json());
                        if (risk.status === 'success' && risk.data.stop_loss_pct !== undefined) {
                            const sl = risk.data.stop_loss_pct;
                            const mdd = risk.data.max_portfolio_loss_pct;
                            const pos = risk.data.max_position_size_pct;
                            const strat = risk.data.active_strategy || 'HYBRID';
                            
                            document.getElementById('risk-input-sl').value = sl;
                            document.getElementById('lbl-sl').textContent = sl + '%';
                            
                            document.getElementById('risk-input-mdd').value = mdd;
                            document.getElementById('lbl-mdd').textContent = mdd + '%';
                            
                            document.getElementById('risk-input-pos').value = pos;
                            document.getElementById('lbl-pos').textContent = pos + '%';
                            
                            document.getElementById('system-active-strategy').value = strat;
                        }
                    } catch (e) {
                        console.error('Failed to initialize risk settings:', e);
                    }
                }

                // ── AI 주식 진단 리포트 요청 ──────────────────────────────
                async function queryAiOpinion() {
                    const symbol = document.getElementById('ai-symbol').value.trim();
                    const loading = document.getElementById('ai-loading');
                    const repBox = document.getElementById('ai-report-box');
                    const btn = document.getElementById('btn-ai-query');

                    if (!symbol) {
                        alert('진단할 종목명을 입력하세요.');
                        return;
                    }

                    btn.disabled = true;
                    loading.style.display = 'block';
                    repBox.style.display = 'none';

                    try {
                        const resp = await fetch('/api/ai/opinion', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ symbol: symbol })
                        });
                        const res = await resp.json();
                        btn.disabled = false;
                        loading.style.display = 'none';

                        if (res.status === 'success') {
                            const d = res.data;
                            
                            document.getElementById('ai-rec').textContent = d.recommendation || '보유 (HOLD)';
                            document.getElementById('ai-sent').textContent = d.sentiment || 'NEUTRAL';
                            document.getElementById('ai-conf').textContent = ((d.confidence || 0.5) * 100).toFixed(0) + '%';
                            
                            // 통화 단위 동적 분기
                            const isKor = d.symbol && (d.symbol.endsWith('.KS') || d.symbol.endsWith('.KQ'));
                            const currencySym = isKor ? '₩' : '$';
                            const targetVal = parseFloat(d.target_price);
                            if (!isNaN(targetVal) && targetVal > 0) {
                                document.getElementById('ai-target').textContent = currencySym + targetVal.toLocaleString(undefined, {
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: isKor ? 0 : 2
                                });
                            } else {
                                document.getElementById('ai-target').textContent = '-';
                            }
                            
                            document.getElementById('ai-reason').textContent = d.reasoning || '충분한 근거 지표 부재';
                            document.getElementById('ai-opps').textContent = Array.isArray(d.opportunities) ? d.opportunities.join('\n') : (d.opportunities || 'N/A');
                            document.getElementById('ai-risks').textContent = Array.isArray(d.risks) ? d.risks.join('\n') : (d.risks || 'N/A');

                            // AI 진단 모드 배지 표시
                            const badge = document.getElementById('ai-mode-badge');
                            if (badge) {
                                badge.style.display = 'inline-block';
                                if (d.is_simulated) {
                                    badge.textContent = '⚠️ AI 모의 모드';
                                    badge.style.background = 'rgba(255, 152, 0, 0.15)';
                                    badge.style.border = '1px solid rgba(255, 152, 0, 0.4)';
                                    badge.style.color = '#ffb74d';
                                } else {
                                    badge.textContent = '🟢 OpenAI 실시간 분석';
                                    badge.style.background = 'rgba(76, 175, 80, 0.15)';
                                    badge.style.border = '1px solid rgba(76, 175, 80, 0.4)';
                                    badge.style.color = '#81c784';
                                }
                            }

                            // 추천 의견 색상 강조
                            const recEl = document.getElementById('ai-rec');
                            if (d.recommendation && (d.recommendation.includes('매수') || d.recommendation.includes('BUY'))) {
                                recEl.style.color = '#4caf50';
                            } else if (d.recommendation && (d.recommendation.includes('매도') || d.recommendation.includes('SELL'))) {
                                recEl.style.color = '#f44336';
                            } else {
                                recEl.style.color = '#ffeb3b';
                            }

                            repBox.style.display = 'block';
                        } else {
                            alert('AI 진단 실패: ' + res.message);
                        }
                    } catch (e) {
                        btn.disabled = false;
                        loading.style.display = 'none';
                        alert('AI 의견 수집 중 네트워크 오류: ' + e.message);
                    }
                }
                
                function updateTradesTable(trades) {
                    let html = '<table>';
                    html += '<tr><th>주문 ID</th><th>종목</th><th>구분</th><th>수량</th><th>가격</th><th>상태</th></tr>';
                    
                    if (trades.length === 0) {
                        html += '<tr><td colspan="6" style="text-align: center; color: #999;">거래 없음</td></tr>';
                    } else {
                        trades.slice(0, 10).forEach(t => {
                            html += '<tr>';
                            html += '<td>' + t.order_id.substring(0, 12) + '</td>';
                            html += '<td>' + t.symbol + '</td>';
                            html += '<td>' + t.order_type + '</td>';
                            html += '<td>' + t.quantity + '</td>';
                            html += '<td>$' + t.price.toFixed(2) + '</td>';
                            html += '<td><span class="status-badge status-executed">' + t.status + '</span></td>';
                            html += '</tr>';
                        });
                    }
                    
                    html += '</table>';
                    document.getElementById('trades-table').innerHTML = html;
                }
                
                let btChart = null;
                
                async function runBacktest() {
                    const symbol = document.getElementById('bt-symbol').value;
                    const strategy = document.getElementById('bt-strategy').value;
                    const period = document.getElementById('bt-period').value;
                    const allowShort = document.getElementById('bt-allow-short').checked;
                    const trailingStop = parseInt(document.getElementById('bt-trailing-stop').value) / 100;
                    const scaleIn = document.getElementById('bt-scale-in').checked;
                    const stopLoss = parseInt(document.getElementById('bt-stop-loss')?.value || '0') / 100;
                    const takeProfit = parseInt(document.getElementById('bt-take-profit')?.value || '0') / 100;
                    const resultDiv = document.getElementById('bt-result');
                    const canvas = document.getElementById('bt-chart');
                    const chartContainer = document.getElementById('bt-chart-container');
                    const btn = document.querySelector('button[onclick="runBacktest()"]');
                    
                    if (!symbol) return;
                    
                    btn.disabled = true;
                    btn.textContent = '실행 중...';
                    resultDiv.style.display = 'block';
                    chartContainer.style.display = 'none';
                    resultDiv.innerHTML = '<div class="loading">과거 데이터를 yfinance에서 다운로드하여 시뮬레이션 중입니다...</div>';
                    
                    try {
                        const response = await fetch('/api/backtest', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ symbol: symbol, strategy: strategy, period: period, allow_short: allowShort, trailing_stop_pct: trailingStop, scale_in: scaleIn, stop_loss_pct: stopLoss, take_profit_pct: takeProfit })
                        });
                        
                        const res = await response.json();
                        
                        if (res.status === 'success') {
                            const d = res.data;
                            const tsInfo = d.trailing_stop_count > 0 ? `<div><span style="color:#666; font-size:12px;">트레일링 스톱 발동</span><br/><strong style="color:#ff9800;">${d.trailing_stop_count}회</strong></div>` : '';
                            resultDiv.innerHTML = `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px;">
                                    <div><span style="color:#666; font-size:12px;">테스트 기간</span><br/><strong>${d.start_date} ~ ${d.end_date}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">예상 총 수익률</span><br/><strong class="value ${d.total_return_pct.startsWith('-') ? 'negative' : 'positive'}" style="font-size:20px;">${d.total_return_pct}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">승률</span><br/><strong>${d.win_rate}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">최대 낙폭 (MDD)</span><br/><strong class="value negative">${d.max_drawdown}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">Profit Factor</span><br/><strong>${d.profit_factor}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">Sharpe Ratio</span><br/><strong>${d.sharpe_ratio}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">거래 횟수</span><br/><strong>${d.trades_count}회</strong></div>
                                    ${tsInfo}
                                </div>
                            `;
                            
                            // 차트 그리기
                            if (d.chart_data && d.chart_data.labels.length > 0) {
                                if (typeof Chart === 'undefined') {
                                    throw new Error("차트 라이브러리(Chart.js)가 차단되었거나 로드되지 않았습니다. 브라우저의 광고 차단 확장프로그램을 잠시 꺼주세요.");
                                }
                                chartContainer.style.display = 'block';
                                const ctx = canvas.getContext('2d');
                                if (btChart) btChart.destroy();
                                
                                btChart = new Chart(ctx, {
                                    type: 'line',
                                    data: {
                                        labels: d.chart_data.labels,
                                        datasets: [
                                            {
                                                label: '자산 가치 (Equity)',
                                                data: d.chart_data.equity,
                                                borderColor: '#4caf50',
                                                borderWidth: 2,
                                                pointRadius: 0,
                                                fill: false
                                            },
                                            {
                                                label: '주가 (Benchmark)',
                                                data: d.chart_data.price,
                                                borderColor: '#2196f3',
                                                borderWidth: 1.5,
                                                pointRadius: 0,
                                                borderDash: [5, 5],
                                                fill: false
                                            },
                                            {
                                                label: '매수 (Buy)',
                                                data: d.chart_data.buy_points,
                                                backgroundColor: '#ff5722',
                                                borderColor: '#ff5722',
                                                pointStyle: 'triangle',
                                                pointRadius: 6,
                                                showLine: false
                                            },
                                            {
                                                label: '매도 (Sell)',
                                                data: d.chart_data.sell_points,
                                                backgroundColor: '#9c27b0',
                                                borderColor: '#9c27b0',
                                                pointStyle: 'crossRot',
                                                pointRadius: 6,
                                                showLine: false
                                            }
                                        ]
                                    },
                                    options: {
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        interaction: { mode: 'index', intersect: false },
                                        plugins: {
                                            title: { display: true, text: '포트폴리오 성과 vs 벤치마크 (시작점 = 100)' },
                                            tooltip: { enabled: true }
                                        },
                                        scales: {
                                            x: { display: true, title: { display: true, text: '날짜' }, ticks: { maxTicksLimit: 10 } },
                                            y: { display: true, title: { display: true, text: '가치 (기준점: 100)' } }
                                        }
                                    }
                                });
                            }
                        } else {
                            resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px;"><strong>오류 발생:</strong> ${res.message}</div>`;
                            if (chartContainer) chartContainer.style.display = 'none';
                        }
                    } catch (error) {
                        console.error('Frontend execution error:', error);
                        resultDiv.innerHTML = `<div style="color: #f44336; padding: 10px;">클라이언트/네트워크 오류가 발생했습니다. 상세: ${error.message || error}</div>`;
                        if (chartContainer) chartContainer.style.display = 'none';
                    } finally {
                        btn.disabled = false;
                        btn.textContent = '백테스트 실행';
                    }
                }
                
                let searchTimeout;
                async function searchSymbol(query) {
                    if (query.length < 2) return;
                    clearTimeout(searchTimeout);
                    
                    searchTimeout = setTimeout(async () => {
                        try {
                            const response = await fetch('/api/search?q=' + encodeURIComponent(query));
                            const res = await response.json();
                            if (res.status === 'success') {
                                const datalist = document.getElementById('symbol-list');
                                datalist.innerHTML = '';
                                res.results.forEach(item => {
                                    const option = document.createElement('option');
                                    option.value = item.symbol;
                                    option.textContent = item.name + ' (' + item.symbol + ')';
                                    datalist.appendChild(option);
                                });
                            }
                        } catch (e) {
                            console.error('Search API error:', e);
                        }
                    }, 300); // 300ms 디바운스 처리
                }
                
                // 초기 설정 및 데이터 로드
                initSettings();
                updateData();
                
                // WebSocket 연결 설정
                const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const ws = new WebSocket(wsProtocol + '//' + window.location.host + '/ws');
                
                ws.onopen = function() {
                    console.log('Connected to real-time WebSocket dashboard');
                    document.querySelector('header .timestamp').innerHTML += ' (실시간)';
                };
                
                ws.onmessage = function(event) {
                    try {
                        const msg = JSON.parse(event.data);
                        if (msg.type === 'order_update') {
                            console.log('Order update received via WS:', msg.data);
                            updateData();
                        } else if (msg.type === 'portfolio_update') {
                            console.log('Portfolio update received via WS:', msg.data);
                            updateData();
                        } else if (msg.type === 'market_data_update') {
                            // 시장 데이터 렌더링 최적화를 위해 전체 갱신 대신 시세만 갱신 가능 (여기선 생략)
                        }
                    } catch (e) {
                        console.error("Error parsing WS message:", e);
                    }
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket Error:', error);
                };
                
                ws.onclose = function() {
                    console.warn('WebSocket connection closed. Reverting to polling...');
                    setInterval(updateData, 5000);
                };
                
                // 탭 스위칭 로직
                function switchTab(tabId) {
                    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
                    
                    document.getElementById('tabbtn-' + tabId).classList.add('active');
                    document.getElementById('tab-' + tabId).classList.add('active');
                }
                
                // 스캐너 로직
                let scanInterval;
                async function startScanner() {
                    const strategy = document.getElementById('scan-strategy').value;
                    const period = document.getElementById('scan-period').value;
                    const allowShort = document.getElementById('scan-allow-short').checked;
                    const trailingStop = parseInt(document.getElementById('bt-trailing-stop')?.value || '0') / 100;
                    const scaleIn = document.getElementById('bt-scale-in')?.checked || false;
                    const stopLoss = parseInt(document.getElementById('bt-stop-loss')?.value || '0') / 100;
                    const takeProfit = parseInt(document.getElementById('bt-take-profit')?.value || '0') / 100;
                    const btn = document.getElementById('btn-scan');
                    
                    btn.disabled = true;
                    btn.textContent = "스캔 진행 중...";
                    document.getElementById('scan-progress-container').style.display = 'block';
                    document.getElementById('scan-results').style.display = 'none';
                    
                    try {
                        const res = await fetch('/api/scanner/start', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ strategy: strategy, period: period, allow_short: allowShort, trailing_stop_pct: trailingStop, scale_in: scaleIn, stop_loss_pct: stopLoss, take_profit_pct: takeProfit })
                        });
                        const data = await res.json();
                        
                        if (data.status === 'success') {
                            const taskId = data.task_id;
                            scanInterval = setInterval(() => pollScanner(taskId), 1000);
                        } else {
                            alert("스캐너 시작 실패: " + data.message);
                            btn.disabled = false;
                            btn.textContent = "스캔 시작";
                        }
                    } catch (e) {
                        console.error(e);
                        btn.disabled = false;
                        btn.textContent = "스캔 시작";
                    }
                }
                
                async function pollScanner(taskId) {
                    try {
                        const res = await fetch('/api/scanner/status/' + taskId);
                        const data = await res.json();
                        if (data.status === 'success') {
                            const task = data.data;
                            const percent = Math.round((task.progress / Math.max(1, task.total)) * 100);
                            
                            document.getElementById('scan-progress-bar').style.width = percent + '%';
                            document.getElementById('scan-progress-text').textContent = `${task.progress} / ${task.total} (${percent}%)`;
                            
                            if (task.status === 'completed') {
                                clearInterval(scanInterval);
                                document.getElementById('btn-scan').disabled = false;
                                document.getElementById('btn-scan').textContent = "스캔 완료 (다시 시작)";
                                renderScannerResults(task.results);
                            }
                        }
                    } catch (e) {
                        console.error(e);
                    }
                }
                
                // 스캔 결과 전역 보관
                let allScanResults = [];
                let scanModalChart = null;

                function getMinTrades() {
                    return parseInt(document.getElementById('scan-min-trades').value) || 0;
                }

                function createTableHtml(results, market) {
                    const minTrades = getMinTrades();
                    const filtered = results.filter(r => (r.trades || 0) >= minTrades);

                    if (filtered.length === 0) {
                        return `<p style='color:#888; text-align:center; padding:24px; font-size:13px;'>필터 조건에 맞는 결과가 없습니다.</p>`;
                    }

                    let html = `<div style="overflow-x:auto;">
                    <table style="width:100%; font-size:13px;">
                    <thead><tr style="background:rgba(255,255,255,0.05);">
                        <th style="padding:8px 6px; text-align:center; white-space:nowrap;">순위</th>
                        <th style="padding:8px 6px; text-align:left;">종목</th>
                        ${market === 'KR' ? '<th style="padding:8px 4px; text-align:center;">시장</th>' : ''}
                        <th style="padding:8px 6px; text-align:right;">수익률</th>
                        <th style="padding:8px 6px; text-align:right;">승률</th>
                        <th style="padding:8px 6px; text-align:right;">샤프</th>
                        <th style="padding:8px 6px; text-align:right;">거래</th>
                        <th style="padding:8px 6px; text-align:right;">MDD</th>
                    </tr></thead><tbody>`;

                    filtered.forEach((r, idx) => {
                        const trades   = r.trades || 0;
                        const retPct   = r.return_pct !== undefined && r.return_pct !== null ? r.return_pct : 0;
                        const winRate  = r.win_rate  !== undefined && r.win_rate  !== null ? r.win_rate  : 0;
                        const mdd      = r.mdd       !== undefined && r.mdd       !== null ? r.mdd       : 0;
                        const sharpe   = r.sharpe    !== undefined && r.sharpe    !== null ? r.sharpe    : 0;

                        const retColor  = retPct >= 0 ? '#4caf50' : '#f44336';
                        const retArrow  = retPct >= 0 ? '▲' : '▼';
                        const dispRet   = retArrow + (retPct * 100).toFixed(2) + '%';
                        const dispWin   = trades > 0 ? (winRate * 100).toFixed(1) + '%' : '-';
                        const dispMdd   = trades > 0 ? (mdd   * 100).toFixed(2) + '%' : '-';
                        const dispSharpe= trades > 0 ? sharpe.toFixed(2) : '-';

                        const exchBadge = r.exchange === 'KOSPI'
                            ? `<span style="font-size:10px; padding:2px 6px; border-radius:4px; background:rgba(76,175,80,0.2); color:#81c784; font-weight:600;">KOSPI</span>`
                            : r.exchange === 'KOSDAQ'
                            ? `<span style="font-size:10px; padding:2px 6px; border-radius:4px; background:rgba(255,193,7,0.2); color:#ffd54f; font-weight:600;">KOSDAQ</span>`
                            : '';

                        const bgHover = 'rgba(255,255,255,0.04)';
                        const ticker  = r.ticker || r.symbol;

                        html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05); cursor:pointer; transition:background 0.15s;"
                            onmouseover="this.style.background='${bgHover}'"
                            onmouseout="this.style.background='transparent'"
                            onclick="openScanChart('${ticker}', '${r.symbol}', '${r.exchange || ''}')">
                            <td style="padding:9px 6px; text-align:center; color:#888;">${idx + 1}</td>
                            <td style="padding:9px 6px; font-weight:600; white-space:nowrap;">
                                🔍 ${r.symbol}
                            </td>
                            ${market === 'KR' ? `<td style="padding:9px 4px; text-align:center;">${exchBadge}</td>` : ''}
                            <td style="padding:9px 6px; text-align:right; color:${retColor}; font-weight:700;">${dispRet}</td>
                            <td style="padding:9px 6px; text-align:right; color:#aaa;">${dispWin}</td>
                            <td style="padding:9px 6px; text-align:right; color:#aaa;">${dispSharpe}</td>
                            <td style="padding:9px 6px; text-align:right; color:#aaa;">${trades}회</td>
                            <td style="padding:9px 6px; text-align:right; color:#ef9a9a;">${dispMdd}</td>
                        </tr>`;
                    });

                    html += '</tbody></table></div>';
                    return html;
                }

                function renderSummary(results) {
                    if (!results || results.length === 0) return;
                    const minTrades = getMinTrades();
                    const valid = results.filter(r => (r.trades || 0) >= minTrades);
                    if (valid.length === 0) return;

                    const avg = valid.reduce((s, r) => s + r.return_pct, 0) / valid.length;
                    const pos = valid.filter(r => r.return_pct > 0).length;
                    const best = valid.reduce((a, b) => a.return_pct > b.return_pct ? a : b);

                    document.getElementById('sum-total').textContent   = valid.length + '종목';
                    document.getElementById('sum-avg-ret').textContent = (avg * 100).toFixed(2) + '%';
                    document.getElementById('sum-positive').textContent = pos + '종목';
                    document.getElementById('sum-best').textContent    = best.symbol + ' ' + (best.return_pct * 100).toFixed(1) + '%';
                    document.getElementById('sum-avg-ret').style.color  = avg >= 0 ? '#4caf50' : '#f44336';
                    document.getElementById('scan-summary').style.display = 'block';
                }

                function renderScannerResults(results) {
                    allScanResults = results;
                    if (results.length === 0) {
                        document.getElementById('scan-results-kr').innerHTML = '<p style="color:#888;">결과가 없습니다.</p>';
                        document.getElementById('scan-results-us').innerHTML = '<p style="color:#888;">결과가 없습니다.</p>';
                        document.getElementById('scan-results').style.display = 'block';
                        return;
                    }

                    const krResults = results.filter(r => r.market === 'KR').sort((a, b) => b.return_pct - a.return_pct);
                    const usResults = results.filter(r => r.market === 'US').sort((a, b) => b.return_pct - a.return_pct);

                    document.getElementById('scan-results-kr').innerHTML = createTableHtml(krResults.slice(0, 50), 'KR');
                    document.getElementById('scan-results-us').innerHTML = createTableHtml(usResults.slice(0, 50), 'US');
                    document.getElementById('scan-results').style.display = 'block';
                    renderSummary(results);
                }

                // ── 종목 클릭 시 차트 팝업 ──────────────────────────────────
                async function openScanChart(ticker, name, exchange) {
                    const modal = document.getElementById('scan-modal');
                    modal.style.display = 'flex';
                    document.getElementById('modal-title').textContent = name;
                    const period = document.getElementById('scan-period').value;
                    const strategy = document.getElementById('scan-strategy').value;
                    const allowShort = document.getElementById('scan-allow-short').checked;
                    const trailingStop = parseInt(document.getElementById('bt-trailing-stop')?.value || '0') / 100;
                    const scaleIn = document.getElementById('bt-scale-in')?.checked || false;
                    const stopLoss = parseInt(document.getElementById('bt-stop-loss')?.value || '0') / 100;
                    const takeProfit = parseInt(document.getElementById('bt-take-profit')?.value || '0') / 100;
                    const exchLabel = exchange ? ` · ${exchange}` : '';
                    document.getElementById('modal-subtitle').textContent = ticker + exchLabel + '  |  전략: ' + strategy + '  |  기간: ' + period;
                    document.getElementById('modal-stats').innerHTML = '';
                    document.getElementById('modal-loading').style.display = 'block';
                    document.getElementById('modal-chart-container').style.display = 'none';

                    try {
                        const resp = await fetch('/api/backtest', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ symbol: ticker, strategy: strategy, period: period, allow_short: allowShort, trailing_stop_pct: trailingStop, scale_in: scaleIn, stop_loss_pct: stopLoss, take_profit_pct: takeProfit })
                        });
                        const res = await resp.json();
                        document.getElementById('modal-loading').style.display = 'none';

                        if (res.status === 'success') {
                            const d = res.data;
                            // 통계 카드
                            const stats = [
                                { label: '총 수익률',  value: d.total_return_pct, color: d.total_return_pct.startsWith('-') ? '#f44336' : '#4caf50' },
                                { label: '승률',       value: d.win_rate,          color: '#64b5f6' },
                                { label: '최대 낙폭',  value: d.max_drawdown,      color: '#ef9a9a' },
                                { label: '거래 횟수',  value: d.trades_count + '회', color: '#ce93d8' },
                                { label: '기간',       value: d.start_date + ' ~ ' + d.end_date, color: '#aaa' },
                            ];
                            document.getElementById('modal-stats').innerHTML = stats.map(s =>
                                `<div style="background:rgba(255,255,255,0.05); border-radius:10px; padding:10px 14px;">
                                    <div style="font-size:11px; color:#888; margin-bottom:4px;">${s.label}</div>
                                    <div style="font-size:15px; font-weight:700; color:${s.color};">${s.value}</div>
                                </div>`
                            ).join('');

                            // 차트
                            if (d.chart_data && d.chart_data.labels.length > 0) {
                                document.getElementById('modal-chart-container').style.display = 'block';
                                const ctx = document.getElementById('modal-chart').getContext('2d');
                                if (scanModalChart) scanModalChart.destroy();
                                scanModalChart = new Chart(ctx, {
                                    type: 'line',
                                    data: {
                                        labels: d.chart_data.labels,
                                        datasets: [
                                            { label: '자산 (Equity)', data: d.chart_data.equity, borderColor: '#4caf50', borderWidth: 2, pointRadius: 0, fill: false },
                                            { label: '주가 (Benchmark)', data: d.chart_data.price, borderColor: '#2196f3', borderWidth: 1.5, pointRadius: 0, borderDash: [5,5], fill: false },
                                            { label: '매수', data: d.chart_data.buy_points, backgroundColor: '#ff5722', borderColor: '#ff5722', pointStyle: 'triangle', pointRadius: 6, showLine: false },
                                            { label: '매도', data: d.chart_data.sell_points, backgroundColor: '#ce93d8', borderColor: '#ce93d8', pointStyle: 'crossRot', pointRadius: 6, showLine: false }
                                        ]
                                    },
                                    options: {
                                        responsive: true, maintainAspectRatio: false,
                                        interaction: { mode: 'index', intersect: false },
                                        plugins: {
                                            legend: { labels: { color: '#ccc', font: { size: 11 } } },
                                            title: { display: true, text: name + ' 포트폴리오 성과 vs 벤치마크 (기준: 100)', color: '#ddd', font: { size: 13 } }
                                        },
                                        scales: {
                                            x: { ticks: { color: '#888', maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                                            y: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.05)' } }
                                        }
                                    }
                                });
                            } else {
                                document.getElementById('modal-chart-container').innerHTML = `<p style="color:#888; text-align:center; padding:40px;">차트 데이터가 없습니다. (거래 없음)</p>`;
                                document.getElementById('modal-chart-container').style.display = 'block';
                            }
                        } else {
                            document.getElementById('modal-stats').innerHTML = `<p style="color:#f44336;">오류: ${res.message}</p>`;
                        }
                    } catch(e) {
                        document.getElementById('modal-loading').style.display = 'none';
                        document.getElementById('modal-stats').innerHTML = `<p style="color:#f44336;">오류: ${e.message}</p>`;
                    }
                }

                function closeScanModal() {
                    document.getElementById('scan-modal').style.display = 'none';
                    if (scanModalChart) { scanModalChart.destroy(); scanModalChart = null; }
                }

                // ESC 키로 모달 닫기
                document.addEventListener('keydown', e => { if (e.key === 'Escape') closeScanModal(); });

                function updateEquityChart(labels, values) {
                    const canvas = document.getElementById('equity-chart');
                    if (!canvas) return;
                    const ctx = canvas.getContext('2d');
                    if (equityChart) {
                        equityChart.data.labels = labels;
                        equityChart.data.datasets[0].data = values;
                        equityChart.update();
                    } else {
                        equityChart = new Chart(ctx, {
                            type: 'line',
                            data: {
                                labels: labels,
                                datasets: [{
                                    label: '포트폴리오 가치 (USD)',
                                    data: values,
                                    borderColor: '#667eea',
                                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                                    borderWidth: 2,
                                    pointRadius: 0,
                                    fill: true,
                                    tension: 0.1
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                interaction: { mode: 'index', intersect: false },
                                plugins: { legend: { display: false } },
                                scales: {
                                    x: { ticks: { maxTicksLimit: 6, color: '#aaa' }, grid: { display: false } },
                                    y: { ticks: { color: '#aaa' }, grid: { color: '#eee' } }
                                }
                            }
                        });
                    }
                }

                function updateAllocationChart(cash, positions) {
                    const canvas = document.getElementById('allocation-pie-chart');
                    if (!canvas) return;
                    const ctx = canvas.getContext('2d');
                    
                    const labels = ['Cash'];
                    const data = [cash];
                    const bgColors = ['#e0e0e0'];
                    
                    const palette = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff', '#ff9f40'];
                    let colorIdx = 0;
                    
                    for (const [symbol, p] of Object.entries(positions)) {
                        labels.push(symbol);
                        data.push(p.quantity * p.average_price);
                        bgColors.push(palette[colorIdx % palette.length]);
                        colorIdx++;
                    }
                    
                    if (pieChart) {
                        pieChart.data.labels = labels;
                        pieChart.data.datasets[0].data = data;
                        pieChart.data.datasets[0].backgroundColor = bgColors;
                        pieChart.update();
                    } else {
                        pieChart = new Chart(ctx, {
                            type: 'doughnut',
                            data: {
                                labels: labels,
                                datasets: [{
                                    data: data,
                                    backgroundColor: bgColors,
                                    borderWidth: 0
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: { position: 'right', labels: { boxWidth: 12, font: { size: 10 } } }
                                },
                                cutout: '60%'
                            }
                        });
                    }
                }
            </script>
        </body>
        </html>
        '''

    def run(self, debug: bool = False):
        """서버 실행"""
        if not self._enabled:
            self.logger.error("Web dashboard cannot start because FastAPI is not installed.")
            return
        
        self.logger.info(f"Starting FastAPI web dashboard on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="debug" if debug else "info")
