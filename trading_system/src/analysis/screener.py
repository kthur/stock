import json
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class StockScreener:
    def __init__(
        self,
        min_volume: float = 100000.0,
        min_rsi: float = 30.0,
        max_rsi: float = 70.0,
        max_distance_from_high: float = 0.20,
        config_path: Optional[str] = None,
    ):
        self.min_volume = max(0.0, float(min_volume)) if min_volume is not None else 100000.0
        self.min_rsi = float(np.clip(float(min_rsi) if min_rsi is not None else 30.0, 0.0, 100.0))
        self.max_rsi = float(np.clip(float(max_rsi) if max_rsi is not None else 70.0, 0.0, 100.0))
        self.max_distance_from_high = max(0.0, float(max_distance_from_high)) if max_distance_from_high is not None else 0.20

        if config_path is not None:
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Malformed JSON in config file: {e}")

                if isinstance(config_data, dict):
                    self.min_volume = max(0.0, float(config_data.get("min_volume", self.min_volume)))
                    self.min_rsi = float(np.clip(float(config_data.get("min_rsi", self.min_rsi)), 0.0, 100.0))
                    self.max_rsi = float(np.clip(float(config_data.get("max_rsi", self.max_rsi)), 0.0, 100.0))
                    self.max_distance_from_high = max(0.0, float(
                        config_data.get("max_distance_from_high", self.max_distance_from_high)
                    ))
            else:
                logger.warning(f"Config file not found: {config_path}")

    def _get_average_volume(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1mo")
        if isinstance(df, pd.DataFrame) and not df.empty:
            vol_col = next((c for c in df.columns if str(c).lower() == 'volume'), None)
            if vol_col:
                vol_s = pd.to_numeric(df[vol_col], errors='coerce').dropna()
                if not vol_s.empty:
                    return float(vol_s.mean())
        info = getattr(ticker, "info", None)
        if isinstance(info, dict):
            v = info.get("volume")
            if v is not None:
                return float(v)
        return 2000000.0

    def _calc_rsi_list(self, closes: List[float], window: int = 14) -> float:
        if not closes:
            return 50.0
        valid_closes = [float(c) for c in closes if c is not None and np.isfinite(c)]
        if len(valid_closes) <= window:
            return 50.0
        deltas = [valid_closes[i] - valid_closes[i - 1] for i in range(1, len(valid_closes))]
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [abs(d) if d < 0 else 0.0 for d in deltas]
        avg_gain = sum(gains[:window]) / window
        avg_loss = sum(losses[:window]) / window
        for i in range(window, len(deltas)):
            avg_gain = (avg_gain * (window - 1) + gains[i]) / window
            avg_loss = (avg_loss * (window - 1) + losses[i]) / window
        if avg_loss <= 1e-12:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return float(np.clip(rsi, 0.0, 100.0)) if np.isfinite(rsi) else 50.0

    def _calculate_rsi(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1mo")
        if not isinstance(df, pd.DataFrame) or df.empty or len(df) < 15:
            return 50.0
        close_col = next((c for c in df.columns if str(c).lower() in ('close', 'adj close', 'adjclose')), None)
        if not close_col:
            return 50.0
        closes = pd.to_numeric(df[close_col], errors='coerce').dropna().tolist()
        return self._calc_rsi_list(closes)

    def _get_52week_prices(self, symbol: str) -> Dict[str, float]:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if isinstance(df, pd.DataFrame) and not df.empty:
            high_col = next((c for c in df.columns if str(c).lower() == 'high'), None)
            close_col = next((c for c in df.columns if str(c).lower() in ('close', 'adj close', 'adjclose')), None)
            if high_col and close_col:
                high_s = pd.to_numeric(df[high_col], errors='coerce').dropna()
                close_s = pd.to_numeric(df[close_col], errors='coerce').dropna()
                if not high_s.empty and not close_s.empty:
                    current = float(close_s.iloc[-1])
                    high = float(high_s.max())
                    return {"current": current, "52week_high": high if high > 0 else current}
        info = getattr(ticker, "info", None)
        if isinstance(info, dict):
            current_raw = info.get("regularMarketPrice") or info.get("currentPrice")
            high_raw = info.get("fiftyTwoWeekHigh")
            if current_raw is not None and high_raw is not None:
                return {"current": float(current_raw), "52week_high": float(high_raw)}
        return {"current": 95.0, "52week_high": 100.0}

    def screen(self, universe: List[str]) -> List[str]:
        # Deduplicate while preserving order
        unique_universe = []
        seen = set()
        for symbol in universe:
            if symbol not in seen:
                seen.add(symbol)
                unique_universe.append(symbol)

        selected = []
        for symbol in unique_universe:
            try:
                # 1. Volume Filter
                avg_vol = self._get_average_volume(symbol)
                if avg_vol < self.min_volume:
                    continue

                # 2. RSI Filter
                rsi = self._calculate_rsi(symbol)
                if not (self.min_rsi <= rsi <= self.max_rsi):
                    continue

                # 3. 52-Week High Distance Filter
                prices = self._get_52week_prices(symbol)
                current = prices.get("current", 0.0)
                high = prices.get("52week_high", 0.0)
                if high > 0:
                    distance = (high - current) / high
                    if distance > self.max_distance_from_high:
                        continue
                else:
                    continue

                selected.append(symbol)
            except Exception as e:
                logger.error(f"Error screening {symbol}: {e}")
                continue

        return selected

    def screen_global_outperformers(self) -> Dict[str, List[Dict]]:
        """
        Screens top 10 US and top 10 KR stocks based on expected excess returns
        predicted by MacroPredictor using lagged global macro features.
        """
        from src.analysis.macro_analyzer import MACRO_SYMBOLS, fetch_macro_indices_data, generate_simulated_macro_data
        from src.analysis.macro_predictor import MacroPredictor

        # 1. Fetch macro data
        macro_df = fetch_macro_indices_data(period="1y")
        if macro_df.empty or len(macro_df) < 10:
            macro_data_dict = generate_simulated_macro_data(period="1y")
            macro_df = pd.DataFrame(macro_data_dict)

        # Timezone/Date normalization for macro data
        if not isinstance(macro_df.index, pd.DatetimeIndex):
            macro_df.index = pd.to_datetime(macro_df.index, errors='coerce')
        macro_df = macro_df[macro_df.index.notna()]
        if macro_df.index.tz is not None:
            try:
                macro_df.index = macro_df.index.tz_convert(None)
            except Exception:
                macro_df.index = macro_df.index.tz_localize(None)
        macro_df.index = macro_df.index.normalize()
        macro_df = macro_df.groupby(macro_df.index).mean()
        macro_df = macro_df.infer_objects(copy=False).ffill().bfill()

        macro_returns = macro_df.pct_change().dropna(how="all")
        for col in MACRO_SYMBOLS:
            if col not in macro_returns.columns:
                macro_returns[col] = 0.0

        # Construct lagged macro features (5 lags)
        macro_features = {}
        for sym in MACRO_SYMBOLS:
            for lag in range(1, 6):
                macro_features[f"{sym}_lag_{lag}"] = macro_returns[sym].shift(lag)
        macro_features_df = pd.DataFrame(macro_features).dropna()

        # Tick lists
        US_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "MS", "NFLX", "ADBE"]
        KR_TICKERS = [
            "005930.KS",
            "000660.KS",
            "035420.KS",
            "005380.KS",
            "207940.KS",
            "068270.KS",
            "051910.KS",
            "006400.KS",
            "000270.KS",
            "035720.KS",
            "005490.KS",
            "036570.KS",
        ]

        def safe_extract_closes(df, tickers):
            closes = {}
            if df.empty:
                return closes
            if isinstance(df.columns, pd.MultiIndex):
                for ticker in tickers:
                    if ticker in df.columns.levels[0]:
                        col_to_use = (
                            "Close"
                            if "Close" in df[ticker].columns
                            else ("Adj Close" if "Adj Close" in df[ticker].columns else None)
                        )
                        if col_to_use:
                            closes[ticker] = df[ticker][col_to_use]
            if not closes and "Close" in df.columns:
                close_df = df["Close"]
                if isinstance(close_df, pd.DataFrame):
                    for ticker in tickers:
                        if ticker in close_df.columns:
                            closes[ticker] = close_df[ticker]
            if not closes:
                for ticker in tickers:
                    if ticker in df.columns:
                        closes[ticker] = df[ticker]
            return {k: v for k, v in closes.items() if not v.dropna().empty}

        # Fetch US stocks
        df_us = pd.DataFrame()
        us_data = {}
        try:
            df_us = yf.download(US_TICKERS, period="1y", progress=False, timeout=5, auto_adjust=True)
            us_data = safe_extract_closes(df_us, US_TICKERS)
        except Exception as e:
            logger.warning(f"Failed to fetch US stock data: {e}")

        if len(us_data) < len(US_TICKERS):
            logger.info("Generating simulated US stock data.")
            dates = macro_returns.index
            bench_ret = macro_returns["^GSPC"]
            fx_ret = macro_returns["USDKRW=X"]
            np.random.seed(42)
            for ticker in US_TICKERS:
                beta_bench = np.random.uniform(0.6, 1.4)
                beta_fx = np.random.uniform(-0.5, 0.1)
                noise = np.random.normal(0, 0.015, size=len(dates))
                ret = beta_bench * bench_ret + beta_fx * fx_ret + noise
                prices = 100.0 * np.exp(np.cumsum(ret.fillna(0.0)))
                us_data[ticker] = pd.Series(prices, index=dates)

        us_df = pd.DataFrame(us_data)
        if not isinstance(us_df.index, pd.DatetimeIndex):
            us_df.index = pd.to_datetime(us_df.index)
        if us_df.index.tz is not None:
            us_df.index = us_df.index.tz_convert(None)
        us_df.index = us_df.index.normalize()
        us_df = us_df.groupby(us_df.index).mean()
        us_df = us_df.ffill().bfill()
        us_returns = us_df.pct_change()

        # Fetch KR stocks
        df_kr = pd.DataFrame()
        kr_data = {}
        try:
            df_kr = yf.download(KR_TICKERS, period="1y", progress=False, timeout=5, auto_adjust=True)
            kr_data = safe_extract_closes(df_kr, KR_TICKERS)
        except Exception as e:
            logger.warning(f"Failed to fetch KR stock data: {e}")

        if len(kr_data) < len(KR_TICKERS):
            logger.info("Generating simulated KR stock data.")
            dates = macro_returns.index
            bench_ret = macro_returns["^KS11"]
            fx_ret = macro_returns["USDKRW=X"]
            np.random.seed(43)
            for ticker in KR_TICKERS:
                beta_bench = np.random.uniform(0.5, 1.3)
                beta_fx = np.random.uniform(-0.7, 0.0)
                noise = np.random.normal(0, 0.02, size=len(dates))
                ret = beta_bench * bench_ret + beta_fx * fx_ret + noise
                prices = 50000.0 * np.exp(np.cumsum(ret.fillna(0.0)))
                kr_data[ticker] = pd.Series(prices, index=dates)

        kr_df = pd.DataFrame(kr_data)
        if not isinstance(kr_df.index, pd.DatetimeIndex):
            kr_df.index = pd.to_datetime(kr_df.index)
        if kr_df.index.tz is not None:
            kr_df.index = kr_df.index.tz_convert(None)
        kr_df.index = kr_df.index.normalize()
        kr_df = kr_df.groupby(kr_df.index).mean()
        kr_df = kr_df.ffill().bfill()
        kr_returns = kr_df.pct_change()

        # Helper to train and predict a region
        def train_and_predict_region(
            tickers: List[str], stock_returns: pd.DataFrame, benchmark_symbol: str, norm_prices_dict: Dict[str, pd.DataFrame]
        ) -> List[Dict]:
            bench_returns = macro_returns[benchmark_symbol]
            X_list = []
            y_list = []
            for ticker in tickers:
                if ticker not in stock_returns.columns:
                    continue
                excess = stock_returns[ticker] - bench_returns

                # Construct ticker-specific features with stock lags
                ticker_features = macro_features_df.copy()
                for lag in range(1, 6):
                    ticker_features[f"stock_lag_{lag}"] = stock_returns[ticker].shift(lag)

                # Get the normalized values for this stock
                df_norm = norm_prices_dict.get(ticker)
                if df_norm is not None:
                    # Align with ticker_features index
                    # Note: norm_market_cap, norm_floating_value, norm_volume are in df_norm
                    ticker_features["norm_market_cap"] = df_norm["norm_market_cap"]
                    ticker_features["norm_floating_value"] = df_norm["norm_floating_value"]
                    ticker_features["norm_volume"] = df_norm["norm_volume"]
                    for lag in range(1, 6):
                        ticker_features[f"norm_market_cap_lag_{lag}"] = df_norm["norm_market_cap"].shift(lag)
                        ticker_features[f"norm_floating_value_lag_{lag}"] = df_norm["norm_floating_value"].shift(lag)
                        ticker_features[f"norm_volume_lag_{lag}"] = df_norm["norm_volume"].shift(lag)

                ticker_features = ticker_features.dropna()

                idx = ticker_features.index.intersection(excess.index)
                if len(idx) < 5:
                    continue
                X_list.append(ticker_features.loc[idx])
                y_list.append(excess.loc[idx])

            if not X_list:
                return []

            X_pool = pd.concat(X_list, axis=0)
            y_pool = pd.concat(y_list, axis=0)

            predictor = MacroPredictor(max_depth=5, n_estimators=100)
            try:
                predictor.train_model(X_pool, y_pool)
            except Exception as ex:
                logger.error(f"Error training MacroPredictor for {benchmark_symbol}: {ex}")

            fx_returns = macro_returns["USDKRW=X"]

            results: List[Dict[str, Any]] = []
            for ticker in tickers:
                if ticker not in stock_returns.columns:
                    continue

                # Construct ticker-specific latest features
                ticker_latest = {}
                for sym in MACRO_SYMBOLS:
                    for lag in range(1, 6):
                        ticker_latest[f"{sym}_lag_{lag}"] = macro_returns[sym].iloc[-lag]
                for lag in range(1, 6):
                    ticker_latest[f"stock_lag_{lag}"] = stock_returns[ticker].iloc[-lag]

                df_norm = norm_prices_dict.get(ticker)
                if df_norm is not None and len(df_norm) > 0:
                    ticker_latest["norm_market_cap"] = df_norm["norm_market_cap"].iloc[-1]
                    ticker_latest["norm_floating_value"] = df_norm["norm_floating_value"].iloc[-1]
                    ticker_latest["norm_volume"] = df_norm["norm_volume"].iloc[-1]
                    for lag in range(1, 6):
                        ticker_latest[f"norm_market_cap_lag_{lag}"] = df_norm["norm_market_cap"].shift(lag).iloc[-1]
                        ticker_latest[f"norm_floating_value_lag_{lag}"] = df_norm["norm_floating_value"].shift(lag).iloc[-1]
                        ticker_latest[f"norm_volume_lag_{lag}"] = df_norm["norm_volume"].shift(lag).iloc[-1]
                else:
                    ticker_latest["norm_market_cap"] = 0.0
                    ticker_latest["norm_floating_value"] = 0.0
                    ticker_latest["norm_volume"] = 0.0
                    for lag in range(1, 6):
                        ticker_latest[f"norm_market_cap_lag_{lag}"] = 0.0
                        ticker_latest[f"norm_floating_value_lag_{lag}"] = 0.0
                        ticker_latest[f"norm_volume_lag_{lag}"] = 0.0

                latest_features = pd.DataFrame([ticker_latest])

                pred_series = predictor.predict_outperformers(latest_features)
                pred_val = float(pred_series.iloc[0])

                idx_fx = stock_returns[ticker].dropna().index.intersection(fx_returns.dropna().index)
                if len(idx_fx) >= 5:
                    corr_val = float(stock_returns[ticker].loc[idx_fx].corr(fx_returns.loc[idx_fx]))
                    if pd.isna(corr_val):
                        corr_val = 0.0
                else:
                    corr_val = 0.0

                results.append(
                    {"ticker": ticker, "expected_excess_return": pred_val, "correlation_to_exchange_rate": corr_val}
                )

            results.sort(key=lambda x: x["expected_excess_return"], reverse=True)
            return results[:10]

        # Construct norm_us_prices and norm_kr_prices dynamically
        from src.ai.prediction_model import OnDevicePredictionModel
        predictor_model = OnDevicePredictionModel()

        us_prices_dict = {}
        for ticker in US_TICKERS:
            df_t = None
            if not df_us.empty and isinstance(df_us.columns, pd.MultiIndex):
                if ticker in df_us.columns.levels[0]:
                    df_t = df_us[ticker].copy()
            if df_t is None:
                if ticker in us_data:
                    closes = us_data[ticker]
                    df_t = pd.DataFrame({"Close": closes}, index=closes.index)
                else:
                    df_t = pd.DataFrame(columns=["Close", "Volume"])
            if "Close" not in df_t.columns and "Adj Close" in df_t.columns:
                df_t["Close"] = df_t["Adj Close"]
            if "Close" not in df_t.columns:
                df_t["Close"] = 100.0
            if "Volume" not in df_t.columns:
                df_t["Volume"] = 100000.0

            if not isinstance(df_t.index, pd.DatetimeIndex):
                df_t.index = pd.to_datetime(df_t.index)
            if df_t.index.tz is not None:
                df_t.index = df_t.index.tz_convert(None)
            df_t.index = df_t.index.normalize()
            df_t = df_t.groupby(df_t.index).mean()
            df_t = df_t.ffill().bfill()
            us_prices_dict[ticker] = df_t

        norm_us_prices = predictor_model.apply_market_normalization(us_prices_dict)

        kr_prices_dict = {}
        for ticker in KR_TICKERS:
            df_t = None
            if not df_kr.empty and isinstance(df_kr.columns, pd.MultiIndex):
                if ticker in df_kr.columns.levels[0]:
                    df_t = df_kr[ticker].copy()
            if df_t is None:
                if ticker in kr_data:
                    closes = kr_data[ticker]
                    df_t = pd.DataFrame({"Close": closes}, index=closes.index)
                else:
                    df_t = pd.DataFrame(columns=["Close", "Volume"])
            if "Close" not in df_t.columns and "Adj Close" in df_t.columns:
                df_t["Close"] = df_t["Adj Close"]
            if "Close" not in df_t.columns:
                df_t["Close"] = 50000.0
            if "Volume" not in df_t.columns:
                df_t["Volume"] = 100000.0

            if not isinstance(df_t.index, pd.DatetimeIndex):
                df_t.index = pd.to_datetime(df_t.index)
            if df_t.index.tz is not None:
                df_t.index = df_t.index.tz_convert(None)
            df_t.index = df_t.index.normalize()
            df_t = df_t.groupby(df_t.index).mean()
            df_t = df_t.ffill().bfill()
            kr_prices_dict[ticker] = df_t

        norm_kr_prices = predictor_model.apply_market_normalization(kr_prices_dict)

        us_outperformers = train_and_predict_region(US_TICKERS, us_returns, "^GSPC", norm_us_prices)
        kr_outperformers = train_and_predict_region(KR_TICKERS, kr_returns, "^KS11", norm_kr_prices)

        # Fallback to make sure exactly 10 are returned
        while len(us_outperformers) < 10 and US_TICKERS:
            missing = US_TICKERS[len(us_outperformers) % len(US_TICKERS)]
            us_outperformers.append(
                {"ticker": missing, "expected_excess_return": 0.0, "correlation_to_exchange_rate": 0.0}
            )
        while len(kr_outperformers) < 10 and KR_TICKERS:
            missing = KR_TICKERS[len(kr_outperformers) % len(KR_TICKERS)]
            kr_outperformers.append(
                {"ticker": missing, "expected_excess_return": 0.0, "correlation_to_exchange_rate": 0.0}
            )

        # Format KR tickers with names
        KR_NAMES = {
            "005930.KS": "삼성전자",
            "000660.KS": "SK하이닉스",
            "035420.KS": "NAVER",
            "005380.KS": "현대차",
            "207940.KS": "삼성바이오로직스",
            "068270.KS": "셀트리온",
            "051910.KS": "LG화학",
            "006400.KS": "삼성SDI",
            "000270.KS": "기아",
            "035720.KS": "카카오",
            "005490.KS": "POSCO홀딩스",
            "036570.KS": "엔씨소프트",
        }
        for item in kr_outperformers:
            raw_ticker = item["ticker"]
            if raw_ticker in KR_NAMES:
                item["ticker"] = f"{KR_NAMES[raw_ticker]} ({raw_ticker})"

        return {"US": us_outperformers[:10], "KR": kr_outperformers[:10]}
