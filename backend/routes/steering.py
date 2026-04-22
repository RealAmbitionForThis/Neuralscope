"""/api/steering/* — live (reversible) inference-time intervention."""

from __future__ import annotations

from typing import Optional

import torch
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.session import NoModelLoadedError, session

router = APIRouter(prefix="/api/steering", tags=["steering"])


class AddVectorRequest(BaseModel):
    layer: int = Field(..., ge=0)
    strength: float = Field(1.0, ge=-3.0, le=3.0)
    label: str = Field("refusal")
    direction: Optional[list[float]] = Field(
        None,
        description="Unit direction. If omitted, uses the best-layer direction from the last analysis.",
    )
    layer_for_direction: Optional[int] = Field(None)


class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = Field(160, ge=1, le=1024)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    top_p: float = Field(0.9, gt=0.0, le=1.0)


@router.post("/add")
async def add_steering_vector(payload: AddVectorRequest) -> dict:
    try:
        engine = session.steering_engine()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    direction_tensor = _resolve_direction(payload.direction, payload.layer_for_direction)

    engine.add_vector(
        layer=payload.layer,
        direction=direction_tensor,
        strength=payload.strength,
        label=payload.label,
    )
    return {"status": "added", "active": engine.active_vectors()}


@router.post("/clear")
async def clear_steering() -> dict:
    try:
        engine = session.steering_engine()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    engine.clear()
    return {"status": "cleared"}


@router.get("/active")
async def list_active() -> dict:
    try:
        engine = session.steering_engine()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"steerings": engine.active_vectors()}


@router.post("/generate")
async def generate_with_steering(payload: GenerateRequest) -> dict:
    try:
        engine = session.steering_engine()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    text = engine.generate(
        prompt=payload.prompt,
        max_new_tokens=payload.max_new_tokens,
        temperature=payload.temperature,
        top_p=payload.top_p,
    )
    return {
        "prompt": payload.prompt,
        "response": text,
        "steerings_applied": engine.active_vectors(),
    }


def _resolve_direction(
    direction: Optional[list[float]], layer_for_direction: Optional[int]
) -> torch.Tensor:
    if direction is not None:
        return torch.tensor(direction, dtype=torch.float32)

    analysis = session.last_analysis()
    if analysis is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No direction provided and no prior analysis exists.",
        )

    if layer_for_direction is None:
        return torch.tensor(analysis.global_direction, dtype=torch.float32)

    per_layer = analysis.refusal_directions.get(layer_for_direction)
    if per_layer is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No direction for layer {layer_for_direction}.",
        )
    return torch.tensor(per_layer, dtype=torch.float32)
