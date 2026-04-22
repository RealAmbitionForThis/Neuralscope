import { create } from "zustand";

const INITIAL_MODEL_STATE = {
  id: null,
  status: "idle",
  progress: 0,
  message: "",
  map: null,
  error: null,
};

const INITIAL_ANALYSIS_STATE = {
  status: "idle",
  progress: 0,
  message: "",
  results: null,
  error: null,
};

export const useStore = create((set) => ({
  wsConnected: false,
  gpus: [],
  model: { ...INITIAL_MODEL_STATE },
  analysis: { ...INITIAL_ANALYSIS_STATE },
  surgery: { lastReport: null, error: null },
  steering: { active: [], lastResponse: null },

  setWsConnected: (wsConnected) => set({ wsConnected }),
  setGpus: (gpus) => set({ gpus }),

  startModelLoad: (id) =>
    set({
      model: {
        ...INITIAL_MODEL_STATE,
        id,
        status: "loading",
        progress: 0,
        message: "Starting...",
      },
    }),

  updateModelProgress: ({ progress, message }) =>
    set((state) => ({
      model: { ...state.model, progress, message, status: "loading" },
    })),

  finishModelLoad: ({ modelId, map }) =>
    set({
      model: {
        id: modelId,
        status: "ready",
        progress: 1,
        message: "Ready",
        map,
        error: null,
      },
      analysis: { ...INITIAL_ANALYSIS_STATE },
      surgery: { lastReport: null, error: null },
      steering: { active: [], lastResponse: null },
    }),

  failModelLoad: (message) =>
    set((state) => ({
      model: { ...state.model, status: "error", error: message },
    })),

  unloadModel: () =>
    set({
      model: { ...INITIAL_MODEL_STATE },
      analysis: { ...INITIAL_ANALYSIS_STATE },
    }),

  startAnalysis: () =>
    set({
      analysis: { ...INITIAL_ANALYSIS_STATE, status: "running" },
    }),

  updateAnalysisProgress: ({ progress, message }) =>
    set((state) => ({
      analysis: { ...state.analysis, progress, message, status: "running" },
    })),

  finishAnalysis: (results) =>
    set({
      analysis: {
        status: "complete",
        progress: 1,
        message: "Complete",
        results,
        error: null,
      },
    }),

  failAnalysis: (message) =>
    set((state) => ({
      analysis: { ...state.analysis, status: "error", error: message },
    })),

  setSurgeryReport: (report) =>
    set({ surgery: { lastReport: report, error: null } }),

  setSurgeryError: (message) =>
    set((state) => ({
      surgery: { ...state.surgery, error: message },
    })),

  setSteeringActive: (active) =>
    set((state) => ({ steering: { ...state.steering, active } })),

  setSteeringResponse: (response) =>
    set((state) => ({ steering: { ...state.steering, lastResponse: response } })),
}));
