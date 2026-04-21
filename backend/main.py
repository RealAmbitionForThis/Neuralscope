"""NeuralScope FastAPI entry point.

Mounts REST routes, a native WebSocket endpoint at ``/ws``, and a background
task that pushes ``gpu:stats`` events every ``gpu_stats_interval_seconds``.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routes import analyze, export, model, sae, surgery, system
from backend.services.gpu_monitor import get_gpu_info
from backend.ws.manager import ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("neuralscope")


@asynccontextmanager
async def lifespan(app: FastAPI):
    stats_task = asyncio.create_task(_gpu_stats_loop())
    logger.info("backend started")
    try:
        yield
    finally:
        stats_task.cancel()
        try:
            await stats_task
        except asyncio.CancelledError:
            pass
        logger.info("backend stopped")


async def _gpu_stats_loop() -> None:
    """Push GPU telemetry to every connected WebSocket client."""
    while True:
        try:
            if ws_manager.client_count > 0:
                await ws_manager.broadcast("gpu:stats", {"gpus": get_gpu_info()})
        except Exception:
            logger.exception("gpu stats broadcast failed")
        await asyncio.sleep(settings.gpu_stats_interval_seconds)


app = FastAPI(title="NeuralScope", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(model.router)
app.include_router(analyze.router)
app.include_router(sae.router)
app.include_router(surgery.router)
app.include_router(export.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(
            {"event": "gpu:stats", "data": {"gpus": get_gpu_info()}}
        )
        while True:
            # Clients don't need to send anything; we just hold the connection
            # open so the server can push progress events. Read and discard.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("websocket error")
    finally:
        await ws_manager.disconnect(websocket)


@app.get("/")
async def root() -> dict:
    return {"name": "NeuralScope", "version": "0.1.0", "docs": "/docs"}
