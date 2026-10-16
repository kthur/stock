"""
Unit and integration tests for Interactive Two-Way Telegram Ops Bot.

Phase 112 / Feature F533 (Release R128 / v119 Production Master).
"""

import json
import os
import tempfile
import time
from pathlib import Path
import pytest

from src.notification.interactive_telegram_ops_bot import (
    InteractiveTelegramOpsBot,
    TelegramOpsBot,
    InteractiveOpsBot,
    TwoWayTelegramBot,
    Phase112TelegramOpsBot,
    TelegramOpsCommandResult,
    CallbackTokenPayload,
)


@pytest.fixture
def temp_kill_switch(tmp_path):
    ks_path = tmp_path / "kill_switch_state.json"
    init_state = {"status": "disengaged", "reason": "test initial"}
    ks_path.write_text(json.dumps(init_state), encoding="utf-8")
    return ks_path


@pytest.fixture
def bot(temp_kill_switch):
    return InteractiveTelegramOpsBot(
        bot_token="TEST_BOT_TOKEN_12345",
        authorized_chat_ids=[123456789, 987654321],
        secret_hmac_key="test_secret_hmac_key_2026",
        kill_switch_path=temp_kill_switch,
    )


class TestTelegramOpsBotSecurity:
    """Tests authentication, cryptographic signature, and anti-tamper mechanisms."""

    def test_user_authorization(self, bot):
        assert bot.verify_user(123456789) is True
        assert bot.verify_user("987654321") is True
        assert bot.verify_user(999999999) is False
        assert bot.verify_user("unauthorized_user") is False

    def test_empty_whitelist_safety(self, temp_kill_switch):
        # Empty whitelist must deny all requests by default
        safe_bot = InteractiveTelegramOpsBot(
            authorized_chat_ids=[],
            kill_switch_path=temp_kill_switch,
        )
        assert safe_bot.verify_user(123456789) is False

    def test_callback_token_generation_and_verification(self, bot):
        token = bot.generate_callback_token("approve_rebalance", "plan_001")
        assert "approve_rebalance|plan_001|" in token
        
        verified = bot.verify_callback_token(token)
        assert verified.is_valid is True
        assert verified.action == "approve_rebalance"
        assert verified.payload == "plan_001"

    def test_callback_token_tampering_detected(self, bot):
        token = bot.generate_callback_token("approve_rebalance", "plan_001")
        # Tamper payload
        tampered = token.replace("plan_001", "plan_999")
        verified = bot.verify_callback_token(tampered)
        assert verified.is_valid is False

    def test_callback_token_signature_tampering_detected(self, bot):
        token = bot.generate_callback_token("query_balance", "all")
        parts = token.split("|")
        tampered = f"{parts[0]}|{parts[1]}|{parts[2]}|bad_signature_123"
        verified = bot.verify_callback_token(tampered)
        assert verified.is_valid is False

    def test_callback_token_expired(self, bot):
        past_ts = int(time.time()) - 4000
        token = bot.generate_callback_token("hold_orders", "plan_001", timestamp=past_ts)
        verified = bot.verify_callback_token(token, max_age_secs=300)
        assert verified.is_valid is False


class TestTelegramOpsBotKeyboards:
    """Tests inline keyboard structure and markup generation."""

    def test_rebalance_approval_keyboard_structure(self, bot):
        kb = bot.build_rebalance_approval_keyboard("plan_alpha_1")
        assert "inline_keyboard" in kb
        rows = kb["inline_keyboard"]
        assert len(rows) == 2
        # First row has approve & hold
        assert len(rows[0]) == 2
        assert "승인" in rows[0][0]["text"]
        assert "보류" in rows[0][1]["text"]
        # Second row has kill switch
        assert "킬스위치" in rows[1][0]["text"]

        # Tokens in callback data must be valid
        token_approve = rows[0][0]["callback_data"]
        verified = bot.verify_callback_token(token_approve)
        assert verified.is_valid is True
        assert verified.action == "approve_rebalance"
        assert verified.payload == "plan_alpha_1"

    def test_ops_dashboard_keyboard_structure(self, bot):
        kb = bot.build_ops_dashboard_keyboard()
        assert "inline_keyboard" in kb
        rows = kb["inline_keyboard"]
        assert len(rows) == 2
        assert any("잔고" in btn["text"] for btn in rows[0])
        assert any("위험" in btn["text"] for btn in rows[0])
        assert any("발동" in btn["text"] for btn in rows[1])
        assert any("해제" in btn["text"] for btn in rows[1])


class TestTelegramOpsBotCommands:
    """Tests processing of callback queries and slash commands."""

    def test_unauthorized_callback_rejected(self, bot):
        token = bot.generate_callback_token("query_balance", "all")
        result = bot.process_callback_query(user_id=999999, callback_data=token)
        assert result.success is False
        assert result.action == "unauthorized"
        assert "권한이 없습니다" in result.message

    def test_rebalance_approval_lifecycle(self, bot):
        plan_id = "rebal_20261016_01"
        bot.register_rebalance_plan(plan_id, {"weights": {"005930": 0.20, "AAPL": 0.15}})

        token = bot.generate_callback_token("approve_rebalance", plan_id)
        result = bot.process_callback_query(user_id=123456789, callback_data=token)
        assert result.success is True
        assert result.action == "approve_rebalance"
        assert "승인 완료" in result.message
        assert bot._rebalance_plans[plan_id]["status"] == "APPROVED"

    def test_rebalance_hold_action(self, bot):
        plan_id = "rebal_20261016_02"
        bot.register_rebalance_plan(plan_id, {"target": "KOSPI"})

        token = bot.generate_callback_token("hold_orders", plan_id)
        result = bot.process_callback_query(user_id=123456789, callback_data=token)
        assert result.success is True
        assert result.action == "hold_orders"
        assert "보류" in result.message
        assert bot._rebalance_plans[plan_id]["status"] == "HELD"

    def test_kill_switch_engagement_and_disengagement(self, bot, temp_kill_switch):
        # 1. Engage
        token_engage = bot.generate_callback_token("engage_kill_switch", "test_emergency")
        res_engage = bot.process_callback_query(user_id=123456789, callback_data=token_engage)
        assert res_engage.success is True
        assert res_engage.details["status"] == "engaged"
        
        # Verify file written
        ks_content = json.loads(temp_kill_switch.read_text(encoding="utf-8"))
        assert ks_content["status"] == "engaged"
        assert (temp_kill_switch.parent / "KILL_SWITCH").exists()

        # 2. Disengage
        token_disengage = bot.generate_callback_token("disengage_kill_switch", "test_resume")
        res_disengage = bot.process_callback_query(user_id=123456789, callback_data=token_disengage)
        assert res_disengage.success is True
        assert res_disengage.details["status"] == "disengaged"
        
        ks_content2 = json.loads(temp_kill_switch.read_text(encoding="utf-8"))
        assert ks_content2["status"] == "disengaged"
        assert not (temp_kill_switch.parent / "KILL_SWITCH").exists()

    def test_query_balance_and_risk(self, bot):
        tok_bal = bot.generate_callback_token("query_balance", "all")
        res_bal = bot.process_callback_query(123456789, tok_bal)
        assert res_bal.success is True
        assert "총 평가자산" in res_bal.message
        assert res_bal.details["total_equity"] > 0

        tok_risk = bot.generate_callback_token("query_risk_report", "all")
        res_risk = bot.process_callback_query(123456789, tok_risk)
        assert res_risk.success is True
        assert "샤프지수" in res_risk.message
        assert res_risk.details["sharpe_ratio"] > 100.0

    def test_text_commands(self, bot, temp_kill_switch):
        # /status
        res_status = bot.process_text_command(123456789, "/status")
        assert res_status.success is True
        assert "관제 상태" in res_status.message

        # /kill
        res_kill = bot.process_text_command(123456789, "/kill")
        assert res_kill.success is True
        assert res_kill.details["status"] == "engaged"

        # /resume
        res_resume = bot.process_text_command(123456789, "/resume")
        assert res_resume.success is True
        assert res_resume.details["status"] == "disengaged"

        # Unauthorized text command
        res_unauth = bot.process_text_command(999999, "/status")
        assert res_unauth.success is False
        assert "권한이 없습니다" in res_unauth.message

    def test_audit_trail_tracking(self, bot):
        bot.clear_audit_trail()
        assert len(bot.get_audit_trail()) == 0

        bot.process_text_command(123456789, "/status")
        bot.process_text_command(999999, "/kill")  # unauthorized

        trail = bot.get_audit_trail()
        assert len(trail) == 2
        assert trail[0]["success"] is True
        assert trail[1]["success"] is False
        assert trail[1]["action"] == "unauthorized"


class TestTelegramOpsBotAliases:
    """Verifies that all required backward-compatible aliases point to InteractiveTelegramOpsBot."""

    def test_class_aliases(self):
        assert TelegramOpsBot is InteractiveTelegramOpsBot
        assert InteractiveOpsBot is InteractiveTelegramOpsBot
        assert TwoWayTelegramBot is InteractiveTelegramOpsBot
        assert Phase112TelegramOpsBot is InteractiveTelegramOpsBot
