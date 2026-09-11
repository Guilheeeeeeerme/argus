FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx pyyaml

COPY sync.py ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "sync.py"]
