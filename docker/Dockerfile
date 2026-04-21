# NeuralScope — CUDA-enabled image for local GPU servers.
# Phase 1: builds both services from source. Phase 4 will publish pre-built
# images to Docker Hub / GHCR.
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3-pip \
      ca-certificates curl git build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# ---- Backend ----
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r backend/requirements.txt

# ---- Frontend build ----
COPY frontend/package.json frontend/package.json
WORKDIR /app/frontend
RUN npm install --silent
COPY frontend/ .
RUN npm run build

# ---- Copy backend source ----
WORKDIR /app
COPY backend/ backend/

EXPOSE 3000 8000

# Start both services; uvicorn binds to 8000, next start to 3000.
CMD ["bash", "-lc", "\
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 & \
  cd frontend && npm run start -- -p 3000 & \
  wait -n"]
