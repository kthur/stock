import logging
import sqlite3
from typing import Optional
import pandas as pd
import FinanceDataReader as fdr

logger = logging.getLogger(__name__)

class MarketIndicatorStorage:
    def __init__(self, db_path: str = "market_indicators.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Create table for global market indicators (indices, fx, macro)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS global_indicators (
                    date TEXT,
                    symbol TEXT,
                    name TEXT,
                    price REAL,
                    change_pct REAL,
                    PRIMARY KEY (date, symbol)
                )
            ''')
            # Create table for stock universe
            conn.execute('''
                CREATE TABLE IF NOT EXISTS stock_universe (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT
                )
            ''')
            # Create table for AI Predictions
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ai_predictions (
                    date TEXT,
                    symbol TEXT,
                    horizon INTEGER,
                    expected_return REAL,
                    PRIMARY KEY (date, symbol, horizon)
                )
            ''')
            conn.commit()

    def update_stock_universe(self):
        """Fetch and update S&P 500 and KRX all stocks"""
        logger.info("Fetching S&P 500 universe...")
        sp500 = fdr.StockListing('S&P500')

        logger.info("Fetching KRX universe...")
        krx = fdr.StockListing('KRX')

        with sqlite3.connect(self.db_path) as conn:
            # S&P 500
            for _, row in sp500.iterrows():
                conn.execute(
                    "INSERT OR REPLACE INTO stock_universe (symbol, name, market) VALUES (?, ?, ?)",
                    (row['Symbol'], row['Name'], 'SP500')
                )
            # KRX
            for _, row in krx.iterrows():
                # KRX symbols are 6 digits; append .KS/.KQ later if needed for yfinance
                conn.execute(
                    "INSERT OR REPLACE INTO stock_universe (symbol, name, market) VALUES (?, ?, ?)",
                    (row['Code'], row['Name'], row.get('Market', 'KRX'))
                )
            conn.commit()
        logger.info("Stock universe updated successfully.")

    def save_indicators(self, data: dict, date_str: str):
        """
        Save the indicators fetched from GlobalMarketClient.
        `data` is expected to have 'indices', 'fx_rates', 'macro_commodities'
        """
        sql = "INSERT OR REPLACE INTO global_indicators (date,symbol,name,price,change_pct) VALUES (?,?,?,?,?)"
        with sqlite3.connect(self.db_path) as conn:
            for sym, info in data.get('indices', {}).items():
                if info.get('price') is not None:
                    conn.execute(sql, (date_str, info['symbol'], info['name'], info['price'], info['change_pct']))
            for sym, info in data.get('fx_rates', {}).items():
                if info.get('rate') is not None:
                    conn.execute(sql, (date_str, info['pair'], info['name'], info['rate'], info['change_pct']))
            for sym, info in data.get('macro_commodities', {}).items():
                if info.get('price') is not None:
                    conn.execute(sql, (date_str, info['symbol'], info['name'], info['price'], info['change_pct']))
            conn.commit()

    def get_universe(self, market: Optional[str] = None) -> pd.DataFrame:
        query = "SELECT * FROM stock_universe"
        params: tuple = ()
        if market:
            query += " WHERE market = ?"
            params = (market,)
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn, params=params)

    def save_predictions(self, df_preds: pd.DataFrame, date_str: str):
        """Save AI predictions to database."""
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df_preds.iterrows():
                sym = row['symbol']
                for h in [1, 5, 10, 20, 30, 60]:
                    if h in row:
                        sql = "INSERT OR REPLACE INTO ai_predictions (date,symbol,horizon,expected_return) VALUES (?,?,?,?)"  # noqa: E501
                        conn.execute(sql, (date_str, sym, h, float(row[h])))
            conn.commit()

    def get_predictions(self, date_str: Optional[str] = None) -> pd.DataFrame:
        """Get AI predictions. If date_str is None, returns the latest predictions."""
        with sqlite3.connect(self.db_path) as conn:
            if date_str:
                query = "SELECT * FROM ai_predictions WHERE date = ?"
                return pd.read_sql(query, conn, params=(date_str,))
            else:
                query = "SELECT * FROM ai_predictions WHERE date = (SELECT MAX(date) FROM ai_predictions)"
            return pd.read_sql(query, conn)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    storage = MarketIndicatorStorage()
    storage.update_stock_universe()
    print("Universe size:", len(storage.get_universe()))
