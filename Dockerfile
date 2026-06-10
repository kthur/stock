FROM python:3.11-slim

WORKDIR /app

COPY trading_system/pyproject.toml trading_system/requirements.txt /app/
RUN pip install --no-cache-dir -e .[dev]

COPY trading_system/ /app/

EXPOSE 5000 8000

CMD ["python", "run_dashboard.py"]
