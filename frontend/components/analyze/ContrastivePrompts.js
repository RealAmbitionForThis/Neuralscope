"use client";

import { useEffect, useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import { useStore } from "@/lib/store";

export default function ContrastivePrompts() {
  const [harmful, setHarmful] = useState("");
  const [harmless, setHarmless] = useState("");
  const [useDefaults, setUseDefaults] = useState(true);
  const [maxPrompts, setMaxPrompts] = useState(25);
  const [error, setError] = useState(null);
  const analysis = useStore((state) => state.analysis);

  useEffect(() => {
    if (!useDefaults) return;
    apiFetch("/api/analyze/datasets/defaults")
      .then((data) => {
        setHarmful((data.harmful || []).join("\n"));
        setHarmless((data.harmless || []).join("\n"));
      })
      .catch(() => {});
  }, [useDefaults]);

  const start = async () => {
    setError(null);
    useStore.getState().startAnalysis();
    const payload = useDefaults
      ? { max_prompts: maxPrompts }
      : {
          harmful_prompts: harmful.split("\n").map((l) => l.trim()).filter(Boolean),
          harmless_prompts: harmless.split("\n").map((l) => l.trim()).filter(Boolean),
          max_prompts: maxPrompts,
        };

    try {
      await apiFetch("/api/analyze/refusal", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      const results = await apiFetch("/api/analyze/refusal/results");
      useStore.getState().finishAnalysis(results);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : String(err);
      setError(message);
      useStore.getState().failAnalysis(message);
    }
  };

  const running = analysis.status === "running";

  return (
    <div className="card p-5 space-y-4">
      <header className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
            Contrastive prompts
          </h3>
          <p className="text-xs text-muted mt-1">
            Harmful and harmless prompt sets. Defaults are bundled with the backend.
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs font-mono text-muted">
          <input
            type="checkbox"
            checked={useDefaults}
            onChange={(e) => setUseDefaults(e.target.checked)}
          />
          use defaults
        </label>
      </header>

      <div className="grid grid-cols-2 gap-3">
        <PromptBox label="Harmful" value={harmful} onChange={setHarmful} disabled={useDefaults} />
        <PromptBox label="Harmless" value={harmless} onChange={setHarmless} disabled={useDefaults} />
      </div>

      <div className="flex items-center gap-3">
        <label className="text-xs font-mono text-muted">max prompts</label>
        <input
          type="number"
          className="input w-24"
          min={1}
          max={500}
          value={maxPrompts}
          onChange={(e) => setMaxPrompts(Number(e.target.value) || 1)}
          disabled={running}
        />
        <button onClick={start} className="btn-primary" disabled={running}>
          {running ? `${Math.round((analysis.progress || 0) * 100)}% · ${analysis.message || "..."}` : "Run analysis"}
        </button>
      </div>

      {error && (
        <div className="text-xs text-danger font-mono p-2 bg-panel rounded border border-danger/30">
          {error}
        </div>
      )}
    </div>
  );
}

function PromptBox({ label, value, onChange, disabled }) {
  return (
    <div className="space-y-1">
      <div className="text-[10px] font-mono text-muted uppercase tracking-wide">
        {label} ({value.split("\n").filter((l) => l.trim()).length})
      </div>
      <textarea
        className="input h-40 font-mono text-xs"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={`One prompt per line (e.g. ${label.toLowerCase()} instructions)`}
      />
    </div>
  );
}
