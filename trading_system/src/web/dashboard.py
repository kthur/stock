"""Web Dashboard - FastAPI 기반 웹 대시보드"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import logging
import json

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

KOR_TICKERS = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS",
    "기아": "000270.KS", "POSCO홀딩스": "005490.KS", "NAVER": "035420.KS",
    "네이버": "035420.KS", "카카오": "035720.KS", "셀트리온": "068270.KS",
    "삼성바이오로직스": "207940.KS", "LG에너지솔루션": "373220.KS",
    "LG화학": "051910.KS", "삼성SDI": "006400.KS", "KB금융": "105560.KS",
    "신한지주": "055550.KS", "하나금융지주": "086790.KS", "현대모비스": "012330.KS",
    "LG전자": "066570.KS", "에코프로비엠": "247540.KQ", "에코프로": "086520.KQ",
    "HLB": "028300.KQ", "엔씨소프트": "036570.KS", "대한항공": "003490.KS",
    "SK텔레콤": "017670.KS", "KT": "030200.KS", "한국전력": "015760.KS",
    "크래프톤": "259960.KS", "SK이노베이션": "096770.KS", 
    "한화에어로스페이스": "012450.KS", "삼성물산": "028260.KS",
    "고려아연": "010130.KS"
}

KOR_TICKERS_REV = {v: k for k, v in KOR_TICKERS.items()}


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
                        'volatility': f"{metrics.portfolio_volatility:.2%}"
                    }
                }
            return {'status': 'error', 'message': 'Risk manager not available'}
            
        @self.app.post("/api/backtest")
        async def api_backtest(request: Request):
            """백테스트 실행 API"""
            
            try:
                body = await request.json()
                raw_symbol = body.get('symbol', 'AAPL').strip()
                symbol = KOR_TICKERS.get(raw_symbol, raw_symbol)
                strategy_name = body.get('strategy', 'MA')
                period = body.get('period', '10y')
                
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
                
                self.logger.info(f"Running backtest for {symbol} with strategy {strategy_name} for period {period} (download: {download_period}, target_bars: {target_period_bars})")
                
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
                result = engine.run_backtest(symbol, price_bars, strategy_func, target_period_bars=target_period_bars)
                
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
                    if entry_d in date_to_idx and price_rebased:
                        idx = date_to_idx[entry_d]
                        buy_points[idx] = price_rebased[idx]
                    if exit_d in date_to_idx and price_rebased:
                        idx = date_to_idx[exit_d]
                        sell_points[idx] = price_rebased[idx]
                
                return {
                    'status': 'success',
                    'data': {
                        'symbol': KOR_TICKERS_REV.get(result.symbol, result.symbol),
                        'total_return_pct': f"{result.total_return_pct:.2f}%",
                        'win_rate': f"{result.win_rate:.2%}",
                        'max_drawdown': f"{result.max_drawdown:.2%}",
                        'trades_count': len(result.trades),
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
            import urllib.request
            import urllib.parse
            import json
            
            if not q or len(q) < 2:
                return {'status': 'success', 'results': []}
            
            local_results = []
            for name, code in KOR_TICKERS.items():
                if q.lower() in name.lower() or q.upper() in code:
                    local_results.append({"symbol": code, "name": name})
                    
            # 영어 기반이나 다른 티커는 Yahoo 검색으로 처리 (한국어는 야후가 차단할 수 있음)
                
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(q)}&quotesCount=8&newsCount=0"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
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
            except Exception as e:
                self.logger.warning(f"Yahoo Search API failed, using local results. Error: {e}")
                return {'status': 'success', 'results': local_results}

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
            import uuid
            import asyncio
            try:
                body = await request.json()
                strategy_name = body.get('strategy', 'MA')
                period = body.get('period', '1y')
                
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
                
                # S&P500 + KOSPI 대형주 샘플 (API 한도 고려)
                UNIVERSE = [
                    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "JNJ",
                    "005930.KS", "000660.KS", "005380.KS", "000270.KS", "035420.KS", "035720.KS",
                    "051910.KS", "006400.KS", "373220.KS", "207940.KS", "068270.KS", "005490.KS",
                    "105560.KS", "055550.KS", "036570.KS", "012330.KS", "066570.KS", "015760.KS",
                    "017670.KS", "030200.KS", "012450.KS", "028260.KS", "010130.KS", "096770.KS",
                    "247540.KQ", "086520.KQ", "028300.KQ", "259960.KS", "003490.KS", "086790.KS"
                ]
                
                task_id = str(uuid.uuid4())
                self.scan_tasks[task_id] = {
                    'status': 'running',
                    'progress': 0,
                    'total': len(UNIVERSE),
                    'results': [],
                    'error': None
                }
                
                async def run_scan_task(tid: str, univ: list, strat: str, dl_per: str, target_bars: int):
                    engine = self.trading_system.backtest_engine
                    handler = self.trading_system.market_data_handler
                    
                    if hasattr(engine, 'get_strategy_func'):
                        strategy_func = engine.get_strategy_func(strat)
                    else:
                        strategy_func = engine._simple_ma_strategy
                        
                    import math
                    def sanitize_float(val, default=0.0):
                        if val is None or math.isnan(val) or math.isinf(val):
                            return default
                        return val

                    results = []
                    for i, symbol in enumerate(univ):
                        try:
                            price_bars = handler.fetch_historical_data(symbol, period=dl_per)
                            if price_bars:
                                res = engine.run_backtest(symbol, price_bars, strategy_func, target_period_bars=target_bars)
                                
                                # 한국 시장 종목은 코드가 아니라 종목명(예: 삼성전자)으로 표출되도록 변환
                                display_symbol = KOR_TICKERS_REV.get(symbol, symbol)
                                
                                # KOSPI / KOSDAQ 구분
                                if symbol.endswith('.KS'):
                                    exchange = 'KOSPI'
                                    market = 'KR'
                                elif symbol.endswith('.KQ'):
                                    exchange = 'KOSDAQ'
                                    market = 'KR'
                                else:
                                    exchange = 'NASDAQ/NYSE'
                                    market = 'US'
                                
                                results.append({
                                    'symbol': display_symbol,
                                    'ticker': symbol,          # 원본 야후 티커 (차트 조회용)
                                    'return_pct': sanitize_float(res.total_return_pct / 100.0),
                                    'win_rate': sanitize_float(res.win_rate),
                                    'sharpe': sanitize_float(getattr(res, 'sharpe_ratio', 0.0)),
                                    'trades': len(res.trades),
                                    'mdd': sanitize_float(getattr(res, 'max_drawdown', 0.0)),
                                    'market': market,
                                    'exchange': exchange,
                                })
                        except Exception as e:
                            self.logger.warning(f"Scan failed for {symbol}: {e}")
                        
                        self.scan_tasks[tid]['progress'] = i + 1
                        await asyncio.sleep(0.1)
                        
                    # 최종 정리 (수익률 내림차순 정렬)
                    results.sort(key=lambda x: x['return_pct'], reverse=True)
                    self.scan_tasks[tid]['results'] = results
                    self.scan_tasks[tid]['status'] = 'completed'

                # 비동기 백그라운드 태스크로 실행
                asyncio.create_task(run_scan_task(task_id, UNIVERSE, strategy_name, download_period, target_period_bars))
                
                return {'status': 'success', 'task_id': task_id}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        @self.app.get("/api/scanner/status/{task_id}")
        async def api_scanner_status(task_id: str):
            task = self.scan_tasks.get(task_id)
            if not task:
                return {'status': 'error', 'message': 'Task not found'}
            return {'status': 'success', 'data': task}
                    
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
                <header>
                    <h1>📊 주식 트레이딩 시스템</h1>
                    <div class="timestamp">최근 업데이트: <span id="update-time">-</span></div>
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
                                <option value="MACD" title="MACD 오실레이터가 0선을 상향 돌파 시 매수 (추세 전환 포착)">MACD</option>
                                <option value="RSI" title="RSI가 30 이하로 침체 시 매수 (과매도 반등 포착)">RSI</option>
                                <option value="TREND" title="추세 추종(Trend Following): 가격이 200일선 위에 있고 단기 이평(20일)이 중기 이평(50일) 위에 있을 때 매수">추세 추종(Trend Following)</option>
                                <option value="BUFFETT" title="워렌 버핏(가치/역발상): 200일선 아래 크게 하락(할인)하고 단기 과매도 시 매수">워렌 버핏(Value Proxy)</option>
                                <option value="LYNCH" title="피터 린치(성장/모멘텀): 50일 신고가 및 평균 거래량 크게 상회 시 강한 모멘텀 매수">피터 린치(Growth Proxy)</option>
                                <option value="DALIO" title="레이 달리오(안정/올웨더): 200일선 위 상승추세에서 주가 변동성(ATR 대용)이 2% 미만으로 극히 안정적일 때 매수">레이 달리오(Safe Proxy)</option>
                            </select>
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
                        <p style="font-size: 13px; color: #888; margin-bottom: 18px;">유니버스 내 40개 주요 종목(한국/미국)을 대상으로 백그라운드 스캔을 수행합니다. 종목을 클릭하면 수익률 차트를 확인할 수 있습니다.</p>
                        
                        <div style="display: flex; gap: 12px; align-items: flex-end; margin-bottom: 18px; flex-wrap: wrap;">
                            <div>
                                <label style="font-size: 12px; color: #888; display: block; margin-bottom: 5px;">전략 (마우스를 올려 설명 확인)</label>
                                <select id="scan-strategy" class="form-control" style="margin-bottom: 0; width: 180px;">
                                    <option value="MA" title="단순 이동평균선 돌파: 단기 이평선이 장기 이평선을 상향 돌파 시 매수">이동평균(MA)</option>
                                    <option value="MACD" title="MACD 오실레이터가 0선을 상향 돌파 시 매수 (추세 전환 포착)">MACD</option>
                                    <option value="RSI" title="RSI가 30 이하로 침체 시 매수 (과매도 반등 포착)">RSI</option>
                                    <option value="TREND" title="추세 추종(Trend Following): 가격이 200일선 위에 있고 단기 이평(20일)이 중기 이평(50일) 위에 있을 때 매수">추세 추종(Trend)</option>
                                    <option value="BUFFETT" title="워렌 버핏(가치/역발상): 200일선 아래 크게 하락(할인)하고 단기 과매도 시 매수">워렌 버핏(Value)</option>
                                    <option value="LYNCH" title="피터 린치(성장/모멘텀): 50일 신고가 및 평균 거래량 크게 상회 시 강한 모멘텀 매수">피터 린치(Growth)</option>
                                    <option value="DALIO" title="레이 달리오(안정/올웨더): 200일선 위 상승추세에서 주가 변동성(ATR 대용)이 2% 미만으로 극히 안정적일 때 매수">레이 달리오(Safe)</option>
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
                // 데이터 갱신
                async function updateData() {
                    try {
                        const portfolio = await fetch('/api/portfolio').then(r => r.json());
                        if (portfolio.status === 'success') {
                            document.getElementById('cash').textContent = 
                                '$' + portfolio.data.cash.toLocaleString('en-US', {maximumFractionDigits: 0});
                            document.getElementById('positions').textContent = 
                                Object.keys(portfolio.data.positions).length;
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
                    html += '<tr><th>주문 ID</th><th>종목</th><th>구분</th><th>수량</th><th>가격</th><th>상태</th></tr>';
                    
                    if (orders.length === 0) {
                        html += '<tr><td colspan="6" style="text-align: center; color: #999;">미체결 주문 없음</td></tr>';
                    } else {
                        orders.forEach(o => {
                            html += '<tr>';
                            html += '<td>' + o.order_id.substring(0, 12) + '</td>';
                            html += '<td>' + o.symbol + '</td>';
                            html += '<td>' + o.type + '</td>';
                            html += '<td>' + o.quantity + '</td>';
                            html += '<td>$' + o.price.toFixed(2) + '</td>';
                            html += '<td><span class="status-badge status-' + o.status.toLowerCase() + '">' + o.status + '</span></td>';
                            html += '</tr>';
                        });
                    }
                    
                    html += '</table>';
                    document.getElementById('orders-table').innerHTML = html;
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
                            body: JSON.stringify({ symbol: symbol, strategy: strategy, period: period })
                        });
                        
                        const res = await response.json();
                        
                        if (res.status === 'success') {
                            const d = res.data;
                            resultDiv.innerHTML = `
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                                    <div><span style="color:#666; font-size:12px;">테스트 기간</span><br/><strong>${d.start_date} ~ ${d.end_date}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">예상 총 수익률</span><br/><strong class="value ${d.total_return_pct.startsWith('-') ? 'negative' : 'positive'}" style="font-size:20px;">${d.total_return_pct}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">승률</span><br/><strong>${d.win_rate}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">최대 낙폭 (MDD)</span><br/><strong class="value negative">${d.max_drawdown}</strong></div>
                                    <div><span style="color:#666; font-size:12px;">거래 횟수</span><br/><strong>${d.trades_count}회</strong></div>
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
                
                // 초기 데이터 로드
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
                    const btn = document.getElementById('btn-scan');
                    
                    btn.disabled = true;
                    btn.textContent = "스캔 진행 중...";
                    document.getElementById('scan-progress-container').style.display = 'block';
                    document.getElementById('scan-results').style.display = 'none';
                    
                    try {
                        const res = await fetch('/api/scanner/start', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ strategy: strategy, period: period })
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
                    const exchLabel = exchange ? ` · ${exchange}` : '';
                    document.getElementById('modal-subtitle').textContent = ticker + exchLabel + '  |  전략: ' + strategy + '  |  기간: ' + period;
                    document.getElementById('modal-stats').innerHTML = '';
                    document.getElementById('modal-loading').style.display = 'block';
                    document.getElementById('modal-chart-container').style.display = 'none';

                    try {
                        const resp = await fetch('/api/backtest', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({ symbol: ticker, strategy: strategy, period: period })
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
