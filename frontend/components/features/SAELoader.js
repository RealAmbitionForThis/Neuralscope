"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";

const PRESETS = [
  { release: "gpt2-small-res-jb", sae_id: "blocks.6.hook_resid_pre", layer: 6, hint: "GPT-2 small, layer 6" },
  { release: "gemma-scope-2b-pt-res-canonical", sae_id: "layer_12/width_16k/canonical", layer: 12, hint: "Gemma 2 2B, layer 12" },
  { release: "gemma-scope-9b-pt-res", sae_id: "layer_20/width_16k/canonical", layer: 20, hint: "Gemma 2 9B, layer 20" },
];

export default function SAELoader({ onLoaded }) {
  const [release, setRelease] = useState(PRESETS[0].release);
  const [saeId, setSaeId] = useState(PRESETS[0].sae_id);
  const [layer, setLayer] = useState(PRESETS[0].layer);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const applyPreset = (preset) => {
    setRelease(preset.release);
    setSaeId(preset.sae_id);
    setLayer(preset.layer);
  };

  const load = async () => {
    setBusy(true);
    setError(null);
    try {
      const info = await apiFetch("/api/sae/load", {
        method: "POST",
        body: JSON.stringify({ release, sae_id: saeId, layer, device: "cpu" }),
      });
      if (onLoaded) onLoaded(info);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card p-5 space-y-3">
      <header>
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Load SAE
        </h3>
        <p className="text-xs text-muted mt-1">
          Pretrained SAEs are downloaded from HuggingFace on first load.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.sae_id}
            onClick={() => applyPreset(p)}
            className="text-left p-2 bg-panel rounded text-xs font-mono hover:border-accent border border-border"
          >
            <div>{p.release}</div>
            <div className="text-[10px] text-muted">{p.hint}</div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <input
          className="input col-span-2"
          placeholder="release"
          value={release}
          onChange={(e) => setRelease(e.target.value)}
        />
        <input
          className="input col-span-2"
          placeholder="sae_id"
          value={saeId}
          onChange={(e) => setSaeId(e.target.value)}
        />
        <input
          type="number"
          className="input col-span-2"
          placeholder="layer"
          value={layer}
          onChange={(e) => setLayer(Number(e.target.value))}
        />
      </div>

      <button onClick={load} className="btn-primary" disabled={busy}>
        {busy ? "Loading..." : "Load SAE"}
      </button>

      {error && (
        <div className="text-xs text-danger font-mono p-2 bg-panel rounded border border-danger/30">
          {error}
        </div>
      )}
    </div>
  );
}
