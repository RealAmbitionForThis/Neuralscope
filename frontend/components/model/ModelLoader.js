"use client";

import { useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import { useStore } from "@/lib/store";
import QuantizationPicker from "./QuantizationPicker";

const DEFAULT_MODEL_ID = "gpt2";
const DEFAULT_QUANTIZATION = "fp16";

export default function ModelLoader() {
  const [modelId, setModelId] = useState(DEFAULT_MODEL_ID);
  const [quantization, setQuantization] = useState(DEFAULT_QUANTIZATION);
  const [error, setError] = useState(null);

  const model = useStore((state) => state.model);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    useStore.getState().startModelLoad(modelId);
    try {
      await apiFetch("/api/model/load", {
        method: "POST",
        body: JSON.stringify({ model_id: modelId, quantization }),
      });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to reach backend.";
      setError(message);
      useStore.getState().failModelLoad(message);
    }
  };

  const disabled = model.status === "loading";

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <FormField label="HuggingFace model id">
        <input
          className="input"
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          placeholder="e.g. gpt2, meta-llama/Llama-3.1-8B-Instruct"
          disabled={disabled}
        />
      </FormField>

      <FormField label="Quantization">
        <QuantizationPicker value={quantization} onChange={setQuantization} />
      </FormField>

      {error && (
        <div className="text-sm text-danger font-mono bg-panel p-3 rounded-md border border-danger/30">
          {error}
        </div>
      )}

      <button type="submit" className="btn-primary" disabled={disabled}>
        {disabled ? "Loading..." : "Load Model"}
      </button>
    </form>
  );
}

function FormField({ label, children }) {
  return (
    <label className="block space-y-2">
      <span className="text-xs font-mono text-muted uppercase tracking-wide">
        {label}
      </span>
      {children}
    </label>
  );
}
