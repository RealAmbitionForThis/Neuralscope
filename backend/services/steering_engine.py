"""Inference-time activation steering via forward hooks.

Unlike the SurgeryEngine (permanent weight modification), steering is
reversible — hooks add/subtract a direction from the residual stream during
generation, and ``clear()`` removes them with no trace.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import torch

logger = logging.getLogger(__name__)


@dataclass
class SteeringVector:
    layer: int
    direction: torch.Tensor
    strength: float
    label: str


class SteeringEngine:
    def __init__(self, model: Any, tokenizer: Any, model_map: dict):
        self.model = model
        self.tokenizer = tokenizer
        self.map = model_map
        self.layer_template = model_map.get("layer_path_template")
        self._vectors: list[SteeringVector] = []

    def add_vector(
        self,
        layer: int,
        direction: torch.Tensor,
        strength: float = 1.0,
        label: str = "refusal",
    ) -> None:
        vec = direction.to(torch.float32)
        vec = vec / (vec.norm() + 1e-8)
        self._vectors.append(
            SteeringVector(layer=layer, direction=vec, strength=float(strength), label=label)
        )

    def clear(self) -> None:
        self._vectors = []

    def active_vectors(self) -> list[dict]:
        return [
            {"layer": v.layer, "strength": v.strength, "label": v.label}
            for v in self._vectors
        ]

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 160,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Generate text with steering vectors applied via forward hooks."""
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        text = self._apply_chat_template(prompt)
        inputs = self.tokenizer(text, return_tensors="pt").to(_device(self.model))

        handles = self._register_hooks()
        try:
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=temperature > 0,
                    temperature=max(temperature, 1e-4),
                    top_p=top_p,
                    pad_token_id=self.tokenizer.pad_token_id,
                )
        finally:
            for handle in handles:
                handle.remove()

        generated = output_ids[0, inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True)

    def _apply_chat_template(self, prompt: str) -> str:
        template = getattr(self.tokenizer, "chat_template", None)
        if not template:
            return prompt
        try:
            return self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            return prompt

    def _register_hooks(self) -> list[Any]:
        handles = []
        by_layer: dict[int, list[SteeringVector]] = {}
        for vector in self._vectors:
            by_layer.setdefault(vector.layer, []).append(vector)

        for layer, vectors in by_layer.items():
            module = self._get_layer_module(layer)
            if module is None:
                continue
            handles.append(module.register_forward_hook(_make_steering_hook(vectors)))
        return handles

    def _get_layer_module(self, layer: int) -> Optional[Any]:
        if self.layer_template is None:
            return None
        path = self.layer_template.replace("{i}", str(layer))
        return _navigate(self.model, path)


def _make_steering_hook(vectors: list[SteeringVector]):
    """Create a hook that subtracts ``strength * direction`` from the layer's
    residual-stream output. Positive strength *removes* the direction; negative
    adds it back (amplify)."""
    def hook(_module, _inputs, output):
        if isinstance(output, torch.Tensor):
            return _apply_steering(output, vectors)
        if isinstance(output, tuple):
            new_head = _apply_steering(output[0], vectors)
            return (new_head,) + output[1:]
        return output
    return hook


def _apply_steering(tensor: torch.Tensor, vectors: list[SteeringVector]) -> torch.Tensor:
    """tensor shape: (batch, seq, hidden)."""
    result = tensor
    for vector in vectors:
        direction = vector.direction.to(device=tensor.device, dtype=tensor.dtype)
        shift = direction * vector.strength
        result = result - shift.view(1, 1, -1)
    return result


def _navigate(model: Any, path: str) -> Optional[Any]:
    current = model
    for part in path.split("."):
        if part == "":
            continue
        if part.isdigit():
            try:
                current = current[int(part)]
            except (IndexError, TypeError):
                return None
        else:
            current = getattr(current, part, None)
        if current is None:
            return None
    return current


def _device(model: Any) -> torch.device:
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cpu")
