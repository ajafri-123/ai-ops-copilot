"use client";

import { clsx } from "clsx";
import { X } from "lucide-react";
import type { Toast } from "@/hooks/useWebSocket";
import { SEVERITY_DOT } from "@/lib/severity";
import type { AlertSeverity } from "@/lib/types";

interface Props {
  toasts: Toast[];
  onDismiss: (id: number) => void;
}

const EVENT_LABEL: Record<string, string> = {
  "alert.created":    "Alert",
  "incident.created": "New Incident",
  "incident.escalated": "Escalated",
  "alert.correlated": "Correlated",
};

const SEVERITY_BORDER: Record<string, string> = {
  critical: "border-l-red-500/70",
  high:     "border-l-orange-500/70",
  medium:   "border-l-amber-500/60",
  low:      "border-l-blue-500/60",
  info:     "border-l-slate-500/50",
};

export function ToastStack({ toasts, onDismiss }: Props) {
  if (toasts.length === 0) return null;
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col-reverse gap-2 w-80">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  const sev       = toast.severity as AlertSeverity | undefined;
  const dotClass  = sev ? SEVERITY_DOT[sev] : "bg-slate-500";
  const borderL   = sev ? (SEVERITY_BORDER[sev] ?? "border-l-slate-500/50") : "border-l-cyan-500/50";
  const label     = EVENT_LABEL[toast.event] ?? toast.event;

  return (
    <div className={clsx(
      "flex items-start gap-3 rounded-xl border border-cyan-500/[0.1] border-l-2 bg-[#06101f] px-4 py-3 shadow-glow-cyan",
      borderL,
      "animate-in",
    )}>
      <span className={clsx("mt-0.5 h-2 w-2 flex-shrink-0 rounded-full", dotClass)} />

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
            {label}
          </span>
        </div>
        <p className="mt-1 text-xs leading-relaxed text-slate-300 line-clamp-2">
          {toast.message}
        </p>
      </div>

      <button
        onClick={() => onDismiss(toast.id)}
        className="flex-shrink-0 text-slate-600 transition hover:text-slate-400"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
