"""Singleton model manager: loads/unloads HuggingFace causal LMs.

Phase 1 uses raw ``transformers.AutoModelForCausalLM``. Phase 2 wraps the
already-loaded model with ``nnsight.NNsight(...)`` for activation tracing.

Progress events are pushed to every connected WebSocket client via
``ws_manager.broadcast``. See ``backend/ws/manager.py`` for the event schema.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from backend.services.model_introspector import introspect_model
from backend.ws.manager import ws_manager

logger = logging.getLogger(__name__)


QUANTIZATION_CHOICES = ("4bit", "8bit", "bf16", "fp16", "fp32")


@dataclass
class LoadedModel:
    model_id: str
    quantization: str
    model: Any
    tokenizer: Any
    structure_map: dict
    loaded_at: float = field(default_factory=time.time)


class ModelLoadError(Exception):
    """Raised for user-facing load failures; messages are safe to surface."""


class ModelManager:
    """Holds at most one loaded model at a time."""

    def __init__(self) -> None:
        self._loaded: Optional[LoadedModel] = None
        self._lock = asyncio.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._loaded is not None

    def get(self) -> Optional[LoadedModel]:
        return self._loaded

    async def load(self, model_id: str, quantization: str) -> LoadedModel:
        """Load a model, broadcasting progress to WebSocket clients."""
        if quantization not in QUANTIZATION_CHOICES:
            raise ModelLoadError(
                f"Unsupported quantization '{quantization}'. "
                f"Choose one of: {', '.join(QUANTIZATION_CHOICES)}"
            )

        loop = asyncio.get_running_loop()

        async with self._lock:
            if self._loaded is not None:
                await self._release_loaded()

            await self._emit_loading(0.02, f"Preparing to load {model_id}...")

            try:
                loaded = await asyncio.to_thread(
                    self._load_sync, model_id, quantization, loop
                )
            except ModelLoadError:
                raise
            except Exception as exc:
                message = _format_load_error(model_id, exc)
                await ws_manager.broadcast("model:error", {"message": message})
                raise ModelLoadError(message) from exc

            self._loaded = loaded
            await ws_manager.broadcast(
                "model:ready",
                {"model_id": model_id, "map": loaded.structure_map},
            )
            return loaded

    async def unload(self) -> dict:
        async with self._lock:
            if self._loaded is None:
                return {"status": "noop", "freed_gb": 0.0}
            freed = self._loaded.structure_map.get("total_size_gb", 0.0)
            await self._release_loaded()
            await ws_manager.broadcast("model:unloaded", {"freed_gb": freed})
            return {"status": "unloaded", "freed_gb": freed}

    async def _release_loaded(self) -> None:
        self._loaded = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    async def _emit_loading(self, progress: float, message: str) -> None:
        await ws_manager.broadcast(
            "model:loading",
            {"status": "loading", "progress": progress, "message": message},
        )

    def _load_sync(
        self,
        model_id: str,
        quantization: str,
        loop: asyncio.AbstractEventLoop,
    ) -> LoadedModel:
        """Blocking load path; run in a worker thread from ``load``."""
        _notify_progress(loop, 0.05, "Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=True
        )

        _notify_progress(loop, 0.15, "Resolving quantization config...")
        load_kwargs = _build_load_kwargs(quantization)

        _notify_progress(
            loop,
            0.25,
            f"Downloading and loading weights ({quantization})...",
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            **load_kwargs,
        )
        model.eval()

        _notify_progress(loop, 0.85, "Introspecting model architecture...")
        structure_map = introspect_model(model)

        _notify_progress(loop, 0.98, "Ready.")
        return LoadedModel(
            model_id=model_id,
            quantization=quantization,
            model=model,
            tokenizer=tokenizer,
            structure_map=structure_map,
        )


def _notify_progress(
    loop: asyncio.AbstractEventLoop,
    progress: float,
    message: str,
) -> None:
    """Fire-and-forget progress notification from a worker thread."""
    if loop.is_closed():
        return
    payload = {"status": "loading", "progress": progress, "message": message}
    try:
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast("model:loading", payload),
            loop,
        )
    except RuntimeError as exc:
        logger.debug("progress broadcast skipped: %s", exc)


def _build_load_kwargs(quantization: str) -> dict:
    """Translate a quantization choice into ``from_pretrained`` kwargs."""
    if torch.cuda.is_available():
        kwargs: dict = {"device_map": "auto"}
    else:
        kwargs = {"device_map": "cpu"}

    if quantization in ("4bit", "8bit"):
        kwargs.update(_quantization_kwargs(quantization))
    elif quantization == "bf16":
        kwargs["torch_dtype"] = torch.bfloat16
    elif quantization == "fp16":
        kwargs["torch_dtype"] = torch.float16
    else:
        kwargs["torch_dtype"] = torch.float32

    return kwargs


def _quantization_kwargs(quantization: str) -> dict:
    if not torch.cuda.is_available():
        raise ModelLoadError(
            f"{quantization} quantization requires a CUDA GPU. "
            "Pick bf16, fp16, or fp32 for CPU machines."
        )
    try:
        from transformers import BitsAndBytesConfig
    except ImportError as exc:
        raise ModelLoadError(
            "bitsandbytes not installed; 4-bit/8-bit quantization unavailable."
        ) from exc

    if quantization == "4bit":
        return {
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        }
    return {"quantization_config": BitsAndBytesConfig(load_in_8bit=True)}


def _format_load_error(model_id: str, exc: Exception) -> str:
    text = str(exc).lower()
    if "401" in text or "gated" in text or "restricted" in text:
        return (
            f"Model '{model_id}' is gated. Add your HuggingFace token in "
            "Settings, or accept the license on the model's HF page."
        )
    if "404" in text or "not found" in text or "repository not found" in text:
        return f"Model '{model_id}' not found on HuggingFace."
    if "cuda out of memory" in text or "out of memory" in text:
        return (
            "Not enough GPU memory. Try a smaller model or 4-bit quantization."
        )
    return f"Failed to load '{model_id}': {exc}"


model_manager = ModelManager()
