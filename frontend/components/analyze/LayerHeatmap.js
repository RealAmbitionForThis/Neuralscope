"use client";

import { useMemo } from "react";

const CELL_HEIGHT = 14;
const CELL_WIDTH = 10;

export default function LayerHeatmap({ harmfulProjections, harmlessProjections, bestLayer }) {
  const { rows, extent, harmfulCount, harmlessCount } = useMemo(
    () => _buildGrid(harmfulProjections, harmlessProjections),
    [harmfulProjections, harmlessProjections],
  );

  if (!rows.length) return null;

  const width = (harmfulCount + harmlessCount + 2) * CELL_WIDTH;
  const height = rows.length * CELL_HEIGHT;

  return (
    <div className="card p-5 overflow-x-auto">
      <header className="mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Cross-layer activation heatmap
        </h3>
        <p className="text-xs text-muted mt-1">
          Each dot is one prompt projected onto that layer's refusal direction.
          Red = high projection magnitude (harmful-like), green = low.
        </p>
      </header>
      <svg width={width + 40} height={height + 20} className="font-mono text-[10px]">
        {rows.map((row) => (
          <g key={row.layer} transform={`translate(28, ${row.layer * CELL_HEIGHT})`}>
            <text
              x={-4}
              y={CELL_HEIGHT - 3}
              textAnchor="end"
              fill={row.layer === bestLayer ? "#00f0ff" : "#6b6b80"}
            >
              L{row.layer}
            </text>
            {row.cells.map((cell, index) => (
              <rect
                key={index}
                x={index * CELL_WIDTH}
                y={0}
                width={CELL_WIDTH - 1}
                height={CELL_HEIGHT - 1}
                fill={_colorFor(cell.value, extent, cell.kind)}
              >
                <title>{`L${row.layer} ${cell.kind}#${cell.index} = ${cell.value.toFixed(3)}`}</title>
              </rect>
            ))}
          </g>
        ))}
      </svg>
      <div className="flex gap-4 mt-3 text-[10px] font-mono text-muted">
        <span>
          <span className="inline-block w-3 h-3 mr-1 align-middle" style={{ background: "#ff3333" }} />
          harmful prompts
        </span>
        <span>
          <span className="inline-block w-3 h-3 mr-1 align-middle" style={{ background: "#00ff88" }} />
          harmless prompts
        </span>
      </div>
    </div>
  );
}

function _buildGrid(harmful, harmless) {
  if (!harmful || !harmless) {
    return { rows: [], extent: [0, 1], harmfulCount: 0, harmlessCount: 0 };
  }

  const layerKeys = Object.keys(harmful)
    .map(Number)
    .sort((a, b) => a - b);
  if (!layerKeys.length) {
    return { rows: [], extent: [0, 1], harmfulCount: 0, harmlessCount: 0 };
  }

  const harmfulCount = harmful[layerKeys[0]]?.length || 0;
  const harmlessCount = harmless[layerKeys[0]]?.length || 0;

  let min = Infinity;
  let max = -Infinity;
  layerKeys.forEach((layer) => {
    [...(harmful[layer] || []), ...(harmless[layer] || [])].forEach((v) => {
      if (v < min) min = v;
      if (v > max) max = v;
    });
  });

  const rows = layerKeys.map((layer) => {
    const cells = [
      ...(harmful[layer] || []).map((value, index) => ({
        value,
        kind: "harmful",
        index,
      })),
      { value: 0, kind: "gap", index: -1 },
      ...(harmless[layer] || []).map((value, index) => ({
        value,
        kind: "harmless",
        index,
      })),
    ];
    return { layer, cells };
  });

  return { rows, extent: [min, max], harmfulCount, harmlessCount };
}

function _colorFor(value, extent, kind) {
  if (kind === "gap") return "transparent";
  const [min, max] = extent;
  const range = max - min || 1;
  const t = (value - min) / range;
  const clamp = Math.max(0, Math.min(1, t));
  const intensity = Math.round(60 + clamp * 180);
  if (kind === "harmful") {
    return `rgb(${intensity + 60}, ${50}, ${50})`;
  }
  return `rgb(${30}, ${intensity + 40}, ${70})`;
}
