import { useEffect, useRef, useState } from "react";
import { createWebSocket } from "@/api/websocket";
import type { SlotWS, Stats, WSEvent } from "@/types";

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [slots, setSlots] = useState<SlotWS[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    const cleanup = createWebSocket(
      (msg) => {
        if (msg.type === "tick") {
          setSlots(msg.slots);
          setStats(msg.stats);
        } else if (msg.type === "event") {
          setLastEvent(msg);
        }
      },
      setConnected
    );
    cleanupRef.current = cleanup;
    return cleanup;
  }, []);

  return { connected, slots, stats, lastEvent };
}
