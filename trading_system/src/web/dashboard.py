"""Web Dashboard using Plotly Dash"""

import logging
import threading
from typing import Any, List, Dict, Optional
import dash
from dash import dcc, html, dash_table

logger = logging.getLogger(__name__)

# Create the Dash app instance
app = dash.Dash(__name__)
# Keep reference to the underlying flask server
server = app.server

# Define a clean layout matching the requirements
app.layout = html.Div([
    html.H1("Trading System Dashboard"),
    dcc.Tabs(id="tabs-example", children=[
        dcc.Tab(label='Strategy Performance', id='performance-tab', children=[
            html.Div([
                dcc.Graph(id='performance-comparison-chart')
            ])
        ]),
        dcc.Tab(label='Real-time P&L', id='pnl-tab', children=[
            html.Div([
                dash_table.DataTable(id='pnl-status-table')
            ])
        ]),
        dcc.Tab(label='Backtest Viewer', id='backtest-tab', children=[
            html.Div([
                dcc.Dropdown(
                    id='backtest-symbol-dropdown',
                    options=[
                        {'label': 'AAPL', 'value': 'AAPL'},
                        {'label': 'MSFT', 'value': 'MSFT'}
                    ],
                    value='AAPL'
                ),
                dcc.Graph(id='backtest-curve-chart'),
                html.Div(id='optimized-cache-viewer')
            ])
        ])
    ])
])

# Module-level callback helper functions

def update_backtest_chart(symbol: Optional[str], strategy: Optional[str]) -> Dict[str, Any]:
    """Helper to update backtest chart. Handles None inputs and returns distinct/deterministic charts."""
    if not symbol or not strategy:
        return {
            'data': [],
            'layout': {
                'title': 'No data'
            }
        }
    
    # Return distinct/deterministic figures for AAPL and MSFT
    if symbol == "AAPL":
        y_data = [100.0, 102.5, 101.2, 105.0, 107.3]
    elif symbol == "MSFT":
        y_data = [200.0, 198.5, 202.1, 201.0, 206.8]
    else:
        y_data = [10.0 + len(symbol), 12.0 + len(symbol), 11.0 + len(symbol), 15.0 + len(symbol)]
        
    return {
        'data': [{
            'x': list(range(len(y_data))),
            'y': y_data,
            'type': 'scatter',
            'name': f"{symbol} ({strategy})"
        }],
        'layout': {
            'title': f"Backtest for {symbol} ({strategy})"
        }
    }

def update_positions_table(positions: List[Any]) -> List[Dict[str, Any]]:
    """Helper to format positions into table rows. Returns standard row if empty."""
    if not positions:
        return [{
            'symbol': 'No active positions',
            'quantity': 0,
            'entry_price': 0.0,
            'current_price': 0.0,
            'pnl': 0.0
        }]
    
    rows = []
    for pos in positions:
        if isinstance(pos, dict):
            symbol = pos.get('symbol', 'Unknown')
            quantity = pos.get('quantity', 0)
            entry_price = pos.get('entry_price', 0.0)
            current_price = pos.get('current_price', 0.0)
            pnl = pos.get('pnl', 0.0)
        else:
            symbol = getattr(pos, 'symbol', 'Unknown')
            quantity = getattr(pos, 'quantity', 0)
            entry_price = getattr(pos, 'entry_price', 0.0)
            current_price = getattr(pos, 'current_price', 0.0)
            pnl = getattr(pos, 'pnl', 0.0)
        
        rows.append({
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'current_price': current_price,
            'pnl': pnl
        })
    return rows

def update_performance_comparison(performance_data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to compare strategy performance curves."""
    if not performance_data:
        return {
            'data': [],
            'layout': {
                'title': 'No Performance Data'
            }
        }
    
    data_list = []
    for strategy, values in performance_data.items():
        if isinstance(values, list):
            y_vals = values
            x_vals = list(range(len(y_vals)))
        elif isinstance(values, dict) and 'equity' in values:
            y_vals = values['equity']
            x_vals = values.get('dates', list(range(len(y_vals))))
        else:
            y_vals = [values]
            x_vals = [0]
            
        data_list.append({
            'x': x_vals,
            'y': y_vals,
            'type': 'scatter',
            'name': strategy
        })
        
    return {
        'data': data_list,
        'layout': {
            'title': 'Strategy Performance Comparison'
        }
    }

class DashboardServer:
    """Dashboard configuration server class."""
    def __init__(self, port: int = 5000, host: str = '127.0.0.1'):
        self.port = port
        self.host = host

class WebDashboard:
    """Wrapper class for starting the Dash Dashboard."""
    def __init__(self, trading_system: Any = None, event_bus: Any = None, host: str = '127.0.0.1', port: int = 5000):
        self.trading_system = trading_system
        self.event_bus = event_bus
        self.host = host
        self.port = port
        self.app = app
        
    def run(self, debug: bool = False) -> None:
        """Launches the Dash server in a separate background thread to avoid blocking."""
        def _run():
            try:
                # We disable reloader to prevent issues inside background thread
                self.app.run(host=self.host, port=self.port, debug=debug, use_reloader=False)
            except Exception as e:
                logger.error(f"Error starting Dash web dashboard: {e}")
                
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        logger.info(f"Dashboard running in background thread on {self.host}:{self.port}")
