"""GPU memory and utilization monitoring via torch.cuda.

Gracefully returns an empty list on CPU-only machines so the frontend can
render a ``no GPUs detected`` state instead of an error.
"""

from __future__ import annotations

import torch

_BYTES_PER_GB = 1_000_000_000


def get_gpu_info() -> list[dict]:
    """Return per-GPU memory stats, or an empty list if CUDA isn't available."""
    if not torch.cuda.is_available():
        return []

    device_count = torch.cuda.device_count()
    return [_snapshot_gpu(index) for index in range(device_count)]


def _snapshot_gpu(index: int) -> dict:
    props = torch.cuda.get_device_properties(index)
    allocated = torch.cuda.memory_allocated(index)
    reserved = torch.cuda.memory_reserved(index)
    total = props.total_memory

    return {
        "index": index,
        "name": props.name,
        "total_gb": _bytes_to_gb(total),
        "allocated_gb": _bytes_to_gb(allocated),
        "reserved_gb": _bytes_to_gb(reserved),
        "free_gb": _bytes_to_gb(total - allocated),
        "utilization_pct": round(allocated / total * 100, 1) if total else 0.0,
    }


def _bytes_to_gb(value: int) -> float:
    return round(value / _BYTES_PER_GB, 2)
