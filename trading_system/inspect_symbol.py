#!/usr/bin/env python3
"""
trading_system/inspect_symbol.py
Interactive CLI Diagnostic Tool for Stock Exclusion Analysis.

Usage:
    python inspect_symbol.py 005930
    python inspect_symbol.py TSLA
    python inspect_symbol.py AAPL --json
    python inspect_symbol.py --all-excluded
    python inspect_symbol.py --market KOSPI --all-excluded
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is on sys.path
_current_dir = Path(__file__).resolve().parent
_project_root = _current_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from src.analysis.symbol_inspector import SymbolInspector


def main():
    parser = argparse.ArgumentParser(
        description="4-Stage Stock Exclusion Diagnostic & Inspector Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python inspect_symbol.py 005930          # Inspect Samsung Electronics (KRX)
  python inspect_symbol.py TSLA            # Inspect Tesla (US)
  python inspect_symbol.py AAPL --json     # Inspect Apple in JSON format
  python inspect_symbol.py --all-excluded  # Summary of all excluded stocks
        """
    )

    parser.add_argument(
        "symbol",
        nargs="?",
        default="",
        help="Stock ticker symbol (e.g. 005930, 005930.KS, TSLA, AAPL)"
    )
    parser.add_argument(
        "-s", "--symbol-opt",
        dest="symbol_opt",
        default="",
        help="Stock ticker symbol (alternative flag)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output diagnostics in machine-readable JSON format"
    )
    parser.add_argument(
        "--all-excluded",
        action="store_true",
        help="Analyze and summarize exclusion statistics across entire universe"
    )
    parser.add_argument(
        "--market",
        default="",
        help="Filter market for batch summary (e.g. KOSPI, KOSDAQ, SP500, NASDAQ, RUSSELL2000)"
    )

    args = parser.parse_args()
    target_sym = (args.symbol or args.symbol_opt).strip()

    inspector = SymbolInspector()

    if args.all_excluded:
        # Batch analysis
        print("=" * 80)
        print("📊 [시스템 전체 종목 제외 현황 및 원인 분석 요약]")
        print("=" * 80)
        
        u_df = None
        if inspector.indicator_storage is not None:
            try:
                u_df = inspector.indicator_storage.get_universe(args.market if args.market else None)
            except Exception as e:
                print(f"⚠️ 유니버스 로드 실패: {e}")
        
        batch_res = inspector.generate_batch_diagnostics(universe_df=u_df)
        
        if args.json:
            print(json.dumps(batch_res, ensure_ascii=False, indent=2))
            return

        total = batch_res.get("total_symbols_evaluated", 0)
        stages = batch_res.get("stage_breakdown", {})
        top_reasons = batch_res.get("top_exclusion_reasons", {})

        print(f"• 총 평가 대상 종목 수: {total:,}개")
        print(f"• 단계별 탈락 분포:")
        for stg, cnt in stages.items():
            pct = (cnt / total * 100) if total > 0 else 0
            icon = "🟢" if stg == "INCLUDED" else "🔴"
            print(f"  {icon} [{stg:<14}]: {cnt:>5,}개 ({pct:>5.1f}%)")
        
        print("\n• 최다 제외 사유 TOP 5:")
        for r_name, r_cnt in list(top_reasons.items())[:5]:
            r_pct = (r_cnt / total * 100) if total > 0 else 0
            print(f"  * {r_name:<30}: {r_cnt:>5,}개 ({r_pct:>5.1f}%)")
        print("=" * 80)
        return

    if not target_sym:
        parser.print_help()
        print("\n⚠️ 오류: 진단할 종목 코드(티커)를 입력해 주세요. (예: python inspect_symbol.py 005930)")
        sys.exit(1)

    diag = inspector.inspect_symbol(target_sym)

    if args.json:
        print(json.dumps(diag.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(inspector.format_text_report(diag))


if __name__ == "__main__":
    main()
