"""
tests/test_challenger_rim_2_stress.py
Adversarial Empirical Stress Test Suite by Challenger 2:
1. MarketIndicatorStorage SQLite Schema Auto-Migration & Persistence
2. generate_report.py::parse_rim robustness (12-col, 9-col, 8-col, NaNs, special chars, malformed lines)
3. merge_predictions.py 5-market mock merging & header deduplication
"""

import os
import sys
import sqlite3
import concurrent.futures
import numpy as np
import pandas as pd
import pytest

# Ensure trading_system is in sys.path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TS_DIR = os.path.join(_ROOT, "trading_system")
if _TS_DIR not in sys.path:
    sys.path.insert(0, _TS_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.data_layer.indicator_storage import MarketIndicatorStorage
from generate_report import parse_rim
from merge_predictions import merge_generic_strategy_files


# ==============================================================================
# 1. MarketIndicatorStorage Auto-Migration & Persistence Adversarial Tests
# ==============================================================================

class TestIndicatorStorageMigrationAndPersistence:

    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        self.tmp_dir = str(tmp_path)
        self.db_path = os.path.join(self.tmp_dir, "test_indicators.db")

    def test_legacy_sqlite_v1_migration_no_data_loss(self):
        """Verify that an ancient SQLite DB with only 4 columns auto-migrates without data loss."""
        legacy_db = os.path.join(self.tmp_dir, "legacy_v1.db")
        with sqlite3.connect(legacy_db) as conn:
            conn.execute('''
                CREATE TABLE stock_fundamentals (
                    symbol TEXT,
                    date TEXT,
                    revenue REAL,
                    operating_income REAL,
                    PRIMARY KEY (symbol, date)
                )
            ''')
            # Seed with 10 legacy records
            for i in range(1, 11):
                conn.execute(
                    "INSERT INTO stock_fundamentals VALUES (?, ?, ?, ?)",
                    (f"SYM_{i:04d}", "2024-03-31", i * 1_000_000.0, i * 100_000.0)
                )
            conn.commit()

        # Initialize MarketIndicatorStorage on the legacy DB
        storage = MarketIndicatorStorage(db_path=legacy_db)

        # 1. Verify schema migration
        with storage._connect() as conn:
            info = conn.execute("PRAGMA table_info('stock_fundamentals')").fetchall()
            cols = [c[1] for c in info]
            expected_new_cols = [
                "net_income", "eps", "shares_outstanding", "dividend_per_share",
                "book_value", "bps", "total_debt", "cash_equivalents"
            ]
            for col in expected_new_cols:
                assert col in cols, f"Migrated column {col} missing from table info"

        # 2. Verify all 10 legacy records are preserved intact
        for i in range(1, 11):
            df_sym = storage.get_fundamentals(f"SYM_{i:04d}")
            assert len(df_sym) == 1, f"Legacy record for SYM_{i:04d} was lost!"
            assert df_sym.iloc[0]["revenue"] == i * 1_000_000.0
            assert df_sym.iloc[0]["operating_income"] == i * 100_000.0
            # Newly migrated columns should exist with default 0.0 or nan
            assert "bps" in df_sym.columns
            assert "total_debt" in df_sym.columns
            assert "cash_equivalents" in df_sym.columns

        # 3. Update existing legacy record with new fundamental columns
        update_df = pd.DataFrame([{
            "symbol": "SYM_0001",
            "date": "2024-03-31",
            "revenue": 1_000_000.0,
            "operating_income": 100_000.0,
            "net_income": 90_000.0,
            "eps": 500.0,
            "shares_outstanding": 10_000.0,
            "dividend_per_share": 50.0,
            "book_value": 5_000_000.0,
            "bps": 500.0,
            "total_debt": 200_000.0,
            "cash_equivalents": 100_000.0,
        }])
        storage.save_fundamentals(update_df)

        updated = storage.get_fundamentals("SYM_0001")
        assert len(updated) == 1
        assert updated.iloc[0]["bps"] == 500.0
        assert updated.iloc[0]["total_debt"] == 200_000.0
        assert updated.iloc[0]["cash_equivalents"] == 100_000.0
        assert updated.iloc[0]["book_value"] == 5_000_000.0
        storage.close()

    def test_migration_partial_columns_idempotence(self):
        """Verify migration is idempotent when some columns already exist."""
        partial_db = os.path.join(self.tmp_dir, "partial.db")
        with sqlite3.connect(partial_db) as conn:
            conn.execute('''
                CREATE TABLE stock_fundamentals (
                    symbol TEXT,
                    date TEXT,
                    revenue REAL,
                    operating_income REAL,
                    net_income REAL DEFAULT 0,
                    book_value REAL DEFAULT 0,
                    PRIMARY KEY (symbol, date)
                )
            ''')
            conn.commit()

        # Run storage init twice
        s1 = MarketIndicatorStorage(db_path=partial_db)
        s1.close()
        s2 = MarketIndicatorStorage(db_path=partial_db)

        with s2._connect() as conn:
            info = conn.execute("PRAGMA table_info('stock_fundamentals')").fetchall()
            cols = [c[1] for c in info]
            assert "bps" in cols
            assert "total_debt" in cols
            assert "cash_equivalents" in cols
            assert "book_value" in cols
        s2.close()

    def test_batch_query_chunking_stress_2500_symbols(self):
        """Stress test chunking with 2,500 symbols (exceeding SQLite 999 parameter limit)."""
        storage = MarketIndicatorStorage(db_path=self.db_path)
        symbols = [f"SYM_{i:05d}" for i in range(2500)]
        records = []
        for sym in symbols:
            records.append({
                "symbol": sym,
                "date": "2026-08-22",
                "revenue": 1000.0,
                "operating_income": 100.0,
                "net_income": 80.0,
                "eps": 2.0,
                "shares_outstanding": 500.0,
                "book_value": 2000.0,
                "bps": 4.0,
                "total_debt": 300.0,
                "cash_equivalents": 150.0,
            })
        df_all = pd.DataFrame(records)
        storage.save_fundamentals(df_all)

        # Batch query all 2,500 symbols
        retrieved = storage.get_all_fundamentals(symbols)
        assert len(retrieved) == 2500
        assert set(retrieved["symbol"]) == set(symbols)
        assert (retrieved["bps"] == 4.0).all()
        assert (retrieved["total_debt"] == 300.0).all()
        assert (retrieved["cash_equivalents"] == 150.0).all()
        storage.close()

    def test_concurrent_multithreaded_save(self):
        """Verify concurrent multi-threaded writes on migrated DB without SQLite lock errors."""
        storage = MarketIndicatorStorage(db_path=self.db_path)

        def worker_write(worker_id):
            sub_records = []
            for j in range(50):
                sym = f"TH_{worker_id}_{j}"
                sub_records.append({
                    "symbol": sym,
                    "date": "2026-08-22",
                    "revenue": float(worker_id * 1000 + j),
                    "operating_income": float(worker_id * 100 + j),
                    "bps": float(worker_id + 1),
                    "total_debt": float(worker_id * 50),
                    "cash_equivalents": float(worker_id * 20),
                })
            df = pd.DataFrame(sub_records)
            storage.save_fundamentals(df)
            return len(sub_records)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_write, w) for w in range(8)]
            results = [f.result() for f in futures]

        assert sum(results) == 400
        # Check all symbols exist
        all_syms = [f"TH_{w}_{j}" for w in range(8) for j in range(50)]
        res_df = storage.get_all_fundamentals(all_syms)
        assert len(res_df) == 400
        storage.close()

    def test_save_fundamentals_adversarial_nan_and_corrupt_types(self):
        """Verify save_fundamentals handles NaNs, None, inf, -inf, unicode strings gracefully."""
        storage = MarketIndicatorStorage(db_path=self.db_path)
        adv_df = pd.DataFrame([
            {
                "symbol": "ADV_NAN",
                "date": "2026-08-22",
                "revenue": np.nan,
                "operating_income": None,
                "net_income": np.nan,
                "eps": None,
                "shares_outstanding": np.nan,
                "book_value": None,
                "bps": np.nan,
                "total_debt": None,
                "cash_equivalents": np.nan,
            },
            {
                "symbol": "ADV_UNICODE_005930",
                "date": "2026-08-22T10:00:00+09:00",
                "revenue": 5000.0,
                "operating_income": 500.0,
                "bps": 1000.0,
                "total_debt": 200.0,
                "cash_equivalents": 50.0,
            }
        ])
        # Must execute without exception
        storage.save_fundamentals(adv_df)

        nan_res = storage.get_fundamentals("ADV_NAN")
        assert len(nan_res) == 1
        assert nan_res.iloc[0]["bps"] == 0.0  # pd.notna checks convert to 0.0

        uni_res = storage.get_fundamentals("ADV_UNICODE_005930")
        assert len(uni_res) == 1
        assert uni_res.iloc[0]["date"] == "2026-08-22"  # date sliced [:10]
        assert uni_res.iloc[0]["bps"] == 1000.0
        storage.close()


# ==============================================================================
# 2. generate_report.py::parse_rim Robustness Adversarial Tests
# ==============================================================================

class TestParseRimAdversarial:

    def test_parse_rim_12_columns_all_5_markets(self):
        """Verify exact parsing of 12-column format across all 5 supported markets."""
        raw_text = """=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===
Date: 2026-08-22 09:30 KST
Total symbols evaluated: 5
Filters: EQ=Earnings Quality | [ADJ]=Extreme ROE normalized | [HC]=Holding Co. discount

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  ROE_raw  ROE_adj     EQ  Filter                          RIM Score
--------------------------------------------------------------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00          +33.9%    15.0%    15.0%   100%  [ADJ]                               95.0%
2    035420    NAVER               KOSDAQ    200000.00   220000.00         +10.0%    12.0%    12.0%   100%                                      85.0%
3    AAPL      Apple Inc.          SP500     180.00      240.00            +33.3%    25.0%    20.0%    85%  [ADJ]                               90.0%
4    NVDA      NVIDIA Corp         NASDAQ    120.00      150.00            +25.0%    30.0%    25.0%    90%  [ADJ] [HC]                          88.0%
5    IWM01     Russell Small       RUSSELL2000 50.00     60.00             +20.0%    10.0%    10.0%   100%                                      70.0%
"""
        date_str, rows = parse_rim(raw_text)
        assert date_str == "2026-08-22 09:30 KST"
        assert len(rows) == 5

        # Check fields of row 1 (KOSPI)
        r1 = rows[0]
        assert r1.rank == 1
        assert r1.symbol == "005930"
        assert r1.name == "삼성전자"
        assert r1.market == "KOSPI"
        assert r1.price == "70000.00"
        assert r1.intrinsic_value == "93750.00"
        assert r1.discount == "+33.9%"
        assert r1.roe_raw == "15.0%"
        assert r1.roe_adj == "15.0%"
        assert r1.eq == "100%"
        assert r1.filter_tags == "[ADJ]"
        assert r1.score == "95.0%"
        assert r1.rim_score == "95.0%"

        # Check multiple filter tags in row 4 (NASDAQ)
        r4 = rows[3]
        assert r4.symbol == "NVDA"
        assert r4.filter_tags == "[ADJ] [HC]"
        assert r4.score == "88.0%"

        # Check RUSSELL2000
        r5 = rows[4]
        assert r5.market == "RUSSELL2000"
        assert r5.symbol == "IWM01"

    def test_parse_rim_9_column_backward_compatibility(self):
        """Verify legacy 9-column format is parsed accurately."""
        raw_text = """=== Strategy 9: RIM Intrinsic Valuation Predictions ===
Date: 2026-08-20 18:00 KST
Total symbols evaluated: 2

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  EQ     RIM Score
------------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00      +33.9%      100%   95.0%
2    AAPL      Apple Inc.          SP500     180.00      240.00        +33.3%      90%    90.0%
"""
        date_str, rows = parse_rim(raw_text)
        assert date_str == "2026-08-20 18:00 KST"
        assert len(rows) == 2
        assert rows[0].symbol == "005930"
        assert rows[0].eq == "100%"
        assert rows[0].score == "95.0%"
        assert rows[0].roe_raw == "N/A"
        assert rows[0].roe_adj == "N/A"

    def test_parse_rim_8_column_backward_compatibility(self):
        """Verify legacy 8-column format is parsed accurately."""
        raw_text = """=== Strategy 9: RIM Valuation ===
Date: 2026-07-26 15:30
Total symbols evaluated: 2

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  RIM Score
--------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00      +33.9%      95.0%
2    AAPL      Apple Inc.          SP500     180.00      240.00        +33.3%      90.0%
"""
        date_str, rows = parse_rim(raw_text)
        assert date_str == "2026-07-26 15:30"
        assert len(rows) == 2
        assert rows[0].symbol == "005930"
        assert rows[0].score == "95.0%"
        assert rows[0].eq == "N/A"

    def test_parse_rim_with_nans_and_na_fields(self):
        """Verify parsing when intrinsic value, discount, roe, eq or scores contain nan / N/A."""
        raw_text = """=== Strategy 9: RIM Valuation ===
Date: 2026-08-22 10:00 KST
Total symbols evaluated: 3

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  ROE_raw  ROE_adj     EQ  Filter                          RIM Score
--------------------------------------------------------------------------------------------------------------------------------------------------
1    NAN01     Missing BPS Corp    KOSPI     5000.00     nan                 nan%      N/A      N/A    N/A                                       nan%
2    NAN02     Distressed Inc      NASDAQ    10.50       nan                 nan%    -5.0%    -5.0%    50%  LOW_EARNINGS_QUALITY                 nan%
3    VALID01   Healthy Co          SP500     100.00      150.00            +50.0%    20.0%    20.0%   100%                                      99.0%
"""
        date_str, rows = parse_rim(raw_text)
        assert len(rows) == 3
        r1 = rows[0]
        assert r1.symbol == "NAN01"
        assert r1.intrinsic_value == "nan"
        assert r1.discount == "nan%"
        assert r1.roe_raw == "N/A"
        assert r1.roe_adj == "N/A"
        assert r1.eq == "N/A"
        assert r1.score == "nan%"

        r2 = rows[1]
        assert r2.symbol == "NAN02"
        assert r2.filter_tags == "LOW_EARNINGS_QUALITY"

        r3 = rows[2]
        assert r3.symbol == "VALID01"
        assert r3.score == "99.0%"

    def test_parse_rim_complex_names_and_negative_numbers(self):
        """Verify parsing with spaces in stock names, special chars, negative discounts and negative scores."""
        raw_text = """=== Strategy 9: RIM Predictions ===
Date: 2026-08-22 10:00 KST

Rank Symbol    Name                      Market    Price       Intrinsic V0  Discount %  ROE_raw  ROE_adj     EQ  Filter                          RIM Score
----------------------------------------------------------------------------------------------------------------------------------------------------------
1    BRK.B     Berkshire Hathaway Inc.   SP500     450.00      500.00            +11.1%    12.5%    12.5%   100%                                      80.0%
2    000270    기아 (KIA Corp.)          KOSPI     95000.00    80000.00          -15.8%    18.0%     3.6%    20%  QUALITY_ADJUSTED                 -10.0%
3    T         AT&T Inc.                 SP500     18.50       15.00             -18.9%     8.0%     8.0%   100%                                    -15.0%
"""
        date_str, rows = parse_rim(raw_text)
        assert len(rows) == 3
        assert rows[0].symbol == "BRK.B"
        assert rows[0].name == "Berkshire Hathaway Inc."

        assert rows[1].symbol == "000270"
        assert rows[1].name == "기아 (KIA Corp.)"
        assert rows[1].discount == "-15.8%"
        assert rows[1].score == "-10.0%"

        assert rows[2].symbol == "T"
        assert rows[2].name == "AT&T Inc."
        assert rows[2].score == "-15.0%"

    def test_parse_rim_malformed_and_garbage_lines_resilience(self):
        """Verify parse_rim gracefully skips malformed, empty, and corrupted lines without crashing."""
        garbage_text = """
=== Header ===
Date: 2026-08-22
Some random noise
Total symbols: 100
Rank Symbol Name Market Price Intrinsic Discount ROE_raw ROE_adj EQ Filter RIM Score
---------------------------------------------------------------------------------
INVALID_LINE_1
1 2 3
1 005930 Samsung KOSPI NOT_A_NUMBER 100 10% 10% 10% 100% ADJ 50%
1    005930    삼성전자            KOSPI     70000.00    93750.00          +33.9%    15.0%    15.0%   100%  [ADJ]                               95.0%
ANOTHER_GARBAGE_LINE_#$%^&*()
"""
        date_str, rows = parse_rim(garbage_text)
        assert date_str == "2026-08-22"
        # Only the 1 well-formed line should be extracted
        assert len(rows) == 1
        assert rows[0].symbol == "005930"


# ==============================================================================
# 3. merge_predictions.py 5-Market Merging & Header Deduplication Adversarial Tests
# ==============================================================================

class TestMergeGenericStrategyFilesAdversarial:

    @pytest.fixture(autouse=True)
    def setup_dirs(self, tmp_path):
        self.tmp_path = tmp_path
        self.result_dir = tmp_path / "result"
        self.result_dir.mkdir(parents=True, exist_ok=True)

        self.markets = ["KOSPI", "KOSDAQ", "SP500", "NASDAQ", "RUSSELL2000"]
        self.target_dirs = {}
        for mkt in self.markets:
            mkt_dir = tmp_path / f"market_{mkt}"
            mkt_dir.mkdir(parents=True, exist_ok=True)
            self.target_dirs[mkt] = mkt_dir

    def test_5_market_mock_merge_single_header_block(self):
        """Verify 5 per-market RIM files merge into a unified file with EXACTLY ONE header block and no duplicates."""
        # Create 5 distinct per-market prediction files
        for i, mkt in enumerate(self.markets):
            file_path = self.target_dirs[mkt] / f"rim_predictions_{mkt}.txt"
            content = f"""=== Strategy 9: RIM (Residual Income Model) Valuation Predictions ===
Date: 2026-08-22 09:00 KST
Total symbols evaluated: 3
Filters: EQ=Earnings Quality | [ADJ]=Extreme ROE normalized | [HC]=Holding Co. discount

Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  ROE_raw  ROE_adj     EQ  Filter                          RIM Score
--------------------------------------------------------------------------------------------------------------------------------------------------
1    SYM_{mkt}_1 Name_{mkt}_1       {mkt:<10} 100.00      150.00            +50.0%    20.0%    20.0%   100%  [ADJ]                               90.0%
2    SYM_{mkt}_2 Name_{mkt}_2       {mkt:<10} 200.00      250.00            +25.0%    15.0%    15.0%   100%                                      80.0%
3    SYM_{mkt}_3 Name_{mkt}_3       {mkt:<10} 300.00      330.00            +10.0%    10.0%    10.0%   100%  [HC]                                70.0%
"""
            file_path.write_text(content, encoding="utf-8")

        # Run merge
        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="rim_predictions.txt",
            title="RIM Intrinsic Valuation Predictions"
        )

        merged_file = self.result_dir / "rim_predictions.txt"
        assert merged_file.exists(), "Merged file rim_predictions.txt was not created!"
        merged_text = merged_file.read_text(encoding="utf-8")

        # Header deduplication verification
        lines = merged_text.splitlines()
        title_count = sum(1 for line in lines if line.startswith("=== RIM Intrinsic Valuation Predictions ==="))
        date_count = sum(1 for line in lines if line.startswith("Date:"))
        filters_count = sum(1 for line in lines if line.startswith("Filters:"))
        rank_header_count = sum(1 for line in lines if line.startswith("Rank "))
        divider_count = sum(1 for line in lines if line.startswith("---"))

        assert title_count == 1, f"Expected 1 title header, found {title_count}"
        assert date_count == 1, f"Expected 1 Date header, found {date_count}"
        assert filters_count == 1, f"Expected 1 Filters line, found {filters_count}"
        assert rank_header_count == 1, f"Expected 1 column header line, found {rank_header_count}"
        assert divider_count == 1, f"Expected 1 divider line, found {divider_count}"

        # Data consolidation verification
        for mkt in self.markets:
            assert f"SYM_{mkt}_1" in merged_text
            assert f"SYM_{mkt}_2" in merged_text
            assert f"SYM_{mkt}_3" in merged_text

        # Verify parse_rim can ingest the entire merged file
        date_parsed, parsed_rows = parse_rim(merged_text)
        assert len(parsed_rows) == 15  # 3 symbols * 5 markets
        parsed_markets = {r.market for r in parsed_rows}
        assert parsed_markets == set(self.markets)

    def test_merge_when_some_markets_have_no_data(self):
        """Verify merge behavior when only a subset of markets have data."""
        # Only KOSPI and SP500 have data
        (self.target_dirs["KOSPI"] / "rim_predictions_KOSPI.txt").write_text(
            """=== Strategy 9: RIM Valuation Predictions ===
Date: 2026-08-22 09:00 KST
Filters: EQ=Earnings Quality | [ADJ]=Extreme ROE normalized | [HC]=Holding Co. discount
Rank Symbol    Name                Market    Price       Intrinsic V0  Discount %  ROE_raw  ROE_adj     EQ  Filter                          RIM Score
--------------------------------------------------------------------------------------------------------------------------------------------------
1    005930    삼성전자            KOSPI     70000.00    93750.00          +33.9%    15.0%    15.0%   100%  [ADJ]                               95.0%
""", encoding="utf-8"
        )
        (self.target_dirs["KOSDAQ"] / "rim_predictions_KOSDAQ.txt").write_text(
            "=== Strategy 9 ===\nDate: 2026-08-22\n데이터 없음\n", encoding="utf-8"
        )

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="rim_predictions.txt",
            title="RIM Intrinsic Valuation Predictions"
        )

        merged_text = (self.result_dir / "rim_predictions.txt").read_text(encoding="utf-8")
        assert "005930" in merged_text
        # Header should exist once
        assert merged_text.count("Filters:") == 1
        assert "데이터 없음" not in merged_text  # Filtered out because KOSPI had real data

    def test_merge_when_all_markets_have_no_data(self):
        """Verify merged file outputs single '데이터 없음' when all markets are empty."""
        for mkt in self.markets:
            (self.target_dirs[mkt] / f"rim_predictions_{mkt}.txt").write_text(
                "=== Strategy 9 ===\nDate: 2026-08-22\n데이터 없음\n", encoding="utf-8"
            )

        merge_generic_strategy_files(
            result_dir=self.result_dir,
            target_dirs=self.target_dirs,
            filename="rim_predictions.txt",
            title="RIM Intrinsic Valuation Predictions"
        )

        merged_text = (self.result_dir / "rim_predictions.txt").read_text(encoding="utf-8")
        assert "데이터 없음" in merged_text
        # Should not crash parse_rim
        date_parsed, rows = parse_rim(merged_text)
        assert len(rows) == 0
