"""
tests/test_phase114_mamba_forecaster.py
Unit & Integration Tests for Mamba SSM Foundation Engine & Multi-Horizon Forecaster (Phase 114, Features F540 & F541).
"""

import math
import numpy as np
import pytest

from src.ai.mamba_ssm_engine import MambaSSMBlock, MambaSSMConfig, MambaSSMEngine
from src.ai.multi_horizon_sequence_forecaster import (
    ConformalQuantileCalibrator,
    MultiHorizonSequenceForecaster,
    create_multi_horizon_forecaster,
)


class TestMambaSSMEngine:
    def test_mamba_config_defaults(self):
        cfg = MambaSSMConfig(d_model=64, d_state=16, d_conv=4, expand=2)
        assert cfg.d_model == 64
        assert cfg.d_state == 16
        assert cfg.d_inner == 128
        assert cfg.dt_rank == 4

    def test_mamba_block_forward_numpy(self):
        cfg = MambaSSMConfig(d_model=32, d_state=8, d_conv=4, expand=2)
        block = MambaSSMBlock(cfg, use_torch=False)
        x = np.random.randn(2, 10, 32).astype(np.float32)
        out = block.forward_numpy(x)
        assert out.shape == (2, 10, 32)
        assert not np.isnan(out).any()

    def test_mamba_engine_forward_both_backends(self):
        cfg = MambaSSMConfig(d_model=32, d_state=8, n_layers=2)
        for use_torch in [True, False]:
            engine = MambaSSMEngine(cfg, use_torch=use_torch)
            x = np.random.randn(3, 12, 32).astype(np.float32)
            out = engine.forward(x)
            assert out.shape == (3, 12, 32)
            assert not np.isnan(out).any()

    def test_mamba_numerical_stability_under_extreme_inputs(self):
        cfg = MambaSSMConfig(d_model=16, d_state=8, n_layers=1)
        engine = MambaSSMEngine(cfg, use_torch=False)
        # Extreme values
        x = np.array([[[1e4] * 16, [-1e4] * 16]], dtype=np.float32)
        out = engine.forward(x)
        assert np.all(np.isfinite(out))


class TestMultiHorizonSequenceForecaster:
    def test_forecaster_multi_horizon_predictions(self):
        forecaster = MultiHorizonSequenceForecaster(
            d_model=32,
            hidden_dim=64,
            horizons=(1, 5, 20, 60),
            use_torch=False,
        )
        x = np.random.randn(5, 32).astype(np.float32)
        out = forecaster.predict(x, mc_passes=3)

        assert len(out.predictions) == 4
        for h in [1, 5, 20, 60]:
            assert h in out.predictions
            p = out.predictions[h]
            assert "p10" in p and "p50" in p and "p90" in p
            assert len(p["p50"]) == 5
            # Quantile ordering: P10 <= P90
            assert np.all(p["p10"] <= p["p90"])
            assert np.all(p["aleatoric_std"] > 0.0)

    def test_forecaster_3d_sequence_pooling(self):
        forecaster = MultiHorizonSequenceForecaster(
            d_model=32,
            hidden_dim=64,
            horizons=(1, 5),
            use_torch=False,
        )
        # Sequence input (batch=4, seq_len=15, d_model=32)
        seq_x = np.random.randn(4, 15, 32).astype(np.float32)
        out = forecaster.predict(seq_x, mc_passes=1)
        assert len(out.predictions[1]["p50"]) == 4

    def test_conformal_calibration_guarantees(self):
        calibrator = ConformalQuantileCalibrator(target_coverage=0.80)
        np.random.seed(42)
        n = 100
        val_preds = {
            1: {
                "p10": np.full(n, -0.02),
                "p50": np.full(n, 0.00),
                "p90": np.full(n, 0.02),
            }
        }
        val_targets = {
            1: np.random.normal(0.0, 0.015, size=n)
        }
        q_hat = calibrator.fit(val_preds, val_targets)
        assert 1 in q_hat
        assert q_hat[1] >= 0.0

        calibrated = calibrator.calibrate(val_preds)
        assert np.all(calibrated[1]["p90"] >= val_preds[1]["p90"])
        assert np.all(calibrated[1]["p10"] <= val_preds[1]["p10"])

    def test_pinball_loss_computation(self):
        forecaster = create_multi_horizon_forecaster(d_model=16, use_torch=False)
        preds = {
            1: np.array([[-0.01, 0.00, 0.01], [-0.02, 0.01, 0.03]]),
            5: np.array([[-0.03, 0.01, 0.05], [-0.04, 0.02, 0.06]]),
        }
        targets = {
            1: np.array([0.005, -0.01]),
            5: np.array([0.02, 0.03]),
        }
        losses = forecaster.compute_pinball_loss(preds, targets)
        assert 1 in losses and 5 in losses
        assert losses[1] > 0.0
        assert losses[5] > 0.0
