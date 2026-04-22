"use client";

import { useMemo } from "react";

export default function RefusalStrengthChart({ strengths, separability, bestLayer }) {
  const data = useMemo(() => _buildData(strengths, separability), [
    strengths,
    separability,
  ]);

  if (!data.length) return null;

  const maxStrength = Math.max(...data.map((d) => d.strength));
  const maxSeparability = Math.max(...data.map((d) => d.separability));

  return (
    <div className="card p-5">
      <header className="mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Per-layer refusal strength
        </h3>
        <p className="text-xs text-muted mt-1">
          Highlighted layer is the one with the highest separability between
          harmful and harmless activations.
        </p>
      </header>
      <div className="space-y-1.5">
        {data.map((d) => (
          <Row
            key={d.layer}
            row={d}
            maxStrength={maxStrength}
            maxSeparability={maxSeparability}
            best={d.layer === bestLayer}
          />
        ))}
      </div>
    </div>
  );
}

function Row({ row, maxStrength, maxSeparability, best }) {
  const strengthPct = (row.strength / maxStrength) * 100;
  const sepPct = (row.separability / maxSeparability) * 100;
  return (
    <div className="flex items-center gap-3 text-xs font-mono">
      <span className={`w-8 text-right ${best ? "text-accent" : "text-muted"}`}>
        L{row.layer}
      </span>
      <div className="flex-1 flex gap-1">
        <div className="flex-1 h-4 bg-panel rounded overflow-hidden">
          <div
            className={`h-full ${best ? "bg-accent" : "bg-muted/60"}`}
            style={{ width: `${strengthPct}%` }}
            title={`strength ${row.strength.toFixed(3)}`}
          />
        </div>
        <div className="flex-1 h-4 bg-panel rounded overflow-hidden">
          <div
            className={`h-full ${best ? "bg-warn" : "bg-muted/40"}`}
            style={{ width: `${sepPct}%` }}
            title={`separability ${row.separability.toFixed(3)}`}
          />
        </div>
      </div>
      <span className="w-12 text-right text-muted">
        {row.separability.toFixed(2)}
      </span>
    </div>
  );
}

function _buildData(strengths, separability) {
  if (!strengths || !separability) return [];
  return Object.keys(strengths)
    .map((key) => ({
      layer: Number(key),
      strength: strengths[key],
      separability: separability[key] ?? 0,
    }))
    .sort((a, b) => a.layer - b.layer);
}
