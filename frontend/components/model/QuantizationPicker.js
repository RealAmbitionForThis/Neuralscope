"use client";

import { cn } from "@/lib/cn";

const OPTIONS = [
  { value: "4bit", label: "4-bit", hint: "GPU, smallest VRAM" },
  { value: "8bit", label: "8-bit", hint: "GPU" },
  { value: "bf16", label: "bf16", hint: "GPU preferred" },
  { value: "fp16", label: "fp16", hint: "GPU or CPU" },
  { value: "fp32", label: "fp32", hint: "CPU testing" },
];

export default function QuantizationPicker({ value, onChange }) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            "flex flex-col items-start px-3 py-2 rounded-md border text-left transition-colors",
            value === option.value
              ? "border-accent bg-panel text-accent"
              : "border-border bg-card text-text hover:border-muted",
          )}
        >
          <span className="font-mono text-sm">{option.label}</span>
          <span className="text-[10px] text-muted mt-0.5">{option.hint}</span>
        </button>
      ))}
    </div>
  );
}
