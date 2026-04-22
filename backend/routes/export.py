"""/api/export/* — safetensors, GGUF, and HF Hub export."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.exporter import (
    ExportError,
    export_gguf,
    export_safetensors,
    push_to_hub,
)
from backend.services.model_manager import model_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


class SafetensorsRequest(BaseModel):
    output_dir: Optional[str] = None
    name: Optional[str] = None


class GgufRequest(BaseModel):
    source_dir: str = Field(..., description="Path returned by /api/export/safetensors.")
    output_path: Optional[str] = None
    quantization: str = Field("F16", description="F16, F32, BF16, Q8_0, AUTO")
    llama_cpp_root: Optional[str] = None


class HubRequest(BaseModel):
    source_dir: str
    repo_id: str
    private: bool = True
    token: Optional[str] = None


@router.post("/safetensors")
async def export_as_safetensors(payload: SafetensorsRequest) -> dict:
    loaded = model_manager.get()
    if loaded is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No model is loaded.")

    try:
        return export_safetensors(
            model=loaded.model,
            tokenizer=loaded.tokenizer,
            output_dir=Path(payload.output_dir) if payload.output_dir else None,
            model_id=payload.name or loaded.model_id.replace("/", "__") + "-modified",
        )
    except Exception as exc:
        logger.exception("safetensors export failed")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/gguf")
async def export_as_gguf(payload: GgufRequest) -> dict:
    try:
        return export_gguf(
            source_dir=Path(payload.source_dir),
            output_path=Path(payload.output_path) if payload.output_path else None,
            llama_cpp_root=Path(payload.llama_cpp_root) if payload.llama_cpp_root else None,
            quantization=payload.quantization,
        )
    except ExportError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.post("/hub")
async def export_to_hub(payload: HubRequest) -> dict:
    try:
        return push_to_hub(
            source_dir=Path(payload.source_dir),
            repo_id=payload.repo_id,
            private=payload.private,
            token=payload.token,
        )
    except ExportError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
