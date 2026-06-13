"use client";

import { clsx } from "clsx";
import type { Alert } from "@/lib/types";
import { SOURCE_COLOR, SOURCE_LABEL, relativeTime } from "@/lib/severity";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  alerts: Alert[];
  loading?: boolean;
}

const SEVERITY_LEFT: Record<string, string> = {
  critical: "border-l-red-500",
  high:     "border-l-orange-500",
  medium:   "border-l-amber-500",
  low:      "border-l-blue-500",
  info:     "border-l-slate-600",
};

const SEVERITY_GLOW: Record<string, string> = {
  critical: "hover:shadow-glow-red",
  high:     "hover:shadow-glow-orange",
  medium:   "",
  low:      "",
  info:     "",
};

function AlertSkeleton() {
  return (
    <div className="flex animate-pulse gap-3 rounded-lg border border-cyan-500/[0.06] bg-[#081320] border-l-2 border-l-slate-800 px-4 py-3">
      <div className="h-6 w-10 flex-shrink-0 rounded bg-white/[0.05]" />
      <div className="flex flex-1 flex-col gap-2 pt-0.5">
        <div className="h-3.5 w-3/4 rounded bg-white/[0.05]" />
        <div className="flex gap-2">
          <div className="h-2.5 w-20 rounded bg-white/[0.04]" />
          <div className="h-2.5 w-16 rounded bg-white/[0.04]" />
        </div>
      </div>
    </div>
  );
}

export function AlertFeed({ alerts, loading = false }: Props) {
  if (loading) {
    return (
      <div className="flex flex-col gap-1.5">
        {[...Array(6)].map((_, i) => <AlertSkeleton key={i} />)}
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="flex h-48 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-cyan-500/10 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-500/15 bg-cyan-500/[0.05]">
          <span className="text-lg">📡</span>
        </div>
        <div>
          <p className="text-xs font-medium text-slate-400">No alerts</p>
          <p className="mt-0.5 text-[10px] text-slate-600">Use Demo Scenarios to generate some</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      {alerts.map((alert) => (
        <AlertRow key={alert.id} alert={alert} />
      ))}
    </div>
  );
}

function AlertRow({ alert }: { alert: Alert }) {
  const sourceLabel = SOURCE_LABEL[alert.source] ?? alert.source.toUpperCase().slice(0, 4);
  const sourceColor = SOURCE_COLOR[alert.source] ?? "bg-slate-500/20 text-slate-300";

  return (
    <div
      className={clsx(
        "group relative flex gap-3 rounded-lg border border-cyan-500/[0.06] bg-[#081320]",
        "border-l-2 px-4 py-3 transition-all",
        SEVERITY_LEFT[alert.severity] ?? "border-l-slate-600",
        SEVERITY_GLOW[alert.severity],
        "hover:bg-[#0c1828] hover:border-cyan-500/[0.1]",
      )}
    >
      {/* Source chip */}
      <div className="flex-shrink-0 pt-0.5">
        <span className={clsx("inline-flex h-6 w-10 items-center justify-center rounded text-[10px] font-bold", sourceColor)}>
          {sourceLabel}
        </span>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <p className="truncate text-sm font-medium text-slate-200 group-hover:text-white">
            {alert.title}
          </p>
          <SeverityBadge severity={alert.severity} size="sm" pulse />
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-slate-600">
          <span className="font-mono text-slate-500">{alert.service_name}</span>
          <span className="text-slate-700">·</span>
          <span className="capitalize">{alert.environment}</span>
          <span className="text-slate-700">·</span>
          <span className="font-mono">{relativeTime(alert.timestamp)}</span>
          {alert.status !== "open" && (
            <>
              <span className="text-slate-700">·</span>
              <span className={clsx(
                "capitalize font-medium",
                alert.status === "resolved"     && "text-green-500",
                alert.status === "acknowledged" && "text-yellow-500",
              )}>
                {alert.status}
              </span>
            </>
          )}
        </div>

        {alert.description && (
          <p className="mt-1.5 line-clamp-1 text-[11px] leading-relaxed text-slate-600">
            {alert.description}
          </p>
        )}
      </div>
    </div>
  );
}
