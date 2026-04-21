"""/api/analyze/* — refusal analysis. Phase 2."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

_PHASE_2_MESSAGE = (
    "Refusal analysis is implemented in phase 2 of the NeuralScope roadmap."
)


@router.post("/refusal")
async def start_refusal_analysis() -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_PHASE_2_MESSAGE,
    )


@router.get("/refusal/results")
async def get_refusal_results() -> dict:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_PHASE_2_MESSAGE,
    )
