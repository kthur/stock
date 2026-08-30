import numpy as np
import pandas as pd
from trading_system.src.ai.concept_drift import ConceptDriftDetector
from trading_system.src.telegram_bot.bot_engine import TelegramBotEngine, fetch_market_data_with_fallback


def test_concept_drift_psi_calculation():
    """Verify ConceptDriftDetector calculates PSI and triggers automated re-training flag when PSI > 0.25."""
    detector = ConceptDriftDetector(psi_threshold=0.25)
    
    np.random.seed(42)
    reference = np.random.normal(loc=0.0, scale=1.0, size=1000)
    
    # 1. Identical distribution -> low PSI (< 0.10)
    current_same = np.random.normal(loc=0.0, scale=1.0, size=1000)
    psi_same = detector.compute_psi(reference, current_same)
    assert psi_same < 0.10

    # 2. Shifted distribution -> high PSI (> 0.25)
    current_shifted = np.random.normal(loc=1.5, scale=1.0, size=1000)
    psi_shifted = detector.compute_psi(reference, current_shifted)
    assert psi_shifted > 0.25

    # 3. DataFrame feature drift check
    df_ref = pd.DataFrame({'feat1': reference, 'feat2': reference})
    df_cur = pd.DataFrame({'feat1': current_shifted, 'feat2': current_shifted})
    
    report = detector.check_feature_drift(df_ref, df_cur)
    assert report['requires_retraining'] is True
    assert report['max_psi'] > 0.25


def test_telegram_bot_emergency_stop_and_override():
    """Verify Telegram bot emergency stop liquidates portfolio and override weight modifies strategy weight."""
    bot = TelegramBotEngine()
    bot.add_authorized_user(12345)

    # 1. Test /emergency_stop command
    msg_stop = bot.process_message(12345, "/emergency_stop")
    assert "EMERGENCY STOP" in msg_stop

    # 2. Test /override_weight command
    msg_override = bot.process_message(12345, "/override_weight regression 0.15")
    assert "STRATEGY OVERRIDE" in msg_override
    assert "regression" in msg_override
    assert "0.15" in msg_override


def test_multi_source_data_fallback():
    """Verify fetch_market_data_with_fallback handles fallbacks gracefully."""
    df = fetch_market_data_with_fallback("AAPL", period="5d")
    assert isinstance(df, pd.DataFrame)
