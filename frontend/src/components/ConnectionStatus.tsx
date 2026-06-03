"use client";

import { clsx } from "clsx";
import type { ConnectionStatus } from "@/hooks/useWebSocket";

const CONFIG: Record<
  ConnectionStatus,
  { label: string; dot: string; text: string }
> = {
  connected: {
    label: "Live",
    dot: "bg-green-500 animate-pulse",
    text: "text-green-400",
  },
  connecting: {
    label: "Connecting…",
    dot: "bg-yellow-500 animate-pulse",
    text: "text-yellow-400",
  },
  disconnected: {
    label: "Reconnecting",
    dot: "bg-orange-500",
    text: "text-orange-400",
  },
  error: {
    label: "Offline",
    dot: "bg-red-500",
    text: "text-red-400",
  },
};

export function ConnectionStatus({ status }: { status: ConnectionStatus }) {
  const cfg = CONFIG[status];
  return (
    <div
      className={clsx(
        "inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium",
        cfg.text,
      )}
    >
      <span className={clsx("h-2 w-2 rounded-full", cfg.dot)} />
      {cfg.label}
    </div>
  );
}
