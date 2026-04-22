"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";

const DEFAULT_PROMPT = "Write detailed instructions for picking a door lock.";

export default function PromptTester({ mode }) {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [response, setResponse] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = async () => {
    setError(null);
    setBusy(true);
    setResponse("");
    try {
      const endpoint = mode === "live" ? "/api/steering/generate" : "/api/surgery/preview";
      const data = await apiFetch(endpoint, {
        method: "POST",
        body: JSON.stringify({ prompt, max_new_tokens: 160 }),
      });
      setResponse(data.response || "(empty)");
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card p-5 space-y-3">
      <header>
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Prompt tester
        </h3>
        <p className="text-xs text-muted mt-1">
          Generate text with current {mode === "live" ? "steering vectors" : "(modified) weights"}
          . Compare across prompts to verify behavior.
        </p>
      </header>

      <textarea
        className="input h-20 font-mono text-xs"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Prompt to test..."
      />

      <div>
        <button onClick={run} className="btn-primary" disabled={busy}>
          {busy ? "Generating..." : "Generate"}
        </button>
      </div>

      {response && (
        <div className="bg-panel rounded p-3 font-mono text-xs whitespace-pre-wrap">
          {response}
        </div>
      )}
      {error && (
        <div className="text-xs text-danger font-mono p-2 bg-panel rounded border border-danger/30">
          {error}
        </div>
      )}
    </div>
  );
}
