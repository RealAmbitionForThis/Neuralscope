"""Native FastAPI WebSocket connection manager with broadcast support."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Tracks active WebSocket clients and broadcasts typed events to them.

    Events have the shape ``{"event": str, "data": Any}``. Known events:
      - ``model:loading`` ``{status, progress, message}``
      - ``model:ready`` ``{model_id, map}``
      - ``model:error`` ``{message}``
      - ``model:unloaded`` ``{freed_gb}``
      - ``gpu:stats`` ``{gpus: [...]}``
    """

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        logger.info("ws client connected (total=%d)", len(self._clients))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)
        logger.info("ws client disconnected (total=%d)", len(self._clients))

    async def broadcast(self, event: str, data: Any) -> None:
        """Send an event to every connected client; silently drop dead sockets."""
        payload = {"event": event, "data": data}
        async with self._lock:
            clients = list(self._clients)

        if not clients:
            return

        results = await asyncio.gather(
            *(self._safe_send(client, payload) for client in clients),
            return_exceptions=False,
        )
        dead = [client for client, ok in zip(clients, results) if not ok]
        if dead:
            async with self._lock:
                for client in dead:
                    self._clients.discard(client)

    async def _safe_send(self, websocket: WebSocket, payload: dict) -> bool:
        try:
            await websocket.send_json(payload)
            return True
        except Exception as exc:
            logger.debug("ws send failed, dropping client: %s", exc)
            return False

    @property
    def client_count(self) -> int:
        return len(self._clients)


ws_manager = WebSocketManager()
