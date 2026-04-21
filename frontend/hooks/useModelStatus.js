"use client";

import { useStore } from "@/lib/store";

export function useModelStatus() {
  return useStore((state) => state.model);
}

export function useIsModelReady() {
  return useStore((state) => state.model.status === "ready");
}
