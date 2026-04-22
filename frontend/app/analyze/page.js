"use client";

import { useEffect } from "react";

import ContrastivePrompts from "@/components/analyze/ContrastivePrompts";
import LayerHeatmap from "@/components/analyze/LayerHeatmap";
import RefusalStrengthChart from "@/components/analyze/RefusalStrengthChart";
import PhasePlaceholder from "@/components/common/PhasePlaceholder";
import { apiFetch } from "@/lib/api";
import { useStore } from "@/lib/store";
import { useIsModelReady } from "@/hooks/useModelStatus";

export default function AnalyzePage() {
  const modelReady = useIsModelReady();
  const analysis = useStore((state) => state.analysis);

  useEffect(() => {
    if (!modelReady) return;
    if (analysis.results) return;
    apiFetch("/api/analyze/refusal/results")
      .then((results) => useStore.getState().finishAnalysis(results))
      .catch(() => {});
  }, [modelReady, analysis.results]);

  if (!modelReady) {
    return (
      <PhasePlaceholder
        title="Refusal analysis"
        phase="Phase 2"
        description="Load a model to continue."
      />
    );
  }

  const results = analysis.results;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Refusal analysis</h1>
        <p className="text-sm text-muted mt-1">
          Diff-in-means direction extraction with 99.5th-percentile winsorization.
          Analysis runs in the background; progress streams via WebSocket.
        </p>
      </div>

      <ContrastivePrompts />

      {results && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RefusalStrengthChart
            strengths={results.refusal_strengths}
            separability={results.separability_scores}
            bestLayer={results.best_layer}
          />
          <LayerHeatmap
            harmfulProjections={results.harmful_projections}
            harmlessProjections={results.harmless_projections}
            bestLayer={results.best_layer}
          />
        </div>
      )}
    </div>
  );
}
