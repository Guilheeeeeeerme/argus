# Build from the monorepo root:
#   docker build -f deploy/docker/api.Dockerfile --build-arg GIT_SHA=<sha> .
# Ported from infra/containers/argus/api.Dockerfile (self-contained; no shared
# deps image). CI also tags this image as `argus/worker:<tag>` (Celery runs the
# same app package with a different command — except worker, see
# infra/scripts/build.sh). The `migrate` one-shot service runs THIS image via
# deploy/migrate.sh, so the image carries deploy/ops/{ensure_grants,bootstrap}.py.
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY apps/api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/ ./
# Migration ops (migrate service only): deploy/migrate.sh + ensure_grants + bootstrap.
COPY deploy/migrate.sh /app/deploy/migrate.sh
COPY deploy/ops/ /app/deploy/ops/
RUN chmod 0755 /app/deploy/migrate.sh /app/deploy/ops/*.py \
    # The dev entrypoint migrates/seeds on start — it must never run in prod.
    && rm -f /app/docker-entrypoint.sh

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

# Plain uvicorn factory — NEVER migrates on start (alembic runs in `migrate`).
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "argus.apps.http:create_admin_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
