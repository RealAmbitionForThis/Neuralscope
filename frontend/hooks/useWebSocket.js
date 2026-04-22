"use client";

import { useEffect } from "react";

import { createWebSocket } from "@/lib/ws";
import { useStore } from "@/lib/store";

function handleEvent(event, data, store) {
  if (event === "gpu:stats") {
    store.setGpus(data.gpus || []);
    return;
  }
  if (event === "model:loading") {
    store.updateModelProgress({
      progress: data.progress ?? 0,
      message: data.message ?? "",
    });
    return;
  }
  if (event === "model:ready") {
    store.finishModelLoad({ modelId: data.model_id, map: data.map });
    return;
  }
  if (event === "model:error") {
    store.failModelLoad(data.message || "Model load failed");
    return;
  }
  if (event === "model:unloaded") {
    store.unloadModel();
    return;
  }
  if (event === "analyze:progress") {
    store.updateAnalysisProgress({
      progress: data.progress ?? 0,
      message: data.message ?? "",
    });
    return;
  }
  if (event === "analyze:complete") {
    // Results are fetched via REST; this is just a signal.
    return;
  }
  if (event === "analyze:error") {
    store.failAnalysis(data.message || "Analysis failed");
    return;
  }
  if (event === "sae:progress" || event === "sae:label_progress") {
    // Currently only used for status indication; store could be extended later.
    return;
  }
  if (event === "sae:error") {
    console.warn("sae error:", data.message);
  }
}

export function useWebSocket() {
  const store = useStore.getState();

  useEffect(() => {
    const conn = createWebSocket({
      onEvent: (event, data) => handleEvent(event, data, useStore.getState()),
      onOpen: () => useStore.getState().setWsConnected(true),
      onClose: () => useStore.getState().setWsConnected(false),
    });
    return () => conn.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
