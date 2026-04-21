import { MAX_WS_RECONNECT_DELAY_MS, WS_RECONNECT_DELAYS_MS } from "./config";
import { readBackendUrl } from "./storage";

function httpToWs(url) {
  if (url.startsWith("https://")) return "wss://" + url.slice(8);
  if (url.startsWith("http://")) return "ws://" + url.slice(7);
  return url;
}

export function createWebSocket({ onEvent, onOpen, onClose }) {
  let attempt = 0;
  let socket = null;
  let closedByClient = false;
  let reconnectTimer = null;

  function connect() {
    const url = `${httpToWs(readBackendUrl())}/ws`;
    socket = new WebSocket(url);

    socket.onopen = () => {
      attempt = 0;
      if (onOpen) onOpen();
    };

    socket.onmessage = (event) => {
      if (!onEvent) return;
      try {
        const parsed = JSON.parse(event.data);
        onEvent(parsed.event, parsed.data);
      } catch (err) {
        console.warn("ws: bad message", err);
      }
    };

    socket.onclose = () => {
      if (onClose) onClose();
      if (closedByClient) return;
      scheduleReconnect();
    };

    socket.onerror = () => {
      // onclose will fire next; reconnect logic lives there.
    };
  }

  function scheduleReconnect() {
    const delay =
      WS_RECONNECT_DELAYS_MS[Math.min(attempt, WS_RECONNECT_DELAYS_MS.length - 1)] ||
      MAX_WS_RECONNECT_DELAY_MS;
    attempt += 1;
    reconnectTimer = setTimeout(connect, delay);
  }

  function close() {
    closedByClient = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (socket) socket.close();
  }

  connect();
  return { close };
}
