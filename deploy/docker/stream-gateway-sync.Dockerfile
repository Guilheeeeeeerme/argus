# Build from the monorepo root:
#   docker build -f deploy/docker/stream-gateway-sync.Dockerfile --build-arg GIT_SHA=<sha> .
# Ported from infra/containers/argus/stream-gateway-sync.Dockerfile:
# tiny httpx/pyyaml sidecar that keeps go2rtc config streams in sync with the API.
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY deploy/probe/pipeline_health.py /app/pipeline_health.py
RUN pip install --no-cache-dir 'httpx>=0.28.0' 'pyyaml>=6.0.0,<7'
COPY services/stream-gateway/sync.py /app/sync.py

ENV PYTHONUNBUFFERED=1
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

USER 10001:10001
CMD ["python", "-u", "/app/sync.py"]
