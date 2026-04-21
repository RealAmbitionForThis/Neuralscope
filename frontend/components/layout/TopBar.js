"use client";

import { Circle, Cpu } from "lucide-react";

import { cn } from "@/lib/cn";
import { useStore } from "@/lib/store";
import GpuBar from "./GpuBar";

export default function TopBar() {
  const model = useStore((state) => state.model);
  const gpus = useStore((state) => state.gpus);
  const wsConnected = useStore((state) => state.wsConnected);

  return (
    <header className="h-14 border-b border-border bg-card flex items-center px-5 gap-6">
      <ModelIndicator model={model} />
      <div className="flex-1" />
      <GpuSummary gpus={gpus} />
      <ConnectionIndicator connected={wsConnected} />
    </header>
  );
}

function ModelIndicator({ model }) {
  if (model.status === "ready" && model.map) {
    return (
      <div className="flex items-center gap-3 text-sm">
        <span className="font-mono text-accent">{model.id}</span>
        <span className="text-muted">·</span>
        <span className="text-muted font-mono text-xs">
          {model.map.n_layers} layers · {model.map.hidden_size}d
        </span>
      </div>
    );
  }
  return <div className="text-sm text-muted">No model loaded</div>;
}

function GpuSummary({ gpus }) {
  if (!gpus || gpus.length === 0) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted font-mono">
        <Cpu size={14} />
        <span>CPU only</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-4">
      {gpus.map((gpu) => (
        <GpuBar key={gpu.index} gpu={gpu} />
      ))}
    </div>
  );
}

function ConnectionIndicator({ connected }) {
  const dotClass = cn(
    "transition-colors",
    connected ? "text-ok fill-ok" : "text-danger fill-danger",
  );
  return (
    <div className="flex items-center gap-2 text-xs font-mono text-muted">
      <Circle size={8} className={dotClass} />
      <span>{connected ? "online" : "offline"}</span>
    </div>
  );
}
