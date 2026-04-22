"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

export default function SnapshotManager() {
  const [snapshots, setSnapshots] = useState([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const refresh = async () => {
    try {
      const data = await apiFetch("/api/surgery/snapshots");
      setSnapshots(data.snapshots || []);
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const save = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/api/surgery/snapshots", {
        method: "POST",
        body: JSON.stringify({ name: name.trim() }),
      });
      setName("");
      await refresh();
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  const rollback = async (snapshotName) => {
    setBusy(true);
    try {
      await apiFetch(`/api/surgery/snapshots/${encodeURIComponent(snapshotName)}/rollback`, {
        method: "POST",
      });
      await refresh();
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
          Snapshots
        </h3>
        <p className="text-xs text-muted mt-1">
          Save named weight states for later comparison or rollback.
        </p>
      </header>

      <div className="flex gap-2">
        <input
          className="input flex-1"
          placeholder="snapshot name (e.g. before-surgery)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className="btn-primary" onClick={save} disabled={busy || !name.trim()}>
          Save
        </button>
      </div>

      {snapshots.length > 0 && (
        <div className="space-y-1 text-xs font-mono">
          {snapshots.map((snap) => (
            <div key={snap.name} className="flex justify-between p-2 bg-panel rounded">
              <div>
                <div>{snap.name}</div>
                <div className="text-[10px] text-muted">{snap.tensor_count} tensors</div>
              </div>
              <button
                onClick={() => rollback(snap.name)}
                className="text-accent hover:underline"
              >
                rollback
              </button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="text-xs text-danger font-mono">{error}</div>
      )}
    </div>
  );
}
