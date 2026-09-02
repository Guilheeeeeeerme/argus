# syntax=docker/dockerfile:1
# Multi-target Dockerfile for all ARGUS backend deployables.
# Build: docker build --target api-admin -f docker/Dockerfile -t argus-api-admin .

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

ENV PYTHONPATH=/app/src

COPY requirements.txt pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY alembic ./alembic
COPY scripts ./scripts

CMD ["python", "-m", "argus.main"]

# ── HTTP services ──────────────────────────────────────────────────────────

FROM base AS api-admin
ENV SERVICE_ROLE=api-admin API_PORT=8000
EXPOSE 8000

FROM base AS api-ingest
ENV SERVICE_ROLE=api-ingest API_PORT=8001
EXPOSE 8001

FROM base AS ws-gateway
ENV SERVICE_ROLE=ws-gateway API_PORT=8002
EXPOSE 8002

# ── Workers (SERVICE_ROLE overridden in compose) ───────────────────────────

FROM base AS worker
