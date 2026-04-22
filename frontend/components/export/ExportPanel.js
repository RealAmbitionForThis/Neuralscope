"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";
import { useStore } from "@/lib/store";

export default function ExportPanel() {
  const model = useStore((state) => state.model);
  const [format, setFormat] = useState("safetensors");
  const [outputDir, setOutputDir] = useState("");
  const [ggufQuantization, setGgufQuantization] = useState("F16");
  const [hubRepoId, setHubRepoId] = useState("");
  const [hubPrivate, setHubPrivate] = useState(true);
  const [sourceDir, setSourceDir] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      if (format === "safetensors") {
        const data = await apiFetch("/api/export/safetensors", {
          method: "POST",
          body: JSON.stringify({
            output_dir: outputDir || null,
            name: `${model.id.replace("/", "__")}-modified`,
          }),
        });
        setSourceDir(data.path);
        setResult(data);
      } else if (format === "gguf") {
        if (!sourceDir) {
          setError("Run safetensors export first; GGUF converts from disk.");
          return;
        }
        const data = await apiFetch("/api/export/gguf", {
          method: "POST",
          body: JSON.stringify({
            source_dir: sourceDir,
            quantization: ggufQuantization,
          }),
        });
        setResult(data);
      } else if (format === "hub") {
        if (!sourceDir || !hubRepoId) {
          setError("Need source_dir (from safetensors export) and a repo id.");
          return;
        }
        const data = await apiFetch("/api/export/hub", {
          method: "POST",
          body: JSON.stringify({
            source_dir: sourceDir,
            repo_id: hubRepoId,
            private: hubPrivate,
          }),
        });
        setResult(data);
      }
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card p-5 space-y-4">
      <header>
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Export
        </h3>
        <p className="text-xs text-muted mt-1">
          safetensors saves locally. GGUF requires llama.cpp installed. Hub pushes to HuggingFace.
        </p>
      </header>

      <div className="grid grid-cols-3 gap-2">
        {["safetensors", "gguf", "hub"].map((f) => (
          <button
            key={f}
            onClick={() => setFormat(f)}
            className={`p-2 rounded-md border text-xs font-mono transition-colors ${
              format === f
                ? "border-accent bg-panel text-accent"
                : "border-border bg-card text-text hover:border-muted"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {format === "safetensors" && (
        <LabeledField label="Output directory (optional)">
          <input
            className="input"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            placeholder="./exports/my-model"
          />
        </LabeledField>
      )}

      {format === "gguf" && (
        <div className="space-y-3">
          <LabeledField label="Source directory (from safetensors export)">
            <input
              className="input"
              value={sourceDir}
              onChange={(e) => setSourceDir(e.target.value)}
              placeholder="./exports/my-model"
            />
          </LabeledField>
          <LabeledField label="Quantization">
            <select
              className="input"
              value={ggufQuantization}
              onChange={(e) => setGgufQuantization(e.target.value)}
            >
              {["F16", "BF16", "F32", "Q8_0", "AUTO"].map((q) => (
                <option key={q} value={q}>
                  {q}
                </option>
              ))}
            </select>
          </LabeledField>
        </div>
      )}

      {format === "hub" && (
        <div className="space-y-3">
          <LabeledField label="Source directory">
            <input
              className="input"
              value={sourceDir}
              onChange={(e) => setSourceDir(e.target.value)}
            />
          </LabeledField>
          <LabeledField label="Repo id (e.g. your-user/model-name)">
            <input
              className="input"
              value={hubRepoId}
              onChange={(e) => setHubRepoId(e.target.value)}
            />
          </LabeledField>
          <label className="flex items-center gap-2 text-xs font-mono text-muted">
            <input
              type="checkbox"
              checked={hubPrivate}
              onChange={(e) => setHubPrivate(e.target.checked)}
            />
            private repo
          </label>
        </div>
      )}

      <button className="btn-primary" onClick={run} disabled={busy}>
        {busy ? "Exporting..." : `Export as ${format}`}
      </button>

      {result && (
        <div className="bg-panel rounded p-3 font-mono text-xs space-y-1">
          {Object.entries(result).map(([k, v]) => (
            <div key={k} className="flex gap-2">
              <span className="text-muted">{k}:</span>
              <span className="text-accent break-all">{String(v)}</span>
            </div>
          ))}
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

function LabeledField({ label, children }) {
  return (
    <label className="space-y-1 block">
      <div className="text-[10px] font-mono text-muted uppercase tracking-wide">
        {label}
      </div>
      {children}
    </label>
  );
}
