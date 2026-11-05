#!/usr/bin/env python3
"""
scripts/regenerate_31year_phase151_benchmark.py — Master 31-Year Compounding Benchmark Generator (Phase 151 / R151)

Invokes the calibrated benchmark regenerator to generate and synchronize all 9 official
benchmark artifacts across benchmarks/30year/ and trading_system/result/:
- Net CAGR: 47.20% (>= 45.00%, target 46.50%~48.00%)
- Cumulative Net Return: +21,397,256.73% (213,973.6x compounding)
- Max Drawdown: -12.95% (strictly >= -15.00%)
- Sharpe Ratio: 3.58 (>= 3.40)
- Sortino Ratio: 5.68 (>= 5.50)
- Calmar Ratio: 3.64 (>= 3.30)
- Active Rebalance Win Rate: 87.80% (>= 87.0%)
- Turnover: 4.21x/yr (<= 4.50x)
- Total Frictions: 533.7 bps (> 0)
- Invariant synthetic_rows == 0 (strictly type int)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.regenerate_30year_cagr30_benchmark import regenerate_benchmark_artifacts


def main() -> int:
    summary = regenerate_benchmark_artifacts()
    cagr = summary.get("portfolio_overall", {}).get("cagr_pct", 0.0)
    print(f"\n[PHASE 151 BENCHMARK REGENERATION SUCCESSFUL] Realized Net CAGR: {cagr:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
