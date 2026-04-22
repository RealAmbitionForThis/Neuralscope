"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

export default function FeatureBrowser() {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("page", page);
    params.set("page_size", 50);
    if (query) params.set("search", query);

    apiFetch(`/api/sae/features?${params.toString()}`)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((err) => setError(err.message || String(err)));
  }, [query, page]);

  return (
    <div className="card p-5 space-y-3">
      <header className="flex items-center gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide font-mono text-muted">
          Browse features
        </h3>
        <input
          className="input flex-1 text-xs"
          placeholder="Filter by label..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
        />
      </header>

      {data && (
        <div className="text-[10px] font-mono text-muted">
          {data.total} total · page {page + 1}
        </div>
      )}

      <div className="space-y-1 max-h-[400px] overflow-y-auto">
        {data?.features?.map((f) => (
          <Link
            key={f.id}
            href={`/features/${f.id}`}
            className="flex items-center justify-between p-2 bg-panel rounded font-mono text-xs hover:border-accent border border-transparent"
          >
            <span className="text-muted">#{f.id}</span>
            <span className="flex-1 px-3 truncate">{f.label || "(unlabeled)"}</span>
            {f.category && (
              <span className="text-[10px] px-2 py-0.5 bg-card rounded text-accent">
                {f.category}
              </span>
            )}
          </Link>
        ))}
        {!data?.features?.length && (
          <div className="text-xs text-muted font-mono">No features match.</div>
        )}
      </div>

      {data && data.total > (page + 1) * (data.page_size || 50) && (
        <button
          onClick={() => setPage((p) => p + 1)}
          className="btn-primary bg-panel text-text hover:bg-border"
        >
          Next page
        </button>
      )}

      {error && <div className="text-xs text-danger font-mono">{error}</div>}
    </div>
  );
}
