"""/api/model/* — load, inspect, and unload the active model."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.model_manager import (
    QUANTIZATION_CHOICES,
    ModelLoadError,
    model_manager,
)

router = APIRouter(prefix="/api/model", tags=["model"])


class LoadRequest(BaseModel):
    model_id: str = Field(..., description="HuggingFace model id (e.g. 'gpt2').")
    quantization: str = Field("fp16", description=f"One of: {QUANTIZATION_CHOICES}")
    max_memory: Optional[dict[str, str]] = Field(
        None,
        description="Optional per-device memory cap (e.g. {'0': '70GB'}).",
    )


class LoadResponse(BaseModel):
    status: str
    model_id: str


@router.post("/load", response_model=LoadResponse)
async def load_model(payload: LoadRequest) -> LoadResponse:
    try:
        loaded = await model_manager.load(payload.model_id, payload.quantization)
    except ModelLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return LoadResponse(status="ready", model_id=loaded.model_id)


@router.get("/info")
async def model_info() -> dict:
    loaded = model_manager.get()
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No model is currently loaded.",
        )

    structure = loaded.structure_map
    return {
        "model_id": loaded.model_id,
        "quantization": loaded.quantization,
        "loaded_at": loaded.loaded_at,
        "model_type": structure.get("model_type"),
        "architecture": structure.get("architecture"),
        "n_layers": structure.get("n_layers"),
        "hidden_size": structure.get("hidden_size"),
        "total_parameters": structure.get("total_parameters"),
        "total_size_gb": structure.get("total_size_gb"),
        "devices": structure.get("devices"),
    }


@router.get("/map")
async def model_map() -> dict:
    loaded = model_manager.get()
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No model is currently loaded.",
        )
    return loaded.structure_map


@router.post("/unload")
async def unload_model() -> dict:
    return await model_manager.unload()
