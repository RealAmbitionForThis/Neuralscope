"use client";

import { cn } from "@/lib/cn";

const MODES = [
  { value: "permanent", label: "Permanent (weight surgery)", hint: "Modifies weights; use undo to revert." },
  { value: "live", label: "Live (inference steering)", hint: "Reversible; no weight changes." },
];

export default function ModeToggle({ value, onChange }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {MODES.map((mode) => (
        <button
          key={mode.value}
          type="button"
          onClick={() => onChange(mode.value)}
          className={cn(
            "p-3 rounded-md border text-left transition-colors",
            value === mode.value
              ? "border-accent bg-panel text-accent"
              : "border-border bg-card text-text hover:border-muted",
          )}
        >
          <div className="text-sm font-mono">{mode.label}</div>
          <div className="text-[10px] text-muted mt-1">{mode.hint}</div>
        </button>
      ))}
    </div>
  );
}
