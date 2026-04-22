"""/api/analyze/* — contrastive-prompt refusal analysis."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.refusal_analyzer import RefusalAnalysisResult
from backend.services.session import NoModelLoadedError, session
from backend.ws.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

_DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"


class AnalyzeRequest(BaseModel):
    harmful_prompts: Optional[list[str]] = Field(
        None, description="Custom harmful prompts. If omitted, bundled defaults are used."
    )
    harmless_prompts: Optional[list[str]] = Field(
        None, description="Custom harmless prompts. If omitted, bundled defaults are used."
    )
    max_prompts: int = Field(
        25,
        ge=1,
        le=500,
        description="Truncate prompt lists to this size before running.",
    )


@router.post("/refusal")
async def start_refusal_analysis(payload: AnalyzeRequest) -> dict:
    try:
        analyzer = session.refusal_analyzer()
    except NoModelLoadedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    harmful = (payload.harmful_prompts or _load_bundled("harmful_prompts.json"))[: payload.max_prompts]
    harmless = (payload.harmless_prompts or _load_bundled("harmless_prompts.json"))[: payload.max_prompts]

    loop = asyncio.get_running_loop()

    def run_analysis() -> RefusalAnalysisResult:
        return analyzer.analyze(
            harmful_prompts=harmful,
            harmless_prompts=harmless,
            progress=lambda p, m: _emit_progress(loop, p, m),
        )

    async with session.lock:
        try:
            result = await asyncio.to_thread(run_analysis)
        except Exception as exc:
            logger.exception("refusal analysis failed")
            await ws_manager.broadcast("analyze:error", {"message": str(exc)})
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc

    session.save_analysis(result)
    await ws_manager.broadcast("analyze:complete", {"best_layer": result.best_layer})
    return {
        "status": "complete",
        "best_layer": result.best_layer,
        "n_harmful": len(harmful),
        "n_harmless": len(harmless),
    }


@router.get("/refusal/results")
async def get_refusal_results() -> dict:
    result = session.last_analysis()
    if result is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No analysis has been run for the current model. POST /api/analyze/refusal first.",
        )
    return result.to_dict()


@router.get("/datasets/defaults")
async def get_default_prompts() -> dict:
    return {
        "harmful": _load_bundled("harmful_prompts.json"),
        "harmless": _load_bundled("harmless_prompts.json"),
    }


def _load_bundled(filename: str) -> list[str]:
    path = _DATASETS_DIR / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def _emit_progress(loop: asyncio.AbstractEventLoop, progress: float, message: str) -> None:
    if loop.is_closed():
        return
    try:
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast(
                "analyze:progress",
                {"progress": progress, "message": message},
            ),
            loop,
        )
    except RuntimeError:
        pass
