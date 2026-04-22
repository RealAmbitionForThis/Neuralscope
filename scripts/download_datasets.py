"""Expand the bundled 25-prompt harmful/harmless sample sets with real
public datasets.

Defaults:
  - Harmful:   mlabonne/harmful_behaviors  (subset of AdvBench)
  - Harmless:  mlabonne/harmless_alpaca

Usage:
    python scripts/download_datasets.py --count 500
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent.parent / "backend" / "datasets"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500, help="Prompts per set")
    parser.add_argument(
        "--harmful-dataset",
        default="mlabonne/harmful_behaviors",
        help="HuggingFace dataset id for harmful prompts",
    )
    parser.add_argument(
        "--harmless-dataset",
        default="mlabonne/harmless_alpaca",
        help="HuggingFace dataset id for harmless prompts",
    )
    parser.add_argument("--harmful-field", default="text")
    parser.add_argument("--harmless-field", default="text")
    return parser.parse_args()


def load_dataset_prompts(dataset_id: str, field: str, count: int) -> list[str]:
    try:
        from datasets import load_dataset
    except ImportError:
        print(
            "The 'datasets' package is required. Install with `pip install datasets`.",
            file=sys.stderr,
        )
        sys.exit(1)

    ds = load_dataset(dataset_id, split="train")
    prompts: list[str] = []
    for row in ds:
        value = row.get(field) or row.get("instruction") or row.get("prompt")
        if value and isinstance(value, str):
            prompts.append(value.strip())
        if len(prompts) >= count:
            break
    return prompts


def write_json(path: Path, prompts: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(prompts, fh, ensure_ascii=False, indent=2)
    print(f"wrote {len(prompts)} prompts to {path}")


def main() -> None:
    args = parse_args()

    harmful = load_dataset_prompts(args.harmful_dataset, args.harmful_field, args.count)
    write_json(DATASETS_DIR / "harmful_prompts.json", harmful)

    harmless = load_dataset_prompts(args.harmless_dataset, args.harmless_field, args.count)
    write_json(DATASETS_DIR / "harmless_prompts.json", harmless)


if __name__ == "__main__":
    main()
