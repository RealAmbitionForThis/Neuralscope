"""/api/sae/* — SAE loading, feature browsing, UMAP map, auto-labeling."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.feature_labeler import get_feature_labeler
from backend.services.sae_engine import sae_engine
from backend.services.session import session
from backend.services.visualization import compute_feature_map
from backend.ws.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sae", tags=["sae"])

_FEATURE_MAP_CACHE: dict[str, dict] = {}


class LoadRequest(BaseModel):
    release: str = Field(..., description="SAELens release id (e.g. gpt2-small-res-jb).")
    sae_id: str = Field(..., description="SAE within the release (e.g. blocks.6.hook_resid_pre).")
    layer: int = Field(..., ge=0, description="Model layer this SAE was trained on.")
    device: str = Field("cpu", description="cpu or cuda")


class FeatureMapRequest(BaseModel):
    n_clusters: int = Field(50, ge=2, le=500)
    subsample: Optional[int] = Field(
        None,
        description="Cap features used for UMAP. Useful for 65k+ feature SAEs.",
    )


class LabelRequest(BaseModel):
    feature_ids: list[int] = Field(..., min_length=1)
    examples_per_feature: int = Field(8, ge=1, le=32)


class SingleLabelRequest(BaseModel):
    feature_id: int = Field(..., ge=0)
    label: str
    category: Optional[str] = None


@router.post("/load")
async def load_sae(payload: LoadRequest) -> dict:
    try:
        return sae_engine.load(
            release=payload.release,
            sae_id=payload.sae_id,
            layer=payload.layer,
            device=payload.device,
        )
    except Exception as exc:
        logger.exception("SAE load failed")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/info")
async def sae_info() -> dict:
    loaded = sae_engine.loaded
    if loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No SAE is loaded.")
    return {
        "release": loaded.release,
        "sae_id": loaded.sae_id,
        "layer": loaded.layer,
        "d_in": loaded.d_in,
        "d_sae": loaded.d_sae,
        "labeled_count": len(loaded.feature_labels),
    }


@router.get("/features")
async def list_features(
    page: int = 0, page_size: int = 100, search: Optional[str] = None
) -> dict:
    if sae_engine.loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No SAE is loaded.")
    return sae_engine.list_features(page=page, page_size=page_size, search=search)


@router.get("/features/{feature_id}")
async def get_feature(feature_id: int) -> dict:
    if sae_engine.loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No SAE is loaded.")
    try:
        return sae_engine.feature_info(feature_id)
    except IndexError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/map")
async def build_feature_map(payload: FeatureMapRequest) -> dict:
    loaded = sae_engine.loaded
    if loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No SAE is loaded.")

    cache_key = f"{loaded.release}:{loaded.sae_id}:{payload.n_clusters}:{payload.subsample}"
    if cache_key in _FEATURE_MAP_CACHE:
        return _FEATURE_MAP_CACHE[cache_key]

    loop = asyncio.get_running_loop()

    def run_map() -> dict:
        return compute_feature_map(
            decoder_weights=loaded.decoder_weights.numpy().astype(np.float32),
            n_clusters=payload.n_clusters,
            subsample=payload.subsample,
        )

    await ws_manager.broadcast(
        "sae:progress", {"progress": 0.05, "message": "Computing UMAP..."}
    )

    try:
        result = await asyncio.to_thread(run_map)
    except Exception as exc:
        logger.exception("UMAP failed")
        await ws_manager.broadcast("sae:error", {"message": str(exc)})
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    _FEATURE_MAP_CACHE[cache_key] = result
    await ws_manager.broadcast(
        "sae:progress", {"progress": 1.0, "message": "Map ready."}
    )
    return result


@router.post("/label/manual")
async def label_feature_manually(payload: SingleLabelRequest) -> dict:
    if sae_engine.loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No SAE is loaded.")
    sae_engine.label(payload.feature_id, payload.label, payload.category)
    return {"status": "labeled", "feature_id": payload.feature_id}


@router.post("/label")
async def auto_label(payload: LabelRequest) -> dict:
    """Auto-label a batch of features using Qwen3-0.6B."""
    loaded_sae = sae_engine.loaded
    if loaded_sae is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No SAE is loaded.")
    try:
        activation_engine = session.activation_engine()
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    from backend.routes.analyze import _load_bundled
    prompts = _load_bundled("harmless_prompts.json") + _load_bundled("harmful_prompts.json")
    if not prompts:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No bundled prompts available; cannot auto-label.",
        )

    loop = asyncio.get_running_loop()

    def collect_examples() -> dict[int, dict]:
        out: dict[int, dict] = {}
        for fid in payload.feature_ids:
            top = sae_engine.top_activating_examples(
                fid, prompts, activation_engine, top_k=payload.examples_per_feature
            )
            out[fid] = {"top_texts": [t["prompt"] for t in top]}
        return out

    def emit(progress: float, message: str) -> None:
        if loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                ws_manager.broadcast(
                    "sae:label_progress",
                    {"progress": progress, "message": message},
                ),
                loop,
            )
        except RuntimeError:
            pass

    def run() -> dict:
        emit(0.05, "Collecting top activating examples...")
        data = collect_examples()
        emit(0.4, "Loading labeler model (Qwen3-0.6B)...")
        labeler = get_feature_labeler()
        labels = labeler.label_batch(data, progress=lambda p, m: emit(0.4 + 0.6 * p, m))
        for feature_id, label in labels.items():
            sae_engine.label(feature_id, label)
        return labels

    try:
        labels = await asyncio.to_thread(run)
    except Exception as exc:
        logger.exception("auto-label failed")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    return {"labels": labels, "labeled_count": len(labels)}
