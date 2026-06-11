import os
import sys
import logging
import random
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import FinanceDataReader as fdr

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.ai.prediction_model import OnDevicePredictionModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_data_fdr(symbol: str, market: str, start_date: str) -> pd.DataFrame:
    """Fetch data using FinanceDataReader"""
    try:
        if market == 'SP500':
            # FDR uses the ticker as is
            df = fdr.DataReader(symbol, start=start_date)
        else:
            # KRX code
            df = fdr.DataReader(symbol, start=start_date)
        return df
    except Exception as e:
        logger.debug(f"Failed to fetch {symbol}: {e}")
        return None

def main():
    logger.info("Initializing Storage and Model...")
    storage = MarketIndicatorStorage()
    model = OnDevicePredictionModel()

    # 1. Ensure universe is loaded
    universe = storage.get_universe()
    if universe.empty:
        logger.info("Universe empty. Fetching...")
        storage.update_stock_universe()
        universe = storage.get_universe()

    logger.info(f"Loaded {len(universe)} symbols from universe.")

    # Let's sample for training to save time: 50 SP500, 50 KRX
    sp500_symbols = universe[universe['market'] == 'SP500']['symbol'].tolist()
    krx_symbols = universe[universe['market'] != 'SP500']['symbol'].tolist()

    random.seed(42)
    n_sp = min(50, len(sp500_symbols))
    n_kr = min(50, len(krx_symbols))
    train_symbols = random.sample(sp500_symbols, n_sp) + random.sample(krx_symbols, n_kr)

    start_date_train = '2023-01-01'
    start_date_infer = '2025-01-01' # 100 days for inference features

    logger.info(f"Fetching training data for {len(train_symbols)} symbols...")
    train_data_dict = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_sym = {}
        for sym in train_symbols:
            market = 'SP500' if sym in sp500_symbols else 'KRX'
            future_to_sym[executor.submit(fetch_data_fdr, sym, market, start_date_train)] = sym

        for future in as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    train_data_dict[sym] = df
            except Exception:
                pass

    logger.info("Preparing training data...")
    df_train = model.prepare_training_data(train_data_dict)

    logger.info("Training XGBoost model (On-device)...")
    model.train(df_train)

    # For inference, let's predict top 200 random to save execution time in demo,
    # OR we can do all if we have time. Doing 3300 takes ~2 mins with ThreadPool.
    # To strictly follow the "All KRX stocks" requirement, we fetch them all!
    all_symbols = sp500_symbols + krx_symbols
    logger.info(f"Fetching recent data for ALL {len(all_symbols)} symbols for inference...")

    infer_data_dict = {}
    # Fetch in chunks to not explode memory/api
    count = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_sym = {}
        for sym in all_symbols:
            market = 'SP500' if sym in sp500_symbols else 'KRX'
            future_to_sym[executor.submit(fetch_data_fdr, sym, market, start_date_infer)] = sym

        for future in as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    infer_data_dict[sym] = df
            except Exception:
                pass
            count += 1
            if count % 500 == 0:
                logger.info(f"Fetched {count}/{len(all_symbols)}")

    logger.info("Running predictions...")
    res_df = model.process_and_predict_all(infer_data_dict)

    if res_df.empty:
        logger.error("No predictions could be made.")
        return

    # Output the top 5 for each horizon
    horizons = [1, 5, 10, 20, 30, 60]

    print("\n" + "="*50)
    print("AI Prediction Results (On-Device XGBoost)")
    print("="*50)

    for h in horizons:
        if h not in res_df.columns:
            continue
        print(f"\n[기간: {h}일] 가장 크게 상승할 것으로 예상되는 종목")
        top5 = res_df.sort_values(by=h, ascending=False).head(5)
        for rank, (_, row) in enumerate(top5.iterrows(), 1):
            sym = row['symbol']
            expected_ret = row[h] * 100
            # find name
            name_row = universe[universe['symbol'] == sym]
            name = name_row['name'].values[0] if not name_row.empty else "Unknown"
            market = name_row['market'].values[0] if not name_row.empty else "Unknown"

            print(f" {rank}. [{market}] {sym} ({name}): +{expected_ret:.2f}% 예상")

if __name__ == "__main__":
    main()
