"use client";

import { useState } from "react";

import PhasePlaceholder from "@/components/common/PhasePlaceholder";
import ModeToggle from "@/components/surgery/ModeToggle";
import PromptTester from "@/components/surgery/PromptTester";
import SnapshotManager from "@/components/surgery/SnapshotManager";
import SteeringControls from "@/components/surgery/SteeringControls";
import SurgeryControls from "@/components/surgery/SurgeryControls";
import { useIsModelReady } from "@/hooks/useModelStatus";

export default function SurgeryPage() {
  const modelReady = useIsModelReady();
  const [mode, setMode] = useState("permanent");

  if (!modelReady) {
    return (
      <PhasePlaceholder
        title="Weight surgery"
        phase="Phase 2"
        description="Load a model to continue."
      />
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Surgery studio</h1>
        <p className="text-sm text-muted mt-1">
          Strip refusal behavior either permanently (weight orthogonalization)
          or reversibly (inference-time steering).
        </p>
      </div>

      <ModeToggle value={mode} onChange={setMode} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {mode === "permanent" ? <SurgeryControls /> : <SteeringControls />}
        <PromptTester mode={mode} />
      </div>

      <SnapshotManager />
    </div>
  );
}
