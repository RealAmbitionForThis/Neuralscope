import { STORAGE_KEYS, DEFAULT_BACKEND_URL } from "./config";

export function readBackendUrl() {
  if (typeof window === "undefined") return DEFAULT_BACKEND_URL;
  return localStorage.getItem(STORAGE_KEYS.backendUrl) || DEFAULT_BACKEND_URL;
}

export function writeBackendUrl(url) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEYS.backendUrl, url);
}

export function readToken(key) {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(key) || "";
}

export function writeToken(key, value) {
  if (typeof window === "undefined") return;
  if (!value) {
    localStorage.removeItem(key);
    return;
  }
  localStorage.setItem(key, value);
}
