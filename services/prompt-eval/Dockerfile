# Build from monorepo root:
#   docker build -f services/prompt-eval/Dockerfile .
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY services/prompt-eval/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Shared ORM + service package on PYTHONPATH=/app
COPY apps/api/src/argus /app/argus
COPY services/prompt-eval/src/argus_prompt_eval /app/argus_prompt_eval

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

CMD ["python", "-m", "argus_prompt_eval"]
