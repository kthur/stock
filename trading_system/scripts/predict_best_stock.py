import os
import sys
import logging
import random
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import FinanceDataReader as fdr
import yfinance as yf

_CPU_WORKERS = max(1, (os.cpu_count() or 4))

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_layer.indicator_storage import MarketIndicatorStorage
from src.ai.prediction_model import OnDevicePredictionModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# yfinance suffix mapping for Korean stock markets
_KR_MARKET_SUFFIX = {
    'KOSPI': '.KS',
    'KOSDAQ': '.KQ',
    'KONEX': '.KQ',
    'KRX': '.KS',
}


def fetch_data_fdr(symbol: str, market: str, start_date: str) -> pd.DataFrame:
    """Fetch OHLCV data using adjusted prices (수정주가).

    For US stocks (SP500): uses FinanceDataReader (Yahoo Finance, already adjusted).
    For Korean stocks: uses yfinance with split/dividend-adjusted prices.
    """
    if market == 'SP500' or market.startswith('NYSE') or market.startswith('NASDAQ'):
        try:
            df = fdr.DataReader(symbol, start=start_date)
            return df
        except Exception as e:
            logger.debug(f"Failed to fetch {symbol} via fdr: {e}")
            return None

    # Korean stock: fetch from yfinance with adjusted prices
    suffix = _KR_MARKET_SUFFIX.get(market, '.KS')
    yf_symbol = f"{symbol}{suffix}"
    try:
        df = yf.download(yf_symbol, start=start_date, progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            return df
    except Exception as e:
        logger.debug(f"Failed to fetch {yf_symbol} via yfinance: {e}")

    # Fallback to FinanceDataReader if yfinance fails
    try:
        df = fdr.DataReader(symbol, start=start_date)
        if df is not None and not df.empty:
            logger.warning(f"Falling back to unadjusted KRX data for {symbol}")
        return df
    except Exception as e:
        logger.debug(f"Failed to fetch {symbol} via fdr fallback: {e}")
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

    # Build symbol→market mapping for adjusted price fetching
    symbol_market = dict(zip(universe['symbol'], universe['market']))

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

    with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:
        future_to_sym = {}
        for sym in train_symbols:
            sym_market = symbol_market.get(sym, 'SP500' if sym in sp500_symbols else 'KRX')
            future_to_sym[executor.submit(fetch_data_fdr, sym, sym_market, start_date_train)] = sym

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
    with ThreadPoolExecutor(max_workers=_CPU_WORKERS) as executor:
        future_to_sym = {}
        for sym in all_symbols:
            sym_market = symbol_market.get(sym, 'SP500' if sym in sp500_symbols else 'KRX')
            future_to_sym[executor.submit(fetch_data_fdr, sym, sym_market, start_date_infer)] = sym

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
    horizons = model.horizons  # [1, 5, 10, 20, 30, 60, 120, 200]

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
