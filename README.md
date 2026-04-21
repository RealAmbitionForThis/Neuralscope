# NeuralScope

Self-hosted web app for loading any open-weight LLM, visualizing internal features via Sparse Autoencoders, identifying refusal behaviors, and surgically modifying model weights.

**Status:** Phase 1 — scaffolding + backend core + frontend shell. Refusal analysis, surgery, SAE integration, and RunPod integration land in subsequent phases.

## Architecture

```
frontend/   Next.js 14 App Router (JavaScript) — dark industrial UI, Zustand store
backend/    FastAPI + native WebSocket — model loading, architecture-agnostic introspection, GPU monitoring
docker/     CUDA + RunPod Dockerfiles
scripts/    launch.sh (local) and launch_runpod.py (remote)
```

The backend discovers model structure at load time via `ModelIntrospector` rather than hardcoding layer paths. This lets it work with Llama/Mistral/Qwen (`model.layers.{i}`), GPT-2/Falcon/Bloom (`transformer.h.{i}`), and custom architectures loaded with `trust_remote_code=True`.

## Phase 1 quickstart (local, CPU-compatible)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. Enter `gpt2` as the model id, pick `fp16`, click Load. Progress streams via WebSocket; when the model is ready the sidebar unlocks and the top bar shows architecture info.

Or use the launch script:

```bash
bash scripts/launch.sh
```

## Phase 1 endpoints

| Method | Path                        | Status         |
|--------|-----------------------------|----------------|
| GET    | `/api/system/health`        | implemented    |
| GET    | `/api/system/gpu`           | implemented    |
| POST   | `/api/model/load`           | implemented    |
| GET    | `/api/model/info`           | implemented    |
| GET    | `/api/model/map`            | implemented    |
| POST   | `/api/model/unload`         | implemented    |
| WS     | `/ws`                       | implemented    |
| *      | `/api/analyze/*`            | 501 (phase 2)  |
| *      | `/api/sae/*`                | 501 (phase 3)  |
| *      | `/api/surgery/*`            | 501 (phase 2)  |
| *      | `/api/export/*`             | 501 (phase 2)  |

## Phase roadmap

1. **Phase 1 (this commit):** scaffolding, backend core, frontend shell, GPT-2 testable on CPU
2. **Phase 2:** refusal analysis (diff-in-means, winsorization), surgery engine (orthogonalization), safetensors export, live inference steering
3. **Phase 3:** SAELens integration, UMAP feature map, Qwen3-0.6B auto-labeler, feature browser
4. **Phase 4:** RunPod integration, GGUF export via llama.cpp, snapshots + rollback, Docker Hub published images

## License

MIT — see [LICENSE](LICENSE).
