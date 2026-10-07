# Build from the monorepo root:
#   docker build -f deploy/docker/stream-prep.Dockerfile --build-arg GIT_SHA=<sha> .
# Ported from infra/containers/argus/stream-prep.Dockerfile (self-contained).
# Pillow wheels on bookworm-slim need no extra system libs; no libmagic import
# in argus_stream_prep (verified by grep), so the apt layer stays empty —
# caching/decompressing is handled by Pillow itself.
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY deploy/probe/pipeline_health.py /app/pipeline_health.py
COPY services/stream-prep/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY services/stream-prep/src/argus_stream_prep /app/argus_stream_prep

RUN useradd --uid 10001 --user-group --create-home argus
USER 10001:10001
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

CMD ["python", "-m", "argus_stream_prep"]
