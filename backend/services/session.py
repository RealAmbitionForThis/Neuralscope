"""Process-wide session state holding engines bound to the active model."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from backend.services.activation_engine import ActivationEngine
from backend.services.model_manager import LoadedModel, model_manager
from backend.services.refusal_analyzer import (
    RefusalAnalysisResult,
    RefusalAnalyzer,
)
from backend.services.snapshot_manager import SnapshotManager
from backend.services.steering_engine import SteeringEngine
from backend.services.surgery_engine import SurgeryEngine

logger = logging.getLogger(__name__)


class NoModelLoadedError(Exception):
    pass


class SessionState:
    """Lazily-constructed engines bound to the currently loaded model.

    Cleared whenever the active model changes or is unloaded.
    """

    def __init__(self) -> None:
        self._model_signature: Optional[str] = None
        self._activation_engine: Optional[ActivationEngine] = None
        self._refusal_analyzer: Optional[RefusalAnalyzer] = None
        self._surgery_engine: Optional[SurgeryEngine] = None
        self._steering_engine: Optional[SteeringEngine] = None
        self._snapshot_manager: Optional[SnapshotManager] = None
        self._last_analysis: Optional[RefusalAnalysisResult] = None
        self._lock = asyncio.Lock()

    def _current(self) -> LoadedModel:
        loaded = model_manager.get()
        if loaded is None:
            raise NoModelLoadedError("No model is currently loaded.")
        signature = f"{loaded.model_id}@{loaded.loaded_at}"
        if signature != self._model_signature:
            self._reset(signature)
        return loaded

    def _reset(self, signature: str) -> None:
        logger.info("session reset for model %s", signature)
        self._model_signature = signature
        self._activation_engine = None
        self._refusal_analyzer = None
        self._surgery_engine = None
        self._steering_engine = None
        self._snapshot_manager = None
        self._last_analysis = None

    def activation_engine(self) -> ActivationEngine:
        loaded = self._current()
        if self._activation_engine is None:
            self._activation_engine = ActivationEngine(
                loaded.model, loaded.tokenizer, loaded.structure_map
            )
        return self._activation_engine

    def refusal_analyzer(self) -> RefusalAnalyzer:
        if self._refusal_analyzer is None:
            self._refusal_analyzer = RefusalAnalyzer(self.activation_engine())
        return self._refusal_analyzer

    def surgery_engine(self) -> SurgeryEngine:
        loaded = self._current()
        if self._surgery_engine is None:
            self._surgery_engine = SurgeryEngine(loaded.model, loaded.structure_map)
        return self._surgery_engine

    def steering_engine(self) -> SteeringEngine:
        loaded = self._current()
        if self._steering_engine is None:
            self._steering_engine = SteeringEngine(
                loaded.model, loaded.tokenizer, loaded.structure_map
            )
        return self._steering_engine

    def snapshot_manager(self) -> SnapshotManager:
        loaded = self._current()
        if self._snapshot_manager is None:
            self._snapshot_manager = SnapshotManager(loaded.model, loaded.structure_map)
        return self._snapshot_manager

    def save_analysis(self, result: RefusalAnalysisResult) -> None:
        self._last_analysis = result

    def last_analysis(self) -> Optional[RefusalAnalysisResult]:
        self._current()  # refresh if model changed
        return self._last_analysis

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock


session = SessionState()
