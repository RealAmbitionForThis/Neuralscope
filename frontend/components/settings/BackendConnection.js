"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import { DEFAULT_BACKEND_URL } from "@/lib/config";
import { readBackendUrl, writeBackendUrl } from "@/lib/storage";

export default function BackendConnection() {
  const [url, setUrl] = useState(DEFAULT_BACKEND_URL);
  const [result, setResult] = useState(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    setUrl(readBackendUrl());
  }, []);

  const save = () => {
    writeBackendUrl(url.trim() || DEFAULT_BACKEND_URL);
    setResult({ kind: "info", message: "Saved. Reload to reconnect WebSocket." });
  };

  const test = async () => {
    setTesting(true);
    setResult(null);
    const started = performance.now();
    try {
      writeBackendUrl(url.trim() || DEFAULT_BACKEND_URL);
      const data = await apiFetch("/api/system/gpu");
      const latency = Math.round(performance.now() - started);
      setResult({
        kind: "ok",
        message: `Connected in ${latency}ms · ${data.gpus.length} GPU(s) detected`,
      });
    } catch (err) {
      setResult({ kind: "error", message: err.message || "Connection failed" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="card p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Backend connection
        </h2>
        <p className="text-xs text-muted mt-1">
          Point the frontend at any backend — local, RunPod proxy, or anywhere else.
        </p>
      </div>
      <input
        className="input"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder={DEFAULT_BACKEND_URL}
      />
      <div className="flex gap-2">
        <button type="button" onClick={save} className="btn-primary">
          Save
        </button>
        <button
          type="button"
          onClick={test}
          disabled={testing}
          className="btn-primary bg-panel text-text hover:bg-border disabled:opacity-50"
        >
          {testing ? "Testing..." : "Test connection"}
        </button>
      </div>
      {result && <ResultLine result={result} />}
    </div>
  );
}

function ResultLine({ result }) {
  const color =
    result.kind === "ok"
      ? "text-ok"
      : result.kind === "error"
      ? "text-danger"
      : "text-muted";
  return <div className={`text-xs font-mono ${color}`}>{result.message}</div>;
}
