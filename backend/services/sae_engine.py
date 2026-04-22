"""Sparse Autoencoder loading and feature extraction via SAELens.

Uses SAELens's ``SAE.from_pretrained`` to load a pre-trained SAE from
HuggingFace. The decoder weight matrix is exposed for visualization (UMAP)
and the encode/decode methods are used to compute feature activations on
real prompts.

SAELens has had several API revisions; we look up the decoder weight by
inspecting the SAE object at runtime (W_dec, decoder.weight, or the
state_dict) rather than hardcoding.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import torch

from backend.services.activation_engine import ActivationEngine

logger = logging.getLogger(__name__)


@dataclass
class LoadedSAE:
    release: str
    sae_id: str
    sae: Any
    layer: int
    d_in: int
    d_sae: int
    decoder_weights: torch.Tensor  # shape (d_sae, d_in) -- per-feature direction
    feature_labels: dict[int, str] = field(default_factory=dict)
    feature_categories: dict[int, str] = field(default_factory=dict)


class SAEEngine:
    def __init__(self) -> None:
        self._loaded: Optional[LoadedSAE] = None

    @property
    def loaded(self) -> Optional[LoadedSAE]:
        return self._loaded

    def load(self, release: str, sae_id: str, layer: int, device: str = "cpu") -> dict:
        try:
            from sae_lens import SAE
        except ImportError as exc:
            raise RuntimeError(
                "sae-lens is not installed. Add it to backend/requirements.txt "
                "and rebuild the environment."
            ) from exc

        logger.info("loading SAE release=%s id=%s on %s", release, sae_id, device)
        result = SAE.from_pretrained(release=release, sae_id=sae_id, device=device)
        # SAELens versions differ: some return (sae, cfg_dict, sparsity), some return SAE.
        sae = result[0] if isinstance(result, tuple) else result

        decoder = _find_decoder_weights(sae)
        d_sae, d_in = decoder.shape
        self._loaded = LoadedSAE(
            release=release,
            sae_id=sae_id,
            sae=sae,
            layer=layer,
            d_in=d_in,
            d_sae=d_sae,
            decoder_weights=decoder.detach().cpu().to(torch.float32),
        )
        return {
            "release": release,
            "sae_id": sae_id,
            "layer": layer,
            "d_in": d_in,
            "d_sae": d_sae,
        }

    def encode_activations(self, activations: torch.Tensor) -> torch.Tensor:
        loaded = self._require_loaded()
        device = next(loaded.sae.parameters()).device
        with torch.no_grad():
            return loaded.sae.encode(activations.to(device)).detach().cpu()

    def top_activating_examples(
        self,
        feature_id: int,
        prompts: list[str],
        activation_engine: ActivationEngine,
        top_k: int = 8,
    ) -> list[dict]:
        """Return the prompts where ``feature_id`` activates most strongly."""
        loaded = self._require_loaded()
        if loaded.layer >= activation_engine.n_layers:
            raise ValueError(
                f"SAE layer {loaded.layer} >= model n_layers {activation_engine.n_layers}"
            )

        captures = activation_engine.extract_last_token(prompts, layers=[loaded.layer])
        layer_activations = captures[loaded.layer]  # (n_prompts, d_in)
        feature_activations = self.encode_activations(layer_activations)
        column = feature_activations[:, feature_id].numpy()

        ranked = sorted(
            range(len(prompts)),
            key=lambda i: float(column[i]),
            reverse=True,
        )
        return [
            {"prompt": prompts[i], "activation": float(column[i])}
            for i in ranked[:top_k]
        ]

    def label(self, feature_id: int, label: str, category: Optional[str] = None) -> None:
        loaded = self._require_loaded()
        loaded.feature_labels[feature_id] = label
        if category:
            loaded.feature_categories[feature_id] = category

    def feature_info(self, feature_id: int) -> dict:
        loaded = self._require_loaded()
        if not 0 <= feature_id < loaded.d_sae:
            raise IndexError(
                f"feature_id {feature_id} out of range [0, {loaded.d_sae})"
            )
        direction = loaded.decoder_weights[feature_id]
        return {
            "id": feature_id,
            "label": loaded.feature_labels.get(feature_id),
            "category": loaded.feature_categories.get(feature_id),
            "direction_norm": float(direction.norm()),
            "direction_preview": direction[:16].tolist(),
        }

    def list_features(
        self, page: int = 0, page_size: int = 100, search: Optional[str] = None
    ) -> dict:
        loaded = self._require_loaded()
        total = loaded.d_sae

        if search:
            search_lower = search.lower()
            indices = [
                i
                for i, label in loaded.feature_labels.items()
                if search_lower in label.lower()
            ]
        else:
            indices = list(range(total))

        start = page * page_size
        page_ids = indices[start : start + page_size]

        return {
            "total": len(indices),
            "page": page,
            "page_size": page_size,
            "features": [
                {
                    "id": fid,
                    "label": loaded.feature_labels.get(fid),
                    "category": loaded.feature_categories.get(fid),
                }
                for fid in page_ids
            ],
        }

    def _require_loaded(self) -> LoadedSAE:
        if self._loaded is None:
            raise RuntimeError("No SAE loaded. POST /api/sae/load first.")
        return self._loaded


def _find_decoder_weights(sae: Any) -> torch.Tensor:
    """SAELens API has shifted; locate the decoder weight matrix robustly.

    The decoder maps features (d_sae) -> activations (d_in). In v6+ this
    is exposed as ``W_dec`` with shape (d_sae, d_in). Older or alternate
    layouts use ``decoder.weight`` (in, sae) which we transpose.
    """
    candidate = getattr(sae, "W_dec", None)
    if isinstance(candidate, torch.Tensor):
        return candidate

    decoder = getattr(sae, "decoder", None)
    if decoder is not None and hasattr(decoder, "weight"):
        weight = decoder.weight
        if weight.ndim == 2:
            return weight if weight.shape[0] == _guess_d_sae(sae) else weight.T

    if hasattr(sae, "state_dict"):
        for key, value in sae.state_dict().items():
            if "W_dec" in key or key.endswith("decoder.weight"):
                if isinstance(value, torch.Tensor) and value.ndim == 2:
                    return value

    raise RuntimeError(
        "Could not locate the SAE's decoder weight matrix. SAE class: "
        f"{type(sae).__name__}. Inspect the object and update _find_decoder_weights."
    )


def _guess_d_sae(sae: Any) -> Optional[int]:
    cfg = getattr(sae, "cfg", None)
    if cfg is None:
        return None
    return getattr(cfg, "d_sae", None) or getattr(cfg, "n_features", None)


sae_engine = SAEEngine()
