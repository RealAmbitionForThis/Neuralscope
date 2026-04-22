"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import PhasePlaceholder from "@/components/common/PhasePlaceholder";
import FeatureBrowser from "@/components/features/FeatureBrowser";
import FeatureMap from "@/components/features/FeatureMap";
import SAELoader from "@/components/features/SAELoader";
import { apiFetch } from "@/lib/api";
import { useIsModelReady } from "@/hooks/useModelStatus";

export default function FeaturesPage() {
  const modelReady = useIsModelReady();
  const router = useRouter();
  const [sae, setSae] = useState(null);

  useEffect(() => {
    apiFetch("/api/sae/info")
      .then(setSae)
      .catch(() => setSae(null));
  }, []);

  if (!modelReady) {
    return (
      <PhasePlaceholder
        title="SAE feature browser"
        phase="Phase 3"
        description="Load a model to continue."
      />
    );
  }

  if (!sae) {
    return (
      <div className="max-w-xl mx-auto space-y-4 pt-10">
        <h1 className="text-2xl font-semibold">Features</h1>
        <p className="text-sm text-muted">
          Load a pretrained Sparse Autoencoder (SAE) to browse and visualize
          its features. Gemma Scope SAEs cover Gemma 2; Joseph Bloom's SAEs
          cover GPT-2 small.
        </p>
        <SAELoader onLoaded={setSae} />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Features</h1>
          <p className="text-sm text-muted mt-1 font-mono">
            {sae.release} · {sae.sae_id} · L{sae.layer} ·
            {" "}{sae.d_sae.toLocaleString()} features
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <FeatureMap
            onFeatureClick={(id) => router.push(`/features/${id}`)}
          />
        </div>
        <FeatureBrowser />
      </div>
    </div>
  );
}
