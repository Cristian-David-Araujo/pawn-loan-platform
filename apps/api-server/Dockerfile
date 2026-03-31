FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "if [ -f pyproject.toml ]; then pip install --no-cache-dir -e . && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload; elif [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload; else echo 'Missing pyproject.toml or requirements.txt in /app'; tail -f /dev/null; fi"]
