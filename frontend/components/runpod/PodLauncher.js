"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

const FALLBACK_GPUS = [
  "NVIDIA A100 80GB PCIe",
  "NVIDIA A100-SXM4-80GB",
  "NVIDIA H100 80GB HBM3",
  "NVIDIA H100 SXM",
  "NVIDIA RTX A6000",
];

export default function PodLauncher() {
  const [gpus, setGpus] = useState(FALLBACK_GPUS.map((id) => ({ id })));
  const [gpuType, setGpuType] = useState(FALLBACK_GPUS[0]);
  const [gpuCount, setGpuCount] = useState(1);
  const [volumeGb, setVolumeGb] = useState(100);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiFetch("/api/runpod/gpus")
      .then((data) => {
        const list = (data.gpus || []).slice(0, 40);
        if (list.length) setGpus(list);
      })
      .catch(() => {});
  }, []);

  const launch = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch("/api/runpod/launch", {
        method: "POST",
        body: JSON.stringify({
          gpu_type_ids: [gpuType],
          gpu_count: gpuCount,
          volume_gb: volumeGb,
        }),
      });
      setResult(data);
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
          Launch pod
        </h3>
      </header>

      <div className="grid grid-cols-2 gap-2">
        <label className="col-span-2 space-y-1">
          <div className="text-[10px] font-mono text-muted uppercase tracking-wide">
            GPU type
          </div>
          <select
            className="input"
            value={gpuType}
            onChange={(e) => setGpuType(e.target.value)}
          >
            {gpus.map((g) => (
              <option key={g.id || g.displayName || g.name} value={g.id || g.name}>
                {g.displayName || g.name || g.id}
                {g.lowestPrice ? ` · $${g.lowestPrice}/hr` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <div className="text-[10px] font-mono text-muted uppercase tracking-wide">
            Count
          </div>
          <input
            type="number"
            className="input"
            min={1}
            max={8}
            value={gpuCount}
            onChange={(e) => setGpuCount(Number(e.target.value))}
          />
        </label>
        <label className="space-y-1">
          <div className="text-[10px] font-mono text-muted uppercase tracking-wide">
            Volume (GB)
          </div>
          <input
            type="number"
            className="input"
            min={10}
            max={5000}
            value={volumeGb}
            onChange={(e) => setVolumeGb(Number(e.target.value))}
          />
        </label>
      </div>

      <button className="btn-primary" onClick={launch} disabled={busy}>
        {busy ? "Launching..." : "Launch pod"}
      </button>

      {result && (
        <div className="bg-panel rounded p-3 font-mono text-xs space-y-1">
          <div>
            <span className="text-muted">pod_id:</span>{" "}
            <span className="text-accent">{result.pod_id}</span>
          </div>
          {result.backend_url && (
            <div>
              <span className="text-muted">backend:</span>{" "}
              <a
                href={result.backend_url}
                target="_blank"
                rel="noreferrer"
                className="text-accent hover:underline"
              >
                {result.backend_url}
              </a>
            </div>
          )}
          {result.frontend_url && (
            <div>
              <span className="text-muted">frontend:</span>{" "}
              <a
                href={result.frontend_url}
                target="_blank"
                rel="noreferrer"
                className="text-accent hover:underline"
              >
                {result.frontend_url}
              </a>
            </div>
          )}
        </div>
      )}

      {error && <div className="text-xs font-mono text-danger">{error}</div>}
    </div>
  );
}
