# Build from the monorepo root:
#   docker build -f deploy/docker/prompt-eval.Dockerfile --build-arg GIT_SHA=<sha> .
# Ported from infra/containers/argus/prompt-eval.Dockerfile (self-contained):
# prompt-eval service = the `argus_prompt_eval` package + the shared `argus`
# package (ORM/services) copied into the image (no bind mounts in prod).
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY deploy/probe/pipeline_health.py /app/pipeline_health.py
COPY services/prompt-eval/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Shared ORM + service package on PYTHONPATH=/app
COPY apps/api/src/argus /app/argus
COPY services/prompt-eval/src/argus_prompt_eval /app/argus_prompt_eval

RUN useradd --uid 10001 --user-group --create-home argus
USER 10001:10001
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

CMD ["python", "-m", "argus_prompt_eval"]
