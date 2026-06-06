#!/usr/bin/env python3
"""Phase 3 Verification Script"""
import sys
import os
sys.path.insert(0, 'd:/Finance/code/stock/trading_system/src')
os.chdir('d:/Finance/code/stock/trading_system')

print('=' * 60)
print('PHASE 3 ACCEPTANCE CRITERIA VERIFICATION')
print('=' * 60)

results = {}

# Test 1: Sentiment
print('\n[1] Sentiment Analysis...')
try:
    from ai.sentiment import analyze_sentiment, SentimentAnalyzer
    score = analyze_sentiment('The stock market is rallying with strong bullish momentum')
    assert isinstance(score, float), f'Expected float, got {type(score)}'
    assert -1.0 <= score <= 1.0, f'Score {score} out of range [-1, 1]'
    neg_score = analyze_sentiment('Market crash is devastating, major losses')
    sa = SentimentAnalyzer()
    result = sa.analyze('Stock prices are rising strongly')
    assert 'score' in result and 'label' in result
    print(f'  positive text score: {score:.4f}')
    print(f'  negative text score: {neg_score:.4f}')
    print(f'  SentimentAnalyzer result: {result}')
    results['sentiment'] = 'PASS'
except Exception as e:
    print(f'  FAIL: {e}')
    results['sentiment'] = f'FAIL: {e}'

# Test 2: RL Trader
print('\n[2] RL Trading Model...')
try:
    from ai.rl_trader import train_rl_model, TradingEnvironment, DQNAgent
    import numpy as np
    result = train_rl_model()
    assert result['episodes'] >= 1, 'No episodes completed'
    assert len(result['rewards']) >= 1, 'No rewards recorded'
    print(f'  Episodes: {result["episodes"]}')
    print(f'  Rewards: {result["rewards"]}')
    print(f'  Final loss: {result.get("final_loss", "N/A")}')
    results['rl_trader'] = 'PASS'
except Exception as e:
    print(f'  FAIL: {e}')
    import traceback; traceback.print_exc()
    results['rl_trader'] = f'FAIL: {e}'

# Test 3: Asset Allocation
print('\n[3] Asset Allocation...')
try:
    from strategy.asset_allocation import AssetAllocator, allocate_assets
    price_data = {
        'SAMSUNG': [70000, 71000, 69500, 72000, 73500],
        'HYUNDAI': [180000, 182000, 179000, 185000, 188000],
        'KAKAO': [45000, 44500, 46000, 47000, 45500],
    }
    for strategy in ['equal_weight', 'risk_parity', 'momentum']:
        weights = allocate_assets(price_data, strategy=strategy)
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-9, f'{strategy}: weights sum to {total}, not 1.0'
        print(f'  {strategy}: {weights} (sum={total:.10f})')
    results['asset_allocation'] = 'PASS'
except Exception as e:
    print(f'  FAIL: {e}')
    import traceback; traceback.print_exc()
    results['asset_allocation'] = f'FAIL: {e}'

# Test 4: PDF Report
print('\n[4] PDF Report Generator...')
try:
    from utils.pdf_report import generate_backtest_pdf, PDFReportGenerator
    mock_data = {
        'symbol': 'SAMSUNG',
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'initial_capital': 10000000,
        'final_capital': 11500000,
        'total_return_pct': '15.0%',
        'win_rate': '62%',
        'max_drawdown': '-8.5%',
        'profit_factor': 1.85,
        'sharpe_ratio': 1.42,
        'total_fees': 45000,
        'trades_count': 48,
        'trades': [
            {'exit_date': '2024-03-15', 'direction': 'LONG', 'quantity': 10, 'entry_price': 70000, 'exit_price': 73000, 'pnl': 30000},
            {'exit_date': '2024-06-20', 'direction': 'SHORT', 'quantity': 5, 'entry_price': 75000, 'exit_price': 72000, 'pnl': 15000},
        ]
    }
    output_path = 'd:/Finance/code/stock/trading_system/test_report_phase3.pdf'
    result_path = generate_backtest_pdf(mock_data, output_path)
    assert os.path.exists(result_path), f'PDF not created at {result_path}'
    size = os.path.getsize(result_path)
    assert size > 1000, f'PDF too small: {size} bytes'
    print(f'  PDF saved to: {result_path}')
    print(f'  PDF size: {size:,} bytes')
    results['pdf_report'] = 'PASS'
except Exception as e:
    print(f'  FAIL: {e}')
    import traceback; traceback.print_exc()
    results['pdf_report'] = f'FAIL: {e}'

# Test 5: Broker
print('\n[5] Broker API Abstraction...')
try:
    from broker.real_broker import BrokerBase, RealBroker, KoreaInvestmentBroker, KiwoomBroker
    from abc import ABC
    assert issubclass(BrokerBase, ABC), 'BrokerBase must extend ABC'
    assert issubclass(RealBroker, BrokerBase), 'RealBroker must extend BrokerBase'
    
    rb = RealBroker()
    conn = rb.connect()
    print(f'  RealBroker.connect() = {conn}')
    order = rb.submit_order('SAMSUNG', 10, 'BUY')
    print(f'  RealBroker.submit_order() = {order}')
    
    ki = KoreaInvestmentBroker()
    ki_conn = ki.connect()
    print(f'  KoreaInvestmentBroker.connect() = {ki_conn}')
    ki_order = ki.submit_order('005930', 5, 'BUY')
    print(f'  KoreaInvestmentBroker.submit_order() = {ki_order}')
    
    kw = KiwoomBroker()
    kw_conn = kw.connect()
    print(f'  KiwoomBroker.connect() = {kw_conn}')
    kw_order = kw.submit_order('005930', 5, 'BUY')
    print(f'  KiwoomBroker.submit_order() = {kw_order}')
    
    results['broker'] = 'PASS'
except Exception as e:
    print(f'  FAIL: {e}')
    import traceback; traceback.print_exc()
    results['broker'] = f'FAIL: {e}'

# Summary
print('\n' + '=' * 60)
print('RESULTS SUMMARY')
print('=' * 60)
all_pass = True
for name, status in results.items():
    icon = 'v' if status == 'PASS' else 'x'
    print(f'  {icon} {name}: {status}')
    if status != 'PASS':
        all_pass = False

print()
if all_pass:
    print('ALL ACCEPTANCE CRITERIA PASSED - VICTORY!')
else:
    print('SOME CRITERIA FAILED - see above')
    sys.exit(1)
