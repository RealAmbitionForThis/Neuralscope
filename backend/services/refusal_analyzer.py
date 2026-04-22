"""Refusal direction extraction via diff-in-means with winsorization.

Based on Arditi et al. 2024 ("Refusal in Language Models Is Mediated by a
Single Direction") with the common stability improvements:

- Winsorize activations at the 99.5th percentile magnitude before averaging
- Perform linear algebra in fp32 even if activations were captured in bf16
- Score each layer's separability with a Gaussian Discriminant Value (GDV)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import torch

from backend.services.activation_engine import ActivationEngine

logger = logging.getLogger(__name__)


_WINSORIZE_PERCENTILE = 99.5
_EPS = 1e-8


@dataclass
class LayerResult:
    layer: int
    direction: list[float]
    refusal_strength: float
    separability: float
    harmful_mean_projection: float
    harmless_mean_projection: float


@dataclass
class RefusalAnalysisResult:
    best_layer: int
    global_direction: list[float]
    refusal_strengths: dict[int, float]
    separability_scores: dict[int, float]
    refusal_directions: dict[int, list[float]]
    harmful_projections: dict[int, list[float]]
    harmless_projections: dict[int, list[float]]

    def to_dict(self) -> dict:
        return {
            "best_layer": self.best_layer,
            "global_direction": self.global_direction,
            "refusal_strengths": self.refusal_strengths,
            "separability_scores": self.separability_scores,
            "refusal_directions": self.refusal_directions,
            "harmful_projections": self.harmful_projections,
            "harmless_projections": self.harmless_projections,
        }


class RefusalAnalyzer:
    def __init__(self, engine: ActivationEngine):
        self.engine = engine

    def analyze(
        self,
        harmful_prompts: list[str],
        harmless_prompts: list[str],
        progress: Optional[Callable[[float, str], None]] = None,
    ) -> RefusalAnalysisResult:
        if not harmful_prompts or not harmless_prompts:
            raise ValueError("Need at least one harmful and one harmless prompt.")

        n_layers = self.engine.n_layers
        layers = list(range(n_layers))

        if progress:
            progress(0.05, "Extracting harmful activations...")
        harmful = self.engine.extract_last_token(
            harmful_prompts,
            layers=layers,
            progress=lambda p, m: progress(0.05 + 0.4 * p, m) if progress else None,
        )

        if progress:
            progress(0.5, "Extracting harmless activations...")
        harmless = self.engine.extract_last_token(
            harmless_prompts,
            layers=layers,
            progress=lambda p, m: progress(0.5 + 0.4 * p, m) if progress else None,
        )

        if progress:
            progress(0.9, "Computing refusal directions...")
        results = _compute_directions_per_layer(harmful, harmless)

        best_layer = max(
            results, key=lambda layer: results[layer].separability
        )
        best = results[best_layer]

        if progress:
            progress(1.0, "Analysis complete.")

        return RefusalAnalysisResult(
            best_layer=best_layer,
            global_direction=best.direction,
            refusal_strengths={l: r.refusal_strength for l, r in results.items()},
            separability_scores={l: r.separability for l, r in results.items()},
            refusal_directions={l: r.direction for l, r in results.items()},
            harmful_projections=_project_to_list(harmful, results),
            harmless_projections=_project_to_list(harmless, results),
        )


def _compute_directions_per_layer(
    harmful: dict[int, torch.Tensor],
    harmless: dict[int, torch.Tensor],
) -> dict[int, LayerResult]:
    results: dict[int, LayerResult] = {}
    for layer, harmful_acts in harmful.items():
        harmless_acts = harmless[layer]
        results[layer] = _compute_direction_for_layer(
            layer, harmful_acts, harmless_acts
        )
    return results


def _compute_direction_for_layer(
    layer: int,
    harmful: torch.Tensor,
    harmless: torch.Tensor,
) -> LayerResult:
    harmful_w = _winsorize(harmful)
    harmless_w = _winsorize(harmless)

    mean_harmful = harmful_w.mean(dim=0)
    mean_harmless = harmless_w.mean(dim=0)
    mean_diff = mean_harmful - mean_harmless

    norm = float(mean_diff.norm()) + _EPS
    direction = mean_diff / norm

    harmful_proj = (harmful_w @ direction).cpu().numpy()
    harmless_proj = (harmless_w @ direction).cpu().numpy()

    gdv = _gaussian_discriminant_value(harmful_proj, harmless_proj)

    return LayerResult(
        layer=layer,
        direction=direction.tolist(),
        refusal_strength=float(norm),
        separability=float(gdv),
        harmful_mean_projection=float(harmful_proj.mean()),
        harmless_mean_projection=float(harmless_proj.mean()),
    )


def _winsorize(activations: torch.Tensor) -> torch.Tensor:
    """Clip per-dim magnitudes at the 99.5th percentile across prompts."""
    values = activations.to(torch.float32)
    magnitudes = values.abs()
    percentile = torch.quantile(magnitudes, _WINSORIZE_PERCENTILE / 100.0, dim=0)
    clipped = torch.clamp(values, min=-percentile, max=percentile)
    return clipped


def _gaussian_discriminant_value(a: np.ndarray, b: np.ndarray) -> float:
    mu_a, mu_b = a.mean(), b.mean()
    std_a, std_b = a.std() + _EPS, b.std() + _EPS
    return float(abs(mu_a - mu_b) / (std_a + std_b))


def _project_to_list(
    activations: dict[int, torch.Tensor],
    results: dict[int, LayerResult],
) -> dict[int, list[float]]:
    """Return per-prompt projections onto each layer's refusal direction,
    used by the frontend to render per-prompt dots on the heatmap."""
    out: dict[int, list[float]] = {}
    for layer, acts in activations.items():
        direction = torch.tensor(results[layer].direction, dtype=torch.float32)
        projections = (_winsorize(acts) @ direction).cpu().tolist()
        out[layer] = projections
    return out
