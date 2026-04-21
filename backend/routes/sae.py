"""/api/sae/* — Sparse Autoencoder feature decomposition. Phase 3."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/sae", tags=["sae"])

_PHASE_3_MESSAGE = (
    "SAE feature browsing is implemented in phase 3 of the NeuralScope roadmap."
)


def _deferred() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_PHASE_3_MESSAGE,
    )


@router.post("/load")
async def load_sae() -> dict:
    _deferred()


@router.get("/features")
async def list_features() -> dict:
    _deferred()


@router.get("/features/{feature_id}")
async def get_feature(feature_id: int) -> dict:
    _deferred()


@router.get("/map")
async def feature_map() -> dict:
    _deferred()


@router.post("/label")
async def label_features() -> dict:
    _deferred()
