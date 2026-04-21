import ModelInfo from "@/components/model/ModelInfo";
import ModelLoader from "@/components/model/ModelLoader";

export default function HomePage() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Load a model</h1>
        <p className="text-sm text-muted mt-1">
          Enter a HuggingFace model id. GPT-2 loads on CPU and is the recommended
          first test target.
        </p>
      </div>

      <div className="card p-5">
        <ModelLoader />
      </div>

      <ModelInfo />
    </div>
  );
}
