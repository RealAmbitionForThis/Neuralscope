"""/api/export/* — safetensors / GGUF / HF Hub export. Phase 2."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/export", tags=["export"])

_PHASE_2_MESSAGE = (
    "Model export is implemented in phase 2 of the NeuralScope roadmap."
)


def _deferred() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_PHASE_2_MESSAGE,
    )


@router.post("/safetensors")
async def export_safetensors() -> dict:
    _deferred()


@router.post("/gguf")
async def export_gguf() -> dict:
    _deferred()


@router.post("/hub")
async def export_to_hub() -> dict:
    _deferred()
