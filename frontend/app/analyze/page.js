import PhasePlaceholder from "@/components/common/PhasePlaceholder";

export default function AnalyzePage() {
  return (
    <PhasePlaceholder
      title="Refusal analysis"
      phase="Phase 2"
      description="Cross-layer heatmap of refusal direction strength, built from contrastive prompt activations (diff-in-means with winsorization). Landing in the next commit."
    />
  );
}
