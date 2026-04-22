"""Export a modified model to disk (safetensors) or to HuggingFace Hub.

GGUF export is delegated to llama.cpp's ``convert_hf_to_gguf.py``; this
service shells out to it if available. If llama.cpp is not installed,
the GGUF export returns a clear error rather than crashing.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


DEFAULT_EXPORT_ROOT = Path(os.environ.get("NEURALSCOPE_EXPORT_DIR", "./exports"))


class ExportError(Exception):
    pass


def export_safetensors(
    model: Any,
    tokenizer: Any,
    output_dir: Optional[Path] = None,
    model_id: str = "modified-model",
) -> dict:
    """Save the model + tokenizer to ``output_dir`` using HF's save_pretrained."""
    destination = Path(output_dir) if output_dir else DEFAULT_EXPORT_ROOT / model_id
    destination.mkdir(parents=True, exist_ok=True)

    logger.info("saving model to %s", destination)
    model.save_pretrained(str(destination), safe_serialization=True)
    tokenizer.save_pretrained(str(destination))

    size_bytes = sum(f.stat().st_size for f in destination.rglob("*") if f.is_file())
    return {
        "path": str(destination.resolve()),
        "size_gb": round(size_bytes / 1_000_000_000, 3),
        "format": "safetensors",
    }


def export_gguf(
    source_dir: Path,
    output_path: Optional[Path] = None,
    llama_cpp_root: Optional[Path] = None,
    quantization: str = "F16",
) -> dict:
    """Convert a saved HuggingFace model to GGUF via llama.cpp's script.

    ``llama_cpp_root`` must contain ``convert_hf_to_gguf.py``. Looked up in:
      - explicit ``llama_cpp_root`` argument
      - ``NEURALSCOPE_LLAMA_CPP`` env var
      - ``./llama.cpp`` relative to cwd
    """
    source = Path(source_dir)
    if not source.exists():
        raise ExportError(f"Source directory not found: {source}")

    root = _resolve_llama_cpp_root(llama_cpp_root)
    convert_script = root / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        raise ExportError(
            "llama.cpp's convert_hf_to_gguf.py not found. Install llama.cpp "
            "(git clone https://github.com/ggml-org/llama.cpp) and either "
            "place it at ./llama.cpp or set NEURALSCOPE_LLAMA_CPP."
        )

    output = Path(output_path) if output_path else source.with_suffix(".gguf")
    dtype_flag = _quantization_to_dtype(quantization)

    cmd = [
        "python3",
        str(convert_script),
        str(source),
        "--outtype",
        dtype_flag,
        "--outfile",
        str(output),
    ]
    logger.info("running %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ExportError(
            f"GGUF conversion failed (exit {result.returncode}):\n{result.stderr}"
        )

    size_bytes = output.stat().st_size
    return {
        "path": str(output.resolve()),
        "size_gb": round(size_bytes / 1_000_000_000, 3),
        "format": f"gguf-{dtype_flag}",
    }


def push_to_hub(
    source_dir: Path,
    repo_id: str,
    private: bool = True,
    token: Optional[str] = None,
) -> dict:
    """Upload a saved model directory to HuggingFace Hub."""
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise ExportError("huggingface_hub is not installed.") from exc

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, private=private, exist_ok=True)
    api.upload_folder(
        folder_path=str(source_dir),
        repo_id=repo_id,
        commit_message="NeuralScope surgery upload",
    )
    return {"url": f"https://huggingface.co/{repo_id}", "private": private}


def _resolve_llama_cpp_root(explicit: Optional[Path]) -> Path:
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("NEURALSCOPE_LLAMA_CPP")
    if env:
        return Path(env)
    return Path("./llama.cpp").resolve()


def _quantization_to_dtype(quantization: str) -> str:
    mapping = {
        "F16": "f16",
        "F32": "f32",
        "BF16": "bf16",
        "Q8_0": "q8_0",
        "AUTO": "auto",
    }
    key = quantization.upper()
    if key not in mapping:
        raise ExportError(
            f"Unsupported GGUF quantization '{quantization}'. "
            f"Choose: {', '.join(mapping.keys())}"
        )
    return mapping[key]
