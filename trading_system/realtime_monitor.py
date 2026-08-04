#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Realtime Intraday Monitor Daemon - 장중 실시간 리스크/시그널 보정/매매 실행

일 단위 파이프라인(run_pipeline.py)이 장 마감 후 생성한 워치리스트를 읽어,
장중 15분 간격으로 실시간 시세를 폴링하며 아래를 수행한다:
  1. 손절/익절 트리거        (진입가 대비 임계값 + 인트라데이 마이크로구조 엔진)
  2. 매크로 위험 경보         (실시간 VIX/USDKRW 위기 임계 돌파)
  3. 시그널 보정              (일봉 예상수익률과 장중 방향 역행 시 다운그레이드)
  4. 실매매 실행              (DRY_RUN 기본, 키움 실연결 시 라이브)

사용법:
  .venv/bin/python trading_system/realtime_monitor.py --once
  .venv/bin/python trading_system/realtime_monitor.py --interval 15   # 데몬
  .venv/bin/python trading_system/realtime_monitor.py --dry-run       # 기본
  REALTIME_TRADE_ENABLED=true .venv/bin/python trading_system/realtime_monitor.py
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# 프로젝트 루트를 sys.path에 추가 (trading_system/ 아래에서 실행해도 동작)
_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.realtime.intraday_monitor import IntradayMonitor, WatchItem
from src.realtime.market_hours import get_session
from src.realtime.price_feed import RealtimePriceFeed
from src.realtime.state_store import RealtimeStateStore
from src.realtime.trade_executor import TradeExecutor

logger = logging.getLogger(__name__)


# ── 워치리스트 로딩 ────────────────────────────────────────────────────────

def load_ensemble_watchlist(result_dir: str = "result") -> tuple[List[str], Dict[str, str], Dict[str, float], Dict[str, float]]:
    """ensemble_predictions.txt에서 TOP 종목 워치리스트를 로드한다.

    파일 형식 (ensemble_scorer 출력):
        [SP500] Top 100 Ensemble Picks
        Rank Symbol    Name              Ens Score   Expected Ret ...
        1    AAPL      Apple Inc.              39.1%        0.00% ...

    Returns: (symbols, market_of, expected_returns, scores)
    """
    import re

    symbols: List[str] = []
    market_of: Dict[str, str] = {}
    expected_returns: Dict[str, float] = {}
    scores: Dict[str, float] = {}
    path = Path(result_dir) / "ensemble_predictions.txt"
    if not path.exists():
        logger.warning(f"[WATCHLIST] {path} not found — watchlist empty")
        return symbols, market_of, expected_returns, scores

    current_market = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        m_section = re.match(r"\[([A-Z0-9]+)\]\s+Top\s+\d+", line)
        if m_section:
            current_market = m_section.group(1)
            continue
        if not current_market:
            continue
        tokens = line.split()
        if len(tokens) < 4:
            continue
        if not tokens[0].isdigit():
            continue
        sym = tokens[1]
        if not sym or not sym.replace(".", "").replace("-", "").isalnum():
            continue
        pct_tokens = re.findall(r"[+-]?[\d.]+%", line)
        score = 0.0
        exp_ret = 0.0
        if len(pct_tokens) >= 1:
            score = float(pct_tokens[0].rstrip("%")) / 100.0
        if len(pct_tokens) >= 2:
            exp_ret = float(pct_tokens[1].rstrip("%")) / 100.0
        if sym not in symbols:
            symbols.append(sym)
            market_of[sym] = current_market
        expected_returns[sym] = exp_ret
        scores[sym] = score
    logger.info(f"[WATCHLIST] loaded {len(symbols)} symbols from {path.name}")
    return symbols, market_of, expected_returns, scores


def load_positions(kiwoom=None, holdings_path: Optional[str] = None) -> Dict[str, Dict]:
    """보유 포지션 로드: 키움 계좌 우선, 파일(JSON) 폴백."""
    positions: Dict[str, Dict] = {}
    if kiwoom is not None and getattr(kiwoom, "is_connected", False):
        try:
            for h in kiwoom.get_holdings() or []:
                sym = str(h.get("code") or h.get("symbol") or "").strip()
                if not sym:
                    continue
                positions[sym] = {
                    "quantity": int(h.get("quantity", 0) or 0),
                    "entry_price": float(h.get("avg_price", 0) or h.get("entry_price", 0) or 0),
                }
            if positions:
                logger.info(f"[POSITIONS] loaded {len(positions)} from kiwoom account")
                return positions
        except Exception as e:
            logger.warning(f"[POSITIONS] kiwoom holdings failed: {e}")

    if holdings_path and os.path.exists(holdings_path):
        try:
            with open(holdings_path, encoding="utf-8") as f:
                data = json.load(f)
            for sym, info in data.items():
                positions[sym] = {
                    "quantity": int(info.get("quantity", 0) or 0),
                    "entry_price": float(info.get("entry_price", 0) or 0),
                }
            logger.info(f"[POSITIONS] loaded {len(positions)} from {holdings_path}")
        except Exception as e:
            logger.warning(f"[POSITIONS] file load failed: {e}")
    return positions


def _load_live_macro(feed) -> tuple[Optional[float], Optional[float]]:
    """실시간 VIX / USDKRW 조회 (yfinance 폴백)."""
    vix, usdkrw = None, None
    try:
        quotes = feed.get_quotes(["^VIX", "USDKRW=X"], {"^VIX": "US", "USDKRW=X": "US"}, force_refresh=True)
        vix = quotes["^VIX"].price if "^VIX" in quotes else None
        usdkrw = quotes["USDKRW=X"].price if "USDKRW=X" in quotes else None
    except Exception as e:
        logger.debug(f"[MACRO] live macro fetch failed: {e}")
    return vix, usdkrw


def _notify_telegram_rt(msg: str) -> None:
    """텔레그램 알림 (run_pipeline의 _notify_telegram 재사용)."""
    try:
        from run_pipeline import _notify_telegram
        _notify_telegram(msg, level="WARNING" if "⚠️" in msg else "INFO")
    except Exception as e:
        logger.warning(f"[TG] telegram notify failed: {e}")


def build_watch_items_from_sources(
    symbols: List[str], market_of: Dict[str, str],
    expected_returns: Dict[str, float], scores: Dict[str, float],
    positions: Dict[str, Dict],
) -> List[WatchItem]:
    items = []
    for sym in symbols:
        pos = positions.get(sym, {})
        items.append(WatchItem(
            symbol=sym,
            market=market_of.get(sym, "KOSPI"),
            entry_price=float(pos.get("entry_price", 0.0) or 0.0),
            position_qty=int(pos.get("quantity", 0) or 0),
            expected_return=float(expected_returns.get(sym, 0.0) or 0.0),
            ensemble_score=float(scores.get(sym, 0.0) or 0.0),
        ))
    # 보유 중이지만 워치리스트에 없는 종목도 추가
    known = {i.symbol for i in items}
    for sym, pos in positions.items():
        if sym not in known:
            items.append(WatchItem(
                symbol=sym, market="KOSPI",
                entry_price=float(pos.get("entry_price", 0.0) or 0.0),
                position_qty=int(pos.get("quantity", 0) or 0),
            ))
    return items


# ── 메인 실행 루프 ─────────────────────────────────────────────────────────

def run_once(args) -> None:
    session = get_session()
    logger.info(f"[SESSION] {session.market} open={session.is_open} — {session.next_action}")
    if not session.is_open:
        logger.info("[SESSION] market closed — skipping cycle (run during trading hours)")
        return

    state_store = RealtimeStateStore(db_path=args.state_db)

    # 키움 커넥터 (실매매 가능 시에만 연결)
    kiwoom = None
    if args.kiwoom_account and not args.dry_run:
        try:
            from src.broker.kiwoom import KiwoomConnector
            kiwoom = KiwoomConnector()
            kiwoom.simulation_mode = not args.live
            if kiwoom.connect(args.kiwoom_account):
                logger.info(f"[KIWOOM] connected (simulation_mode={kiwoom.simulation_mode})")
            else:
                logger.warning("[KIWOOM] connect failed — fallback to watch-only")
                kiwoom = None
        except Exception as e:
            logger.warning(f"[KIWOOM] init failed: {e}")
            kiwoom = None

    feed = RealtimePriceFeed(kiwoom=kiwoom, use_yfinance=True)

    # 워치리스트 로드
    symbols, market_of, expected_returns, scores = load_ensemble_watchlist(args.result_dir)
    positions = load_positions(kiwoom=kiwoom, holdings_path=args.holdings_path)
    items = build_watch_items_from_sources(symbols, market_of, expected_returns, scores, positions)

    if not items:
        logger.warning("[MONITOR] no watch items — nothing to do")
        return

    # 마켓별 심볼 매핑 (yfinance 접미사용)
    market_of_all = dict(market_of)
    for sym, pos in positions.items():
        if sym not in market_of_all:
            market_of_all[sym] = "KOSPI"

    # 엔진 구성
    from src.risk.intraday_stop_loss import IntradayStopLossEngine
    from src.risk.risk_manager import CrisisDetector, RiskManager
    risk_mgr = RiskManager()
    crisis_detector = CrisisDetector(risk_mgr)
    intraday_engine = IntradayStopLossEngine()

    monitor = IntradayMonitor(
        state_store=state_store,
        intraday_engine=intraday_engine,
        crisis_detector=crisis_detector,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        macro_vix_threshold=args.vix_threshold,
        macro_usdkrw_threshold=args.usdkrw_threshold,
        signal_reversal_threshold=args.signal_reversal,
    )

    executor = TradeExecutor(
        kiwoom=kiwoom,
        oms=None,
        dry_run=args.dry_run,
        max_order_value_krw=args.max_order_value,
    )

    # 1) 실시간 시세 폴링
    logger.info(f"[FETCH] polling {len(items)} symbols (15분 캐시 TTL)")
    quotes_map = feed.get_quotes([i.symbol for i in items], market_of_all, force_refresh=True)
    quotes = {s: q.price for s, q in quotes_map.items()}
    volumes = {s: q.volume for s, q in quotes_map.items()}
    logger.info(f"[FETCH] got {len(quotes)}/{len(items)} quotes")

    # 2) 실시간 매크로
    vix, usdkrw = _load_live_macro(feed)
    if vix is not None or usdkrw is not None:
        logger.info(f"[MACRO] VIX={vix}, USD/KRW={usdkrw}")

    # 3) 모니터링 평가
    date_str = datetime.now().strftime("%Y-%m-%d")
    actions = monitor.evaluate_batch(items, quotes, date_str, volumes=volumes, vix=vix, usdkrw=usdkrw)
    logger.info(f"[MONITOR] evaluated {len(items)} items -> {len(actions)} actions")

    # 4) 액션 처리: 알림 + 매매
    alerts = []
    for act in actions:
        if act.symbol == "__MARKET__":
            msg = f"⚠️ [실시간 매크로 경보] {act.reason}"
            alerts.append(msg)
            continue
        msg = f"{'🔴' if act.action_type == 'STOP_LOSS' else '🟢' if act.action_type == 'TAKE_PROFIT' else '🟡'} [{act.action_type}] {act.symbol} ({act.market}): {act.reason} @ {act.price:,.0f}"
        alerts.append(msg)

        # 매매 실행: 손절/익절 시 SELL
        if act.action_type in ("STOP_LOSS", "TAKE_PROFIT"):
            item = next((i for i in items if i.symbol == act.symbol), None)
            if item is not None and item.position_qty > 0:
                res = executor.execute(act.symbol, item.market, "SELL", item.position_qty, act.price, reason=act.action_type)
                alerts.append(f"💼 [EXEC] {res.message}")

    for m in alerts:
        logger.warning(m if "⚠️" in m or "🔴" in m else m)
    if alerts:
        _notify_telegram_rt("\n".join(alerts))

    # 5) 상태 저장 (open_price 등)
    logger.info("[MONITOR] run cycle complete")


def run_daemon(args) -> None:
    interval_min = max(1, args.interval)
    logger.info(f"[DAEMON] starting realtime monitor (interval={interval_min}m, dry_run={args.dry_run})")
    while True:
        try:
            session = get_session()
            if session.is_open:
                run_once(args)
            else:
                logger.info(f"[DAEMON] market closed — sleeping ({session.next_action})")
        except KeyboardInterrupt:
            logger.info("[DAEMON] stopped by user")
            break
        except Exception as e:
            logger.exception(f"[DAEMON] cycle error: {e}")
        time.sleep(interval_min * 60)


def main() -> None:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s - %(levelname)s - %(message)s")

    from src.config import TradingConfig
    _cfg = TradingConfig()

    parser = argparse.ArgumentParser(description="실시간 장중 모니터링 데몬")
    parser.add_argument("--interval", type=int, default=_cfg.realtime_interval_min,
                        help="폴링 간격(분). 데몬 모드에서 사용 (기본 15)")
    parser.add_argument("--once", action="store_true", help="1회만 실행 후 종료")
    parser.add_argument("--dry-run", action="store_true", default=_cfg.realtime_dry_run,
                        help="실매매 없이 모의 실행 (기본 True)")
    parser.add_argument("--live", action="store_true",
                        help="실매매 활성화 (REALTIME_TRADE_ENABLED=true 와 동일). 키움 실연결 필요")
    parser.add_argument("--result-dir", default="result", help="ensemble_predictions.txt 위치 (기본 result/)")
    parser.add_argument("--state-db", default=_cfg.realtime_state_db, help="장중 상태 DB 경로")
    parser.add_argument("--holdings-path", default=None, help="보유 포지션 JSON 파일 (키움 없을 때)")
    parser.add_argument("--kiwoom-account", default=_cfg.kiwoom_account, help="키움 계좌번호")
    parser.add_argument("--stop-loss-pct", type=float, default=_cfg.realtime_stop_loss_pct,
                        help="손절 임계 (기본 -0.04 = -4%%)")
    parser.add_argument("--take-profit-pct", type=float, default=_cfg.realtime_take_profit_pct,
                        help="익절 임계 (기본 0.08 = +8%%)")
    parser.add_argument("--vix-threshold", type=float, default=_cfg.realtime_vix_threshold,
                        help="VIX 위기 임계 (기본 28)")
    parser.add_argument("--usdkrw-threshold", type=float, default=_cfg.realtime_usdkrw_threshold,
                        help="USD/KRW 위기 임계 (기본 1450)")
    parser.add_argument("--max-order-value", type=float, default=_cfg.realtime_max_order_value_krw,
                        help="최대 주문 금액(KRW)")
    parser.add_argument("--signal-reversal", type=float, default=_cfg.realtime_signal_reversal_threshold,
                        help="신호 보정 역행 임계 (기본 -0.03 = 시가 대비 -3%%)")
    args = parser.parse_args()

    if _cfg.realtime_trade_enabled:
        args.dry_run = False
        args.live = True

    if args.once:
        run_once(args)
    else:
        run_daemon(args)


if __name__ == "__main__":
    main()
