# Build from the monorepo root. Install CPU torch explicitly (TensorRT disabled).
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
COPY services/edge-cv/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/src/argus/services/sensor_fusion.py /app/argus/services/sensor_fusion.py
COPY services/edge-cv/src/argus_edge_cv /app/argus_edge_cv
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 EDGE_CV_ENABLED=false EDGE_TENSORRT_ENABLED=false
CMD ["python", "-m", "argus_edge_cv"]
