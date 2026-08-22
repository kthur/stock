#!/usr/bin/env python3
"""
generate_run_snapshot.py — Pipeline Execution JSON Snapshot Generator

Extracts consolidated pipeline run metadata, top 50 ensemble picks with 31-strategy scores,
and applied strategy weights, serializing them to a structured run_snapshot.json file.

Usage:
    python trading_system/generate_run_snapshot.py
    python trading_system/generate_run_snapshot.py --result-dir trading_system/result --output trading_system/result/run_snapshot.json
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

KST = timezone(timedelta(hours=9))

# Ensure trading_system root and repo root are on sys.path
_TS_DIR = Path(__file__).resolve().parent
_ROOT = _TS_DIR.parent
for _p in [str(_TS_DIR), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from src.data_layer.indicator_storage import MarketIndicatorStorage
except ModuleNotFoundError:
    try:
        from trading_system.src.data_layer.indicator_storage import MarketIndicatorStorage  # type: ignore
    except ModuleNotFoundError:
        MarketIndicatorStorage = None  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def generate_snapshot(result_dir: Path, db_path: Path, output_file: Path) -> Dict[str, Any]:
    """Build structured run_snapshot dictionary and save to output_file."""
    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    git_sha = os.environ.get("GITHUB_SHA", "local")
    trigger_type = os.environ.get("GITHUB_EVENT_NAME", "manual")

    run_id = f"run_{datetime.now(KST).strftime('%Y%m%d_%H%M%S')}_{git_sha[:7]}"
    regime_detected = "UNKNOWN"
    duration_seconds = 0.0
    total_symbols = 0
    top_picks: List[Dict[str, Any]] = []
    strategy_weights: Dict[str, float] = {}

    # 1. Query SQLite DB if present
    if MarketIndicatorStorage is not None and db_path.exists():
        try:
            storage = MarketIndicatorStorage(db_path=str(db_path))
            with storage._connect() as conn:
                # Get latest run metadata
                r_meta = conn.execute("""
                    SELECT run_id, run_date, regime_detected, total_symbols, duration_seconds
                    FROM pipeline_run_history
                    ORDER BY start_time DESC LIMIT 1
                """).fetchone()
                if r_meta:
                    run_id = r_meta[0] or run_id
                    regime_detected = r_meta[2] or regime_detected
                    total_symbols = r_meta[3] or 0
                    duration_seconds = r_meta[4] or 0.0

                # Get latest strategy weights
                w_rows = conn.execute("""
                    SELECT strategy_name, weight FROM strategy_weight_history
                    WHERE run_id = ?
                """, (run_id,)).fetchall()
                if w_rows:
                    strategy_weights = {row[0]: float(row[1]) for row in w_rows}

                # Get TOP 50 predictions from ensemble_prediction_history
                score_cols = [
                    'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
                    'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
                    'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
                    'arm_score', 'card_score', 'latr_score', 'inst_foreign_sector_score',
                    'supply_chain_score', 'sentiment_score', 'factor_neutralized_score',
                    'vol_target_score', 'microstructure_score', 'accruals_quality_score',
                    'short_squeeze_score', 'valueup_catalyst_score', 'trend_efficiency_score',
                    'gamma_squeeze_score', 'insider_buying_score', 'darkpool_score',
                    'earnings_tone_drift_score'
                ]
                cols_sql = ", ".join(score_cols)
                p_rows = conn.execute(f"""
                    SELECT symbol, ensemble_score, net_expected_return, regime, portfolio_weight, {cols_sql}
                    FROM ensemble_prediction_history
                    WHERE run_id = ?
                    ORDER BY ensemble_score DESC LIMIT 50
                """, (run_id,)).fetchall()

                for idx, row in enumerate(p_rows):
                    sym, e_score, net_ret, reg, p_weight = row[0], row[1], row[2], row[3], row[4]
                    strat_scores = {}
                    for c_idx, c_name in enumerate(score_cols):
                        val = row[5 + c_idx]
                        if val is not None:
                            strat_scores[c_name] = round(float(val), 4)
                    top_picks.append({
                        "rank": idx + 1,
                        "symbol": sym,
                        "ensemble_score": round(float(e_score or 0.0), 4),
                        "net_expected_return_pct": round(float(net_ret or 0.0), 2),
                        "regime": reg or regime_detected,
                        "portfolio_weight": round(float(p_weight or 0.0), 4),
                        "strategy_scores": strat_scores
                    })
        except Exception as e:
            logger.warning(f"Failed extracting run snapshot from DB: {e}")

    # Fallback if top_picks empty: read ensemble_predictions.txt
    if not top_picks:
        ens_txt_path = result_dir / "ensemble_predictions.txt"
        if ens_txt_path.exists():
            try:
                content = ens_txt_path.read_text(encoding="utf-8", errors="replace")
                import re
                score_keys = [
                    'reg_score', 'surge_score', 'll_score', 'vcp_rule_score', 'vcp_ml_score',
                    'lstm_score', 'stat_arb_score', 'sector_score', 'rim_score', 'event_score',
                    'mq_score', 'iv_skew_score', 'order_flow_score', 'reversal_score',
                    'arm_score', 'card_score', 'latr_score', 'inst_foreign_sector_score',
                    'supply_chain_score', 'sentiment_score', 'factor_neutralized_score',
                    'vol_target_score', 'microstructure_score', 'accruals_quality_score',
                    'short_squeeze_score', 'valueup_catalyst_score', 'trend_efficiency_score',
                    'gamma_squeeze_score', 'insider_buying_score', 'darkpool_score',
                    'earnings_tone_drift_score'
                ]
                m_reg = re.search(r"Current Market Regime Detected:\s*([^\n\r]+)", content)
                if m_reg:
                    regime_detected = m_reg.group(1).strip()

                if not strategy_weights:
                    weights_section = False
                    for line in content.splitlines():
                        if "Applied Ensemble Strategy Weights" in line:
                            weights_section = True
                            continue
                        if weights_section:
                            if line.startswith("---") or line.startswith("==="):
                                break
                            m_w = re.match(r"^\s*(.+?)\s*:\s*([+-]?\d+\.?\d*)%", line)
                            if m_w:
                                w_name, w_val = m_w.groups()
                                try:
                                    strategy_weights[w_name.strip()] = round(float(w_val) / 100.0, 4)
                                except ValueError:
                                    pass

                rank = 1
                for line in content.splitlines():
                    m = re.match(r"^\s*(\d+)\.?\s+(\S+)\s+(.+?)\s+([+-]?\d+\.?\d*)%\s+([+-]?\d+\.?\d*)%", line)
                    if m:
                        r_num, sym, name, ens_sc_str, exp_ret_str = m.groups()
                        rest = line[m.end():].split()
                        strat_map = {}
                        for idx, k in enumerate(score_keys):
                            if idx < len(rest):
                                val_s = rest[idx].rstrip('%')
                                try:
                                    strat_map[k] = round(float(val_s) / 100.0, 4)
                                except ValueError:
                                    pass
                        top_picks.append({
                            "rank": int(r_num),
                            "symbol": sym,
                            "ensemble_score": round(float(ens_sc_str) / 100.0, 4),
                            "net_expected_return_pct": round(float(exp_ret_str), 2),
                            "regime": regime_detected,
                            "portfolio_weight": 0.0,
                            "strategy_scores": strat_map
                        })
                        rank += 1
                        if rank > 50:
                            break
            except Exception as _txt_e:
                logger.warning(f"Failed parsing fallback ensemble_predictions.txt: {_txt_e}")

    snapshot_data = {
        "version": "1.0",
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "run_metadata": {
            "run_id": run_id,
            "run_date": date_str,
            "git_sha": git_sha,
            "trigger_type": trigger_type,
            "regime_detected": regime_detected,
            "total_symbols_processed": total_symbols,
            "duration_seconds": round(duration_seconds, 2),
        },
        "top_50_picks": top_picks,
        "strategy_weights": strategy_weights,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Run snapshot written to: {output_file.resolve()} ({output_file.stat().st_size} bytes)")
    return snapshot_data


def main():
    parser = argparse.ArgumentParser(description="Generate Pipeline Run JSON Snapshot")
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=_TS_DIR / "result",
        help="Path to pipeline result directory",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=_TS_DIR / "market_indicators.db",
        help="Path to market_indicators.db SQLite file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_TS_DIR / "result" / "run_snapshot.json",
        help="Target output JSON path",
    )
    args = parser.parse_args()

    generate_snapshot(args.result_dir, args.db_path, args.output)


if __name__ == "__main__":
    main()
