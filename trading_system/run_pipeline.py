import os
import sys
import logging
import socket
from datetime import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import FinanceDataReader as fdr
import warnings

_CPU_WORKERS = max(1, (os.cpu_count() or 4))

# Set default socket timeout to prevent hanging connections
socket.setdefaulttimeout(5)

# Ignore Pandas pct_change FutureWarning to keep logs clean
warnings.filterwarnings('ignore', category=FutureWarning)

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.config import TradingConfig
from src.data_layer.global_market import GlobalMarketClient
from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.ai.prediction_model import OnDevicePredictionModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_data_fdr(symbol: str, market: str, start_date: str) -> pd.DataFrame:
    """Fetch data using FinanceDataReader"""
    try:
        df = fdr.DataReader(symbol, start=start_date)
        return df
    except Exception as e:
        logger.debug(f"Failed to fetch {symbol}: {e}")
        return None

def format_prediction_message(res_df: pd.DataFrame, universe: pd.DataFrame) -> str:
    """Format prediction results as a Telegram-friendly message"""
    horizons = [1, 5, 10, 20, 30, 60, 120, 200]
    lines = [
        "🤖 *XGBoost 예측 결과*",
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 30,
    ]
    for h in horizons:
        if h not in res_df.columns:
            continue
        top5 = res_df.sort_values(by=h, ascending=False).head(5)
        lines.append(f"\n*{h}일 예상*")
        for rank, (_, row) in enumerate(top5.iterrows(), 1):
            sym = row['symbol']
            ret = row[h] * 100
            name_row = universe[universe['symbol'] == sym]
            name = name_row['name'].values[0] if not name_row.empty else "Unknown"
            marker = name_row['market'].values[0] if not name_row.empty else ""
            lines.append(f"  {rank}. [{marker}] {sym} ({name}): +{ret:.2f}%")
    return "\n".join(lines)


def execute_prediction_pipeline():
    logger.info("Starting consolidated market indicator and prediction pipeline...")
    
    # 1. Load configurations from TradingConfig (.env)
    cfg = TradingConfig()
    cfg.validate()
    logger.info(f"Loaded config: DB={cfg.db_path}, Train Sample Size={cfg.train_sample_size}, Broker={cfg.broker_type}, Mock Trading={cfg.mock_trading}")
    
    # 2. Fetch current global market indicators
    logger.info("Fetching global market indicators...")
    market_client = GlobalMarketClient()
    market_summary = market_client.get_summary()
    
    # 3. Store indicators
    date_str = datetime.now().strftime('%Y-%m-%d')
    storage = MarketIndicatorStorage(db_path=cfg.db_path)
    storage.save_indicators(market_summary, date_str)
    logger.info("Saved market indicators to database.")
    
    # 4. Update stock universe if needed
    universe = storage.get_universe()
    if universe.empty:
        logger.info("Universe is empty. Syncing stock universe...")
        storage.update_stock_universe()
        universe = storage.get_universe()
    logger.info(f"Loaded {len(universe)} symbols from universe.")
    
    # 5. Prepare Training Data (On-device)
    sp500_symbols = universe[universe['market'] == 'SP500']['symbol'].tolist()
    krx_symbols = universe[universe['market'] != 'SP500']['symbol'].tolist()
    
    # Sample from settings
    import random
    random.seed(42)
    sample_size = cfg.train_sample_size
    train_symbols = random.sample(sp500_symbols, min(sample_size, len(sp500_symbols))) + \
                    random.sample(krx_symbols, min(sample_size, len(krx_symbols)))
    
    start_date_train = '2023-01-01'
    start_date_infer = '2025-01-01'
    
    model = OnDevicePredictionModel()
    logger.info(f"Fetching training data for {len(train_symbols)} sampled symbols...")
    train_data_dict = {}
    
    with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:
        future_to_sym = {}
        for sym in train_symbols:
            market = 'SP500' if sym in sp500_symbols else 'KRX'
            future_to_sym[executor.submit(fetch_data_fdr, sym, market, start_date_train)] = sym
            
        for future in as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    df = model.merge_fundamentals(sym, df, storage)
                    train_data_dict[sym] = df
            except Exception:
                pass
                
    df_train = model.prepare_training_data(train_data_dict)
    
    # 6. Train XGBoost model
    logger.info("Training XGBoost Regressor (On-device)...")
    model.train(df_train)
    
    # 7. Fetch recent data for ALL symbols to run inference
    all_symbols = sp500_symbols + krx_symbols
    logger.info(f"Fetching inference data for ALL {len(all_symbols)} symbols...")
    
    infer_data_dict = {}
    count = 0
    with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:
        future_to_sym = {}
        for sym in all_symbols:
            market = 'SP500' if sym in sp500_symbols else 'KRX'
            future_to_sym[executor.submit(fetch_data_fdr, sym, market, start_date_infer)] = sym
            
        for future in as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    df = model.merge_fundamentals(sym, df, storage)
                    infer_data_dict[sym] = df
            except Exception:
                pass
            count += 1
            if count % 500 == 0:
                logger.info(f"Fetched inference data: {count}/{len(all_symbols)}")
                
    # 8. Run predictions
    logger.info("Running prediction inference...")
    res_df = model.process_and_predict_all(infer_data_dict)
    
    if res_df.empty:
        logger.error("No predictions made.")
        return None
        
    # 9. Save predictions to DB
    storage.save_predictions(res_df, date_str)
    logger.info(f"Saved predictions to database table 'ai_predictions' for {date_str}.")
    
    # Build formatted message for Telegram
    message_text = format_prediction_message(res_df, universe)
    print(message_text)
                
    return res_df, message_text

if __name__ == "__main__":
    execute_prediction_pipeline()
