"""Auto-label SAE features with a small local LLM (Qwen3-0.6B by default).

Loaded lazily on first use to avoid the ~600MB-1.2GB VRAM cost when not
needed. Defaults to CPU so it doesn't compete for GPU memory with the
main model under analysis.

CRITICAL: Qwen3's thinking mode is controlled via
``apply_chat_template(..., enable_thinking=False)``, NOT via inline
``/no_think`` text in the prompt.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

import torch

logger = logging.getLogger(__name__)


DEFAULT_LABELER_MODEL = "Qwen/Qwen3-0.6B"
_CATEGORIES = (
    "safety", "refusal", "language", "code", "math", "reasoning",
    "knowledge", "style", "formatting", "punctuation", "emotion",
    "entity", "syntax", "other",
)


class FeatureLabeler:
    def __init__(
        self,
        model_id: str = DEFAULT_LABELER_MODEL,
        device: str = "cpu",
    ):
        self.model_id = model_id
        self.device = device
        self._tokenizer = None
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info("loading labeler %s on %s", self.model_id, self.device)
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            dtype=dtype,
            device_map=self.device,
        )
        self._model.eval()

    def label_feature(
        self,
        top_activating_texts: list[str],
        positive_logits: Optional[list[str]] = None,
        negative_logits: Optional[list[str]] = None,
    ) -> str:
        """Generate a 5-15 word label for a single SAE feature."""
        self._ensure_loaded()
        prompt = _build_label_prompt(
            top_activating_texts, positive_logits or [], negative_logits or []
        )
        return self._chat(prompt, max_new_tokens=30, temperature=0.3).strip().split("\n")[0]

    def categorize(self, label: str) -> str:
        self._ensure_loaded()
        prompt = _build_category_prompt(label)
        raw = self._chat(prompt, max_new_tokens=8, temperature=0.0).strip().lower()
        first_word = raw.split()[0] if raw else "other"
        return first_word if first_word in _CATEGORIES else "other"

    def label_batch(
        self,
        features_data: dict[int, dict],
        progress: Optional[Callable[[float, str], None]] = None,
    ) -> dict[int, str]:
        labels: dict[int, str] = {}
        total = len(features_data)
        for index, (feature_id, payload) in enumerate(features_data.items()):
            labels[feature_id] = self.label_feature(
                top_activating_texts=payload.get("top_texts", []),
                positive_logits=payload.get("positive_logits"),
                negative_logits=payload.get("negative_logits"),
            )
            if progress and (index + 1) % 5 == 0:
                progress((index + 1) / total, f"Labeled {index + 1}/{total}")
        return labels

    def _chat(self, user_message: str, max_new_tokens: int, temperature: float) -> str:
        messages = [{"role": "user", "content": user_message}]
        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

        do_sample = temperature > 0
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                temperature=max(temperature, 1e-4),
                pad_token_id=self._tokenizer.eos_token_id,
            )

        new_tokens = outputs[0, inputs["input_ids"].shape[1]:]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True)


def _build_label_prompt(
    texts: list[str], positive_logits: list[str], negative_logits: list[str]
) -> str:
    text_lines = "\n".join(f'- "{t}"' for t in texts[:8])
    return (
        "You are a neural network interpretability researcher. Given the "
        "evidence below about a sparse autoencoder feature, provide a concise "
        "label (5-15 words) describing what this feature represents.\n\n"
        f"TOP ACTIVATING TEXTS:\n{text_lines}\n\n"
        f"TOKENS PROMOTED: {', '.join(positive_logits[:10]) or 'n/a'}\n"
        f"TOKENS SUPPRESSED: {', '.join(negative_logits[:10]) or 'n/a'}\n\n"
        "LABEL:"
    )


def _build_category_prompt(label: str) -> str:
    return (
        "Categorize this neural network feature into exactly ONE category.\n\n"
        f'Feature: "{label}"\n\n'
        f"Categories: {', '.join(_CATEGORIES)}\n\n"
        "Reply with just the category word, nothing else.\nCategory:"
    )


feature_labeler: Optional[FeatureLabeler] = None


def get_feature_labeler() -> FeatureLabeler:
    global feature_labeler
    if feature_labeler is None:
        feature_labeler = FeatureLabeler()
    return feature_labeler
