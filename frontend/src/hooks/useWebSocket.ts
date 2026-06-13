"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL, fetchAlerts, fetchIncidents } from "@/lib/api";
import { clearAuth, getToken } from "@/lib/auth";
import type {
  Alert,
  AlertCorrelatedData,
  Incident,
  IncidentEscalatedData,
  IncidentUpdatedData,
  SnapshotData,
  WsEnvelope,
} from "@/lib/types";

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";

export interface UseWebSocketReturn {
  status: ConnectionStatus;
  alerts: Alert[];
  incidents: Incident[];
  /** True until the initial REST load settles — distinguishes "loading" from "genuinely empty". */
  loading: boolean;
  lastEvent: WsEnvelope | null;
  toasts: Toast[];
  dismissToast: (id: number) => void;
}

export interface Toast {
  id: number;
  event: string;
  message: string;
  severity?: string;
  timestamp: string;
}

let toastId = 0;

/** Server closes with 4401 when the token is missing/invalid/expired. */
const WS_CLOSE_UNAUTHORIZED = 4401;

/** Union two lists by id, keeping `primary` entries (and their order) first. */
function mergeById<T extends { id: number }>(primary: T[], secondary: T[]): T[] {
  const seen = new Set(primary.map((x) => x.id));
  return [...primary, ...secondary.filter((x) => !seen.has(x.id))];
}

export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastEvent, setLastEvent] = useState<WsEnvelope | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(1000);
  const isUnmounted = useRef(false);

  const pushToast = useCallback((event: string, message: string, severity?: string) => {
    const id = ++toastId;
    setToasts((prev) => [
      { id, event, message, severity, timestamp: new Date().toISOString() },
      ...prev.slice(0, 9), // keep last 10
    ]);
    // Auto-dismiss after 6 s
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6000);
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const connect = useCallback(() => {
    if (typeof window === "undefined" || isUnmounted.current) return;

    const token = getToken();
    if (!token) {
      // The server rejects unauthenticated connections; don't bother trying.
      setStatus("disconnected");
      return;
    }
    const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
    wsRef.current = ws;
    setStatus("connecting");

    ws.onopen = () => {
      setStatus("connected");
      reconnectDelay.current = 1000; // reset backoff
    };

    ws.onmessage = (event) => {
      let envelope: WsEnvelope;
      try {
        envelope = JSON.parse(event.data as string);
      } catch {
        return;
      }
      setLastEvent(envelope);

      switch (envelope.event) {
        case "snapshot": {
          // Merge rather than replace: the REST load may already hold
          // history (e.g. resolved incidents) beyond this snapshot.
          const data = envelope.data as SnapshotData;
          setAlerts((prev) => mergeById(data.alerts ?? [], prev).slice(0, 100));
          setIncidents((prev) => mergeById(data.incidents ?? [], prev));
          break;
        }

        case "alert.created": {
          const alert = envelope.data as Alert;
          setAlerts((prev) => {
            // Prepend and deduplicate
            const exists = prev.some((a) => a.id === alert.id);
            return exists ? prev : [alert, ...prev].slice(0, 100);
          });
          pushToast(
            "alert.created",
            `[${alert.source.toUpperCase()}] ${alert.title}`,
            alert.severity,
          );
          break;
        }

        case "alert.correlated": {
          const data = envelope.data as AlertCorrelatedData;
          if (data.created_new_incident) {
            pushToast(
              "incident.created",
              `New incident #${data.incident_id}: ${data.incident_title}`,
              undefined,
            );
          }
          break;
        }

        case "incident.created": {
          const incident = envelope.data as Incident;
          setIncidents((prev) => {
            const exists = prev.some((i) => i.id === incident.id);
            return exists ? prev : [incident, ...prev];
          });
          break;
        }

        case "incident.updated": {
          const data = envelope.data as IncidentUpdatedData;
          setIncidents((prev) =>
            prev.map((i) => (i.id === data.incident.id ? data.incident : i)),
          );
          break;
        }

        case "incident.escalated": {
          const data = envelope.data as IncidentEscalatedData;
          setIncidents((prev) =>
            prev.map((i) =>
              i.id === data.incident_id
                ? { ...i, severity: data.new_severity }
                : i,
            ),
          );
          pushToast(
            "incident.escalated",
            `Incident #${data.incident_id} escalated ${data.old_severity} → ${data.new_severity}`,
            data.new_severity,
          );
          break;
        }
      }
    };

    ws.onerror = () => {
      setStatus("error");
    };

    ws.onclose = (event) => {
      wsRef.current = null;
      // Don't schedule reconnects after unmount — that leaked background
      // reconnect loops onto pages that never used this hook.
      if (isUnmounted.current) return;

      if (event.code === WS_CLOSE_UNAUTHORIZED) {
        clearAuth();
        window.location.href = "/login?expired=1";
        return;
      }

      setStatus("disconnected");
      // Exponential back-off reconnect (max 30 s)
      const delay = Math.min(reconnectDelay.current, 30000);
      reconnectDelay.current = delay * 2;
      reconnectTimer.current = setTimeout(connect, delay);
    };
  }, [pushToast]);

  // Initial data via REST: includes resolved incidents and history the tiny
  // WS snapshot can't carry, and keeps the dashboard usable if WS is blocked.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [alertRes, incidentRes] = await Promise.all([
          fetchAlerts({ limit: 100 }),
          fetchIncidents({ limit: 100 }),
        ]);
        if (cancelled) return;
        setAlerts((prev) => mergeById(prev, alertRes.items).slice(0, 100));
        setIncidents((prev) => mergeById(prev, incidentRes.items));
      } catch {
        // WS snapshot remains the fallback data source
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    isUnmounted.current = false;
    connect();
    return () => {
      isUnmounted.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      const ws = wsRef.current;
      if (ws) {
        // Detach handlers so onclose can't schedule work after unmount
        ws.onclose = null;
        ws.onerror = null;
        ws.onmessage = null;
        ws.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { status, alerts, incidents, loading, lastEvent, toasts, dismissToast };
}
