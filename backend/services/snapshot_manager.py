"""Named snapshots of a model's weights for save / compare / rollback.

Snapshots store only the tensors for residual-stream-writing weight
matrices (identified via the surgery target heuristic), not the full
model, to keep them small.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import torch

from backend.services.surgery_engine import _collect_targets, _navigate_weight

logger = logging.getLogger(__name__)


@dataclass
class Snapshot:
    name: str
    created_at: float
    tensors: dict[str, torch.Tensor] = field(default_factory=dict)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "tensor_count": len(self.tensors),
        }


class SnapshotManager:
    def __init__(self, model: Any, model_map: dict):
        self.model = model
        self.map = model_map
        self._snapshots: dict[str, Snapshot] = {}

    def list(self) -> list[dict]:
        return [snap.describe() for snap in self._snapshots.values()]

    def save(self, name: str) -> dict:
        hidden = int(self.map.get("hidden_size") or 0)
        layer_indices = [layer["index"] for layer in self.map.get("layers", [])]
        targets = _collect_targets(self.map, layer_indices, hidden, None)

        tensors: dict[str, torch.Tensor] = {}
        for target in targets:
            param = _navigate_weight(self.model, target["path"])
            if param is None:
                continue
            tensors[target["path"]] = param.detach().cpu().clone()

        snapshot = Snapshot(name=name, created_at=time.time(), tensors=tensors)
        self._snapshots[name] = snapshot
        return snapshot.describe()

    def rollback(self, name: str) -> dict:
        snapshot = self._snapshots.get(name)
        if snapshot is None:
            raise KeyError(f"Snapshot '{name}' not found.")

        restored = 0
        for path, original in snapshot.tensors.items():
            param = _navigate_weight(self.model, path)
            if param is None:
                continue
            param.data.copy_(original.to(param.device, param.dtype))
            restored += 1

        return {"status": "reverted", "name": name, "restored": restored}

    def diff(self, name_a: str, name_b: Optional[str] = None) -> dict:
        """Per-tensor Frobenius norm difference between two snapshots, or
        between snapshot A and the current model when ``name_b`` is None."""
        snap_a = self._snapshots.get(name_a)
        if snap_a is None:
            raise KeyError(f"Snapshot '{name_a}' not found.")

        comparison: dict[str, float] = {}
        for path, tensor_a in snap_a.tensors.items():
            tensor_b = _resolve_b(self, path, name_b)
            if tensor_b is None:
                continue
            delta = (tensor_a.to(torch.float32) - tensor_b.to(torch.float32)).norm()
            comparison[path] = float(delta)

        total_change = sum(comparison.values())
        return {
            "name_a": name_a,
            "name_b": name_b or "current",
            "per_tensor_norm": comparison,
            "total_norm_change": total_change,
        }

    def delete(self, name: str) -> dict:
        existed = self._snapshots.pop(name, None) is not None
        return {"deleted": existed, "name": name}


def _resolve_b(
    manager: SnapshotManager, path: str, name_b: Optional[str]
) -> Optional[torch.Tensor]:
    if name_b is None:
        param = _navigate_weight(manager.model, path)
        return param.detach().cpu() if param is not None else None
    snap = manager._snapshots.get(name_b)
    if snap is None:
        raise KeyError(f"Snapshot '{name_b}' not found.")
    return snap.tensors.get(path)
