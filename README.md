# NeuralScope

Self-hosted web app for loading any open-weight LLM, visualizing internal features via Sparse Autoencoders, identifying refusal behaviors, and surgically modifying model weights.

**Status:** full stack shipped — refusal analysis, weight surgery, live steering, SAE feature browsing, RunPod integration, and safetensors/GGUF/Hub export all functional.

## What it does

1. **Load any LLM** (HuggingFace), including custom architectures with `trust_remote_code=True`.
2. **Introspect the architecture dynamically** — no hardcoded layer paths. Works on Llama, GPT-2, Mistral, Qwen, Gemma, Falcon, Bloom, MPT, and MoE variants.
3. **Identify refusal behavior** via diff-in-means with winsorization across a contrastive prompt set.
4. **Modify weights** (permanent, with undo) or **steer activations** (reversible, via hooks) to strip refusals.
5. **Browse SAE features** with a UMAP map + auto-labeling via Qwen3-0.6B.
6. **Export** to safetensors, GGUF (via llama.cpp), or push to HuggingFace Hub.
7. **Launch on RunPod** directly from the UI.

## Architecture

```
frontend/   Next.js 14 App Router (JavaScript) — dark industrial UI, Zustand store, D3 + canvas viz
backend/    FastAPI + native WebSocket — architecture-agnostic introspection, activation hooks,
            refusal analyzer, surgery engine, steering engine, SAE engine, RunPod REST client
docker/     CUDA + RunPod Dockerfiles
scripts/    launch.sh (local) and launch_runpod.py (remote)
```

The backend discovers model structure at load time via `ModelIntrospector`. Every downstream service (refusal analyzer, surgery, steering, SAE) consumes the resulting map and navigates via `layer_path_template` rather than hardcoding paths.

## Quickstart (local, CPU-compatible)

```bash
# One command:
bash scripts/launch.sh

# Or manually, in two terminals:
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000`, enter `gpt2` as the model id, pick `fp32`, click Load. The top bar shows architecture info, the sidebar unlocks, and you can walk through Analyze → Surgery → Features → Export.

## Quickstart on RunPod

```bash
python scripts/launch_runpod.py --api-key $RUNPOD_API_KEY
```

The script creates a pod, waits for it to be RUNNING, and prints the HTTP proxy URLs for the frontend (port 3000) and backend (port 8000). Paste the backend URL into Settings in any NeuralScope frontend.

Or from the running frontend: Settings → RunPod connection, paste your API key, pick a GPU type, launch.

## Endpoints

| Path                                | Purpose                                                |
|-------------------------------------|--------------------------------------------------------|
| `GET  /api/system/gpu`              | Per-GPU memory + utilization                           |
| `GET  /api/system/health`           | Health check                                           |
| `POST /api/model/load`              | Load a HuggingFace model (streams progress)            |
| `GET  /api/model/map`               | Introspected structure                                 |
| `POST /api/analyze/refusal`         | Diff-in-means refusal direction extraction             |
| `GET  /api/analyze/refusal/results` | Per-layer strengths, separability, directions          |
| `POST /api/surgery/apply`           | Permanent weight orthogonalization                     |
| `POST /api/surgery/undo`            | Restore from checkpoint                                |
| `GET  /api/surgery/snapshots`       | Named snapshots (save/rollback/diff)                   |
| `POST /api/steering/add`            | Add a live steering vector                             |
| `POST /api/steering/generate`       | Generate with steering vectors applied                 |
| `POST /api/sae/load`                | Load a pretrained SAELens SAE                          |
| `POST /api/sae/map`                 | UMAP feature map (cached)                              |
| `POST /api/sae/label`               | Auto-label features with Qwen3-0.6B                    |
| `POST /api/export/safetensors`      | Save modified model to disk                            |
| `POST /api/export/gguf`             | Convert via llama.cpp's convert_hf_to_gguf.py          |
| `POST /api/export/hub`              | Push to HuggingFace Hub                                |
| `POST /api/runpod/connect`          | Set RunPod API key                                     |
| `POST /api/runpod/launch`           | Launch a NeuralScope pod                               |
| `WS   /ws`                          | Progress events for every long-running job             |

## Design principles

- **Architecture-agnostic.** Nothing hardcodes `model.model.layers[i]`. Layer paths are discovered at load time; weight surgery detects axis conventions (nn.Linear vs GPT-2 Conv1D).
- **Architecture-correct math.** Orthogonalization math is `W_new = W - outer(r, r^T @ W)` (or the axis=1 equivalent for Conv1D), in fp32 even when weights are bf16, verified to ~1e-6 post-surgery projection on GPT-2.
- **Reversible by default.** Live steering is the recommended entry point; permanent surgery keeps a checkpoint for undo; snapshots allow named rollback.
- **Clean boundaries.** Every route calls a service; services don't touch FastAPI. The session state resets automatically when the active model changes.

## License

MIT — see [LICENSE](LICENSE).
