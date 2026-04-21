export const DEFAULT_BACKEND_URL = "http://localhost:8000";

export const STORAGE_KEYS = {
  backendUrl: "neuralscope_backend_url",
  hfToken: "neuralscope_hf_token",
  apiKey: "neuralscope_api_key",
};

export const WS_RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000];

export const MAX_WS_RECONNECT_DELAY_MS = 30000;
