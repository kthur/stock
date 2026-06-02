"""Web Dashboard - FastAPI 기반 웹 대시보드"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any
import logging
import json

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    FastAPI = None
    WebSocket = None

logger = logging.getLogger(__name__)

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
        
        if HAS_FASTAPI:
            self.app = FastAPI(title="Stock Trading Dashboard")
            self._setup_routes()
            
            # 이벤트 버스 구독 등록 (비동기 처리)
            if self.event_bus:
                self.event_bus.subscribe("market_data", lambda data: asyncio.create_task(self.broadcast_market_data(data)))
                self.event_bus.subscribe("account_sync", lambda data: asyncio.create_task(self.broadcast_portfolio_update()))
                self.event_bus.subscribe("order_status", lambda data: asyncio.create_task(self.broadcast_order_update(data)))
            
            self.logger.info("FastAPI Web Dashboard initialized with Native WebSockets.")
        else:
            self.app = None
            self.logger.warning("FastAPI is not installed. Web dashboard will be disabled. To enable, run: pip install fastapi uvicorn")
    
    def _setup_routes(self):
        """라우트 설정"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            """메인 대시보드"""
            return self.get_dashboard_html()
        
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
                
                footer {
                    text-align: center;
                    color: #999;
                    font-size: 12px;
                    margin-top: 40px;
                    padding: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>📊 주식 트레이딩 시스템</h1>
                    <div class="timestamp">최근 업데이트: <span id="update-time">-</span></div>
                </header>
                
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
