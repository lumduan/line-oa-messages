# === Builder stage ===
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# === Runtime stage ===
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src/ ./src/

# SQLite database lives here; mount as a volume to persist across restarts.
RUN mkdir -p /app/data

ENV PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1

# 9990 = LINE webhook (FastAPI) · 9991 = dashboard (NiceGUI)
EXPOSE 9990 9991

CMD ["python", "-m", "src.main"]
