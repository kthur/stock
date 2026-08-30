import time
import numpy as np
import pandas as pd

from src.core.cross_asset_spillover import CrossAssetSpilloverEngine
from src.core.supply_chain_gnn import SupplyChainGNNEngine
from src.core.range_expansion_breakout import RangeExpansionBreakoutEngine

def _make_dummy_ohlcv(n_bars=30, base_price=100.0, trend=0.001, vol=0.02, volume_base=100000):
    np.random.seed(42)
    returns = np.random.normal(trend, vol, n_bars)
    prices = base_price * np.cumprod(1 + returns)
    highs = prices * (1 + np.abs(np.random.normal(0, vol * 0.5, n_bars)))
    lows = prices * (1 - np.abs(np.random.normal(0, vol * 0.5, n_bars)))
    opens = prices * (1 + np.random.normal(0, vol * 0.3, n_bars))
    volumes = np.random.lognormal(np.log(volume_base), 0.5, n_bars)
    dates = pd.date_range(end='2026-08-30', periods=n_bars, freq='D')
    return pd.DataFrame({'Open': opens, 'High': highs, 'Low': lows, 'Close': prices, 'Volume': volumes}, index=dates)

def test_empty_and_null_inputs():
    for engine_cls, score_col in [
        (CrossAssetSpilloverEngine, 'cross_asset_spillover_score'),
        (SupplyChainGNNEngine, 'supply_chain_gnn_score'),
        (RangeExpansionBreakoutEngine, 'range_expansion_score'),
    ]:
        engine = engine_cls()
        res1 = engine.compute_scores({})
        assert isinstance(res1, pd.DataFrame)
        assert score_col in res1.columns
        assert res1.empty
        res2 = engine.compute_scores(prices_dict={})
        assert isinstance(res2, pd.DataFrame)
        assert res2.empty
        res3 = engine.compute_scores(prices_dict={
            'SYM_NONE': None,
            'SYM_EMPTY': pd.DataFrame(),
            'SYM_FEW_BARS': _make_dummy_ohlcv(n_bars=2),
            'SYM_ONE_BAR': _make_dummy_ohlcv(n_bars=1),
        })
        assert len(res3) == 4
        for score in res3[score_col]:
            assert 0.0 <= score <= 1.0
            assert np.isfinite(score)
            assert score == 0.50

def test_nan_and_inf_resilience_cross_asset():
    engine = CrossAssetSpilloverEngine()
    df_nan = _make_dummy_ohlcv(n_bars=30)
    df_nan.iloc[10:15, :] = np.nan
    df_nan.iloc[20, :] = np.inf
    df_nan.iloc[25, :] = -np.inf
    indicators_bad = {
        'sox': np.nan, 'usdkrw': np.inf, 'tnx': -np.inf,
        'wti': 'invalid_string', 'gold': None,
        'vix': 999999.0, 'sp500': -999999.0
    }
    res = engine.compute_scores(
        prices_dict={'BAD_SYM': df_nan, 'GOOD_SYM': _make_dummy_ohlcv(30)},
        indicators_df=indicators_bad,
        sector_map={'BAD_SYM': 'Semiconductor', 'GOOD_SYM': 'Energy'}
    )
    assert len(res) == 2
    for score in res['cross_asset_spillover_score']:
        assert np.isfinite(score)
        assert 0.05 <= score <= 0.95

def test_nan_and_inf_resilience_supply_chain_gnn():
    engine = SupplyChainGNNEngine()
    df_inf = _make_dummy_ohlcv(30)
    df_inf['Volume'] = np.inf
    df_nan = _make_dummy_ohlcv(30)
    df_nan['Close'] = np.nan
    res = engine.compute_scores(
        prices_dict={
            'NVDA': df_inf, 'TSM': df_nan,
            '000660': _make_dummy_ohlcv(30),
            'ISOLATED_NODE': _make_dummy_ohlcv(30),
        },
        sector_map={'NVDA': 'Tech', 'TSM': 'Tech', '000660': 'Tech'}
    )
    assert len(res) == 4
    for score in res['supply_chain_gnn_score']:
        assert np.isfinite(score)
        assert 0.05 <= score <= 0.95

def test_nan_and_inf_resilience_range_expansion():
    engine = RangeExpansionBreakoutEngine()
    df_corrupt = _make_dummy_ohlcv(30)
    df_corrupt.loc[df_corrupt.index[-1], ['High', 'Low', 'Close']] = [np.inf, -np.inf, np.nan]
    res = engine.compute_scores(prices_dict={'CORRUPT': df_corrupt, 'NORMAL': _make_dummy_ohlcv(30)})
    assert len(res) == 2
    for score in res['range_expansion_score']:
        assert np.isfinite(score)
        assert 0.05 <= score <= 0.95

def test_inverted_and_zero_prices():
    df_inverted = _make_dummy_ohlcv(30)
    df_inverted['High'] = 10.0
    df_inverted['Low'] = 100.0
    df_inverted['Close'] = -50.0
    df_zero = _make_dummy_ohlcv(30)
    df_zero['Open'] = 0.0
    df_zero['High'] = 0.0
    df_zero['Low'] = 0.0
    df_zero['Close'] = 0.0
    df_zero['Volume'] = 0.0

    for engine_cls, col in [
        (CrossAssetSpilloverEngine, 'cross_asset_spillover_score'),
        (SupplyChainGNNEngine, 'supply_chain_gnn_score'),
        (RangeExpansionBreakoutEngine, 'range_expansion_score'),
    ]:
        eng = engine_cls()
        res = eng.compute_scores({'INVERTED': df_inverted, 'ZERO': df_zero})
        assert len(res) == 2
        for score in res[col]:
            assert np.isfinite(score)
            assert 0.05 <= score <= 0.95

def test_extreme_volatility_spikes_and_flash_crashes():
    df_spike = _make_dummy_ohlcv(30)
    df_spike.loc[df_spike.index[-1], ['Open', 'High', 'Low', 'Close']] = [100.0, 10000.0, 100.0, 10000.0]
    df_spike.loc[df_spike.index[-1], 'Volume'] = 1e9
    df_crash = _make_dummy_ohlcv(30)
    df_crash.loc[df_crash.index[-1], ['Open', 'High', 'Low', 'Close']] = [100.0, 100.0, 0.001, 0.001]
    df_crash.loc[df_crash.index[-1], 'Volume'] = 1e9

    for engine_cls, col in [
        (CrossAssetSpilloverEngine, 'cross_asset_spillover_score'),
        (SupplyChainGNNEngine, 'supply_chain_gnn_score'),
        (RangeExpansionBreakoutEngine, 'range_expansion_score'),
    ]:
        eng = engine_cls()
        res = eng.compute_scores({'SPIKE': df_spike, 'CRASH': df_crash})
        assert len(res) == 2
        for score in res[col]:
            assert np.isfinite(score)
            assert 0.05 <= score <= 0.95
        if engine_cls == RangeExpansionBreakoutEngine:
            spike_score = res[res['symbol'] == 'SPIKE'][col].iloc[0]
            crash_score = res[res['symbol'] == 'CRASH'][col].iloc[0]
            assert spike_score > 0.60
            assert crash_score < 0.40

def test_supply_chain_gnn_isolated_and_cyclic_graphs():
    isolated_dict = {f'UNKNOWN_SYM_{i}': _make_dummy_ohlcv(30) for i in range(10)}
    cyclic_edges = [('CYC_A', 'CYC_B', 0.9), ('CYC_B', 'CYC_C', 0.9), ('CYC_C', 'CYC_A', 0.9)]
    engine_cyclic = SupplyChainGNNEngine(custom_edges=cyclic_edges)
    all_dict = {
        **isolated_dict,
        'CYC_A': _make_dummy_ohlcv(30, trend=0.05),
        'CYC_B': _make_dummy_ohlcv(30, trend=-0.05),
        'CYC_C': _make_dummy_ohlcv(30, trend=0.01),
    }
    res = engine_cyclic.compute_scores(prices_dict=all_dict)
    assert len(res) == 13
    for score in res['supply_chain_gnn_score']:
        assert np.isfinite(score)
        assert 0.05 <= score <= 0.95

def test_performance_benchmark_massive_universe():
    n_symbols = 500
    universe = {f'SYM_{i:04d}': _make_dummy_ohlcv(n_bars=30) for i in range(n_symbols)}
    indicators = {'sox': 0.025, 'usdkrw': -0.005, 'tnx': 0.01, 'wti': -0.02, 'gold': 0.005, 'dxy': 0.001, 'vix': -0.08, 'sp500': 0.015}
    sector_map = {f'SYM_{i:04d}': 'Semiconductor' if i % 3 == 0 else 'Financials' for i in range(n_symbols)}

    t0 = time.perf_counter()
    eng_ca = CrossAssetSpilloverEngine()
    res_ca = eng_ca.compute_scores(prices_dict=universe, indicators_df=indicators, sector_map=sector_map)
    t_ca = (time.perf_counter() - t0) * 1000.0 / n_symbols
    assert len(res_ca) == n_symbols

    t0 = time.perf_counter()
    eng_sc = SupplyChainGNNEngine()
    res_sc = eng_sc.compute_scores(prices_dict=universe, sector_map=sector_map)
    t_sc = (time.perf_counter() - t0) * 1000.0 / n_symbols
    assert len(res_sc) == n_symbols

    t0 = time.perf_counter()
    eng_re = RangeExpansionBreakoutEngine()
    res_re = eng_re.compute_scores(prices_dict=universe)
    t_re = (time.perf_counter() - t0) * 1000.0 / n_symbols
    assert len(res_re) == n_symbols

    print(f'\n[Latency Benchmark] CrossAsset: {t_ca:.3f} ms/sym | SupplyChain: {t_sc:.3f} ms/sym | RangeExpansion: {t_re:.3f} ms/sym')
    assert t_ca < 3.0
    assert t_sc < 3.0
    assert t_re < 3.0
