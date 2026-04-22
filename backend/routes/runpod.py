"""/api/runpod/* — launch, monitor, and manage RunPod instances."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.runpod_service import (
    DEFAULT_IMAGE,
    RunPodError,
    RunPodService,
    build_proxy_url,
)

router = APIRouter(prefix="/api/runpod", tags=["runpod"])

# Single in-memory client bound to the most-recently configured API key.
# In a multi-user deployment this would move to per-session storage.
_service: Optional[RunPodService] = None


class ConnectRequest(BaseModel):
    api_key: str = Field(..., min_length=8)


class LaunchRequest(BaseModel):
    name: str = Field("neuralscope")
    gpu_type_ids: list[str] = Field(
        default_factory=lambda: ["NVIDIA A100 80GB PCIe"]
    )
    gpu_count: int = Field(1, ge=1, le=8)
    image: str = Field(DEFAULT_IMAGE)
    volume_gb: int = Field(100, ge=10, le=10000)
    container_disk_gb: int = Field(50, ge=10, le=2000)
    env: Optional[dict[str, str]] = None


@router.post("/connect")
async def connect(payload: ConnectRequest) -> dict:
    global _service
    if _service is not None:
        await _service.close()
    _service = RunPodService(api_key=payload.api_key)
    try:
        gpus = await _service.list_gpus()
    except RunPodError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"status": "connected", "gpu_types_available": len(gpus)}


@router.get("/gpus")
async def list_gpus() -> dict:
    service = _require_service()
    return {"gpus": await service.list_gpus()}


@router.get("/pods")
async def list_pods() -> dict:
    service = _require_service()
    return {"pods": await service.list_pods()}


@router.post("/launch")
async def launch(payload: LaunchRequest) -> dict:
    service = _require_service()
    try:
        pod = await service.create_pod(
            name=payload.name,
            gpu_type_ids=payload.gpu_type_ids,
            gpu_count=payload.gpu_count,
            image=payload.image,
            container_disk_gb=payload.container_disk_gb,
            volume_gb=payload.volume_gb,
            env=payload.env,
        )
    except RunPodError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    pod_id = pod.get("id") or pod.get("podId")
    return {
        "pod_id": pod_id,
        "pod": pod,
        "frontend_url": build_proxy_url(pod_id, 3000) if pod_id else None,
        "backend_url": build_proxy_url(pod_id, 8000) if pod_id else None,
    }


@router.get("/pods/{pod_id}")
async def get_pod(pod_id: str) -> dict:
    service = _require_service()
    try:
        return await service.get_pod(pod_id)
    except RunPodError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/pods/{pod_id}/stop")
async def stop_pod(pod_id: str) -> dict:
    service = _require_service()
    try:
        return await service.stop_pod(pod_id)
    except RunPodError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/pods/{pod_id}/terminate")
async def terminate_pod(pod_id: str) -> dict:
    service = _require_service()
    try:
        return await service.terminate_pod(pod_id)
    except RunPodError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


def _require_service() -> RunPodService:
    if _service is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "RunPod API key not set. POST /api/runpod/connect first.",
        )
    return _service
