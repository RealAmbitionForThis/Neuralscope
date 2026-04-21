"use client";

import { apiFetch } from "@/lib/api";
import { useStore } from "@/lib/store";

export default function ModelInfo() {
  const model = useStore((state) => state.model);

  if (model.status !== "ready" || !model.map) return null;

  const { map } = model;

  return (
    <div className="card p-5 space-y-4">
      <header className="flex items-start justify-between">
        <div>
          <div className="text-xs font-mono text-muted uppercase tracking-wide">
            Loaded model
          </div>
          <div className="text-xl font-mono mt-1 text-accent">{model.id}</div>
        </div>
        <UnloadButton />
      </header>

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <Stat label="Architecture" value={map.architecture || "unknown"} />
        <Stat label="Model type" value={map.model_type || "unknown"} />
        <Stat label="Layers" value={map.n_layers ?? "?"} />
        <Stat label="Hidden size" value={map.hidden_size ?? "?"} />
        <Stat label="Total params" value={formatParams(map.total_parameters)} />
        <Stat label="Size" value={`${map.total_size_gb ?? "?"} GB`} />
        <Stat
          label="Layer path"
          value={<code className="font-mono">{map.layer_path_template || "n/a"}</code>}
        />
        <Stat label="Devices" value={(map.devices || []).join(", ") || "n/a"} />
      </dl>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="flex flex-col">
      <dt className="text-[10px] text-muted uppercase tracking-wide font-mono">
        {label}
      </dt>
      <dd className="text-sm mt-0.5">{value}</dd>
    </div>
  );
}

function UnloadButton() {
  const onClick = async () => {
    try {
      await apiFetch("/api/model/unload", { method: "POST" });
    } catch (err) {
      console.error("unload failed", err);
    }
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-xs font-mono text-muted hover:text-danger transition-colors"
    >
      unload
    </button>
  );
}

function formatParams(count) {
  if (!count) return "?";
  if (count >= 1e9) return `${(count / 1e9).toFixed(2)}B`;
  if (count >= 1e6) return `${(count / 1e6).toFixed(1)}M`;
  if (count >= 1e3) return `${(count / 1e3).toFixed(1)}K`;
  return String(count);
}
