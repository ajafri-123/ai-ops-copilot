"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_URL } from "@/lib/api";
import { getToken } from "@/lib/auth";
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

export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [lastEvent, setLastEvent] = useState<WsEnvelope | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(1000);

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
    if (typeof window === "undefined") return;

    const token = getToken();
    const url = token ? `${WS_URL}?token=${encodeURIComponent(token)}` : WS_URL;
    const ws = new WebSocket(url);
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
          const data = envelope.data as SnapshotData;
          setAlerts(data.alerts ?? []);
          setIncidents(data.incidents ?? []);
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

    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
      // Exponential back-off reconnect (max 30 s)
      const delay = Math.min(reconnectDelay.current, 30000);
      reconnectDelay.current = delay * 2;
      reconnectTimer.current = setTimeout(connect, delay);
    };
  }, [pushToast]);

  useEffect(() => {
    connect();
    return () => {
      reconnectTimer.current && clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { status, alerts, incidents, lastEvent, toasts, dismissToast };
}
