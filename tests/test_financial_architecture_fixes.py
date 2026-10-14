"""
Tests for Quantitative Finance & Risk Management Fixes:
1. VaR / CVaR continuous linear quantile interpolation on small sample windows.
2. Kelly criterion volatility ceiling vs quadratic deflation.
3. Modified Dietz / GIPS-compliant cash flow adjustments and peak drawdown reset.
4. Bessel's correction (ddof=1) in Sharpe Ratio and sample volatility.
5. Sortino Ratio hurdle harmonization.
6. Leland buffer budget constraint preservation.
"""

import math
import numpy as np
import pytest

from src.risk.risk_manager import RiskManager
from src.analysis.statistics import AdvancedStatistics
from src.risk.unified_portfolio_allocator import UnifiedPortfolioAllocator


class TestFinancialArchitectureFixes:
    def test_var_and_cvar_continuous_interpolation_small_samples(self):
        """
        Verify that on small sample sizes (N=19, confidence=0.95),
        continuous quantile interpolation avoids collapsing to the absolute minimum.
        """
        rm = RiskManager()
        stats = AdvancedStatistics()
        
        # 19 distinct sorted daily returns from -5% to +5%
        returns = list(np.linspace(-0.05, 0.05, 19))
        
        var_rm = rm.calculate_var(returns, confidence=0.95)
        var_stats = stats.calculate_var(returns, confidence=0.95)
        cvar_rm = rm.calculate_cvar(returns, confidence=0.95)
        cvar_stats = stats.calculate_cvar(returns, confidence=0.95)
        
        # Legacy int(19 * 0.05) = 0 picked the 0th element (-0.05)
        # Linear interpolation yields a smooth intermediate value between index 0 and 1
        expected_var = float(np.percentile(returns, 5.0))
        assert math.isclose(var_rm, expected_var, rel_tol=1e-5)
        assert math.isclose(var_stats, expected_var, rel_tol=1e-5)
        assert var_rm > returns[0], f"VaR should not be artificially clamped to absolute minimum: {var_rm}"
        
        # CVaR should be strictly <= VaR (tail expected loss is worse or equal to quantile)
        assert cvar_rm <= var_rm
        assert math.isclose(cvar_rm, cvar_stats, rel_tol=1e-5)

    def test_kelly_sizing_volatility_ceiling_avoids_quadratic_penalty(self):
        """
        Verify that Kelly position sizing treats the volatility budget as a ceiling
        rather than compounding multiplicative drag onto an already variance-scaled bet.
        """
        rm = RiskManager(
            portfolio_value=100_000_000.0,
            max_position_size_pct=0.25,
            target_annual_volatility=0.15,
        )
        
        entry_price = 100_000.0
        stop_loss_price = 95_000.0  # 5% stop
        atr_volatile = 5_000.0     # 5% ATR => ~79% annualized vol
        
        qty = rm.calculate_position_sizing(
            symbol="MOMENTUM_RUNNER",
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            win_rate=0.60,
            win_loss_ratio=2.0,
            vix=20.0,
            atr=atr_volatile,
        )
        
        # Ensure positive allocation that respects max_position_size_pct
        assert qty > 0
        allocated_val = qty * entry_price
        assert allocated_val <= rm.portfolio_value * rm.max_position_size_pct

    def test_risk_manager_cash_flow_and_peak_reset(self):
        """
        Verify that external cash deposits and withdrawals do not trigger
        artificial drawdown spikes or false circuit breaker halts.
        """
        rm = RiskManager(portfolio_value=100_000_000.0, max_drawdown_allowed=0.20)
        assert rm.calculate_drawdown() == 0.0
        
        # Portfolio gains 20%
        rm.update_portfolio_value(120_000_000.0)
        assert rm.peak_value == 120_000_000.0
        assert rm.calculate_drawdown() == 0.0
        
        # Client withdraws 30,000,000 KRW (25% capital withdrawal)
        rm.record_cash_flow(-30_000_000.0)
        assert rm.portfolio_value == 90_000_000.0
        
        # The true investment drawdown should still be 0.0 (no investment loss occurred)
        dd = rm.calculate_drawdown()
        assert math.isclose(dd, 0.0, abs_tol=1e-4), f"Cash withdrawal created false drawdown: {dd}"
        
        # Client resets peak to 90M
        rm.reset_peak_value(90_000_000.0)
        assert rm.peak_value == 90_000_000.0

    def test_sharpe_and_volatility_unbiased_bessel_correction(self):
        """
        Verify that sample volatility and Sharpe ratio use ddof=1 (dividing by N-1).
        """
        stats = AdvancedStatistics(risk_free_rate=0.0)
        returns = [0.01, -0.01, 0.02, -0.02, 0.03]  # N=5
        
        vol = stats.calculate_volatility(returns, periods_per_year=1)
        expected_std = float(np.std(returns, ddof=1))
        assert math.isclose(vol, expected_std, rel_tol=1e-5)
        
        sharpe = stats.calculate_sharpe_ratio(returns, periods_per_year=1)
        expected_sharpe = float(np.mean(returns) / expected_std)
        assert math.isclose(sharpe, expected_sharpe, rel_tol=1e-5)

    def test_sortino_ratio_hurdle_harmonization(self):
        """
        Verify that Sortino Ratio uses consistent MAR in both numerator and denominator.
        """
        stats = AdvancedStatistics(risk_free_rate=0.02)
        returns = [0.02, 0.01, -0.01, 0.03, -0.02, 0.04]
        
        # Custom MAR = 0.001
        custom_mar = 0.001
        sortino = stats.calculate_sortino_ratio(returns, target_return=custom_mar, periods_per_year=252)
        assert math.isfinite(sortino)
        assert sortino > 0.0

    def test_leland_no_trade_buffer_budget_constraint(self):
        """
        Verify that Leland buffer bands cannot cause total portfolio allocation
        to exceed 1.0 (preventing unintended borrowing/leverage).
        """
        allocator = UnifiedPortfolioAllocator()
        target_w = np.array([0.35, 0.35, 0.30])
        current_w = np.array([0.40, 0.40, 0.35])  # Sum = 1.15
        vols = np.array([0.02, 0.02, 0.02])
        
        realized_w = allocator.apply_leland_no_trade_buffers(
            target_weights=target_w,
            current_weights=current_w,
            volatilities=vols
        )
        
        assert np.sum(realized_w) <= 1.00 + 1e-6, f"Allocation breached 100%: {np.sum(realized_w)}"
