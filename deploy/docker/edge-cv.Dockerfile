# Build from the monorepo root:
#   docker build -f deploy/docker/edge-cv.Dockerfile --build-arg GIT_SHA=<sha> .
# Ported from infra/containers/argus/edge-cv.Dockerfile (self-contained).
# Install CPU torch explicitly (TensorRT disabled in production).
FROM python:3.12-slim-bookworm

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 \
    --index-url https://download.pytorch.org/whl/cpu

COPY deploy/probe/pipeline_health.py /app/pipeline_health.py
COPY services/edge-cv/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/src/argus/services/sensor_fusion.py /app/argus/services/sensor_fusion.py
COPY services/edge-cv/src/argus_edge_cv /app/argus_edge_cv

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    EDGE_TENSORRT_ENABLED=false \
    EDGE_YOLO_MODEL=/opt/models/yolov8n.pt \
    TORCH_HOME=/opt/models/torch \
    YOLO_CONFIG_DIR=/tmp/ultralytics \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1
ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

# Download weights once in CI and exercise both real CPU inference paths.
RUN mkdir -p /opt/models \
    && cd /opt/models \
    && python -c "from ultralytics import YOLO; YOLO('yolov8n.pt'); from torchvision.models import resnet18, ResNet18_Weights; resnet18(weights=ResNet18_Weights.DEFAULT)" \
    && chmod -R a+rX /opt/models \
    && rm -rf /tmp/ultralytics

USER 10001:10001
RUN python -c "import numpy as np; from argus_edge_cv.detector import YOLODetector, ResNetEmbedder; frame=np.zeros((128,128,3),dtype=np.uint8); YOLODetector('/opt/models/yolov8n.pt').detect(frame,('build','smoke','camera')); assert ResNetEmbedder()(frame).shape == (512,)"

CMD ["python", "-m", "argus_edge_cv"]
