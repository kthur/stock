"""
Unit tests for the TradeExecutor kill-switch gate and live-trade gating.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.realtime.trade_executor import TradeExecutor, ExecResult


class _FakeKiwoom:
    is_connected = True
    simulation_mode = False

    def place_order(self, code, quantity, price, order_type):
        return "FAKE_ORDER_ID"


def _make_executor(**kwargs):
    oms = type("FakeOMS", (), {"orders": {}})()
    return TradeExecutor(kiwoom=_FakeKiwoom(), oms=oms, dry_run=False, **kwargs)


def test_executor_live_gate_requires_env_and_connection():
    os.environ.pop("REALTIME_TRADE_ENABLED", None)
    ex = _make_executor()
    assert not ex.can_trade_live  # env not set

    os.environ["REALTIME_TRADE_ENABLED"] = "true"
    ex2 = _make_executor()
    assert ex2.can_trade_live  # env set + connected + not simulation
    os.environ.pop("REALTIME_TRADE_ENABLED", None)


def test_executor_kill_switch_blocks_execution(tmp_path, monkeypatch):
    """Live-money guard: with kill switch active, no order executes."""
    from src.execution import kill_switch

    ex = _make_executor()
    monkeypatch.setattr(kill_switch, "KILL_SWITCH_FILE", tmp_path / "KILL_SWITCH")
    monkeypatch.setattr(kill_switch, "STATE_FILE", tmp_path / "kill_switch_state.json")

    kill_switch.disengage()
    assert not kill_switch.is_kill_switch_active()

    kill_switch.engage(reason="executor test")
    try:
        assert kill_switch.is_kill_switch_active()
        res = ex.execute("005930", "KOSPI", "BUY", 100, 70000.0)
        assert isinstance(res, ExecResult)
        assert not res.executed
        assert "kill switch" in res.message
    finally:
        kill_switch.disengage()

    res2 = ex.execute("005930", "KOSPI", "BUY", 100, 70000.0)
    assert res2.executed


def test_executor_force_liquidate_bypasses_kill_switch(tmp_path, monkeypatch):
    """Emergency liquidation must still be possible during a kill switch."""
    from src.execution import kill_switch

    ex = _make_executor()
    monkeypatch.setattr(kill_switch, "KILL_SWITCH_FILE", tmp_path / "KILL_SWITCH")
    monkeypatch.setattr(kill_switch, "STATE_FILE", tmp_path / "kill_switch_state.json")

    kill_switch.engage(reason="force liquidate test")
    try:
        res = ex.execute("005930", "KOSPI", "SELL", 100, 70000.0, force_liquidate=True)
        assert res.executed
        assert res.action == "SELL"
    finally:
        kill_switch.disengage()
