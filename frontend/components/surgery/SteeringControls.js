"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";
import { useStore } from "@/lib/store";

export default function SteeringControls() {
  const analysis = useStore((state) => state.analysis);
  const active = useStore((state) => state.steering.active);
  const [layer, setLayer] = useState(analysis.results?.best_layer ?? 0);
  const [strength, setStrength] = useState(1.0);
  const [busy, setBusy] = useState(false);

  const addVector = async () => {
    setBusy(true);
    try {
      const result = await apiFetch("/api/steering/add", {
        method: "POST",
        body: JSON.stringify({
          layer,
          strength,
          layer_for_direction: layer,
          label: "refusal",
        }),
      });
      useStore.getState().setSteeringActive(result.active || []);
    } finally {
      setBusy(false);
    }
  };

  const clear = async () => {
    setBusy(true);
    try {
      await apiFetch("/api/steering/clear", { method: "POST" });
      useStore.getState().setSteeringActive([]);
    } finally {
      setBusy(false);
    }
  };

  const ready = analysis.status === "complete";

  return (
    <div className="card p-5 space-y-4">
      <header>
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Live inference steering
        </h3>
        <p className="text-xs text-muted mt-1">
          Reversible, applied via hooks during generation. No weights are changed.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3">
        <LabeledInput label="Layer">
          <input
            type="number"
            className="input"
            min={0}
            value={layer}
            onChange={(e) => setLayer(Number(e.target.value))}
          />
        </LabeledInput>
        <LabeledInput label="Strength">
          <input
            type="number"
            step={0.1}
            className="input"
            value={strength}
            onChange={(e) => setStrength(Number(e.target.value))}
          />
        </LabeledInput>
      </div>

      <div className="flex gap-2">
        <button className="btn-primary" onClick={addVector} disabled={!ready || busy}>
          Add vector
        </button>
        <button
          className="btn-primary bg-panel text-text hover:bg-border"
          onClick={clear}
          disabled={busy || !active.length}
        >
          Clear all
        </button>
      </div>

      {active.length > 0 && (
        <div className="space-y-1 text-xs font-mono">
          <div className="text-muted uppercase tracking-wide text-[10px]">
            Active vectors ({active.length})
          </div>
          {active.map((v, i) => (
            <div key={i} className="flex justify-between p-2 bg-panel rounded">
              <span>L{v.layer} · {v.label}</span>
              <span className="text-accent">{v.strength.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}

      {!ready && (
        <div className="text-xs text-warn font-mono">Run refusal analysis first.</div>
      )}
    </div>
  );
}

function LabeledInput({ label, children }) {
  return (
    <label className="space-y-1 block">
      <div className="text-[10px] font-mono text-muted uppercase tracking-wide">
        {label}
      </div>
      {children}
    </label>
  );
}
