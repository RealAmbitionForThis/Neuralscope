"""Weight orthogonalization for refusal abliteration.

Removes the component of each target weight matrix that writes to the
refusal direction in the residual stream.

Math (PyTorch convention W.shape == (out_features, in_features)):
    Let r be a unit vector in R^{d_model}.
    For any matrix W with W.shape[0] == d_model:
        W_new = W - outer(r, r^T @ W)
    After this update, for any input x: (r^T @ W_new @ x) == 0.

Targets are discovered dynamically from the model map: any weight matrix
whose first dimension equals ``hidden_size`` is a residual-stream writer.
For Llama/Mistral/Qwen this picks up ``down_proj`` and ``o_proj``; for
GPT-2 it picks up ``mlp.c_proj`` and ``attn.c_proj``. Always architecture-
agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

import torch

logger = logging.getLogger(__name__)


_DEFAULT_TARGET_NAME_KEYWORDS = (
    "down_proj",
    "o_proj",
    "c_proj",
    "dense_4h_to_h",
    "dense",
    "out_proj",
)


class SurgeryEngine:
    def __init__(self, model: Any, model_map: dict):
        self.model = model
        self.map = model_map
        self.hidden_size = int(model_map.get("hidden_size") or 0)
        self._checkpoint: Optional[dict[str, torch.Tensor]] = None

    def orthogonalize(
        self,
        direction: torch.Tensor,
        layer_indices: list[int],
        intensity: float = 1.0,
        norm_preserve: bool = True,
        target_name_filter: Optional[list[str]] = None,
    ) -> dict:
        """Apply orthogonalization and return a report of modified tensors."""
        if direction.ndim != 1 or direction.shape[0] != self.hidden_size:
            raise ValueError(
                f"Direction must be a 1D tensor of size {self.hidden_size}; "
                f"got shape {tuple(direction.shape)}"
            )

        unit = direction.to(torch.float32)
        unit = unit / (unit.norm() + 1e-8)

        targets = _collect_targets(
            self.map, layer_indices, self.hidden_size, target_name_filter
        )
        if not targets:
            raise ValueError(
                "No residual-stream-writing weight matrices found for the "
                "selected layers. Check layer indices or target filter."
            )

        if self._checkpoint is None:
            self._checkpoint = _snapshot_weights(self.model, (t["path"] for t in targets))

        modified = []
        for target in targets:
            module = _navigate(self.model, target["module_path"])
            weight = module.weight.data

            original_norm = weight.norm().item() if norm_preserve else None
            unit_on_device = unit.to(device=weight.device, dtype=weight.dtype)
            scaled = unit_on_device * float(intensity)

            new_weight = _project_out(weight, scaled, axis=target["axis"])

            if norm_preserve and original_norm is not None and original_norm > 0:
                current_norm = new_weight.norm().item()
                if current_norm > 0:
                    new_weight = new_weight * (original_norm / current_norm)

            module.weight.data.copy_(new_weight)
            modified.append(target["path"])

        return {
            "modified_paths": modified,
            "modified_count": len(modified),
            "layers": sorted(layer_indices),
            "intensity": float(intensity),
            "norm_preserve": bool(norm_preserve),
        }

    def undo(self) -> dict:
        """Restore original weights from the latest checkpoint."""
        if self._checkpoint is None:
            return {"status": "noop", "message": "No checkpoint to restore."}

        restored = 0
        for path, original in self._checkpoint.items():
            module = _navigate_weight(self.model, path)
            if module is None:
                continue
            module.data.copy_(original.to(module.device, module.dtype))
            restored += 1

        self._checkpoint = None
        return {"status": "reverted", "restored": restored}


def _project_out(
    weight: torch.Tensor, direction: torch.Tensor, axis: int
) -> torch.Tensor:
    """Remove the component of ``weight`` that writes to ``direction``, in fp32.

    ``axis`` specifies which dimension of ``weight`` is the residual-stream
    (output) dimension:
      - axis=0 (nn.Linear convention): W.shape == (hidden, in),
        output = W @ x.  W_new = W - outer(r, r^T @ W).
      - axis=1 (Conv1D convention, used by GPT-2): W.shape == (in, hidden),
        output = x @ W.  W_new = W - outer(W @ r, r).
    """
    if axis not in (0, 1):
        raise ValueError(f"axis must be 0 or 1, got {axis}")
    if direction.shape[0] != weight.shape[axis]:
        raise ValueError(
            f"direction dim {direction.shape[0]} does not match "
            f"weight axis={axis} dim {weight.shape[axis]} (shape {tuple(weight.shape)})"
        )

    w32 = weight.to(torch.float32)
    r32 = direction.to(torch.float32)

    if axis == 0:
        projection = torch.outer(r32, r32 @ w32)
    else:
        projection = torch.outer(w32 @ r32, r32)

    return (w32 - projection).to(weight.dtype)


def _collect_targets(
    model_map: dict,
    layer_indices: list[int],
    hidden_size: int,
    name_filter: Optional[list[str]],
) -> list[dict]:
    """Find weight matrices in the selected layers whose output dim equals
    hidden_size (i.e. they write to the residual stream)."""
    layers_by_index = {layer["index"]: layer for layer in model_map.get("layers", [])}
    name_filter_lower = [n.lower() for n in (name_filter or _DEFAULT_TARGET_NAME_KEYWORDS)]

    targets: list[dict] = []
    for index in layer_indices:
        layer = layers_by_index.get(index)
        if layer is None:
            continue
        for submodule in layer["submodules"].values():
            for weight in submodule["weight_matrices"]:
                axis = _hidden_axis(weight["shape"], hidden_size)
                if axis is None:
                    continue
                if not _name_matches(weight["name"], name_filter_lower):
                    continue
                targets.append(
                    {
                        "path": weight["path"],
                        "module_path": weight["path"].rsplit(".weight", 1)[0],
                        "name": weight["name"],
                        "shape": weight["shape"],
                        "layer": index,
                        "axis": axis,
                    }
                )
    return targets


def _hidden_axis(shape: list[int], hidden_size: int) -> Optional[int]:
    """Which axis of this weight matrix matches ``hidden_size`` (i.e. is the
    residual-stream dimension). Prefer axis 0 if both match (rare, square)."""
    if not shape:
        return None
    if shape[0] == hidden_size:
        return 0
    if len(shape) > 1 and shape[1] == hidden_size:
        return 1
    return None


def _name_matches(name: str, keywords: Iterable[str]) -> bool:
    lowered = name.lower()
    return any(keyword in lowered for keyword in keywords)


def _snapshot_weights(model: Any, paths: Iterable[str]) -> dict[str, torch.Tensor]:
    state: dict[str, torch.Tensor] = {}
    for path in paths:
        param = _navigate_weight(model, path)
        if param is None:
            continue
        state[path] = param.detach().cpu().clone()
    return state


def _navigate(model: Any, path: str) -> Any:
    current = model
    for part in path.split("."):
        if part == "":
            continue
        if part.isdigit():
            current = current[int(part)]
        else:
            current = getattr(current, part)
    return current


def _navigate_weight(model: Any, path: str) -> Optional[torch.Tensor]:
    """Resolve a dotted path ending in ``.weight`` to its tensor."""
    parts = path.split(".")
    current: Any = model
    for part in parts:
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
    return current if isinstance(current, torch.Tensor) else None
