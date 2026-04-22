"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

export default function PodList() {
  const [pods, setPods] = useState([]);
  const [error, setError] = useState(null);

  const refresh = async () => {
    try {
      const data = await apiFetch("/api/runpod/pods");
      setPods(data.pods || []);
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const stop = async (podId) => {
    await apiFetch(`/api/runpod/pods/${podId}/stop`, { method: "POST" });
    await refresh();
  };

  const terminate = async (podId) => {
    if (!confirm(`Terminate pod ${podId}? This destroys the volume.`)) return;
    await apiFetch(`/api/runpod/pods/${podId}/terminate`, { method: "POST" });
    await refresh();
  };

  return (
    <div className="card p-5 space-y-3">
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Your pods ({pods.length})
        </h3>
        <button onClick={refresh} className="text-xs font-mono text-muted hover:text-accent">
          refresh
        </button>
      </header>

      {pods.length === 0 && (
        <div className="text-xs font-mono text-muted">No pods running.</div>
      )}

      {pods.map((pod) => (
        <PodRow key={pod.id} pod={pod} onStop={stop} onTerminate={terminate} />
      ))}

      {error && <div className="text-xs font-mono text-danger">{error}</div>}
    </div>
  );
}

function PodRow({ pod, onStop, onTerminate }) {
  const podId = pod.id || pod.podId;
  const statusRaw = pod.desiredStatus || pod.status || "unknown";
  const status = String(statusRaw).toLowerCase();
  const color =
    status === "running" ? "text-ok" : status === "exited" ? "text-muted" : "text-warn";

  return (
    <div className="flex items-center justify-between p-2 bg-panel rounded font-mono text-xs">
      <div className="flex-1 min-w-0">
        <div className="truncate">{pod.name || podId}</div>
        <div className="text-[10px] text-muted">
          {podId} · <span className={color}>{statusRaw}</span>
        </div>
      </div>
      <div className="flex gap-2">
        <button onClick={() => onStop(podId)} className="text-warn hover:underline">
          stop
        </button>
        <button onClick={() => onTerminate(podId)} className="text-danger hover:underline">
          terminate
        </button>
      </div>
    </div>
  );
}
