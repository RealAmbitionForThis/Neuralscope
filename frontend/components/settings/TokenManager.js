"use client";

import { useEffect, useState } from "react";

import { STORAGE_KEYS } from "@/lib/config";
import { readToken, writeToken } from "@/lib/storage";

const FIELDS = [
  {
    key: STORAGE_KEYS.hfToken,
    label: "HuggingFace token",
    placeholder: "hf_...",
    hint: "Required for gated models (Llama, Gemma, etc.).",
  },
  {
    key: STORAGE_KEYS.apiKey,
    label: "Backend API key",
    placeholder: "(optional)",
    hint: "Sent as Authorization: Bearer <token> on every request.",
  },
];

export default function TokenManager() {
  return (
    <div className="card p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Access tokens
        </h2>
        <p className="text-xs text-muted mt-1">
          Stored in your browser's localStorage. Never sent to third parties.
        </p>
      </div>
      {FIELDS.map((field) => (
        <TokenField key={field.key} field={field} />
      ))}
    </div>
  );
}

function TokenField({ field }) {
  const [value, setValue] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setValue(readToken(field.key));
  }, [field.key]);

  const save = () => {
    writeToken(field.key, value.trim());
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div className="space-y-2">
      <label className="text-xs font-mono text-muted uppercase tracking-wide">
        {field.label}
      </label>
      <div className="flex gap-2">
        <input
          type="password"
          className="input flex-1"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={field.placeholder}
        />
        <button type="button" onClick={save} className="btn-primary">
          {saved ? "Saved" : "Save"}
        </button>
      </div>
      <div className="text-[10px] text-muted">{field.hint}</div>
    </div>
  );
}
