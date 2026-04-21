"use client";

import { cn } from "@/lib/cn";

export default function GpuBar({ gpu }) {
  const pct = gpu.utilization_pct ?? 0;
  const fillClass = cn(
    "h-1.5 rounded-full transition-all duration-300",
    pct > 90 && "bg-danger",
    pct > 70 && pct <= 90 && "bg-warn",
    pct <= 70 && "bg-accent",
  );

  return (
    <div className="flex flex-col gap-1 min-w-[140px]">
      <div className="flex items-center justify-between text-[10px] text-muted font-mono">
        <span>GPU {gpu.index}</span>
        <span>
          {gpu.allocated_gb}/{gpu.total_gb} GB
        </span>
      </div>
      <div className="h-1.5 bg-panel rounded-full overflow-hidden">
        <div className={fillClass} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
