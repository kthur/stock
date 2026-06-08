import sys
try:
    import dash
    dash_status = f"installed: {dash.__version__}"
except ImportError:
    dash_status = "not installed"

print(f"python: {sys.executable}")
print(f"dash: {dash_status}")
