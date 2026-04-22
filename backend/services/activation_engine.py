"""Activation extraction via PyTorch forward hooks.

Uses the model map's ``layer_path_template`` to navigate to any transformer
layer on any architecture, avoiding hardcoded paths like
``model.model.layers[i]``. Falls back to the last-token hidden state.

We intentionally use native PyTorch hooks instead of nnsight for this phase
so the extraction pipeline works on any HuggingFace model without a library
dependency that changes shape between versions.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Optional

import torch

logger = logging.getLogger(__name__)


class ActivationEngine:
    """Extract residual-stream activations at the last token for each prompt."""

    def __init__(self, model: Any, tokenizer: Any, model_map: dict):
        self.model = model
        self.tokenizer = tokenizer
        self.map = model_map
        self.layer_template = model_map.get("layer_path_template")
        if self.layer_template is None:
            raise ValueError(
                "Model has no detectable transformer layer path; "
                "activation extraction is not supported."
            )
        self.n_layers = int(model_map.get("n_layers") or 0)
        self.hidden_size = int(model_map.get("hidden_size") or 0)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def extract_last_token(
        self,
        prompts: list[str],
        layers: Optional[list[int]] = None,
        progress: Optional[Callable[[float, str], None]] = None,
    ) -> dict[int, torch.Tensor]:
        """Run each prompt through the model and capture the residual stream
        output of the requested layers at the last (non-pad) token position.

        Returns ``{layer_idx: tensor(n_prompts, hidden_size)}`` on CPU in fp32.
        """
        if layers is None:
            layers = list(range(self.n_layers))

        accumulator: dict[int, list[torch.Tensor]] = {layer: [] for layer in layers}
        total = len(prompts)

        for index, prompt in enumerate(prompts):
            captures = self._run_single_prompt(prompt, layers)
            for layer in layers:
                accumulator[layer].append(captures[layer])
            if progress and (index + 1) % 5 == 0:
                progress(index / total, f"Extracted {index + 1}/{total} prompts")

        return {
            layer: torch.stack(tensors).to(dtype=torch.float32)
            for layer, tensors in accumulator.items()
        }

    def _run_single_prompt(
        self,
        prompt: str,
        layers: list[int],
    ) -> dict[int, torch.Tensor]:
        formatted = self._apply_chat_template(prompt)
        encoded = self.tokenizer(formatted, return_tensors="pt")
        input_ids = encoded["input_ids"].to(_model_device(self.model))

        captures: dict[int, torch.Tensor] = {}
        with _hooks_on_layers(self.model, self.map, layers, captures):
            with torch.no_grad():
                self.model(input_ids=input_ids)

        last_token_index = input_ids.shape[1] - 1
        return {
            layer: tensor[0, last_token_index, :].detach().cpu().to(torch.float32)
            for layer, tensor in captures.items()
        }

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
        except Exception as exc:
            logger.debug("chat template failed, using raw prompt: %s", exc)
            return prompt


@contextmanager
def _hooks_on_layers(
    model: Any,
    model_map: dict,
    layers: list[int],
    captures: dict[int, torch.Tensor],
):
    """Register forward hooks on the requested layers and remove on exit."""
    handles = []
    template = model_map["layer_path_template"]
    for layer_idx in layers:
        path = template.replace("{i}", str(layer_idx))
        module = _resolve_module(model, path)
        if module is None:
            raise ValueError(f"Cannot resolve layer path: {path}")
        handles.append(module.register_forward_hook(_make_hook(layer_idx, captures)))
    try:
        yield
    finally:
        for handle in handles:
            handle.remove()


def _make_hook(layer_idx: int, captures: dict[int, torch.Tensor]):
    def hook(_module, _inputs, output):
        captures[layer_idx] = _residual_from_output(output)
    return hook


def _residual_from_output(output: Any) -> torch.Tensor:
    """Transformer decoder layers return either a Tensor or a tuple whose
    first element is the hidden state. Normalize to a Tensor."""
    if isinstance(output, torch.Tensor):
        return output
    if isinstance(output, (tuple, list)) and output and isinstance(output[0], torch.Tensor):
        return output[0]
    raise TypeError(f"Unexpected layer output type: {type(output)}")


def _resolve_module(model: Any, path: str) -> Optional[Any]:
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


def _model_device(model: Any) -> torch.device:
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cpu")
