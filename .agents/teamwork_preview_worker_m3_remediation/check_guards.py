import os

for phase in range(25, 40):
    p = f"trading_system/scripts/benchmark_phase{phase}_quant_performance.py"
    if not os.path.exists(p):
        print(f"Phase {phase}: FILE NOT FOUND")
        continue
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
    has_guard = 'if __name__ == "__main__":' in content
    # Also find where content = "\n".join(lines) is
    unindented_content = '\ncontent = "\\n".join(lines)' in content
    indented_content = '    content = "\\n".join(lines)' in content
    print(f"Phase {phase}: has_guard={has_guard}, indented={indented_content}, unindented={unindented_content}")
