import PhasePlaceholder from "@/components/common/PhasePlaceholder";

export default function ExportPage() {
  return (
    <PhasePlaceholder
      title="Export modified model"
      phase="Phase 2"
      description="Save as safetensors, convert to GGUF via llama.cpp, or push directly to HuggingFace Hub with an auto-generated model card."
    />
  );
}
