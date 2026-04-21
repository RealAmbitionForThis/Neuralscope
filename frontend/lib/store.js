import { create } from "zustand";

const INITIAL_MODEL_STATE = {
  id: null,
  status: "idle",
  progress: 0,
  message: "",
  map: null,
  error: null,
};

export const useStore = create((set) => ({
  wsConnected: false,
  gpus: [],
  model: { ...INITIAL_MODEL_STATE },

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
    }),

  failModelLoad: (message) =>
    set((state) => ({
      model: {
        ...state.model,
        status: "error",
        error: message,
      },
    })),

  unloadModel: () => set({ model: { ...INITIAL_MODEL_STATE } }),
}));
