"use client";

import PhasePlaceholder from "@/components/common/PhasePlaceholder";
import ExportPanel from "@/components/export/ExportPanel";
import { useIsModelReady } from "@/hooks/useModelStatus";

export default function ExportPage() {
  const modelReady = useIsModelReady();

  if (!modelReady) {
    return (
      <PhasePlaceholder
        title="Export modified model"
        phase="Phase 2"
        description="Load a model to continue."
      />
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Export</h1>
        <p className="text-sm text-muted mt-1">
          Save the current (possibly-modified) model to disk, convert to GGUF,
          or push to HuggingFace Hub.
        </p>
      </div>
      <ExportPanel />
    </div>
  );
}
