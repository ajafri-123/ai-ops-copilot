"use client";

import { clsx } from "clsx";
import type { ConnectionStatus } from "@/hooks/useWebSocket";

const CONFIG: Record<ConnectionStatus, { label: string; dot: string; ring: string; text: string; bg: string; border: string }> = {
  connected: {
    label:  "Live",
    dot:    "bg-green-500",
    ring:   "bg-green-500",
    text:   "text-green-400",
    bg:     "bg-green-500/[0.07]",
    border: "border-green-500/20",
  },
  connecting: {
    label:  "Connecting",
    dot:    "bg-yellow-500 animate-pulse",
    ring:   "bg-yellow-500",
    text:   "text-yellow-400",
    bg:     "bg-yellow-500/[0.07]",
    border: "border-yellow-500/20",
  },
  disconnected: {
    label:  "Reconnecting",
    dot:    "bg-orange-500 animate-pulse",
    ring:   "bg-orange-500",
    text:   "text-orange-400",
    bg:     "bg-orange-500/[0.07]",
    border: "border-orange-500/20",
  },
  error: {
    label:  "Offline",
    dot:    "bg-red-500",
    ring:   "bg-red-500",
    text:   "text-red-400",
    bg:     "bg-red-500/[0.07]",
    border: "border-red-500/20",
  },
};

export function ConnectionStatus({ status }: { status: ConnectionStatus }) {
  const cfg = CONFIG[status];
  return (
    <div className={clsx(
      "inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide",
      cfg.text, cfg.bg, cfg.border,
    )}>
      <span className="relative flex h-2 w-2 flex-shrink-0">
        {(status === "connected" || status === "connecting") && (
          <span className={clsx("animate-ping-slow absolute inline-flex h-full w-full rounded-full opacity-60", cfg.ring)} />
        )}
        <span className={clsx("relative inline-flex h-2 w-2 rounded-full", cfg.dot)} />
      </span>
      {cfg.label}
    </div>
  );
}
