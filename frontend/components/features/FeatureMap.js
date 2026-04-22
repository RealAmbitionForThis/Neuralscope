"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";

const POINT_SIZE = 3;
const CLUSTER_PALETTE = [
  "#00f0ff", "#ff9d00", "#ff3333", "#00ff88", "#b366ff",
  "#ffd700", "#ff6ec7", "#00b3ff", "#66ff66", "#ff6a00",
];

export default function FeatureMap({ onFeatureClick }) {
  const canvasRef = useRef(null);
  const [map, setMap] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hovered, setHovered] = useState(null);

  const build = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch("/api/sae/map", {
        method: "POST",
        body: JSON.stringify({ n_clusters: 50, subsample: 5000 }),
      });
      setMap(data);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!map || !canvasRef.current) return;
    _draw(canvasRef.current, map);
  }, [map]);

  const onClick = (e) => {
    if (!map) return;
    const index = _hitTest(canvasRef.current, map, e);
    if (index !== null && onFeatureClick) {
      onFeatureClick(map.feature_indices[index]);
    }
  };

  const onMove = (e) => {
    if (!map) return;
    const index = _hitTest(canvasRef.current, map, e);
    setHovered(index === null ? null : map.feature_indices[index]);
  };

  return (
    <div className="card p-5 space-y-3">
      <header className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
            Feature map (UMAP)
          </h3>
          <p className="text-xs text-muted mt-1">
            2D projection of decoder weight vectors; color = cluster.
          </p>
        </div>
        <button onClick={build} disabled={loading} className="btn-primary">
          {loading ? "Computing..." : map ? "Rebuild" : "Build map"}
        </button>
      </header>

      <div className="relative">
        <canvas
          ref={canvasRef}
          width={800}
          height={500}
          onClick={onClick}
          onMouseMove={onMove}
          className="bg-panel rounded-md cursor-crosshair"
        />
        {hovered !== null && (
          <div className="absolute top-2 right-2 text-xs font-mono bg-card p-2 rounded border border-border">
            feature #{hovered}
          </div>
        )}
        {!map && !loading && (
          <div className="absolute inset-0 flex items-center justify-center text-xs text-muted">
            Click "Build map" to compute the UMAP embedding.
          </div>
        )}
      </div>

      {error && (
        <div className="text-xs text-danger font-mono">{error}</div>
      )}
    </div>
  );
}

function _draw(canvas, map) {
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#15151f";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const { xs, ys, extents } = _bounds(map.coordinates);
  const padding = 20;
  const scaleX = (canvas.width - 2 * padding) / (extents.xMax - extents.xMin || 1);
  const scaleY = (canvas.height - 2 * padding) / (extents.yMax - extents.yMin || 1);

  map.coordinates.forEach(([x, y], i) => {
    const cx = padding + (x - extents.xMin) * scaleX;
    const cy = canvas.height - padding - (y - extents.yMin) * scaleY;
    const color = CLUSTER_PALETTE[map.cluster_ids[i] % CLUSTER_PALETTE.length];
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, POINT_SIZE, 0, Math.PI * 2);
    ctx.fill();
  });
}

function _bounds(coords) {
  let xMin = Infinity,
    xMax = -Infinity,
    yMin = Infinity,
    yMax = -Infinity;
  coords.forEach(([x, y]) => {
    if (x < xMin) xMin = x;
    if (x > xMax) xMax = x;
    if (y < yMin) yMin = y;
    if (y > yMax) yMax = y;
  });
  return {
    xs: coords.map(([x]) => x),
    ys: coords.map(([, y]) => y),
    extents: { xMin, xMax, yMin, yMax },
  };
}

function _hitTest(canvas, map, event) {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const { extents } = _bounds(map.coordinates);
  const padding = 20;
  const scaleX = (canvas.width - 2 * padding) / (extents.xMax - extents.xMin || 1);
  const scaleY = (canvas.height - 2 * padding) / (extents.yMax - extents.yMin || 1);

  for (let i = 0; i < map.coordinates.length; i += 1) {
    const [px, py] = map.coordinates[i];
    const cx = padding + (px - extents.xMin) * scaleX;
    const cy = canvas.height - padding - (py - extents.yMin) * scaleY;
    const dx = cx - x;
    const dy = cy - y;
    if (dx * dx + dy * dy <= POINT_SIZE * POINT_SIZE * 4) {
      return i;
    }
  }
  return null;
}
