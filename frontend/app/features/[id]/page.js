"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

export default function FeatureDetailPage({ params }) {
  const featureId = Number(params.id);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);
  const [labelInput, setLabelInput] = useState("");
  const [autoLabeling, setAutoLabeling] = useState(false);

  const refresh = async () => {
    try {
      const data = await apiFetch(`/api/sae/features/${featureId}`);
      setInfo(data);
      setLabelInput(data.label || "");
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [featureId]);

  const saveLabel = async () => {
    if (!labelInput.trim()) return;
    await apiFetch("/api/sae/label/manual", {
      method: "POST",
      body: JSON.stringify({ feature_id: featureId, label: labelInput.trim() }),
    });
    await refresh();
  };

  const autoLabel = async () => {
    setAutoLabeling(true);
    try {
      await apiFetch("/api/sae/label", {
        method: "POST",
        body: JSON.stringify({
          feature_ids: [featureId],
          examples_per_feature: 8,
        }),
      });
      await refresh();
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setAutoLabeling(false);
    }
  };

  if (error) {
    return (
      <div className="max-w-xl mx-auto space-y-4 pt-10">
        <Link href="/features" className="text-xs font-mono text-muted hover:text-accent">
          ← back to features
        </Link>
        <div className="text-sm text-danger font-mono">{error}</div>
      </div>
    );
  }

  if (!info) {
    return <div className="text-xs font-mono text-muted">Loading...</div>;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <Link href="/features" className="text-xs font-mono text-muted hover:text-accent">
        ← back to features
      </Link>

      <header>
        <div className="text-xs font-mono text-muted uppercase tracking-wide">
          Feature
        </div>
        <h1 className="text-3xl font-mono text-accent">#{info.id}</h1>
      </header>

      <div className="card p-5 space-y-3">
        <div className="text-xs font-mono text-muted uppercase tracking-wide">
          Label
        </div>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            value={labelInput}
            onChange={(e) => setLabelInput(e.target.value)}
            placeholder="e.g. 'References to legal proceedings'"
          />
          <button className="btn-primary" onClick={saveLabel}>
            Save
          </button>
          <button
            className="btn-primary bg-panel text-text hover:bg-border"
            onClick={autoLabel}
            disabled={autoLabeling}
          >
            {autoLabeling ? "Labeling..." : "Auto-label"}
          </button>
        </div>
        {info.category && (
          <div className="text-xs font-mono">
            <span className="text-muted">category:</span>{" "}
            <span className="text-accent">{info.category}</span>
          </div>
        )}
      </div>

      <div className="card p-5 space-y-2">
        <div className="text-xs font-mono text-muted uppercase tracking-wide">
          Decoder direction
        </div>
        <div className="text-xs font-mono">
          norm: <span className="text-accent">{info.direction_norm.toFixed(4)}</span>
        </div>
        <div className="bg-panel p-3 rounded font-mono text-[10px] break-all">
          [{info.direction_preview.map((v) => v.toFixed(3)).join(", ")}, ...]
        </div>
      </div>
    </div>
  );
}
