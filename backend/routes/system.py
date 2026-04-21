"""/api/system/* — health check and GPU telemetry."""

from fastapi import APIRouter

from backend.services.gpu_monitor import get_gpu_info

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/gpu")
async def gpu() -> dict:
    return {"gpus": get_gpu_info()}
