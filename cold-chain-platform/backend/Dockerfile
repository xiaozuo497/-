FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY alembic ./alembic
COPY alembic.ini ./
COPY app ./app

CMD ["sh", "-c", "alembic upgrade head && (python -m app.backup --quiet || true) && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
