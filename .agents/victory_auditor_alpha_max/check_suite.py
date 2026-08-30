import sys, os  
sys.path.insert(0, 'trading_system')  
sys.path.insert(0, 'trading_system/src')  
sys.path.insert(0, '.')  
from src.core.strategy_registry import get_registry  
reg = get_registry()  
reg.auto_discover(['src.core', 'src.ai'])  
print('REGISTERED_COUNT:', len(reg.get_all_ids()))  
from src.ai.ensemble_scorer import EnsembleScoringEngine  
scorer = EnsembleScoringEngine()  
print('REGIME_2D_SUMS:', {k: round(sum(v.values()), 6) for k, v in scorer.REGIME_2D_WEIGHTS.items()})  
print('REGIME_1D_SUMS:', {k: round(sum(v.values()), 6) for k, v in scorer.REGIME_WEIGHTS.items()})  
