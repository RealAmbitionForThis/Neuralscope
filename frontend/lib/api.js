import { STORAGE_KEYS } from "./config";
import { readBackendUrl, readToken } from "./storage";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function buildHeaders(extra) {
  const headers = { "Content-Type": "application/json", ...(extra || {}) };
  const apiKey = readToken(STORAGE_KEYS.apiKey);
  const hfToken = readToken(STORAGE_KEYS.hfToken);
  if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`;
  if (hfToken) headers["X-HF-Token"] = hfToken;
  return headers;
}

async function parseError(response) {
  try {
    const body = await response.json();
    return body.detail || response.statusText;
  } catch (err) {
    return response.statusText;
  }
}

export async function apiFetch(path, options = {}) {
  const url = `${readBackendUrl()}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: buildHeaders(options.headers),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await parseError(response));
  }
  return response.json();
}

export function api() {
  return {
    get: (path) => apiFetch(path),
    post: (path, body) =>
      apiFetch(path, { method: "POST", body: JSON.stringify(body || {}) }),
  };
}
