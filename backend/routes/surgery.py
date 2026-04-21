"""/api/surgery/* — weight orthogonalization. Phase 2."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/surgery", tags=["surgery"])

_PHASE_2_MESSAGE = (
    "Weight surgery is implemented in phase 2 of the NeuralScope roadmap."
)


def _deferred() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_PHASE_2_MESSAGE,
    )


@router.post("/preview")
async def preview_surgery() -> dict:
    _deferred()


@router.post("/apply")
async def apply_surgery() -> dict:
    _deferred()


@router.post("/undo")
async def undo_surgery() -> dict:
    _deferred()


@router.get("/metrics")
async def get_metrics() -> dict:
    _deferred()
