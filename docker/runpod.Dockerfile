# NeuralScope — RunPod-optimized image.
# Uses RunPod's pre-baked PyTorch image as base, which already has CUDA,
# cuDNN, and a compatible PyTorch build. We layer Node + frontend on top.
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r backend/requirements.txt

COPY frontend/package.json frontend/package.json
WORKDIR /app/frontend
RUN npm install --silent
COPY frontend/ .
RUN npm run build

WORKDIR /app
COPY backend/ backend/

EXPOSE 3000 8000

CMD ["bash", "-lc", "\
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 & \
  cd frontend && npm run start -- -p 3000 & \
  wait -n"]
