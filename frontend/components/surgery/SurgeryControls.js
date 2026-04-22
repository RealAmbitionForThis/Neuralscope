"use client";

import { useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import { useStore } from "@/lib/store";

export default function SurgeryControls() {
  const analysis = useStore((state) => state.analysis);
  const model = useStore((state) => state.model);
  const [layersText, setLayersText] = useState("");
  const [intensity, setIntensity] = useState(1.0);
  const [normPreserve, setNormPreserve] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const bestLayer = analysis.results?.best_layer;
  const nLayers = model.map?.n_layers ?? 0;

  const apply = async () => {
    setError(null);
    setBusy(true);
    try {
      const layers = _parseLayers(layersText, bestLayer, nLayers);
      const report = await apiFetch("/api/surgery/apply", {
        method: "POST",
        body: JSON.stringify({
          layers,
          intensity,
          norm_preserve: normPreserve,
        }),
      });
      useStore.getState().setSurgeryReport(report);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : String(err);
      setError(message);
      useStore.getState().setSurgeryError(message);
    } finally {
      setBusy(false);
    }
  };

  const undo = async () => {
    setError(null);
    setBusy(true);
    try {
      const result = await apiFetch("/api/surgery/undo", { method: "POST" });
      useStore.getState().setSurgeryReport(result);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  const ready = analysis.status === "complete";

  return (
    <div className="card p-5 space-y-4">
      <header>
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Permanent weight surgery
        </h3>
        <p className="text-xs text-muted mt-1">
          Orthogonalizes down_proj / o_proj / c_proj weights on the selected
          layers against the refusal direction from the last analysis
          {bestLayer !== undefined && ` (best layer: ${bestLayer})`}.
        </p>
      </header>

      <div className="space-y-2">
        <label className="text-xs font-mono text-muted uppercase tracking-wide">
          Layers (comma-separated; blank = all after best)
        </label>
        <input
          className="input"
          placeholder={bestLayer !== undefined ? `${bestLayer},${bestLayer + 1}` : "0,1,2"}
          value={layersText}
          onChange={(e) => setLayersText(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-xs font-mono text-muted">
          <span>Intensity</span>
          <span>{intensity.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={2}
          step={0.05}
          value={intensity}
          onChange={(e) => setIntensity(Number(e.target.value))}
          className="w-full accent-[#00f0ff]"
        />
      </div>

      <label className="flex items-center gap-2 text-xs font-mono text-muted">
        <input
          type="checkbox"
          checked={normPreserve}
          onChange={(e) => setNormPreserve(e.target.checked)}
        />
        preserve weight matrix norms
      </label>

      <div className="flex gap-2">
        <button className="btn-primary" onClick={apply} disabled={!ready || busy}>
          {busy ? "Applying..." : "Apply surgery"}
        </button>
        <button
          className="btn-primary bg-panel text-text hover:bg-border"
          onClick={undo}
          disabled={busy}
        >
          Undo
        </button>
      </div>

      {!ready && (
        <div className="text-xs text-warn font-mono">
          Run refusal analysis first.
        </div>
      )}
      {error && (
        <div className="text-xs text-danger font-mono p-2 bg-panel rounded border border-danger/30">
          {error}
        </div>
      )}
    </div>
  );
}

function _parseLayers(text, bestLayer, nLayers) {
  const trimmed = text.trim();
  if (trimmed) {
    return trimmed
      .split(",")
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isInteger(n) && n >= 0);
  }
  if (bestLayer === undefined) {
    return [0, 1, 2];
  }
  const spread = Math.min(3, nLayers - bestLayer);
  return Array.from({ length: spread }, (_, i) => bestLayer + i);
}
