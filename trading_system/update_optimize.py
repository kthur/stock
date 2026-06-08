import re

with open("src/analysis/backtest.py", "r", encoding="utf-8") as f:
    content = f.read()

replacement = """    def optimize_parameters(self, symbol: str, price_bars: List[PriceBar],
                           param_ranges: Dict, strategy_name: str = "MA") -> Dict:
        \"\"\"파라미터 최적화 (캐싱 포함)\"\"\"
        best_result = None
        best_params = None
        best_return = -float('inf')
        
        self.logger.info(f"Starting parameter optimization for {strategy_name}...")
        
        import json
        import os
        
        cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, 'optimized_params.json')
        
        cache_key = f"{symbol}_{strategy_name}"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    # Check if ranges match (simplified check)
                    # In real scenario we might check more, but let's just proceed to optimize if ranges differ or just overwrite.
            except Exception:
                pass

        strategy_func = self.get_strategy_func(strategy_name)
        
        # 간단한 그리드 서치
        for param_combo in self._generate_param_combos(param_ranges):
            def strategy(bars):
                # 파라미터 기반 전략 실행
                return strategy_func(bars, param_combo)
            
            result = self.run_backtest(symbol, price_bars, strategy)
            
            if result.total_return_pct > best_return:
                best_return = result.total_return_pct
                best_result = result
                best_params = param_combo
        
        self.logger.info(f"Optimization complete: best params={best_params}, "
                        f"best return={best_return:.2f}%")
        
        # Save to cache
        cache_data = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
            except Exception:
                cache_data = {}
        
        cache_data[cache_key] = {
            'best_params': best_params,
            'best_return': best_return,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=4)
        
        return {
            'best_params': best_params,
            'best_result': best_result,
            'best_return': best_return
        }"""

pattern = r"    def optimize_parameters\(self, symbol: str, price_bars: List\[PriceBar\],\n                           param_ranges: Dict\) -> Dict:\n        \"\"\"파라미터 최적화\"\"\"\n        best_result = None\n        best_params = None\n        best_return = -float\('inf'\)\n        \n        self\.logger\.info\(\"Starting parameter optimization\.\.\.\"\)\n        \n        # 간단한 그리드 서치\n        for param_combo in self\._generate_param_combos\(param_ranges\):\n            def strategy\(bars\):\n                # 파라미터 기반 전략 실행\n                return self\._simple_ma_strategy\(bars, param_combo\)\n            \n            result = self\.run_backtest\(symbol, price_bars, strategy\)\n            \n            if result\.total_return_pct > best_return:\n                best_return = result\.total_return_pct\n                best_result = result\n                best_params = param_combo\n        \n        self\.logger\.info\(f\"Optimization complete: best params=\{best_params\}, \"\n                        f\"best return=\{best_return:\.2f\}%\"\)\n        \n        return \{\n            'best_params': best_params,\n            'best_result': best_result,\n            'best_return': best_return\n        \}"

new_content, count = re.subn(pattern, replacement, content)
if count > 0:
    with open("src/analysis/backtest.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Replaced optimize_parameters successfully!")
else:
    print("Failed to match optimize_parameters pattern.")
