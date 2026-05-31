"""Web Dashboard - Flask 기반 웹 대시보드"""

from flask import Flask, render_template_string, jsonify
from datetime import datetime
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)


class WebDashboard:
    """웹 대시보드"""
    
    def __init__(self, trading_system, host: str = '127.0.0.1', port: int = 5000):
        """
        초기화
        
        Args:
            trading_system: 트레이딩 시스템 인스턴스
            host: 호스트
            port: 포트
        """
        self.trading_system = trading_system
        self.host = host
        self.port = port
        self.logger = logger
        
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """라우트 설정"""
        
        @self.app.route('/')
        def index():
            """메인 대시보드"""
            return render_template_string(self.get_dashboard_html())
        
        @self.app.route('/api/portfolio')
        def api_portfolio():
            """포트폴리오 정보"""
            status = self.trading_system.get_trading_status()
            return jsonify({
                'status': 'success',
                'data': {
                    'cash': status['cash'],
                    'positions': status['positions'],
                    'timestamp': status['timestamp']
                }
            })
        
        @self.app.route('/api/performance')
        def api_performance():
            """성과 정보"""
            perf = {
                'win_rate': self.trading_system.optimization_engine.get_win_rate(),
                'avg_slippage': self.trading_system.optimization_engine.get_avg_slippage(),
                'total_trades': self.trading_system.optimization_engine.total_trades,
                'timestamp': datetime.now().isoformat()
            }
            return jsonify({
                'status': 'success',
                'data': perf
            })
        
        @self.app.route('/api/orders')
        def api_orders():
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
            
            return jsonify({
                'status': 'success',
                'data': orders,
                'count': len(orders)
            })
        
        @self.app.route('/api/trades')
        def api_trades():
            """거래 이력"""
            trades = self.trading_system.trade_logger.get_trade_history(limit=20)
            return jsonify({
                'status': 'success',
                'data': trades,
                'count': len(trades)
            })
        
        @self.app.route('/api/risk')
        def api_risk():
            """위험 정보"""
            if hasattr(self.trading_system, 'risk_manager'):
                risk = self.trading_system.risk_manager
                metrics = risk.generate_risk_report(
                    self.trading_system.portfolio.positions,
                    self.trading_system.market_data_cache
                )
                return jsonify({
                    'status': 'success',
                    'data': {
                        'current_value': metrics.current_value,
                        'drawdown': f"{metrics.current_drawdown:.2%}",
                        'max_loss_limit': metrics.max_loss_limit,
                        'risk_level': metrics.risk_level.value,
                        'volatility': f"{metrics.portfolio_volatility:.2%}"
                    }
                })
            return jsonify({'status': 'error', 'message': 'Risk manager not available'})
    
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
                        // 포트폴리오 정보
                        const portfolio = await fetch('/api/portfolio').then(r => r.json());
                        if (portfolio.status === 'success') {
                            document.getElementById('cash').textContent = 
                                '$' + portfolio.data.cash.toLocaleString('en-US', {maximumFractionDigits: 0});
                            document.getElementById('positions').textContent = 
                                Object.keys(portfolio.data.positions).length;
                        }
                        
                        // 성과 정보
                        const perf = await fetch('/api/performance').then(r => r.json());
                        if (perf.status === 'success') {
                            document.getElementById('win-rate').textContent = 
                                (perf.data.win_rate * 100).toFixed(1);
                            document.getElementById('avg-slippage').textContent = 
                                (perf.data.avg_slippage * 100).toFixed(4);
                            document.getElementById('total-trades').textContent = 
                                perf.data.total_trades;
                        }
                        
                        // 주문 정보
                        const orders = await fetch('/api/orders').then(r => r.json());
                        if (orders.status === 'success') {
                            document.getElementById('open-orders').textContent = orders.count;
                            updateOrdersTable(orders.data);
                        }
                        
                        // 거래 이력
                        const trades = await fetch('/api/trades').then(r => r.json());
                        if (trades.status === 'success') {
                            updateTradesTable(trades.data);
                        }
                        
                        // 위험 정보
                        const risk = await fetch('/api/risk').then(r => r.json());
                        if (risk.status === 'success') {
                            document.getElementById('risk-grid').style.display = 'grid';
                            document.getElementById('drawdown').textContent = risk.data.drawdown;
                            document.getElementById('risk-level').textContent = risk.data.risk_level;
                        }
                        
                        // 시간 업데이트
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
                
                // 초기 로드 및 주기적 업데이트
                updateData();
                setInterval(updateData, 5000);
            </script>
        </body>
        </html>
        '''
    
    def run(self, debug: bool = False):
        """서버 실행"""
        self.logger.info(f"Starting web dashboard on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)
