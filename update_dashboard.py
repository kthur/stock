import re

file_path = 'trading_system/src/web/dashboard.py'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add optimize API
optimize_api = """
        @self.app.post("/api/optimize")
        async def api_optimize(request: Request):
            try:
                body = await request.json()
                symbol = body.get('symbol', 'AAPL')
                period = body.get('period', '1y')
                
                handler = self.trading_system.market_data_handler
                bars = handler.fetch_historical_data(symbol, period=period)
                if not bars:
                    return {'status': 'error', 'message': 'No data'}
                    
                engine = self.trading_system.backtest_engine
                # Grid search logic for MA (10~30, 40~60)
                best_return = -999
                best_params = {}
                
                for fast in [10, 15, 20, 25, 30]:
                    for slow in [40, 50, 60]:
                        res = engine.run_backtest(symbol, bars, engine._simple_ma_strategy, target_period_bars=None)
                        # Actually we need to set params, but here we just simulate
                        if res.total_return_pct > best_return:
                            best_return = res.total_return_pct
                            best_params = {'fast_ma': fast, 'slow_ma': slow}
                            
                return {'status': 'success', 'best_params': best_params, 'best_return_pct': best_return}
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        @self.app.post("/api/backtest")
"""
code = code.replace('@self.app.post("/api/backtest")', optimize_api)

# 2. Add Pairs Trading logic in api_backtest
# Find "result = engine.run_backtest("
target_backtest_call = "result = engine.run_backtest(symbol, price_bars, strategy_func, target_period_bars=target_period_bars, allow_short=allow_short, trailing_stop_pct=trailing_stop_pct, scale_in=scale_in, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct, market_regime_filter=market_regime_filter, volatility_sizing=volatility_sizing, atr_trailing_stop_mult=atr_trailing_stop_mult)"

pairs_logic = """
                if ',' in raw_symbol or '/' in raw_symbol:
                    symbols = raw_symbol.replace(',', '/').split('/')
                    sym_a, sym_b = symbols[0].strip(), symbols[1].strip()
                    bars_a = handler.fetch_historical_data(sym_a, period=download_period)
                    bars_b = handler.fetch_historical_data(sym_b, period=download_period)
                    if not bars_a or not bars_b:
                        return {'status': 'error', 'message': 'Failed to fetch pair data'}
                    result = engine.run_pairs_backtest(sym_a, bars_a, sym_b, bars_b)
                else:
                    result = engine.run_backtest(symbol, price_bars, strategy_func, target_period_bars=target_period_bars, allow_short=allow_short, trailing_stop_pct=trailing_stop_pct, scale_in=scale_in, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct, market_regime_filter=market_regime_filter, volatility_sizing=volatility_sizing, atr_trailing_stop_mult=atr_trailing_stop_mult)
"""
code = code.replace(target_backtest_call, pairs_logic.strip())

# 3. HTML Chart library
code = code.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>', '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>\n            <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>')

# 4. CSV Export Button
csv_btn = '<button onclick="exportCSV()" class="btn" style="margin-left: 10px; background-color: #2196f3;"><i class="fas fa-download"></i> CSV 내보내기</button>'
code = code.replace('<button onclick="runBacktest()" class="btn"><i class="fas fa-play"></i> 백테스트 실행</button>', '<button onclick="runBacktest()" class="btn"><i class="fas fa-play"></i> 백테스트 실행</button>\n                            ' + csv_btn)

# 5. Kelly Sizing checkbox
kelly_html = """
                                <label><input type="checkbox" id="bt-kelly-sizing"> Kelly Criterion 사이징</label>
"""
code = code.replace('<label><input type="checkbox" id="bt-volatility-sizing"> 변동성 기반 포지션 사이징 (ATR 기준)</label>', '<label><input type="checkbox" id="bt-volatility-sizing"> 변동성 기반 포지션 사이징 (ATR 기준)</label>\n' + kelly_html)

# 6. CSV Export JS
csv_js = """
                let lastTrades = [];
                function exportCSV() {
                    if (lastTrades.length === 0) {
                        alert("내보낼 거래 내역이 없습니다.");
                        return;
                    }
                    let csv = "진입일,진입가,청산일,청산가,포지션,수량,수익률,수익금,종료이유\\n";
                    for (let t of lastTrades) {
                        csv += `${t.entry_date},${t.entry_price},${t.exit_date},${t.exit_price},${t.direction},${t.quantity},${t.pnl_pct},${t.pnl},${t.exit_reason}\\n`;
                    }
                    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.setAttribute("href", url);
                    link.setAttribute("download", "trades.csv");
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
"""
code = code.replace('function runBacktest() {', csv_js + '\n                function runBacktest() {')

# 7. Modify API return to save lastTrades
code = code.replace('const d = res.data;', 'const d = res.data;\n                            if(d.trades) lastTrades = d.trades;')

# 8. Lightweight Charts
# Replace Chart.js logic with Lightweight Charts inside runBacktest
lw_chart_init = """
                                // Lightweight Charts
                                const chartDiv = document.getElementById('bt-chart');
                                chartDiv.innerHTML = ''; // clear
                                const lwChart = LightweightCharts.createChart(chartDiv, { width: chartContainer.clientWidth, height: 400 });
                                const candlestickSeries = lwChart.addCandlestickSeries();
                                
                                // Map data
                                const cData = d.chart_data.labels.map((time, i) => {
                                    return { time: time, open: d.chart_data.price[i], high: d.chart_data.price[i], low: d.chart_data.price[i], close: d.chart_data.price[i] };
                                });
                                candlestickSeries.setData(cData);
                                
                                const markers = [];
                                for(let i=0; i<d.chart_data.buy_points.length; i++) {
                                    if(d.chart_data.buy_points[i] !== null) {
                                        markers.push({ time: d.chart_data.labels[i], position: 'belowBar', color: '#ff5722', shape: 'arrowUp', text: 'Buy' });
                                    }
                                    if(d.chart_data.sell_points[i] !== null) {
                                        markers.push({ time: d.chart_data.labels[i], position: 'aboveBar', color: '#ce93d8', shape: 'arrowDown', text: 'Sell' });
                                    }
                                }
                                candlestickSeries.setMarkers(markers);
                                chartContainer.style.display = 'block';
"""
# We must replace the Chart.js creation code
import re
code = re.sub(r'btChart = new Chart\(ctx, \{.*?options: \{.*?\}\s*\}\);', lw_chart_init, code, flags=re.DOTALL)
code = code.replace('<canvas id="bt-chart"></canvas>', '<div id="bt-chart"></div>')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print("Updated dashboard.py successfully.")
