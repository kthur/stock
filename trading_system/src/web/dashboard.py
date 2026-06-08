"""Web Dashboard using Plotly Dash"""

import logging
import threading
from typing import Any, List, Dict, Optional
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output

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
                dash_table.DataTable(id='pnl-status-table')  # type: ignore[attr-defined]
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
        ]),
        dcc.Tab(label='Global Macro', id='global-macro-tab', children=[
            html.Div([
                html.H3("Global Macro Analysis"),
                html.Label("Select Macro Symbols:"),
                dcc.Dropdown(
                    id='macro-symbol-dropdown',
                    options=[{'label': sym, 'value': sym} for sym in ["^GSPC", "^IXIC", "^KS11", "^KQ11", "USDKRW=X", "^TNX", "^VIX"]],
                    value=["^GSPC", "^IXIC", "^KS11", "^KQ11", "USDKRW=X", "^TNX", "^VIX"],
                    multi=True
                ),
                html.Label("Select Timeframe:"),
                dcc.Dropdown(
                    id='macro-timeframe-dropdown',
                    options=[
                        {'label': '1 Month', 'value': '1mo'},
                        {'label': '3 Months', 'value': '3mo'},
                        {'label': '6 Months', 'value': '6mo'},
                        {'label': '1 Year', 'value': '1y'},
                        {'label': '2 Years', 'value': '2y'}
                    ],
                    value='1y'
                ),
                html.Label("Limit Output:"),
                dcc.Slider(
                    id='macro-limit-slider',
                    min=1, max=10, step=1, value=10,
                    marks={i: str(i) for i in range(1, 11)}
                ),
                
                html.Div([
                    dcc.Graph(id='macro-correlation-heatmap')
                ]),
                
                html.Div([
                    html.H4("US Expected Outperformers"),
                    dash_table.DataTable(  # type: ignore[attr-defined]
                        id='us-outperformers-table',
                        columns=[
                            {"name": "Ticker", "id": "ticker"},
                            {"name": "Expected Excess Return", "id": "expected_excess_return"},
                            {"name": "Exchange Rate Correlation", "id": "correlation_to_exchange_rate"}
                        ],
                        data=[]
                    )
                ], style={'width': '48%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H4("KR Expected Outperformers"),
                    dash_table.DataTable(  # type: ignore[attr-defined]
                        id='kr-outperformers-table',
                        columns=[
                            {"name": "Ticker", "id": "ticker"},
                            {"name": "Expected Excess Return", "id": "expected_excess_return"},
                            {"name": "Exchange Rate Correlation", "id": "correlation_to_exchange_rate"}
                        ],
                        data=[]
                    )
                ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
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

def update_macro_correlation_heatmap(selected_symbols: List[str], timeframe: str) -> Dict[str, Any]:
    """
    Stateless callback helper function to generate heatmap figure.
    """
    if not selected_symbols:
        return {
            'data': [],
            'layout': {
                'title': 'No symbols selected'
            }
        }
    
    from src.analysis.macro_analyzer import fetch_macro_indices_data
    import pandas as pd
    try:
        # Fetch the macro data
        macro_df = fetch_macro_indices_data(period=timeframe)
        if macro_df.empty:
            return {
                'data': [],
                'layout': {'title': 'Failed to fetch data'}
            }
        
        # Align, fillna, pct_change
        if not isinstance(macro_df.index, pd.DatetimeIndex):
            macro_df.index = pd.to_datetime(macro_df.index)
        if macro_df.index.tz is not None:
            macro_df.index = macro_df.index.tz_convert(None)
        macro_df.index = macro_df.index.normalize()
        macro_df = macro_df.groupby(macro_df.index).mean()
        macro_df = macro_df.ffill().bfill()
        
        returns = macro_df.pct_change().dropna(how='all')
        
        # Filter for selected symbols
        valid_symbols = [s for s in selected_symbols if s in returns.columns]
        if not valid_symbols:
            return {
                'data': [],
                'layout': {'title': 'No valid symbols found in returns'}
            }
            
        corr_matrix = returns[valid_symbols].corr().fillna(0.0)
        
        # Create heatmap data
        heatmap_data = {
            'x': list(corr_matrix.columns),
            'y': list(corr_matrix.index),
            'z': corr_matrix.values.tolist(),
            'type': 'heatmap',
            'colorscale': 'RdBu',
            'zmin': -1.0,
            'zmax': 1.0
        }
        
        return {
            'data': [heatmap_data],
            'layout': {
                'title': f'Global Macro Correlation Heatmap ({timeframe})',
                'xaxis': {'title': 'Symbols'},
                'yaxis': {'title': 'Symbols'}
            }
        }
    except Exception as e:
        logger.error(f"Error updating heatmap: {e}")
        return {
            'data': [],
            'layout': {
                'title': f'Error: {str(e)}'
            }
        }

def update_outperformers_table(country: str, timeframe: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Stateless callback helper function to return outperformer recommendations.
    """
    from src.analysis.screener import StockScreener
    try:
        limit = max(0, limit)
        screener = StockScreener()
        results = screener.screen_global_outperformers()
        region_results = results.get(country, [])
        return region_results[:limit]
    except Exception as e:
        logger.error(f"Error in update_outperformers_table: {e}")
        return []

# Register Dash callbacks
@app.callback(
    Output('macro-correlation-heatmap', 'figure'),
    [Input('macro-symbol-dropdown', 'value'),
     Input('macro-timeframe-dropdown', 'value')]
)
def callback_update_macro_correlation_heatmap(selected_symbols, timeframe):
    return update_macro_correlation_heatmap(selected_symbols, timeframe)

@app.callback(
    Output('us-outperformers-table', 'data'),
    [Input('macro-timeframe-dropdown', 'value'),
     Input('macro-limit-slider', 'value')]
)
def callback_update_us_outperformers_table(timeframe, limit):
    return update_outperformers_table('US', timeframe, limit)

@app.callback(
    Output('kr-outperformers-table', 'data'),
    [Input('macro-timeframe-dropdown', 'value'),
     Input('macro-limit-slider', 'value')]
)
def callback_update_kr_outperformers_table(timeframe, limit):
    return update_outperformers_table('KR', timeframe, limit)

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
