"use client";

import { useStore } from "@/lib/store";

export default function ProgressOverlay() {
  const model = useStore((state) => state.model);

  if (model.status !== "loading") return null;

  const pct = Math.round((model.progress || 0) * 100);

  return (
    <div className="fixed inset-0 z-50 bg-bg/90 backdrop-blur-sm flex items-center justify-center">
      <div className="card card-glow w-full max-w-md p-6 space-y-4">
        <div>
          <div className="text-xs font-mono text-muted uppercase tracking-wide">
            Loading model
          </div>
          <div className="text-lg font-mono mt-1">{model.id}</div>
        </div>
        <div className="space-y-2">
          <div className="h-2 bg-panel rounded-full overflow-hidden">
            <div
              className="h-full bg-accent transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between text-xs font-mono text-muted">
            <span>{model.message || "..."}</span>
            <span>{pct}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
