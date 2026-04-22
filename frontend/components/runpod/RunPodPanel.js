"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import PodLauncher from "./PodLauncher";
import PodList from "./PodList";

export default function RunPodPanel() {
  const [connected, setConnected] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [gpuCount, setGpuCount] = useState(0);
  const [error, setError] = useState(null);

  const connect = async () => {
    setError(null);
    try {
      const result = await apiFetch("/api/runpod/connect", {
        method: "POST",
        body: JSON.stringify({ api_key: apiKey }),
      });
      setConnected(true);
      setGpuCount(result.gpu_types_available || 0);
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  return (
    <div className="space-y-5">
      <div className="card p-5 space-y-3">
        <header>
          <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
            RunPod connection
          </h3>
          <p className="text-xs text-muted mt-1">
            Launch and manage NeuralScope pods directly from here. API key is
            held in backend memory only (never persisted).
          </p>
        </header>
        <input
          type="password"
          className="input"
          placeholder="RunPod API key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <button className="btn-primary" onClick={connect} disabled={!apiKey}>
          Connect
        </button>
        {connected && (
          <div className="text-xs font-mono text-ok">
            connected · {gpuCount} GPU types available
          </div>
        )}
        {error && (
          <div className="text-xs font-mono text-danger">{error}</div>
        )}
      </div>

      {connected && <PodLauncher />}
      {connected && <PodList />}
    </div>
  );
}
