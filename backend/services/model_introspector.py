"""Architecture-agnostic discovery of transformer model structure.

Given any loaded ``torch.nn.Module`` returns a JSON-serializable map of
layers, submodules, and weight matrices. All later services (refusal
analyzer, surgery engine, SAE loader, steering engine) navigate the model
through this map rather than hardcoding paths like ``model.model.layers[i]``.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import torch
from torch import nn

_ATTENTION_KEYWORDS = ("attn", "attention", "self_attn", "mha")
_MLP_KEYWORDS = ("mlp", "ffn", "feed_forward", "dense", "experts", "moe")
_HIDDEN_SIZE_ATTRS = ("hidden_size", "d_model", "n_embd", "dim")
_N_LAYER_ATTRS = ("num_hidden_layers", "n_layer", "num_layers", "n_layers")


def introspect_model(model: nn.Module) -> dict[str, Any]:
    """Return the structure map for ``model``.

    Fields:
      - ``model_type``, ``architecture``
      - ``n_layers``, ``hidden_size``
      - ``layer_path_template`` (e.g. ``"transformer.h.{i}"``) or ``None``
      - ``layers``: per-layer submodules and weight matrices
      - ``all_weight_matrices``: flat catalog of every parameter tensor
      - ``hookable_modules``: every ``nn.Module`` that can be targeted
      - ``total_parameters``, ``total_size_gb``, ``devices``
    """
    config = getattr(model, "config", None)

    layer_template = _detect_layer_path_template(model)
    n_layers = _detect_n_layers(model, config, layer_template)
    hidden_size = _detect_hidden_size(config)

    layers = (
        _discover_layers(model, layer_template, n_layers) if layer_template else []
    )

    all_weights = _catalog_weights(model)
    total_params = sum(w["numel"] for w in all_weights)

    return {
        "model_type": getattr(config, "model_type", None) if config else None,
        "architecture": model.__class__.__name__,
        "n_layers": n_layers,
        "hidden_size": hidden_size,
        "layer_path_template": layer_template,
        "layers": layers,
        "all_weight_matrices": all_weights,
        "hookable_modules": _catalog_modules(model),
        "total_parameters": total_params,
        "total_size_gb": _estimate_size_gb(model),
        "devices": _unique_devices(model),
    }


def _detect_n_layers(
    model: nn.Module,
    config: Any,
    layer_template: Optional[str],
) -> int:
    if config is not None:
        for attr in _N_LAYER_ATTRS:
            value = getattr(config, attr, None)
            if value is not None:
                return int(value)

    if layer_template is None:
        return 0

    container_path = layer_template.replace(".{i}", "")
    container = _get_module_by_path(model, container_path)
    if container is None:
        return 0
    return len(container) if hasattr(container, "__len__") else 0


def _detect_hidden_size(config: Any) -> Optional[int]:
    if config is None:
        return None
    for attr in _HIDDEN_SIZE_ATTRS:
        value = getattr(config, attr, None)
        if value is not None:
            return int(value)
    return None


def _detect_layer_path_template(model: nn.Module) -> Optional[str]:
    """Find the path pattern to access transformer layer N."""
    for name, module in model.named_modules():
        if not _is_layer_container(module):
            continue

        first_child = next(iter(module.children()), None)
        if first_child is None:
            continue

        if _looks_like_transformer_layer(first_child):
            return f"{name}.{{i}}"

    return None


def _is_layer_container(module: nn.Module) -> bool:
    if not isinstance(module, (nn.ModuleList, nn.Sequential)):
        return False
    return len(module) > 1


def _looks_like_transformer_layer(module: nn.Module) -> bool:
    """Heuristic: a transformer decoder layer has BOTH attention and MLP children."""
    child_names = {name for name, _ in module.named_children()}
    has_attention = _any_keyword_match(child_names, _ATTENTION_KEYWORDS)
    has_mlp = _any_keyword_match(child_names, _MLP_KEYWORDS)
    return has_attention and has_mlp


def _any_keyword_match(names: set[str], keywords: tuple[str, ...]) -> bool:
    lowered = [name.lower() for name in names]
    return any(keyword in name for name in lowered for keyword in keywords)


def _discover_layers(
    model: nn.Module,
    layer_template: str,
    n_layers: int,
) -> list[dict]:
    layers: list[dict] = []
    for index in range(n_layers):
        path = layer_template.replace("{i}", str(index))
        module = _get_module_by_path(model, path)
        if module is None:
            continue
        layers.append(_describe_layer(module, path, index))
    return layers


def _describe_layer(module: nn.Module, path: str, index: int) -> dict:
    submodules: dict[str, dict] = {}
    for child_name, child in module.named_children():
        submodules[child_name] = _describe_submodule(child, f"{path}.{child_name}")
    return {
        "index": index,
        "path": path,
        "type": module.__class__.__name__,
        "submodules": submodules,
    }


def _describe_submodule(module: nn.Module, path: str) -> dict:
    weights = list(_walk_weight_children(module, path, max_depth=2, depth=0))
    return {
        "path": path,
        "type": module.__class__.__name__,
        "weight_matrices": weights,
    }


def _walk_weight_children(
    module: nn.Module,
    path: str,
    max_depth: int,
    depth: int,
):
    """Walk children up to ``max_depth`` levels deep and yield a weight record
    for each descendant whose ``weight`` parameter is rank >= 2 (i.e. a
    Linear/Conv1D-style matrix). The descendant's module name is used as the
    weight matrix's short name so callers see ``c_attn``, ``q_proj``, etc.
    rather than just ``weight``.
    """
    for child_name, child in module.named_children():
        child_path = f"{path}.{child_name}"
        weight = getattr(child, "weight", None)
        if isinstance(weight, torch.Tensor) and weight.dim() >= 2:
            yield _describe_weight(
                name=child_name,
                path=f"{child_path}.weight",
                param=weight,
            )
        if depth < max_depth:
            yield from _walk_weight_children(
                child, child_path, max_depth, depth + 1
            )


def _describe_weight(name: str, path: str, param: torch.Tensor) -> dict:
    return {
        "name": name,
        "path": path,
        "shape": list(param.shape),
        "dtype": str(param.dtype).replace("torch.", ""),
        "device": str(param.device),
    }


def _catalog_weights(model: nn.Module) -> list[dict]:
    catalog = []
    for name, param in model.named_parameters():
        catalog.append(
            {
                "path": name,
                "shape": list(param.shape),
                "dtype": str(param.dtype).replace("torch.", ""),
                "device": str(param.device),
                "numel": param.numel(),
                "requires_grad": param.requires_grad,
            }
        )
    return catalog


def _catalog_modules(model: nn.Module) -> list[dict]:
    modules = []
    for name, module in model.named_modules():
        if name == "":
            continue
        modules.append(
            {
                "path": name,
                "type": module.__class__.__name__,
                "has_parameters": _has_direct_parameters(module),
            }
        )
    return modules


def _has_direct_parameters(module: nn.Module) -> bool:
    return any(True for _ in module.parameters(recurse=False))


def _get_module_by_path(model: nn.Module, path: str) -> Optional[nn.Module]:
    current: Any = model
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


def _estimate_size_gb(model: nn.Module) -> float:
    total_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    return round(total_bytes / 1_000_000_000, 3)


def _unique_devices(model: nn.Module) -> list[str]:
    devices = {str(p.device) for p in model.parameters()}
    return sorted(devices)
