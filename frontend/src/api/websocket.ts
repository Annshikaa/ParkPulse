import type { WSMessage } from "@/types";

export function createWebSocket(
  onMessage: (msg: WSMessage) => void,
  onStatusChange?: (connected: boolean) => void
): () => void {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${window.location.host}/stream/ws`;

  let ws: WebSocket | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let destroyed = false;

  function connect() {
    if (destroyed) return;
    ws = new WebSocket(url);

    ws.onopen = () => {
      onStatusChange?.(true);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as WSMessage;
        onMessage(msg);
      } catch {
        // malformed message — ignore
      }
    };

    ws.onclose = () => {
      onStatusChange?.(false);
      if (!destroyed) {
        reconnectTimer = setTimeout(connect, 2000);
      }
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  connect();

  return () => {
    destroyed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    ws?.close();
  };
}
