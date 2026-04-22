"""/api/surgery/* — permanent weight orthogonalization + undo + snapshots."""

from __future__ import annotations

import logging
from typing import Optional

import torch
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.session import NoModelLoadedError, session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/surgery", tags=["surgery"])


class ApplyRequest(BaseModel):
    layers: list[int] = Field(..., description="Layer indices to orthogonalize.")
    intensity: float = Field(1.0, ge=0.0, le=3.0)
    norm_preserve: bool = Field(True)
    target_filter: Optional[list[str]] = Field(
        None,
        description="Keywords to match against weight-matrix names (default: down_proj/o_proj/c_proj).",
    )
    direction: Optional[list[float]] = Field(
        None,
        description="Unit refusal direction. If omitted, use the best-layer direction from the last analysis.",
    )
    layer_for_direction: Optional[int] = Field(
        None,
        description="If direction is omitted, use the per-layer direction from this layer of the last analysis.",
    )


class PreviewRequest(BaseModel):
    prompt: str
    max_new_tokens: int = Field(120, ge=1, le=1024)


class SnapshotRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class DiffRequest(BaseModel):
    name_a: str
    name_b: Optional[str] = None


@router.post("/apply")
async def apply_surgery(payload: ApplyRequest) -> dict:
    try:
        engine = session.surgery_engine()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    direction = _resolve_direction(payload.direction, payload.layer_for_direction)

    try:
        report = engine.orthogonalize(
            direction=direction,
            layer_indices=payload.layers,
            intensity=payload.intensity,
            norm_preserve=payload.norm_preserve,
            target_name_filter=payload.target_filter,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return {"status": "applied", **report}


@router.post("/undo")
async def undo_surgery() -> dict:
    try:
        engine = session.surgery_engine()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return engine.undo()


@router.post("/preview")
async def preview_on_prompt(payload: PreviewRequest) -> dict:
    try:
        steering = session.steering_engine()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    # Preview with no active steering vectors simply generates from the
    # current (possibly-modified) model weights.
    steering.clear()
    response = steering.generate(payload.prompt, max_new_tokens=payload.max_new_tokens)
    return {"prompt": payload.prompt, "response": response}


@router.get("/snapshots")
async def list_snapshots() -> dict:
    try:
        manager = session.snapshot_manager()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"snapshots": manager.list()}


@router.post("/snapshots")
async def save_snapshot(payload: SnapshotRequest) -> dict:
    manager = session.snapshot_manager()
    return manager.save(payload.name)


@router.post("/snapshots/{name}/rollback")
async def rollback_snapshot(name: str) -> dict:
    try:
        return session.snapshot_manager().rollback(name)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/snapshots/diff")
async def diff_snapshots(payload: DiffRequest) -> dict:
    try:
        return session.snapshot_manager().diff(payload.name_a, payload.name_b)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


def _resolve_direction(
    direction: Optional[list[float]], layer_for_direction: Optional[int]
) -> torch.Tensor:
    if direction is not None:
        return torch.tensor(direction, dtype=torch.float32)

    analysis = session.last_analysis()
    if analysis is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No refusal direction provided and no prior analysis found. "
            "Run /api/analyze/refusal first or pass 'direction' in the body.",
        )

    if layer_for_direction is None:
        return torch.tensor(analysis.global_direction, dtype=torch.float32)

    per_layer = analysis.refusal_directions.get(layer_for_direction)
    if per_layer is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No refusal direction for layer {layer_for_direction} in the last analysis.",
        )
    return torch.tensor(per_layer, dtype=torch.float32)
