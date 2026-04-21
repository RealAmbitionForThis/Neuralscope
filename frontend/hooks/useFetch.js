"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";

export function useFetch(path, { skip = false } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: !skip });

  const run = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const data = await apiFetch(path);
      setState({ data, error: null, loading: false });
    } catch (err) {
      setState({ data: null, error: err, loading: false });
    }
  }, [path]);

  useEffect(() => {
    if (skip) return;
    run();
  }, [run, skip]);

  return { ...state, refetch: run };
}
