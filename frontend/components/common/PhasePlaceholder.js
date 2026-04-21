"use client";

import Link from "next/link";

import { useIsModelReady } from "@/hooks/useModelStatus";

export default function PhasePlaceholder({ title, phase, description }) {
  const modelReady = useIsModelReady();

  if (!modelReady) {
    return (
      <div className="max-w-xl mx-auto text-center space-y-4 pt-20">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <p className="text-sm text-muted">Load a model to continue.</p>
        <Link href="/" className="btn-primary inline-block">
          Go to model loader
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto text-center space-y-4 pt-20">
      <div className="text-xs font-mono text-warn uppercase tracking-wide">
        {phase}
      </div>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-sm text-muted">{description}</p>
    </div>
  );
}
